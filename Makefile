.PHONY: help init crawl purge docker docker-rebuild docker-delete

# Default target - show help
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║         Git Repository Crawler with GitIngest             ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "Available targets:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'
	@echo ""

init: ## Install dependencies with uv
	@echo "Installing dependencies..."
	@if [ ! -f pyproject.toml ]; then \
		echo "Error: pyproject.toml not found"; \
		exit 1; \
	fi
	uv sync
	@mkdir -p data
	@echo "Dependencies installed"
	@echo ""

crawl: init ## Crawl repositories from crawl-jobs.txt
	@echo "Starting repository crawler..."
	@if [ ! -f crawl-jobs.txt ]; then \
		echo "Error: crawl-jobs.txt not found"; \
		echo "  Create this file with one GitHub URL per line"; \
		exit 1; \
	fi
	@rm -rf .temp-downloads 2>/dev/null || true
	@echo ""
	uv run python git-gist-crawler.py
	@echo ""
	@rm -rf .temp-downloads 2>/dev/null || true
	@echo "Crawling complete"
	@echo ""

docker: ## Build and run crawler in Docker container
	@echo "Checking Docker image..."
	@if [ -z "$$(docker images -q git-gist-crawl:latest 2>/dev/null)" ]; then \
		echo "Building Docker image..."; \
		docker build -t git-gist-crawl:latest .; \
		echo "Docker image built successfully"; \
	else \
		echo "Docker image already exists"; \
	fi
	@echo ""
	@echo "Starting crawler in Docker container..."
	@mkdir -p data
	@docker run --rm \
		-v "$$(pwd)/data:/app/data" \
		-v "$$(pwd)/crawl-jobs.txt:/app/crawl-jobs.txt" \
		git-gist-crawl:latest
	@echo ""
	@echo "Docker crawl complete"
	@echo ""

docker-rebuild: ## Rebuild Docker image without cache and run
	@echo "Removing existing Docker image..."
	@docker rmi -f git-gist-crawl:latest 2>/dev/null || true
	@echo "Building Docker image (no cache)..."
	@docker build --no-cache -t git-gist-crawl:latest .
	@echo "Docker image rebuilt successfully"
	@echo ""
	@echo "Starting crawler in Docker container..."
	@mkdir -p data
	@docker run --rm \
		-v "$$(pwd)/data:/app/data" \
		-v "$$(pwd)/crawl-jobs.txt:/app/crawl-jobs.txt" \
		git-gist-crawl:latest
	@echo ""
	@echo "Docker crawl complete"
	@echo ""

docker-delete: ## Remove Docker image
	@echo "Removing Docker image..."
	@if [ -n "$$(docker images -q git-gist-crawl:latest 2>/dev/null)" ]; then \
		docker rmi -f git-gist-crawl:latest; \
		echo "Docker image removed"; \
	else \
		echo "Docker image has already been removed"; \
	fi
	@echo ""

purge: docker-delete ## Remove all crawled data, state, and Docker image
	@echo "Removing data directory contents..."
	@rm -rf data/*
	@rm -rf .temp-downloads 2>/dev/null || true
	@echo "Purge complete"
	@echo ""
