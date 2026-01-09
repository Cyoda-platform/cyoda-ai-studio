# Build Automation Guide

This document describes the automated build and quality checks system for Cyoda AI Studio.

## Overview

The project uses **Makefile** for build automation, providing a consistent way to run tests, linting, and quality checks both locally and in CI/CD pipelines.

## Quick Start

```bash
# Show all available commands
make help

# Run all checks and generate reports
make check-all

# View all generated reports
make open-reports
```

## Setup Development Environment

```bash
# One-time setup: install dependencies and git hooks
bash scripts/setup-dev.sh

# This will:
# - Install Python dependencies
# - Install pre-commit hooks
# - Setup lizard for complexity analysis
# - Create reports directory structure
```

## Available Make Targets

### Main Targets

| Command | Description |
|---------|-------------|
| `make help` | Show all available targets |
| `make check-all` | Run all checks and generate all reports |
| `make clean` | Clean all generated reports and cache files |
| `make install` | Install project dependencies |
| `make open-reports` | Open all HTML reports in browser |

### Individual Check Targets

| Command | Description | Report Location |
|---------|-------------|-----------------|
| `make test-coverage` | Run tests with coverage | `reports/coverage/index.html` |
| `make test-eval` | Run ADK evaluations | `reports/eval/unified_report.html` |
| `make lint` | Run all code style checks | `reports/lint/report.html` |
| `make complexity` | Run complexity analysis | `reports/complexity/report.html` |

## What Each Check Does

### 1. Test Coverage (`make test-coverage`)

Runs all tests with pytest and generates HTML coverage report.

**What it includes:**
- All unit tests in `tests/`
- Coverage for: `cyoda_mcp/`, `common/`, `application/`, `services/`
- Excludes: test files, proto files, cache directories

**Output:**
- Terminal: Coverage percentage and missing lines
- HTML: Interactive coverage report with line-by-line analysis

### 2. Eval Tests (`make test-eval`)

Runs ADK agent evaluations and generates unified HTML report.

**What it includes:**
- Coordinator agent evaluations
- Setup agent evaluations
- GitHub agent evaluations
- All evalset files from `application/agents/*/evals/`

**Environment variables set:**
- `DISABLE_MCP_TOOLSET=true`
- `MOCK_ALL_TOOLS=true`

**Output:**
- Unified HTML report with all evaluation results
- Individual evalset result JSON files in `.adk/eval_history/`

### 3. Lint Checks (`make lint`)

Runs comprehensive code quality checks.

**Tools included:**
- **Black**: Code formatting check (88 char line length)
- **isort**: Import sorting check
- **Flake8**: Style guide enforcement (PEP 8)
- **MyPy**: Static type checking
- **Bandit**: Security vulnerability scanning

**Output:**
- Combined HTML report with sections for each tool
- Shows all issues found with file locations

### 4. Complexity Analysis (`make complexity`)

Runs Lizard code complexity analyzer.

**Configuration:**
- Max cyclomatic complexity: 100 (`-L 100`)
- Max function length: 30 lines (`-W 30`)

**Analyzes:**
- `cyoda_mcp/`, `common/`, `application/`, `services/`

**Excludes:**
- Hidden directories, node_modules, build artifacts
- Proto files, cache directories, test files

**Output:**
- Interactive HTML report with sortable tables
- Shows complexity metrics per function

## Pre-commit Hooks

Git pre-commit hooks run automatically before each commit.

### What Gets Checked

- **Fast checks** (always):
  - Trailing whitespace
  - End of file fixers
  - YAML/JSON syntax
  - Large files detection
  - Merge conflict markers

- **Code quality** (always):
  - Black formatting (auto-fix)
  - isort import sorting (auto-fix)
  - Flake8 linting
  - Bandit security checks

- **Optional** (commented out by default):
  - MyPy type checking (can be slow)
  - Quick pytest on changed files

### Managing Pre-commit Hooks

```bash
# Install hooks
pre-commit install

# Run hooks manually on all files
pre-commit run --all-files

# Run specific hook
pre-commit run black --all-files

# Skip hooks for a commit (not recommended)
git commit --no-verify

# Update hooks to latest versions
pre-commit autoupdate
```

## CI/CD Integration

GitHub Actions workflow uses the same Makefile targets.

### What Runs in CI

1. **Create virtual environment** - Isolated Python environment
2. **Install dependencies** - Project + dev dependencies + lizard
3. **Run coverage tests** - `make test-coverage`
4. **Run eval tests** - `make test-eval`
5. **Run lint checks** - `make lint`
6. **Run complexity** - `make complexity`
7. **Upload reports** - All HTML reports as GitHub Actions artifacts

