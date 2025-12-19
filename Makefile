# ymery Makefile - using uv for all Python operations

.PHONY: help install dev-install test lint format type-check build clean upload upload-test release bump-patch bump-minor bump-major show-version

help:  ## Show this help message
	@echo "ymery Development Commands (using uv)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ { printf "\033[36m%-15s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

install:  ## Install package dependencies
	uv sync

dev-install:  ## Install package with development dependencies
	uv sync --all-extras

test:  ## Run tests
	uv run pytest

test-cov:  ## Run tests with coverage
	uv run pytest --cov=ymery --cov-report=html --cov-report=term

lint:  ## Run linting (ruff)
	uv run ruff check src/ tests/

format:  ## Format code (black + ruff)
	uv run black src/ tests/
	uv run ruff check --fix src/ tests/

type-check:  ## Run type checking (mypy)
	uv run mypy src/

check: lint type-check test  ## Run all quality checks

build:  ## Build package for distribution
	uv build

clean:  ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete

upload-test:  ## Upload to TestPyPI
	uv run twine upload --repository testpypi dist/*

upload:  ## Upload to PyPI
	uv run twine upload dist/*

release:  ## Clean, build, and upload to PyPI (production release)
	@echo "🚀 Starting release process..."
	@echo "📦 Cleaning previous builds..."
	$(MAKE) clean
	@echo "🔨 Building package..."
	$(MAKE) build
	@echo "📤 Uploading to PyPI..."
	$(MAKE) upload
	@echo "✅ Release complete!"
	@echo "🎉 Package published to PyPI"

show-version:  ## Show current version
	@python -c "import sys; sys.path.insert(0, 'src'); import ymery; print(f'Current version: {ymery.__version__}')"

bump-patch:  ## Bump patch version (0.0.X)
	@echo "🔢 Bumping patch version..."
	@python scripts/bump_version.py patch
	@$(MAKE) show-version
	@echo "🧹 Cleaning old builds..."
	@$(MAKE) clean
	@echo "🔨 Building new package..."
	@$(MAKE) build

bump-minor:  ## Bump minor version (0.X.0)
	@echo "🔢 Bumping minor version..."
	@python scripts/bump_version.py minor
	@$(MAKE) show-version
	@echo "🧹 Cleaning old builds..."
	@$(MAKE) clean
	@echo "🔨 Building new package..."
	@$(MAKE) build

bump-major:  ## Bump major version (X.0.0)
	@echo "🔢 Bumping major version..."
	@python scripts/bump_version.py major
	@$(MAKE) show-version
	@echo "🧹 Cleaning old builds..."
	@$(MAKE) clean
	@echo "🔨 Building new package..."
	@$(MAKE) build

test-plugin:  ## Test the test plugin
	@echo "Testing ymery with test plugin..."
	@PYTHONPATH=src python -c "from ymery.app import ymery; import ymery.plugins.test.plugin; from ymery.expose import apply_pending_registrations; app = ymery(auto_discover=False); apply_pending_registrations(app); result = app._execute_from_registry('test'); test = result.unwrap(); print('✅ Test plugin loaded'); print('hello():', test.hello()); print('echo():', test.echo('test message')); print('status():', test.status())"

test-cli:  ## Test CLI with test plugin
	@echo "Testing CLI with test plugin..."
	@PYTHONPATH=src python -c "from ymery import run; run()" test hello --name ymery

ymery-dev:  ## Run ymery CLI in development mode
	@echo "Running ymery CLI in development mode..."
	@echo "Usage: make ymery-dev ARGS='--help'"
	@PYTHONPATH=src python -m ymery $(ARGS)

ymery-dev-help:  ## Show ymery development CLI help
	@PYTHONPATH=src python -m ymery --help
