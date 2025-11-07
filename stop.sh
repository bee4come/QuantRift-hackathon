#!/bin/bash

# QuantRift - Stop Script
# Stops backend and frontend services

echo "=================================================="
echo "🛑 QuantRift Stop Script"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Function to kill process on a port
kill_port() {
    local port=$1
    echo -e "${YELLOW}Checking port ${port}...${NC}"
    if lsof -ti:${port} > /dev/null 2>&1; then
        echo -e "${RED}Killing process on port ${port}${NC}"
        lsof -ti:${port} | xargs kill -9 2>/dev/null || true
        sleep 1
        echo -e "${GREEN}✓ Port ${port} is now free${NC}"
    else
        echo -e "${GREEN}Port ${port} is already free${NC}"
    fi
}

echo ""
echo "Stopping services..."
kill_port 8000
kill_port 3000

echo ""
echo "=================================================="
echo -e "${GREEN}✅ All services stopped${NC}"
echo "=================================================="

