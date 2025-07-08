#!/bin/bash

# Alert Log에서 SQL 구문 모니터링 스크립트

# Oracle 환경 변수 설정 (필요시 수정)
export ORACLE_HOME=${ORACLE_HOME:-/u01/app/oracle/product/19.0.0/dbhome_1}
export ORACLE_SID=${ORACLE_SID:-ORCL}

# Alert Log 경로 찾기
ALERT_LOG_PATH=$(sqlplus -s / as sysdba <<EOF
SET PAGESIZE 0
SET FEEDBACK OFF
SET HEADING OFF
SELECT value FROM v\$diag_info WHERE name = 'Diag Alert';
EXIT;
EOF
)

ALERT_LOG_FILE="${ALERT_LOG_PATH}/alert_${ORACLE_SID}.log"

echo "Alert Log 파일: $ALERT_LOG_FILE"
echo "SQL 구문 모니터링 시작..."
echo "================================"

# Alert Log에서 SQL 관련 항목 실시간 모니터링
tail -f "$ALERT_LOG_FILE" | grep -E "(PARSING|EXEC|SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER)" --line-buffered | while read line; do
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $line"
done