### Viewing CI Reports

1. Go to GitHub Actions tab
2. Click on the workflow run
3. Scroll to "Artifacts" section
4. Download any of:
   - `coverage-report`
   - `eval-report`
   - `lint-report`
   - `complexity-report`

Reports are kept for **30 days**.

### All Checks Continue-on-Error

All CI checks use `continue-on-error: true`, meaning:
- ✅ Pipeline won't fail even if checks find issues
- ⚠️ You can still review reports to see what needs fixing
- 🎯 Useful for gradual quality improvements

## Helper Scripts

### `scripts/setup-dev.sh`

Sets up complete development environment.

**What it does:**
- Checks Python version
- Warns if not in virtual environment
- Installs project dependencies
- Installs pre-commit
- Sets up git hooks
- Optionally runs pre-commit on all files
- Creates reports directory structure

**Usage:**
```bash
source .venv/bin/activate  # Recommended first
bash scripts/setup-dev.sh
```

### `scripts/open-reports.sh`

Opens all generated HTML reports in browser.

**What it does:**
- Checks if each report exists
- Opens reports using `xdg-open` (Linux) with fallbacks
- Shows helpful messages if reports don't exist
- Suggests which make target to run

**Usage:**
```bash
bash scripts/open-reports.sh
# or
make open-reports
```

## Report Structure

```
reports/
├── coverage/
│   ├── index.html          # Main coverage report
│   └── ...                 # Per-file coverage pages
├── eval/
│   └── unified_report.html # All eval results
├── lint/
│   └── report.html         # Combined lint report
└── complexity/
    └── report.html         # Complexity analysis
```

## Best Practices

### Local Development

1. **Before starting work:**
   ```bash
   make clean
   ```

2. **While developing:**
   - Pre-commit hooks run automatically
   - Run specific checks as needed: `make lint`, `make test-coverage`

3. **Before committing:**
   ```bash
   make check-all  # Optional but recommended
   ```

4. **Review reports:**
   ```bash
   make open-reports
   ```

### Continuous Integration

- All checks run automatically on push to `main`/`develop`
- All checks run on pull requests to `main`
- Reports available as downloadable artifacts
- Pipeline shows status but doesn't fail (continue-on-error)

## Troubleshooting

### Pre-commit hooks failing

```bash
# See what's failing
pre-commit run --all-files

# Auto-fix formatting issues
black .
isort .

# Then commit again
```

### Makefile command not found

```bash
# Make sure you have make installed (usually pre-installed on Linux)
sudo apt-get install make  # Ubuntu/Debian

# Or run commands directly
bash scripts/setup-dev.sh
```

### Virtual environment issues

```bash
# Create new virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pip install lizard
```

### Reports not opening

```bash
# Open manually
xdg-open reports/coverage/index.html
xdg-open reports/eval/unified_report.html
xdg-open reports/lint/report.html
xdg-open reports/complexity/report.html
```

### Eval tests failing

Check environment variables:
```bash
export DISABLE_MCP_TOOLSET=true
export MOCK_ALL_TOOLS=true
make test-eval
```

## Customization

### Modify Complexity Thresholds

Edit `Makefile`, line ~119:
```makefile
@.venv/bin/lizard -L 100 -W 30 \  # -L = complexity, -W = line count
```

### Add/Remove Linting Tools

Edit `Makefile`, `lint` target:
```makefile
lint: ## Run all code style checks and generate report
    # Add new tool here
```

### Modify Pre-commit Hooks

Edit `.pre-commit-config.yaml`:
```yaml
repos:
  # Add new hook here
```

### Change Coverage Settings

Edit `pyproject.toml`, `[tool.coverage.run]` section:
```toml
[tool.coverage.run]
source = ["cyoda_mcp", "common", "application", "services"]
omit = ["*/tests/*", ...]
```

## Additional Resources

- [Pre-commit Documentation](https://pre-commit.com/)
- [Pytest Coverage Documentation](https://pytest-cov.readthedocs.io/)
- [Black Code Style](https://black.readthedocs.io/)
- [MyPy Type Checking](https://mypy.readthedocs.io/)
- [Lizard Complexity Analyzer](https://github.com/terryyin/lizard)
- [Bandit Security](https://bandit.readthedocs.io/)

## Summary

This build automation system provides:
- ✅ Consistent quality checks locally and in CI
- 📊 Comprehensive HTML reports for all checks
- 🎣 Git hooks for fast feedback before commit
- 🚀 Simple commands via Makefile
- 📦 Easy setup with helper scripts
- 🔄 Same tools everywhere (local = CI)

Run `make help` anytime to see available commands!
