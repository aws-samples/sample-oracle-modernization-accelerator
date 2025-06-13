#!/bin/bash

# Disable AWS CLI pager for cleaner output
export AWS_PAGER=""

# Function to setup secrets
setup_secrets() {
    echo ""
    echo "=== Creating Secrets Manager Secrets ==="
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

# PostgreSQL Credentials (will be updated with Aurora info after deployment)
echo "3. PostgreSQL Credentials (for Aurora PostgreSQL):"
echo "Note: Aurora endpoint will be automatically configured after deployment"
read -p "Enter PostgreSQL Admin Username [postgres]: " POSTGRES_ADMIN_USER
POSTGRES_ADMIN_USER=${POSTGRES_ADMIN_USER:-postgres}
read -s -p "Enter PostgreSQL Admin Password: " POSTGRES_ADMIN_PASSWORD
echo ""
read -p "Enter PostgreSQL Database Name [postgres]: " POSTGRES_DATABASE
POSTGRES_DATABASE=${POSTGRES_DATABASE:-postgres}
echo ""

# PostgreSQL Service Credentials
echo "4. PostgreSQL Service Credentials:"
read -p "Enter PostgreSQL Service Username [pguser]: " POSTGRES_SERVICE_USER
POSTGRES_SERVICE_USER=${POSTGRES_SERVICE_USER:-pguser}
read -s -p "Enter PostgreSQL Service Password: " POSTGRES_SERVICE_PASSWORD
echo ""
echo ""

# Create Secrets in AWS Secrets Manager
echo "Creating secrets in AWS Secrets Manager..."

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

# PostgreSQL Admin Secret (placeholder - will be updated after Aurora deployment)
POSTGRES_ADMIN_SECRET=$(cat <<EOF
{
  "username": "$POSTGRES_ADMIN_USER",
  "password": "$POSTGRES_ADMIN_PASSWORD",
  "host": "placeholder-will-be-updated",
  "port": 5432,
  "database": "$POSTGRES_DATABASE"
}
EOF
)

aws secretsmanager create-secret \
    --name "oma-secret-postgres-admin" \
    --description "PostgreSQL Admin credentials for OMA (Aurora)" \
    --secret-string "$POSTGRES_ADMIN_SECRET" \
    --region $REGION 2>/dev/null || \
aws secretsmanager update-secret \
    --secret-id "oma-secret-postgres-admin" \
    --secret-string "$POSTGRES_ADMIN_SECRET" \
    --region $REGION

# PostgreSQL Service Secret (placeholder - will be updated after Aurora deployment)
POSTGRES_SERVICE_SECRET=$(cat <<EOF
{
  "username": "$POSTGRES_SERVICE_USER",
  "password": "$POSTGRES_SERVICE_PASSWORD",
  "host": "placeholder-will-be-updated",
  "port": 5432,
  "database": "$POSTGRES_DATABASE"
}
EOF
)

aws secretsmanager create-secret \
    --name "oma-secret-postgres-service" \
    --description "PostgreSQL Service credentials for OMA (Aurora)" \
    --secret-string "$POSTGRES_SERVICE_SECRET" \
    --region $REGION 2>/dev/null || \
aws secretsmanager update-secret \
    --secret-id "oma-secret-postgres-service" \
    --secret-string "$POSTGRES_SERVICE_SECRET" \
    --region $REGION

    echo "✅ Secrets created/updated successfully!"
    echo ""
    echo "📋 Created/Updated Secrets Manager secrets:"
    echo "- oma-secret-oracle-admin"
    echo "- oma-secret-oracle-service"
    echo "- oma-secret-postgres-admin (placeholder - will be updated after Aurora deployment)"
    echo "- oma-secret-postgres-service (placeholder - will be updated after Aurora deployment)"
    echo ""
    echo "🔄 Next step: Run './deploy-omabox.sh' and select option 2 to deploy infrastructure"
}

