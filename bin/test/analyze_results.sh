#!/bin/bash

# 현재 디렉토리 확인
if [ ! -f "com/test/mybatis/TestResultAnalyzer.java" ]; then
    echo "❌ TestResultAnalyzer.java 파일이 없습니다."
    echo "올바른 디렉토리에서 실행하세요: /home/ec2-user/workspace/oma/bin/test"
    exit 1
fi

# 컴파일
echo "🔧 컴파일 중..."
javac -cp ".:lib/*" com/test/mybatis/*.java

if [ $? -ne 0 ]; then
    echo "❌ 컴파일 실패"
    exit 1
fi

echo "✅ 컴파일 완료"

# 분석 보고서 파일 생성
REPORT_FILE="out/analysis_report_$(date +%Y%m%d_%H%M%S).md"

# 실행
echo "▶️ 분석 프로그램 실행 중..."
echo ""

java -cp ".:lib/*" com.test.mybatis.TestResultAnalyzer | tee "$REPORT_FILE"

echo ""
echo "✅ 분석 완료"
echo "📄 보고서 파일: $REPORT_FILE"

# 정렬 방식 차이 자동 수정 (출력 숨김)
java -cp ".:lib/*" com.test.mybatis.TestResultAnalyzer --fix-sorting > /dev/null 2>&1

# Amazon Q 자동 변환 제안
echo ""
echo "🤖 Amazon Q를 통한 SQL 구문 자동 변환을 진행하시겠습니까? (y/n): "
read -r answer

if [[ "$answer" =~ ^[Yy]$ ]]; then
    echo "🚀 Amazon Q 자동 변환을 시작합니다..."
    
    # retransform.md 파일 확인
    if [ ! -f "retransform.md" ]; then
        echo "❌ retransform.md 파일이 없습니다."
        exit 1
    fi
    
    # 환경변수 정보를 포함한 프롬프트 생성
    PROMPT="환경변수 정보:
  - SOURCE_DBMS_TYPE: ${SOURCE_DBMS_TYPE:-oracle}
  - TARGET_DBMS_TYPE: ${TARGET_DBMS_TYPE:-postgresql}
  - PostgreSQL 접속 정보:
    - PGHOST: ${PGHOST}
    - PGPORT: ${PGPORT:-5432}
    - PGDATABASE: ${PGDATABASE}
    - PGUSER: ${PGUSER}

$(cat retransform.md)"
    
    # q chat 실행 (환경변수 정보 포함)
    q chat "$PROMPT"
else
    echo "👋 분석을 완료했습니다."
fi
