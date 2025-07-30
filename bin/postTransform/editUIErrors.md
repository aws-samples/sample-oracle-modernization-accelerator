# Application UI Test 오류 기반 SQL 변환 수정

Reference: Apply environment information from $APP_TOOLS_FOLDER/environmentContext.md

**Language Instruction**: All messages, prompts, and user interactions must be displayed in Korean.(한글)

**IMPORTANT**: This process requires interactive user input. The system MUST pause and wait for user input at designated points. Do not skip or auto-fill any user input sections.

[$TARGET_DBMS_TYPE Expert Mode]
**목표**: Application UI Test에서 수행된 결과 중에서 오류를 기반으로 SQL 변환 수정을 수행

**전문가 모드 설정**: 
- $SOURCE_DBMS_TYPE에서 $TARGET_DBMS_TYPE로의 SQL 변환 전문 지식 활용
- $TARGET_DBMS_TYPE 특화 구문, 함수, 데이터 타입에 대한 깊은 이해
- $TARGET_DBMS_TYPE 성능 최적화 및 모범 사례 적용
- $TARGET_DBMS_TYPE 호환성 및 제약사항 고려

## 수정 접근 방법

### 1. TransformXML과 SourceXML의 전환 완정성 검토
- **SourceXML**: $SOURCE_DBMS_TYPE SQL이 포함된 원본 XML 파일
- **TransformXML**: SourceXML을 $TARGET_DBMS_TYPE SQL로 변환한 XML 파일
- **오류 정보**: SQLID와 SQL Error Message를 포함
- **파일 위치**:
  - TransformXML: `$APP_LOGS_FOLDER/mapper/*/transform/*.xml` (파일명에 SQLID 포함)
  - SourceXML: `$APP_LOGS_FOLDER/mapper/*/extract/*.xml` (파일명에 SQLID 포함)

### 2. 오류 분석 및 수정 절차
1. 사용자로부터 오류 정보 텍스트를 일괄 입력 받기
2. 텍스트에서 SQLID와 SQL Error Message 자동 추출
3. 해당 SQLID의 TransformXML과 SourceXML 파일 식별
4. 오류 원인 분석 및 수정 방안 제시
5. 사용자 승인 후 TransformXML 수정 실행
6. 백업 파일 생성 (기존 파일명 + 날짜시간)

### 3. 자동 파싱 가이드라인
**SQLID 추출 패턴**:
- "SQLID:" 또는 "SQL ID:" 다음에 오는 문자열
- 파일명 패턴과 일치하는 문자열 (예: USER_SELECT_001, PRODUCT_INSERT_002)
- 대문자와 언더스코어로 구성된 식별자 패턴

**Error Message 추출 패턴**:
- "Error:" 또는 "ERROR:" 다음에 오는 문자열
- 데이터베이스 오류 코드 패턴 (ORA-, SQL-, ERROR 등으로 시작)
- 오류 메시지로 보이는 긴 텍스트 블록

**추출 우선순위**:
1. 명시적 라벨이 있는 경우 (SQLID:, Error: 등)
2. 패턴 매칭을 통한 자동 인식
3. 사용자 확인을 통한 검증

## Task Instructions

### 0. 오류 정보 일괄 입력
**Interactive Error Information Batch Input**

**MANDATORY USER INTERACTION REQUIRED**
The following steps require user input. The system must pause and wait for user responses.

1. **Display Current Setting**:
   ```
   ================================
   SQL 변환 오류 수정 시스템
   ================================
   
   Application UI Test에서 발생한 SQL 오류를 기반으로 
   TransformXML 파일을 수정합니다.
   
   입력 방법:
   - 오류 로그나 테스트 결과에서 관련 텍스트를 복사하여 붙여넣기
   - SQLID와 Error Message가 포함된 텍스트면 자동으로 추출됩니다
   - 구분자나 특별한 형식은 필요하지 않습니다
   
   파일 위치:
   - TransformXML: $APP_LOGS_FOLDER/mapper/*/transform/*.xml
   - SourceXML: $APP_LOGS_FOLDER/mapper/*/extract/*.xml
   
   ================================
   ```

