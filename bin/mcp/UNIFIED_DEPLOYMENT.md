# OMA MCP Servers - Unified Deployment Guide

## Architecture

```
Internet → CloudFront (HTTPS) → ALB (Path-based routing) → EC2 (3 servers)
                                  ├── /oma-sc → :9080 (oma-sc-mcp)
                                  ├── /pg → :9081 (pg-client-mcp)
                                  └── /oracle → :9082 (oracle-client-mcp)
                                                    ↓
                                            Cognito OAuth2

Gateway (1) → 3 Targets → CloudFront endpoints
```

## Prerequisites
- AWS CLI configured
- Maven 3.6+, Java 21
- Existing VPC with 2+ public subnets
- SSH key pair

## Step 1: Build All Servers

```bash
cd /path/to/oma-mcp
./build-all.sh

# Verify JARs
ls -lh */target/*.jar
# oma-sc-mcp/target/oma-sc-mcp-server-1.0.0.jar
# pg-client-mcp/target/pg-client-mcp-server-1.0.0.jar
# oracle-client-mcp/target/oracle-client-mcp-server-1.0.0.jar
```

## Step 2: Create Cognito OAuth

```bash
REGION="us-east-1"
USER_POOL_NAME="oma-mcp-pool"
DOMAIN_PREFIX="oma-mcp-$(date +%s)"

# Create User Pool
USER_POOL_ID=$(aws cognito-idp create-user-pool \
  --pool-name "$USER_POOL_NAME" \
  --region "$REGION" \
  --query 'UserPool.Id' \
  --output text)

# Create Domain
aws cognito-idp create-user-pool-domain \
  --domain "$DOMAIN_PREFIX" \
  --user-pool-id "$USER_POOL_ID" \
  --region "$REGION"

# Create Resource Server
aws cognito-idp create-resource-server \
  --user-pool-id "$USER_POOL_ID" \
  --identifier "oma-mcp" \
  --name "oma-mcp" \
  --scopes ScopeName=mcp.access,ScopeDescription="MCP access" \
  --region "$REGION"

# Create M2M Client
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

echo "USER_POOL_ID=$USER_POOL_ID"
echo "DOMAIN=https://${DOMAIN_PREFIX}.auth.${REGION}.amazoncognito.com"
echo "CLIENT_ID=$CLIENT_ID"
echo "CLIENT_SECRET=$CLIENT_SECRET"
```

## Step 3: Update Server Configurations

Update `application.properties` for all 3 servers:

```bash
# oma-sc-mcp
cat > oma-sc-mcp/src/main/resources/application.properties <<EOF
spring.ai.mcp.server.enabled=true
spring.ai.mcp.server.name=oma-sc-mcp
spring.ai.mcp.server.version=1.0.0
spring.ai.mcp.server.transport=sse
server.port=9080
spring.security.oauth2.resourceserver.jwt.issuer-uri=https://cognito-idp.${REGION}.amazonaws.com/${USER_POOL_ID}
spring.security.oauth2.resourceserver.jwt.jwk-set-uri=https://cognito-idp.${REGION}.amazonaws.com/${USER_POOL_ID}/.well-known/jwks.json
EOF

# pg-client-mcp
cat > pg-client-mcp/src/main/resources/application.properties <<EOF
spring.ai.mcp.server.enabled=true
spring.ai.mcp.server.name=pg-client-mcp
spring.ai.mcp.server.version=1.0.0
spring.ai.mcp.server.transport=sse
server.port=9081
spring.security.oauth2.resourceserver.jwt.issuer-uri=https://cognito-idp.${REGION}.amazonaws.com/${USER_POOL_ID}
spring.security.oauth2.resourceserver.jwt.jwk-set-uri=https://cognito-idp.${REGION}.amazonaws.com/${USER_POOL_ID}/.well-known/jwks.json
mcp.db.connection.type=secretsmanager
mcp.db.connection.detail=YOUR_PG_SECRET_ARN
EOF

# oracle-client-mcp
cat > oracle-client-mcp/src/main/resources/application.properties <<EOF
spring.ai.mcp.server.enabled=true
spring.ai.mcp.server.name=oracle-client-mcp
spring.ai.mcp.server.version=1.0.0
spring.ai.mcp.server.transport=sse
server.port=9082
spring.security.oauth2.resourceserver.jwt.issuer-uri=https://cognito-idp.${REGION}.amazonaws.com/${USER_POOL_ID}
spring.security.oauth2.resourceserver.jwt.jwk-set-uri=https://cognito-idp.${REGION}.amazonaws.com/${USER_POOL_ID}/.well-known/jwks.json
mcp.db.connection.type=secretsmanager
mcp.db.connection.detail=YOUR_ORACLE_SECRET_ARN
EOF

# Rebuild
./build-all.sh
```

