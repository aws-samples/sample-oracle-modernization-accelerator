## 환경 설정
```bash
# 환경 변수 로드
source ./bin/oma_env_${APPLICATION_NAME}.sh

# 환경 변수 확인
./checkEnv.sh
```

## 변환 작업 수행
```bash
# 각 디렉토리에서 필요한 작업 수행
# 각 디렉토리에서 필요한 작업 수행

# 각 도구별로 실행
```

## 디렉토리 구조
- `transform` - DB 스키마 변환 결과
- `transform` - 애플리케이션 분석 및 변환 결과
- `transform` - 테스트 관련 파일들

## 주의사항
- DB 관련 작업은 Oracle/PostgreSQL 연결이 필요합니다
- 환경 변수 파일을 먼저 source 해야 합니다
