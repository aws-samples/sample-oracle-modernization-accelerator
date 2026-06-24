#!/usr/bin/env bash
# OMA App - Dependencies Installation Wrapper
# This script calls the centralized installation script

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_DIR="$(cd "$SCRIPT_DIR/../env" && pwd)"
INSTALL_SCRIPT="$ENV_DIR/install-dependencies.sh"

echo ""
echo "=========================================="
echo "  OMA App - Dependencies Installation"
echo "=========================================="
echo ""

# Check if centralized installation script exists
if [ ! -f "$INSTALL_SCRIPT" ]; then
    echo "Error: install-dependencies.sh not found at: $INSTALL_SCRIPT"
    echo ""
    echo "Expected location: /home/ec2-user/workspace/oma/env/install-dependencies.sh"
    echo ""
    echo "Please ensure you have the complete OMA repository structure:"
    echo "  oma/"
    echo "  ├── env/"
    echo "  │   └── install-dependencies.sh"
    echo "  └── app/"
    echo "      └── setup.sh (this script)"
    echo ""
    exit 1
fi

# Run the centralized installation script
echo "Running centralized installation script..."
echo "Location: $INSTALL_SCRIPT"
echo ""

bash "$INSTALL_SCRIPT"

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "  Installation completed successfully!"
    echo "=========================================="
    echo ""
    echo "Next steps for App Migration:"
    echo ""
    echo "  1. Configure oma.properties:"
    echo "     cd /home/ec2-user/workspace/oma/env"
    echo "     vi oma.properties"
    echo ""
    echo "  2. Start Claude Code:"
    echo "     cd /home/ec2-user/workspace/oma/app"
    echo "     claude"
    echo ""
    echo "  3. Run skills in order:"
    echo "     /verify-env"
    echo "     /build-oracle-dict"
    echo "     /split-mappers your-project-name"
    echo "     /convert-sql your-project-name"
    echo "     /merge-mappers your-project-name"
    echo "     /validate your-project-name"
    echo ""
else
    echo ""
    echo "Error: Installation failed with exit code $exit_code"
    exit $exit_code
fi
