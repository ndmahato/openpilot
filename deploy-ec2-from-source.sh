#!/usr/bin/env bash
set -euo pipefail

# Source-based EC2 deployment: clone repo, build image locally, run container.
# Usage:
#   chmod +x deploy-ec2-from-source.sh
#   ./deploy-ec2-from-source.sh [--branch master] [--no-build] [--no-prune]
# Optional env vars:
#   OPENPILOT_REPO (default https://github.com/ndmahato/openpilot.git)
#   OPENPILOT_DIR  (default ~/openpilot)
#   COMPOSE_FILES  (default "docker-compose.yml docker-compose.prod.yml")
#   SERVICE_NAME   (default multi-device-detection)
#   CONTAINER_NAME (default openpilot-detection)

BRANCH="master"
NO_BUILD="false"
NO_PRUNE="false"
for arg in "$@"; do
  case "$arg" in
    --branch) shift; BRANCH="$1" ;;
    --branch=*) BRANCH="${arg#*=}" ;;
    --no-build) NO_BUILD="true" ;;
    --no-prune) NO_PRUNE="true" ;;
  esac
  shift || true
done

OPENPILOT_REPO="${OPENPILOT_REPO:-https://github.com/ndmahato/openpilot.git}"
OPENPILOT_DIR="${OPENPILOT_DIR:-$HOME/openpilot}"
COMPOSE_FILES=(docker-compose.yml docker-compose.prod.yml)
SERVICE_NAME="${SERVICE_NAME:-multi-device-detection}"
CONTAINER_NAME="${CONTAINER_NAME:-openpilot-detection}"
IMAGE_REF="kainosit/openpilot:latest"

log() { echo -e "\033[1;32m[INFO]\033[0m $*"; }
warn() { echo -e "\033[1;33m[WARN]\033[0m $*"; }
err() { echo -e "\033[1;31m[ERROR]\033[0m $*"; }

require_cmd() { command -v "$1" >/dev/null 2>&1 || { err "Missing command: $1"; exit 1; }; }

# Detect OS and install docker if missing
install_docker() {
  if command -v docker >/dev/null 2>&1; then
    log "Docker already installed."; return
  fi
  log "Installing Docker..."
  if [ -f /etc/os-release ]; then
    . /etc/os-release
    case "$ID" in
      ubuntu|debian)
        sudo apt-get update -y
        sudo apt-get install -y ca-certificates curl gnupg
        sudo install -m 0755 -d /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/$ID/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        sudo chmod a+r /etc/apt/keyrings/docker.gpg
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$ID $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
        sudo apt-get update -y
        sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
        sudo usermod -aG docker "$USER" || true
        ;;
      amzn|amazon)
        sudo yum update -y
        sudo amazon-linux-extras install docker -y || sudo yum install docker -y
        sudo systemctl enable docker
        sudo systemctl start docker
        sudo usermod -aG docker "$USER" || true
        ;;
      *)
        warn "Unsupported OS ($ID). Attempting generic install via convenience script."
        curl -fsSL https://get.docker.com | sh
        sudo usermod -aG docker "$USER" || true
        ;;
    esac
  else
    err "Unknown OS. Aborting Docker install."; exit 1
  fi
  log "Docker installation complete. You may need to re-login for group changes to apply."
}

install_docker
require_cmd docker

if [ "$NO_PRUNE" != "true" ]; then
  log "Pruning old stopped containers and dangling images..."
  docker container prune -f || true
  docker image prune -f || true
fi

# Stop and remove existing project containers/images
log "Stopping existing containers matching $CONTAINER_NAME or image $IMAGE_REF..."
for cid in $(docker ps -q --filter "name=$CONTAINER_NAME"); do
  docker stop "$cid" || true
  docker rm "$cid" || true
done
for cid in $(docker ps -q --filter "ancestor=$IMAGE_REF"); do
  docker stop "$cid" || true
  docker rm "$cid" || true
done

log "Removing old project images (kainosit/openpilot and local builds)..."
for img in $(docker images --format '{{.Repository}}:{{.Tag}}' | grep -E '^kainosit/openpilot'); do
  docker rmi "$img" || true
done
# Remove unnamed local images based on Dockerfile label
for img in $(docker images --filter "reference=openpilot*" --format '{{.Repository}}:{{.Tag}}'); do
  docker rmi "$img" || true
done

# Clone or update repository
if [ -d "$OPENPILOT_DIR/.git" ]; then
  log "Repository exists. Fetching and resetting to $BRANCH..."
  git -C "$OPENPILOT_DIR" fetch --all --depth=1
  git -C "$OPENPILOT_DIR" checkout "$BRANCH"
  git -C "$OPENPILOT_DIR" reset --hard origin/"$BRANCH"
else
  log "Cloning repository branch $BRANCH..."
  git clone --depth=1 --branch "$BRANCH" "$OPENPILOT_REPO" "$OPENPILOT_DIR"
fi

cd "$OPENPILOT_DIR"

# Decide compose invocation
COMPOSE_ARGS=(compose)
for f in "${COMPOSE_FILES[@]}"; do
  if [ ! -f "$f" ]; then err "Missing compose file: $f"; exit 2; fi
  COMPOSE_ARGS+=( -f "$f" )
done

if [ "$NO_BUILD" = "true" ]; then
  log "Skipping build (--no-build specified), attempting pull (will build if no image)."
  if ! docker ${COMPOSE_ARGS[@]} pull "$SERVICE_NAME"; then
    warn "Pull failed; performing build as fallback.";
    docker ${COMPOSE_ARGS[@]} build --pull "$SERVICE_NAME"
  fi
else
  log "Building image from source via docker compose build..."
  if ! docker ${COMPOSE_ARGS[@]} build --pull "$SERVICE_NAME"; then
    warn "--pull failed; retrying without --pull"; docker ${COMPOSE_ARGS[@]} build "$SERVICE_NAME"
  fi
fi

log "Starting stack..."
docker ${COMPOSE_ARGS[@]} up -d "$SERVICE_NAME"

log "Waiting 10s for container initialization..."
sleep 10

log "Container status:"; docker ps --filter "name=$CONTAINER_NAME" --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'

log "Inspect health (if defined):"
if docker inspect "$CONTAINER_NAME" --format '{{json .State.Health.Status}}' 2>/dev/null; then
  docker inspect "$CONTAINER_NAME" --format 'Health={{.State.Health.Status}}'
else
  warn "No healthcheck configured."
fi

log "Done. Access application on: http://$(curl -s http://checkip.amazonaws.com):5000"
