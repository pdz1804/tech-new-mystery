#!/bin/bash

# Comprehensive test runner for Tech News Mystery
# Runs all unit tests and integration tests

set -e

echo "=========================================="
echo "Tech News Mystery - Full Test Suite"
echo "=========================================="
echo ""

cd "$(dirname "$0")/backend"

echo "📊 Running ALL tests against real backend..."
echo ""

# Run pytest with coverage report
python -m pytest tests/ \
    -v \
    --tb=short \
    --cov=app \
    --cov-report=term-missing \
    --cov-report=html:htmlcov \
    2>&1 | tee test_results.log

TEST_EXIT_CODE=$?

echo ""
echo "=========================================="
echo "Test Results Summary"
echo "=========================================="

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ ALL TESTS PASSED!"
else
    echo "❌ Some tests failed (exit code: $TEST_EXIT_CODE)"
fi

echo ""
echo "Coverage report generated in: htmlcov/index.html"
echo "Test log saved in: test_results.log"
echo ""

exit $TEST_EXIT_CODE