2. **오류 정보 일괄 입력**:
   ```
   오류 정보를 입력하세요 (SQLID와 Error Message가 포함된 텍스트를 복사하여 붙여넣기):
   
   예시:
   SQLID: USER_SELECT_001
   Error: ORA-00904: "INVALID_COLUMN": invalid identifier
   
   또는 단순히:
   USER_SELECT_001 ORA-00904: "INVALID_COLUMN": invalid identifier
   
   > 
   ```
   
   **STOP HERE - WAIT FOR USER INPUT**
   
   The system must pause at this point and wait for the user to enter the error information.
   Do not proceed to the next step until the user provides input.
   
   Expected user input format: [텍스트에서 SQLID와 Error Message 자동 추출]

3. **입력 정보 자동 파싱 및 확인**:
   ```
   ================================
   입력된 오류 정보 자동 분석
   ================================
   
   📥 입력된 텍스트: [user_input_text]
   
   🔍 자동 추출 결과:
   📋 SQLID: [extracted_sqlid]
   ❌ Error Message: [extracted_error_message]
   
   추출 결과가 정확합니까? (y/n/m/c)
   y: 예, 분석 시작
   n: 아니오, 다시 입력
   m: 수동으로 SQLID와 Error Message 수정
   c: 취소
   ================================
   ```
   
   **STOP HERE - WAIT FOR USER CONFIRMATION**
   
   The system must pause and wait for user to enter y, n, m, or c.
   Do not proceed until user provides confirmation.

4. **수동 수정 모드 (m 선택 시)**:
   ```
   ================================
   수동 수정 모드
   ================================
   
   현재 추출된 정보:
   📋 SQLID: [extracted_sqlid]
   ❌ Error Message: [extracted_error_message]
   
   수정할 항목을 선택하세요:
   1: SQLID 수정
   2: Error Message 수정
   3: 둘 다 수정
   4: 수정 완료, 분석 시작
   > 
   ```
   
   **STOP HERE - WAIT FOR USER SELECTION**
   
   사용자가 1, 2, 3을 선택하면 해당 항목을 다시 입력받고,
   4를 선택하면 분석을 시작합니다.

### 1. 파일 식별 및 오류 분석 단계
- 입력받은 SQLID를 기반으로 해당하는 TransformXML과 SourceXML 파일을 식별
- 오류 메시지를 분석하여 변환 과정에서 발생한 문제점 파악

**파일 식별 결과 표시**:
```
================================
SQL 파일 식별 결과
================================

📋 SQLID: [user_entered_sqlid]
❌ Error Message: [user_entered_error_message]

📁 식별된 파일:
   🎯 TransformXML: [transform_xml_path]
   📄 SourceXML: [source_xml_path]

🔍 파일 존재 여부:
   - TransformXML: [존재함/존재하지 않음]
   - SourceXML: [존재함/존재하지 않음]

📊 오류 분석 결과:
   - 오류 유형: [error_type]
   - 예상 원인: [suspected_cause]
   - 영향 범위: [impact_scope]

================================
파일 분석을 계속 진행하시겠습니까? (y/n/q)
y: 예, 상세 분석 진행
n: 아니오, 다른 SQLID 입력
q: 종료
================================
```

**STOP HERE - WAIT FOR USER DECISION**

The system must pause and wait for user to enter y, n, or q.
Do not proceed until user provides their choice.

### 2. 상세 분석 및 수정 계획 ($TARGET_DBMS_TYPE 전문가 관점)
- SourceXML과 TransformXML의 내용을 비교 분석
- 오류 메시지를 기반으로 변환 과정에서의 문제점 식별
- $SOURCE_DBMS_TYPE에서 $TARGET_DBMS_TYPE로의 변환 오류 원인 파악
- $TARGET_DBMS_TYPE 특화 구문 및 최적화 방안 제시
- $TARGET_DBMS_TYPE 성능 및 호환성 고려사항 검토

