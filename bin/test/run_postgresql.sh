#!/bin/bash

# PostgreSQL MyBatis 테스트 실행 스크립트

echo "=== PostgreSQL MyBatis 테스트 실행 ==="

# 환경변수 확인
if [ -z "$PGUSER" ] || [ -z "$PGPASSWORD" ]; then
    echo "❌ PostgreSQL 환경변수가 설정되지 않았습니다."
    echo "필요한 환경변수:"
    echo "  PGUSER (필수)"
    echo "  PGPASSWORD (필수)"
    echo "  PGHOST (선택사항, 기본값: localhost)"
    echo "  PGPORT (선택사항, 기본값: 5432)"
    echo "  PGDATABASE (선택사항, 기본값: postgres)"
    echo ""
    echo "예시:"
    echo "  export PGUSER=postgres"
    echo "  export PGPASSWORD=your_password"
    echo "  export PGHOST=localhost"
    echo "  export PGPORT=5432"
    echo "  export PGDATABASE=testdb"
    exit 1
fi

echo "✅ PostgreSQL 환경변수 확인 완료"
echo "   사용자: $PGUSER"
echo "   호스트: ${PGHOST:-localhost}"
echo "   포트: ${PGPORT:-5432}"
echo "   데이터베이스: ${PGDATABASE:-postgres}"

# TARGET_DBMS_TYPE 설정 (SqlListRepository용)
export TARGET_DBMS_TYPE=postgresql
echo "   타겟 DB 타입: $TARGET_DBMS_TYPE"

# PostgreSQL JDBC 드라이버 확인
if [ ! -f "lib/postgresql-42.7.1.jar" ]; then
    echo "❌ PostgreSQL JDBC 드라이버가 없습니다."
    exit 1
fi

# Oracle 연동을 위한 환경변수 확인 (선택사항)
if [ -n "$ORACLE_SVC_USER" ] && [ -n "$ORACLE_SVC_PASSWORD" ]; then
    echo "✅ Oracle 연동 환경변수 확인 완료"
    echo "   Oracle 사용자: $ORACLE_SVC_USER"
    echo "   Oracle 연결문자열: ${ORACLE_SVC_CONNECT_STRING:-기본값 사용}"
else
    echo "ℹ️  Oracle 연동 환경변수가 설정되지 않았습니다. (선택사항)"
    echo "   Oracle 연동을 원하면 다음 환경변수를 설정하세요:"
    echo "   ORACLE_SVC_USER, ORACLE_SVC_PASSWORD, ORACLE_SVC_CONNECT_STRING"
fi

# 컴파일
echo ""
echo "=== Java 컴파일 ==="
javac -cp ".:lib/*" com/test/mybatis/*.java

if [ $? -ne 0 ]; then
    echo "❌ 컴파일 실패"
    exit 1
fi

echo "✅ 컴파일 완료"

# 실행
echo ""
echo "=== PostgreSQL 테스트 실행 ==="

# TEST_FOLDER 환경변수 설정 (첫 번째 인수가 매퍼 디렉토리)
if [ -z "$TEST_FOLDER" ] && [ -n "$1" ]; then
    export TEST_FOLDER="$1"
fi

java -cp ".:lib/*" com.test.mybatis.MyBatisBulkExecutorWithJson "$@" --db postgres --compare

echo ""
echo "=== 실행 완료 ==="
