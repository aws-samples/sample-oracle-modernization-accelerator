#!/bin/bash

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'
UNDERLINE='\033[4m'

# 구분선 출력 함수
print_separator() {
    printf "${BLUE}${BOLD}%80s${NC}\n" | tr " " " "
}

# ====================================================
# Pre-Requisites: OMA Environment 설정
# ====================================================
setup_oma_environment() {
    print_separator
    echo -e "${BLUE}${BOLD}Pre-Requisites: OMA Environment 설정${NC}"
    print_separator
    echo -e "${CYAN}이 단계에서는 OMA 환경 설정을 수행합니다:${NC}"
    echo -e "${CYAN}- Aurora 설정${NC}"
    echo -e "${CYAN}- DMS 설정${NC}"
    echo -e "${CYAN}- Amazon Q on EC2 설정${NC}"
    print_separator
    
    # deploy-omabox.sh 파일 존재 확인
    if [ ! -f "./setup/deploy-omabox.sh" ]; then
        echo -e "${RED}오류: ./setup/deploy-omabox.sh 파일을 찾을 수 없습니다.${NC}"
        return 1
    fi
    
    echo -e "${BLUE}${BOLD}실행 명령:${NC}"
    echo -e "${BLUE}${BOLD}./setup/deploy-omabox.sh${NC}"
    print_separator

    echo -e "${BLUE}${BOLD}작업을 수행하기 이전에 3초 대기 합니다.${NC}"
    sleep 3

    ./setup/deploy-omabox.sh
    print_separator
    echo -e "${GREEN}OMA Environment 설정이 완료되었습니다.${NC}"
}

# ====================================================
# 메인 스크립트 시작
# ====================================================

print_separator
echo -e "${BLUE}${BOLD}OMA Pre-Requisites 설정${NC}"
print_separator
echo -e "${CYAN}이 스크립트는 OMA 환경 설정을 위한 사전 필수 구성요소를 설정합니다.${NC}"
echo -e "${CYAN}다음 구성요소들이 설정됩니다:${NC}"
echo -e "${CYAN}- Aurora 데이터베이스${NC}"
echo -e "${CYAN}- DMS (Database Migration Service)${NC}"
echo -e "${CYAN}- Amazon Q on EC2${NC}"
print_separator

# 확인 메시지
echo -e "${YELLOW}Pre-Requisites 설정을 시작하시겠습니까? (y/N): ${NC}"
read -r confirmation
confirmation=${confirmation:-N}

if [[ $confirmation =~ ^[Yy]$ ]]; then
    setup_oma_environment
    echo -e "${GREEN}Pre-Requisites 설정이 완료되었습니다.${NC}"
    echo -e "${GREEN}이제 initOMA.sh를 실행하여 프로젝트를 선택하고 변환 작업을 수행할 수 있습니다.${NC}"
else
    echo -e "${YELLOW}Pre-Requisites 설정이 취소되었습니다.${NC}"
fi

print_separator
