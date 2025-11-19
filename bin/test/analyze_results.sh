#!/bin/bash

# Check current directory
if [ ! -f "com/test/mybatis/TestResultAnalyzer.java" ]; then
    echo "❌ TestResultAnalyzer.java file not found."
    echo "Please run from the correct directory: /home/ec2-user/workspace/oma/bin/test"
    exit 1
fi

# Compile
echo "🔧 Compiling..."
javac -cp ".:lib/*" com/test/mybatis/*.java

if [ $? -ne 0 ]; then
    echo "❌ Compilation failed"
    exit 1
fi

echo "✅ Compilation completed"

# Generate analysis report file
REPORT_FILE="out/analysis_report_$(date +%Y%m%d_%H%M%S).md"

# Execute
echo "▶️ Running analysis program..."
echo ""

java -cp ".:lib/*" com.test.mybatis.TestResultAnalyzer | tee "$REPORT_FILE"

echo ""
echo "✅ Analysis completed"
echo "📄 Report file: $REPORT_FILE"

# Automatically fix sorting differences (hide output)
java -cp ".:lib/*" com.test.mybatis.TestResultAnalyzer --fix-sorting > /dev/null 2>&1

# Amazon Q automatic conversion suggestion
echo ""
echo "🤖 Would you like to proceed with automatic SQL statement conversion through Amazon Q? (y/n): "
read -r answer

if [[ "$answer" =~ ^[Yy]$ ]]; then
    echo "🚀 Starting Amazon Q automatic conversion..."
    
    # Check retransform.md file
    if [ ! -f "retransform.md" ]; then
        echo "❌ retransform.md file not found."
        exit 1
    fi
    
    # Generate prompt including environment variable information
    PROMPT="Environment variable information:
  - SOURCE_DBMS_TYPE: ${SOURCE_DBMS_TYPE:-oracle}
  - TARGET_DBMS_TYPE: ${TARGET_DBMS_TYPE:-postgresql}
  - PostgreSQL connection information:
    - PGHOST: ${PGHOST}
    - PGPORT: ${PGPORT:-5432}
    - PGDATABASE: ${PGDATABASE}
    - PGUSER: ${PGUSER}

$(cat retransform.md)"
    
    # Execute kiro-cli chat (including environment variable information)
    kiro-cli chat "$PROMPT"
else
    echo "👋 Analysis completed."
fi
