# 백그라운드 병렬 SQL 변환 처리

## 파일 위치: /tmp

### 주요 파일들
- `sqlTransformTarget_parallel.py`: 병렬 처리 지원 메인 프로그램
- `run_parallel_background.sh`: 백그라운드 병렬 실행 스크립트
- `check_parallel_status.sh`: 프로세스 상태 확인
- `stop_parallel_processes.sh`: 모든 프로세스 종료

## 사용 방법

### 1. 백그라운드 실행 시작
```bash
# 환경 변수 설정
source ./oma_env_프로젝트명.sh

# 백그라운드 병렬 실행
/tmp/run_parallel_background.sh
```

### 2. 상태 확인
```bash
# 프로세스 상태 확인
/tmp/check_parallel_status.sh

# 실시간 로그 확인
tail -f $APP_LOGS_FOLDER/background/process_*_*.log
```

### 3. 프로세스 종료
```bash
# 모든 프로세스 종료
/tmp/stop_parallel_processes.sh
```

## 특징

### 병렬 처리 방식
- CSV의 No 컬럼 끝자리(0~9)로 파일 분할
- 10개 프로세스 동시 실행
- 각 프로세스 독립적 작업

### 백그라운드 실행
- `nohup` 사용으로 터미널 종료 후에도 계속 실행
- 각 프로세스별 개별 로그 파일
- PID 파일로 프로세스 관리

### 모니터링
- 실시간 상태 확인 가능
- CPU 사용률 표시
- 최근 로그 미리보기

## 로그 파일 위치
- 백그라운드 로그: `$APP_LOGS_FOLDER/background/`
- 프로세스별 로그: `process_{0-9}_YYYYMMDD_HHMMSS.log`
- 마스터 로그: `parallel_master_YYYYMMDD_HHMMSS.log`
- PID 파일: `$APP_LOGS_FOLDER/background/pids/`

## 성능 향상
- 기존 대비 약 10배 빠른 처리 속도
- 시스템 리소스 효율적 활용
- 대용량 파일 처리에 최적화
