#!/bin/bash

# PostgreSQL metadata extraction script
# Extract metadata using direct SQL queries instead of AI

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting PostgreSQL metadata extraction...${NC}"

# Check environment variables
if [ -z "$APP_TRANSFORM_FOLDER" ]; then
    echo -e "${RED}Error: APP_TRANSFORM_FOLDER environment variable is not set.${NC}"
    exit 1
fi

# Output file path
OUTPUT_FILE="$APP_TRANSFORM_FOLDER/oma_metadata.txt"

echo -e "${YELLOW}Output file: $OUTPUT_FILE${NC}"

# Check PostgreSQL connection
echo -e "${BLUE}Checking PostgreSQL connection...${NC}"
if ! psql -c "SELECT version();" > /dev/null 2>&1; then
    echo -e "${RED}Error: Cannot connect to PostgreSQL database.${NC}"
    echo -e "${YELLOW}Please check if the following environment variables are set correctly:${NC}"
    echo -e "${YELLOW}  - PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD${NC}"
    exit 1
fi

echo -e "${GREEN}PostgreSQL connection successful!${NC}"

# Execute metadata extraction SQL
echo -e "${BLUE}Extracting metadata...${NC}"

psql -c "
SELECT 
    table_schema,
    table_name,
    column_name,
    data_type
FROM information_schema.columns 
WHERE table_schema NOT IN (
    'information_schema', 
    'pg_catalog', 
    'pg_toast',
    'aws_commons',
    'aws_oracle_context',
    'aws_oracle_data', 
    'aws_oracle_ext',
    'public'
)
ORDER BY table_schema, table_name, ordinal_position;
" > "$OUTPUT_FILE"

# Check execution result
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Metadata extraction completed successfully!${NC}"
    
    # Validate results
    echo -e "${BLUE}Result validation:${NC}"
    
    # Check file existence
    if [ -f "$OUTPUT_FILE" ]; then
        echo -e "${GREEN}  ✓ File creation confirmed: $OUTPUT_FILE${NC}"
        
        # Check file size
        file_size=$(wc -l < "$OUTPUT_FILE")
        echo -e "${GREEN}  ✓ Total lines: $file_size${NC}"
        
        # Preview first 10 lines
        echo -e "${BLUE}  📋 First 10 lines preview:${NC}"
        head -10 "$OUTPUT_FILE"
        
        echo ""
        
        # Schema statistics
        echo -e "${BLUE}  📊 Table/View count by schema:${NC}"
        grep -v "^-" "$OUTPUT_FILE" | grep -v "table_schema" | awk '{print $1}' | sort | uniq -c | while read count schema; do
            echo -e "${GREEN}    $schema: $count items${NC}"
        done
        
    else
        echo -e "${RED}  ✗ File was not created.${NC}"
        exit 1
    fi
    
else
    echo -e "${RED}❌ Metadata extraction failed.${NC}"
    exit 1
fi

echo -e "${GREEN}🎉 PostgreSQL metadata extraction completed successfully!${NC}"
