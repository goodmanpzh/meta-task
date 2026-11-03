#!/bin/bash
set -e

# Ensure log directory exists
mkdir -p /logs/verifier

# Install test dependencies
pip install pytest pytest-asyncio pytest-timeout 2>/dev/null || true

# Run tests
if python -m pytest /tests/test_outputs.py -v --timeout=60 2>&1; then
    echo "All tests passed"
    echo 1 > /logs/verifier/reward.txt
else
    echo "Some tests failed"
    echo 0 > /logs/verifier/reward.txt
fi
