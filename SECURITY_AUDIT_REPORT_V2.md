# OMA 프로젝트 보안점검 보고서 (2차 점검)

**점검일:** 2025년 7월 29일  
**점검자:** Amazon Q  
**점검 범위:** Oracle Modernization Accelerator (OMA) 전체 프로젝트  
**점검 버전:** 2.0 (심화 점검)

## 📋 점검 개요

본 보고서는 OMA 프로젝트의 2차 보안점검 결과로, 1차 점검에서 놓친 추가 보안 취약점들을 포함합니다.

## 🔍 점검 결과 요약 (업데이트)

| 보안 영역 | 상태 | 위험도 | 발견된 이슈 수 | 변경사항 |
|-----------|------|--------|---------------|----------|
| 민감정보 노출 | ⚠️ 주의 | 중간 | 5개 | +2개 |
| 명령어 인젝션 | 🚨 위험 | 높음 | 4개 | 신규 |
| 파일 권한 | ⚠️ 주의 | 중간 | 2개 | +2개 |
| 네트워크 보안 | ⚠️ 주의 | 중간 | 2개 | 신규 |
| 백업 파일 노출 | ⚠️ 주의 | 낮음 | 5개 | 신규 |

**전체 보안 점수: 65/100** (이전 75점에서 하향 조정)

## 🚨 새로 발견된 심각한 보안 이슈

### 1. 명령어 인젝션 취약점 (높음 위험도) 🚨

#### 이슈 1: subprocess.run에서 shell=True 사용
**파일:** `bin/database/asct.py`  
**위험도:** 높음  
**설명:** 사용자 입력이 포함된 명령어를 shell=True로 실행

```python
# 라인 323
cmd = f"sqlplus -S {ORACLE_CONNECTION} @{temp_file_path}"
result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

# 라인 388
cmd = f"q chat < {prompt_file_path}"
result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

# 라인 717
cmd = f"psql -h {PGHOST} -U {PGUSER} -p {PGPORT} -d {PGDATABASE} -f {sql_file}"
return subprocess.run(cmd, shell=True, capture_output=True, text=True)
```

**권장 조치:**
```python
# 안전한 방법으로 변경
cmd = ["sqlplus", "-S", ORACLE_CONNECTION, f"@{temp_file_path}"]
result = subprocess.run(cmd, capture_output=True, text=True)

# 또는 shlex.quote() 사용
import shlex
cmd = f"sqlplus -S {shlex.quote(ORACLE_CONNECTION)} @{shlex.quote(temp_file_path)}"
```

#### 이슈 2: sudo 권한 상승 로직
**파일:** `bin/batch/sqlTransformTarget_parallel.py`  
**위험도:** 높음  
**설명:** 자동으로 sudo 권한으로 상승하는 로직

```python
# 라인 577
cmd = ["sudo", "mkdir", "-p", directory]
```

**권장 조치:**
- sudo 사용을 명시적으로 사용자가 승인하도록 변경
- 권한 상승 전 사용자 확인 절차 추가

### 2. 추가 민감정보 노출 (중간 위험도)

#### 이슈 3: S3 버킷 하드코딩
**파일:** `bin/application/uploadDiscoveryReport.sh`  
**위험도:** 중간  
**설명:** S3 버킷명이 하드코딩되어 있음

```bash
S3_BUCKET="s3://aws-oma-source-bucket/analysis/"
```

**권장 조치:**
- 환경 변수로 변경: `S3_BUCKET=${OMA_S3_BUCKET:-"s3://your-bucket/analysis/"}`

#### 이슈 4: 네트워크 정보 노출
**파일:** `config/setup/README.md`, `docs/Pre-Requisites.md`  
**위험도:** 중간  
**설명:** 내부 네트워크 CIDR 정보 노출

```
VPC: OMA_VPC (10.255.255.0/24)
--destination-cidr-block 10.0.0.0/16
```

**권장 조치:**
- 실제 CIDR 대신 예시 값으로 변경
- 문서에서 실제 환경에 맞게 변경하라는 안내 추가

### 3. 백업 파일 보안 (낮음 위험도)

#### 이슈 5: 백업 파일 노출
**발견된 파일들:**
```
./bin/test/backup/XMLToSQL.py.backup
./bin/test/backup/ExecuteAndCompareSQL.py.backup
./bin/test/backup/AnalyzeResult.py.backup
./bin/postTransform/function/sql_function_parser.py.backup
./bin/postTransform/function/genSelectFromXML.py.backup
```

**권장 조치:**
- .gitignore에 *.backup, *.bak 패턴 추가
- 기존 백업 파일들 제거 또는 별도 디렉토리로 이동

### 4. 파일 권한 및 임시 파일 (중간 위험도)

#### 이슈 6: /tmp 디렉토리 사용 확장
**파일:** `bin/application/downloadS3Files.sh`  
**위험도:** 중간  
**설명:** 추가로 /tmp 디렉토리 사용 발견

```bash
ls -la > /tmp/before_download.txt
ls -la > /tmp/after_download.txt
```

**권장 조치:**
- 프로젝트 전용 임시 디렉토리 사용
- 작업 완료 후 자동 정리

## 🔧 즉시 조치 필요 항목 (Critical)

