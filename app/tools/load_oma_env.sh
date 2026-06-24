#!/bin/bash
# Load environment variables from oma.properties
# Usage: source tools/load_oma_env.sh

# Determine script location
if [ -n "${BASH_SOURCE[0]}" ]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
else
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
fi

APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
OMA_BASE_DIR="$(cd "$APP_DIR/.." && pwd)"
PROPERTIES_FILE="$OMA_BASE_DIR/env/oma.properties"

if [ ! -f "$PROPERTIES_FILE" ]; then
    echo "Error: oma.properties not found at $PROPERTIES_FILE"
    return 1 2>/dev/null || exit 1
fi

# Function to parse and export variables from a section
parse_section() {
    local section=$1
    local in_section=false

    while IFS= read -r line || [ -n "$line" ]; do
        # Skip empty lines and comments
        [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue

        # Check for section headers
        if [[ "$line" =~ ^\[(.*)\] ]]; then
            section_name="${BASH_REMATCH[1]}"
            if [ "$section_name" = "$section" ]; then
                in_section=true
            else
                in_section=false
            fi
            continue
        fi

        # Parse key=value pairs in the target section
        if [ "$in_section" = true ] && [[ "$line" =~ ^[[:space:]]*([^=]+)=(.*)$ ]]; then
            key="${BASH_REMATCH[1]}"
            value="${BASH_REMATCH[2]}"

            # Trim whitespace
            key=$(echo "$key" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
            value=$(echo "$value" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

            # Convert to uppercase
            env_var=$(echo "$key" | tr '[:lower:]' '[:upper:]')

            # Variable expansion (simple ${VAR} replacement)
            # First, expand OMA_BASE_DIR if set
            if [ -n "$OMA_BASE_DIR" ]; then
                value="${value//\$\{OMA_BASE_DIR\}/$OMA_BASE_DIR}"
            fi

            # Export the variable
            export "$env_var"="$value"
        fi
    done < "$PROPERTIES_FILE"
}

# Parse [COMMON] section
parse_section "COMMON"

# Variable name mapping for backward compatibility
# PostgreSQL uses standard PG* variables (already correct in oma.properties)
# Just ensure they're exported

# Export OMA_BASE_DIR for use in variable expansion
export OMA_BASE_DIR="$OMA_BASE_DIR"

# Debug output (optional, comment out in production)
# echo "✓ Loaded environment from: $PROPERTIES_FILE"
# echo "  OMA_BASE_DIR: $OMA_BASE_DIR"
# echo "  BEDROCK_MODEL_ID: $BEDROCK_MODEL_ID"
