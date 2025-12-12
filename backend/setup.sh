#!/bin/bash
set -e

# Load environment variables
set -a
source .env
set +a

# Create data directories
mkdir -p "$DATA_PATH"/{esdata,mongodata}

# Set proper ownership for Docker container users
# elasticsearch runs as uid 1000, mongodb runs as uid 999
chown -R 1000:1000 "$DATA_PATH"/esdata
chown -R 999:999 "$DATA_PATH"/mongodata

echo "✓ Data directories initialized successfully"
