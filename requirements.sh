#!/bin/bash

# QuantRift - Install Dependencies Script
# Installs all Python and Node.js dependencies for first-time setup

set -e

echo "=================================================="
echo "📦 QuantRift Dependency Installation"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Install Backend Dependencies
echo ""
echo "=================================================="
echo "🐍 Installing Backend Dependencies (Python)..."
echo "=================================================="
cd "${SCRIPT_DIR}/backend"

if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}Error: requirements.txt not found in backend/${NC}"
    exit 1
fi

# Check if Python virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating Python virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate

# Install Python dependencies
echo -e "${YELLOW}Installing Python packages...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

echo -e "${GREEN}✓ Backend dependencies installed${NC}"

# Install Frontend Dependencies
echo ""
echo "=================================================="
echo "📦 Installing Frontend Dependencies (Node.js)..."
echo "=================================================="
cd "${SCRIPT_DIR}/frontend"

if [ ! -f "package.json" ]; then
    echo -e "${RED}Error: package.json not found in frontend/${NC}"
    exit 1
fi

# Install Node.js dependencies
echo -e "${YELLOW}Installing Node.js packages...${NC}"
npm install

echo -e "${GREEN}✓ Frontend dependencies installed${NC}"

# Final status
echo ""
echo "=================================================="
echo "✅ All Dependencies Installed Successfully!"
echo "=================================================="
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "  1. Configure environment variables (.env files)"
echo "  2. Run ./start.sh to start the services"
echo ""
echo -e "${GREEN}Happy coding!${NC}"
echo "=================================================="

