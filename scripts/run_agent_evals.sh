#!/bin/bash
# Run Cyoda Assistant Agent Evaluations
# Usage: ./scripts/run_agent_evals.sh [test_type]
# test_type: all (default), qa, guidelines, setup, coordinator, integration

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if we're in the project root
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}Error: Must run from project root${NC}"
    exit 1
fi

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}Warning: Virtual environment not activated${NC}"
    echo -e "${YELLOW}Activating .venv...${NC}"
    source .venv/bin/activate
fi

# Check if GOOGLE_API_KEY is set
if [ -z "$GOOGLE_API_KEY" ]; then
    echo -e "${RED}Error: GOOGLE_API_KEY environment variable not set${NC}"
    echo -e "${YELLOW}Set it with: export GOOGLE_API_KEY='your-key-here'${NC}"
    exit 1
fi

TEST_TYPE=${1:-all}

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Cyoda Assistant Agent Evaluations${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

case $TEST_TYPE in
    qa)
        echo -e "${GREEN}Running QA Agent Tests...${NC}"
        pytest tests/integration/agents/test_agent_evaluation.py::TestQAAgent -v -s
        ;;
    guidelines)
        echo -e "${GREEN}Running Guidelines Agent Tests...${NC}"
        pytest tests/integration/agents/test_agent_evaluation.py::TestGuidelinesAgent -v -s
        ;;
    setup)
        echo -e "${GREEN}Running Setup Agent Tests...${NC}"
        pytest tests/integration/agents/test_agent_evaluation.py::TestSetupAgent -v -s
        ;;
    coordinator)
        echo -e "${GREEN}Running Coordinator Agent Tests...${NC}"
        pytest tests/integration/agents/test_agent_evaluation.py::TestCoordinatorAgent -v -s
        ;;
    integration)
        echo -e "${GREEN}Running Integration Tests...${NC}"
        pytest tests/integration/agents/test_agent_evaluation.py::TestCyodaAssistantIntegration -v -s
        ;;
    all)
        echo -e "${GREEN}Running All Agent Tests...${NC}"
        pytest tests/integration/agents/test_agent_evaluation.py -v -s
        ;;
    *)
        echo -e "${RED}Error: Unknown test type '$TEST_TYPE'${NC}"
        echo -e "${YELLOW}Valid options: all, qa, guidelines, setup, coordinator, integration${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Evaluation Complete!${NC}"
echo -e "${BLUE}========================================${NC}"

