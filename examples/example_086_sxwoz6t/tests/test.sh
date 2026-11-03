#!/bin/bash
set -e

mkdir -p /logs/verifier

# Install test dependencies
pip install pytest 2>&1 | tail -1

if pytest /tests/test_outputs.py -v 2>&1; then
    echo "1" > /logs/verifier/reward.txt
else
    echo "0" > /logs/verifier/reward.txt
fi
