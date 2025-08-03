#!/bin/bash

# OMA Box 향상된 배포 스크립트
# 기존 deploy-omabox.sh의 모든 기능을 포함하면서 타겟 DB에 따라 CloudFormation 템플릿 자동 선택

# Disable AWS CLI pager for cleaner output
export AWS_PAGER=""

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수들
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 스크립트 디렉토리 설정
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="${SCRIPT_DIR}"

# 함수: 사용법 출력
usage() {
    echo "사용법: $0 [옵션]"
    echo ""
    echo "옵션:"
    echo "  -h, --help          이 도움말을 표시합니다"
    echo "  -r, --region        AWS 리전 (기본값: ap-northeast-2)"
    echo "  -d, --database      타겟 데이터베이스 (postgres|mysql)"
    echo "  -o, --option        실행 옵션 (1: Secrets 설정, 2: CloudFormation 배포)"
    echo ""
    echo "예시:"
    echo "  $0                                    # 대화형 모드"
    echo "  $0 --region us-west-2 --database postgres --option 1"
    echo "  $0 -r ap-northeast-2 -d mysql -o 2"
}

# Function to setup secrets
setup_secrets() {
    echo ""
    log_info "=== Creating Secrets Manager Secrets ==="
    echo "Please provide database credentials for the secrets:"
    echo ""

    # Oracle Admin Credentials
    echo "1. Oracle Admin Credentials:"
    read -p "Enter Oracle Admin Username: " ORACLE_ADMIN_USER
    read -s -p "Enter Oracle Admin Password: " ORACLE_ADMIN_PASSWORD
    echo ""
    read -p "Enter Oracle Host (e.g., oracle.example.com): " ORACLE_HOST
    read -p "Enter Oracle Port [1521]: " ORACLE_PORT
    ORACLE_PORT=${ORACLE_PORT:-1521}
    read -p "Enter Oracle SID/Service Name: " ORACLE_SID
    echo ""

    # Oracle Service Credentials
    echo "2. Oracle Service Credentials:"
    read -p "Enter Oracle Service Username: " ORACLE_SERVICE_USER
    read -s -p "Enter Oracle Service Password: " ORACLE_SERVICE_PASSWORD
    echo ""
    echo ""

    # Target Database Credentials (will be updated with Aurora info after deployment)
    if [ "$TARGET_DB" = "postgres" ]; then
        echo "3. PostgreSQL Credentials (for Aurora PostgreSQL):"
        echo "Note: Aurora endpoint will be automatically configured after deployment"
        read -p "Enter PostgreSQL Admin Username [postgres]: " TARGET_ADMIN_USER
        TARGET_ADMIN_USER=${TARGET_ADMIN_USER:-postgres}
        read -s -p "Enter PostgreSQL Admin Password: " TARGET_ADMIN_PASSWORD
        echo ""
        read -p "Enter PostgreSQL Database Name [postgres]: " TARGET_DATABASE
        TARGET_DATABASE=${TARGET_DATABASE:-postgres}
        TARGET_PORT=5432
        TARGET_SECRET_PREFIX="postgres"
        TARGET_DB_NAME="PostgreSQL"
        echo ""

        # PostgreSQL Service Credentials
        echo "4. PostgreSQL Service Credentials:"
        read -p "Enter PostgreSQL Service Username [pguser]: " TARGET_SERVICE_USER
        TARGET_SERVICE_USER=${TARGET_SERVICE_USER:-pguser}
        read -s -p "Enter PostgreSQL Service Password: " TARGET_SERVICE_PASSWORD
    else
        echo "3. MySQL Credentials (for Aurora MySQL):"
        echo "Note: Aurora endpoint will be automatically configured after deployment"
        read -p "Enter MySQL Admin Username [admin]: " TARGET_ADMIN_USER
        TARGET_ADMIN_USER=${TARGET_ADMIN_USER:-admin}
        read -s -p "Enter MySQL Admin Password: " TARGET_ADMIN_PASSWORD
        echo ""
        read -p "Enter MySQL Database Name [mysql]: " TARGET_DATABASE
        TARGET_DATABASE=${TARGET_DATABASE:-mysql}
        TARGET_PORT=3306
        TARGET_SECRET_PREFIX="mysql"
        TARGET_DB_NAME="MySQL"
        echo ""

        # MySQL Service Credentials
        echo "4. MySQL Service Credentials:"
        read -p "Enter MySQL Service Username [mysqluser]: " TARGET_SERVICE_USER
        TARGET_SERVICE_USER=${TARGET_SERVICE_USER:-mysqluser}
        read -s -p "Enter MySQL Service Password: " TARGET_SERVICE_PASSWORD
    fi
    echo ""
    echo ""

    # Create Secrets in AWS Secrets Manager
    log_info "Creating secrets in AWS Secrets Manager..."

    # Oracle Admin Secret
    ORACLE_ADMIN_SECRET=$(cat <<EOF
{
  "username": "$ORACLE_ADMIN_USER",
  "password": "$ORACLE_ADMIN_PASSWORD",
  "host": "$ORACLE_HOST",
  "port": $ORACLE_PORT,
  "sid": "$ORACLE_SID"
}
EOF
)

    aws secretsmanager create-secret \
        --name "oma-secret-oracle-admin" \
        --description "Oracle Admin credentials for OMA" \
        --secret-string "$ORACLE_ADMIN_SECRET" \
        --region $REGION 2>/dev/null || \
    aws secretsmanager update-secret \
        --secret-id "oma-secret-oracle-admin" \
        --secret-string "$ORACLE_ADMIN_SECRET" \
        --region $REGION

    # Oracle Service Secret
    ORACLE_SERVICE_SECRET=$(cat <<EOF
{
  "username": "$ORACLE_SERVICE_USER",
  "password": "$ORACLE_SERVICE_PASSWORD",
  "host": "$ORACLE_HOST",
  "port": $ORACLE_PORT,
  "sid": "$ORACLE_SID"
}
EOF
)

    aws secretsmanager create-secret \
        --name "oma-secret-oracle-service" \
        --description "Oracle Service credentials for OMA" \
        --secret-string "$ORACLE_SERVICE_SECRET" \
        --region $REGION 2>/dev/null || \
    aws secretsmanager update-secret \
        --secret-id "oma-secret-oracle-service" \
        --secret-string "$ORACLE_SERVICE_SECRET" \
        --region $REGION

    # Target Database Admin Secret (placeholder - will be updated after Aurora deployment)
    TARGET_ADMIN_SECRET=$(cat <<EOF
{
  "username": "$TARGET_ADMIN_USER",
  "password": "$TARGET_ADMIN_PASSWORD",
  "host": "placeholder-will-be-updated",
  "port": $TARGET_PORT,
  "database": "$TARGET_DATABASE"
}
EOF
)

    aws secretsmanager create-secret \
        --name "oma-secret-${TARGET_SECRET_PREFIX}-admin" \
        --description "$TARGET_DB_NAME Admin credentials for OMA (Aurora)" \
        --secret-string "$TARGET_ADMIN_SECRET" \
        --region $REGION 2>/dev/null || \
    aws secretsmanager update-secret \
        --secret-id "oma-secret-${TARGET_SECRET_PREFIX}-admin" \
        --secret-string "$TARGET_ADMIN_SECRET" \
        --region $REGION

    # Target Database Service Secret (placeholder - will be updated after Aurora deployment)
    TARGET_SERVICE_SECRET=$(cat <<EOF
{
  "username": "$TARGET_SERVICE_USER",
  "password": "$TARGET_SERVICE_PASSWORD",
  "host": "placeholder-will-be-updated",
  "port": $TARGET_PORT,
  "database": "$TARGET_DATABASE"
}
EOF
)

    aws secretsmanager create-secret \
        --name "oma-secret-${TARGET_SECRET_PREFIX}-service" \
        --description "$TARGET_DB_NAME Service credentials for OMA (Aurora)" \
        --secret-string "$TARGET_SERVICE_SECRET" \
        --region $REGION 2>/dev/null || \
    aws secretsmanager update-secret \
        --secret-id "oma-secret-${TARGET_SECRET_PREFIX}-service" \
        --secret-string "$TARGET_SERVICE_SECRET" \
        --region $REGION

    log_success "Secrets created/updated successfully!"
    echo ""
    echo "📋 Created/Updated Secrets Manager secrets:"
    echo "- oma-secret-oracle-admin"
    echo "- oma-secret-oracle-service"
    echo "- oma-secret-${TARGET_SECRET_PREFIX}-admin (placeholder - will be updated after Aurora deployment)"
    echo "- oma-secret-${TARGET_SECRET_PREFIX}-service (placeholder - will be updated after Aurora deployment)"
    echo ""
    log_info "Next step: Run this script with option 2 to deploy infrastructure"
}

