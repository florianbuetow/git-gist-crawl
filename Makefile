.PHONY: help init crawl purge

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
	uv run python gist-crawler.py
	@echo ""
	@rm -rf .temp-downloads 2>/dev/null || true
	@echo "Crawling complete"
	@echo ""

purge: ## Remove all crawled data and state
	@echo "Removing data directory contents..."
	@rm -rf data/*
	@rm -rf .temp-downloads 2>/dev/null || true
	@echo "Purge complete"
	@echo ""
