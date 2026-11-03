#!/bin/bash
set -e

# Create log directory
mkdir -p /logs/verifier

# Install test dependencies
pip install pytest > /dev/null 2>&1

# Run tests
if pytest /tests/test_outputs.py -v 2>&1; then
    echo "1" > /logs/verifier/reward.txt
    echo "All tests passed!"
else
    echo "0" > /logs/verifier/reward.txt
    echo "Some tests failed."
fi
