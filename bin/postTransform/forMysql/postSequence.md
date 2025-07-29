Reference: Apply environment information from $APP_TOOLS_FOLDER/environmentContext.md

# Oracle NEXTVAL → MySQL AUTO_INCREMENT 완전 변환 가이드

## 📋 목차
1. [개요](#1-개요)
2. [변환 작업 규칙](#2-변환-작업-규칙)
3. [유형별 변환 패턴](#3-유형별-변환-패턴)
4. [실제 적용 예시](#4-실제-적용-예시)
5. [검증 및 보정](#5-검증-및-보정)

---

## 1. 개요

Oracle MyBatis XML에서 SEQUENCE.NEXTVAL 패턴을 MySQL AUTO_INCREMENT로 변환하는 **6가지 유형별** 완전 가이드

**전제 조건:**
- 대상 테이블의 시퀀스 컬럼이 AUTO_INCREMENT로 설정되어 있음
- 기존 시퀀스 값은 별도 마이그레이션 완료

---

## 2. 변환 작업 규칙

### 2.1 파일 경로 및 처리 방식

**SOURCE XML 경로:** `$APP_LOGS_FOLDER/mapper/*/extract/*.xml`
**TARGET XML 경로:** `$APP_LOGS_FOLDER/mapper/*/transform/*.xml`
**변환 대상:** `$SOURCE_DBMS_TYPE` → `$TARGET_DBMS_TYPE`

### 2.2 패턴 인식 및 변환 프로세스

```
Oracle MyBatis XML 파일에서 다음 패턴들을 자동 감지하고 해당 유형별 변환 규칙을 적용하세요:

**패턴 감지 규칙:**
1. 유형 1: `<selectKey.*order="BEFORE".*NEXTVAL` 패턴
2. 유형 2: `VALUES.*NEXTVAL.*<selectKey.*CURRVAL` 패턴  
3. 유형 3: `SELECT.*NEXTVAL.*FROM` 패턴 (INSERT INTO ... SELECT)
4. 유형 4: `VALUES.*NEXTVAL` 패턴 (selectKey 태그 없음)
5. 유형 5: `CURRVAL.*FROM DUAL` 패턴 (NEXTVAL 없이 단독 사용)
6. 유형 6: `<selectKey.*BEFORE.*NEXTVAL.*#{.*}.*#{.*}` 패턴 (비즈니스 로직 결합)
7. **유형 7: 기타 패턴** - 위 6가지 유형에 해당하지 않는 NEXTVAL/CURRVAL 사용 패턴

**패턴 미매칭 시 처리 방침:**
- 정의된 6가지 유형에 해당하지 않는 NEXTVAL/CURRVAL 패턴 발견 시
- Oracle-MySQL 변환 전문가 관점에서 다음 원칙에 따라 판단하여 처리:
  1. **Oracle SEQUENCE 동작 원리 분석**: 해당 패턴이 Oracle에서 어떤 동작을 하는지 파악
  2. **MySQL AUTO_INCREMENT 특성 고려**: MySQL에서 동일한 결과를 얻을 수 있는 방법 검토
  3. **MyBatis 프레임워크 호환성**: MyBatis에서 지원하는 MySQL 기능 활용
  4. **데이터 정합성 보장**: 변환 후에도 동일한 데이터 결과 보장
  5. **성능 최적화**: MySQL 환경에서 최적의 성능을 낼 수 있는 방식 선택

**전문가 판단 처리 절차:**
1. 패턴 분석 및 Oracle 동작 방식 설명
2. MySQL 환경에서의 최적 변환 방안 제시
3. 변환 시 주의사항 및 제약사항 명시
4. 필요시 애플리케이션 레벨 수정 권고사항 포함
5. **SQL 주석(-- 또는 /* */)으로 TODO 표시하여 추가 검토 필요성 명시**

**변환 실행 순서:**
1. `$APP_TRANSFORM_FOLDER/postSequence.csv`에서 기 처리된 파일 목록 추출
2. SOURCE XML에서 NEXTVAL/CURRVAL 패턴 포함 파일 중 미처리 파일만 필터링하여 처리 대상 리스트 구성
3. 처리 대상 리스트의 각 파일을 순차적으로 처리:
   - SOURCE 파일 내용을 분석하여 패턴 유형 판단
   - TARGET 파일 상태를 분석 (주석 제외한 실제 코드만)
   - 컴팩트한 승인 요청 형식으로 사용자 확인
   - 승인 시 유형별 변환 규칙 적용
4. TARGET XML 파일로 저장
5. 변환 결과 검증
6. **처리 완료 파일을 CSV에 기록**

**파일별 처리 절차:**
```bash
# 1. 완료 파일 목록 확인 (없으면 생성)
if [ ! -f "$APP_TRANSFORM_FOLDER/postSequence.csv" ]; then
    echo "SourceXML,TransformXML,ProcessDate,Status" > "$APP_TRANSFORM_FOLDER/postSequence.csv"
fi

# 2. 기 처리된 파일 목록 추출
processed_files=$(awk -F',' 'NR>1 {print $1}' "$APP_TRANSFORM_FOLDER/postSequence.csv" | xargs -I {} basename {})

# 3. NEXTVAL/CURRVAL 포함 파일 중 미처리 파일만 필터링
unprocessed_files=()
while IFS= read -r -d '' source_file; do
    filename=$(basename "$source_file")
    if ! echo "$processed_files" | grep -q "^$filename$"; then
        unprocessed_files+=("$source_file")
    fi
done < <(find "$APP_LOGS_FOLDER/mapper/*/extract/" -name "*.xml" -exec grep -l "NEXTVAL\|CURRVAL" {} \; -print0)

# 4. 처리 대상 파일 목록 출력
echo "📋 처리 대상 파일: ${#unprocessed_files[@]}개"
for file in "${unprocessed_files[@]}"; do
    echo "  - $(basename "$file")"
done

# 5. 각 파일 처리 시작
for source_file in "${unprocessed_files[@]}"; do
    target_file="${source_file/extract/transform}"
    target_file="${target_file/_src-/_tgt-}"

    # SOURCE 파일 내용 표시
    echo "📁 SOURCE 파일: $(basename "$source_file")"
    echo "📋 SOURCE 내용:"
    cat "$source_file"

    # TARGET 파일 상태 확인
    echo "📁 TARGET 파일: $(basename "$target_file")"
    echo "📋 TARGET 현재 상태:"
    cat "$target_file"

    # 패턴 분석하여 컴팩트한 승인 요청 제공
    # 사용자 승인 시 보정 실행
    # CSV에 결과 기록
done

# 6. 전체 작업 완료 후 CSV 중복행 삭제
echo "🧹 postSequence.csv 중복행 정리 중..."
temp_csv="/tmp/postSequence_temp.csv"
sort -u "$APP_TRANSFORM_FOLDER/postSequence.csv" > "$temp_csv"
mv "$temp_csv" "$APP_TRANSFORM_FOLDER/postSequence.csv"
echo "✅ CSV 중복행 삭제 완료"
```

**처리 완료 파일 관리:**
- **CSV 위치:** `$APP_TRANSFORM_FOLDER/postSequence.csv`
- **CSV 헤더:** `SourceXML,TransformXML,ProcessDate,Status`
- **Status 값:** `COMPLETED` (보정완료), `SKIPPED` (건너뜀), `NO_CHANGE` (보정불필요)
- **중복 방지:** 재실행 시 CSV에 등록된 파일들은 자동 제외
- **전체 완료 후:** postSequence.csv의 중복행을 삭제하여 데이터 정합성 보장

**출력 형식:**
- 파일별 변환 전/후 비교
- 감지된 패턴 유형 표시
- 변경 사항 요약
- 검증 포인트 제시
```

### 2.3 유형별 변환 규칙 요약

1. **유형 1 (selectKey BEFORE)**: `<selectKey order="BEFORE">` 완전 제거, `useGeneratedKeys="true"` 설정
2. **유형 2 (VALUES NEXTVAL + AFTER CURRVAL)**: VALUES에서 NEXTVAL 제거, `<selectKey order="AFTER">` 제거
3. **유형 3 (INSERT SELECT NEXTVAL)**: SELECT절에서 NEXTVAL 제거
4. **유형 4 (VALUES 직접 NEXTVAL)**: VALUES에서 NEXTVAL 제거 (selectKey 없음)
5. **유형 5 (CURRVAL 단독)**: `CURRVAL` → `LAST_INSERT_ID()` 변경
6. **유형 6 (비즈니스 로직 결합)**: 비즈니스 로직 컬럼 NULL 처리, TODO 주석 추가

---

## 3. 유형별 변환 패턴

### 3.1 유형 1: selectKey BEFORE 방식
**특징:** INSERT 전에 시퀀스 값을 미리 가져와서 사용

**Oracle 원본:**
```xml
<insert id="insertMethod" parameterType="..." useGeneratedKeys="true" keyProperty="seqColumn">
    <selectKey resultType="java.lang.Integer" keyProperty="seqColumn" order="BEFORE">
        SELECT SEQUENCE_NAME.NEXTVAL FROM DUAL
    </selectKey>
    INSERT INTO TABLE_NAME (SEQ_COLUMN, OTHER_COLUMNS...)
    VALUES (#{seqColumn}, #{otherValues}...)
</insert>
```

**MySQL 변환:**
```xml
<insert id="insertMethod" parameterType="..." useGeneratedKeys="true" keyProperty="seqColumn">
    INSERT INTO TABLE_NAME (OTHER_COLUMNS...)
    VALUES (#{otherValues}...)
</insert>
```

**변환 작업:**
- `<selectKey order="BEFORE">` 태그 완전 제거
- INSERT 컬럼 목록에서 AUTO_INCREMENT 컬럼 제거
- VALUES에서 해당 파라미터 제거
- `useGeneratedKeys="true" keyProperty` 유지

---

### 3.2 유형 2: VALUES 직접 NEXTVAL + AFTER CURRVAL 방식
**특징:** INSERT 시 NEXTVAL 사용, INSERT 후 CURRVAL로 생성된 값 반환

**Oracle 원본:**
```xml
<insert id="insertMethod" parameterType="...">
    INSERT INTO TABLE_NAME (COL1, SEQ_COLUMN, COL3...)
    VALUES (#{col1}, SEQUENCE_NAME.NEXTVAL, #{col3}...)
    <selectKey keyProperty="seqColumn" resultType="int" order="AFTER">
        SELECT SEQUENCE_NAME.CURRVAL FROM DUAL
    </selectKey>
</insert>
```

**MySQL 변환 (권장 방법):**
```xml
<insert id="insertMethod" parameterType="..." useGeneratedKeys="true" keyProperty="seqColumn">
    INSERT INTO TABLE_NAME (COL1, COL3...)
    VALUES (#{col1}, #{col3}...)
</insert>
```

**MySQL 변환 (대안 방법):**
```xml
<insert id="insertMethod" parameterType="...">
    INSERT INTO TABLE_NAME (COL1, COL3...)
    VALUES (#{col1}, #{col3}...)
    <selectKey keyProperty="seqColumn" resultType="int" order="AFTER">
        SELECT LAST_INSERT_ID()
    </selectKey>
</insert>
```

**변환 작업:**
- VALUES에서 `SEQUENCE_NAME.NEXTVAL` 제거
- 컬럼 목록에서 AUTO_INCREMENT 컬럼 제거
- `<selectKey order="AFTER">` 제거하고 `useGeneratedKeys="true"` 추가
- 또는 `CURRVAL` → `LAST_INSERT_ID()` 변경
- `keyProperty` 반드시 유지 (Java 객체에 생성된 ID 반환)

---

### 3.3 유형 3: INSERT INTO ... SELECT with NEXTVAL
**특징:** SELECT 구문에서 NEXTVAL을 사용하여 INSERT

**Oracle 원본:**
```xml
<insert id="insertMethod" parameterType="...">
    INSERT INTO TABLE_NAME (columns...)
    SELECT SEQUENCE_NAME.NEXTVAL AS SEQ_COLUMN,
           OTHER_COLUMNS...
    FROM SOURCE_TABLE
    WHERE conditions...
</insert>
```

**MySQL 변환:**
```xml
<insert id="insertMethod" parameterType="...">
    INSERT INTO TABLE_NAME (OTHER_COLUMNS...)
    SELECT OTHER_COLUMNS...
    FROM SOURCE_TABLE  
    WHERE conditions...
</insert>
```

**변환 작업:**
- SELECT절에서 `SEQUENCE_NAME.NEXTVAL AS SEQ_COLUMN` 제거
- INSERT 컬럼 목록에서 AUTO_INCREMENT 컬럼 제거
- 복잡한 배치 처리의 경우 별도 처리 방식 고려

---

### 3.4 유형 4: VALUES 절 직접 NEXTVAL (selectKey 없음)
**특징:** INSERT VALUES에서 NEXTVAL을 직접 사용하되, selectKey가 없는 경우

**Oracle 원본:**
```xml
<insert id="insertBatch" parameterType="...">
    INSERT INTO TABLE_NAME (
        SEQ_COLUMN,
        OTHER_COLUMNS...
    ) VALUES (
        SQ_SEQUENCE_01.NEXTVAL,
        #{param1},
        #{param2}...
    )
</insert>
```

**MySQL 변환:**
```xml
<insert id="insertBatch" parameterType="...">
    INSERT INTO TABLE_NAME (
        OTHER_COLUMNS...
    ) VALUES (
        #{param1},
        #{param2}...
    )
</insert>
```

**변환 작업:**
- INSERT 컬럼 목록에서 AUTO_INCREMENT 컬럼 제거
- VALUES에서 `SEQUENCE.NEXTVAL` 제거
- 생성된 키 값이 필요하지 않은 배치 처리에 주로 사용

---

### 3.5 유형 5: CURRVAL 단독 사용 (NEXTVAL 없이)
**특징:** 동일 세션에서 이전에 호출된 NEXTVAL의 현재 값을 참조

**Oracle 원본:**
```xml
<select id="getCurrentSeqValue" resultType="int">
    SELECT SEQUENCE_NAME.CURRVAL FROM DUAL
</select>
```

**MySQL 변환:**
```xml
<select id="getCurrentSeqValue" resultType="int">
    SELECT LAST_INSERT_ID()
</select>
```

**변환 작업:**
- `SEQUENCE.CURRVAL` → `LAST_INSERT_ID()` 변경
- `FROM DUAL` 제거
- 주의: MySQL의 LAST_INSERT_ID()는 연결별로 관리됨

---

### 3.6 유형 6: NEXTVAL + 비즈니스 로직 결합 패턴
**특징:** selectKey BEFORE로 시퀀스 값을 획득하여 다른 컬럼의 비즈니스 로직에도 활용

**Oracle 원본:**
```xml
<insert id="insertByBusiness" parameterType="..." useGeneratedKeys="true" keyProperty="seqColumn">
    <selectKey resultType="java.lang.Integer" keyProperty="seqColumn" order="BEFORE">
        SELECT SEQUENCE_NAME.NEXTVAL FROM DUAL
    </selectKey>
    INSERT INTO TABLE_NAME (SEQ_COLUMN, BUSINESS_COLUMN, OTHER_COLUMNS...)
    VALUES (#{seqColumn}, to_char(sysdate,'yyyymmdd')||'-'||#{seqColumn}, #{otherValues}...)
</insert>
```

**MySQL 변환 (문제 상황):**
```xml
<insert id="insertByBusiness" parameterType="..." useGeneratedKeys="true" keyProperty="seqColumn">
    INSERT INTO TABLE_NAME (BUSINESS_COLUMN, OTHER_COLUMNS...)
    VALUES (CONCAT(DATE_FORMAT(NOW(),'%Y%m%d'),'-',LAST_INSERT_ID()), #{otherValues}...)
</insert>
```

**MySQL 변환 (올바른 해결):**
```xml
<insert id="insertByBusiness" parameterType="..." useGeneratedKeys="true" keyProperty="seqColumn">
    INSERT INTO TABLE_NAME (BUSINESS_COLUMN, OTHER_COLUMNS...)
    VALUES (NULL, #{otherValues}...)
    
    -- TODO: Sequence 처리 문제 해결 - INSERT 후 BUSINESS_COLUMN 업데이트
    <selectKey resultType="int" keyProperty="seqColumn" order="AFTER">
        SELECT LAST_INSERT_ID();
        UPDATE TABLE_NAME 
        SET BUSINESS_COLUMN = CONCAT(DATE_FORMAT(NOW(),'%Y%m%d'),'-',SEQ_COLUMN)
        WHERE SEQ_COLUMN = LAST_INSERT_ID()
    </selectKey>
</insert>
```

**변환 작업:**
- INSERT 컬럼 목록에서 AUTO_INCREMENT 컬럼 제거
- 비즈니스 로직이 포함된 컬럼은 NULL로 INSERT
- selectKey AFTER로 UPDATE 처리 추가
- 또는 애플리케이션 레벨에서 INSERT 후 별도 UPDATE 처리
- **SQL 주석으로 TODO 표시**

**주의사항:**
- LAST_INSERT_ID()는 INSERT 실행 중에는 0을 반환
- 비즈니스 로직이 복잡할수록 애플리케이션 레벨 처리 권장
- **SQL 주석(-- 또는 /* */)으로 TODO 표시하여 후속 작업 필요성 명시**

---

## 5. 검증 및 보정

### 5.1 SOURCE-TARGET 변환 검증 프로세스

**검증 대상 식별:**
SOURCE XML 파일 중 다음 패턴을 포함한 파일들만 검토:
- NEXTVAL 패턴 포함
- CURRVAL 패턴 포함

**처리 완료 파일 관리:**
- **완료 파일 목록:** `$APP_TRANSFORM_FOLDER/postSequence.csv`
- **CSV 형식:** `SourceXML,TransformXML,ProcessDate,Status`
- **중복 작업 방지:** CSV에 등록된 파일은 재처리 시 자동 제외

**검증 절차:**
```bash
# 1. 완료 파일 목록 확인 (없으면 생성)
if [ ! -f "$APP_TRANSFORM_FOLDER/postSequence.csv" ]; then
    echo "SourceXML,TransformXML,ProcessDate,Status" > "$APP_TRANSFORM_FOLDER/postSequence.csv"
fi

# 2. 대상 파일 스캔 (완료된 파일 제외)
find $APP_LOGS_FOLDER/mapper/*/extract/ -name "*.xml" -exec grep -l "NEXTVAL\|CURRVAL" {} \; | \
while read source_file; do
    # CSV에서 이미 처리된 파일인지 확인
    if ! grep -q "$(basename "$source_file")" "$APP_TRANSFORM_FOLDER/postSequence.csv"; then
        echo "처리 대상: $source_file"
    else
        echo "이미 처리됨 (건너뜀): $source_file"
    fi
done
```

1. **SOURCE-TARGET 매핑 검증**
   - SOURCE XML과 대응되는 TARGET XML 존재 확인
   - 파일 구조 및 매핑 ID 일치성 검증

2. **변환 규칙 적용 검증**
   각 유형별 변환 규칙이 정확히 적용되었는지 검토

3. **오류 패턴 감지 및 보정**
   - keyProperty 누락 또는 잘못된 매핑
   - useGeneratedKeys 설정 누락
   - 불완전한 NEXTVAL/CURRVAL 제거
   - 컬럼-값 불일치
   - XML 문법 오류

### 5.2 파일별 보정 승인 프로세스

각 TARGET XML 파일 보정 전에 다음과 같이 승인 요청:

```
================================
파일 보정 승인 요청
================================

📁 SOURCE (Oracle): [파일경로]
📁 TARGET (MySQL): [파일경로] 
🔍 감지된 유형: 유형 N (패턴 설명)
📊 테이블: [테이블명]
🔑 AUTO_INCREMENT: [컬럼명] (상태: 정상/누락)

📋 현재 TARGET 상태 분석:
❌ 발견된 문제:
   - [구체적인 문제점 나열]

🔧 적용할 보정:
   - [구체적인 보정 내용]

📊 변환 품질: [현재상태] → [보정후 예상상태]

📈 보정 영향도:
   - 기능적 개선: [설명]
   - 성능 개선: [설명]  
   - 호환성 개선: [설명]

⚠️  주의사항: [있다면 명시]

================================

보정을 진행하시겠습니까? (y/n/s/q)
y: 승인하고 다음 파일로
n: 건너뛰고 다음 파일로  
s: 모든 보정 자동 승인
q: 작업 중단
```

**사용자 응답에 따른 처리:**
- `y` 또는 `s`: 보정 실행 후 "✅ 보정 완료: [파일명]" 표시 → **CSV에 기록**
- `n`: "❌ 보정 건너뜀: [파일명]" 표시 후 다음 파일 → **CSV에 SKIPPED 상태로 기록**
- `q`: 작업 중단 및 현재까지 결과 리포트
- `s` 선택 시: 이후 파일들은 승인 절차 없이 자동 보정

보정이 불필요한 파일은: "✅ 보정 불필요: [파일명] (변환 상태: 정상)" → **CSV에 COMPLETED 상태로 기록**

**CSV 기록 형식:**
```bash
# 보정 완료 시
echo "$source_xml,$target_xml,$(date '+%Y-%m-%d %H:%M:%S'),COMPLETED" >> "$APP_TRANSFORM_FOLDER/postSequence.csv"

# 보정 건너뜀 시  
echo "$source_xml,$target_xml,$(date '+%Y-%m-%d %H:%M:%S'),SKIPPED" >> "$APP_TRANSFORM_FOLDER/postSequence.csv"

# 보정 불필요 시
echo "$source_xml,$target_xml,$(date '+%Y-%m-%d %H:%M:%S'),NO_CHANGE" >> "$APP_TRANSFORM_FOLDER/postSequence.csv"
```

### 5.3 검증 체크리스트

**변환 후 필수 확인 사항:**
- [ ] `<selectKey order="BEFORE">` 완전 제거 확인
- [ ] `useGeneratedKeys="true" keyProperty` 설정 확인
- [ ] INSERT 컬럼 목록에서 AUTO_INCREMENT 컬럼 제거 확인
- [ ] VALUES에서 NEXTVAL 파라미터 제거 확인
- [ ] keyProperty 값 유지 확인 (중요!)
- [ ] XML 문법 오류 없음 확인

**데이터베이스 검증:**
```sql
-- AUTO_INCREMENT 설정 확인
SELECT TABLE_NAME, COLUMN_NAME, EXTRA 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA='database_name' 
AND EXTRA LIKE '%auto_increment%';

-- 특정 테이블 구조 확인
SHOW CREATE TABLE table_name;
```

### 5.4 검증 리포트 생성

**리포트 위치:** `/tmp/sequence_conversion_report_YYYYMMDD_HHMMSS.md`

**리포트 내용:**
```
# Sequence 변환 검증 리포트

## 검토 대상 파일 목록
- 총 SOURCE 파일: N개
- NEXTVAL/CURRVAL 포함 파일: N개
- 대응 TARGET 파일: N개
- 이전 처리 완료 파일: N개 (제외됨)

## 처리 결과 요약
- 보정 완료 (COMPLETED): N개
- 보정 건너뜀 (SKIPPED): N개  
- 보정 불필요 (NO_CHANGE): N개
- 처리 완료 파일 목록: $APP_TRANSFORM_FOLDER/postSequence.csv

## AUTO_INCREMENT 설정 검증
### 검증된 테이블: N개
### AUTO_INCREMENT 설정 완료: N개
### AUTO_INCREMENT 설정 누락: N개

## 변환 품질 분석
### 정상 변환: N개
### 오류 발견 및 보정: N개

## 파일별 상세 분석
### [파일명]
- 유형: 유형 1/2/3/4/5/6
- 대상 테이블: [테이블명]
- AUTO_INCREMENT 컬럼: [컬럼명]
- 변환 상태: 정상/오류보정
- 발견된 문제: [구체적 문제점]
- 적용된 보정: [보정 내용]
- DB 검증 결과: PASS/FAIL
- CSV 기록 상태: COMPLETED/SKIPPED/NO_CHANGE

## 권장사항
- AUTO_INCREMENT 값 조정이 필요한 테이블: [목록]
- 애플리케이션 레벨 테스트 권장
- 성능 테스트 권장 (특히 배치 처리)

## 다음 실행 시 참고사항
- 처리 완료된 파일들은 $APP_TRANSFORM_FOLDER/postSequence.csv에서 관리됨
- 재실행 시 CSV에 등록된 파일들은 자동으로 제외됨
- CSV 파일을 삭제하면 모든 파일을 다시 처리함
```

### 5.5 성능 최적화 팁

- AUTO_INCREMENT 값 범위 확인 (기존 시퀀스 최대값과 비교)
- 배치 처리 시 useGeneratedKeys 설정 최적화
- 트랜잭션 처리 방식 검토
- 애플리케이션 레벨 테스트 권장

---

## 📚 참고사항

**MySQL AUTO_INCREMENT 특징:**
- 연결별로 LAST_INSERT_ID() 값 관리
- 테이블당 하나의 AUTO_INCREMENT 컬럼만 허용
- 기본값은 1부터 시작, 1씩 증가

**Oracle SEQUENCE와의 차이점:**
- Oracle: 세션별 CURRVAL 관리
- MySQL: 연결별 LAST_INSERT_ID() 관리
- Oracle: 명시적 NEXTVAL 호출 필요
- MySQL: INSERT 시 자동 증가

## 4. 주의 사항
- keyProperty 매핑 확인 필수
- 테이블별 AUTO_INCREMENT 컬럼 설정 확인
- 기존 시퀀스 값과의 정합성 검증
- 트랜잭션 처리 방식 검토
