# OMA Streamlit Web Application

Oracle Migration Assistant (OMA)의 shell 스크립트를 Streamlit 웹 애플리케이션으로 변환한 버전입니다.

## 주요 기능

### 🏠 환경 설정
- 환경 변수 설정 및 확인
- 프로젝트 초기 설정

### 📊 애플리케이션 분석
- Java 소스 코드 및 MyBatis Mapper 파일 분석
- 분석 보고서 작성 및 SQL 변환 대상 추출
- PostgreSQL 메타데이터 생성

### 🔄 애플리케이션 변환
- SQL 샘플 변환
- SQL 전체 변환
- 변환 테스트 및 결과 수정
- XML Merge 작업

### 🧪 SQL 테스트
- XML List 생성
- SQL Unit Test 실행

### 📋 변환 보고서
- 변환 작업 보고서 생성
- Java Source 변환

## 실행 방법

### 1. 간단한 실행 (권장)
```bash
./run_oma_app.sh
```

### 2. 수동 실행
```bash
# 필요한 패키지 설치
pip install -r requirements.txt

# 환경 변수 설정 (필요한 경우)
export OMA_BASE_DIR="$HOME/workspace/oma"

# Streamlit 애플리케이션 실행
streamlit run oma_streamlit_app.py --server.port 8501 --server.address 0.0.0.0
```

## 접속 방법

애플리케이션이 시작되면 브라우저에서 다음 주소로 접속하세요:
- 로컬: http://localhost:8501
- 원격: http://[서버IP]:8501

## 주요 특징

### 실시간 로그 출력
- 각 작업의 실행 로그가 실시간으로 웹 브라우저에 표시됩니다
- 작업 진행 상황을 시각적으로 확인할 수 있습니다

### 작업 중단 기능
- 사이드바의 "현재 작업 중단" 버튼으로 실행 중인 작업을 중단할 수 있습니다

### 탭 기반 인터페이스
- 각 작업 단계별로 탭으로 구분되어 있어 쉽게 탐색할 수 있습니다

### 환경 상태 표시
- 사이드바에서 현재 환경 설정 상태를 확인할 수 있습니다

## 사전 요구사항

1. **Python 3.7 이상**
2. **OMA 환경 설정**
   - `OMA_BASE_DIR` 환경 변수 설정
   - 필요한 OMA 스크립트들이 올바른 위치에 있어야 함
3. **네트워크 접근**
   - 데이터베이스 연결이 필요한 작업의 경우

## 환경 변수

- `OMA_BASE_DIR`: OMA 설치 디렉토리 (기본값: ~/workspace/oma)
- `APPLICATION_NAME`: 현재 프로젝트명 (환경 설정 후 자동 설정)

## 문제 해결

### 포트 충돌
다른 포트를 사용하려면:
```bash
streamlit run oma_streamlit_app.py --server.port 8502
```

### 권한 문제
스크립트 실행 권한 확인:
```bash
chmod +x run_oma_app.sh
```

### 환경 변수 문제
OMA 환경이 제대로 설정되지 않은 경우, 웹 애플리케이션의 "환경 설정" 탭에서 환경을 다시 설정하세요.

## 기존 Shell 스크립트와의 차이점

1. **웹 인터페이스**: 터미널 대신 웹 브라우저에서 실행
2. **실시간 로그**: 로그가 실시간으로 웹에 표시
3. **시각적 피드백**: 진행률 표시 및 상태 아이콘
4. **작업 중단**: 웹에서 실행 중인 작업을 중단 가능
5. **탭 기반 네비게이션**: 각 단계별로 쉽게 접근

## 지원

문제가 발생하면 다음을 확인하세요:
1. OMA 환경 설정이 올바른지 확인
2. 필요한 스크립트 파일들이 존재하는지 확인
3. 네트워크 연결 상태 확인 (DB 관련 작업의 경우)
