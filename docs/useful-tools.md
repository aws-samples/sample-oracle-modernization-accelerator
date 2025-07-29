---
layout: default
title: 유용한 툴들
nav_order: 9
description: "OMA 프로젝트에서 활용할 수 있는 유용한 도구들"
---

# 유용한 툴들

OMA 프로젝트 진행 시 활용할 수 있는 유용한 도구들을 소개합니다.

## 🚀 Batch 프로세싱

### **OMA 병렬 SQL 변환 처리**
- **용도**: 대용량 SQL 변환 작업의 병렬 처리
- **위치**: `$APP_TOOLS_FOLDER/../batch/`
- **주요 기능**:
  - 백그라운드 병렬 실행으로 처리 속도 향상 (약 10배)
  - CSV No 컬럼 끝자리(0~9)로 파일 자동 분할
  - 최대 10개 프로세스 동시 실행
  - 실시간 모니터링 및 제어

#### **주요 스크립트**
- `sqlTransformTarget_parallel.py`: 병렬 처리 메인 프로그램
- `run_parallel_background.sh`: 전체 병렬 실행 (10개 프로세스)
- `run_single_background.sh`: 단일 프로세스 실행
- `check_parallel_status.sh`: 프로세스 상태 확인
- `stop_parallel_processes.sh`: 모든 프로세스 종료

#### **사용 방법**

**전체 병렬 실행:**
```bash
# 환경 변수 설정
source ./oma_env_<project_name>.sh

# 10개 프로세스 병렬 실행
/tmp/run_parallel_background.sh
```

**선택적 프로세스 실행:**
```bash
# 프로세스 0 실행 (No 끝자리 0 처리)
$APP_TOOLS_FOLDER/../batch/run_single_background.sh 0

# 프로세스 3 실행, transform 모드
$APP_TOOLS_FOLDER/../batch/run_single_background.sh 3 transform

# 프로세스 7 실행, extract 모드, 배치크기 5
$APP_TOOLS_FOLDER/../batch/run_single_background.sh 7 extract 5
```

**상태 모니터링:**
```bash
# 프로세스 상태 확인
$APP_TOOLS_FOLDER/../batch/check_parallel_status.sh

# 실시간 로그 확인
tail -f $APP_LOGS_FOLDER/background/process_*_*.log
```

**프로세스 제어:**
```bash
# 모든 프로세스 종료
$APP_TOOLS_FOLDER/../batch/stop_parallel_processes.sh
```

#### **파라미터 옵션**
- **process_id** (필수): 0~9 중 하나 (CSV No 끝자리와 매칭)
- **mode** (선택): all|extract|transform|merge (기본값: all)
- **batch_size** (선택): 처리 단위 크기 (기본값: 10)

#### **로그 관리**
- **위치**: `$APP_LOGS_FOLDER/background/`
- **프로세스별 로그**: `process_{0-9}_YYYYMMDD_HHMMSS.log`
- **마스터 로그**: `parallel_master_YYYYMMDD_HHMMSS.log`
- **PID 파일**: `$APP_LOGS_FOLDER/background/pids/`

#### **다중 계정 활용 예시**
```bash
# 계정1에서 프로세스 0,1 실행
$APP_TOOLS_FOLDER/../batch/run_single_background.sh 0
$APP_TOOLS_FOLDER/../batch/run_single_background.sh 1

# 계정2에서 프로세스 2,3 실행  
$APP_TOOLS_FOLDER/../batch/run_single_background.sh 2
$APP_TOOLS_FOLDER/../batch/run_single_background.sh 3
```

### **OMA 상태 수집 도구 (gatherStatus.sh)**
- **용도**: OMA 프로젝트의 전체 진행 상황 및 통계 정보 수집
- **위치**: `$OMA_HOME/bin/gatherStatus.sh`
- **주요 기능**:
  - SQL 변환 작업 진행 상황 통계
  - Extract/Transform XML 파일 개수 집계
  - Process 상태별 분포 및 비율 분석
  - 전체 작업 현황 요약 리포트

#### **수집하는 정보**

**1. SQLTransformTarget.csv Process 컬럼 통계:**
- 총 레코드 수
- Process 상태별 개수 및 비율
- 완료/진행중/오류 상태 분포

**2. Extract XML 파일 통계:**
- Extract 단계에서 생성된 XML 파일 개수
- 파일 위치: `$APP_LOGS_FOLDER/*/extract/*.xml`

**3. Transform XML 파일 통계:**
- Transform 단계에서 생성된 XML 파일 개수
- 파일 위치: `$APP_LOGS_FOLDER/*/transform/*.xml`

**4. 전체 요약:**
- CSV 파일 위치 정보
- 총 XML 파일 개수
- 작업 진행률 개요

#### **사용 방법**
```bash
# 환경 변수 설정
source ./oma_env_<project_name>.sh

# 상태 정보 수집 실행
$OMA_HOME/bin/gatherStatus.sh

# 결과를 파일로 저장
$OMA_HOME/bin/gatherStatus.sh > status_report_$(date +%Y%m%d_%H%M%S).txt
```

