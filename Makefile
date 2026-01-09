.PHONY: help clean install test-coverage test-eval lint complexity check-all open-reports

# Colors for output
BLUE := \033[1;34m
GREEN := \033[1;32m
YELLOW := \033[1;33m
RED := \033[1;31m
RESET := \033[0m

# Project paths
PROJECT_ROOT := $(shell pwd)
REPORTS_DIR := $(PROJECT_ROOT)/reports
COVERAGE_DIR := $(REPORTS_DIR)/coverage
EVAL_DIR := $(PROJECT_ROOT)/application/agents/tests/evals
EVAL_REPORT := $(REPORTS_DIR)/eval/unified_report.html
LINT_REPORT := $(REPORTS_DIR)/lint/report.html
COMPLEXITY_REPORT := $(REPORTS_DIR)/complexity/report.html

# Python interpreter
PYTHON := python3
PIP := $(PYTHON) -m pip
PYTEST := pytest
VENV_PYTHON := .venv/bin/python
VENV_PYTEST := .venv/bin/pytest

help: ## Show this help message
	@echo "$(BLUE)Cyoda AI Studio - Build Automation$(RESET)"
	@echo "===================================="
	@echo ""
	@echo "$(GREEN)Available targets:$(RESET)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-18s$(RESET) %s\n", $$1, $$2}'
	@echo ""

clean: ## Clean all generated reports and cache files
	@echo "$(BLUE)🧹 Cleaning generated files...$(RESET)"
	@rm -rf $(REPORTS_DIR)
	@rm -rf .pytest_cache .mypy_cache .coverage htmlcov
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@echo "$(GREEN)✅ Clean complete$(RESET)"

install: ## Install project dependencies
	@echo "$(BLUE)📦 Installing dependencies...$(RESET)"
	@$(PIP) install -e ".[dev]"
	@echo "$(GREEN)✅ Dependencies installed$(RESET)"

test-coverage: ## Run tests with coverage and generate HTML report
	@echo "$(BLUE)🧪 Running tests with coverage...$(RESET)"
	@mkdir -p $(COVERAGE_DIR)
	@$(VENV_PYTEST) tests/ \
		--cov=cyoda_mcp \
		--cov=common \
		--cov=application \
		--cov=services \
		--cov-report=html:$(COVERAGE_DIR) \
		--cov-report=term \
		--cov-report=term-missing \
		-v || (echo "$(RED)❌ Tests failed$(RESET)" && exit 1)
	@echo ""
	@echo "$(GREEN)✅ Tests passed$(RESET)"
	@echo "$(YELLOW)📊 Coverage report: $(COVERAGE_DIR)/index.html$(RESET)"

test-eval: ## Run ADK evaluations and generate HTML report
	@echo "$(BLUE)🧪 Running ADK evaluations...$(RESET)"
	@mkdir -p $(REPORTS_DIR)/eval
	@cd $(EVAL_DIR) && bash run_all_evals.sh
	@if [ -f "$(EVAL_DIR)/unified_report.html" ]; then \
		cp $(EVAL_DIR)/unified_report.html $(EVAL_REPORT); \
		echo "$(GREEN)✅ Evaluations complete$(RESET)"; \
		echo "$(YELLOW)📊 Eval report: $(EVAL_REPORT)$(RESET)"; \
	else \
		echo "$(RED)❌ Eval report not generated$(RESET)"; \
		exit 1; \
	fi

lint: ## Run all code style checks and generate report
	@echo "$(BLUE)🔍 Running code style checks...$(RESET)"
	@mkdir -p $(REPORTS_DIR)/lint
	@echo "<html><head><title>Lint Report</title><style>" > $(LINT_REPORT)
	@echo "body { font-family: monospace; margin: 20px; background: #f5f5f5; }" >> $(LINT_REPORT)
	@echo "h1 { color: #333; } h2 { color: #666; margin-top: 30px; }" >> $(LINT_REPORT)
	@echo "pre { background: white; padding: 15px; border-left: 4px solid #4CAF50; overflow-x: auto; }" >> $(LINT_REPORT)
	@echo ".error { border-left-color: #f44336; } .success { color: #4CAF50; }" >> $(LINT_REPORT)
	@echo "</style></head><body><h1>Code Style Report</h1>" >> $(LINT_REPORT)
	@echo "<p>Generated: $$(date)</p>" >> $(LINT_REPORT)
	@echo ""
	@echo "$(YELLOW)▶ Running Black...$(RESET)"
	@echo "<h2>Black (Code Formatting)</h2><pre>" >> $(LINT_REPORT)
	@black --check . 2>&1 | tee -a $(LINT_REPORT) || echo "$(YELLOW)⚠️  Black formatting issues found$(RESET)"
	@echo "</pre>" >> $(LINT_REPORT)
	@echo ""
	@echo "$(YELLOW)▶ Running isort...$(RESET)"
	@echo "<h2>isort (Import Sorting)</h2><pre>" >> $(LINT_REPORT)
	@isort --check-only . 2>&1 | tee -a $(LINT_REPORT) || echo "$(YELLOW)⚠️  Import sorting issues found$(RESET)"
	@echo "</pre>" >> $(LINT_REPORT)
	@echo ""
	@echo "$(YELLOW)▶ Running Flake8...$(RESET)"
	@echo "<h2>Flake8 (Style Guide)</h2><pre>" >> $(LINT_REPORT)
	@flake8 . 2>&1 | tee -a $(LINT_REPORT) || echo "$(YELLOW)⚠️  Flake8 issues found$(RESET)"
	@echo "</pre>" >> $(LINT_REPORT)
	@echo ""
	@echo "$(YELLOW)▶ Skipping MyPy (disabled - too slow)...$(RESET)"
	@echo "<h2>MyPy (Type Checking) - SKIPPED</h2><pre>MyPy disabled for performance. Run manually with: mypy .</pre>" >> $(LINT_REPORT)
	@echo ""
	@echo "$(YELLOW)▶ Running Bandit...$(RESET)"
	@echo "<h2>Bandit (Security)</h2><pre>" >> $(LINT_REPORT)
	@bandit -r common/ application/ cyoda_mcp/ services/ scripts/ 2>&1 | tee -a $(LINT_REPORT) || echo "$(YELLOW)⚠️  Security issues found$(RESET)"
	@echo "</pre>" >> $(LINT_REPORT)
	@echo "</body></html>" >> $(LINT_REPORT)
	@echo ""
	@echo "$(GREEN)✅ Linting complete$(RESET)"
	@echo "$(YELLOW)📊 Lint report: $(LINT_REPORT)$(RESET)"

complexity: ## Run lizard complexity analysis and generate HTML report
	@echo "$(BLUE)📊 Running complexity analysis...$(RESET)"
	@mkdir -p $(REPORTS_DIR)/complexity
	@.venv/bin/lizard -L 100 -W 30 \
		-x "*/.*" -x "*/node_modules/*" -x "*/build/*" -x "*/dist/*" \
		-x "*/__pycache__/*" -x "*/proto/*" -x "*/venv/*" -x "*/.venv/*" \
		-x "*/htmlcov/*" -x "*/.mypy_cache/*" -x "*/.pytest_cache/*" \
		-x "*/ai-assistant-ui-react/*" \
		cyoda_mcp/ common/ application/ services/ \
		-o $(COMPLEXITY_REPORT) --html || \
		(echo "$(YELLOW)⚠️  Complexity issues found (continuing...)$(RESET)")
	@echo "$(GREEN)✅ Complexity analysis complete$(RESET)"
	@echo "$(YELLOW)📊 Complexity report: $(COMPLEXITY_REPORT)$(RESET)"

check-all: clean test-coverage test-eval lint complexity ## Run all checks and generate all reports
	@echo ""
	@echo "$(GREEN)========================================$(RESET)"
	@echo "$(GREEN)✅ All checks complete!$(RESET)"
	@echo "$(GREEN)========================================$(RESET)"
	@echo ""
	@echo "$(YELLOW)📊 Reports generated:$(RESET)"
	@echo "  • Coverage:   $(COVERAGE_DIR)/index.html"
	@echo "  • Eval:       $(EVAL_REPORT)"
	@echo "  • Lint:       $(LINT_REPORT)"
	@echo "  • Complexity: $(COMPLEXITY_REPORT)"
	@echo ""
	@echo "$(BLUE)Run 'make open-reports' to view all reports$(RESET)"

open-reports: ## Open all HTML reports in browser
	@echo "$(BLUE)🌐 Opening reports in browser...$(RESET)"
	@if [ -f "$(COVERAGE_DIR)/index.html" ]; then xdg-open $(COVERAGE_DIR)/index.html 2>/dev/null || true; fi
	@sleep 1
	@if [ -f "$(EVAL_REPORT)" ]; then xdg-open $(EVAL_REPORT) 2>/dev/null || true; fi
	@sleep 1
	@if [ -f "$(LINT_REPORT)" ]; then xdg-open $(LINT_REPORT) 2>/dev/null || true; fi
	@sleep 1
	@if [ -f "$(COMPLEXITY_REPORT)" ]; then xdg-open $(COMPLEXITY_REPORT) 2>/dev/null || true; fi
	@echo "$(GREEN)✅ Reports opened$(RESET)"
