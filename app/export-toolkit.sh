#!/usr/bin/env bash
# Export OMA Toolkit for deployment to new sites
# Creates a portable package excluding site-specific data

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

OUTPUT_FILE="${1:-oma-toolkit.tar.gz}"

echo "=========================================="
echo "OMA Toolkit Export"
echo "=========================================="
echo ""
echo "Creating portable package..."
echo "Output: $OUTPUT_FILE"
echo ""

# Check if tar supports --exclude
if tar --version 2>&1 | grep -q "GNU tar"; then
    echo "Using GNU tar"
else
    echo "Warning: Non-GNU tar detected. Some excludes may not work."
fi

# Create archive
tar -czf "$OUTPUT_FILE" \
  --exclude='.env' \
  --exclude='.env.*' \
  --exclude='mappers' \
  --exclude='source' \
  --exclude='target' \
  --exclude='logs/*.log' \
  --exclude='output/*.json' \
  --exclude='extensions/extension.json' \
  --exclude='docs/OGNL_IMPLEMENTATION_GUIDE.md' \
  --exclude='lib/ognl_handlers/ognl_scan_report.json' \
  --exclude='lib/ognl_handlers/*.jar' \
  --exclude='lib/ognl_handlers/com' \
  --exclude='lib/ognl_handlers/org' \
  --exclude='lib/typehandlers/*.jar' \
  --exclude='*.pyc' \
  --exclude='__pycache__' \
  --exclude='tools/validator/target' \
  --exclude='.git' \
  --exclude='.vscode' \
  --exclude='.idea' \
  --exclude='*.swp' \
  --exclude='*.tmp' \
  --exclude='*.bak' \
  --exclude='.DS_Store' \
  .

# Get file size
FILE_SIZE=$(du -h "$OUTPUT_FILE" | cut -f1)

echo ""
echo "=========================================="
echo "Export Complete!"
echo "=========================================="
echo ""
echo "Package: $OUTPUT_FILE"
echo "Size: $FILE_SIZE"
echo ""
echo "Contents:"
echo "  ✓ setup.sh (initial setup script)"
echo "  ✓ tools/ (conversion & validation tools)"
echo "  ✓ .claude/skills/ (Claude Code skills)"
echo "  ✓ README.md (usage guide)"
echo "  ✓ PORTABILITY.md (deployment guide)"
echo ""
echo "Excluded (site-specific):"
echo "  ✗ .env (database credentials)"
echo "  ✗ mappers/ (project data)"
echo "  ✗ extensions/extension.json (project config)"
echo "  ✗ output/ (execution outputs)"
echo ""
echo "Next steps:"
echo "  1. Transfer package to new site:"
echo "     scp $OUTPUT_FILE user@new-site:/path/to/destination/"
echo ""
echo "  2. On new site, extract and setup:"
echo "     tar -xzf $OUTPUT_FILE"
echo "     ./setup.sh"
echo "     nano .env"
echo "     ./.claude/skills/verify-env.sh"
echo ""
echo "See PORTABILITY.md for detailed deployment guide."
echo ""
