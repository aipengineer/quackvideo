.PHONY: help install install-dev install-all test lint format clean build dev doc

PYTHON := python3.10
VENV := .venv
BIN := $(VENV)/bin

help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

$(VENV)/bin/activate: pyproject.toml  ## Create virtual environment
	uv venv --python $(PYTHON) $(VENV)
	. $(BIN)/activate
	touch $(BIN)/activate

venv: $(VENV)/bin/activate  ## Create virtual environment if it doesn't exist

install: venv ## Install package (inference only)
	uv pip install -e .

install-train: venv ## Install package with training dependencies
	uv pip install -e ".[train]"

install-dev: venv ## Install package with development dependencies
	uv pip install -e ".[dev]"

install-all: venv ## Install package with all dependencies (train + dev)
	uv pip install -e ".[all]"

test: install-dev ## Run tests with pytest
	$(BIN)/pytest tests/ -v --cov=src --cov-report=term-missing

lint: install-dev ## Run ruff and mypy
	$(BIN)/ruff check src/ tests/
	$(BIN)/ruff format --check src/ tests/
	$(BIN)/mypy src/ tests/

format: install-dev ## Format code using ruff
	$(BIN)/ruff format src/ tests/
	$(BIN)/ruff check --fix src/ tests/

build: install-dev ## Build package
	$(BIN)/python -m build

clean: ## Clean up cache and build files
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .coverage
	rm -rf .mypy_cache
	rm -rf .pytest_cache
	rm -rf .ruff_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf $(VENV)

dev: install-all ## Start Jupyter notebook server with all dependencies
	$(BIN)/jupyter notebook

setup: clean install-all ## Clean environment and install all dependencies
	@echo "Development environment ready!"

check: lint test ## Run all checks (lint and test)

# Specialized setup targets
setup-inference: clean install ## Setup for inference only
	@echo "Inference environment ready!"

setup-training: clean install-train ## Setup for training
	@echo "Training environment ready!"

.PHONY: structure
structure: ## Show current project structure
	@echo "${YELLOW}Current Project Structure:${RESET}"
	@echo "${BLUE}"
	@if command -v tree > /dev/null; then \
		tree -a -I '.git|.venv|__pycache__|*.pyc|*.pyo|*.pyd|.pytest_cache|.ruff_cache|.coverage|htmlcov'; \
	else \
		echo "Note: Install 'tree' for better directory visualization:"; \
		echo "  macOS:     brew install tree"; \
		echo "  Ubuntu:    sudo apt-get install tree"; \
		echo "  Fedora:    sudo dnf install tree"; \
		echo ""; \
		find . -not -path '*/\.*' -not -path '*.pyc' -not -path '*/__pycache__/*' \
			-not -path './.venv/*' -not -path './build/*' -not -path './dist/*' \
			-not -path './*.egg-info/*' \
			| sort \
			| sed -e "s/[^-][^\/]*\// │   /g" -e "s/├── /│── /" -e "s/└── /└── /"; \
	fi
	@echo "${RESET}"