**상세 분석 결과 표시**:
```
================================
상세 분석 및 수정 계획 ($TARGET_DBMS_TYPE 전문가 분석)
================================

📋 SQLID: [sqlid]
📄 파일 정보:
   - SourceXML: [source_xml_path]
   - TransformXML: [transform_xml_path]

🔍 SourceXML 내용 분석:
   - SQL 유형: [sql_type] (SELECT/INSERT/UPDATE/DELETE/DDL)
   - $SOURCE_DBMS_TYPE 특화 구문: [source_specific_syntax]
   - 주요 함수/구문: [key_functions]
   - 데이터 타입: [source_data_types]

🎯 TransformXML 내용 분석:
   - 변환된 SQL: [transformed_sql_preview]
   - $TARGET_DBMS_TYPE 구문 적용: [target_syntax_applied]
   - 변환 상태: [conversion_status]
   - $TARGET_DBMS_TYPE 호환성: [compatibility_status]

❌ 오류 분석 ($TARGET_DBMS_TYPE 관점):
   - 오류 메시지: [error_message]
   - 오류 위치: [error_location_in_sql]
   - 오류 원인: [root_cause_analysis]
   - $TARGET_DBMS_TYPE 제약사항: [target_constraints]
   - 변환 실패 요소: [failed_conversion_elements]

🔧 $TARGET_DBMS_TYPE 전문가 수정 제안:
   1. [구체적_수정사항_1_with_before_after_sql]
   2. [구체적_수정사항_2_with_before_after_sql]
   3. [추가_수정사항들...]

📈 $TARGET_DBMS_TYPE 최적화 제안:
   - 성능 개선: [performance_optimization_suggestions]
   - 구문 최적화: [syntax_optimization]
   - 인덱스 활용: [index_usage_recommendations]

⚠️  $TARGET_DBMS_TYPE 수정 시 고려사항:
   - 데이터 타입 호환성: [data_type_compatibility]
   - 함수 매핑 정확성: [function_mapping_accuracy]
   - 성능 영향: [performance_impact]
   - 제약조건 준수: [constraint_compliance]
   - 트랜잭션 처리: [transaction_handling]

🔍 검증 계획:
   - 구문 검증: [syntax_validation_plan]
   - 기능 검증: [functional_validation_plan]
   - 성능 검증: [performance_validation_plan]

================================
이 수정 계획을 승인하시겠습니까? (y/n/s/q)
y: 승인하고 수정 진행
n: 수정 계획 재검토
s: 상세 내용 표시
q: 종료
================================
```

**STOP HERE - WAIT FOR USER APPROVAL**

The system must pause and wait for user to enter y, n, s, or q.
Do not proceed until user provides their decision.

**임시 파일 관리**:
- **모든 임시 작업 파일은 /tmp 디렉토리에 생성**
- 명명 규칙: `/tmp/sql_transform_fix_[timestamp]_[purpose].[extension]`
- 예시:
  - `/tmp/sql_transform_fix_20250730_020000_analysis.txt` - 분석 결과
  - `/tmp/sql_transform_fix_20250730_020000_backup_list.txt` - 백업 파일 추적
  - `/tmp/sql_transform_fix_20250730_020000_changes.log` - 임시 변경 로그
  - `/tmp/sql_transform_fix_20250730_020000_diff.txt` - 코드 차이점 미리보기
- 성공적인 완료 또는 사용자 취소 시 임시 파일 정리

### 3. 백업 및 수정 실행
- 사용자 승인 후 수정 작업 실행
- TransformXML 파일의 백업 생성 (기존 파일명 + 날짜시간)
- 승인된 수정 사항을 TransformXML 파일에 적용
- 적절한 오류 처리 및 검증 수행

