#!/usr/bin/env bash
# Update and restart local Docker Desktop deployment of openpilot multi-device detection.
# Usage (Git Bash / WSL):
#   ./update_local_docker.sh               # Default pull + recreate
#   ./update_local_docker.sh --build       # Force local rebuild instead of pulling
#   ./update_local_docker.sh --no-health   # Skip health check
#   ./update_local_docker.sh --prune       # Run docker system prune -f (CAUTION)
#   ./update_local_docker.sh --override    # Use docker-compose.override.yml if present (default behavior of compose)
#   ./update_local_docker.sh --prod        # Force production compose (docker-compose.yml + docker-compose.prod.yml)
#   ./update_local_docker.sh --logs        # Attach logs after start
#
# Requirements:
# - Docker Desktop running
# - docker-compose.yml in current directory
# - For rebuild: Dockerfile + requirements.txt present
#
# Exit codes:
# 0 success | 1 docker not available | 2 compose file missing | 3 health failed
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if ! command -v docker >/dev/null 2>&1; then
  echo "[ERROR] docker CLI not found. Start Docker Desktop or install Docker." >&2
  exit 1
fi

if [ ! -f docker-compose.yml ]; then
  echo "[ERROR] docker-compose.yml not found in $SCRIPT_DIR" >&2
  exit 2
fi

USE_OVERRIDE=0
DO_BUILD=0
SKIP_HEALTH=0
DO_PRUNE=0
ATTACH_LOGS=0
USE_PROD=0

for arg in "$@"; do
  case "$arg" in
    --override) USE_OVERRIDE=1 ;;
    --prod) USE_PROD=1 ;;
    --build) DO_BUILD=1 ;;
    --no-health) SKIP_HEALTH=1 ;;
    --prune) DO_PRUNE=1 ;;
    --logs) ATTACH_LOGS=1 ;;
    *) echo "[WARN] Unknown arg: $arg" ;;
  esac
done

SERVICE_NAME="multi-device-detection"
CONTAINER_NAME="openpilot-detection"
IMAGE_REF="kainosit/openpilot:latest"

if [ $DO_PRUNE -eq 1 ]; then
  echo "[INFO] Pruning unused Docker resources (CAUTION)";
  docker system prune -f || true
fi

COMPOSE_CMD=(docker compose)
if [ $USE_PROD -eq 1 ]; then
  if [ ! -f docker-compose.prod.yml ]; then
    echo "[ERROR] --prod requested but docker-compose.prod.yml not found" >&2
    exit 2
  fi
  COMPOSE_CMD=(docker compose -f docker-compose.yml -f docker-compose.prod.yml)
  echo "[INFO] Using production compose files (no local build): docker-compose.yml + docker-compose.prod.yml"
else
  # Default compose will auto-include docker-compose.override.yml if present
  if [ -f docker-compose.override.yml ]; then
    echo "[INFO] Using default compose with override (local build may occur)"
  fi
fi

# Decide pull vs build
if [ $DO_BUILD -eq 1 ]; then
  echo "[INFO] Building local image from Dockerfile"
  "${COMPOSE_CMD[@]}" build --pull || "${COMPOSE_CMD[@]}" build
else
  echo "[INFO] Pulling latest remote image $IMAGE_REF"
  "${COMPOSE_CMD[@]}" pull $SERVICE_NAME || echo "[WARN] Pull failed; you may need to login or build locally."
fi

echo "[INFO] Recreating container"
# Down existing
if docker ps --format '{{.Names}}' | grep -q "^$CONTAINER_NAME$"; then
  "${COMPOSE_CMD[@]}" down --remove-orphans || true
else
  # Ensure any stale stopped container is removed
  docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
fi

# Up
if [ $DO_BUILD -eq 1 ]; then
  "${COMPOSE_CMD[@]}" up -d --build
else
  "${COMPOSE_CMD[@]}" up -d
fi

echo "[INFO] Waiting for container start (5s)"
sleep 5

if [ $SKIP_HEALTH -eq 0 ]; then
  echo "[INFO] Checking health status (timeout 60s)"
  ATTEMPTS=0
  until [ $ATTEMPTS -ge 12 ]; do
    STATUS=$(docker inspect "$CONTAINER_NAME" --format='{{.State.Health.Status}}' 2>/dev/null || echo "unknown")
    if [ "$STATUS" = "healthy" ]; then
      echo "[INFO] Health: healthy"
      break
    else
      echo "[INFO] Health: $STATUS (attempt $((ATTEMPTS+1))/12)"
      sleep 5
      ATTEMPTS=$((ATTEMPTS+1))
    fi
  done
  if [ "$STATUS" != "healthy" ]; then
    echo "[ERROR] Container did not become healthy in expected time." >&2
    exit 3
  fi
else
  echo "[INFO] Skipping health check by user request"
fi

echo "[INFO] Deployed image version:"
docker inspect "$CONTAINER_NAME" --format='Image={{.Config.Image}}' || true

echo "[INFO] Running containers matching openpilot:"
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}' | grep -E 'openpilot|NAME' || true

if [ $ATTACH_LOGS -eq 1 ]; then
  echo "[INFO] Attaching logs (Ctrl+C to detach)"
  "${COMPOSE_CMD[@]}" logs -f --no-color $SERVICE_NAME
fi

echo "[SUCCESS] Local update complete."