#!/bin/bash

# OMA Streamlit 애플리케이션 실행 스크립트

# 현재 스크립트 디렉토리로 이동
cd "$(dirname "$0")"

# 가상환경이 있는지 확인하고 없으면 생성
if [ ! -d "venv" ]; then
    echo "가상환경을 생성합니다..."
    python3 -m venv venv
fi

# 가상환경 활성화
echo "가상환경을 활성화합니다..."
source venv/bin/activate

# 필요한 패키지 설치
echo "필요한 패키지를 설치합니다..."
pip install -r requirements.txt

# OMA_BASE_DIR 환경 변수 설정 (필요한 경우)
if [ -z "$OMA_BASE_DIR" ]; then
    export OMA_BASE_DIR="$HOME/workspace/oma"
    echo "OMA_BASE_DIR을 $OMA_BASE_DIR로 설정했습니다."
fi

# Streamlit 애플리케이션 실행
echo "OMA Streamlit 애플리케이션을 시작합니다..."
echo "브라우저에서 http://localhost:8501 로 접속하세요."
echo ""
echo "종료하려면 Ctrl+C를 누르세요."
echo ""

streamlit run oma_streamlit_app.py --server.port 8501 --server.address 0.0.0.0