**백업 및 수정 실행 과정**:
```
================================
백업 및 수정 실행
================================

📁 대상 파일: [transform_xml_path]
💾 백업 파일: [transform_xml_path]_backup_YYYYMMDD_HHMMSS.xml

🔄 수정 진행 상황:
   ✅ 백업 파일 생성 완료
   🔧 TransformXML 수정 중...
   ✅ 수정 완료
   🔍 검증 중...
   ✅ 검증 완료

📊 수정 결과:
   - 수정된 요소: [modified_elements]
   - 변경된 SQL 구문: [changed_sql_parts]
   - 검증 상태: [validation_status]

================================
수정이 완료되었습니다. 다른 오류를 수정하시겠습니까? (y/n)
y: 예, 다른 오류 입력
n: 아니오, 종료
================================
```

**STOP HERE - WAIT FOR USER DECISION**

The system must pause and wait for user to enter y or n.
If user enters 'y', return to step 0 for next error input.
If user enters 'n', proceed to step 4.

### 4. 문서화 및 로깅
- 모든 변경 사항을 $APP_TRANSFORM_FOLDER/EditUIErrors.log에 기록
- 수정 전후의 SQL 구문 스니펫 포함
- 수동 개입이 필요한 사항 문서화
- 다음 오류 처리를 위한 시스템 준비

## 수정 승인 요청 템플릿

```
================================
TransformXML 수정 승인 요청 ($TARGET_DBMS_TYPE 전문가 분석)
================================

📋 SQLID: [sqlid]
📁 대상 파일: [transform_xml_path]
📄 파일 유형: TransformXML (.xml)
🔍 감지된 오류: [error_type] ([error_description])
📊 복잡도: [Low/Medium/High]
🎯 $TARGET_DBMS_TYPE 호환성: [compatibility_level]

❌ 식별된 $SOURCE_DBMS_TYPE → $TARGET_DBMS_TYPE 변환 문제점:
   - [specific_sql_issue_1_with_dbms_context]
   - [specific_sql_issue_2_with_dbms_context]
   - [additional_issues_with_target_impact...]

🔧 $TARGET_DBMS_TYPE 전문가 수정 제안:
   BEFORE ($SOURCE_DBMS_TYPE): [original_sql_snippet]
   AFTER ($TARGET_DBMS_TYPE):  [proposed_sql_snippet]
   
   - [specific_change_1_with_target_optimization]
   - [specific_change_2_with_target_best_practices]
   - [additional_changes_with_performance_consideration...]

📈 $TARGET_DBMS_TYPE 변환 품질: [current_state] → [expected_post_fix_state]

📊 $TARGET_DBMS_TYPE 영향 평가:
   - 기능적 영향: [functional_impact_in_target_context]
   - 성능 영향: [target_performance_optimization]
   - $TARGET_DBMS_TYPE 호환성: [target_compatibility_improvements]
   - $TARGET_DBMS_TYPE 특화 기능 활용: [target_specific_features_used]
   - 테스트 요구사항: [target_specific_testing_approach]

⚠️  $TARGET_DBMS_TYPE 관련 경고 및 고려사항:
   - $TARGET_DBMS_TYPE 제약사항: [target_constraints_and_limitations]
   - 수동 검증 필요: [manual_verification_for_target]
   - 추가 $TARGET_DBMS_TYPE 의존성: [additional_target_dependencies]
   - 성능 모니터링: [performance_monitoring_recommendations]

🔄 롤백 계획:
   - 백업 위치: [transform_xml_path]_backup_YYYYMMDD_HHMMSS.xml
   - 작업 사본: /tmp/sql_transform_work_[sqlid]_[timestamp].xml
   - 차이점 미리보기: /tmp/sql_transform_diff_[sqlid]_[timestamp].txt
   - 롤백 절차: [steps_to_revert_changes]

================================

수정을 진행하시겠습니까? (y/n/s/q/d)
y: 승인하고 다음 파일로 계속
n: 이 파일을 건너뛰고 계속
s: 남은 모든 수정 사항 자동 승인
q: 수정 프로세스 종료
d: 상세 차이점 미리보기 표시 (/tmp/sql_transform_diff_[sqlid]_[timestamp].txt에 저장)
```

