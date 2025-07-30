#!/bin/bash

# Script to dynamically update JAVA_SOURCE_FOLDER value in convertOracleJava.md

# Get current JAVA_SOURCE_FOLDER value
CURRENT_JAVA_SOURCE_FOLDER="${JAVA_SOURCE_FOLDER:-'[NOT SET]'}"

# Update the markdown file with current environment variable value
sed -i "s|Current JAVA_SOURCE_FOLDER: .*|Current JAVA_SOURCE_FOLDER: $CURRENT_JAVA_SOURCE_FOLDER|g" convertOracleJava.md

echo "Updated convertOracleJava.md with current JAVA_SOURCE_FOLDER value: $CURRENT_JAVA_SOURCE_FOLDER"
