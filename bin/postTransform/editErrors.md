
# SQL Test 오류 기반 SQL 변환 수정

Reference: Apply environment information from $APP_TOOLS_FOLDER/environmentContext.md

**IMPORTANT**: This process requires interactive user input. The system MUST pause and wait for user input at designated points. Do not skip or auto-fill any user input sections.

[$TARGET_DBMS_TYPE Expert Mode]
**목표**: 전체 SQL Test를 수행해고 수행된 결과 중에서 오류를 기반으로 SQL 변환 수정을 수행

**전문가 모드 설정**: 
- $SOURCE_DBMS_TYPE에서 $TARGET_DBMS_TYPE로의 SQL 변환 전문 지식 활용
- $TARGET_DBMS_TYPE , 함수, 데이터 타입에 대한 깊은 이해

---

## 1단계: SQL 테스트 실행

**MANDATORY USER INTERACTION REQUIRED**

1. **Display Current Setting**:
   ```
   ================================
   SQL 변환 오류 수정 시스템
   ================================
   
   SQL Test 결과를 기반으로 TransformXML 파일을 수정합니다.
   
   테스트 실행 명령어:
   cd $APP_TOOLS_FOLDER/../test && java -cp ".:lib/*" com.test.mybatis.MyBatisBulkExecutorWithJson $APP_LOGS_FOLDER/mapper --db $TARGET_DBMS_TYPE --include transform --json-file oma_test_result.json
   
   결과 파일: $APP_TOOLS_FOLDER/../test/out/oma_test_result.json
   ================================
   ```

2. **테스트 실행 확인**:
   ```
   SQL Test를 실행하시겠습니까? (y/s/q)
   y: 예, 테스트 실행
   s: 건너뛰기 (이미 실행됨)
   q: 종료
   > 
   ```
   
   **STOP HERE - WAIT FOR USER INPUT**
   
   The system must pause and wait for user to enter y, s, or q.

다음 명령어로 변환된 SQL에 대한 테스트를 수행합니다:

```bash
cd $APP_TOOLS_FOLDER/../test && java -cp ".:lib/*" com.test.mybatis.MyBatisBulkExecutorWithJson $APP_LOGS_FOLDER/mapper --db $TARGET_DBMS_TYPE --include transform --json-file oma_test_result.json
```

**테스트 결과 파일**: `$APP_TOOLS_FOLDER/../test/out/oma_test_result.json`

---

## 2단계: 오류 분석 및 수정

### 2.1 오류 식별
- 테스트 결과 JSON 파일에서 오류가 발생한 항목들을 식별
- 각 오류에 대해 다음 정보 추출:
  - XML 파일명
  - SQL ID
  - 오류 메시지
  - 오류 유형 (구문 오류, 함수 호환성, 데이터 타입 등)

### 2.2 관련 파일 위치 확인
- **원본 XML** ($SOURCE_DBMS_TYPE): `$APP_LOGS_FOLDER/mapper/**/extract/*.xml`
- **변환된 XML** ($TARGET_DBMS_TYPE): `$APP_LOGS_FOLDER/mapper/**/transform/*.xml`

### 2.3 오류 분석 프로세스
각 오류에 대해 다음 단계를 수행:

1. **오류 원인 분석**
   - 원본 SQL과 변환된 SQL 비교
   - $SOURCE_DBMS_TYPE와 $TARGET_DBMS_TYPE 간의 문법 차이점 식별
   - 오류 메시지 기반 구체적 문제점 파악

2. **수정 방안 제시**
   - 구체적인 수정 내용 설명
   - 수정 전후 SQL 비교
   - 수정이 다른 부분에 미칠 영향 검토

3. **사용자 승인 요청**
   - 제안된 수정 사항을 사용자에게 명확히 설명
   - 사용자 승인 후에만 수정 진행
   - 승인되지 않은 경우 대안 제시

**오류 분석 결과 표시**:
```
================================
오류 분석 및 수정 계획 ($TARGET_DBMS_TYPE 전문가 분석)
================================

📋 SQLID: [sqlid]
📄 파일 정보:
   - SourceXML: [source_xml_path]
   - TransformXML: [transform_xml_path]

❌ 오류 분석:
   - 오류 메시지: [error_message]
   - 오류 원인: [root_cause_analysis]
   - $TARGET_DBMS_TYPE 제약사항: [target_constraints]

🔧 수정 제안:
   BEFORE: [original_sql_snippet]
   AFTER:  [proposed_sql_snippet]
   
   수정 내용: [specific_changes]

⚠️  수정 시 고려사항:
   - 영향 범위: [impact_scope]
   - 성능 영향: [performance_impact]
   - 검증 필요사항: [validation_requirements]

================================
이 수정을 승인하시겠습니까? (y/n/s/q)
y: 승인하고 수정 진행
n: 이 오류 건너뛰기
s: 모든 수정 자동 승인
q: 종료
================================
```

**STOP HERE - WAIT FOR USER APPROVAL**

The system must pause and wait for user to enter y, n, s, or q.
Each modification requires explicit user approval.

