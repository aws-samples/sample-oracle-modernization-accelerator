#!/bin/bash
# Quick Deploy Script for OMA MCP Servers
# Usage: ./quick-deploy.sh <vpc-id> <subnet-id-1> <subnet-id-2> <key-name>

set -e

if [ "$#" -ne 4 ]; then
    echo "Usage: $0 <vpc-id> <subnet-id-1> <subnet-id-2> <key-name>"
    echo "Example: $0 vpc-123456 subnet-abc123 subnet-def456 my-key"
    exit 1
fi

VPC_ID=$1
SUBNET_ID=$2
SUBNET_ID_2=$3
KEY_NAME=$4
REGION="us-east-1"

echo "🚀 OMA MCP Unified Deployment"
echo "=============================="
echo "VPC: $VPC_ID"
echo "Subnets: $SUBNET_ID, $SUBNET_ID_2"
echo "Key: $KEY_NAME"
echo "Region: $REGION"
echo ""

# Step 1: Build
echo "📦 Building all servers..."
./build-all.sh
echo "✅ Build complete"
echo ""

# Step 2: Cognito
echo "🔐 Creating Cognito OAuth..."
USER_POOL_NAME="oma-mcp-pool-$(date +%s)"
DOMAIN_PREFIX="oma-mcp-$(date +%s)"

USER_POOL_ID=$(aws cognito-idp create-user-pool \
  --pool-name "$USER_POOL_NAME" \
  --region "$REGION" \
  --query 'UserPool.Id' \
  --output text)

aws cognito-idp create-user-pool-domain \
  --domain "$DOMAIN_PREFIX" \
  --user-pool-id "$USER_POOL_ID" \
  --region "$REGION" > /dev/null

aws cognito-idp create-resource-server \
  --user-pool-id "$USER_POOL_ID" \
  --identifier "oma-mcp" \
  --name "oma-mcp" \
  --scopes ScopeName=mcp.access,ScopeDescription="MCP access" \
  --region "$REGION" > /dev/null

CLIENT_OUTPUT=$(aws cognito-idp create-user-pool-client \
  --user-pool-id "$USER_POOL_ID" \
  --client-name "oma-mcp-m2m" \
  --generate-secret \
  --allowed-o-auth-flows client_credentials \
  --allowed-o-auth-flows-user-pool-client \
  --allowed-o-auth-scopes "oma-mcp/mcp.access" \
  --region "$REGION")

CLIENT_ID=$(echo "$CLIENT_OUTPUT" | jq -r '.UserPoolClient.ClientId')
CLIENT_SECRET=$(aws cognito-idp describe-user-pool-client \
  --user-pool-id "$USER_POOL_ID" \
  --client-id "$CLIENT_ID" \
  --region "$REGION" | jq -r '.UserPoolClient.ClientSecret')

echo "✅ Cognito created"
echo "   User Pool: $USER_POOL_ID"
echo "   Domain: https://${DOMAIN_PREFIX}.auth.${REGION}.amazoncognito.com"
echo ""

# Step 3: EC2
echo "🖥️  Launching EC2 instance..."
SG_ID=$(aws ec2 create-security-group \
  --group-name "oma-mcp-sg-$(date +%s)" \
  --description "OMA MCP Servers" \
  --vpc-id "$VPC_ID" \
  --region "$REGION" \
  --query 'GroupId' \
  --output text)

aws ec2 authorize-security-group-ingress \
  --group-id "$SG_ID" \
  --protocol tcp \
  --port 22 \
  --cidr 0.0.0.0/0 \
  --region "$REGION" > /dev/null

aws ec2 authorize-security-group-ingress \
  --group-id "$SG_ID" \
  --protocol tcp \
  --port 9080-9082 \
  --cidr 0.0.0.0/0 \
  --region "$REGION" > /dev/null

