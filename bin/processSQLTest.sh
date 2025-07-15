#!/bin/bash

# processSqlTest.sh - Oracle Modernization SQL Test Processing Script
# This script executes a series of test scripts in a specific order

set -e  # Exit on any error (will be overridden for validateEnv.sh)

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to print step header
print_step() {
    local step_num=$1
    local step_name=$2
    echo
    print_status $GREEN "=== Step ${step_num}: ${step_name} ==="
}

# Function to ask user confirmation
ask_confirmation() {
    local message=$1
    while true; do
        read -p "${message} (y/n): " yn
        case $yn in
            [Yy]* ) return 0;;
            [Nn]* ) return 1;;
            * ) echo "Please answer yes (y) or no (n).";;
        esac
    done
}

echo "Starting Oracle Modernization SQL Test Process..."
echo "================================================"

# Step 1: Validate Environment
print_step "1" "Environment Validation"
set +e  # Don't exit on error for this step
./test/validateEnv.sh
validation_result=$?
set -e  # Re-enable exit on error

if [ $validation_result -ne 0 ]; then
    print_status $YELLOW "Warning: Environment validation failed or found missing required variables."
    if ! ask_confirmation "Do you want to continue with the test process?"; then
        print_status $RED "Process aborted by user."
        exit 1
    fi
    print_status $YELLOW "Continuing with test process..."
fi

# Step 2: Get DDL
print_step "2" "Getting DDL"
./test/GetDDL.sh

# Step 3: Convert XML to SQL
print_step "3" "Converting XML to SQL"
python3 ./test/XMLToSQL.py

# Step 4: Get Dictionary
print_step "4" "Getting Dictionary"
python3 ./test/GetDictionary.py

# Step 5: Bind Sampler
print_step "5" "Running Bind Sampler"
python3 ./test/BindSampler.py

# Step 6: Bind Mapper
print_step "6" "Running Bind Mapper"
python3 ./test/BindMapper.py

# Step 7: Save SQL to DB
print_step "7" "Saving SQL to Database"
python3 ./test/SaveSQLToDB.py

# Step 8: Execute and Compare SQL
print_step "8" "Executing and Comparing SQL"
python3 ./test/ExecuteAndCompareSQL.py

# Step 9: Analyze Results
print_step "9" "Analyzing Results"
python3 ./test/AnalyzeResult.py

echo
print_status $GREEN "=== SQL Test Process Completed Successfully ==="
echo "All test steps have been executed."
