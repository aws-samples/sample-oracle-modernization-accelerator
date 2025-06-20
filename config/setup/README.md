# OMABox EC2 Instance Deployment

이 프로젝트는 Oracle Modernization Accelerator (OMA)를 위한 EC2 인스턴스를 AWS CloudFormation을 통해 배포합니다.

## 🚀 빠른 시작

### 1. 사전 요구사항 확인
```bash
# AWS CLI 설치 및 설정 확인
aws --version
aws sts get-caller-identity
```

### 2. 스크립트 실행 권한 부여
```bash
chmod +x deploy-omabox.sh
chmod +x cleanup-omabox.sh
```

### 3. 배포 실행
```bash
# 단계별 배포 시작
./deploy-omabox.sh

# 1단계: AWS Region 선택 → 옵션 1 (Secrets Manager 설정)
# 2단계: 다시 실행 → 옵션 2 (CloudFormation 배포)
```

## 📋 파일 구성

- `omabox-cloudformation.yaml`: CloudFormation 템플릿
- `deploy-omabox.sh`: 배포 스크립트
- `cleanup-omabox.sh`: 정리 스크립트
- `README.md`: 사용법 가이드

## 📋 사전 요구사항

### 필수 소프트웨어
- **AWS CLI v2**: [설치 가이드](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- **Bash Shell**: 배포 스크립트 실행용

### AWS 계정 요구사항
- **AWS 계정**: 활성화된 AWS 계정
- **IAM 권한**: 다음 서비스들에 대한 관리 권한
  - CloudFormation (전체)
  - EC2 (전체)
  - IAM (역할 생성/관리)
  - Secrets Manager (전체)
  - RDS/Aurora (전체)
  - DMS (전체)
  - VPC (관리)
  - KMS (키 생성/관리)

### Oracle 데이터베이스 정보
배포 전에 다음 Oracle DB 정보를 준비하세요:
- **호스트명/IP**: Oracle DB 서버 주소
- **포트**: 기본값 1521
- **SID 또는 Service Name**: 데이터베이스 식별자
- **관리자 계정**: Username/Password (DBA 권한)
- **서비스 계정**: Username/Password (일반 사용자)

### Amazon Q 사용 권한
- **Amazon Q 액세스**: AWS 계정에서 Amazon Q 서비스 활성화 필요
- **Bedrock 모델 액세스**: Claude 4 등 AI 모델 사용 권한

## ✅ 배포 전 체크리스트

배포하기 전에 다음 사항들을 확인하세요:

- [ ] AWS CLI가 설치되고 올바르게 설정되어 있음
- [ ] AWS 계정에 필요한 IAM 권한이 있음
- [ ] Oracle 데이터베이스 연결 정보를 준비함
- [ ] Amazon Q 서비스 사용 권한이 있음
- [ ] 배포할 AWS 리전을 결정함
- [ ] 예상 비용을 검토함 (월 약 $505)
- [ ] 스크립트 파일에 실행 권한을 부여함

## 배포 방법

### 1. 단계별 배포 스크립트 실행

배포는 2단계로 나누어져 있습니다:

```bash
./deploy-omabox.sh
```

#### 단계 1: Secrets Manager 설정
먼저 AWS Region을 선택한 후, **옵션 1**을 선택하여 데이터베이스 자격증명을 설정합니다.

**입력 정보:**
1. **Oracle Admin 자격증명**:
   - Username, Password
   - Host, Port (기본값: 1521)
   - SID/Service Name

2. **Oracle Service 자격증명**:
   - Username, Password
   - (Host, Port, SID는 Admin과 동일)

3. **PostgreSQL Credentials (for Aurora PostgreSQL)**:
   - Username, Password
   - Database Name (기본값: postgres)
   - Host는 Aurora 배포 후 자동으로 설정됩니다

4. **PostgreSQL Service Credentials**:
   - Username, Password
   - (Host, Port, Database는 Admin과 동일)

#### 단계 2: CloudFormation 인프라 배포
다시 스크립트를 실행하고 **옵션 2**를 선택하여 AWS 인프라를 배포합니다.

```bash
./deploy-omabox.sh
# AWS Region 선택 후 옵션 2 선택
```

> **참고**: 
> - 단계 1에서 AWS Secrets Manager에 4개의 시크릿이 생성됩니다
> - 단계 2에서 Aurora 배포 완료 후 PostgreSQL 시크릿이 실제 Aurora 엔드포인트로 자동 업데이트됩니다

### 2. 수동 배포 (AWS CLI 사용)

```bash
aws cloudformation deploy \
    --template-file omabox-cloudformation.yaml \
    --stack-name omabox-stack \
    --parameter-overrides \
        VpcId=vpc-xxxxxxxxx \
        SubnetId=subnet-xxxxxxxxx \
    --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
    --region us-east-1
```

## 생성되는 리소스

### 네트워크 인프라
- **VPC**: OMA_VPC (10.255.255.0/24)
- **Public Subnets**: 2개 (EC2, VPC Endpoints용)
- **Private Subnets**: 2개 (Aurora, DMS용)
- **Internet Gateway**: 인터넷 연결
- **NAT Gateway**: Private 서브넷 인터넷 접근
- **Route Tables**: Public/Private 라우팅

### EC2 인스턴스
- **인스턴스 타입**: m6i.xlarge
- **AMI**: Amazon Linux 2023
- **이름**: OMABox
- **위치**: Private Subnet (보안 강화, SSM으로 접근)

### Aurora PostgreSQL (Target Database)
- **엔진**: Aurora PostgreSQL 15.7
- **인스턴스 클래스**: db.r6g.large
- **암호화**: KMS 키로 암호화
- **백업**: 7일 보존
- **위치**: Private Subnets

### DMS (Database Migration Service)
- **Replication Instance**: dms.t3.medium
- **Target Endpoint**: Aurora PostgreSQL 연결
- **Subnet Group**: Private Subnets 사용
- **위치**: Private Subnets

### IAM 역할 및 정책
- SSM 연결을 위한 IAM 역할
- Secrets Manager 접근 권한
- CloudWatch 에이전트 권한
- DMS VPC 관리 권한
- DMS CloudWatch Logs 권한

### 보안 그룹
- **EC2 인스턴스용**: 아웃바운드 트래픽만 허용
- **VPC Endpoints용**: EC2에서 HTTPS(443) 접근 허용
- **데이터베이스용**: EC2에서 PostgreSQL(5432) 접근 허용, DMS 간 통신 허용

### VPC Endpoints
Private subnet에서 인터넷 없이 AWS 서비스 접근을 위해 다음 VPC Endpoints를 생성:
- **SSM**: Systems Manager 서비스 접근
- **SSM Messages**: Session Manager 통신
- **EC2 Messages**: EC2 메시지 서비스
- **Secrets Manager**: 데이터베이스 자격증명 접근

### 설치되는 소프트웨어
- AWS CLI v2
- Amazon Q CLI
- Oracle Instant Client 19.26
- PostgreSQL 15 클라이언트
- pg_get_tabledef 도구
- 기타 유틸리티 (unzip, wget, jq)

## 인스턴스 연결

배포 완료 후 AWS Systems Manager Session Manager를 통해 연결:

### macOS에서 Session Manager 접속

#### 1. Session Manager Plugin 설치

```bash
# Homebrew를 사용한 설치 (권장)
brew install --cask session-manager-plugin

# 또는 수동 설치
curl "https://s3.amazonaws.com/session-manager-downloads/plugin/latest/mac_arm64/sessionmanager-bundle.zip" -o "sessionmanager-bundle.zip"
unzip sessionmanager-bundle.zip
sudo ./sessionmanager-bundle/install -i /usr/local/sessionmanagerplugin -b /usr/local/bin/session-manager-plugin

# Intel Mac의 경우
curl "https://s3.amazonaws.com/session-manager-downloads/plugin/latest/mac/sessionmanager-bundle.zip" -o "sessionmanager-bundle.zip"
```

#### 2. 설치 확인

```bash
session-manager-plugin
```

성공적으로 설치되면 Session Manager plugin 정보가 출력됩니다.

#### 3. EC2 인스턴스 접속

```bash
# 기본 접속 방법
aws ssm start-session --target i-xxxxxxxxx --region us-east-1

# 특정 프로필 사용
aws ssm start-session --target i-xxxxxxxxx --region us-east-1 --profile your-profile

# 인스턴스 ID 자동 조회 후 접속
INSTANCE_ID=$(aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=OMABox" "Name=instance-state-name,Values=running" \
    --query "Reservations[0].Instances[0].InstanceId" \
    --output text \
    --region us-east-1)

aws ssm start-session --target $INSTANCE_ID --region us-east-1
```

#### 4. 접속 문제 해결

**Session Manager Plugin을 찾을 수 없는 경우:**
```bash
# PATH 확인
echo $PATH

# 수동으로 PATH 추가 (필요시)
export PATH=$PATH:/usr/local/bin

# .zshrc 또는 .bash_profile에 영구 추가
echo 'export PATH=$PATH:/usr/local/bin' >> ~/.zshrc
source ~/.zshrc
```

**AWS CLI 권한 문제:**
```bash
# AWS 자격증명 확인
aws sts get-caller-identity

# 필요한 IAM 권한:
# - ssm:StartSession
# - ssm:TerminateSession
# - ssm:ResumeSession
# - ssm:DescribeSessions
# - ec2:DescribeInstances
```

**인스턴스가 Session Manager에 나타나지 않는 경우:**
- EC2 인스턴스에 SSM Agent가 설치되어 있는지 확인
- 인스턴스에 적절한 IAM 역할이 연결되어 있는지 확인
- 인스턴스가 실행 중인지 확인

#### 5. 유용한 Session Manager 명령어

```bash
# 활성 세션 목록 확인
aws ssm describe-sessions --region us-east-1

# 특정 세션 종료
aws ssm terminate-session --session-id s-xxxxxxxxx --region us-east-1

# 포트 포워딩 (예: PostgreSQL)
aws ssm start-session \
    --target i-xxxxxxxxx \
    --document-name AWS-StartPortForwardingSession \
    --parameters '{"portNumber":["5432"],"localPortNumber":["5432"]}' \
    --region us-east-1
```

인스턴스 ID는 배포 완료 후 출력됩니다.

## Amazon Q CLI 설정 (배포 후 필수)

인스턴스에 접속한 후 Amazon Q CLI를 설정해야 합니다:

### 1. Amazon Q 로그인

```bash
# Amazon Q에 로그인 (기본 프로필)
q login

# 특정 프로필로 로그인
q login --profile work
```

**로그인 과정:**
1. 명령 실행 시 브라우저 URL이 표시됩니다
2. 해당 URL을 복사하여 로컬 브라우저에서 열기
3. AWS 계정으로 로그인
4. Amazon Q 사용 권한 승인
5. 터미널에서 로그인 완료 확인

### 2. 사용 가능한 모델 확인

```bash
# 계정에서 사용 가능한 모델 목록 확인
q configure list-models
```

**주요 모델들:**
- `anthropic.claude-4` - 가장 강력한 모델 (추천)
- `anthropic.claude-3-5-sonnet-20241022-v2:0` - 고성능 모델
- `anthropic.claude-3-haiku-20240307-v1:0` - 빠르고 경제적인 모델
- `amazon.nova-pro-v1:0` - AWS의 자체 모델
- `amazon.nova-lite-v1:0` - 가벼운 AWS 모델

### 3. 기본 모델 설정

```bash
# 추천: Claude 4 (가장 성능이 좋음)
q configure set model anthropic.claude-4

# 고성능 옵션: Claude 3.5 Sonnet
q configure set model anthropic.claude-3-5-sonnet-20241022-v2:0

# 경제적 옵션: Claude 3 Haiku
q configure set model anthropic.claude-3-haiku-20240307-v1:0

# AWS 모델 사용
q configure set model amazon.nova-pro-v1:0
```

### 4. 설정 확인 및 테스트

```bash
# 현재 설정 확인
q configure list

# 로그인 상태 확인
q auth status

# Amazon Q 채팅 테스트
q chat
```

**채팅 테스트 예시:**
```bash
q chat
> Hello, can you help me with Oracle to PostgreSQL migration?
> /quit  # 채팅 종료
```

### 5. 고급 설정 옵션

```bash
# AWS 리전 설정 (선택사항)
q configure set region us-east-1

# 프로필별 다른 모델 설정
q configure set model anthropic.claude-4 --profile production
q configure set model anthropic.claude-3-haiku-20240307-v1:0 --profile development

# 특정 프로필로 채팅 시작
q chat --profile production
```

### 6. 설정 파일 위치

```bash
# Amazon Q 설정 파일들 확인
ls -la ~/.aws/q/

# 설정 내용 확인
cat ~/.aws/q/config
```

### 7. 문제 해결

**로그인 문제:**
```bash
# 로그아웃 후 재로그인
q auth logout
q login

# 캐시 클리어
rm -rf ~/.aws/q/cache/
```

**권한 문제:**
- AWS 계정에 Amazon Q 액세스 권한이 필요합니다
- AWS 관리자에게 Amazon Q 서비스 활성화를 요청하세요
- IAM 사용자의 경우 적절한 Amazon Q 정책이 필요합니다

### 8. OMA 작업에서 Amazon Q 활용

```bash
# Oracle 스키마 분석 도움 요청
q chat
> I need help analyzing Oracle database schema for PostgreSQL migration

# SQL 변환 도움
q chat
> Can you help convert this Oracle PL/SQL to PostgreSQL function?

# 마이그레이션 전략 문의
q chat
> What's the best approach for migrating Oracle stored procedures to PostgreSQL?
```

> **💡 팁**: Amazon Q CLI는 컨텍스트를 유지하므로 긴 대화를 통해 복잡한 마이그레이션 문제를 단계별로 해결할 수 있습니다.

## 환경 변수

인스턴스에는 다음 환경 변수들이 자동으로 설정됩니다:

### Oracle 환경
- `ORACLE_HOME`: Oracle Instant Client 경로
- `ORACLE_SID`: Oracle 데이터베이스 SID
- `ORACLE_ADM_USER`: Oracle 관리자 사용자
- `ORACLE_ADM_PASSWORD`: Oracle 관리자 비밀번호
- `ORACLE_SVC_USER`: Oracle 서비스 사용자
- `ORACLE_SVC_PASSWORD`: Oracle 서비스 비밀번호

### PostgreSQL 환경 (Aurora 기반)
- `PGHOST`: Aurora PostgreSQL 엔드포인트 (자동 설정)
- `PGDATABASE`: PostgreSQL 데이터베이스명
- `PGPORT`: PostgreSQL 포트 (5432)
- `PGUSER`: PostgreSQL 사용자
- `PGPASSWORD`: PostgreSQL 비밀번호

### OMA 환경
- `OMA_HOME`: OMA 홈 디렉토리
- `DB_ASSESSMENTS_FOLDER`: Assessment 디렉토리
- `OMA_TEST`: Test 디렉토리
- `OMA_TRANSFORM`: Transform 디렉토리

## 필요한 Secrets Manager 시크릿

다음 시크릿들이 AWS Secrets Manager에 존재해야 합니다:
- `oma-secret-oracle-admin`: Oracle 관리자 자격증명
- `oma-secret-oracle-service`: Oracle 서비스 자격증명
- `oma-secret-postgres-admin`: PostgreSQL 관리자 자격증명 (Aurora 엔드포인트 포함)
- `oma-secret-postgres-service`: PostgreSQL 서비스 자격증명 (Aurora 엔드포인트 포함)

> **참고**: PostgreSQL 시크릿은 배포 스크립트에서 생성되며, Aurora 배포 완료 후 자동으로 Aurora 엔드포인트 정보로 업데이트됩니다.

## 배포 후 필수 작업 (POST-DEPLOYMENT)

CloudFormation 배포 완료 후 다음 설정들이 **반드시** 필요합니다.

### 0. Amazon Q CLI 로그인 설정

EC2 인스턴스에 접속한 후 Amazon Q CLI 로그인을 먼저 설정합니다.

```bash
# EC2 인스턴스 접속
aws ssm start-session --target i-xxxxxxxxx --region us-east-1

# 인스턴스 내부에서 Amazon Q 로그인
q login

# 사용 가능한 모델 확인
q configure list-models

# 기본 모델 설정 (Claude 4 권장)
q configure set model anthropic.claude-4

# 설정 확인
q configure list

# 로그인 상태 확인
q auth status

# 테스트
q chat
> Hello, can you help me with Oracle to PostgreSQL migration?
> /quit
```

**로그인 과정:**
1. `q login` 명령 실행 시 브라우저 URL이 표시됩니다
2. 해당 URL을 복사하여 로컬 브라우저에서 열기
3. AWS 계정으로 로그인
4. Amazon Q 사용 권한 승인
5. 터미널에서 로그인 완료 확인

> **💡 팁**: Amazon Q CLI 로그인은 OMA 작업 전반에서 AI 지원을 받기 위해 필수적입니다. Oracle 스키마 분석, SQL 변환, 마이그레이션 전략 수립 등에 활용할 수 있습니다.

### 1. VPC Peering 설정

Oracle 데이터베이스 VPC와 OMA VPC 간 연결을 설정합니다.

```bash
# 1. VPC Peering Connection 생성
aws ec2 create-vpc-peering-connection \
    --vpc-id vpc-xxxxxxxxx \  # OMA VPC ID (CloudFormation 출력 확인)
    --peer-vpc-id vpc-yyyyyyyyy \  # Oracle DB VPC ID
    --region us-east-1

# 2. Peering Connection 수락
aws ec2 accept-vpc-peering-connection \
    --vpc-peering-connection-id pcx-xxxxxxxxx \
    --region us-east-1

# 3. Route Table 업데이트 (양방향)
# OMA VPC → Oracle DB VPC
aws ec2 create-route \
    --route-table-id rtb-xxxxxxxxx \  # OMA Private Route Table
    --destination-cidr-block 10.0.0.0/16 \  # Oracle DB VPC CIDR
    --vpc-peering-connection-id pcx-xxxxxxxxx

# Oracle DB VPC → OMA VPC  
aws ec2 create-route \
    --route-table-id rtb-yyyyyyyyy \  # Oracle DB Route Table
    --destination-cidr-block 10.255.255.0/24 \  # OMA VPC CIDR
    --vpc-peering-connection-id pcx-xxxxxxxxx
```

### 2. Oracle 데이터베이스 보안 그룹 설정

Oracle DB 보안 그룹에 OMA 리소스 접근을 허용합니다.

```bash
# Oracle DB 보안 그룹에 규칙 추가
aws ec2 authorize-security-group-ingress \
    --group-id sg-oracle-database \  # Oracle DB Security Group ID
    --protocol tcp \
    --port 1521 \
    --cidr 10.255.255.0/24 \  # OMA VPC CIDR
    --region us-east-1
```

### 3. 연결 테스트

```bash
# EC2 인스턴스에서 Oracle 연결 테스트
aws ssm start-session --target i-xxxxxxxxx --region us-east-1

# 인스턴스 내부에서 실행
sqlplus username/password@hostname:1521/SID
# 또는
telnet hostname 1521
```

> **⚠️ 중요**: 이 네트워크 설정 없이는 EC2 인스턴스와 DMS가 Oracle 데이터베이스에 접근할 수 없습니다.

## 정리

리소스를 삭제하려면:

```bash
./cleanup-omabox.sh
```

정리 스크립트는 다음을 수행합니다:
- CloudFormation 스택 삭제 (EC2, Aurora, DMS, IAM 역할, 보안 그룹, VPC Endpoints, KMS 키)
- 선택적으로 Secrets Manager 시크릿 삭제 (사용자 확인 후)

또는 수동으로:

```bash
# CloudFormation 스택 삭제
aws cloudformation delete-stack --stack-name omabox-stack --region us-east-1

# Secrets Manager 시크릿 삭제 (선택사항)
aws secretsmanager delete-secret --secret-id oma-secret-oracle-admin --force-delete-without-recovery --region us-east-1
aws secretsmanager delete-secret --secret-id oma-secret-oracle-service --force-delete-without-recovery --region us-east-1
aws secretsmanager delete-secret --secret-id oma-secret-postgres-admin --force-delete-without-recovery --region us-east-1
aws secretsmanager delete-secret --secret-id oma-secret-postgres-service --force-delete-without-recovery --region us-east-1
```

## 주의사항

- VPC Endpoints를 통해 private subnet에서도 SSM 접근이 가능합니다
- NAT Gateway를 통해 private subnet에서 인터넷 접근이 가능합니다 (소프트웨어 다운로드용)
- m6i.xlarge 인스턴스는 시간당 요금이 발생하므로 사용하지 않을 때는 중지하거나 삭제하시기 바랍니다
- Aurora PostgreSQL과 DMS 리소스도 시간당 요금이 발생합니다
- NAT Gateway와 VPC Endpoints도 시간당 요금이 발생합니다
- Aurora는 자동으로 백업이 설정되어 있으며, 7일간 보존됩니다

## 예상 월간 비용 (US East 1 기준)

다음은 CloudFormation으로 배포되는 리소스들의 **1개월(30일) 24시간 운영** 기준 예상 비용입니다:

### 주요 컴퓨팅 리소스
- **EC2 m6i.xlarge**: ~$116/월 (4 vCPU, 16GB RAM)
- **Aurora PostgreSQL db.r6g.large**: ~$146/월 (Writer 인스턴스)
- **DMS dms.t3.medium**: ~$146/월 (Replication Instance)

### 네트워크 리소스
- **NAT Gateway**: ~$32/월 (시간당 요금) + 데이터 처리 비용
- **VPC Endpoints (4개)**: ~$29/월 ($7.2/월 × 4개)

### 스토리지 및 기타
- **Aurora 스토리지**: ~$23/월 (100GB 기준, 실제 사용량에 따라 변동)
- **Aurora 백업**: ~$5/월 (추가 백업 스토리지 기준)
- **EBS 볼륨 (EC2)**: ~$8/월 (gp3 80GB)

### **총 예상 비용: 약 $505/월**

> **⚠️ 중요 비용 절약 팁:**
> - **EC2 인스턴스 중지**: 사용하지 않을 때 EC2를 중지하면 월 $116 절약
> - **Aurora 일시 중지**: 7일까지 Aurora를 일시 중지할 수 있어 월 $146 절약 가능
> - **DMS 삭제**: 마이그레이션 완료 후 DMS 인스턴스 삭제로 월 $146 절약
> - **개발/테스트 환경**: 업무 시간(8시간)만 운영 시 약 70% 비용 절약 가능

### 비용 최적화 권장사항

1. **단계별 리소스 관리**:
   ```bash
   # EC2 인스턴스 중지 (컴퓨팅 비용 절약)
   aws ec2 stop-instances --instance-ids i-xxxxxxxxx
   
   # Aurora 클러스터 일시 중지 (최대 7일)
   aws rds stop-db-cluster --db-cluster-identifier omabox-aurora-cluster
   ```

2. **사용 패턴별 운영**:
   - **개발/테스트**: 업무시간만 운영 → 월 $180-250
   - **POC/데모**: 필요시에만 운영 → 월 $50-100
   - **프로덕션**: 24시간 운영 → 월 $505

3. **정확한 비용 계산**:
   - [AWS Pricing Calculator](https://calculator.aws)에서 정확한 견적 확인
   - AWS Cost Explorer로 실제 사용 비용 모니터링
   - CloudWatch 알람으로 예산 초과 방지

> **참고**: 위 비용은 US East 1 리전 기준이며, 실제 비용은 사용 패턴, 데이터 전송량, 스토리지 사용량에 따라 달라질 수 있습니다.
