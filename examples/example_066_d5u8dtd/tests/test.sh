#!/bin/bash
set -e

mkdir -p /logs/verifier

pip install --quiet pytest numpy

if pytest /tests/test_outputs.py -v; then
    echo "1" > /logs/verifier/reward.txt
else
    echo "0" > /logs/verifier/reward.txt
fi
