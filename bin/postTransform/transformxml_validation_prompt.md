# TransformXML 문법적 완결성 확인 및 수정 프롬프트
Reference: Apply environment information from $APP_TOOLS_FOLDER/environmentContext.md

**Language Instruction**: 모든 메시지, 프롬프트, 사용자 상호작용은 한국어로 표시되어야 합니다.

**IMPORTANT**: 이 프로세스는 예외 기반 승인 방식으로 진행됩니다. 파일 리스트를 먼저 생성하고, 문제가 없는 파일들은 자동으로 처리하며, 오류가 발견된 파일에 대해서만 사용자 승인을 받습니다.

## 목표
TransformXML의 문법적 완결성을 확인하고 수정합니다. TransformXML은 $SOURCE_DBMS_TYPE에서 $TARGET_DBMS_TYPE으로 변경된 SQL을 포함하는 XML 파일입니다. $TARGET_DBMS_TYPE의 전문가로서 변경된 SQL을 검증하고 오류가 있을 시 수정을 수행해야 합니다.

## 파일 위치 및 패턴
- **TransformXML**: `$APP_LOGS_FOLDER/mapper/*/transform/*.xml` (파일명에 'tgt' 포함)
- **OriginXML**: `$APP_LOGS_FOLDER/mapper/*/extract/*.xml` (파일명에 'src' 포함)
- **수정 규칙**: `editUIErrors.md` 참조

## 전문가 모드 설정
[$TARGET_DBMS_TYPE Expert Mode]
- $SOURCE_DBMS_TYPE에서 $TARGET_DBMS_TYPE로의 SQL 변환 전문 지식 활용
- $TARGET_DBMS_TYPE 특화 구문, 함수, 데이터 타입에 대한 깊은 이해
- $TARGET_DBMS_TYPE 성능 최적화 및 모범 사례 적용
- $TARGET_DBMS_TYPE 호환성 및 제약사항 고려

## 핵심 원칙
1. **개별 파일 검증**: 각 XML 파일은 개별적으로 분석되어야 함 (패턴 방식의 일괄 수정 금지)
2. **예외 기반 승인**: 오류가 발견된 파일에 대해서만 사용자 승인 필요
3. **자동 진행**: 문제가 없는 파일들은 자동으로 다음 파일로 진행
4. **전체 파일 검증**: 모든 TransformXML 파일에 대해 문법적 완결성 확인 필수
5. **안전한 백업**: 수정 전 백업 파일 생성 (파일명_backup_YYYYMMDD_HHMMSS.xml)

---

## Task Instructions

### 0. 환경변수 검증 및 시스템 초기화

**환경변수 검증**:
```bash
# 필수 환경변수 존재 여부 확인
echo "APP_TOOLS_FOLDER: ${APP_TOOLS_FOLDER:-'❌ 미설정'}"
echo "APP_LOGS_FOLDER: ${APP_LOGS_FOLDER:-'❌ 미설정'}"
echo "SOURCE_DBMS_TYPE: ${SOURCE_DBMS_TYPE:-'❌ 미설정'}"
echo "TARGET_DBMS_TYPE: ${TARGET_DBMS_TYPE:-'❌ 미설정'}"
```

**시스템 설정 표시**:
```
================================
TransformXML 문법적 완결성 검증 시스템
================================

$SOURCE_DBMS_TYPE → $TARGET_DBMS_TYPE SQL 변환 검증 및 수정

파일 위치:
- TransformXML: $APP_LOGS_FOLDER/mapper/*/transform/*.xml
- OriginXML: $APP_LOGS_FOLDER/mapper/*/extract/*.xml

검증 방식: 예외 기반 승인 (오류 발견 시에만 사용자 승인)
전문가 모드: $TARGET_DBMS_TYPE 전문가

================================
```

**전체 TransformXML 파일 스캔 및 처리 계획**:
1. `$APP_LOGS_FOLDER/mapper/*/transform/*.xml` 경로에서 모든 XML 파일 검색
2. 각 파일의 기본 정보 수집 (파일명, 크기, 수정일)
3. 파일 목록을 사용자에게 표시하고 처리 시작

**파일 목록 및 처리 계획 표시**:
```
================================
TransformXML 파일 스캔 결과 및 처리 계획
================================

📁 스캔 경로: $APP_LOGS_FOLDER/mapper/*/transform/
📊 발견된 파일 수: [total_count]개

📋 파일 목록:
[번호] [파일명] [크기] [수정일]
1. transform_user_001_tgt.xml (2.3KB) 2025-07-30
2. transform_product_002_tgt.xml (1.8KB) 2025-07-30
...

🔄 처리 방식:
- 각 파일을 순차적으로 검증
- 문제가 없는 파일: 자동으로 다음 파일 진행
- 오류 발견 시: 사용자 승인 후 수정 진행
- 전체 진행 상황을 실시간으로 표시

================================
검증을 시작하시겠습니까? (y/n/q)
y: 예, 검증 시작
n: 아니오, 특정 파일만 선택
q: 종료
================================
```