**STOP HERE - WAIT FOR USER APPROVAL**

The system must pause and wait for user to enter y, n, s, q, or d.
Each file modification requires explicit user approval.
Do not proceed until user provides their decision.

## 핵심 원칙

### 1. 개별 오류 평가
- **일괄 패턴 교체 금지**: 각 오류는 개별적으로 분석되어야 함
- **컨텍스트 인식 수정**: 특정 사용 사례와 주변 SQL 구문을 고려
- **의미 보존**: $TARGET_DBMS_TYPE 호환성을 확보하면서 원본 기능 유지

### 2. 안전성 및 신뢰성
- **필수 백업**: 원본 파일과 동일한 디렉토리에 타임스탬프가 포함된 백업 생성: [filename]_backup_YYYYMMDD_HHMMSS.[extension]
  - 예시: `transform_user_001.xml` → `transform_user_001_backup_20250730_020000.xml`
- **임시 작업 파일**: 모든 중간 처리 파일은 `/tmp` 디렉토리에 생성
  - 분석용 작업 사본: `/tmp/sql_transform_[sqlid]_work_[timestamp].xml`
  - 미리보기용 차이점 파일: `/tmp/sql_transform_[sqlid]_diff_[timestamp].txt`
  - 검증 결과: `/tmp/sql_transform_validation_[timestamp].log`
- **점진적 변경**: 한 번에 하나의 오류씩 검증과 함께 변경 적용
- **롤백 기능**: 문제 발생 시 변경 사항을 되돌릴 수 있는 능력 유지
- **정리**: 완료 또는 취소 시 `/tmp`의 모든 임시 파일 제거

### 3. 품질 보증
- **코드 검토**: 명확한 수정 전후 비교 제시
- **테스트 권장사항**: 적절한 테스트 전략 제안
- **문서화**: 포괄적인 변경 로그 유지

### 4. 대상 데이터베이스 호환성
- **표준 준수**: 가능한 경우 ANSI SQL 및 표준 구문 선호
- **대상별 최적화**: 유익한 경우 $TARGET_DBMS_TYPE 특화 기능 사용
- **성능 고려**: 변환된 SQL이 성능을 유지하거나 개선하도록 보장

## 일반적인 $SOURCE_DBMS_TYPE → $TARGET_DBMS_TYPE 변환 오류 유형

### 1. 데이터 타입 변환 오류
- **VARCHAR2/NVARCHAR2** → $TARGET_DBMS_TYPE 문자열 타입
- **NUMBER** → $TARGET_DBMS_TYPE 숫자 타입 (DECIMAL, NUMERIC 등)
- **DATE/TIMESTAMP** → $TARGET_DBMS_TYPE 날짜/시간 타입
- **CLOB/BLOB** → $TARGET_DBMS_TYPE 대용량 데이터 타입
- **ROWID** → $TARGET_DBMS_TYPE 행 식별자 대체

### 2. 함수 변환 오류
- **NVL/NVL2** → $TARGET_DBMS_TYPE NULL 처리 함수 (ISNULL, COALESCE 등)
- **DECODE** → $TARGET_DBMS_TYPE CASE 구문 또는 조건 함수
- **TO_CHAR/TO_DATE/TO_NUMBER** → $TARGET_DBMS_TYPE 형변환 함수
- **SUBSTR** → $TARGET_DBMS_TYPE 문자열 추출 함수 (SUBSTRING 등)
- **INSTR** → $TARGET_DBMS_TYPE 문자열 검색 함수 (CHARINDEX, POSITION 등)
- **LENGTH** → $TARGET_DBMS_TYPE 문자열 길이 함수 (LEN 등)

