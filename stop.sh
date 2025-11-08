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

# Function to kill process on a port (force kill)
kill_port() {
    local port=$1
    echo -e "${YELLOW}Checking port ${port}...${NC}"
    if lsof -ti:${port} > /dev/null 2>&1; then
        echo -e "${RED}Force killing process on port ${port}${NC}"
        # Try multiple times to ensure process is killed
        for i in {1..3}; do
            lsof -ti:${port} | xargs kill -9 2>/dev/null || true
            sleep 0.5
        done
        # Final check and kill if still running
        if lsof -ti:${port} > /dev/null 2>&1; then
            echo -e "${RED}Process still running, force killing again...${NC}"
            lsof -ti:${port} | xargs kill -9 2>/dev/null || true
            sleep 0.5
        fi
        if lsof -ti:${port} > /dev/null 2>&1; then
            echo -e "${RED}⚠️  Warning: Port ${port} may still be in use${NC}"
        else
            echo -e "${GREEN}✓ Port ${port} is now free${NC}"
        fi
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