**STOP HERE - WAIT FOR USER INPUT**

시스템은 이 지점에서 일시 정지하고 사용자가 y, n, q 중 하나를 입력할 때까지 기다려야 합니다.

### 1. 개별 파일 문법적 완결성 검증 (자동 진행)

각 TransformXML 파일에 대해 다음 단계를 수행:

**1.1 파일 분석 진행 상황 표시**:
```
================================
파일 검증 진행 중 ([current]/[total])
================================

📁 현재 파일: [transform_xml_filename]
📄 대응 원본: [origin_xml_filename]
🔍 분석 상태: 진행 중...

✅ XML 구조 검증 완료
✅ SQL 구문 추출 완료
🔍 $TARGET_DBMS_TYPE 호환성 검사 중...
```

**1.2 검증 결과에 따른 자동 분기**:

**A) 문제가 없는 경우 (자동 진행)**:
```
✅ [transform_xml_filename] 검증 완료 - 문제 없음
   - XML 구조: 정상
   - SQL 구문: [sql_count]개 모두 정상
   - $TARGET_DBMS_TYPE 호환성: 100%
   
🔄 다음 파일로 자동 진행...
```

**B) 오류 발견 시 (사용자 승인 필요)**:
```
================================
⚠️  오류 발견: [transform_xml_filename]
================================

📊 기본 정보:
   - 파일 크기: [file_size]
   - SQL 블록 수: [sql_block_count]
   - 변환 유형: $SOURCE_DBMS_TYPE → $TARGET_DBMS_TYPE

🔍 XML 구조 검증:
   ✅ XML 형식: 유효
   ✅ 인코딩: UTF-8
   ✅ 필수 태그: 모두 존재

❌ SQL 문법 검증 결과 ($TARGET_DBMS_TYPE 관점):
   📋 총 SQL 구문: [total_sql_count]개
   ✅ 정상 구문: [valid_sql_count]개
   ❌ 오류 구문: [error_sql_count]개
   ⚠️  경고 사항: [warning_count]개

❌ 발견된 주요 오류:
   1. [SQL_ID_1]: [error_description_1]
   2. [SQL_ID_2]: [error_description_2]
   [... 최대 5개까지 표시]

🔧 수정 필요 사항:
   - 구문 오류: [syntax_error_count]개
   - 함수 변환: [function_error_count]개
   - 데이터 타입: [datatype_error_count]개

================================
이 파일을 수정하시겠습니까? (y/n/s/d/q)
y: 예, 수정 진행
n: 아니오, 건너뛰고 다음 파일로
s: 건너뛰기 (나중에 수정)
d: 상세 오류 내용 표시
q: 전체 검증 중단
================================
```

**STOP HERE - WAIT FOR USER DECISION (오류 발견 시에만)**

시스템은 오류가 발견된 파일에 대해서만 사용자 결정을 기다립니다.

### 2. 오류 상세 분석 및 수정 계획 수립

**2.1 OriginXML과의 비교 분석**:
```
================================
상세 오류 분석 및 수정 계획 ($TARGET_DBMS_TYPE 전문가)
================================

📁 분석 대상: [transform_xml_filename]
📄 원본 참조: [origin_xml_filename]

🔍 오류 #1 상세 분석:
   📋 SQL ID: [sql_id]
   ❌ 오류 내용: [detailed_error_description]
   📍 오류 위치: [line_number]행, [column_number]열

   📄 OriginXML ($SOURCE_DBMS_TYPE):
   ```sql
   [original_sql_snippet]
   ```

   🎯 TransformXML ($TARGET_DBMS_TYPE):
   ```sql
   [transformed_sql_snippet]
   ```

   🔍 $TARGET_DBMS_TYPE 전문가 분석:
   - 변환 오류 원인: [root_cause_analysis]
   - $TARGET_DBMS_TYPE 제약사항: [target_constraints]
   - 호환성 문제: [compatibility_issues]

   🔧 수정 제안:
   ```sql
   [proposed_corrected_sql]
   ```

   📈 수정 근거:
   - [justification_1]
   - [justification_2]
   - [performance_impact]

   ⚠️  수정 시 고려사항:
   - [consideration_1]
   - [consideration_2]

================================
[다음 오류들도 동일한 형식으로 표시...]
================================

전체 수정 계획 요약:
📊 수정 대상: [total_errors]개 오류
🔧 수정 유형: 
   - 구문 오류: [syntax_error_count]개
   - 함수 변환: [function_error_count]개
   - 데이터 타입: [datatype_error_count]개
   - 기타: [other_error_count]개

⏱️  예상 수정 시간: [estimated_time]
🎯 수정 후 $TARGET_DBMS_TYPE 호환성: [expected_compatibility_level]

================================
이 수정 계획을 승인하시겠습니까? (y/n/m/q)
y: 승인하고 수정 실행
n: 수정 계획 재검토
m: 개별 오류별 승인
q: 취소하고 다음 파일로
================================
```

**STOP HERE - WAIT FOR USER APPROVAL**

시스템은 사용자의 승인을 기다려야 합니다.

