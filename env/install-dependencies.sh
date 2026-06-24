#!/usr/bin/env bash
# OMA - Complete Dependencies Installation Script
# Installs all required dependencies for Oracle to PostgreSQL/MySQL migration
# Supports: Amazon Linux 2023, RHEL, CentOS, Ubuntu, Debian

set -euo pipefail

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Log functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo ""
log_info "=========================================="
log_info "  OMA - Dependencies Installation"
log_info "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    SUDO=""
    log_warning "Running as root"
else
    SUDO="sudo"
fi

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VERSION=$VERSION_ID
else
    log_error "Cannot detect OS version"
    exit 1
fi

log_info "Detected OS: $OS $VERSION"
echo ""

# ============================================
# 1. System Packages
# ============================================
log_info "=== Step 1: Installing System Packages ==="
echo ""

if [ "$OS" = "amzn" ] || [ "$OS" = "rhel" ] || [ "$OS" = "centos" ]; then
    log_info "Installing packages via dnf/yum..."

    # Use dnf for Amazon Linux 2023, yum for older versions
    if command -v dnf &> /dev/null; then
        PKG_MANAGER="dnf"
    else
        PKG_MANAGER="yum"
    fi

    $SUDO $PKG_MANAGER update -y
    $SUDO $PKG_MANAGER install -y \
        python3.11 \
        python3.11-pip \
        python3.11-devel \
        java-21-amazon-corretto-devel \
        maven \
        git \
        wget \
        curl \
        unzip \
        jq \
        tree \
        gcc \
        gcc-c++ \
        make \
        openssl-devel \
        libffi-devel \
        libnsl \
        libaio \
        postgresql16 \
        postgresql16-devel \
        python3-psycopg2

