#!/usr/bin/env bash
# Mateo ConsultOps Themes — Docker Compose helpers
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST_PORT="${HOST_PORT:-8010}"
APP_URL="http://localhost:${HOST_PORT}"
cd "$ROOT"

ensure_env() {
  if [[ -f .env ]]; then
    return
  fi
  if [[ ! -f .env.example ]]; then
    echo ".env is missing and .env.example was not found." >&2
    exit 1
  fi
  cp .env.example .env
  if sed --version 2>/dev/null | grep -q GNU; then
    sed -i "s|^BASE_URL=.*|BASE_URL=${APP_URL}|" .env
  else
    sed -i '' "s|^BASE_URL=.*|BASE_URL=${APP_URL}|" .env
  fi
  echo "Created .env from .env.example (BASE_URL set to ${APP_URL})."
}

compose() {
  if docker compose version &>/dev/null; then
    docker compose "$@"
  elif command -v docker-compose &>/dev/null; then
    docker-compose "$@"
  else
    echo "Docker Compose not found. Install Docker Desktop or the compose plugin." >&2
    exit 1
  fi
}

usage() {
  cat <<'EOF'
Docker Compose shortcuts:

  ./scripts/docker.sh up        Start stack in background (--build to rebuild)
  ./scripts/docker.sh down      Stop and remove containers
  ./scripts/docker.sh restart   down, then up
  ./scripts/docker.sh rebuild   Force image rebuild, then start
  ./scripts/docker.sh logs      Follow web service logs
  ./scripts/docker.sh ps        Show container status
  ./scripts/docker.sh shell     Open a shell in the web container
  ./scripts/docker.sh clean     down + remove volumes and orphans
EOF
}

ACTION="${1:-help}"
BUILD="${BUILD:-}"

case "$ACTION" in
  help|-h|--help)
    usage
    ;;
  up)
    ensure_env
    ARGS=(up)
    [[ "${2:-}" == "--build" || "$BUILD" == "1" ]] && ARGS+=(--build)
    ARGS+=(-d)
    compose "${ARGS[@]}"
    echo
    echo "App: ${APP_URL}"
    ;;
  down)
    compose down
    ;;
  restart)
    ensure_env
    compose down
    ARGS=(up -d)
    [[ "${2:-}" == "--build" || "$BUILD" == "1" ]] && ARGS+=(--build)
    compose "${ARGS[@]}"
    echo
    echo "App: ${APP_URL}"
    ;;
  rebuild)
    ensure_env
    compose build --no-cache
    compose up -d
    echo
    echo "App: ${APP_URL}"
    ;;
  logs)
    compose logs -f web
    ;;
  ps)
    compose ps
    ;;
  shell)
    compose exec web sh
    ;;
  clean)
    compose down -v --remove-orphans
    ;;
  *)
    echo "Unknown action: $ACTION" >&2
    usage >&2
    exit 1
    ;;
esac
