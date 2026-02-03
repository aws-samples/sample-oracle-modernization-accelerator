#!/bin/bash

# SQL Test Agent Setup Script

set -e

echo "=== SQL Test Agent Setup ==="

# Check Python version
echo "Checking Python version..."
python3 --version

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
else
    echo "Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "Creating directories..."
mkdir -p logs
mkdir -p reports
mkdir -p config

# Copy example config if .env doesn't exist
if [ ! -f "config/.env" ]; then
    echo "Creating config/.env from example..."
    cp config/.env.example config/.env
    echo "⚠️  Please edit config/.env with your credentials"
else
    echo "config/.env already exists"
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Edit config/.env with your database credentials and API keys"
echo "2. Run tests: pytest"
echo "3. Run agent: python -m agent.orchestrator"
echo ""
