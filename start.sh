#!/bin/bash

# QuantRift - One-Click Startup Script
# Kills existing processes and starts backend + frontend services

set -e

echo "=================================================="
echo "🚀 QuantRift Startup Script"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to kill process on a port
kill_port() {
    local port=$1
    echo -e "${YELLOW}Checking port ${port}...${NC}"
    if lsof -ti:${port} > /dev/null 2>&1; then
        echo -e "${RED}Killing process on port ${port}${NC}"
        lsof -ti:${port} | xargs kill -9 2>/dev/null || true
        sleep 1
    else
        echo -e "${GREEN}Port ${port} is free${NC}"
    fi
}

# Kill existing processes
echo ""
echo "📦 Step 1: Cleaning up existing processes..."
kill_port 8000
kill_port 3000

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Start Backend
echo ""
echo "=================================================="
echo "🔧 Step 2: Starting Backend (Port 8000)..."
echo "=================================================="
cd "${SCRIPT_DIR}/backend/api"

if [ ! -f "server.py" ]; then
    echo -e "${RED}Error: server.py not found in backend/api/${NC}"
    exit 1
fi

nohup python server.py > "${SCRIPT_DIR}/backend.log" 2>&1 &
BACKEND_PID=$!
echo -e "${GREEN}Backend started with PID: ${BACKEND_PID}${NC}"
echo "Waiting for backend to initialize..."
sleep 3

# Check if backend is running
if ! lsof -ti:8000 > /dev/null 2>&1; then
    echo -e "${RED}Error: Backend failed to start. Check backend.log${NC}"
    tail -20 "${SCRIPT_DIR}/backend.log"
    exit 1
fi
echo -e "${GREEN}✓ Backend is running${NC}"

# Start Frontend
echo ""
echo "=================================================="
echo "🎨 Step 3: Starting Frontend (Port 3000)..."
echo "=================================================="
cd "${SCRIPT_DIR}/frontend"

if [ ! -f "package.json" ]; then
    echo -e "${RED}Error: package.json not found in frontend/${NC}"
    exit 1
fi

nohup npm run dev > "${SCRIPT_DIR}/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo -e "${GREEN}Frontend started with PID: ${FRONTEND_PID}${NC}"
echo "Waiting for frontend to initialize..."
sleep 5

# Check if frontend is running
if ! lsof -ti:3000 > /dev/null 2>&1; then
    echo -e "${RED}Error: Frontend failed to start. Check frontend.log${NC}"
    tail -20 "${SCRIPT_DIR}/frontend.log"
    exit 1
fi
echo -e "${GREEN}✓ Frontend is running${NC}"

# Final status
echo ""
echo "=================================================="
echo "✅ QuantRift Services Started Successfully!"
echo "=================================================="
echo ""
echo -e "${BLUE}Frontend:${NC}"
echo "  • URL: http://localhost:3000"
echo "  • Log: ${SCRIPT_DIR}/frontend.log"
echo ""
echo -e "${BLUE}Backend:${NC}"
echo "  • API: http://localhost:8000"
echo "  • Docs: http://localhost:8000/docs"
echo "  • ReDoc: http://localhost:8000/redoc"
echo "  • Log: ${SCRIPT_DIR}/backend.log"
echo ""
echo -e "${YELLOW}To stop services:${NC}"
echo "  • Kill ports: lsof -ti:8000 | xargs kill -9 && lsof -ti:3000 | xargs kill -9"
echo "  • Or use: ./stop.sh (if available)"
echo ""
echo -e "${GREEN}Happy analyzing!${NC}"
echo "=================================================="

