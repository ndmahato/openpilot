#!/usr/bin/env bash
# Build and push the latest container image to Docker Hub.
# This script creates both 'latest' and a date+git tag (e.g., 2025-11-08-abc1234) if git metadata is available.
# Usage:
#   ./push_latest_image.sh                 # Build and push with default tags
#   ./push_latest_image.sh --no-cache      # Force no-cache build
#   ./push_latest_image.sh --platform linux/amd64   # Cross-build for amd64
#   ./push_latest_image.sh --tag extra-tag # Add an extra tag
#   ./push_latest_image.sh --dry-run       # Show actions without pushing
#
# Requirements:
# - Docker login to Docker Hub (docker login)
# - Dockerfile in current directory
# - Network access for dependency downloads
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if ! command -v docker >/dev/null 2>&1; then
  echo "[ERROR] docker CLI not found. Start Docker Desktop or install Docker." >&2
  exit 1
fi

IMAGE_BASE="kainosit/openpilot"
DATE_TAG=$(date +%Y-%m-%d)
GIT_SHA=""
EXTRA_TAG=""
NO_CACHE=0
DRY_RUN=0
PLATFORM=""

if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  GIT_SHA=$(git rev-parse --short HEAD || true)
fi
VERSION_TAG="$DATE_TAG"
if [ -n "$GIT_SHA" ]; then
  VERSION_TAG="$DATE_TAG-$GIT_SHA"
fi

for arg in "$@"; do
  case "$arg" in
    --no-cache) NO_CACHE=1 ;;
    --dry-run) DRY_RUN=1 ;;
    --tag) shift; EXTRA_TAG="$1" ;;
    --platform) shift; PLATFORM="$1" ;;
    *) echo "[WARN] Unknown arg: $arg" ;;
  esac
done

BUILD_ARGS=(docker build -t "$IMAGE_BASE:latest" -t "$IMAGE_BASE:$VERSION_TAG" .)
if [ $NO_CACHE -eq 1 ]; then
  BUILD_ARGS+=(--no-cache)
fi
if [ -n "$PLATFORM" ]; then
  # Use buildx if platform specified
  if ! docker buildx version >/dev/null 2>&1; then
    echo "[ERROR] docker buildx not available; install or create builder (docker buildx create --use)." >&2
    exit 2
  fi
  BUILD_ARGS=(docker buildx build --platform "$PLATFORM" -t "$IMAGE_BASE:latest" -t "$IMAGE_BASE:$VERSION_TAG" .)
  if [ $NO_CACHE -eq 1 ]; then
    BUILD_ARGS+=(--no-cache)
  fi
  # buildx needs --push to push directly, but we'll separate steps if not dry-run
fi

echo "[INFO] Building image tags: latest, $VERSION_TAG"
if [ $DRY_RUN -eq 1 ]; then
  echo "[DRY-RUN] ${BUILD_ARGS[*]}"
else
  "${BUILD_ARGS[@]}"
fi

if [ -n "$EXTRA_TAG" ]; then
  echo "[INFO] Adding extra tag: $EXTRA_TAG"
  if [ $DRY_RUN -eq 1 ]; then
    echo "[DRY-RUN] docker tag $IMAGE_BASE:latest $IMAGE_BASE:$EXTRA_TAG"
  else
    docker tag "$IMAGE_BASE:latest" "$IMAGE_BASE:$EXTRA_TAG"
  fi
fi

if [ $DRY_RUN -eq 1 ]; then
  echo "[DRY-RUN] Would push: $IMAGE_BASE:latest, $IMAGE_BASE:$VERSION_TAG${EXTRA_TAG:+, $IMAGE_BASE:$EXTRA_TAG}" 
  exit 0
fi

# Push tags
for TAG in latest "$VERSION_TAG" "$EXTRA_TAG"; do
  if [ -n "$TAG" ]; then
    echo "[INFO] Pushing $IMAGE_BASE:$TAG"
    docker push "$IMAGE_BASE:$TAG"
  fi
done

echo "[SUCCESS] Image pushed: $IMAGE_BASE:latest, $IMAGE_BASE:$VERSION_TAG${EXTRA_TAG:+, $IMAGE_BASE:$EXTRA_TAG}"