### 3. 백업 및 수정 실행

**3.1 백업 생성**:
```
================================
백업 및 수정 실행
================================

📁 대상 파일: [transform_xml_filename]
💾 백업 생성 중...

✅ 백업 완료: [transform_xml_filename].xml.202507301200
📍 백업 위치: [full_backup_path]

🔧 수정 실행 중:
   ✅ 오류 #1 수정 완료: [sql_id_1]
   ✅ 오류 #2 수정 완료: [sql_id_2]
   🔄 오류 #3 수정 중: [sql_id_3]...
   ✅ 모든 오류 수정 완료

🔍 수정 후 검증:
   ✅ XML 형식 유효성 확인
   ✅ SQL 구문 검증 완료
   ✅ $TARGET_DBMS_TYPE 호환성 확인

📊 수정 결과:
   - 수정된 SQL 구문: [corrected_sql_count]개
   - 제거된 오류: [fixed_error_count]개
   - 남은 경고: [remaining_warning_count]개

✅ 수정 완료! 다음 파일로 자동 진행합니다...

================================

### 4. 전체 검증 완료 및 보고서 생성

모든 파일 검증 완료 후:

```
================================
전체 TransformXML 검증 완료 보고서
================================

📊 검증 통계:
   - 총 검증 파일: [total_files]개
   - 수정된 파일: [modified_files]개
   - 오류 없는 파일: [clean_files]개
   - 건너뛴 파일: [skipped_files]개

🔧 수정 통계:
   - 총 수정된 오류: [total_fixed_errors]개
   - 구문 오류 수정: [syntax_fixes]개
   - 함수 변환 수정: [function_fixes]개
   - 데이터 타입 수정: [datatype_fixes]개

💾 백업 파일:
   [backup_file_list]

📁 수정 로그: $APP_LOGS_FOLDER/TransformXML_Validation_Log_20250730_020000.txt

🎯 $TARGET_DBMS_TYPE 호환성 개선:
   - 수정 전 호환성: [before_compatibility]%
   - 수정 후 호환성: [after_compatibility]%
   - 개선도: [improvement_percentage]%

⚠️  추가 권장사항:
   - [recommendation_1]
   - [recommendation_2]
   - [recommendation_3]

================================
검증 및 수정 작업이 완료되었습니다.
모든 변경사항이 로그에 기록되었습니다.

추가 작업이 필요하시면 언제든지 다시 실행하세요.
================================
```

## 중요 규칙 및 제약사항

### 1. 개별 파일 처리 원칙
- **패턴 방식 일괄 수정 절대 금지**
- 각 XML 파일은 개별적으로 분석하고 수정
- 파일별로 고유한 SQL 구문과 컨텍스트 고려
- 사용자 승인 없이는 어떤 수정도 실행하지 않음

### 2. 안전성 보장
- 모든 수정 전 백업 파일 생성 필수
- 백업 파일명: `[원본파일명].xml.YYYYMMDDHHMM`
- 임시 작업 파일은 `/tmp` 디렉토리 사용
- 오류 발생 시 자동 롤백 기능

### 3. $TARGET_DBMS_TYPE 전문가 관점
- $TARGET_DBMS_TYPE 특화 구문 및 함수 활용
- 성능 최적화 고려
- 호환성 및 제약사항 준수
- 모범 사례 적용

### 4. 사용자 상호작용
- 시작 시 전체 파일 목록 확인 필수
- 오류 발견 시에만 사용자 확인 필요
- 정상 파일은 자동으로 다음 파일 진행
- 명확한 선택지 제공 (y/n/s/q 등)
- 상세 정보 요청 시 추가 정보 제공
- 언제든지 중단 가능

### 5. 로깅 및 문서화
- 모든 변경사항을 상세 로그에 기록
- 수정 전후 SQL 구문 비교 포함
- 백업 파일 위치 추적
- 다음 검증을 위한 기준 정보 제공

## 오류 처리 및 복구

### 임시 파일 관리
- **위치**: `/tmp/transformxml_validation_[timestamp]/`
- **파일 유형**:
  - 분석 결과: `analysis_[filename]_[timestamp].txt`
  - 작업 사본: `work_[filename]_[timestamp].xml`
  - 차이점 미리보기: `diff_[filename]_[timestamp].txt`
- **정리**: 완료 또는 취소 시 임시 파일 제거

### 검증 단계
1. XML 구조 유효성 검사
2. SQL 구문 문법 검증
3. $TARGET_DBMS_TYPE 호환성 확인
4. 성능 영향 평가

### 복구 절차
1. 백업 파일을 이용한 자동 복원
2. 부분 롤백 지원
3. 수동 복구를 위한 상세 로그

이 프롬프트는 TransformXML 파일들의 문법적 완결성을 체계적으로 검증하고, 필요시 안전하게 수정하는 전체 프로세스를 다룹니다. 각 단계에서 사용자의 명시적 승인을 받으며, $TARGET_DBMS_TYPE 전문가 관점에서 최적의 수정 방안을 제시합니다.
