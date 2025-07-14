#!/bin/bash

# 환경 변수 확인
if [ -z "$TARGET_DBMS_TYPE" ]; then
    echo "TARGET_DBMS_TYPE 환경 변수가 설정되지 않았습니다. 기본값 'postgres'를 사용합니다."
    export TARGET_DBMS_TYPE=postgres
fi

echo "타겟 DBMS 타입: $TARGET_DBMS_TYPE"

# 1. sqllist 테이블 초기화 (TARGET_DBMS_TYPE에 따라 분기)
echo "sqllist 테이블 초기화 중..."

if [ "$TARGET_DBMS_TYPE" = "postgres" ] || [ "$TARGET_DBMS_TYPE" = "postgresql" ]; then
    # PostgreSQL 환경 변수 확인
    if [ -z "$PGHOST" ] || [ -z "$PGPORT" ] || [ -z "$PGDATABASE" ] || [ -z "$PGUSER" ] || [ -z "$PGPASSWORD" ]; then
        echo "오류: PostgreSQL 연결 정보가 환경 변수에 설정되지 않았습니다."
        echo "필요한 환경 변수: PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD"
        exit 1
    fi
    
    echo "PostgreSQL에서 sqllist 테이블 초기화..."
    psql -h $PGHOST -p $PGPORT -d $PGDATABASE -U $PGUSER -c "TRUNCATE TABLE sqllist;"
    
    if [ $? -eq 0 ]; then
        echo "PostgreSQL sqllist 테이블 초기화 완료"
    else
        echo "오류: PostgreSQL sqllist 테이블 초기화 실패"
        exit 1
    fi

elif [ "$TARGET_DBMS_TYPE" = "mysql" ]; then
    # MySQL 환경 변수 확인
    if [ -z "$MYSQL_HOST" ] || [ -z "$MYSQL_PORT" ] || [ -z "$MYSQL_DATABASE" ] || [ -z "$MYSQL_USER" ] || [ -z "$MYSQL_PASSWORD" ]; then
        echo "오류: MySQL 연결 정보가 환경 변수에 설정되지 않았습니다."
        echo "필요한 환경 변수: MYSQL_HOST, MYSQL_PORT, MYSQL_DATABASE, MYSQL_USER, MYSQL_PASSWORD"
        exit 1
    fi
    
    echo "MySQL에서 sqllist 테이블 초기화..."
    mysql -h $MYSQL_HOST -P $MYSQL_PORT -u $MYSQL_USER -p$MYSQL_PASSWORD -D $MYSQL_DATABASE -e "TRUNCATE TABLE sqllist;"
    
    if [ $? -eq 0 ]; then
        echo "MySQL sqllist 테이블 초기화 완료"
    else
        echo "오류: MySQL sqllist 테이블 초기화 실패"
        exit 1
    fi

else
    echo "오류: 지원하지 않는 TARGET_DBMS_TYPE: $TARGET_DBMS_TYPE"
    echo "지원되는 타입: postgres, postgresql, mysql"
    exit 1
fi

# 2. 작업 폴더 초기화
echo "작업 폴더 초기화 중..."
if [ -n "$TEST_FOLDER" ] && [ -d "$TEST_FOLDER" ]; then
    rm -rf $TEST_FOLDER/*
    echo "작업 폴더 초기화 완료: $TEST_FOLDER"
else
    echo "경고: TEST_FOLDER 환경 변수가 설정되지 않았거나 디렉토리가 존재하지 않습니다."
fi

# 3. XML 파일에서 SQL 구문 추출
echo "XML 파일에서 SQL 구문 추출 중..."
./XMLToSQL.py

# 4. 딕셔너리 파일 생성
echo "딕셔너리 파일 생성 중..."
./GetDictionary.py

# 5. 바인드 변수 처리 시스템 (기본 설정 사용, 필요시 config 수정)
echo "바인드 변수 샘플링 중..."
./BindSampler.py

echo "바인드 변수 매핑 중..."
./BindMapper.py

# 6. 바인드 변수가 치환된 SQL 파일을 sqllist 테이블에 저장
echo "SQL 파일을 sqllist 테이블에 저장 중..."
./SaveSQLToDB.py

# 7. SQL 파일 실행하고 실행 결과 저장 및 비교
echo "SQL 실행 및 결과 비교 중..."
./ExecuteAndCompareSQL.py -t S

# 8. Postgres 에러 유형 분석 (PostgreSQL인 경우에만)
if [ "$TARGET_DBMS_TYPE" = "postgres" ] || [ "$TARGET_DBMS_TYPE" = "postgresql" ]; then
    echo "PostgreSQL 에러 유형 분석 중..."
    ./analyze_pg_errors.py
fi

# 9. 오류 구문 자동 수정 (향후 구현)
# ./pg_transform.py

echo "initTest.sh 실행 완료"
