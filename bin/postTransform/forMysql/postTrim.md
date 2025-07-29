Reference: Apply environment information from $APP_TOOLS_FOLDER/environmentContext.md

# Oracle TRIM/LTRIM/RTRIM → MySQL 변환 검증 가이드

## 📋 목차
1. [개요](#1-개요)
2. [변환 작업 규칙](#2-변환-작업-규칙)
3. [검증 및 보정](#3-검증-및-보정)

---

## 1. 개요

Oracle MyBatis XML에서 TRIM/LTRIM/RTRIM 함수가 MySQL로 올바르게 변환되었는지 검증하는 가이드

**Oracle TRIM 함수:**
```sql
-- Oracle 문법
TRIM([LEADING|TRAILING|BOTH] [trim_character] FROM string)
LTRIM(string [, trim_character])  -- 특정 문자 지정 가능
RTRIM(string [, trim_character])  -- 특정 문자 지정 가능

-- 예시
TRIM(' ' FROM column_name)
TRIM(LEADING '0' FROM column_name)
LTRIM(column_name, '0')  -- '0' 문자 제거
RTRIM(column_name, 'x')  -- 'x' 문자 제거
```

**MySQL TRIM 함수:**
```sql
-- MySQL 문법
TRIM([{BOTH | LEADING | TRAILING} [remstr] FROM] str)
LTRIM(str)  -- 공백만 제거, 특정 문자 지정 불가
RTRIM(str)  -- 공백만 제거, 특정 문자 지정 불가

-- 예시
TRIM(column_name)
TRIM(LEADING '0' FROM column_name)
LTRIM(column_name)  -- 공백만 제거
RTRIM(column_name)  -- 공백만 제거
```

**핵심 차이점:**
1. **LTRIM/RTRIM 제한**: MySQL은 공백만 제거, Oracle은 특정 문자 지정 가능
2. **변환 필요**: Oracle `LTRIM(col, 'x')` → MySQL `TRIM(LEADING 'x' FROM col)`
3. **변환 필요**: Oracle `RTRIM(col, 'x')` → MySQL `TRIM(TRAILING 'x' FROM col)`

**전제 조건:**
- Oracle TRIM 함수들이 MySQL 호환 형태로 변환되어 있음
- **전체 SQL 컨텍스트를 종합적으로 분석하여 변환 품질 판단**

---

## 2. 변환 작업 규칙

### 2.1 파일 경로 및 처리 방식

**SOURCE XML 경로:** `$APP_LOGS_FOLDER/mapper/*/extract/*.xml`
**TARGET XML 경로:** `$APP_LOGS_FOLDER/mapper/*/transform/*.xml`
**변환 대상:** `$SOURCE_DBMS_TYPE` → `$TARGET_DBMS_TYPE`

### 2.2 패턴 인식 및 변환 검증 프로세스

```
Oracle MyBatis XML 파일에서 다음 패턴들을 자동 감지하고 변환 품질을 검증하세요:

**패턴 감지 규칙:**
- `TRIM()` 함수 사용 패턴
- `LTRIM(column)` - 공백 제거 패턴
- `LTRIM(column, 'char')` - 특정 문자 제거 패턴 (변환 필요)
- `RTRIM(column)` - 공백 제거 패턴
- `RTRIM(column, 'char')` - 특정 문자 제거 패턴 (변환 필요)
- `TRIM(LEADING/TRAILING/BOTH)` 방향 지정 패턴

**전체 SQL 분석 원칙:**
- **전체 SQL 구문을 종합적으로 분석하여 변환 품질 판단**
- SELECT, FROM, WHERE, HAVING, ORDER BY 등 모든 절과의 연관성 고려
- 다른 문자열 함수들과의 조합 및 호환성 검토
- 조건절, 조인 조건 등에서의 TRIM 함수 사용 분석
- **SOURCE를 참조해서 의도에 맞게 MySQL 변환이 정확히 구현되었는지 전문가 관점에서 판단**

**변환 검증 실행 순서:**
1. `$APP_TRANSFORM_FOLDER/postTrim.csv`에서 기 처리된 파일 목록 추출
2. SOURCE XML에서 TRIM/LTRIM/RTRIM 패턴 포함 파일 중 미처리 파일만 필터링
3. 처리 대상 리스트의 각 파일을 순차적으로 처리:
   - SOURCE 파일의 전체 SQL 구문 분석
   - TARGET 파일의 전체 SQL 구문 분석 (주석 제외한 실제 코드만)
   - **전체 SQL 컨텍스트에서 변환 품질 종합 판단**
   - 컴팩트한 승인 요청 형식으로 사용자 확인
   - 승인 시 보정 및 TODO 주석 추가
4. TARGET XML 파일로 저장
5. **처리 완료 파일을 CSV에 기록**

**파일별 처리 절차:**
```bash
# 1. 완료 파일 목록 확인 (없으면 생성)
if [ ! -f "$APP_TRANSFORM_FOLDER/postTrim.csv" ]; then
    echo "SourceXML,TransformXML,ProcessDate,Status" > "$APP_TRANSFORM_FOLDER/postTrim.csv"
fi

# 2. 기 처리된 파일 목록 추출
processed_files=$(awk -F',' 'NR>1 {print $1}' "$APP_TRANSFORM_FOLDER/postTrim.csv" | xargs -I {} basename {})

# 3. TRIM/LTRIM/RTRIM 포함 파일 중 미처리 파일만 필터링
unprocessed_files=()
while IFS= read -r -d '' source_file; do
    filename=$(basename "$source_file")
    if ! echo "$processed_files" | grep -q "^$filename$"; then
        unprocessed_files+=("$source_file")
    fi
done < <(find "$APP_LOGS_FOLDER/mapper/*/extract/" -name "*.xml" -exec grep -l "TRIM\|LTRIM\|RTRIM" {} \; -print0)

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

    # 전체 SQL 분석하여 컴팩트한 승인 요청 제공
    # 사용자 승인 시 보정 실행 및 TODO 주석 추가
    # CSV에 결과 기록
done

# 6. 전체 작업 완료 후 CSV 중복행 삭제
echo "🧹 postTrim.csv 중복행 정리 중..."
temp_csv="/tmp/postTrim_temp.csv"
sort -u "$APP_TRANSFORM_FOLDER/postTrim.csv" > "$temp_csv"
mv "$temp_csv" "$APP_TRANSFORM_FOLDER/postTrim.csv"
echo "✅ CSV 중복행 삭제 완료"
```

**처리 완료 파일 관리:**
- **CSV 위치:** `$APP_TRANSFORM_FOLDER/postTrim.csv`
- **CSV 헤더:** `SourceXML,TransformXML,ProcessDate,Status`
- **Status 값:** `COMPLETED` (보정완료), `SKIPPED` (건너뜀), `NO_CHANGE` (보정불필요)
- **중복 방지:** 재실행 시 CSV에 등록된 파일들은 자동 제외
- **전체 완료 후:** postTrim.csv의 중복행을 삭제하여 데이터 정합성 보장
```

---

## 3. 검증 및 보정

### 3.1 SOURCE-TARGET 변환 검증 프로세스

**검증 대상 식별:**
SOURCE XML 파일 중 다음 패턴을 포함한 파일들만 검토:
- TRIM 함수 포함
- LTRIM 함수 포함 (특히 2번째 매개변수 있는 경우)
- RTRIM 함수 포함 (특히 2번째 매개변수 있는 경우)
- TRIM(LEADING/TRAILING/BOTH) 패턴 포함

**처리 완료 파일 관리:**
- **완료 파일 목록:** `$APP_TRANSFORM_FOLDER/postTrim.csv`
- **CSV 형식:** `SourceXML,TransformXML,ProcessDate,Status`
- **중복 작업 방지:** CSV에 등록된 파일은 재처리 시 자동 제외

### 3.2 파일별 보정 승인 프로세스

각 TARGET XML 파일 보정 전에 다음과 같이 승인 요청:

```
================================
TRIM 함수 패턴 검증 승인 요청
================================

📁 SOURCE (Oracle): [파일경로]
📁 TARGET (MySQL): [파일경로] 
🔍 감지된 패턴: [TRIM/LTRIM/RTRIM 패턴 설명]

📋 전체 SQL 분석 결과:
🔍 SOURCE 의도 분석: [SQL 전체 구문 분석 결과]
🔍 MySQL 변환 상태: [변환된 SQL 분석 결과]

📋 현재 TARGET 상태 분석:
❌ 발견된 문제:
   - [구체적인 문제점 나열]

🔧 적용할 보정:
   - [구체적인 보정 내용]
   - SQL 주석 추가: -- TODO: 변경내용 확인

📊 변환 품질: [현재상태] → [보정후 예상상태]

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

보정이 불필요한 파일은: "✅ 보정 불필요: [파일명] (변환 상태: 정상)" → **CSV에 NO_CHANGE 상태로 기록**

### 3.3 TODO 주석 추가 규칙

**보정 시 반드시 추가할 SQL 주석:**
```sql
-- TODO: 변경내용 확인 - [구체적인 변경 사항 설명]
```

**주석 추가 위치:**
- 변경된 SQL 구문 바로 위에 추가
- 여러 변경사항이 있을 경우 각각에 개별 TODO 주석 추가

**주석 예시:**
```sql
-- TODO: 변경내용 확인 - LTRIM 2번째 매개변수를 TRIM(LEADING)으로 변환
SELECT TRIM(LEADING '0' FROM column_name) as trimmed_value
FROM table_name

-- TODO: 변경내용 확인 - RTRIM 2번째 매개변수를 TRIM(TRAILING)으로 변환
SELECT TRIM(TRAILING 'x' FROM column_name) as trimmed_value
FROM table_name
```

### 3.4 검증 리포트 생성

**리포트 위치:** `/tmp/trim_conversion_report_YYYYMMDD_HHMMSS.md`

**리포트 내용:**
```
# TRIM 함수 변환 검증 리포트

## 검토 대상 파일 목록
- 총 SOURCE 파일: N개
- TRIM/LTRIM/RTRIM 포함 파일: N개
- 대응 TARGET 파일: N개
- 이전 처리 완료 파일: N개 (제외됨)

## 처리 결과 요약
- 보정 완료 (COMPLETED): N개
- 보정 건너뜀 (SKIPPED): N개  
- 보정 불필요 (NO_CHANGE): N개
- 처리 완료 파일 목록: $APP_TRANSFORM_FOLDER/postTrim.csv

## 변환 패턴별 분석
### LTRIM/RTRIM 2번째 매개변수 변환: N개
### 단순 공백 제거 TRIM: N개
### TRIM(LEADING/TRAILING/BOTH) 패턴: N개

## 파일별 상세 분석
### [파일명]
- 감지된 패턴: [TRIM/LTRIM/RTRIM]
- 변환 상태: 정상/오류보정
- 발견된 문제: [구체적 문제점]
- 적용된 보정: [보정 내용]
- TODO 주석 추가: [추가된 주석 내용]
- CSV 기록 상태: COMPLETED/SKIPPED/NO_CHANGE

## 권장사항
- TODO 주석이 추가된 파일들은 추가 검토 필요
- LTRIM/RTRIM 2번째 매개변수 변환 결과 테스트 필요
- 애플리케이션 레벨 문자열 처리 로직 검증 권장

## 다음 실행 시 참고사항
- 처리 완료된 파일들은 $APP_TRANSFORM_FOLDER/postTrim.csv에서 관리됨
- 재실행 시 CSV에 등록된 파일들은 자동으로 제외됨
- CSV 파일을 삭제하면 모든 파일을 다시 처리함
```

---

## 📚 참고사항

**주요 변환 패턴:**
```sql
-- Oracle → MySQL 변환 예시

-- 1. 공백 제거 (변환 불필요)
Oracle: LTRIM(column_name)     → MySQL: LTRIM(column_name)
Oracle: RTRIM(column_name)     → MySQL: RTRIM(column_name)

-- 2. 특정 문자 제거 (변환 필요)
Oracle: LTRIM(column_name, '0') → MySQL: TRIM(LEADING '0' FROM column_name)
Oracle: RTRIM(column_name, 'x') → MySQL: TRIM(TRAILING 'x' FROM column_name)

-- 3. TRIM 함수 (변환 불필요)
Oracle: TRIM(' ' FROM column_name) → MySQL: TRIM(' ' FROM column_name)
Oracle: TRIM(LEADING '0' FROM column_name) → MySQL: TRIM(LEADING '0' FROM column_name)
```

**검증 핵심 원칙:**
- **LTRIM/RTRIM 2번째 매개변수 사용 여부 확인 필수**
- **전체 SQL 구문을 종합적으로 분석**
- **SOURCE를 참조해서 의도에 맞게 MySQL 변환이 정확히 구현되었는지 판단**
- **변경사항에 대한 TODO 주석 반드시 추가**

**주의사항:**
- MySQL LTRIM/RTRIM은 공백만 제거 가능
- Oracle의 특정 문자 제거 기능은 TRIM(LEADING/TRAILING)으로 변환 필요
- 성능상 차이는 미미하나 문법 정확성 중요