## Step 4: Launch EC2 Instance

```bash
VPC_ID="vpc-xxxxxxxxx"
SUBNET_ID="subnet-xxxxxxxxx"
KEY_NAME="your-key-pair"

# Create Security Group
SG_ID=$(aws ec2 create-security-group \
  --group-name oma-mcp-sg \
  --description "OMA MCP Servers" \
  --vpc-id "$VPC_ID" \
  --region "$REGION" \
  --query 'GroupId' \
  --output text)

# Allow SSH
aws ec2 authorize-security-group-ingress \
  --group-id "$SG_ID" \
  --protocol tcp \
  --port 22 \
  --cidr 0.0.0.0/0 \
  --region "$REGION"

# Allow ports 9080-9082
aws ec2 authorize-security-group-ingress \
  --group-id "$SG_ID" \
  --protocol tcp \
  --port 9080-9082 \
  --cidr 0.0.0.0/0 \
  --region "$REGION"

# Launch instance
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

aws ec2 wait instance-running --instance-ids "$INSTANCE_ID" --region "$REGION"

INSTANCE_IP=$(aws ec2 describe-instances \
  --instance-ids "$INSTANCE_ID" \
  --region "$REGION" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text)

echo "Instance ID: $INSTANCE_ID"
echo "Instance IP: $INSTANCE_IP"
```

## Step 5: Deploy All Servers to EC2

```bash
# Copy JARs
scp -i ~/.ssh/${KEY_NAME}.pem \
  oma-sc-mcp/target/oma-sc-mcp-server-1.0.0.jar \
  pg-client-mcp/target/pg-client-mcp-server-1.0.0.jar \
  oracle-client-mcp/target/oracle-client-mcp-server-1.0.0.jar \
  ec2-user@${INSTANCE_IP}:/home/ec2-user/

# SSH to instance
ssh -i ~/.ssh/${KEY_NAME}.pem ec2-user@${INSTANCE_IP}

# On EC2 instance:
sudo yum install -y java-21-amazon-corretto

# Create systemd services
sudo tee /etc/systemd/system/oma-sc-mcp.service > /dev/null <<EOF
[Unit]
Description=OMA SC MCP Server
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/home/ec2-user
ExecStart=/usr/bin/java -jar /home/ec2-user/oma-sc-mcp-server-1.0.0.jar
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/systemd/system/pg-client-mcp.service > /dev/null <<EOF
[Unit]
Description=PostgreSQL Client MCP Server
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/home/ec2-user
ExecStart=/usr/bin/java -jar /home/ec2-user/pg-client-mcp-server-1.0.0.jar
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/systemd/system/oracle-client-mcp.service > /dev/null <<EOF
[Unit]
Description=Oracle Client MCP Server
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/home/ec2-user
ExecStart=/usr/bin/java -jar /home/ec2-user/oracle-client-mcp-server-1.0.0.jar
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Start all services
sudo systemctl daemon-reload
sudo systemctl enable oma-sc-mcp pg-client-mcp oracle-client-mcp
sudo systemctl start oma-sc-mcp pg-client-mcp oracle-client-mcp

# Check status
sudo systemctl status oma-sc-mcp pg-client-mcp oracle-client-mcp
```

## Step 6: Create ALB with Path-based Routing

