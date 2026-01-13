#!/bin/bash
set -e

# Cyoda AI Studio - Development Environment Setup
# This script installs all development dependencies and sets up pre-commit hooks

echo "🚀 Setting up Cyoda AI Studio development environment..."
echo "======================================================"
echo ""

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "📌 Python version: $PYTHON_VERSION"

# Check if we're in a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Warning: Not in a virtual environment"
    echo "   Recommended: source .venv/bin/activate"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Install project dependencies
echo ""
echo "📦 Installing project dependencies..."
pip install -e ".[dev]"

# Install pre-commit
echo ""
echo "🔧 Installing pre-commit..."
pip install pre-commit

# Install pre-commit hooks
echo ""
echo "🎣 Setting up git pre-commit hooks..."
pre-commit install

# Install additional tools
echo ""
echo "🛠️  Installing additional development tools..."
pip install lizard

# Run pre-commit on all files (optional)
echo ""
read -p "Run pre-commit on all files now? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🏃 Running pre-commit on all files..."
    pre-commit run --all-files || echo "⚠️  Some checks failed - you can fix these later"
fi

# Create reports directory
echo ""
echo "📁 Creating reports directory..."
mkdir -p reports/{coverage,eval,lint,complexity}

echo ""
echo "======================================================"
echo "✅ Development environment setup complete!"
echo "======================================================"
echo ""
echo "📝 Next steps:"
echo "  1. Run 'make help' to see available commands"
echo "  2. Run 'make test-coverage' to run tests"
echo "  3. Run 'make check-all' to run all checks"
echo "  4. Git hooks are now active - they'll run on every commit"
echo ""
echo "💡 Useful commands:"
echo "  • make help           - Show all available targets"
echo "  • make test-coverage  - Run tests with coverage report"
echo "  • make lint           - Run code style checks"
echo "  • make check-all      - Run all checks"
echo "  • pre-commit run      - Run git hooks manually"
echo ""