#### **출력 예시**
```
=== 통계 자료 수집 시작 ===
수집 시간: 2024-07-29 17:00:00

=== SQLTransformTarget.csv Process 컬럼별 통계 ===
파일 위치: /path/to/SQLTransformTarget.csv
총 레코드 수: 1500

Process 상태별 통계 및 비율:
+---------------+-------+--------+
| 상태          | 개수  | 비율   |
+---------------+-------+--------+
| COMPLETED     |   850 | 56.67% |
| PROCESSING    |   400 | 26.67% |
| ERROR         |   150 | 10.00% |
| (빈값)        |   100 |  6.67% |
+---------------+-------+--------+
| 전체          |  1500 | 100.00% |
+---------------+-------+--------+

=== Extract XML 파일 통계 ===
Extract XML 파일 개수: 850

=== Transform XML 파일 통계 ===
Transform XML 파일 개수: 750

=== 전체 요약 ===
CSV 파일: /path/to/SQLTransformTarget.csv
Extract XML 파일: 850 개
Transform XML 파일: 750 개
총 XML 파일: 1600 개
```

## 📊 Amazon Q Log Monitoring

### **실시간 로그 모니터링 도구 (tailLatestLog.sh)**
- **용도**: Amazon Q 작업 로그의 실시간 모니터링
- **위치**: `$APP_TOOLS_FOLDER/tailLatestLog.sh`
- **주요 기능**:
  - 가장 최근 생성된 로그 파일 자동 추적
  - 새 로그 파일 생성 시 자동 전환
  - 연속적인 로그 모니터링 지원

#### **사용 방법**
```bash
# 환경 변수 설정
source ./oma_env_<project_name>.sh

# 직접 실행
$APP_TOOLS_FOLDER/tailLatestLog.sh

# 또는 alias 사용 (설정 후)
qlog
```

#### **Alias 설정**
```bash
# .bashrc에 alias 추가
echo "alias qlog='\$APP_TOOLS_FOLDER/tailLatestLog.sh'" >> ~/.bashrc

# .bashrc 재로드
source ~/.bashrc

# 이제 qlog 명령어로 간단히 실행 가능
qlog
```

## 🔄 MySQL Post Transform

### **MySQL 전용 후처리 변환 가이드**
- **용도**: Oracle에서 MySQL로 변환된 SQL의 MySQL 특화 후처리 작업
- **위치**: `$APP_TOOLS_FOLDER/../postTransform/forMysql/`
- **주요 기능**:
  - Oracle 전용 함수/구문을 MySQL 호환 형태로 변환
  - 변환 품질 검증 및 보정 가이드 제공
  - Amazon Q를 활용한 자동 변환 프롬프트 제공

#### **주요 변환 가이드**

**1. postSequence.md - SEQUENCE → AUTO_INCREMENT 변환**
- **목적**: Oracle SEQUENCE.NEXTVAL을 MySQL AUTO_INCREMENT로 변환
- **주요 내용**:
  - 6가지 유형별 변환 패턴 제공
  - INSERT 구문에서 시퀀스 제거 및 AUTO_INCREMENT 활용
  - MyBatis XML의 selectKey 구문 변환

**2. postRollUp.md - GROUP BY ROLLUP 변환**
- **목적**: Oracle GROUP BY ROLLUP/GROUPING SETS를 MySQL 호환 형태로 변환
- **주요 내용**:
  - Oracle ROLLUP → MySQL WITH ROLLUP 변환
  - GROUPING() 함수 대안 방법 제시
  - CUBE, GROUPING SETS → UNION ALL 변환 패턴

**3. postTrim.md - TRIM 함수 변환**
- **목적**: Oracle TRIM/LTRIM/RTRIM 함수를 MySQL 호환 형태로 변환
- **주요 내용**:
  - Oracle 특정 문자 제거 구문 → MySQL 호환 형태 변환
  - LEADING/TRAILING/BOTH 옵션 처리
  - 복합 TRIM 구문 변환 패턴

#### **Amazon Q 활용 예시**

**postSequence.md 프롬프트 활용:**
```
다음 Oracle MyBatis XML에서 SEQUENCE.NEXTVAL 패턴을 MySQL AUTO_INCREMENT로 변환해주세요:

[변환할 XML 내용 붙여넣기]

변환 시 다음 규칙을 적용해주세요:
1. INSERT 구문에서 시퀀스 컬럼 제거
2. selectKey 구문을 MySQL 호환 형태로 변경
3. 기존 시퀀스 값은 AUTO_INCREMENT로 대체
```

**postRollUp.md 프롬프트 활용:**
```
다음 Oracle SQL의 GROUP BY ROLLUP 구문을 MySQL WITH ROLLUP으로 변환해주세요:

[변환할 SQL 내용 붙여넣기]

변환 시 다음 사항을 고려해주세요:
1. GROUPING() 함수는 CASE WHEN으로 대체
2. CUBE나 GROUPING SETS는 UNION ALL로 분해
3. MySQL WITH ROLLUP 제한사항 반영
```

**postTrim.md 프롬프트 활용:**
```
다음 Oracle TRIM 함수를 MySQL 호환 형태로 변환해주세요:

[변환할 SQL 내용 붙여넣기]

변환 시 다음 규칙을 적용해주세요:
1. 특정 문자 제거 구문을 MySQL 문법으로 변경
2. LTRIM/RTRIM의 두 번째 파라미터 처리
3. 중첩된 TRIM 함수 최적화
```

#### **사용 방법**
```bash
# 환경 변수 설정
source ./oma_env_<project_name>.sh

# 가이드 파일 확인
cat $APP_TOOLS_FOLDER/../postTransform/forMysql/postSequence.md
cat $APP_TOOLS_FOLDER/../postTransform/forMysql/postRollUp.md  
cat $APP_TOOLS_FOLDER/../postTransform/forMysql/postTrim.md

# Amazon Q CLI에서 프롬프트 활용
q chat
# 위의 프롬프트 예시를 복사하여 사용
```

---

💡 **팁**: 각 도구의 사용법을 숙지하고, 프로젝트 단계에 맞는 도구를 선택하여 효율적으로 작업하세요.
