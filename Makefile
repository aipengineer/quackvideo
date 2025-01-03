# Terminal colors
GREEN  := $(shell tput -Txterm setaf 2)
YELLOW := $(shell tput -Txterm setaf 3)
WHITE  := $(shell tput -Txterm setaf 7)
RESET  := $(shell tput -Txterm sgr0)
BLUE   := $(shell tput -Txterm setaf 4)

# Project settings
PYTHON_VERSION := 3.12
VENV_NAME := .venv
PYTHON := $(VENV_NAME)/bin/python
PROJECT_NAME := quackvideo

# Test settings
TEST_PATH := tests/
PYTEST_ARGS ?= -v
COVERAGE_THRESHOLD := 90

RUN_ARGS ?= --help

help: ## Show this help message
	@echo ''
	@echo '${YELLOW}Quackvideo Development Guide${RESET}'
	@echo ''
	@echo '${YELLOW}Installation Options:${RESET}'
	@echo '  Core only:     ${GREEN}make install-core${RESET}  - Basic installation'
	@echo '  ML Support:    ${GREEN}make install-ml${RESET}    - With ML features'
	@echo '  Full:         ${GREEN}make install-full${RESET}   - All user features'
	@echo '  Development:  ${GREEN}make install-dev${RESET}    - Development tools'
	@echo '  Complete:     ${GREEN}make install-all${RESET}    - Everything'
	@echo ''
	@echo '${YELLOW}Development Workflow:${RESET}'
	@echo '  1. Setup:     ${GREEN}make setup${RESET}         - Full development environment'
	@echo '  2. Test:      ${GREEN}make test${RESET}          - Run tests with coverage'
	@echo '  3. Lint:      ${GREEN}make lint${RESET}          - Check code style'
	@echo '  4. Examples:  ${GREEN}make run-examples${RESET}   - Run example scripts'
	@echo ''
	@echo '${YELLOW}Available Targets:${RESET}'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  ${YELLOW}%-15s${GREEN}%s${RESET}\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ''

# Development environment targets
.PHONY: env
env: ## Create virtual environment using uv
	@echo "${BLUE}Creating virtual environment...${RESET}"
	uv venv --python $(PYTHON_VERSION)
	@echo "${GREEN}Virtual environment created. Activate it with:${RESET}"
	@echo "source $(VENV_NAME)/bin/activate"

.PHONY: install-core
install-core: ## Install core package only
	@echo "${BLUE}Installing core package...${RESET}"
	uv pip install -e .

.PHONY: install-ml
install-ml: ## Install package with ML dependencies
	@echo "${BLUE}Installing package with ML support...${RESET}"
	uv pip install -e ".[ml]"

.PHONY: install-full
install-full: ## Install package with all user features (no dev tools)
	@echo "${BLUE}Installing package with all user features...${RESET}"
	uv pip install -e ".[full]"

.PHONY: install-dev
install-dev: ## Install package with development dependencies
	@echo "${BLUE}Installing package with development tools...${RESET}"
	uv pip install -e ".[dev]"

.PHONY: install-all
install-all: ## Install package with all dependencies (including dev tools)
	@echo "${BLUE}Installing package with all dependencies...${RESET}"
	uv pip install -e ".[all]"

# Update the setup target to reflect full development environment
.PHONY: setup
setup: ## Create environment and install full development dependencies
	@echo "${BLUE}Creating complete development environment...${RESET}"
	@echo '#!/bin/bash' > setup.sh
	@echo 'uv venv --python $(PYTHON_VERSION)' >> setup.sh
	@echo 'source $(VENV_NAME)/bin/activate' >> setup.sh
	@echo 'uv pip install -e ".[all]"' >> setup.sh
	@echo 'rm "$$0"' >> setup.sh
	@chmod +x setup.sh
	@echo "${GREEN}Environment setup script created. To complete setup, run:${RESET}"
	@echo "${YELLOW}source setup.sh${RESET}"

