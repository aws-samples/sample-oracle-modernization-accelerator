# SQL Test 변환 오류 기반 SQL 변환 수정

**CRITICAL DATABASE CONNECTION INFO**:
- **절대 SQLite 사용 금지!** 
- **반드시 PostgreSQL 사용**: psql 명령어로 접속
- **접속 명령어**: `psql` (환경변수 자동 사용)
- **테이블 위치**: oma.sqllist (PostgreSQL 스키마)
- **SQLite 파일 (oma_test.db) 절대 사용하지 말 것**

Reference: Apply environment information from $APP_TOOLS_FOLDER/environmentContext.md

**IMPORTANT**: This process requires interactive user input. The system MUST pause and wait for user input at designated points. Do not skip or auto-fill any user input sections.

[$TARGET_DBMS_TYPE Expert Mode]
**목표**: 전체 SQL Test를 수행해고 수행된 결과 중에서 결과가 동일하지 않은 SQL에 대한 SQL 변환 수정을 수행

**전문가 모드 설정**:
- $SOURCE_DBMS_TYPE에서 $TARGET_DBMS_TYPE로의 SQL 변환 전문 지식 활용
- $TARGET_DBMS_TYPE , 함수, 데이터 타입에 대한 깊은 이해

---

## 1 부정확한 변환 구문 식별
- analyze_result.sh 의 실행 결과로 생성된 최신의 out/analysis_report_*.md 테스트 결과 파일에서 결과가 다른 항목들을 식별
- **PostgreSQL 접속**: `psql` 명령어 사용 (환경변수 자동 인식)
- sqllist table
$ psql
oma=> \d sqllist
                         Table "oma.sqllist"
   Column   |          Type          | Collation | Nullable | Default
------------+------------------------+-----------+----------+---------
 sql_id     | character varying(100) |           | not null |
 sql_type   | character(1)           |           | not null |
 src_path   | text                   |           |          |
 src_stmt   | text                   |           |          |
 src_params | text                   |           |          |
 src_result | text                   |           |          |
 tgt_path   | text                   |           |          |
 tgt_stmt   | text                   |           |          |
 tgt_params | text                   |           |          |
 tgt_result | text                   |           |          |
 same       | character(1)           |           |          |
Indexes:
    "sqllist_pkey" PRIMARY KEY, btree (sql_id)
    "idx_sqllist_same" btree (same)
    "idx_sqllist_sql_type" btree (sql_type)
Check constraints:
    "sqllist_same_check" CHECK (same = ANY (ARRAY['Y'::bpchar, 'N'::bpchar]))
    "sqllist_sql_type_check" CHECK (sql_type = ANY (ARRAY['S'::bpchar, 'I'::bpchar, 'U'::bpchar, 'D'::bpchar, 'P'::bpchar, 'O'::bpchar]))

- **쿼리 예시**: `psql -c "SELECT sql_id, length(src_result) as src_result_length, length(tgt_result) as tgt_result_length FROM oma.sqllist WHERE same='N' ORDER BY sql_id"`
- 각 오류에 대해 다음 정보 추출:
  - SQL ID
  - 소스와 타겟 매퍼 파일명

## 2 테스트 결과가 다른 원인 분석
- **PostgreSQL에서** oma.sqllist 테이블의 src_result 와 tgt_result 를 비교 분석
- 소스 매퍼와 타겟 매퍼 파일을 비교 분석
- 테스트 결과의 차이가 발생한 원인을 찾고 수정 방안 제시

## 3 타겟 매퍼 수정 프로세스
- 구체적인 수정 내용 설명
- 수정 전후 SQL 비교
- 수정이 다른 부분에 미칠 영향 검토
- 수정 시 반드시 지켜야 할 원칙
  1. SQL 구조 단순화 금지! 반드시 소스의 구조를 유지하면서 변환
  2. 하드코딩 형태의 수정은 허용하지 않음
  3. 소스 매퍼(Oracle)는 절대 건드리지 않음
  4. 정규식을 사용한 sed 변경은 절대 사용 불가, AI가 직접 확인하고 수정
  5. SQL 구문을 단순화 해서 변환하지 않음
  6. 소스의 결과와 타겟의 결과가 완전히 일치할 때 까지 수정. 약간의 오차도 절대 허용하지 않음
  7. 타겟 구문 수정 시, 소스 구문과 비교하면서 수정
  8. 데이터 타입이나 정밀도 차이가 있을 수 있기 때문에 소스와 타겟의 실행 결과 값도 비교 분석할 것
- 수정 구문 검증 방법 : ./run_postgresql.sh [sqllist.tgt_path]
- 사용자 승인 요청
   ```
   타겟 매퍼 SQL 변환을 실행 하시겠습니까? (y/s/q)
   y: 예, 변환 실행
   s: 건너뛰기 (이미 변환됨)
   q: 종료
   >
   ```
**STOP HERE - WAIT FOR USER APPROVAL**

The system must pause and wait for user to enter y, n, s, or q.
Each modification requires explicit user approval.

- 변환이 완료되면 사용자의 확인을 통해 다음 변환을 진행
   ```
   [매퍼명.sql_id] 변환을 완료하고 다음 구문의 변환을 실행 하시겠습니까? (y/n/s/q)
   y: 예, 다음 구문 변환 실행
   n: 아니오, 지금 구문 변환을 계속 진행
   s: 건너뛰기 (이미 변환됨)
   q: 종료
   >
   ```

## 주의사항

- **백업 필수**: 모든 수정 전에 원본 파일 백업
- **점진적 수정**: 한 번에 여러 오류를 수정하지 말고 하나씩 처리
- **개별 검증**: 각 파일 수정 후 개별 테스트로 즉시 검증
- **전체 검증**: 여러 파일 수정 후 전체 테스트로 종합 검증
- **부작용 확인**: 수정으로 인한 새로운 오류 발생 여부 모니터링
- **문서화**: 수정 내용과 이유를 명확히 기록
- **사용자 확인**: 모든 수정 사항은 사용자 승인 후 진행