# Function to deploy CloudFormation
deploy_cloudformation() {
    echo ""
    log_info "=== Deploying CloudFormation Stack ==="
    echo "Deploying OMABox with complete infrastructure:"
    echo "Region: $REGION"
    echo "Target Database: $TARGET_DB_NAME"
    echo "VPC: OMA_VPC (10.255.255.0/24)"
    echo "Public Subnets: 2 (for NAT Gateway)"
    echo "Private Subnets: 2 (for EC2, Aurora, DMS, and VPC Endpoints)"
    echo ""

    # Check if secrets exist
    log_info "Checking if required secrets exist..."
    SECRETS_EXIST=true
    
    for SECRET_NAME in "oma-secret-oracle-admin" "oma-secret-oracle-service" "oma-secret-${TARGET_SECRET_PREFIX}-admin" "oma-secret-${TARGET_SECRET_PREFIX}-service"; do
        aws secretsmanager describe-secret --secret-id "$SECRET_NAME" --region $REGION >/dev/null 2>&1
        if [ $? -ne 0 ]; then
            log_error "Secret '$SECRET_NAME' not found!"
            SECRETS_EXIST=false
        fi
    done
    
    if [ "$SECRETS_EXIST" = false ]; then
        echo ""
        log_warning "Required secrets are missing. Please run option 1 first to create secrets."
        exit 1
    fi
    
    log_success "All required secrets found!"
    echo ""

    # Deploy CloudFormation Stack
    STACK_NAME="omabox-stack"

    # Select appropriate CloudFormation template based on target database
    if [ "$TARGET_DB" = "postgres" ]; then
        TEMPLATE_FILE="${CONFIG_DIR}/omabox-cloudformation-apg.yaml"
        log_info "Using PostgreSQL CloudFormation template: omabox-cloudformation-apg.yaml"
    else
        TEMPLATE_FILE="${CONFIG_DIR}/omabox-cloudformation-mysql.yaml"
        log_info "Using MySQL CloudFormation template: omabox-cloudformation-mysql.yaml"
    fi

    # Check if template file exists
    if [[ ! -f "$TEMPLATE_FILE" ]]; then
        log_error "CloudFormation template file not found: $TEMPLATE_FILE"
        exit 1
    fi

    log_info "Deploying CloudFormation stack: $STACK_NAME"
    aws cloudformation deploy \
        --template-file "$TEMPLATE_FILE" \
        --stack-name $STACK_NAME \
        --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
        --region $REGION

    if [ $? -eq 0 ]; then
        echo ""
        log_success "=== Deployment Successful ==="
        log_info "Getting instance and Aurora information..."
        
        INSTANCE_ID=$(aws cloudformation describe-stacks \
            --stack-name $STACK_NAME \
            --region $REGION \
            --query 'Stacks[0].Outputs[?OutputKey==`InstanceId`].OutputValue' \
            --output text)
        
        AURORA_ENDPOINT=$(aws cloudformation describe-stacks \
            --stack-name $STACK_NAME \
            --region $REGION \
            --query 'Stacks[0].Outputs[?OutputKey==`AuroraClusterEndpoint`].OutputValue' \
            --output text)
        
        echo "Instance ID: $INSTANCE_ID"
        echo "Aurora Endpoint: $AURORA_ENDPOINT"
        echo ""
        
        # Update Target Database secrets with Aurora endpoint information
        log_info "Updating $TARGET_DB_NAME secrets with Aurora endpoint..."
        
        # Get existing Target Database credentials from secrets
        TARGET_ADMIN_CREDS=$(aws secretsmanager get-secret-value \
            --secret-id "oma-secret-${TARGET_SECRET_PREFIX}-admin" \
            --region $REGION \
            --query 'SecretString' \
            --output text)
        
        TARGET_SERVICE_CREDS=$(aws secretsmanager get-secret-value \
            --secret-id "oma-secret-${TARGET_SECRET_PREFIX}-service" \
            --region $REGION \
            --query 'SecretString' \
            --output text)
        
        # Extract credentials using jq
        TARGET_ADMIN_USER=$(echo "$TARGET_ADMIN_CREDS" | jq -r '.username')
        TARGET_ADMIN_PASSWORD=$(echo "$TARGET_ADMIN_CREDS" | jq -r '.password')
        TARGET_DATABASE=$(echo "$TARGET_ADMIN_CREDS" | jq -r '.database')
        TARGET_PORT=$(echo "$TARGET_ADMIN_CREDS" | jq -r '.port')
        
        TARGET_SERVICE_USER=$(echo "$TARGET_SERVICE_CREDS" | jq -r '.username')
        TARGET_SERVICE_PASSWORD=$(echo "$TARGET_SERVICE_CREDS" | jq -r '.password')
        
        # Update Target Database Admin Secret
        TARGET_ADMIN_SECRET_UPDATED=$(cat <<EOF
{
  "username": "$TARGET_ADMIN_USER",
  "password": "$TARGET_ADMIN_PASSWORD",
  "host": "$AURORA_ENDPOINT",
  "port": $TARGET_PORT,
  "database": "$TARGET_DATABASE"
}
EOF
)

        aws secretsmanager update-secret \
            --secret-id "oma-secret-${TARGET_SECRET_PREFIX}-admin" \
            --secret-string "$TARGET_ADMIN_SECRET_UPDATED" \
            --region $REGION

        # Update Target Database Service Secret
        TARGET_SERVICE_SECRET_UPDATED=$(cat <<EOF
{
  "username": "$TARGET_SERVICE_USER",
  "password": "$TARGET_SERVICE_PASSWORD",
  "host": "$AURORA_ENDPOINT",
  "port": $TARGET_PORT,
  "database": "$TARGET_DATABASE"
}
EOF
)

        aws secretsmanager update-secret \
            --secret-id "oma-secret-${TARGET_SECRET_PREFIX}-service" \
            --secret-string "$TARGET_SERVICE_SECRET_UPDATED" \
            --region $REGION
        
        log_success "$TARGET_DB_NAME secrets updated with Aurora endpoint!"
        echo ""
        log_success "Updated Secrets Manager secrets:"
        echo "- oma-secret-oracle-admin"
        echo "- oma-secret-oracle-service"
        echo "- oma-secret-${TARGET_SECRET_PREFIX}-admin (now with Aurora endpoint)"
        echo "- oma-secret-${TARGET_SECRET_PREFIX}-service (now with Aurora endpoint)"
        echo ""
        log_success "Created AWS Resources:"
        echo "- EC2 Instance (OMABox): $INSTANCE_ID"
        echo "- Aurora $TARGET_DB_NAME Cluster and Instance"
        echo "- DMS Replication Instance and Endpoints"
        echo "- VPC Endpoints (SSM, SSM Messages, EC2 Messages, Secrets Manager)"
        echo ""
        log_info "You can connect to the instance using AWS Systems Manager Session Manager"
        echo "Command: aws ssm start-session --target $INSTANCE_ID --region $REGION"
        echo ""
        echo "📋 Environment variables will be automatically set from Aurora and secrets:"
        echo "- Oracle: ORACLE_HOME, ORACLE_SID, ORACLE_ADM_USER, ORACLE_ADM_PASSWORD, etc."
        if [ "$TARGET_DB" = "postgres" ]; then
            echo "- PostgreSQL: PGHOST, PGDATABASE, PGPORT, PGUSER, PGPASSWORD (from Aurora)"
        else
            echo "- MySQL: MYSQL_HOST, MYSQL_DATABASE, MYSQL_TCP_PORT, MYSQL_USER, MYSQL_PASSWORD (from Aurora)"
        fi
        echo "- OMA: OMA_HOME, DB_ASSESSMENTS_FOLDER, OMA_TEST, OMA_TRANSFORM"
        echo ""
        log_warning "Next step: Configure Amazon Q CLI on the instance"
        echo "1. Connect to instance: aws ssm start-session --target $INSTANCE_ID --region $REGION"
        echo "2. Login to Amazon Q: q auth login"
        echo "3. Set model: q configure set model anthropic.claude-3-5-sonnet-20241022-v2:0"
        echo "4. Test: q chat"
    else
        log_error "Deployment failed!"
        exit 1
    fi
}

