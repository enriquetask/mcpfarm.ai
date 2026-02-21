#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "Restarting MCPFarm..."

# Pass through flags to stop/start
OBS_FLAG=""
BUILD_FLAG="--build"
for arg in "$@"; do
    case "$arg" in
        --obs)      OBS_FLAG="--obs" ;;
        --no-build) BUILD_FLAG="" ;;
    esac
done

# Stop compose services
if [ -n "$OBS_FLAG" ]; then
    docker compose -f docker-compose.yml -f docker-compose.observability.yml down
else
    docker compose down
fi

# Clean up gateway-spawned containers (created via Docker SDK, not compose)
ORPHANS=$(docker ps -aq --filter "label=mcpfarm.managed=true" 2>/dev/null || true)
if [ -n "$ORPHANS" ]; then
    echo "Removing gateway-managed orphan containers..."
    docker rm -f $ORPHANS 2>/dev/null || true
fi

# Start
if [ -n "$OBS_FLAG" ]; then
    docker compose -f docker-compose.yml -f docker-compose.observability.yml up $BUILD_FLAG -d
else
    docker compose up $BUILD_FLAG -d
fi

echo ""
echo "Restarted. Waiting for health..."
sleep 3

# Quick health check
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo "Gateway: healthy"
else
    echo "Gateway: still starting (check: docker compose logs -f gateway)"
fi
