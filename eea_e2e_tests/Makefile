.PHONY: install run headed docker help

install:        ## Install deps + Playwright browser
	pip install -r requirements.txt
	playwright install chromium

run:            ## Run all tests locally
	pytest tests/ -v -s --tb=short

headed:         ## Run tests with visible browser
	HEADLESS=false pytest tests/ -v -s --tb=short

docker:         ## Build & run tests in Docker
	docker compose up --build --abort-on-container-exit

help:           ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
