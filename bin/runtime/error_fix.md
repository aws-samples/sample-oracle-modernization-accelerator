# SQL 에러 분석 및 수정 요청

## 요청사항
1. **MySQL Migration 전문가로서 작업 진행**
2. **XML 파일 분석**: `{{FILE_PATH}}`에서 SQL ID `{{SQL_ID}}`로 해당하는 전체 SQL을 찾아 분석
   - XML 화일만 입력된 경우 $TRANSFORM_XML_FOLDER의 하위 디렉토리를 검색
3. **에러 분석**: `{{ERROR_MESSAGE}}` 에러 메시지를 분석해서 왜 문제가 되는지 첨부된 SQL `{{SQL_QUERY}}을 참조해서 분석 및 설명
4. **해결 방안 제시**: 고칠 수 있는 해결 방안을 제시
5. **XML 수정**: 원본 로직이나 포맷 및 구문은 무조건 유지하고 빠르게 Fix 할 수 있는 방안 (MySQL에서 돌아갈 수 있게)으로 xml을 수정.
6. **백업 생성**: 수정 전 백업을 /tmp에 만들고 수정

## 특별 에러 처리 규칙
6. 에러 유형이 "Every derived table must have its own alias"인 경우 현재 디렉토리의 alias.md를 참조하여 수정합니다.
7. 에러 유형이 "Unknown column 'ROWNUM' in 'order clause'"인 경우 수정 필요 없음으로 리턴합니다.
8. Unknown column 에러인 경우, Table Alias와 컬럼 참조가 Alias에서 기술된 대/소문자로 지정 되었는지 우선 확인 해봅니다. ( 예. 오류 : Select a.name from EMP as A -> 해결책 A.name으로 대문자 Alias지정)
9. XML에 simplified라는 주석이 포함된 경우 작업을 중지하고 사용자에게 노티합니다. 절대 simplified/truncated 하지 말것.
10. XML 태그 유지. choose 및 CDATA 및 if 유지
11. outer join, subqueyr alias 주의
12. 테이블 및 alias 대문자. Target MySQL은 v8
13. MAX ( 는 MAX( 로 변경. MAX 함수 뒤에는 공백이 없어야 함.
14. 특수 태그 변환: "_TAG_" → `_TAG_`, "_ROWI_" → `_ROWI_`, "_COUNT_" → `_COUNT_`

## 작업 순서
1. XML 파일을 읽어서 해당 SQL ID의 전체 SQL 확인
2. 에러 메시지와 SQL을 비교 분석. 이미 수정 적용된 파일이면 스킵.
3. 문제점 식별 및 해결 방안 제시
4. 백업 파일 생성
5. XML 파일 수정 ( 참조 : 필요하다면 $ORCL_XML_FOLDER의 하위 디렉토리를 검색해서 Oracle 원본과 로직을 비교 )
6. 수정 내용 확인

**⚠️ 중요: 코드 최적화 절대 금지**
- MySQL 호환성 변환 시 어떠한 코드 최적화도 하지 말 것
- 중복 코드라도 Extract 파일과 동일하게 유지
- 주석 처리된 코드(<!-- -->)도 그대로 보존
- 들여쓰기, 공백, 탭도 최대한 원본과 동일하게 유지
- 불필요해 보이는 조건문도 Extract와 동일하게 복원
- 목적: Extract와 Transform 간 1:1 정확한 대응 관계 유지

**지금 바로 XML 파일을 읽어서 분석을 시작해주세요.**