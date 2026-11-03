#!/bin/bash

# Install test dependencies
pip install pytest==8.4.1 pytest-json-ctrf==0.3.5 numpy==1.24.0 scipy==1.11.4 --break-system-packages 2>/dev/null || \
pip install pytest==8.4.1 pytest-json-ctrf==0.3.5 numpy==1.24.0 scipy==1.11.4

mkdir -p /logs/verifier

python -m pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA -v

if [ $? -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
