#!/bin/bash

echo "======================================"
echo "Multi-Agent Workflow Setup"
echo "======================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

echo "✓ Python is installed: $(python3 --version)"
echo ""

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✓ .env file created"
    echo ""
    echo "⚠️  Please edit .env file and add your NVIDIA_API_KEY"
    echo ""
else
    echo "✓ .env file already exists"
    echo ""
fi

# Ask if user wants to create virtual environment
read -p "Do you want to create a virtual environment? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
        echo "✓ Virtual environment created"
        echo ""
        echo "To activate it, run:"
        echo "  source venv/bin/activate  (Linux/Mac)"
        echo "  venv\\Scripts\\activate     (Windows)"
        echo ""
    else
        echo "✓ Virtual environment already exists"
        echo ""
    fi
fi

# Ask if user wants to install dependencies
read -p "Do you want to install dependencies now? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
    echo ""
    echo "✓ Dependencies installed"
    echo ""
fi

echo "======================================"
echo "Setup Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Edit .env file and add your NVIDIA_API_KEY"
echo "2. Run: python main.py"
echo ""
echo "For examples, run: python examples/basic_usage.py"
echo ""
