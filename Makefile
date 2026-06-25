# Convenience targets. `make help` lists everything.
.DEFAULT_GOAL := help

BACKEND := backend
FRONTEND := frontend

.PHONY: help install backend-install frontend-install backend frontend test build clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: backend-install frontend-install ## Install both backend and frontend deps

backend-install: ## Create venv and install Python deps
	cd $(BACKEND) && python -m venv .venv && \
		. .venv/bin/activate && pip install -r requirements.txt

frontend-install: ## Install npm deps
	cd $(FRONTEND) && npm install

backend: ## Run the FastAPI backend on :8000
	cd $(BACKEND) && . .venv/bin/activate && \
		uvicorn app.main:app --reload --port 8000

frontend: ## Run the Vite dev server on :5173
	cd $(FRONTEND) && npm run dev

test: ## Run backend analyzer tests
	cd $(BACKEND) && . .venv/bin/activate && pytest -q

build: ## Production build of the frontend
	cd $(FRONTEND) && npm run build

clean: ## Remove caches and build artifacts
	rm -rf $(BACKEND)/.venv $(BACKEND)/.pytest_cache $(BACKEND)/.cache
	find $(BACKEND) -name __pycache__ -type d -prune -exec rm -rf {} +
	rm -rf $(FRONTEND)/node_modules $(FRONTEND)/dist
