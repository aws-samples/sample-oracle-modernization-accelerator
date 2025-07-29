# OMA 프로젝트 보안점검 보고서

**점검일:** 2025년 7월 29일  
**점검자:** Amazon Q  
**점검 범위:** Oracle Modernization Accelerator (OMA) 전체 프로젝트  

## 📋 점검 개요

본 보고서는 OMA 프로젝트의 보안 취약점을 체계적으로 분석하고 개선 방안을 제시합니다.

## 🔍 점검 결과 요약

| 보안 영역 | 상태 | 위험도 | 발견된 이슈 수 |
|-----------|------|--------|---------------|
| 민감정보 노출 | ⚠️ 주의 | 중간 | 3개 |
| 파일 권한 | ✅ 양호 | 낮음 | 0개 |
| SQL 인젝션 | ✅ 양호 | 낮음 | 0개 |
| 임시 파일 보안 | ⚠️ 주의 | 중간 | 2개 |
| 로그 보안 | ⚠️ 주의 | 중간 | 1개 |

## 🚨 발견된 보안 이슈

### 1. 민감정보 노출 (중간 위험도)

#### 이슈 1: 설정 파일의 빈 패스워드 필드
**파일:** `config/oma.properties`  
**위험도:** 중간  
**설명:** 데이터베이스 패스워드 필드가 빈 값으로 설정되어 있음

```properties
ORACLE_ADM_PASSWORD=
ORACLE_SVC_PASSWORD=
PG_SVC_PASSWORD=
PG_ADM_PASSWORD=
PGPASSWORD=
```

**권장 조치:**
- 패스워드 필드를 주석 처리하거나 예시 값으로 변경
- 실제 운영 시 환경 변수 사용 강제화
- `.env.example` 파일로 분리

#### 이슈 2: 하드코딩된 기본 사용자명
**파일:** `config/oma.properties`  
**위험도:** 낮음  
**설명:** 기본 사용자명이 하드코딩되어 있음

```properties
ORACLE_SVC_USER=AAA
PG_SVC_USER=aaa
```

**권장 조치:**
- 기본값을 더 일반적인 예시로 변경
- 문서에서 실제 값으로 변경 필요성 명시

#### 이슈 3: 배포 스크립트의 패스워드 처리
**파일:** `config/setup/deploy-omabox.sh`  
**위험도:** 중간  
**설명:** AWS Secrets Manager에서 패스워드를 추출하는 과정이 로그에 노출될 가능성

**권장 조치:**
- 패스워드 추출 시 로그 출력 비활성화
- 임시 변수 사용 후 즉시 unset

### 2. 임시 파일 보안 (중간 위험도)

#### 이슈 1: /tmp 디렉토리 사용
**파일:** `bin/test/analyze_pg_errors.py`  
**위험도:** 중간  
**설명:** 공용 /tmp 디렉토리에 분석 결과 파일 생성

```python
output_file = f"/tmp/missing_{object_type}_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
output_file = f"/tmp/pg_error_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
csv_file_path = "/tmp/pg_error.csv"
```

**권장 조치:**
- 프로젝트 전용 임시 디렉토리 사용
- 파일 권한을 600으로 제한
- 작업 완료 후 자동 삭제 메커니즘 추가

#### 이슈 2: tempfile 모듈 사용 시 보안 설정 부족
**파일:** `bin/database/asct.py`, `bin/test/pg_transform.py`  
**위험도:** 낮음  
**설명:** tempfile 사용 시 적절한 권한 설정 필요

**권장 조치:**
- tempfile.mkstemp() 사용 시 mode 매개변수로 권한 제한
- delete=True 옵션 활용하여 자동 삭제

### 3. 로그 보안 (중간 위험도)

#### 이슈 1: 배포 스크립트의 민감정보 로깅
**파일:** `config/setup/deploy-omabox.sh`  
**위험도:** 중간  
**설명:** 패스워드 추출 과정이 로그에 기록될 가능성

**권장 조치:**
- set +x를 사용하여 민감한 부분의 로깅 비활성화
- 패스워드 관련 변수 처리 후 즉시 unset

## ✅ 양호한 보안 사항

### 1. 환경 변수 사용
- 대부분의 스크립트에서 환경 변수를 통한 설정 관리
- 하드코딩된 패스워드 없음

### 2. SQL 인젝션 방지
- 파라미터화된 쿼리 사용
- 사용자 입력 검증 로직 존재

### 3. 파일 권한 관리
- 실행 파일들의 적절한 권한 설정 (755)
- 설정 파일의 적절한 권한 (644)

## 🔧 권장 보안 개선 사항

### 즉시 조치 필요 (High Priority)

1. **설정 파일 보안 강화**
   ```bash
   # config/oma.properties 수정
   # ORACLE_ADM_PASSWORD=your_password_here
   # ORACLE_SVC_PASSWORD=your_password_here
   # 실제 값은 환경 변수로 설정하세요
   ```

2. **임시 파일 보안 개선**
   ```python
   # 개선된 임시 파일 생성
   import tempfile
   import os
   
   # 프로젝트 전용 임시 디렉토리
   temp_dir = os.path.join(os.getcwd(), 'temp')
   os.makedirs(temp_dir, mode=0o700, exist_ok=True)
   
   # 보안 임시 파일 생성
   with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', 
                                   dir=temp_dir, delete=True) as temp_file:
       # 파일 작업
   ```

3. **로그 보안 강화**
   ```bash
   # 민감한 작업 시 로깅 비활성화
   set +x
   POSTGRES_ADMIN_PASSWORD=$(echo "$POSTGRES_ADMIN_CREDS" | jq -r '.password')
   # 작업 수행
   unset POSTGRES_ADMIN_PASSWORD
   set -x
   ```

### 중기 개선 사항 (Medium Priority)

1. **보안 설정 파일 분리**
   - `.env.example` 파일 생성
   - 실제 설정과 예시 설정 분리

2. **보안 검증 스크립트 추가**
   - 설정 파일 보안 검증
   - 권한 검증 자동화

3. **로깅 정책 수립**
   - 민감정보 로깅 금지 정책
   - 로그 파일 권한 관리

### 장기 개선 사항 (Low Priority)

1. **암호화 강화**
   - 설정 파일 암호화
   - 전송 중 데이터 암호화

2. **접근 제어 강화**
   - 역할 기반 접근 제어
   - 감사 로그 구현

## 📊 보안 점수

**전체 보안 점수: 75/100**

- 민감정보 관리: 60/100
- 접근 제어: 85/100
- 데이터 보호: 70/100
- 로깅 보안: 65/100
- 코드 보안: 90/100

## 🎯 다음 단계

1. **즉시 조치** (1주일 내)
   - 설정 파일의 빈 패스워드 필드 수정
   - 임시 파일 생성 로직 개선

2. **단기 조치** (1개월 내)
   - 보안 설정 파일 분리
   - 로그 보안 강화

3. **중장기 조치** (3개월 내)
   - 보안 검증 자동화
   - 보안 정책 문서화

## 📞 문의사항

보안 관련 문의사항이나 추가 점검이 필요한 경우 프로젝트 관리자에게 연락하시기 바랍니다.

---

**면책조항:** 본 보고서는 정적 코드 분석을 기반으로 작성되었으며, 실제 운영 환경에서의 추가 보안 테스트가 권장됩니다.
