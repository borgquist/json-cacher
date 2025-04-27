#!/bin/sh
set -e

# Start the fetcher in the background
echo "Starting fetcher.py..."
python fetcher.py &
FETCHER_PID=$!

# Give fetcher a moment to start
sleep 2

# Start the API server (this will become the main process)
echo "Starting api_server.py..."
exec python api_server.py 