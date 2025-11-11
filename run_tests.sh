#!/bin/bash
# Test runner script for Lake Evaporation application

set -e  # Exit on error

echo "=========================================="
echo "Lake Evaporation Test Suite"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${YELLOW}Warning: pytest not found. Installing...${NC}"
    pip install pytest pytest-cov
fi

echo -e "${BLUE}Running Unit Tests...${NC}"
echo "------------------------------------------"
pytest tests/test_algorithms.py tests/test_processing.py -v
echo ""

echo -e "${BLUE}Running Integration Tests...${NC}"
echo "------------------------------------------"
pytest tests/test_integration.py -v
echo ""

# API tests are optional (require credentials)
if [ -f ".env" ] || [ -f "config.json" ]; then
    echo -e "${BLUE}Running API Connection Tests...${NC}"
    echo "------------------------------------------"
    pytest tests/test_api_connection.py -v || echo -e "${YELLOW}API tests skipped (no valid credentials)${NC}"
    echo ""
else
    echo -e "${YELLOW}Skipping API tests (no .env or config.json found)${NC}"
    echo ""
fi

echo -e "${GREEN}=========================================="
echo "All tests completed!"
echo "==========================================${NC}"
