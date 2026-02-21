#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

# Parse flags
BUILD=""
OBSERVABILITY=""
DETACH="-d"
for arg in "$@"; do
    case "$arg" in
        --build)      BUILD="--build" ;;
        --obs)        OBSERVABILITY="yes" ;;
        --foreground) DETACH="" ;;
        --help|-h)
            echo "Usage: start.sh [OPTIONS]"
            echo "  --build       Rebuild images before starting"
            echo "  --obs         Include Prometheus + Grafana"
            echo "  --foreground  Run in foreground (show logs)"
            exit 0 ;;
    esac
done

if [ -n "$OBSERVABILITY" ]; then
    echo "Starting MCPFarm + observability stack..."
    docker compose -f docker-compose.yml -f docker-compose.observability.yml up $BUILD $DETACH
else
    echo "Starting MCPFarm..."
    docker compose up $BUILD $DETACH
fi

if [ -n "$DETACH" ]; then
    echo ""
    echo "Services running. Endpoints:"
    echo "  Gateway:  http://localhost:8000"
    echo "  Frontend: http://localhost:3100"
    echo "  Health:   http://localhost:8000/health"
    echo "  Metrics:  http://localhost:8000/metrics"
    if [ -n "$OBSERVABILITY" ]; then
        echo "  Grafana:  http://localhost:3000  (admin/mcpfarm)"
        echo "  Prometheus: http://localhost:9090"
    fi
    echo ""
    echo "Logs: docker compose logs -f"
fi