INSTANCE_ID=$(aws ec2 run-instances \
  --image-id resolve:ssm:/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64 \
  --instance-type t3.medium \
  --key-name "$KEY_NAME" \
  --security-group-ids "$SG_ID" \
  --subnet-id "$SUBNET_ID" \
  --associate-public-ip-address \
  --region "$REGION" \
  --query 'Instances[0].InstanceId' \
  --output text)

echo "   Waiting for instance..."
aws ec2 wait instance-running --instance-ids "$INSTANCE_ID" --region "$REGION"

INSTANCE_IP=$(aws ec2 describe-instances \
  --instance-ids "$INSTANCE_ID" \
  --region "$REGION" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text)

echo "✅ EC2 launched: $INSTANCE_ID ($INSTANCE_IP)"
echo ""

# Step 4: Deploy JARs
echo "📤 Deploying servers to EC2..."
sleep 10  # Wait for SSH to be ready

scp -i ~/.ssh/${KEY_NAME}.pem -o StrictHostKeyChecking=no \
  oma-sc-mcp/target/oma-sc-mcp-server-1.0.0.jar \
  pg-client-mcp/target/pg-client-mcp-server-1.0.0.jar \
  oracle-client-mcp/target/oracle-client-mcp-server-1.0.0.jar \
  ec2-user@${INSTANCE_IP}:/home/ec2-user/

ssh -i ~/.ssh/${KEY_NAME}.pem -o StrictHostKeyChecking=no ec2-user@${INSTANCE_IP} << 'ENDSSH'
sudo yum install -y java-21-amazon-corretto

# Create systemd services
for service in oma-sc-mcp pg-client-mcp oracle-client-mcp; do
  port=$([[ "$service" == "oma-sc-mcp" ]] && echo 9080 || [[ "$service" == "pg-client-mcp" ]] && echo 9081 || echo 9082)
  sudo tee /etc/systemd/system/${service}.service > /dev/null <<EOF
[Unit]
Description=${service}
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/home/ec2-user
ExecStart=/usr/bin/java -jar /home/ec2-user/${service}-server-1.0.0.jar
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
done

sudo systemctl daemon-reload
sudo systemctl enable oma-sc-mcp pg-client-mcp oracle-client-mcp
sudo systemctl start oma-sc-mcp pg-client-mcp oracle-client-mcp
ENDSSH

echo "✅ Servers deployed and started"
echo ""

# Save deployment info
cat > deployment-info.txt <<EOF
# OMA MCP Deployment - $(date)

USER_POOL_ID=$USER_POOL_ID
DOMAIN=https://${DOMAIN_PREFIX}.auth.${REGION}.amazoncognito.com
CLIENT_ID=$CLIENT_ID
CLIENT_SECRET=$CLIENT_SECRET

INSTANCE_ID=$INSTANCE_ID
INSTANCE_IP=$INSTANCE_IP
SECURITY_GROUP=$SG_ID

# Next steps:
# 1. Create ALB with path-based routing (see UNIFIED_DEPLOYMENT.md Step 6)
# 2. Create CloudFront distribution (Step 7)
# 3. Create Bedrock Gateway and targets (Step 8)

# Test locally:
TOKEN=\$(curl -s -X POST https://${DOMAIN_PREFIX}.auth.${REGION}.amazoncognito.com/oauth2/token \\
  -H "Content-Type: application/x-www-form-urlencoded" \\
  -d "grant_type=client_credentials&client_id=${CLIENT_ID}&client_secret=${CLIENT_SECRET}&scope=oma-mcp/mcp.access" | jq -r '.access_token')

curl http://${INSTANCE_IP}:9080/mcp -H "Authorization: Bearer \$TOKEN" -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
EOF

echo "✅ Deployment info saved to deployment-info.txt"
echo ""
echo "🎉 Core deployment complete!"
echo ""
echo "Next steps:"
echo "1. Follow UNIFIED_DEPLOYMENT.md Step 6-8 to create ALB, CloudFront, and Gateway"
echo "2. Or test locally: ssh -i ~/.ssh/${KEY_NAME}.pem ec2-user@${INSTANCE_IP}"
