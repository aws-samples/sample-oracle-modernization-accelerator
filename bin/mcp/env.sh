#!/bin/bash
# Environment Configuration

# DMS SC Project Configuration
export DMS_SC_S3_BUCKET="mma-dms-sc-147671602580"
export DMS_SC_SCHEMA_NAME="DEMO"

# PostgreSQL Configuration
export PG_CONNECTION_TYPE="secretsmanager"
export PG_CONNECTION_DETAIL="arn:aws:secretsmanager:us-east-1:147671602580:secret:MMA-secret-aurora-admin"

# Oracle Configuration
export ORACLE_CONNECTION_TYPE="secretsmanager"
export ORACLE_CONNECTION_DETAIL="arn:aws:secretsmanager:us-east-1:147671602580:secret:MMA-secret-oracle-admin"

# DMS Migration Project
export DMS_MIGRATION_PROJECT_ARN="arn:aws:dms:us-east-1:147671602580:migration-project:MNP3KCYEP5DATEH2OSMBHGZ2DY"