```bash
# Get second subnet for ALB
SUBNET_ID_2="subnet-yyyyyyyyy"

# Create ALB
ALB_ARN=$(aws elbv2 create-load-balancer \
  --name oma-mcp-alb \
  --subnets "$SUBNET_ID" "$SUBNET_ID_2" \
  --security-groups "$SG_ID" \
  --scheme internet-facing \
  --type application \
  --region "$REGION" \
  --query 'LoadBalancers[0].LoadBalancerArn' \
  --output text)

ALB_DNS=$(aws elbv2 describe-load-balancers \
  --load-balancer-arns "$ALB_ARN" \
  --region "$REGION" \
  --query 'LoadBalancers[0].DNSName' \
  --output text)

echo "ALB DNS: $ALB_DNS"

# Create Target Groups
TG_OMA_SC=$(aws elbv2 create-target-group \
  --name oma-sc-tg \
  --protocol HTTP \
  --port 9080 \
  --vpc-id "$VPC_ID" \
  --health-check-path /actuator/health \
  --region "$REGION" \
  --query 'TargetGroups[0].TargetGroupArn' \
  --output text)

TG_PG=$(aws elbv2 create-target-group \
  --name pg-client-tg \
  --protocol HTTP \
  --port 9081 \
  --vpc-id "$VPC_ID" \
  --health-check-path /actuator/health \
  --region "$REGION" \
  --query 'TargetGroups[0].TargetGroupArn' \
  --output text)

TG_ORACLE=$(aws elbv2 create-target-group \
  --name oracle-client-tg \
  --protocol HTTP \
  --port 9082 \
  --vpc-id "$VPC_ID" \
  --health-check-path /actuator/health \
  --region "$REGION" \
  --query 'TargetGroups[0].TargetGroupArn' \
  --output text)

# Register targets
aws elbv2 register-targets --target-group-arn "$TG_OMA_SC" --targets Id="$INSTANCE_ID" --region "$REGION"
aws elbv2 register-targets --target-group-arn "$TG_PG" --targets Id="$INSTANCE_ID" --region "$REGION"
aws elbv2 register-targets --target-group-arn "$TG_ORACLE" --targets Id="$INSTANCE_ID" --region "$REGION"

# Create listener with default action
LISTENER_ARN=$(aws elbv2 create-listener \
  --load-balancer-arn "$ALB_ARN" \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn="$TG_OMA_SC" \
  --region "$REGION" \
  --query 'Listeners[0].ListenerArn' \
  --output text)

# Add path-based rules
aws elbv2 create-rule \
  --listener-arn "$LISTENER_ARN" \
  --priority 1 \
  --conditions Field=path-pattern,Values='/oma-sc*' \
  --actions Type=forward,TargetGroupArn="$TG_OMA_SC" \
  --region "$REGION"

aws elbv2 create-rule \
  --listener-arn "$LISTENER_ARN" \
  --priority 2 \
  --conditions Field=path-pattern,Values='/pg*' \
  --actions Type=forward,TargetGroupArn="$TG_PG" \
  --region "$REGION"

aws elbv2 create-rule \
  --listener-arn "$LISTENER_ARN" \
  --priority 3 \
  --conditions Field=path-pattern,Values='/oracle*' \
  --actions Type=forward,TargetGroupArn="$TG_ORACLE" \
  --region "$REGION"

# Wait for healthy targets
sleep 60
```

## Step 7: Create CloudFront Distribution

```bash
cat > cloudfront-config.json <<EOF
{
  "CallerReference": "oma-mcp-$(date +%s)",
  "Comment": "OMA MCP Servers",
  "Enabled": true,
  "Origins": {
    "Quantity": 1,
    "Items": [
      {
        "Id": "oma-mcp-alb",
        "DomainName": "${ALB_DNS}",
        "CustomOriginConfig": {
          "HTTPPort": 80,
          "HTTPSPort": 443,
          "OriginProtocolPolicy": "http-only",
          "OriginReadTimeout": 60,
          "OriginKeepaliveTimeout": 5
        }
      }
    ]
  },
  "DefaultCacheBehavior": {
    "TargetOriginId": "oma-mcp-alb",
    "ViewerProtocolPolicy": "https-only",
    "AllowedMethods": {
      "Quantity": 7,
      "Items": ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"],
      "CachedMethods": {
        "Quantity": 2,
        "Items": ["GET", "HEAD"]
      }
    },
    "CachePolicyId": "4135ea2d-6df8-44a3-9df3-4b5a84be39ad",
    "OriginRequestPolicyId": "216adef6-5c7f-47e4-b989-5492eafa07d3",
    "Compress": true,
    "MinTTL": 0
  }
}
EOF

CF_OUTPUT=$(aws cloudfront create-distribution \
  --distribution-config file://cloudfront-config.json \
  --region "$REGION")

CF_ID=$(echo "$CF_OUTPUT" | jq -r '.Distribution.Id')
CF_DOMAIN=$(echo "$CF_OUTPUT" | jq -r '.Distribution.DomainName')

echo "CloudFront ID: $CF_ID"
echo "CloudFront Domain: $CF_DOMAIN"

# Wait for deployment
aws cloudfront wait distribution-deployed --id "$CF_ID" --region "$REGION"
```

## Step 8: Create Bedrock AgentCore Gateway & Targets

