"""
Tests to verify the data processing pipeline is working correctly.
Checks that all services ran, all jobs were processed, and the
final output is complete and well-formed.
"""

import json
import os
import math
import hashlib
import subprocess


RESULTS_DIR = "/app/data/results"
OUTPUT_FILE = "/app/output/results.json"
QUEUE_DIR = "/app/data/queue"
EXPECTED_JOBS = 20


def test_output_file_exists():
    """The final aggregated output file must exist."""
    assert os.path.isfile(OUTPUT_FILE), (
        f"Output file {OUTPUT_FILE} does not exist. "
        "The aggregator did not produce output."
    )


def test_output_is_valid_json():
    """The output file must be valid JSON."""
    with open(OUTPUT_FILE, "r") as f:
        data = json.load(f)
    assert isinstance(data, dict), "Output must be a JSON object"


def test_all_jobs_processed():
    """All 20 jobs must be processed - no partial results."""
    with open(OUTPUT_FILE, "r") as f:
        data = json.load(f)

    total = data.get("total_jobs", 0)
    assert total == EXPECTED_JOBS, (
        f"Expected {EXPECTED_JOBS} total jobs, got {total}"
    )

    # Must not be a partial result
    assert data.get("partial", False) is not True, (
        "Output is marked as partial - not all jobs were processed"
    )


def test_individual_result_files():
    """Each job should have a corresponding result file in the results directory."""
    assert os.path.isdir(RESULTS_DIR), (
        f"Results directory {RESULTS_DIR} does not exist"
    )

    result_files = [
        f for f in os.listdir(RESULTS_DIR)
        if f.startswith("result-") and f.endswith(".json")
    ]
    assert len(result_files) >= EXPECTED_JOBS, (
        f"Expected at least {EXPECTED_JOBS} result files, "
        f"found {len(result_files)}"
    )


def test_output_has_required_sections():
    """The output must contain all required summary sections."""
    with open(OUTPUT_FILE, "r") as f:
        data = json.load(f)

    required_keys = [
        "pipeline_version",
        "total_jobs",
        "completed_at",
        "jobs",
        "integrity_hash"
    ]

    for key in required_keys:
        assert key in data, f"Missing required key: {key}"

    assert data["pipeline_version"] == "1.0", "Wrong pipeline version"
    assert isinstance(data["completed_at"], (int, float)), "completed_at must be numeric"
    assert isinstance(data["jobs"], dict), "jobs must be a dict"
    assert len(data["jobs"]) == EXPECTED_JOBS, (
        f"Expected {EXPECTED_JOBS} jobs in output, got {len(data['jobs'])}"
    )


def test_stats_jobs_correct():
    """
    Verify that stats job results contain valid statistical computations.
    Re-compute from the input data to verify correctness.
    """
    with open(OUTPUT_FILE, "r") as f:
        data = json.load(f)

    stats_jobs = {
        jid: j for jid, j in data["jobs"].items()
        if "mean" in j
    }

    assert len(stats_jobs) > 0, "No stats jobs found in output"

    # Verify at least one stats job by re-computing from input data
    for job_id, result in stats_jobs.items():
        # Find the corresponding input job
        input_job = None
        for fname in os.listdir(QUEUE_DIR):
            fpath = os.path.join(QUEUE_DIR, fname)
            if fname.endswith(".json"):
                with open(fpath, "r") as f:
                    job = json.load(f)
                if job.get("id") == job_id:
                    input_job = job
                    break

        if input_job is None:
            continue

        dataset = input_job["dataset"]
        n = len(dataset)
        expected_mean = sum(dataset) / n
        expected_var = sum((x - expected_mean) ** 2 for x in dataset) / n
        expected_stddev = math.sqrt(expected_var)

        assert abs(result["mean"] - round(expected_mean, 6)) < 0.001, (
            f"Mean mismatch for {job_id}: got {result['mean']}, "
            f"expected ~{round(expected_mean, 6)}"
        )
        assert abs(result["stddev"] - round(expected_stddev, 6)) < 0.001, (
            f"Stddev mismatch for {job_id}: got {result['stddev']}, "
            f"expected ~{round(expected_stddev, 6)}"
        )
        assert result["count"] == n, (
            f"Count mismatch for {job_id}: got {result['count']}, expected {n}"
        )


