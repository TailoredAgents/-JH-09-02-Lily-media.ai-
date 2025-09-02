#!/bin/bash

# Build script for Render deployment
set -e

echo "🚀 Starting Render build process..."
echo "Python version: $(python --version)"

# Check Python version
PYTHON_VERSION=$(python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')")
echo "Detected Python version: $PYTHON_VERSION"

if [[ "$PYTHON_VERSION" == 3.13.* ]]; then
    echo "❌ ERROR: Python 3.13 detected; pin to Python 3.11.x or update all deploy runtimes"
    exit 1
fi

# Backend setup
echo "📦 Setting up backend..."
python -m pip install --upgrade pip setuptools wheel
pip install -e .

echo "✅ Build completed successfully!"
echo "🌐 Ready for deployment on Render"