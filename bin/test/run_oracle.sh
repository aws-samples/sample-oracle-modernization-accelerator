#!/bin/bash

# Oracle MyBatis 테스트 실행 스크립트

echo "=== Oracle MyBatis 테스트 실행 ==="

# 도움말 출력 함수
print_usage() {
    echo "사용법: $0 <디렉토리경로> [옵션]"
    echo ""
    echo "옵션:"
    echo "  --select-only   SELECT 구문만 실행 (기본값)"
    echo "  --all          모든 SQL 구문 실행 (INSERT/UPDATE/DELETE 포함)"
    echo "  --summary      요약 정보만 출력"
    echo "  --verbose      상세 정보 출력"
    echo "  --json         JSON 결과 파일 생성"
    echo "  --json-file <filename>  JSON 결과 파일 생성 (파일명 지정)"
    echo "  --include <pattern>     지정된 패턴이 포함된 폴더만 탐색"
    echo "  --compare      SQL 결과 비교 기능 활성화 (Oracle ↔ PostgreSQL/MySQL)"
    echo ""
    echo "환경변수:"
    echo "  ORACLE_SVC_USER        Oracle 사용자명 (필수)"
    echo "  ORACLE_SVC_PASSWORD    Oracle 비밀번호 (필수)"
    echo "  ORACLE_SVC_CONNECT_STRING  Oracle 연결 문자열 (선택사항)"
    echo "  TARGET_DBMS_TYPE       비교 대상 DB 타입 (mysql 또는 postgresql, --compare 사용시 필수)"
    echo ""
    echo "PostgreSQL 연동 환경변수 (--compare 사용시):"
    echo "  PGUSER, PGPASSWORD, PGHOST, PGPORT, PGDATABASE"
    echo ""
    echo "MySQL 연동 환경변수 (--compare 사용시):"
    echo "  MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_TCP_PORT, MYSQL_DATABASE"
    echo ""
    echo "예시:"
    echo "  $0 /path/to/mappers --select-only --summary"
    echo "  $0 /path/to/mappers --all --verbose --json"
    echo "  $0 /path/to/mappers --compare --verbose"
}

# 파라미터 확인
if [ $# -eq 0 ] || [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    print_usage
    exit 0
fi

# 환경변수 확인
if [ -z "$ORACLE_SVC_USER" ] || [ -z "$ORACLE_SVC_PASSWORD" ]; then
    echo "❌ Oracle 환경변수가 설정되지 않았습니다."
    echo "필요한 환경변수:"
    echo "  ORACLE_SVC_USER"
    echo "  ORACLE_SVC_PASSWORD"
    echo "  ORACLE_SVC_CONNECT_STRING (선택사항)"
    echo ""
    echo "예시:"
    echo "  export ORACLE_SVC_USER=your_username"
    echo "  export ORACLE_SVC_PASSWORD=your_password"
    echo "  export ORACLE_SVC_CONNECT_STRING=your_tns_name"
    exit 1
fi

echo "✅ Oracle 환경변수 확인 완료"
echo "   사용자: $ORACLE_SVC_USER"
echo "   연결문자열: ${ORACLE_SVC_CONNECT_STRING:-기본값 사용}"

# PostgreSQL 연동을 위한 환경변수 설정 (선택사항)
if [ -n "$PGUSER" ] && [ -n "$PGPASSWORD" ]; then
    echo "✅ PostgreSQL 연동 환경변수 확인 완료"
    echo "   PostgreSQL 사용자: $PGUSER"
    echo "   PostgreSQL 호스트: ${PGHOST:-localhost}"
    echo "   PostgreSQL 포트: ${PGPORT:-5432}"
    echo "   PostgreSQL 데이터베이스: ${PGDATABASE:-postgres}"
    
    # TARGET_DBMS_TYPE 자동 설정
    export TARGET_DBMS_TYPE=postgresql
    echo "   타겟 DB 타입: $TARGET_DBMS_TYPE"
else
    echo "ℹ️  PostgreSQL 연동 환경변수가 설정되지 않았습니다. (선택사항)"
    echo "   PostgreSQL 연동을 원하면 다음 환경변수를 설정하세요:"
    echo "   PGUSER, PGPASSWORD, PGHOST, PGPORT, PGDATABASE"
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
echo "=== Oracle 테스트 실행 ==="

# TEST_FOLDER 환경변수 설정 (첫 번째 인수가 매퍼 디렉토리)
if [ -z "$TEST_FOLDER" ] && [ -n "$1" ]; then
    export TEST_FOLDER="$1"
fi

java -cp ".:lib/*" com.test.mybatis.MyBatisBulkExecutorWithJson "$@" --db oracle --compare

echo ""
echo "=== 실행 완료 ==="