elif [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
    log_info "Installing packages via apt..."
    $SUDO apt-get update
    $SUDO apt-get install -y \
        python3.11 \
        python3.11-pip \
        python3.11-dev \
        openjdk-21-jdk \
        maven \
        git \
        wget \
        curl \
        unzip \
        jq \
        tree \
        gcc \
        g++ \
        make \
        libssl-dev \
        libffi-dev \
        postgresql-client \
        libpq-dev
else
    log_warning "Unsupported OS: $OS"
    log_warning "Please install dependencies manually"
    exit 1
fi

log_success "System packages installed"
echo ""

# ============================================
# 2. Python Packages
# ============================================
log_info "=== Step 2: Installing Python Packages ==="
echo ""

log_info "Upgrading pip..."
python3.11 -m pip install --user --upgrade pip setuptools wheel

echo ""
log_info "Installing core packages..."
python3.11 -m pip install --user \
    boto3 \
    botocore \
    anthropic \
    oracledb \
    psycopg2-binary \
    pymysql \
    openpyxl \
    lxml \
    beautifulsoup4 \
    httpx \
    aiohttp \
    asyncpg \
    click \
    jsonschema

log_success "Python packages installed"
echo ""

# ============================================
# 3. Java & Maven Verification
# ============================================
log_info "=== Step 3: Verifying Java & Maven ==="
echo ""

if command -v java &> /dev/null; then
    JAVA_VERSION=$(java -version 2>&1 | head -n 1)
    log_success "Java: $JAVA_VERSION"
else
    log_error "Java not found"
fi

if command -v mvn &> /dev/null; then
    MVN_VERSION=$(mvn -version 2>&1 | head -n 1)
    log_success "Maven: $MVN_VERSION"
else
    log_error "Maven not found"
fi

# Set JAVA_HOME if not set
if [ -z "${JAVA_HOME:-}" ]; then
    if [ -d "/usr/lib/jvm/java-21-amazon-corretto" ]; then
        export JAVA_HOME="/usr/lib/jvm/java-21-amazon-corretto"
    elif [ -d "/usr/lib/jvm/java-21-openjdk"* ]; then
        export JAVA_HOME=$(ls -d /usr/lib/jvm/java-21-openjdk* | head -1)
    fi

    if [ -n "${JAVA_HOME:-}" ]; then
        log_info "Set JAVA_HOME=$JAVA_HOME"

        # Add to .bashrc if not already present
        if ! grep -q "export JAVA_HOME=" ~/.bashrc; then
            echo "" >> ~/.bashrc
            echo "# Java Home" >> ~/.bashrc
            echo "export JAVA_HOME=$JAVA_HOME" >> ~/.bashrc
            log_info "Added JAVA_HOME to ~/.bashrc"
        fi
    fi
fi

echo ""

# ============================================
# 4. Database Clients
# ============================================
log_info "=== Step 4: Verifying Database Clients ==="
echo ""

# PostgreSQL client
if command -v psql &> /dev/null; then
    PSQL_VERSION=$(psql --version)
    log_success "PostgreSQL client: $PSQL_VERSION"
else
    log_warning "psql not found (PostgreSQL client)"
fi

# MySQL client (optional)
if command -v mysql &> /dev/null; then
    MYSQL_VERSION=$(mysql --version)
    log_success "MySQL client: $MYSQL_VERSION"
else
    log_info "MySQL client not found (install later if needed: $PKG_MANAGER install mysql)"
fi

echo ""

# ============================================
# 5. Oracle Instant Client Installation
# ============================================
log_info "=== Step 5: Installing Oracle Instant Client ==="
echo ""

ORACLE_HOME="$HOME/oracle"

if [ -d "$ORACLE_HOME" ] && [ -f "$ORACLE_HOME/sqlplus" ]; then
    log_success "Oracle Instant Client already installed: $ORACLE_HOME"
else
    log_info "Downloading Oracle Instant Client 19.26..."

    cd /tmp

    # Download Oracle Instant Client
    log_info "Downloading Basic package..."
    wget -q https://download.oracle.com/otn_software/linux/instantclient/1926000/instantclient-basic-linux.x64-19.26.0.0.0dbru.zip

    log_info "Downloading SQL*Plus..."
    wget -q https://download.oracle.com/otn_software/linux/instantclient/1926000/instantclient-sqlplus-linux.x64-19.26.0.0.0dbru.zip

    log_info "Downloading Tools..."
    wget -q https://download.oracle.com/otn_software/linux/instantclient/1926000/instantclient-tools-linux.x64-19.26.0.0.0dbru.zip

    # Extract
    log_info "Extracting packages..."
    unzip -q instantclient-basic-linux.x64-19.26.0.0.0dbru.zip
    unzip -q -o instantclient-sqlplus-linux.x64-19.26.0.0.0dbru.zip
    unzip -q -o instantclient-tools-linux.x64-19.26.0.0.0dbru.zip

    # Move to home directory
    log_info "Installing to $ORACLE_HOME..."
    rm -rf "$ORACLE_HOME"
    mv instantclient_19_26 "$ORACLE_HOME"

    # Cleanup
    rm -f instantclient-*.zip

    # Set environment variables
    log_info "Setting environment variables..."

    if ! grep -q "export ORACLE_HOME=" ~/.bashrc; then
        echo "" >> ~/.bashrc
        echo "# Oracle Instant Client" >> ~/.bashrc
        echo "export ORACLE_HOME=$ORACLE_HOME" >> ~/.bashrc
        echo 'export LD_LIBRARY_PATH=$ORACLE_HOME:$LD_LIBRARY_PATH' >> ~/.bashrc
        echo 'export PATH=$ORACLE_HOME:$PATH' >> ~/.bashrc
        log_info "Added ORACLE_HOME to ~/.bashrc"
    fi

    export LD_LIBRARY_PATH=$ORACLE_HOME:${LD_LIBRARY_PATH:-}
    export PATH=$ORACLE_HOME:$PATH

    log_success "Oracle Instant Client installed: $ORACLE_HOME"
fi

# Verify Oracle client
if command -v sqlplus &> /dev/null; then
    SQLPLUS_VERSION=$(sqlplus -version 2>&1 | grep "Release" || echo "Oracle SQL*Plus")
    log_success "Oracle SQL*Plus: $SQLPLUS_VERSION"
else
    log_warning "sqlplus not found in PATH"
fi

echo ""

# ============================================
# 6. AWS CLI Verification
# ============================================
log_info "=== Step 6: Verifying AWS CLI ==="
echo ""

if command -v aws &> /dev/null; then
    AWS_VERSION=$(aws --version)
    log_success "AWS CLI: $AWS_VERSION"
else
    log_warning "AWS CLI not found"
    log_info "Install AWS CLI: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
fi

echo ""

# ============================================
# 7. Claude Code CLI Verification
# ============================================
log_info "=== Step 7: Verifying Claude Code CLI ==="
echo ""

if command -v claude &> /dev/null; then
    CLAUDE_VERSION=$(claude --version 2>&1 || echo "Claude Code CLI")
    log_success "Claude Code CLI: $CLAUDE_VERSION"
else
    log_warning "Claude Code CLI not found"
    log_info "Install Claude Code: https://claude.com/claude-code"
fi

echo ""

# ============================================
# Final Summary
# ============================================
log_info "=========================================="
log_info "  Installation Summary"
log_info "=========================================="
echo ""

log_success "✓ System packages installed"
log_success "✓ Python 3.11 and packages installed"
log_success "✓ Java 21 and Maven installed"
log_success "✓ Database clients verified"
log_success "✓ Oracle Instant Client installed"

echo ""
log_info "Important: Reload your shell environment:"
echo ""
echo "  source ~/.bashrc"
echo ""
echo "Or restart your terminal session."
echo ""

log_info "Next steps:"
echo ""
echo "  1. Configure oma.properties:"
echo "     cd /home/ec2-user/workspace/oma/env"
echo "     vi oma.properties"
echo ""
echo "  2. Deploy infrastructure:"
echo "     bash deploy-omabox.sh -o 1  # Setup Secrets Manager"
echo "     bash deploy-omabox.sh -o 2  # Deploy CloudFormation"
echo ""
echo "  3. Start migration:"
echo "     cd /home/ec2-user/workspace/oma/schema/postgresql/scripts"
echo "     python3.11 run_migration.py"
echo ""

log_success "Installation completed successfully!"
