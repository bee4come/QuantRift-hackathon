#!/bin/bash
# OP.GG MCP Server Startup Script
# Ensures the MCP server is always working

echo "Starting OP.GG MCP Server Health Check..."

# Function to check MCP server health
check_mcp_health() {
    curl -s -X POST https://mcp-api.op.gg/mcp \
        -H "Content-Type: application/json" \
        -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' \
        | jq -e '.result.tools | length > 0' > /dev/null
}

# Function to start the Flask backend
start_backend() {
    echo "Starting Flask backend..."
    cd /Users/jyeuforever/Documents/Documents\ -\ 74MPM1X21/cursor/front/combatpower
    python app.py &
    BACKEND_PID=$!
    echo "Backend started with PID: $BACKEND_PID"
}

# Function to start the monitor
start_monitor() {
    echo "Starting MCP monitor..."
    cd /Users/jyeuforever/Documents/Documents\ -\ 74MPM1X21/cursor/front/combatpower
    python monitor_opgg_mcp.py &
    MONITOR_PID=$!
    echo "Monitor started with PID: $MONITOR_PID"
}

# Check if MCP server is available
echo "Checking OP.GG MCP server availability..."
if check_mcp_health; then
    echo "✅ OP.GG MCP server is healthy"
else
    echo "❌ OP.GG MCP server is not responding"
    echo "The system will use fallback data until the MCP server is restored"
fi

# Start the backend
start_backend

# Wait a moment for backend to start
sleep 3

# Test the backend API
echo "Testing backend API..."
if curl -s http://localhost:5000/api/health/opgg-mcp | jq -e '.mcp_server_healthy' > /dev/null; then
    echo "✅ Backend API is working"
else
    echo "❌ Backend API is not responding"
fi

# Start the monitor
start_monitor

echo "OP.GG MCP system is now running"
echo "Backend PID: $BACKEND_PID"
echo "Monitor PID: $MONITOR_PID"
echo ""
echo "To stop the system, run:"
echo "kill $BACKEND_PID $MONITOR_PID"
