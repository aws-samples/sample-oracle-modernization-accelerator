#!/bin/bash

# MySQL MyBatis 테스트 실행 스크립트

echo "=== MySQL MyBatis 테스트 실행 ==="

# 환경변수 확인
if [ -z "$MYSQL_USER" ] || [ -z "$MYSQL_PASSWORD" ]; then
    echo "❌ MySQL 환경변수가 설정되지 않았습니다."
    echo "필요한 환경변수:"
    echo "  MYSQL_USER (필수)"
    echo "  MYSQL_PASSWORD (필수)"
    echo "  MYSQL_HOST (선택사항, 기본값: localhost)"
    echo "  MYSQL_TCP_PORT (선택사항, 기본값: 3306)"
    echo "  MYSQL_DATABASE (선택사항, 기본값: test)"
    echo ""
    echo "예시:"
    echo "  export MYSQL_USER=root"
    echo "  export MYSQL_PASSWORD=your_password"
    echo "  export MYSQL_HOST=localhost"
    echo "  export MYSQL_TCP_PORT=3306"
    echo "  export MYSQL_DATABASE=testdb"
    exit 1
fi

echo "✅ MySQL 환경변수 확인 완료"
echo "   사용자: $MYSQL_USER"
echo "   호스트: ${MYSQL_HOST:-localhost}"
echo "   포트: ${MYSQL_TCP_PORT:-3306}"
echo "   데이터베이스: ${MYSQL_DATABASE:-test}"

# TARGET_DBMS_TYPE 설정 (SqlListRepository용)
export TARGET_DBMS_TYPE=mysql
echo "   타겟 DB 타입: $TARGET_DBMS_TYPE"

# MySQL JDBC 드라이버 확인
if [ ! -f "lib/mysql-connector-j-8.2.0.jar" ]; then
    echo "❌ MySQL JDBC 드라이버가 없습니다."
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
echo "=== MySQL 테스트 실행 ==="

# TEST_FOLDER 환경변수 설정 (첫 번째 인수가 매퍼 디렉토리)
if [ -z "$TEST_FOLDER" ] && [ -n "$1" ]; then
    export TEST_FOLDER="$1"
fi

java -cp ".:lib/*" com.test.mybatis.MyBatisBulkExecutorWithJson "$@" --db mysql

echo ""
echo "=== 실행 완료 ==="
