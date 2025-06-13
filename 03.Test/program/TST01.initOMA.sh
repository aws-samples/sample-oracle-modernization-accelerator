#!/bin/bash

## Install utilities
sudo apt install -y unzip

curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

## Oracle Instant Client Setup

wget https://download.oracle.com/otn_software/linux/instantclient/1926000/instantclient-basic-linux.x64-19.26.0.0.0dbru.zip
wget https://download.oracle.com/otn_software/linux/instantclient/1926000/instantclient-sqlplus-linux.x64-19.26.0.0.0dbru.zip
wget https://download.oracle.com/otn_software/linux/instantclient/1926000/instantclient-tools-linux.x64-19.26.0.0.0dbru.zip
wget https://download.oracle.com/otn_software/linux/instantclient/1926000/instantclient-jdbc-linux.x64-19.26.0.0.0dbru.zip

unzip -o instantclient-basic-linux.x64-19.26.0.0.0dbru.zip
unzip -o instantclient-sqlplus-linux.x64-19.26.0.0.0dbru.zip
unzip -o instantclient-tools-linux.x64-19.26.0.0.0dbru.zip
unzip -o instantclient-jdbc-linux.x64-19.26.0.0.0dbru.zip

sudo ln -s /usr/lib/x86_64-linux-gnu/libaio.so.1t64 ${ORACLE_HOME}/libaio.so.1

## Set Oracle Environment Variables
ORCLSECRETARN=`aws secretsmanager list-secrets --filters Key="name",Values="oma-secret-oracle-admin" --query 'SecretList[*].ARN' | jq -r '.[0]'`

echo $ORCLSECRETARN

ORCLCREDS=`aws secretsmanager get-secret-value --secret-id $ORCLSECRETARN --region us-east-1 | jq -r '.SecretString'`

export ORCL_ADM_USER="`echo $ORCLCREDS | jq -r '.username'`"
export ORCL_ADM_PWD="`echo $ORCLCREDS | jq -r '.password'`"
export ORCL_HOST="`echo $ORCLCREDS | jq -r '.host'`"
export ORCL_PORT="`echo $ORCLCREDS | jq -r '.port'`"
export ORCL_SID="`echo $ORCLCREDS | jq -r '.dbname'`"
export ORACLE_HOME=/home/ubuntu/instantclient_19_26

echo "" >> /home/ubuntu/.profile
echo "## Oracle Env ##" >> /home/ubuntu/.profile
echo "" >> /home/ubuntu/.profile

echo "export ORACLE_HOME=$ORACLE_HOME" >> /home/ubuntu/.profile
echo "export ORACLE_SID=$ORCL_SID" >> /home/ubuntu/.profile
echo "export ORACLE_ADM_USER=$ORCL_ADM_USER" >> /home/ubuntu/.profile
echo "export ORACLE_ADM_PASSWORD=$ORCL_ADM_PWD" >> /home/ubuntu/.profile
echo "export LD_LIBRARY_PATH=$ORACLE_HOME" >> /home/ubuntu/.profile
echo "export PATH=$PATH:$ORACLE_HOME" >> /home/ubuntu/.profile

ORCLSECRETARN=`aws secretsmanager list-secrets --filters Key="name",Values="oma-secret-oracle-service" --query 'SecretList[*].ARN' | jq -r '.[0]'`

echo $ORCLSECRETARN

ORCLCREDS=`aws secretsmanager get-secret-value --secret-id $ORCLSECRETARN --region us-east-1 | jq -r '.SecretString'`

export ORCL_SVC_USER="`echo $ORCLCREDS | jq -r '.username'`"
export ORCL_SVC_PWD="`echo $ORCLCREDS | jq -r '.password'`"

echo "export ORACLE_SVC_USER=$ORCL_SVC_USER" >> /home/ubuntu/.profile
echo "export ORACLE_SVC_PASSWORD=$ORCL_SVC_PWD" >> /home/ubuntu/.profile

echo "orcl=(DESCRIPTION=(ADDRESS_LIST=(ADDRESS=(PROTOCOL=TCP)(HOST=$ORCL_HOST)(PORT=$ORCL_PORT)))(CONNECT_DATA=(SID=$ORACLE_SID)))" > $ORACLE_HOME/network/admin/tnsnames.ora


## PostgreSQL Client Setup

sudo apt install postgresql-16 postgresql-contrib-16 -y

## Set PostgreSQL Environment Variables

PGSECRETARN=`aws secretsmanager list-secrets --filters Key="name",Values="oma-secret-postgres-admin" --query 'SecretList[*].ARN' | jq -r '.[0]'`
PGCREDS=`aws secretsmanager get-secret-value --secret-id $PGSECRETARN --region us-east-1 | jq -r '.SecretString'`

export PG_ADM_USER="`echo $PGCREDS | jq -r '.username'`"
export PG_ADM_PWD="`echo $PGCREDS | jq -r '.password'`"
export PG_HOST="`echo $PGCREDS | jq -r '.host'`"
export PG_PORT="`echo $PGCREDS | jq -r '.port'`"
export PG_DB="`echo $PGCREDS | jq -r '.dbname'`"

echo "" >> /home/ubuntu/.profile
echo "## Aurora PostgreSQL Env ##" >> /home/ubuntu/.profile
echo "" >> /home/ubuntu/.profile
echo "export PGHOST=$PG_HOST" >> /home/ubuntu/.profile
echo "export PGDATABASE=$PG_DB" >> /home/ubuntu/.profile
echo "export PG_ADM_USER=$PG_ADM_USER" >> /home/ubuntu/.profile
echo "export PG_ADM_PASSWORD=$PG_ADM_PWD" >> /home/ubuntu/.profile
echo "export PGPORT=$PG_PORT" >> /home/ubuntu/.profile

PGSECRETARN=`aws secretsmanager list-secrets --filters Key="name",Values="oma-secret-postgres-service" --query 'SecretList[*].ARN' | jq -r '.[0]'`
PGCREDS=`aws secretsmanager get-secret-value --secret-id $PGSECRETARN --region us-east-1 | jq -r '.SecretString'`

export PG_SVC_USER="`echo $PGCREDS | jq -r '.username'`"
export PG_SVC_PWD="`echo $PGCREDS | jq -r '.password'`"

echo "export PGUSER=$PG_SVC_USER" >> /home/ubuntu/.profile
echo "export PGPASSWORD=$PG_SVC_PWD" >> /home/ubuntu/.profile

## Create OMA Working Directories
mkdir -p ~/OMA/Database/Assessments/tab_ddl ~/OMA/Database/Test ~/OMA/Transform

## Set OMA Environment Variables
export OMA=/home/ubuntu/OMA
echo "" >> /home/ubuntu/.profile
echo "## OMA Env ##" >> /home/ubuntu/.profile
echo "" >> /home/ubuntu/.profile
echo "export OMA_HOME=$OMA" >> /home/ubuntu/.profile
echo "export OMA_ASSESSMENT=$OMA_HOME/Assessment" >> /home/ubuntu/.profile
echo "export OMA_TEST=$OMA_HOME/Test" >> /home/ubuntu/.profile
echo "export OMA_TRANSFORM=$OMA_HOME/Transform" >> /home/ubuntu/.profile

. .profile

## pg_get_tabledef setup
wget https://github.com/MichaelDBA/pg_get_tabledef/archive/refs/heads/main.zip
unzip main.zip

psql -f /home/ubuntu/pg_get_tabledef-main/pg_get_tabledef.sql