# 함수: 타겟 데이터베이스 선택
select_target_database() {
    if [[ -n "$TARGET_DB" ]]; then
        # 명령행에서 지정된 경우
        case "$TARGET_DB" in
            "postgres"|"postgresql")
                TARGET_DB="postgres"
                TARGET_DB_NAME="PostgreSQL"
                TARGET_SECRET_PREFIX="postgres"
                log_success "Selected: Aurora PostgreSQL"
                ;;
            "mysql")
                TARGET_DB_NAME="MySQL"
                TARGET_SECRET_PREFIX="mysql"
                log_success "Selected: Aurora MySQL"
                ;;
            *)
                log_error "Invalid target database: $TARGET_DB"
                echo "Please enter 'postgres' or 'mysql'"
                exit 1
                ;;
        esac
    else
        # 대화형 선택
        echo ""
        log_info "=== Target Database Selection ==="
        echo "Available options:"
        echo "  postgres  - Aurora PostgreSQL"
        echo "  mysql     - Aurora MySQL"
        echo ""
        read -p "Enter Target Database (postgres/mysql): " TARGET_DB

        # Validate target database input
        case "$TARGET_DB" in
            "postgres"|"postgresql")
                TARGET_DB="postgres"
                TARGET_DB_NAME="PostgreSQL"
                TARGET_SECRET_PREFIX="postgres"
                log_success "Selected: Aurora PostgreSQL"
                ;;
            "mysql")
                TARGET_DB_NAME="MySQL"
                TARGET_SECRET_PREFIX="mysql"
                log_success "Selected: Aurora MySQL"
                ;;
            *)
                log_error "Invalid target database: $TARGET_DB"
                echo "Please enter 'postgres' or 'mysql'"
                exit 1
                ;;
        esac
    fi
}