def test_transform_jobs_correct():
    """Verify that transform job results contain valid transformations."""
    with open(OUTPUT_FILE, "r") as f:
        data = json.load(f)

    transform_jobs = {
        jid: j for jid, j in data["jobs"].items()
        if "checksum" in j and "transformed" in j
    }

    assert len(transform_jobs) > 0, "No transform jobs found in output"

    for job_id, result in transform_jobs.items():
        transformed = result["transformed"]
        # All sigmoid outputs should be in [0, 1]
        for val in transformed:
            assert 0.0 <= val <= 1.0, (
                f"Transform value {val} out of [0,1] range in job {job_id}"
            )

        # Verify checksum
        expected_checksum = hashlib.md5(
            json.dumps(transformed).encode()
        ).hexdigest()
        assert result["checksum"] == expected_checksum, (
            f"Checksum mismatch for {job_id}"
        )


def test_hash_jobs_correct():
    """Verify that hash job results contain valid hashes."""
    with open(OUTPUT_FILE, "r") as f:
        data = json.load(f)

    hash_jobs = {
        jid: j for jid, j in data["jobs"].items()
        if "sha256" in j and "md5" in j
    }

    assert len(hash_jobs) > 0, "No hash jobs found in output"

    # Verify hashes by recomputing from input data
    for job_id, result in hash_jobs.items():
        input_job = None
        for fname in os.listdir(QUEUE_DIR):
            fpath = os.path.join(QUEUE_DIR, fname)
            if fname.endswith(".json"):
                with open(fpath, "r") as f:
                    job = json.load(f)
                if job.get("id") == job_id:
                    input_job = job
                    break

        if input_job is None:
            continue

        data_str = json.dumps(input_job["dataset"], sort_keys=True)
        expected_sha256 = hashlib.sha256(data_str.encode()).hexdigest()
        expected_md5 = hashlib.md5(data_str.encode()).hexdigest()

        assert result["sha256"] == expected_sha256, (
            f"SHA256 mismatch for {job_id}"
        )
        assert result["md5"] == expected_md5, (
            f"MD5 mismatch for {job_id}"
        )


def test_integrity_hash():
    """
    Verify the integrity hash in the output matches a recomputation
    from the jobs data.
    """
    with open(OUTPUT_FILE, "r") as f:
        data = json.load(f)

    jobs_content = json.dumps(data["jobs"], sort_keys=True)
    expected_hash = hashlib.sha256(jobs_content.encode()).hexdigest()

    assert data["integrity_hash"] == expected_hash, (
        "Integrity hash does not match recomputed value. "
        "The output may have been tampered with or corrupted."
    )


def test_no_zombie_processes():
    """Ensure no zombie processes are left behind by the pipeline."""
    result = subprocess.run(
        ["ps", "aux"],
        capture_output=True,
        text=True
    )
    lines = result.stdout.strip().split("\n")
    zombies = [l for l in lines if "<defunct>" in l or "Z+" in l.split()[7:8]]
    assert len(zombies) == 0, (
        f"Found {len(zombies)} zombie process(es): {zombies}"
    )


def test_supervisor_config_fixed():
    """
    Verify the supervisord configuration has been properly fixed.
    The config should reference correct paths and settings.
    """
    config_path = "/etc/supervisor/conf.d/pipeline.conf"
    assert os.path.isfile(config_path), (
        f"Supervisor config {config_path} not found"
    )

    with open(config_path, "r") as f:
        config = f.read()

    # Queue server path should be correct
    assert "/app/queue_server.py" in config, (
        "Queue server command path not fixed "
        "(should be /app/queue_server.py)"
    )
    # Should not reference the wrong path
    assert "/app/services/" not in config, (
        "Config still references wrong path /app/services/"
    )

    # Bind address should be 127.0.0.1, not 10.0.0.1
    assert "10.0.0.1" not in config, (
        "Config still has unreachable bind address 10.0.0.1"
    )

    # Worker should not run as non-existent user
    lines = config.split("\n")
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("user="):
            user = stripped.split("=", 1)[1].strip()
            assert user != "pipeline", (
                "Config still references non-existent user 'pipeline'"
            )
