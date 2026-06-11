#!/bin/bash
# NEXUS Server Startup Script

echo "🚀 Starting NEXUS Server..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Run install.sh first."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Create logs directory if not exists
mkdir -p logs

# Start the server
echo "Starting FastAPI server on port 8000..."
python -m nexus.api.server