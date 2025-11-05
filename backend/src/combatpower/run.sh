#!/bin/bash

# Riot Rift Rewind - Startup Script

echo "======================================"
echo "  Riot Rift Rewind Backend Server"
echo "======================================"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Check if .env exists
if [ ! -f ".env" ]; then
    echo ""
    echo "WARNING: .env file not found!"
    echo "Please create .env file with your RIOT_API_KEY"
    echo ""
    read -p "Enter your Riot API Key: " api_key
    echo "RIOT_API_KEY=$api_key" > .env
    echo "FLASK_ENV=development" >> .env
    echo "FLASK_PORT=5000" >> .env
    echo ".env file created!"
fi

echo ""
echo "Starting server..."
echo "API will be available at: http://localhost:5000"
echo ""

# Run the application
python app.py

