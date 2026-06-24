# OMA Phase 1 -- Schema + Data Migration

Oracle DDL + 데이터를 PostgreSQL(Aurora)로 이관하는 Strands Agents SDK 기반 파이프라인.

## 실행 순서

**반드시 preflight 체크 후 실행하라. 바로 run_migration.py 실행 금지.**

```
1. Preflight 체크 (환경변수 + 리소스 확인)
2. python3 scripts/run_migration.py 실행
3. 3분마다 진행 모니터링
```

## 1단계: Preflight 체크 (필수)

마이그레이션 실행 전 아래를 **반드시 순서대로** 확인하라:

```bash
echo "== Phase 1 Preflight =="

# 1. .env 로드
if [ -f ../.env ]; then set -a; source ../.env; set +a; echo "  .env: OK"; else echo "  ERROR: ../.env 없음. /init-project 먼저 실행"; exit 1; fi

# 2. Oracle 접속 정보
echo -n "  Oracle: "
[ -n "$ORACLE_HOST" ] && echo "$ORACLE_HOST:${ORACLE_PORT:-1521}/${ORACLE_SID} (user: $ORACLE_USER, schema: ${ORACLE_SCHEMA:-$ORACLE_USER})" || echo "ERROR: ORACLE_HOST 미설정"

# 3. PG 접속 정보
echo -n "  PG: "
[ -n "$PG_HOST" ] && echo "$PG_HOST:${PG_PORT:-5432}/${PG_DATABASE} (user: $PG_USER)" || echo "ERROR: PG_HOST 미설정"

# 4. Bedrock 리전
echo -n "  Bedrock: "
[ -n "$BEDROCK_REGIONS" ] && echo "$BEDROCK_REGIONS" || echo "${BEDROCK_REGION:-ap-northeast-2} (단일)"

# 5. Python 3.11+
echo -n "  Python: "
python3.11 --version 2>/dev/null || python3 --version

# 6. pip 패키지
echo -n "  strands-agents: "
python3 -c "import strands; print('OK')" 2>/dev/null || python3.11 -c "import strands; print('OK')" 2>/dev/null || echo "FAIL (pip install -r requirements.txt)"

# 7. DynamoDB 체크포인트 테이블
echo -n "  DynamoDB oma-migration-state: "
python3 -c "
import boto3, os
ddb = boto3.resource('dynamodb', region_name=os.environ.get('AWS_DEFAULT_REGION','ap-northeast-2'))
t = ddb.Table('oma-migration-state')
t.table_status
print('OK')
" 2>/dev/null || echo "FAIL (테이블 생성 필요)"

echo -n "  DynamoDB oma-pattern-memory: "
python3 -c "
import boto3, os
ddb = boto3.resource('dynamodb', region_name=os.environ.get('AWS_DEFAULT_REGION','ap-northeast-2'))
t = ddb.Table('oma-pattern-memory')
t.table_status
print('OK')
" 2>/dev/null || echo "WARNING (RAG 선택적)"

# 8. S3 버킷
echo -n "  S3 (${DMS_SC_S3_BUCKET:-미설정}): "
[ -n "$DMS_SC_S3_BUCKET" ] && python3 -c "
import boto3, os
s3 = boto3.client('s3', region_name=os.environ.get('AWS_DEFAULT_REGION','ap-northeast-2'))
s3.head_bucket(Bucket=os.environ['DMS_SC_S3_BUCKET'])
print('OK')
" 2>/dev/null || echo "FAIL"

# 9. DMS Migration Project
echo -n "  DMS ARN: "
[ -n "$DMS_MIGRATION_PROJECT_ARN" ] && echo "OK ($DMS_MIGRATION_PROJECT_ARN)" || echo "WARNING: 미설정 (DMS SC 사용 시 필요)"

# 10. Oracle DB 연결 테스트
echo -n "  Oracle 연결: "
python3 -c "
import oracledb, os
dsn = f'{os.environ[\"ORACLE_HOST\"]}:{os.environ.get(\"ORACLE_PORT\",\"1521\")}/{os.environ[\"ORACLE_SID\"]}'
conn = oracledb.connect(user=os.environ['ORACLE_USER'], password=os.environ['ORACLE_PASSWORD'], dsn=dsn)
cur = conn.cursor(); cur.execute('SELECT 1 FROM DUAL'); conn.close()
print('OK')
" 2>/dev/null || echo "FAIL"

# 11. PG DB 연결 테스트
echo -n "  PG 연결: "
PGPASSWORD="$PG_PASSWORD" psql -h "$PG_HOST" -p "${PG_PORT:-5432}" -U "$PG_USER" -d "$PG_DATABASE" -c "SELECT 1" 2>/dev/null | grep -q "1" && echo "OK" || echo "FAIL"

echo ""
echo "== Preflight 완료 =="
```

**ERROR가 하나라도 있으면 실행하지 마라.** .env를 수정하거나 /init-project를 다시 실행.

## 2단계: 마이그레이션 실행

```bash
python3 scripts/run_migration.py
```

재개: `python3 scripts/run_migration.py --resume <migration_id>`

## 3단계: 진행 모니터링 (필수)

Phase 1은 **수 시간** 걸릴 수 있다. 3분마다 진행 체크:

```bash
bash ../app-migration/tools/check-phase1-progress.sh
```

**절대 금지:**
- 프로세스를 kill/terminate 하지 마라. 수 시간 정상.
- Bash timeout을 걸지 마라.
- "멈춤" "응답 없음"으로 판단하지 마라. 프로세스가 살아있으면 기다려라.

## 환경변수 (.env)

`/init-project`가 설정:
- `ORACLE_HOST/PORT/SID/USER/PASSWORD/SCHEMA`
- `PG_HOST/PORT/DATABASE/USER/PASSWORD`
- `BEDROCK_REGIONS`
- `DMS_MIGRATION_PROJECT_ARN` (Phase 1용)
- `DMS_SC_S3_BUCKET` (Phase 1용)
- `DMS_SC_PROJECT_NAME` (Phase 1용)

## 산출물

| 파일 | 설명 |
|------|------|
| `migration_result.json` | 결과 요약 |
| `../migration-config.json` | Phase 2 핸드오프 |
| `workspace/reports/*.html` | HTML 보고서 |

## Phase 2 전환

Phase 1 완료 후:
```bash
cd ../app-migration
claude
/phase-transition
```

## 아키텍처

- 9개 Strands 에이전트 (discover, convert, verify, remediate, evaluate 등)
- 43개 MCP 도구 (Oracle/PG 쿼리, DMS SC, 분석, RAG)
- DynamoDB 체크포인트 (재개 가능)
- Bedrock Claude Opus