```bash
# Create OAuth Provider
OAUTH_PROVIDER_ARN=$(aws bedrock-agentcore-control create-oauth2-credential-provider \
  --name oma-mcp-oauth2 \
  --credential-provider-vendor CustomOauth2 \
  --oauth2-provider-config-input "{
    \"customOauth2ProviderConfig\": {
      \"oauthDiscovery\": {
        \"authorizationServerMetadata\": {
          \"issuer\": \"https://cognito-idp.${REGION}.amazonaws.com/${USER_POOL_ID}\",
          \"tokenEndpoint\": \"https://${DOMAIN_PREFIX}.auth.${REGION}.amazoncognito.com/oauth2/token\",
          \"authorizationEndpoint\": \"https://${DOMAIN_PREFIX}.auth.${REGION}.amazoncognito.com/oauth2/authorize\"
        }
      },
      \"clientId\": \"${CLIENT_ID}\",
      \"clientSecret\": \"${CLIENT_SECRET}\"
    }
  }" \
  --region "$REGION" \
  --query 'credentialProviderArn' \
  --output text)

# Create Gateway
GATEWAY_ID=$(aws bedrock-agentcore-control create-gateway \
  --name oma-mcp-gateway \
  --region "$REGION" \
  --query 'gatewayId' \
  --output text)

echo "Gateway ID: $GATEWAY_ID"

# Create 3 Gateway Targets
TARGET_OMA_SC=$(aws bedrock-agentcore-control create-gateway-target \
  --gateway-identifier "$GATEWAY_ID" \
  --name "oma-sc-mcp" \
  --target-configuration "{\"mcp\":{\"mcpServer\":{\"endpoint\":\"https://${CF_DOMAIN}/oma-sc\"}}}" \
  --credential-provider-configurations "[{
    \"credentialProviderType\":\"OAUTH\",
    \"credentialProvider\":{
      \"oauthCredentialProvider\":{
        \"providerArn\":\"${OAUTH_PROVIDER_ARN}\",
        \"scopes\":[\"oma-mcp/mcp.access\"],
        \"grantType\":\"CLIENT_CREDENTIALS\"
      }
    }
  }]" \
  --region "$REGION" \
  --query 'targetId' \
  --output text)

TARGET_PG=$(aws bedrock-agentcore-control create-gateway-target \
  --gateway-identifier "$GATEWAY_ID" \
  --name "pg-client-mcp" \
  --target-configuration "{\"mcp\":{\"mcpServer\":{\"endpoint\":\"https://${CF_DOMAIN}/pg\"}}}" \
  --credential-provider-configurations "[{
    \"credentialProviderType\":\"OAUTH\",
    \"credentialProvider\":{
      \"oauthCredentialProvider\":{
        \"providerArn\":\"${OAUTH_PROVIDER_ARN}\",
        \"scopes\":[\"oma-mcp/mcp.access\"],
        \"grantType\":\"CLIENT_CREDENTIALS\"
      }
    }
  }]" \
  --region "$REGION" \
  --query 'targetId' \
  --output text)

TARGET_ORACLE=$(aws bedrock-agentcore-control create-gateway-target \
  --gateway-identifier "$GATEWAY_ID" \
  --name "oracle-client-mcp" \
  --target-configuration "{\"mcp\":{\"mcpServer\":{\"endpoint\":\"https://${CF_DOMAIN}/oracle\"}}}" \
  --credential-provider-configurations "[{
    \"credentialProviderType\":\"OAUTH\",
    \"credentialProvider\":{
      \"oauthCredentialProvider\":{
        \"providerArn\":\"${OAUTH_PROVIDER_ARN}\",
        \"scopes\":[\"oma-mcp/mcp.access\"],
        \"grantType\":\"CLIENT_CREDENTIALS\"
      }
    }
  }]" \
  --region "$REGION" \
  --query 'targetId' \
  --output text)

echo "Target IDs:"
echo "  oma-sc-mcp: $TARGET_OMA_SC"
echo "  pg-client-mcp: $TARGET_PG"
echo "  oracle-client-mcp: $TARGET_ORACLE"
```

## Step 9: Test Deployment

