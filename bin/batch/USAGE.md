# 병렬 SQL 변환 처리 사용법

## 파일 위치: $APP_TOOLS_FOLDER/../batch/

### 주요 파일들
- `sqlTransformTarget_parallel.py`: 병렬 처리 지원 메인 프로그램
- `run_single_background.sh`: 단일 프로세스 백그라운드 실행 스크립트
- `check_parallel_status.sh`: 프로세스 상태 확인
- `stop_parallel_processes.sh`: 모든 프로세스 종료

## 사용 방법

### 1. 단일 프로세스 백그라운드 실행
```bash
# 환경 변수 설정
source ./oma_env_프로젝트명.sh

# 프로세스 0 실행 (No 끝자리 0 처리)
$APP_TOOLS_FOLDER/../batch/run_single_background.sh 0

# 프로세스 3 실행, transform 모드
$APP_TOOLS_FOLDER/../batch/run_single_background.sh 3 transform

# 프로세스 7 실행, extract 모드, 배치크기 5
$APP_TOOLS_FOLDER/../batch/run_single_background.sh 7 extract 5
```

### 2. 상태 확인
```bash
# 프로세스 상태 확인
$APP_TOOLS_FOLDER/../batch/check_parallel_status.sh

# 실시간 로그 확인
tail -f $APP_LOGS_FOLDER/background/process_*_*.log
```

### 3. 프로세스 종료
```bash
# 모든 프로세스 종료
$APP_TOOLS_FOLDER/../batch/stop_parallel_processes.sh
```

## 계정별 실행 예시

### 계정1에서:
```bash
source ./oma_env_프로젝트명.sh
$APP_TOOLS_FOLDER/../batch/run_single_background.sh 0
$APP_TOOLS_FOLDER/../batch/run_single_background.sh 1
```

### 계정2에서:
```bash
source ./oma_env_프로젝트명.sh
$APP_TOOLS_FOLDER/../batch/run_single_background.sh 2
$APP_TOOLS_FOLDER/../batch/run_single_background.sh 3
```

### 계정3에서:
```bash
source ./oma_env_프로젝트명.sh
$APP_TOOLS_FOLDER/../batch/run_single_background.sh 4
$APP_TOOLS_FOLDER/../batch/run_single_background.sh 5
```

## 파라미터 설명

### run_single_background.sh 파라미터:
1. **process_id** (필수): 0~9 중 하나 (CSV No 끝자리와 매칭)
2. **mode** (선택): all|extract|transform|merge (기본값: all)
3. **batch_size** (선택): 숫자 (기본값: 10)

## 로그 파일 위치
- 백그라운드 로그: `$APP_LOGS_FOLDER/background/`
- 프로세스별 로그: `process_{0-9}_YYYYMMDD_HHMMSS.log`
- PID 파일: `$APP_LOGS_FOLDER/background/pids/`

## 장점
- 계정별 독립 실행으로 리소스 분산
- 필요한 프로세스만 선택적 실행
- 백그라운드 실행으로 터미널 독립성
- 실시간 모니터링 및 제어 가능
