#!/bin/bash
# NEXUS Installation Script

echo "🚀 NEXUS B2B Lead Generation & OSINT Intelligence Suite"
echo "Installation Script"
echo ""

# Check Python version
echo "Checking Python version..."
python3 --version
if [ $? -ne 0 ]; then
    echo "❌ Python 3.11+ required"
    exit 1
fi

# Create virtual environment
echo ""
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Install Playwright browsers
echo ""
echo "Installing Playwright browsers..."
playwright install

# Create .env file if not exists
if [ ! -f .env ]; then
    echo ""
    echo "Creating .env file..."
    cat > .env << EOF
# NEXUS Configuration
API_HOST=0.0.0.0
API_PORT=8000

# LLM Settings
LLM_MODEL_PATH=D:/models/Llama-3.2-1B-Instruct-Q4_K_M.gguf
LLM_CONTEXT_SIZE=4096
LLM_THREADS=3

# API Keys
HIBP_API_KEY=your_haveibeenpwned_api_key_here
EOF
    echo "✅ .env file created"
fi

# Create logs directory
mkdir -p logs

# Initialize database
echo ""
echo "Initializing database..."
python3 -c "from nexus.database.repository import repository; print('Database initialized')"

echo ""
echo "✅ Installation complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your configuration"
echo "2. Run: source venv/bin/activate"
echo "3. Run: bash scripts/run_server.sh"
echo ""