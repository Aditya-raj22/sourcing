#!/bin/bash
# Test runner script for AI-driven outreach engine tests

echo "🧪 AI-Driven Outreach Engine - Test Suite"
echo "=========================================="
echo ""

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo "❌ pytest not found. Installing test dependencies..."
    pip install -r requirements-test.txt
    echo ""
fi

# Parse command line arguments
TEST_TYPE=${1:-"all"}

case $TEST_TYPE in
    "all")
        echo "Running all tests..."
        pytest tests/ -v
        ;;
    "fast")
        echo "Running fast tests only (skipping slow tests)..."
        pytest tests/ -m "not slow" -v
        ;;
    "tier1")
        echo "Running Production Tier 1 (Must-Have) tests..."
        pytest tests/ -m tier1 -v
        ;;
    "tier2")
        echo "Running Production Tier 2 (Should-Have) tests..."
        pytest tests/ -m tier2 -v
        ;;
    "integration")
        echo "Running integration tests..."
        pytest tests/ -m integration -v
        ;;
    "e2e")
        echo "Running end-to-end tests..."
        pytest tests/ -m e2e -v
        ;;
    "coverage")
        echo "Running all tests with coverage report..."
        pytest tests/ --cov=src --cov-report=term-missing --cov-report=html
        echo ""
        echo "📊 Coverage report generated: htmlcov/index.html"
        ;;
    "category")
        if [ -z "$2" ]; then
            echo "❌ Please specify a test file"
            echo "Example: ./run_tests.sh category test_data_ingestion.py"
            exit 1
        fi
        echo "Running tests from $2..."
        pytest "tests/$2" -v
        ;;
    "help")
        echo "Usage: ./run_tests.sh [TYPE]"
        echo ""
        echo "Test Types:"
        echo "  all          - Run all tests (default)"
        echo "  fast         - Run only fast tests (skip slow integration tests)"
        echo "  tier1        - Run Production Tier 1 (critical) tests"
        echo "  tier2        - Run Production Tier 2 (important) tests"
        echo "  integration  - Run integration tests"
        echo "  e2e          - Run end-to-end tests"
        echo "  coverage     - Run all tests with coverage report"
        echo "  category FILE - Run specific test file"
        echo "  help         - Show this help message"
        echo ""
        echo "Examples:"
        echo "  ./run_tests.sh                                    # Run all tests"
        echo "  ./run_tests.sh fast                               # Run fast tests"
        echo "  ./run_tests.sh tier1                              # Run Tier 1 tests"
        echo "  ./run_tests.sh coverage                           # Run with coverage"
        echo "  ./run_tests.sh category test_data_ingestion.py    # Run specific category"
        ;;
    *)
        echo "❌ Unknown test type: $TEST_TYPE"
        echo "Run './run_tests.sh help' for usage information"
        exit 1
        ;;
esac

echo ""
echo "✅ Test run complete!"
