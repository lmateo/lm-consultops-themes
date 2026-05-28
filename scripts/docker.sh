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

Optional flags:
  --dev                         Enable bind mount (docker-compose.dev.yml)
EOF
}

ACTION="help"
BUILD_FLAG=0
DEV_MODE=0

for arg in "$@"; do
  case "$arg" in
    --dev)
      DEV_MODE=1
      ;;
    --build)
      BUILD_FLAG=1
      ;;
    up|down|restart|rebuild|logs|ps|shell|clean|help|-h|--help)
      ACTION="$arg"
      ;;
  esac
done

COMPOSE_ARGS=()
if [[ "$DEV_MODE" == "1" ]]; then
  COMPOSE_ARGS=(-f docker-compose.yml -f docker-compose.dev.yml)
fi

case "$ACTION" in
  help|-h|--help)
    usage
    ;;
  up)
    ensure_env
    ARGS=(up)
    [[ "$BUILD_FLAG" == "1" || "${BUILD:-}" == "1" ]] && ARGS+=(--build)
    ARGS+=(-d)
    compose "${COMPOSE_ARGS[@]}" "${ARGS[@]}"
    echo
    echo "App: ${APP_URL}"
    ;;
  down)
    compose "${COMPOSE_ARGS[@]}" down
    ;;
  restart)
    ensure_env
    compose "${COMPOSE_ARGS[@]}" down
    ARGS=(up -d)
    [[ "$BUILD_FLAG" == "1" || "${BUILD:-}" == "1" ]] && ARGS+=(--build)
    compose "${COMPOSE_ARGS[@]}" "${ARGS[@]}"
    echo
    echo "App: ${APP_URL}"
    ;;
  rebuild)
    ensure_env
    compose "${COMPOSE_ARGS[@]}" build --no-cache
    compose "${COMPOSE_ARGS[@]}" up -d
    echo
    echo "App: ${APP_URL}"
    ;;
  logs)
    compose "${COMPOSE_ARGS[@]}" logs -f web
    ;;
  ps)
    compose "${COMPOSE_ARGS[@]}" ps
    ;;
  shell)
    compose "${COMPOSE_ARGS[@]}" exec web sh
    ;;
  clean)
    compose "${COMPOSE_ARGS[@]}" down -v --remove-orphans
    ;;
  *)
    echo "Unknown action: $ACTION" >&2
    usage >&2
    exit 1
    ;;
esac
