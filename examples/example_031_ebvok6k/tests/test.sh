#!/bin/bash

# Install test dependencies
pip install pytest==8.4.2 pytest-json-ctrf==0.3.5 2>/dev/null

pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -v -rA

if [ $? -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
