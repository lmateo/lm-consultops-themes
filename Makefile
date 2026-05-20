# Docker Compose shortcuts (requires Docker; make optional on Windows — use .\docker.ps1)
COMPOSE := $(shell docker compose version >/dev/null 2>&1 && echo "docker compose" || echo docker-compose)

.PHONY: help docker-up docker-down docker-restart docker-rebuild docker-logs docker-ps docker-shell docker-clean up down restart rebuild logs ps shell clean

help:
	@echo "Docker:"
	@echo "  make up          Start stack (detached)"
	@echo "  make down        Stop containers"
	@echo "  make restart     down then up"
	@echo "  make rebuild     no-cache build then up"
	@echo "  make logs        Follow web logs"
	@echo "  make ps          Container status"
	@echo "  make shell       Shell in web container"
	@echo "  make clean       down with volumes"
	@echo ""
	@echo "Windows (PowerShell): .\\docker.ps1 up | down | restart | ..."

up docker-up:
	$(COMPOSE) up -d --build
	@echo App: http://localhost:8010

down docker-down:
	$(COMPOSE) down

restart docker-restart: down up

rebuild docker-rebuild:
	$(COMPOSE) build --no-cache
	$(COMPOSE) up -d
	@echo App: http://localhost:8010

logs docker-logs:
	$(COMPOSE) logs -f web

ps docker-ps:
	$(COMPOSE) ps

shell docker-shell:
	$(COMPOSE) exec web sh

clean docker-clean:
	$(COMPOSE) down -v --remove-orphans