# Function to deploy CloudFormation
deploy_cloudformation() {
    echo ""
    echo "=== Deploying CloudFormation Stack ==="
    echo "Deploying OMABox with complete infrastructure:"
    echo "Region: $REGION"
    echo "VPC: OMA_VPC (10.255.255.0/24)"
    echo "Public Subnets: 2 (for NAT Gateway)"
    echo "Private Subnets: 2 (for EC2, Aurora, DMS, and VPC Endpoints)"
    echo ""

    # Get the directory where the script is located
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

    # Check if secrets exist
    echo "Checking if required secrets exist..."
    SECRETS_EXIST=true
    
    for SECRET_NAME in "oma-secret-oracle-admin" "oma-secret-oracle-service" "oma-secret-postgres-admin" "oma-secret-postgres-service"; do
        aws secretsmanager describe-secret --secret-id "$SECRET_NAME" --region $REGION >/dev/null 2>&1
        if [ $? -ne 0 ]; then
            echo "❌ Secret '$SECRET_NAME' not found!"
            SECRETS_EXIST=false
        fi
    done
    
    if [ "$SECRETS_EXIST" = false ]; then
        echo ""
        echo "⚠️  Required secrets are missing. Please run option 1 first to create secrets."
        echo "Command: ./deploy-omabox.sh (then select option 1)"
        exit 1
    fi
    
    echo "✅ All required secrets found!"
    echo ""

    # Deploy CloudFormation Stack
    STACK_NAME="omabox-stack"

    aws cloudformation deploy \
        --template-file "${SCRIPT_DIR}/omabox-cloudformation.yaml" \
        --stack-name $STACK_NAME \
        --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
        --region $REGION

    if [ $? -eq 0 ]; then
        echo ""
        echo "=== Deployment Successful ==="
        echo "Getting instance and Aurora information..."
        
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
        
        # Update PostgreSQL secrets with Aurora endpoint information
        echo "Updating PostgreSQL secrets with Aurora endpoint..."
        
        # Get existing PostgreSQL credentials from secrets
        POSTGRES_ADMIN_CREDS=$(aws secretsmanager get-secret-value \
            --secret-id "oma-secret-postgres-admin" \
            --region $REGION \
            --query 'SecretString' \
            --output text)
        
        POSTGRES_SERVICE_CREDS=$(aws secretsmanager get-secret-value \
            --secret-id "oma-secret-postgres-service" \
            --region $REGION \
            --query 'SecretString' \
            --output text)
        
        # Extract credentials using jq
        POSTGRES_ADMIN_USER=$(echo "$POSTGRES_ADMIN_CREDS" | jq -r '.username')
        POSTGRES_ADMIN_PASSWORD=$(echo "$POSTGRES_ADMIN_CREDS" | jq -r '.password')
        POSTGRES_DATABASE=$(echo "$POSTGRES_ADMIN_CREDS" | jq -r '.database')
        
        POSTGRES_SERVICE_USER=$(echo "$POSTGRES_SERVICE_CREDS" | jq -r '.username')
        POSTGRES_SERVICE_PASSWORD=$(echo "$POSTGRES_SERVICE_CREDS" | jq -r '.password')
        
        # Update PostgreSQL Admin Secret
        POSTGRES_ADMIN_SECRET_UPDATED=$(cat <<EOF
{
  "username": "$POSTGRES_ADMIN_USER",
  "password": "$POSTGRES_ADMIN_PASSWORD",
  "host": "$AURORA_ENDPOINT",
  "port": 5432,
  "database": "$POSTGRES_DATABASE"
}
EOF
)

        aws secretsmanager update-secret \
            --secret-id "oma-secret-postgres-admin" \
            --secret-string "$POSTGRES_ADMIN_SECRET_UPDATED" \
            --region $REGION

        # Update PostgreSQL Service Secret
        POSTGRES_SERVICE_SECRET_UPDATED=$(cat <<EOF
{
  "username": "$POSTGRES_SERVICE_USER",
  "password": "$POSTGRES_SERVICE_PASSWORD",
  "host": "$AURORA_ENDPOINT",
  "port": 5432,
  "database": "$POSTGRES_DATABASE"
}
EOF
)

        aws secretsmanager update-secret \
            --secret-id "oma-secret-postgres-service" \
            --secret-string "$POSTGRES_SERVICE_SECRET_UPDATED" \
            --region $REGION
        
        echo "✅ PostgreSQL secrets updated with Aurora endpoint!"
        echo ""
        echo "✅ Updated Secrets Manager secrets:"
        echo "- oma-secret-oracle-admin"
        echo "- oma-secret-oracle-service"
        echo "- oma-secret-postgres-admin (now with Aurora endpoint)"
        echo "- oma-secret-postgres-service (now with Aurora endpoint)"
        echo ""
        echo "✅ Created AWS Resources:"
        echo "- EC2 Instance (OMABox): $INSTANCE_ID"
        echo "- Aurora PostgreSQL Cluster and Instance"
        echo "- DMS Replication Instance and Endpoints"
        echo "- VPC Endpoints (SSM, SSM Messages, EC2 Messages, Secrets Manager)"
        echo ""
        echo "🚀 You can connect to the instance using AWS Systems Manager Session Manager"
        echo "Command: aws ssm start-session --target $INSTANCE_ID --region $REGION"
        echo ""
        echo "📋 Environment variables will be automatically set from Aurora and secrets:"
        echo "- Oracle: ORACLE_HOME, ORACLE_SID, ORACLE_ADM_USER, ORACLE_ADM_PASSWORD, etc."
        echo "- PostgreSQL: PGHOST, PGDATABASE, PGPORT, PGUSER, PGPASSWORD (from Aurora)"
        echo "- OMA: OMA_HOME, OMA_ASSESSMENT, OMA_TEST, OMA_TRANSFORM"
        echo ""
        echo "⚠️  Next step: Configure Amazon Q CLI on the instance"
        echo "1. Connect to instance: aws ssm start-session --target $INSTANCE_ID --region $REGION"
        echo "2. Login to Amazon Q: q auth login"
        echo "3. Set model: q configure set model anthropic.claude-3-5-sonnet-20241022-v2:0"
        echo "4. Test: q chat"
    else
        echo "❌ Deployment failed!"
        exit 1
    fi
}

# Main script execution
echo "=== OMABox EC2 Instance Deployment ==="
echo ""

# Input Parameters
read -p "Enter AWS Region [ap-northeast-2]: " REGION
REGION=${REGION:-ap-northeast-2}

echo ""
echo "=== Deployment Options ==="
echo "1. Setup Secrets Manager (Database Credentials)"
echo "2. Deploy CloudFormation Stack (Infrastructure)"
echo ""
read -p "Select option (1 or 2): " OPTION

case $OPTION in
    1)
        echo ""
        echo "=== Option 1: Setting up Secrets Manager ==="
        setup_secrets
        ;;
    2)
        echo ""
        echo "=== Option 2: Deploying CloudFormation Stack ==="
        deploy_cloudformation
        ;;
    *)
        echo "Invalid option. Please select 1 or 2."
        exit 1
        ;;
esac