# 메인 함수
main() {
    # 기본값 설정
    REGION="ap-northeast-2"
    TARGET_DB=""
    OPTION=""
    
    # 명령행 인수 처리
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                exit 0
                ;;
            -r|--region)
                REGION="$2"
                shift 2
                ;;
            -d|--database)
                TARGET_DB="$2"
                shift 2
                ;;
            -o|--option)
                OPTION="$2"
                shift 2
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
    
    echo "======================================"
    echo "  OMA Box 향상된 배포 스크립트"
    echo "======================================"
    echo ""

    # AWS 리전 입력 (명령행에서 지정되지 않은 경우)
    if [[ -z "$REGION" ]] || [[ "$REGION" == "ap-northeast-2" ]]; then
        read -p "Enter AWS Region [ap-northeast-2]: " INPUT_REGION
        REGION=${INPUT_REGION:-ap-northeast-2}
    fi
    
    log_info "Using AWS Region: $REGION"

    # 타겟 데이터베이스 선택
    select_target_database

    # 실행 옵션 선택 (명령행에서 지정되지 않은 경우)
    if [[ -z "$OPTION" ]]; then
        echo ""
        log_info "=== Deployment Options ==="
        echo "1. Setup Secrets Manager (Database Credentials)"
        echo "2. Deploy CloudFormation Stack (Infrastructure)"
        echo ""
        read -p "Select option (1 or 2): " OPTION
    fi

    case $OPTION in
        1)
            echo ""
            log_info "=== Option 1: Setting up Secrets Manager ==="
            setup_secrets
            ;;
        2)
            echo ""
            log_info "=== Option 2: Deploying CloudFormation Stack ==="
            deploy_cloudformation
            ;;
        *)
            log_error "Invalid option. Please select 1 or 2."
            exit 1
            ;;
    esac
}

# 스크립트 실행
main "$@"
