# MCP Deployment Package

3개의 MCP 서버 배포 패키지입니다.

## 포함된 MCP 서버
- oma-mcp: Oracle Modernization Accelerator MCP
- pg-client-mcp: PostgreSQL Client MCP  
- oracle-client-mcp: Oracle Client MCP

## 사용 방법

### 1. 초기화
```bash
./init.sh
```

### 2. 로컬 빌드
```bash
./build-all.sh
```

### 3. 원격 서버 배포
```bash
./deploy.sh <server-host> <server-user>
# 예: ./deploy.sh 10.0.1.100 ec2-user
```

## 설정 파일
각 MCP 디렉토리의 `application-*.properties` 파일을 환경에 맞게 수정하세요.

## Kiro CLI 설정
`mcp-config.json` 파일을 사용하여 Kiro CLI에서 MCP 서버를 설정할 수 있습니다.
경로를 실제 배포 위치에 맞게 수정하세요 (기본값: `/opt/mcp/`).
