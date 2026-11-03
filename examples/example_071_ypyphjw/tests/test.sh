#!/bin/bash

mkdir -p /logs/verifier
echo "0" > /logs/verifier/reward.txt

# Install test dependencies
pip install pytest > /dev/null 2>&1 || true

# Run pytest and capture exit code
pytest /tests/test_outputs.py -v 2>&1
RESULT=$?

if [ $RESULT -eq 0 ]; then
    echo "1" > /logs/verifier/reward.txt
else
    # Count passed/total for partial credit
    TOTAL=$(pytest /tests/test_outputs.py --collect-only -q 2>/dev/null | tail -1 | grep -oP '\d+(?= test)')
    PASSED=$(pytest /tests/test_outputs.py -v 2>/dev/null | grep -c "PASSED" || echo "0")
    if [ -n "$TOTAL" ] && [ "$TOTAL" -gt 0 ]; then
        python3 -c "print(round($PASSED / $TOTAL, 2))" > /logs/verifier/reward.txt
    fi
fi
