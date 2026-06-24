#!/bin/bash
# OMA environment variable settings (auto-generated)
# Project: oma
# Creation time: Wed Jun 17 09:12:46 UTC 2026

export APPLICATION_NAME="oma"
export AWS_REGION="ap-northeast-2"
export BEDROCK_MODEL_ID="global.anthropic.claude-opus-4-7"
export BEDROCK_REGION="ap-northeast-2"
export DMS_MIGRATION_PROJECT_ARN="arn:aws:dms:ap-northeast-2:896586841913:migration-project:T3FO5BVJLRGJJDVPCTO3S3J2UM"
export DMS_SC_S3_BUCKET="oma-dms-sc-896586841913"
export LANGUAGE="en"
export MAPPER_WORK_DIR="${OMA_BASE_DIR}/app/mappers"
export MAX_WORKERS="7"
export MYSQL_DATABASE="wmson"
export MYSQL_HOST="omabox-stack-aurora-cluster.cluster-chgmek0wsdgp.ap-northeast-2.rds.amazonaws.com"
export MYSQL_PASSWORD="welcome1"
export MYSQL_PORT="3306"
export MYSQL_USER="wmson"
export OMA_BASE_DIR="/home/ec2-user/workspace/oma"
export OMA_TYPE_HANDLERS="com.oma.typehandler.CodeDescTypeHandler,com.oma.typehandler.IcomCodeDescTypeHandler,com.oma.typehandler.UrMstDescTypeHandler"
export ORACLE_CONN_TYPE="service"
export ORACLE_DICT_PATH="${OMA_BASE_DIR}/app/output/oracle_dictionary.json"
export ORACLE_HOME="/home/ec2-user/oracle"
export ORACLE_HOST="10.0.139.149"
export ORACLE_PASSWORD="welcome1"
export ORACLE_PORT="1521"
export ORACLE_SCHEMA="WMSON"
export ORACLE_SID="ORCLPDB1"
export ORACLE_USER="WMSON"
export PGDATABASE="wmson"
export PGHOST="omabox-stack-aurora-cluster.cluster-chgmek0wsdgp.ap-northeast-2.rds.amazonaws.com"
export PGPASSWORD="welcome1"
export PGPORT="5432"
export PGSCHEMA="wmson"
export PGUSER="wmson"
export SOURCE_WORKSPACE="/home/ec2-user/workspace/source"
export TARGET_DB_TYPE="postgres"
export TARGET_WORKSPACE="/home/ec2-user/workspace/target"

# NLS Environment Variables
export NLS_DATE_FORMAT=
export NLS_LANG=

# Database Connection Aliases
alias sqlplus-oma='sqlplus $ORACLE_ADM_USER/$ORACLE_ADM_PASSWORD@$ORACLE_HOST:1521/$ORACLE_SID'