.PHONY: update
update: ## Update all dependencies
	@echo "${BLUE}Updating dependencies...${RESET}"
	uv pip install --upgrade -e ".[all]"

.PHONY: test
test: install-dev ## Run tests with coverage
	$(PYTHON) -m pytest $(TEST_PATH) $(PYTEST_ARGS) --cov=src --cov-report=term-missing

# Code quality targets
.PHONY: format
format: ## Format code with ruff
	@echo "${BLUE}Formatting code...${RESET}"
	$(PYTHON) -m ruff format .

.PHONY: lint
lint: install-dev ## Run linters
	$(PYTHON) -m ruff check src/ tests/ examples/
	$(PYTHON) -m ruff format --check src/ tests/ examples/
	$(PYTHON) -m mypy src/ tests/ examples/

.PHONY: clean
clean: ## Clean build artifacts and cache
	rm -rf build/ dist/ *.egg-info .coverage .mypy_cache .pytest_cache .ruff_cache $(VENV_NAME)
	rm -rf setup.sh
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

.PHONY: pre-commit
pre-commit: format lint test clean-all ## Prepare for commit by formatting, linting, testing, and cleaning
	@echo "${BLUE}Running pre-commit checks...${RESET}"
	@echo "${GREEN}✓${RESET} Format check passed"
	@echo "${GREEN}✓${RESET} Lint check passed"
	@echo "${GREEN}✓${RESET} Tests passed"
	@echo "${GREEN}✓${RESET} Project cleaned"
	@echo "${GREEN}✓${RESET} Ready to commit!"

.PHONY: clean-all
clean-all: clean ## Deep clean including all generated and cache files
	@echo "${BLUE}Deep cleaning project...${RESET}"
	rm -rf .pytest_cache/ .coverage htmlcov/ .tox/ .ruff_cache/
	rm -rf .mypy_cache/ .hypothesis/ .benchmarks/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type f -name "coverage.xml" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".DS_Store" -delete
	find . -type f -name "*.flac" -delete
	find . -type f -name "*.mp4" -delete
	@echo "${GREEN}✓${RESET} Project cleaned successfully"

.PHONY: setup-git-hooks
setup-git-hooks: ## Set up git hooks to run pre-commit automatically
	@echo "${BLUE}Setting up git hooks...${RESET}"
	@mkdir -p .git/hooks
	@echo '#!/bin/sh' > .git/hooks/pre-commit
	@echo 'make pre-commit' >> .git/hooks/pre-commit
	@echo 'make clean-all' >> .git/hooks/pre-commit
	@chmod +x .git/hooks/pre-commit
	@echo "${GREEN}✓${RESET} Git hooks installed successfully"

.PHONY: run-examples
run-examples: install-dev ## Run example scripts
	$(PYTHON) examples/synthetic_generation.py video test.mp4 --pattern color_bars --duration 10
	$(PYTHON) examples/synthetic_generation.py audio test.flac --pattern sine --frequency 440
	$(PYTHON) examples/frame_extraction.py --help
	$(PYTHON) examples/audio_operations.py --help

.PHONY: structure
structure: ## Show project structure
	@echo "${YELLOW}Current Project Structure:${RESET}"
	@echo "${BLUE}"
	@if command -v tree > /dev/null; then \
		tree -a -I '.git|.venv|__pycache__|*.pyc|*.pyo|*.pyd|.pytest_cache|.ruff_cache|.coverage|htmlcov'; \
	else \
		find . -not -path '*/\.*' -not -path '*.pyc' -not -path '*/__pycache__/*' \
			-not -path './.venv/*' -not -path './build/*' -not -path './dist/*' \
			-not -path './*.egg-info/*' \
			| sort | \
			sed -e "s/[^-][^\/]*\// │   /g" -e "s/├── /│── /" -e "s/└── /└── /"; \
	fi
	@echo "${RESET}"

.DEFAULT_GOAL := help
