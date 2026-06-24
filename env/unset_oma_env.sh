#!/bin/bash
# Unset all OMA-related environment variables

# Get all variable names from oma.properties
if [ -f "./oma.properties" ]; then
    # Extract all variable names from COMMON and project sections
    while read -r line || [ -n "$line" ]; do
        # Skip empty lines, comments, and section headers
        [[ -z "$line" || "$line" =~ ^[[:space:]]*# || "$line" =~ ^\[.*\]$ ]] && continue
        
        # Extract key from key=value
        if [[ "$line" =~ ^[[:space:]]*([^=]+)= ]]; then
            key="${BASH_REMATCH[1]}"
            key=$(echo "$key" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
            env_var=$(echo "$key" | tr '[:lower:]' '[:upper:]' | tr ' ' '_')
            unset "$env_var"
            echo "Unset: $env_var"
        fi
    done < "./oma.properties"
fi

# Also unset common OMA variables
unset APPLICATION_NAME
unset OMA_BASE_DIR
unset LANGUAGE
unset AWS_REGION

echo "All OMA environment variables have been unset."
