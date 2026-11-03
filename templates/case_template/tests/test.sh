#!/bin/bash
# ============================================================
# TEST RUNNER
#   1. Install dependencies    ← MODIFY: add packages your tests need
#   2. Run pytest & write reward  ← DO NOT MODIFY
# ============================================================

# --- 1. Install dependencies (MODIFY this section) ---
# Add packages that test_outputs.py imports. Use "|| true" to be safe.
# Examples:
#   pip install pytest numpy pandas 2>/dev/null || true
#   pip install pytest pyyaml requests 2>/dev/null || true
pip install pytest 2>/dev/null || true

# --- 2. Run tests and write reward (DO NOT MODIFY below) ---
mkdir -p /logs/verifier
echo "0" > /logs/verifier/reward.txt

if pytest /tests/test_outputs.py -v --tb=short; then
    echo "1" > /logs/verifier/reward.txt
fi
