#!/bin/bash
set -e

# Install test dependencies
pip install pytest > /dev/null 2>&1

# Ensure log directory exists
mkdir -p /logs/verifier

# Run tests
if pytest /tests/test_outputs.py -v; then
    echo "1" > /logs/verifier/reward.txt
else
    echo "0" > /logs/verifier/reward.txt
fi
