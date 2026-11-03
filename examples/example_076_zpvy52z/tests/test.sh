#!/bin/bash

# Install uv if not available
if ! command -v uv &> /dev/null; then
    curl -LsSf https://astral.sh/uv/0.9.5/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

# Ensure test output directory exists
mkdir -p /logs/verifier

# Run tests with all required packages
uv run --with pytest --with numpy --with pandas --with scipy --with scikit-learn \
    pytest /tests/test_outputs.py -v 2>&1 | tee /logs/verifier/test_output.log

if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo "1" > /logs/verifier/reward.txt
else
    echo "0" > /logs/verifier/reward.txt
fi
