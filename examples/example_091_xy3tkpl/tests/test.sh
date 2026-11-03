#!/bin/bash
set -e

cd /app
mkdir -p /logs/verifier

set +e
python3 -m pytest /tests/test_outputs.py -v 2>&1 | tee /logs/test_output.txt
TEST_EXIT_CODE=${PIPESTATUS[0]}
set -e

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "1" > /logs/verifier/reward.txt
else
    echo "0" > /logs/verifier/reward.txt
fi

exit 0