### 1. 명령어 인젝션 방지
```python
# 현재 (위험)
cmd = f"sqlplus -S {ORACLE_CONNECTION} @{temp_file_path}"
result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

# 개선 (안전)
import shlex
cmd = ["sqlplus", "-S", ORACLE_CONNECTION, f"@{temp_file_path}"]
# 또는
cmd = f"sqlplus -S {shlex.quote(ORACLE_CONNECTION)} @{shlex.quote(temp_file_path)}"
result = subprocess.run(cmd, shell=False, capture_output=True, text=True)
```

### 2. 하드코딩된 리소스 정보 제거
```bash
# config/oma.properties 수정
# S3_BUCKET=s3://your-bucket-name/analysis/
# VPC_CIDR=10.x.x.x/24  # 실제 환경에 맞게 설정
```

### 3. 백업 파일 정리
```bash
# .gitignore 추가
echo "*.backup" >> .gitignore
echo "*.bak" >> .gitignore
echo "*.tmp" >> .gitignore
echo "*~" >> .gitignore

# 기존 백업 파일 제거
find . -name "*.backup" -delete
```

## 📊 보안 개선 우선순위

### 🚨 즉시 (24시간 내)
1. **명령어 인젝션 수정** - subprocess.run의 shell=True 제거
2. **sudo 권한 상승 로직 수정** - 사용자 승인 절차 추가
3. **하드코딩된 S3 버킷명 환경변수화**

### ⚠️ 단기 (1주일 내)
1. **백업 파일 정리 및 .gitignore 업데이트**
2. **네트워크 정보 일반화**
3. **임시 파일 보안 강화**

### 📋 중기 (1개월 내)
1. **입력 검증 로직 강화**
2. **로깅 보안 정책 수립**
3. **보안 테스트 자동화**

## 🛡️ 보안 강화 코드 예시

### 1. 안전한 subprocess 사용
```python
import subprocess
import shlex
from pathlib import Path

def safe_execute_sql(connection_string, sql_file_path):
    """안전한 SQL 실행"""
    # 입력 검증
    if not Path(sql_file_path).exists():
        raise FileNotFoundError(f"SQL file not found: {sql_file_path}")
    
    # 명령어 배열로 구성 (shell=False)
    cmd = [
        "sqlplus", "-S", 
        connection_string, 
        f"@{sql_file_path}"
    ]
    
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=300,  # 5분 타임아웃
            check=False
        )
        return result
    except subprocess.TimeoutExpired:
        raise TimeoutError("SQL execution timed out")
```

### 2. 안전한 임시 파일 생성
```python
import tempfile
import os
from pathlib import Path

def create_secure_temp_file(content, suffix='.sql'):
    """보안이 강화된 임시 파일 생성"""
    # 프로젝트 전용 임시 디렉토리
    temp_dir = Path.cwd() / 'temp'
    temp_dir.mkdir(mode=0o700, exist_ok=True)
    
    # 보안 임시 파일 생성
    with tempfile.NamedTemporaryFile(
        mode='w+', 
        suffix=suffix,
        dir=temp_dir,
        delete=False
    ) as temp_file:
        temp_file.write(content)
        temp_file.flush()
        
        # 파일 권한을 600으로 제한
        os.chmod(temp_file.name, 0o600)
        
        return temp_file.name
```

### 3. 환경 변수 검증 강화
```python
import os
import re

def validate_environment_secure():
    """강화된 환경 변수 검증"""
    required_vars = {
        'ORACLE_HOST': r'^[a-zA-Z0-9.-]+$',  # 호스트명 패턴
        'ORACLE_PORT': r'^\d{1,5}$',         # 포트 번호
        'ORACLE_SID': r'^[a-zA-Z0-9_]+$',    # SID 패턴
    }
    
    for var_name, pattern in required_vars.items():
        value = os.environ.get(var_name)
        if not value:
            raise ValueError(f"Required environment variable {var_name} is not set")
        
        if not re.match(pattern, value):
            raise ValueError(f"Invalid format for {var_name}: {value}")
    
    return True
```

## 📈 보안 점수 재평가

**업데이트된 보안 점수: 65/100**

- 명령어 인젝션 방지: 40/100 (심각한 취약점 발견)
- 민감정보 관리: 55/100 (추가 노출 발견)
- 접근 제어: 70/100 (sudo 사용 이슈)
- 데이터 보호: 65/100 (백업 파일 노출)
- 코드 보안: 75/100 (일부 개선 필요)

## 🎯 보안 개선 로드맵

### Phase 1: 긴급 수정 (1주일)
- [ ] subprocess.run shell=True 제거
- [ ] sudo 권한 상승 로직 수정
- [ ] 하드코딩된 리소스 정보 환경변수화

### Phase 2: 보안 강화 (1개월)
- [ ] 입력 검증 로직 추가
- [ ] 임시 파일 보안 개선
- [ ] 백업 파일 정리

### Phase 3: 보안 정책 (3개월)
- [ ] 보안 코딩 가이드라인 수립
- [ ] 자동화된 보안 테스트 도입
- [ ] 정기 보안 점검 프로세스 구축

## 📞 긴급 연락처

심각한 보안 취약점이 발견되었으므로 즉시 개발팀과 보안팀에 알려주시기 바랍니다.

---

**⚠️ 중요:** 이번 2차 점검에서 명령어 인젝션 등 심각한 보안 취약점이 발견되었습니다. 즉시 조치가 필요합니다.