### 3. 구문 변환 오류
- **ROWNUM** → $TARGET_DBMS_TYPE 페이징 구문 (LIMIT, TOP, ROW_NUMBER 등)
- **CONNECT BY** → $TARGET_DBMS_TYPE 계층적 쿼리 (CTE, 재귀 쿼리 등)
- **DUAL 테이블** → $TARGET_DBMS_TYPE 더미 테이블 또는 VALUES 구문
- **MERGE 구문** → $TARGET_DBMS_TYPE UPSERT 구문
- **OUTER JOIN (+)** → $TARGET_DBMS_TYPE 표준 OUTER JOIN 구문

### 4. 시퀀스 및 자동 증가
- **SEQUENCE.NEXTVAL** → $TARGET_DBMS_TYPE 자동 증가 컬럼 (IDENTITY, AUTO_INCREMENT 등)
- **시퀀스 생성 구문** → $TARGET_DBMS_TYPE 시퀀스 또는 자동 증가 설정

### 5. 날짜/시간 처리 오류
- **SYSDATE** → $TARGET_DBMS_TYPE 현재 날짜/시간 함수
- **ADD_MONTHS** → $TARGET_DBMS_TYPE 날짜 연산 함수
- **TRUNC(날짜)** → $TARGET_DBMS_TYPE 날짜 절삭 함수
- **EXTRACT** → $TARGET_DBMS_TYPE 날짜 부분 추출 함수

### 6. 집계 및 분석 함수
- **LISTAGG** → $TARGET_DBMS_TYPE 문자열 집계 함수
- **RANK/DENSE_RANK** → $TARGET_DBMS_TYPE 순위 함수 호환성
- **LAG/LEAD** → $TARGET_DBMS_TYPE 윈도우 함수 호환성

### 성능 최적화
- 힌트 구문 차이
- 실행 계획 관련 구문
- 통계 정보 수집 방법

## 오류 처리 및 복구

### 임시 파일 관리
- **위치**: 모든 임시 파일은 `/tmp` 디렉토리에 생성
- **명명 규칙**: `/tmp/sql_transform_fix_[component]_[timestamp].[ext]`
- **정리 정책**: 
  - 성공적인 완료 시 임시 파일 제거
  - 사용자 취소 시 임시 파일 제거
  - 중요한 오류 발생 시에만 디버깅을 위해 임시 파일 보존
- **파일 유형**:
  - 분석 파일: `/tmp/sql_transform_analysis_[timestamp].txt`
  - 작업 사본: `/tmp/sql_transform_work_[sqlid]_[timestamp].xml`
  - 차이점 미리보기: `/tmp/sql_transform_diff_[sqlid]_[timestamp].txt`
  - 오류 로그: `/tmp/sql_transform_error_[timestamp].log`

### 검증 단계
1. 각 변경 후 XML 구문 검증
2. SQL 구문 유효성 확인
3. 기본 기능 테스트 권장사항

### 복구 절차
1. 중요한 오류 발생 시 자동 백업 복원
2. 부분 롤백 기능
3. 수동 복구를 위한 변경 로그

## 로깅 형식

EditUIErrors.log의 각 항목은 다음을 포함해야 함:
```
[TIMESTAMP] [SQLID] [TRANSFORM_XML_PATH] [CHANGE_TYPE] [STATUS]
ERROR_MESSAGE: [original_error_message]
BEFORE_SQL: [original_sql_snippet]
AFTER_SQL:  [modified_sql_snippet]
REASON: [explanation_of_change]
IMPACT: [assessment_of_change_impact]
BACKUP_FILE: [backup_file_path]
---
```

## 반복 처리 지원

이 프롬프트는 하나의 오류 수정이 완료된 후, 사용자가 다른 오류를 입력하여 같은 절차로 수행할 수 있도록 설계되었습니다. 각 수정 완료 후 시스템은 다음 오류 입력을 위해 0단계로 돌아갑니다.
