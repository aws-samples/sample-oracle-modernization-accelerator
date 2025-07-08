#!/bin/bash

# 1. sqllist 테이블 초기화
psql -c "truncate table sqllist"

# 2. 작업 폴더 초기화
rm -rf $TEST_FOLDER/*

# 3. XML 파일에서 SQL 구문 추출
./XMLToSQL.py

# 4. 딕셔너리 파일 생성
./GetDictionary.py

# 5. 바인드 변수 처리 시스템 (기본 설정 사용, 필요시 config 수정)
./BindSampler.py
./BindMapper.py

# 6. 바인드 변수가 치환된 SQL 파일을 sqllist 테이블에 저장
./SaveSQLToDB.py

# 7. SQL 파일 실행하고 실행 결과 저장 및 비교
./ExecuteAndCompareSQL.py -t S

# 8. Postgres 에러 유형 분석
./analyze_pg_errors.py
