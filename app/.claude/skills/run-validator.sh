#!/bin/bash
set -euo pipefail

# Load environment variables from .env
if [ -f tools/load_oma_env.sh ]; then
    set -a
    source tools/load_oma_env.sh
    set +a
fi

# Check arguments
if [ $# -lt 3 ]; then
    echo "Usage: $0 <oracle_mapper_dir> <target_mapper_dir> <tc_dir> [target_db]"
    echo "Example: $0 mappers/source mappers/target mappers/convert postgres"
    exit 1
fi

ORACLE_MAPPER_DIR="$1"
TARGET_MAPPER_DIR="$2"
TC_DIR="$3"
TARGET_DB="${4:-postgres}"

# Build classpath with all JARs in lib directory
CLASSPATH="tools/validator/target/mapper-validator-1.0.0.jar"

# Add all JARs from lib directory
for jar in $(find lib -name "*.jar" -type f 2>/dev/null); do
    CLASSPATH="${CLASSPATH}:${jar}"
done

echo "=== MyBatis Mapper Validator ==="
echo ""
echo "Oracle Mappers:  ${ORACLE_MAPPER_DIR}"
echo "Target DB Type:  ${TARGET_DB}"
echo "Target Mappers:  ${TARGET_MAPPER_DIR}"
echo "Test Cases:      ${TC_DIR}"
echo ""

# Run validator with all environment variables
java -cp "${CLASSPATH}" com.oma.validator.MapperValidator \
    "${ORACLE_MAPPER_DIR}" \
    "${TARGET_MAPPER_DIR}" \
    "${TC_DIR}" \
    "${TARGET_DB}"
