#!/bin/bash
# Quick start script for the Flask server

echo "Starting Remote Mixer Flask Server..."
echo "======================================="
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
