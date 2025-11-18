#!/bin/bash
# Run build agent evaluation with real environment (actual git clone and Augment CLI)
#
# This script runs the build agent evaluation test with real tool implementations.
# It will:
# 1. Clone actual GitHub repositories (public templates)
# 2. Run Augment CLI to generate code
# 3. Monitor build progress
#
# Requirements:
# - Git installed
# - Augment CLI configured
# - Environment variables set (AI_MODEL, OPENAI_API_KEY, etc.)
#
# Usage:
#   ./scripts/run_build_agent_eval_real.sh

set -e

echo "🧪 Running Build Agent Evaluation with Real Environment"
echo "========================================================"
echo ""

# Check prerequisites
echo "📋 Checking prerequisites..."

# Check git
if ! command -v git &> /dev/null; then
    echo "❌ Error: git is not installed"
    exit 1
fi
echo "✅ Git found: $(git --version)"

# Check Python
if ! command -v python &> /dev/null; then
    echo "❌ Error: python is not installed"
    exit 1
fi
echo "✅ Python found: $(python --version)"

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found. Using environment variables."
else
    echo "✅ .env file found"
    # Load .env
    export $(grep -v '^#' .env | xargs)
fi

# Check AI_MODEL
if [ -z "$AI_MODEL" ]; then
    echo "⚠️  AI_MODEL not set, using default: openai/gpt-4o-mini"
    export AI_MODEL="openai/gpt-4o-mini"
else
    echo "✅ AI_MODEL: $AI_MODEL"
fi

# Check OPENAI_API_KEY if using OpenAI
if [[ "$AI_MODEL" == openai/* ]]; then
    if [ -z "$OPENAI_API_KEY" ]; then
        echo "❌ Error: OPENAI_API_KEY not set but AI_MODEL is $AI_MODEL"
        exit 1
    fi
    echo "✅ OPENAI_API_KEY is set"
fi

# Check Augment CLI script
if [ ! -f "application/agents/build_app/augment_build.sh" ]; then
    echo "❌ Error: Augment build script not found at application/agents/build_app/augment_build.sh"
    exit 1
fi
echo "✅ Augment build script found"

echo ""
echo "🚀 Starting evaluation test..."
echo ""

# Run the test
python -m pytest \
    application/agents/tests/test_agent_evaluations.py::test_build_agent_pet_store_app \
    -v \
    -s \
    --tb=short \
    --log-cli-level=INFO

echo ""
echo "✅ Evaluation complete!"

