#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "Stopping MCPFarm services..."

if [ "${1:-}" = "--all" ]; then
    echo "Including observability stack..."
    docker compose -f docker-compose.yml -f docker-compose.observability.yml down
else
    docker compose down
fi

# Clean up gateway-spawned containers (created via Docker SDK, not compose)
# These have the mcpfarm.managed=true label but live outside compose control
ORPHANS=$(docker ps -aq --filter "label=mcpfarm.managed=true" 2>/dev/null || true)
if [ -n "$ORPHANS" ]; then
    echo "Removing gateway-managed orphan containers..."
    docker rm -f $ORPHANS 2>/dev/null || true
fi

echo "Stopped."