4. **수정 실행**
   - 변환된 XML 파일 백업 생성 (파일명.xml.YYYYMMDD_HHMMSS)
   - 승인된 수정 사항 적용
   - 수정 완료 확인

**수정 실행 과정**:
```
================================
수정 실행 중
================================

📁 대상 파일: [transform_xml_path]
💾 백업 파일: [transform_xml_path].xml.YYYYMMDDHHMM

🔄 진행 상황:
   ✅ 백업 파일 생성 완료
   🔧 TransformXML 수정 중...
   ✅ 수정 완료
   🔍 검증 완료

================================
```

---

## 3단계: 수정 후 검증 및 테스트

### 3.1 개별 파일 테스트
수정한 각 파일에 대해 개별 테스트를 수행하여 수정 사항이 올바르게 적용되었는지 확인:

**개별 파일 테스트 명령어**:
```bash
cd $APP_TOOLS_FOLDER/../test && java -cp ".:lib/*" com.test.mybatis.MyBatisBulkExecutorWithJson [수정한_파일명] --db $TARGET_DBMS_TYPE 
```

**개별 테스트 확인**:
```
================================
수정 파일 개별 테스트
================================

📄 수정된 파일: [modified_file_name]
🧪 테스트 명령어: 
   cd $APP_TOOLS_FOLDER/../test && java -cp ".:lib/*" com.test.mybatis.MyBatisBulkExecutorWithJson [수정한_파일명] --db $TARGET_DBMS_TYPE 

개별 테스트를 실행하시겠습니까? (y/n/s)
y: 예, 개별 테스트 실행
n: 건너뛰기
s: 전체 테스트로 바로 이동
> 
```

**STOP HERE - WAIT FOR USER INPUT**

### 3.2 전체 재테스트
- 모든 수정 완료 후 1단계 전체 테스트 재실행
- 새로운 오류 발생 여부 및 기존 오류 해결 여부 확인
- 수정으로 인한 부작용(side effect) 검증

**전체 재테스트 명령어**:
```bash
cd $APP_TOOLS_FOLDER/../test && java -cp ".:lib/*" com.test.mybatis.MyBatisBulkExecutorWithJson $APP_LOGS_FOLDER/mapper --db $TARGET_DBMS_TYPE --include transform --json-file oma_test_result_after_fix.json
```

### 3.3 결과 비교 및 분석
- 수정 전후 테스트 결과 비교
- 해결된 오류 수 확인
- 새로 발생한 오류 식별
- 전체적인 개선 상황 평가

**결과 비교 표시**:
```
================================
수정 전후 결과 비교
================================

📊 테스트 결과 요약:
   수정 전 오류: [before_error_count]개
   수정 후 오류: [after_error_count]개
   해결된 오류: [resolved_count]개
   새로 발생한 오류: [new_error_count]개

✅ 해결된 오류 목록:
   - [resolved_error_1]
   - [resolved_error_2]
   ...

❌ 남은 오류 목록:
   - [remaining_error_1]
   - [remaining_error_2]
   ...

⚠️  새로 발생한 오류:
   - [new_error_1]
   - [new_error_2]
   ...

================================
```

### 3.4 수렴 조건 및 반복 결정
- 모든 SQL 오류가 해결될 때까지 2-3단계 반복
- 각 반복에서 진행 상황 리포트 제공
- 해결 불가능한 오류의 경우 사용자에게 보고 및 대안 제시

**반복 확인**:
```
================================
다음 단계 선택
================================

현재까지 수정 완료: [completed_count]개
남은 오류: [remaining_count]개
개선율: [improvement_rate]%

다음 작업을 선택하세요:
1: 남은 오류 수정 계속
2: 새로 발생한 오류 우선 수정
3: 개별 파일 재테스트
4: 전체 테스트 재실행
5: 수정 완료 및 종료
> 
```

**STOP HERE - WAIT FOR USER DECISION**

The system must pause and wait for user selection.
Continue until all errors are resolved or user chooses to exit.

---

## 주의사항

- **백업 필수**: 모든 수정 전에 원본 파일 백업
- **점진적 수정**: 한 번에 여러 오류를 수정하지 말고 하나씩 처리
- **개별 검증**: 각 파일 수정 후 개별 테스트로 즉시 검증
- **전체 검증**: 여러 파일 수정 후 전체 테스트로 종합 검증
- **부작용 확인**: 수정으로 인한 새로운 오류 발생 여부 모니터링
- **문서화**: 수정 내용과 이유를 명확히 기록
- **사용자 확인**: 모든 수정 사항은 사용자 승인 후 진행
- **테스트 명령어 활용**: 
  - 개별 파일: `cd $APP_TOOLS_FOLDER/../test && java -cp ".:lib/*" com.test.mybatis.MyBatisBulkExecutorWithJson [파일명] --db $TARGET_DBMS_TYPE `
  - 전체 테스트: `cd $APP_TOOLS_FOLDER/../test && java -cp ".:lib/*" com.test.mybatis.MyBatisBulkExecutorWithJson $APP_LOGS_FOLDER/mapper --db $TARGET_DBMS_TYPE --include transform --json-file oma_test_result.json`

