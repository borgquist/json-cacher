#!/bin/bash

# Get the script's directory (where requirements.txt and other files are located)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
echo "Script directory: $SCRIPT_DIR"

# Determine shell availability - use sh as fallback
if [ -z "$BASH_VERSION" ]; then
    echo "Note: Running with /bin/sh instead of bash"
    # Consider re-executing with bash if critical
fi

# Determine which Python command to use
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    # Check if python is version 3.x
    PY_VERSION=$(python --version 2>&1 | awk '{print $2}' | cut -d. -f1)
    if [ "$PY_VERSION" -eq 3 ]; then
        PYTHON_CMD="python"
    else
        echo "Error: Python 3 is required but not found"
        exit 1
    fi
else
    echo "Error: Python not found"
    exit 1
fi

echo "Using Python command: $PYTHON_CMD"

# Detect environment
IS_DOCKER=false
if [ -f "/.dockerenv" ] || grep -q docker /proc/self/cgroup 2>/dev/null; then
    IS_DOCKER=true
    echo "Detected Docker environment"
fi

# Only use venv if not in Docker
if [ "$IS_DOCKER" = false ]; then
    # Check for virtual environment and create if it doesn't exist
    VENV_DIR="$SCRIPT_DIR/venv"
    if [ ! -d "$VENV_DIR" ]; then
        echo "Creating virtual environment in $VENV_DIR..."
        $PYTHON_CMD -m venv $VENV_DIR || $PYTHON_CMD -m virtualenv $VENV_DIR
        if [ $? -ne 0 ]; then
            echo "Failed to create virtual environment. Make sure 'venv' module is available."
            echo "You may need to install it: $PYTHON_CMD -m pip install virtualenv"
            echo "Continuing without virtual environment..."
        else
            echo "Virtual environment created."
        fi
    fi

    # Activate the virtual environment
    if [ -f "$VENV_DIR/bin/activate" ]; then
        . "$VENV_DIR/bin/activate" # Using . instead of source for wider shell compatibility
        PYTHON_CMD="python"  # Within the venv, we can just use 'python'
        echo "Virtual environment activated."
    else
        echo "Warning: Could not find activation script for virtual environment."
        echo "Continuing with system Python..."
    fi
else
    echo "Skipping virtual environment in Docker/container environment"
fi

# Check for requirements and install if necessary
if ! $PYTHON_CMD -c "import requests" 2>/dev/null || ! $PYTHON_CMD -c "import flask" 2>/dev/null || ! $PYTHON_CMD -c "import dotenv" 2>/dev/null; then
    echo "Some dependencies are missing. Installing requirements..."
    $PYTHON_CMD -m pip install -r "$SCRIPT_DIR/requirements.txt"
    if [ $? -ne 0 ]; then
        echo "Failed to install dependencies. Please run 'pip install -r $SCRIPT_DIR/requirements.txt' manually."
        exit 1
    fi
    echo "Dependencies installed successfully!"
fi

# Create .env file if it doesn't exist and env.example does
if [ ! -f "$SCRIPT_DIR/.env" ] && [ -f "$SCRIPT_DIR/env.example" ]; then
    echo "Notice: .env file not found, creating from env.example template"
    cp "$SCRIPT_DIR/env.example" "$SCRIPT_DIR/.env"
    echo "Please edit .env file with your actual API credentials and settings"
fi

# Create config.json if it doesn't exist and config.example.json does
if [ ! -f "$SCRIPT_DIR/config.json" ] && [ -f "$SCRIPT_DIR/config.example.json" ]; then
    echo "Notice: config.json file not found, creating from config.example.json template"
    cp "$SCRIPT_DIR/config.example.json" "$SCRIPT_DIR/config.json"
fi

# Environment variables with defaults
export PORT=${PORT:-8000}  # Default port for API server
export TEST_MODE=${TEST_MODE:-false}
export LOG_LEVEL=${LOG_LEVEL:-INFO}  # Default log level

echo "Configuration:"
echo "- API server port: $PORT"
echo "- Test mode: $TEST_MODE"
echo "- Log level: $LOG_LEVEL"

# Change to the script directory before running Python scripts
cd "$SCRIPT_DIR"

# Start the fetcher process in the background
echo "Starting fetcher.py..."
$PYTHON_CMD "$SCRIPT_DIR/fetcher.py" &
FETCHER_PID=$!

# Give fetcher a moment to start
sleep 2

# Start the API server
echo "Starting api_server.py on port $PORT..."
$PYTHON_CMD "$SCRIPT_DIR/api_server.py"

# If API server terminates, also kill the fetcher
kill $FETCHER_PID 2>/dev/null 