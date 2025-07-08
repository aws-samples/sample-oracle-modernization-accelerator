#!/bin/bash

#############################################################################
# Script: DB01.GetDDL.sh
# Description: This script extracts DDL (Data Definition Language) statements
#              for all tables from both Oracle and PostgreSQL databases.
#
# Functionality:
# - First extracts Oracle DDL using admin credentials
# - Then extracts PostgreSQL DDL and appends to the same files
# - Creates comprehensive SQL files with both Oracle and PostgreSQL definitions
# - Includes sample data in CSV format for Oracle tables
#
# Output: Individual SQL files in the tab_ddl directory, one per table,
#         containing both Oracle and PostgreSQL table definitions
#############################################################################

# 환경 변수 확인 함수
check_environment_variables() {
    echo "============================================================"
    echo "환경 변수 확인 중..."
    echo "============================================================"
    
    # 필수 환경 변수 목록
    required_vars=(
        "ORACLE_ADM_USER"
        "ORACLE_ADM_PASSWORD"
        "ORACLE_SVC_USER"
        "PGUSER"
        "PGHOST"
        "PGPORT"
        "PGDATABASE"
        "PGPASSWORD"
    )
    
    # 권장 환경 변수 목록
    recommended_vars=(
        "TEST_FOLDER"
    )
    
    missing_vars=()
    
    echo "필수 환경 변수 확인:"
    for var in "${required_vars[@]}"; do
        if [ -n "${!var}" ]; then
            # 비밀번호는 마스킹하여 표시
            if [[ "$var" == *"PASSWORD"* ]]; then
                echo "✓ $var: $(printf '%*s' ${#!var} | tr ' ' '*')"
            else
                echo "✓ $var: ${!var}"
            fi
        else
            echo "✗ $var: 설정되지 않음"
            missing_vars+=("$var")
        fi
    done
    
    echo ""
    echo "권장 환경 변수 확인:"
    for var in "${recommended_vars[@]}"; do
        if [ -n "${!var}" ]; then
            echo "✓ $var: ${!var}"
        else
            echo "- $var: 설정되지 않음 (기본값: 현재 작업 디렉토리)"
        fi
    done
    
    if [ ${#missing_vars[@]} -ne 0 ]; then
        echo ""
        echo "오류: 다음 환경 변수들이 설정되지 않았습니다:"
        for var in "${missing_vars[@]}"; do
            echo "  - $var"
        done
        echo ""
        echo "환경 변수를 설정한 후 다시 실행해주세요."
        exit 1
    fi
    
    echo ""
    echo "모든 필수 환경 변수가 설정되었습니다."
    echo "============================================================"
}

# 환경 변수 확인 실행
check_environment_variables

# TEST_FOLDER 기반으로 출력 디렉토리 설정
TEST_FOLDER=${TEST_FOLDER:-$(pwd)}
OUTPUT_DIR=$TEST_FOLDER/tab_ddl

echo "출력 디렉토리: $OUTPUT_DIR"

# Create output directory if it doesn't exist
mkdir -p $OUTPUT_DIR
cd $OUTPUT_DIR

echo "==================================================================="
echo "STEP 1: Extracting Oracle DDL"
echo "==================================================================="

# Set parameters for Oracle
SCHEMA_OWNER=$(echo $ORACLE_SVC_USER | tr '[:lower:]' '[:upper:]')
export NLS_LANG=KOREAN_KOREA.AL32UTF8

# Extract Oracle DDL
sqlplus $ORACLE_ADM_USER/$ORACLE_ADM_PASSWORD@orcl << EOF
SET SERVEROUTPUT ON
SET ECHO OFF
SET TERMOUT OFF
ALTER SESSION SET NLS_LANGUAGE = 'KOREAN';
ALTER SESSION SET NLS_TERRITORY = 'KOREA';
ALTER SESSION SET NLS_DATE_FORMAT = 'YYYY-MM-DD HH24:MI:SS';
ALTER SESSION SET NLS_TIMESTAMP_FORMAT = 'YYYY-MM-DD HH24:MI:SS.FF';

exec dbms_metadata.set_transform_param(dbms_metadata.session_transform,'STORAGE',false);
exec dbms_metadata.set_transform_param(dbms_metadata.session_transform,'TABLESPACE',false);
exec dbms_metadata.set_transform_param(dbms_metadata.session_transform,'SEGMENT_ATTRIBUTES',false);
exec dbms_metadata.set_transform_param(dbms_metadata.session_transform,'SQLTERMINATOR',true);
exec dbms_metadata.set_transform_param(dbms_metadata.session_transform,'PRETTY',true);
exec dbms_metadata.set_transform_param(dbms_metadata.session_transform,'BODY',true);
exec dbms_metadata.set_transform_param(dbms_metadata.session_transform,'CONSTRAINTS',false);
exec dbms_metadata.set_transform_param(dbms_metadata.session_transform,'PARTITIONING',false);
set pages 10000 long 100000
set heading off
SPOOL get_ddl_orcl.sql
BEGIN
  FOR tab IN (SELECT table_name 
             FROM dba_tables 
             WHERE owner = '${SCHEMA_OWNER}' 
             ORDER BY table_name) 
  LOOP
    DBMS_OUTPUT.PUT_LINE('SPOOL '||lower(tab.table_name)||'.sql');
    DBMS_OUTPUT.PUT_LINE('SET FEEDBACK OFF');
    DBMS_OUTPUT.PUT_LINE('EXEC DBMS_OUTPUT.PUT_LINE(''/** Source - Oracle DDL **/'');');
    DBMS_OUTPUT.PUT_LINE('SELECT REPLACE(DBMS_METADATA.GET_DDL(''TABLE'','''||tab.table_name||''',''${SCHEMA_OWNER}''), ''"'', '''') FROM DUAL;');
    DBMS_OUTPUT.PUT_LINE('EXEC DBMS_OUTPUT.PUT_LINE(''/** Sample Data, CSV Type **/'');');
    DBMS_OUTPUT.PUT_LINE('SET MARKUP CSV ON QUOTE OFF');
    DBMS_OUTPUT.PUT_LINE('SET HEADING ON');
    DBMS_OUTPUT.PUT_LINE('SELECT * FROM ${SCHEMA_OWNER}.'||tab.table_name||' WHERE ROWNUM<=1;');
    DBMS_OUTPUT.PUT_LINE('SET HEADING OFF');
    DBMS_OUTPUT.PUT_LINE('EXEC DBMS_OUTPUT.PUT_LINE('''');');
    DBMS_OUTPUT.PUT_LINE('EXEC DBMS_OUTPUT.PUT_LINE(''/** Target - PostgreSQL DDL **/'');');
    DBMS_OUTPUT.PUT_LINE('EXEC DBMS_OUTPUT.PUT_LINE('''');');
    DBMS_OUTPUT.PUT_LINE('SET MARKUP CSV OFF');
    DBMS_OUTPUT.PUT_LINE('SPOOL OFF');
    DBMS_OUTPUT.PUT_LINE('/');
  END LOOP;
END;
/
SPOOL OFF
@get_ddl_orcl
EOF

echo "Oracle DDL extraction completed."
echo ""
echo "==================================================================="
echo "STEP 2: Extracting PostgreSQL DDL"
echo "==================================================================="

# Set parameters for PostgreSQL
SCHEMA_NAME=$PGUSER

# Generate script to extract PostgreSQL DDL
psql -At <<EOF
\o ${OUTPUT_DIR}/get_ddl_pg.sh
select 'echo "/** PostgreSQL DDL for '||table_name||' **/" >> ${OUTPUT_DIR}/'||table_name||'.sql; psql -At -c "select pg_get_tabledef('''||table_schema||''', '''||table_name||''', false)" >> ${OUTPUT_DIR}/'||table_name||'.sql' 
from information_schema.tables 
where table_schema='${SCHEMA_NAME}' and table_name not in ('awsdms_validation_failures_v1','sqllist')
order by table_name;
\o
EOF

chmod +x ${OUTPUT_DIR}/get_ddl_pg.sh

echo "PostgreSQL DDL extraction script generated."
echo "Running the script to append PostgreSQL DDL to existing files..."

sh ${OUTPUT_DIR}/get_ddl_pg.sh
rm ${OUTPUT_DIR}/get_ddl_pg.sh

echo "PostgreSQL DDL extraction completed."
echo ""
echo "==================================================================="
echo "DDL extraction process completed successfully!"
echo "Output files are available in: ${OUTPUT_DIR}"
echo "==================================================================="
