#!/bin/bash
# OMA environment variable settings (auto-generated)
# Project: demo
# Creation time: Tue Feb 17 08:10:18 UTC 2026

export APPLICATION_FOLDER="${OMA_BASE_DIR}/demo/application"
export APPLICATION_NAME="demo"
export APP_LOGS_FOLDER="${OMA_BASE_DIR}/demo/logs/application"
export APP_TOOLS_FOLDER="${OMA_BASE_DIR}/bin/application"
export APP_TRANSFORM_FOLDER="${APPLICATION_FOLDER}/transform"
export DBMS_FOLDER="${OMA_BASE_DIR}/demo/database"
export DBMS_LOGS_FOLDER="${OMA_BASE_DIR}/demo/logs/database"
export DMS_MIGRATION_PROJECT_ARN=""arn:aws:dms:us-east-1:122552721004:migration-project:FPCT2MEO7ZEGZCGRXFNBQMS3PM""
export DMS_SC_S3_BUCKET=""mma-dms-sc-122552721004""
export JAVA_SOURCE_FOLDER="/workshop/app/orclsrc/src"
export LANGUAGE="en"
export OMA_BASE_DIR="/home/ec2-user/workspace/oma"
export ORACLE_ADM_PASSWORD="1Qmu0cetyG9u"
export ORACLE_ADM_USER="admin"
export ORACLE_HOST="mma-oracle-source.ce3c4lu4sein.us-east-1.rds.amazonaws.com"
export ORACLE_PORT="1521"
export ORACLE_SID="ORCL"
export ORACLE_SVC_CONNECT_STRING="mma-oracle-source.ce3c4lu4sein.us-east-1.rds.amazonaws.com:1521/ORCL"
export ORACLE_SVC_PASSWORD="1Qmu0cetyG9u"
export ORACLE_SVC_USER="admin"
export ORACLE_SVC_USER_LIST=""DEMO""
export PGDATABASE="demodb"
export PGHOST="mma-aurora-pg-instance.ce3c4lu4sein.us-east-1.rds.amazonaws.com"
export PGPASSWORD="QOZMP^wQ8AlY"
export PGPORT="5432"
export PGUSER="postgres"
export PG_ADM_PASSWORD="QOZMP^wQ8AlY"
export PG_ADM_USER="postgres"
export PG_SVC_PASSWORD="QOZMP^wQ8AlY"
export PG_SVC_USER="postgres"
export SOURCE_DBMS_TYPE="orcl"
export SOURCE_SQL_MAPPER_FOLDER="/workshop/app/orclsrc/src/main/resources/sqlmap"
export TARGET_DBMS_TYPE="postgres"
export TARGET_SQL_MAPPER_FOLDER="/workshop/app/pgsrc/src/main/resources/sqlmap"
export TEST_FOLDER="${OMA_BASE_DIR}/demo/test"
export TEST_LOGS_FOLDER="${OMA_BASE_DIR}/demo/logs/test"
export TRANSFORM_JNDI="jdbc"
export TRANSFORM_RELATED_CLASS="_ALL_"

# PATH setting
export PATH="$APP_TOOLS_FOLDER:$OMA_BASE_DIR/bin:$PATH"

# Alias settings
alias qlog='cd $APP_LOGS_FOLDER/qlogs && $APP_TOOLS_FOLDER/tailLatestLog.sh'

# NLS Environment Variables
export NLS_DATE_FORMAT=
export NLS_LANG=

# Database Connection Aliases
alias sqlplus-oma='sqlplus $ORACLE_ADM_USER/$ORACLE_ADM_PASSWORD@$ORACLE_HOST:1521/$ORACLE_SID'