```bash
# Get OAuth token
TOKEN=$(curl -s -X POST "https://${DOMAIN_PREFIX}.auth.${REGION}.amazoncognito.com/oauth2/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=${CLIENT_ID}&client_secret=${CLIENT_SECRET}&scope=oma-mcp/mcp.access" | jq -r '.access_token')

# Test all 3 servers
echo "Testing oma-sc-mcp..."
curl -s "https://${CF_DOMAIN}/oma-sc" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}' | jq '.result.tools | length'

echo "Testing pg-client-mcp..."
curl -s "https://${CF_DOMAIN}/pg" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}' | jq '.result.tools | length'

echo "Testing oracle-client-mcp..."
curl -s "https://${CF_DOMAIN}/oracle" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}' | jq '.result.tools | length'
```

## Step 10: Save Deployment Info

```bash
cat > deployment-info.txt <<EOF
# OMA MCP Unified Deployment

## OAuth
USER_POOL_ID=$USER_POOL_ID
DOMAIN=https://${DOMAIN_PREFIX}.auth.${REGION}.amazoncognito.com
CLIENT_ID=$CLIENT_ID
CLIENT_SECRET=$CLIENT_SECRET

## Infrastructure
INSTANCE_ID=$INSTANCE_ID
INSTANCE_IP=$INSTANCE_IP
SECURITY_GROUP=$SG_ID
ALB_ARN=$ALB_ARN
ALB_DNS=$ALB_DNS
CLOUDFRONT_ID=$CF_ID
CLOUDFRONT_DOMAIN=$CF_DOMAIN

## Gateway
GATEWAY_ID=$GATEWAY_ID
OAUTH_PROVIDER_ARN=$OAUTH_PROVIDER_ARN
TARGET_OMA_SC=$TARGET_OMA_SC
TARGET_PG=$TARGET_PG
TARGET_ORACLE=$TARGET_ORACLE

## Endpoints
https://${CF_DOMAIN}/oma-sc
https://${CF_DOMAIN}/pg
https://${CF_DOMAIN}/oracle
EOF

cat deployment-info.txt
```

## Maintenance

### Update Servers
```bash
# Rebuild locally
./build-all.sh

# Copy to EC2
scp -i ~/.ssh/${KEY_NAME}.pem */target/*.jar ec2-user@${INSTANCE_IP}:/home/ec2-user/

# Restart services
ssh -i ~/.ssh/${KEY_NAME}.pem ec2-user@${INSTANCE_IP} \
  'sudo systemctl restart oma-sc-mcp pg-client-mcp oracle-client-mcp'
```

### View Logs
```bash
ssh -i ~/.ssh/${KEY_NAME}.pem ec2-user@${INSTANCE_IP}
sudo journalctl -u oma-sc-mcp -f
sudo journalctl -u pg-client-mcp -f
sudo journalctl -u oracle-client-mcp -f
```

### Invalidate CloudFront Cache
```bash
aws cloudfront create-invalidation \
  --distribution-id "$CF_ID" \
  --paths "/*" \
  --region "$REGION"
```

## Cleanup

```bash
# Delete Gateway targets
aws bedrock-agentcore-control delete-gateway-target --gateway-identifier "$GATEWAY_ID" --target-id "$TARGET_OMA_SC" --region "$REGION"
aws bedrock-agentcore-control delete-gateway-target --gateway-identifier "$GATEWAY_ID" --target-id "$TARGET_PG" --region "$REGION"
aws bedrock-agentcore-control delete-gateway-target --gateway-identifier "$GATEWAY_ID" --target-id "$TARGET_ORACLE" --region "$REGION"

# Delete Gateway
aws bedrock-agentcore-control delete-gateway --gateway-identifier "$GATEWAY_ID" --region "$REGION"

# Delete CloudFront
aws cloudfront delete-distribution --id "$CF_ID" --if-match "ETAG" --region "$REGION"

# Delete ALB
aws elbv2 delete-load-balancer --load-balancer-arn "$ALB_ARN" --region "$REGION"
aws elbv2 delete-target-group --target-group-arn "$TG_OMA_SC" --region "$REGION"
aws elbv2 delete-target-group --target-group-arn "$TG_PG" --region "$REGION"
aws elbv2 delete-target-group --target-group-arn "$TG_ORACLE" --region "$REGION"

# Terminate EC2
aws ec2 terminate-instances --instance-ids "$INSTANCE_ID" --region "$REGION"

# Delete Security Group
aws ec2 delete-security-group --group-id "$SG_ID" --region "$REGION"

# Delete Cognito
aws cognito-idp delete-user-pool --user-pool-id "$USER_POOL_ID" --region "$REGION"

# Delete OAuth Provider
aws bedrock-agentcore-control delete-oauth2-credential-provider --name oma-mcp-oauth2 --region "$REGION"
```
