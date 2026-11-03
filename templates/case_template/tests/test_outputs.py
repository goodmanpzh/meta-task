"""
TODO: Write pytest tests that verify the solving agent's output.

Rules:
  1. Do NOT hardcode expected answers — compute them from input data,
     or verify structural properties (file exists, correct format, etc.)
  2. Tests must pass for ANY correct solution, not just your specific solve.sh.
  3. Every assertion must correspond to a requirement stated in instruction.md.
  4. Only import packages that are installed in test.sh.
"""
import os
import json
import pytest


# TODO: Write your test functions below.
#
# Example tests:
#
# def test_output_file_exists():
#     """Check that the required output file was created."""
#     assert os.path.isfile("/app/output/result.json"), "Output file not found"
#
# def test_output_format():
#     """Verify the output has the expected JSON structure."""
#     with open("/app/output/result.json") as f:
#         data = json.load(f)
#     assert "result" in data, "Missing 'result' key"
#     assert isinstance(data["result"], list), "'result' should be a list"
#
# def test_output_correctness():
#     """Verify output values by computing expected from input data."""
#     with open("/app/input/data.json") as f:
#         input_data = json.load(f)
#     with open("/app/output/result.json") as f:
#         output_data = json.load(f)
#     expected_count = len([x for x in input_data["items"] if x["valid"]])
#     assert output_data["count"] == expected_count
