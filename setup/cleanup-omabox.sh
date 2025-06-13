#!/bin/bash

# OMABox EC2 Instance Cleanup Script
echo "=== OMABox EC2 Instance Cleanup ==="
echo ""

read -p "Enter AWS Region [ap-northeast-2]: " REGION
REGION=${REGION:-ap-northeast-2}

STACK_NAME="omabox-stack"

echo "🗑️  Cleaning up OMABox resources..."
echo "Region: $REGION"
echo "Stack: $STACK_NAME"
echo ""

# Ask if user wants to delete secrets as well
read -p "Do you want to delete Secrets Manager secrets as well? (y/N): " DELETE_SECRETS
DELETE_SECRETS=${DELETE_SECRETS:-N}

if [[ "$DELETE_SECRETS" =~ ^[Yy]$ ]]; then
    echo ""
    echo "=== Deleting Secrets Manager Secrets ==="
    
    SECRETS=("oma-secret-oracle-admin" "oma-secret-oracle-service" "oma-secret-postgres-admin" "oma-secret-postgres-service")
    
    for SECRET in "${SECRETS[@]}"; do
        echo "Deleting secret: $SECRET"
        aws secretsmanager delete-secret \
            --secret-id "$SECRET" \
            --force-delete-without-recovery \
            --region $REGION 2>/dev/null
        
        if [ $? -eq 0 ]; then
            echo "✅ Secret $SECRET deleted successfully"
        else
            echo "⚠️  Secret $SECRET not found or already deleted"
        fi
    done
    echo ""
fi

echo "=== Deleting CloudFormation Stack ==="
aws cloudformation delete-stack \
    --stack-name $STACK_NAME \
    --region $REGION

if [ $? -eq 0 ]; then
    echo "✅ Stack deletion initiated successfully!"
    echo ""
    echo "📋 Resources being deleted:"
    echo "- EC2 Instance (OMABox)"
    echo "- Aurora PostgreSQL Cluster and Instance"
    echo "- DMS Replication Instance and Target Endpoint"
    echo "- IAM Roles (EC2, DMS VPC, DMS CloudWatch)"
    echo "- Security Groups (EC2, Database, VPC Endpoints)"
    echo "- VPC Endpoints (SSM, SSM Messages, EC2 Messages, Secrets Manager)"
    echo "- KMS Key and Alias"
    echo "- DB Subnet Group and DMS Subnet Group"
    if [[ "$DELETE_SECRETS" =~ ^[Yy]$ ]]; then
        echo "- Secrets Manager Secrets (Oracle and PostgreSQL)"
    else
        echo "- Secrets Manager Secrets will be retained"
    fi
    echo ""
    echo "⚠️  Note: Aurora and DMS resources may take several minutes to delete"
    echo ""
    echo "🔍 You can monitor the deletion progress using:"
    echo "aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION"
    echo ""
    echo "Or check in the AWS Console: CloudFormation > Stacks"
else
    echo "❌ Stack deletion failed!"
    exit 1
fi
