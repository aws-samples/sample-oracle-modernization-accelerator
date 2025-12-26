#!/bin/bash

# Simple test script that uses the original (non-repackaged) JAR

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../../.." && pwd)"
ORIG_JAR="$PROJECT_ROOT/target/mma-sc-mcp-server-1.0.0.jar.original"

if [ ! -f "$ORIG_JAR" ]; then
    echo "Error: Original JAR not found. Run: ./mvnw clean package"
    exit 1
fi

# Compile test runner
cd "$SCRIPT_DIR"
if [ ! -f "TestRunner.class" ] || [ "TestRunner.java" -nt "TestRunner.class" ]; then
    CP=$(cd "$PROJECT_ROOT" && ./mvnw dependency:build-classpath -q -DincludeScope=runtime -Dmdep.outputFile=/dev/stdout 2>/dev/null)
    javac -cp "$ORIG_JAR:$CP" TestRunner.java 2>/dev/null
fi

# Run test (suppress SLF4J warnings by filtering stderr)
CP=$(cd "$PROJECT_ROOT" && ./mvnw dependency:build-classpath -q -DincludeScope=runtime -Dmdep.outputFile=/dev/stdout 2>/dev/null)
java -Dorg.slf4j.simpleLogger.defaultLogLevel=error -cp ".:$ORIG_JAR:$CP" TestRunner "$@" 2> >(grep -v "SLF4J" >&2)
