#!/bin/bash
# Quick start script for the Flask server

echo "Starting Remote Mixer Flask Server..."
echo "======================================="
echo ""

# Check if UV is installed
if ! command -v uv &> /dev/null; then
    echo "❌ UV package manager is not installed."
    echo ""
    echo "Please install UV using one of the following methods:"
    echo ""
    echo "Option 1: Using Homebrew (macOS)"
    echo "  brew install uv"
    echo ""
    echo "Option 2: Using curl"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo ""
    echo "After installation, restart your shell or run:"
    echo "  source \$HOME/.local/bin/env"
    echo ""
    exit 1
fi

echo "✓ UV is installed"
echo ""

# Source UV environment
source "$HOME/.local/bin/env"

# Navigate to project directory
cd "$(dirname "$0")" || exit

# Install dependencies if needed
echo "Checking dependencies..."
uv sync

echo ""
echo "Starting server on http://localhost:5001"
echo "Press Ctrl+C to stop the server"
echo ""

# Run the Flask app
uv run python app.py
