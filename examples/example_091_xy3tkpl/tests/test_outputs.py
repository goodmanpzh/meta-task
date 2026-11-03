#!/usr/bin/env python3
"""
Tests for Metrics Cardinality Explosion Forensics Engine.
"""

import sys
import os
import re
import json
import subprocess
import glob
from collections import defaultdict

sys.path.insert(0, '/app')

SNAPSHOTS_DIR = '/app/data/snapshots'


def _count_prom_files():
    return len(glob.glob(os.path.join(SNAPSHOTS_DIR, 't_*.prom')))


def _read_type_declarations():
    """Extract TYPE declarations from all snapshot files."""
    types = {}
    for f in glob.glob(os.path.join(SNAPSHOTS_DIR, 't_*.prom')):
        with open(f) as fh:
            for line in fh:
                if line.startswith('# TYPE'):
                    parts = line.split()
                    if len(parts) >= 4:
                        types[parts[2]] = parts[3]
    return types


def _count_raw_metric_lines(filepath):
    """Count non-comment, non-empty lines per raw metric name."""
    counts = defaultdict(int)
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            m = re.match(r'^([a-zA-Z_:][a-zA-Z0-9_:]*)', line)
            if m:
                counts[m.group(1)] += 1
    return dict(counts)


class TestModuleStructure:

    def test_engine_file_exists(self):
        assert os.path.isfile('/app/engine.py'), "engine.py must exist at /app/engine.py"

    def test_class_importable(self):
        from engine import CardinalityForensicsEngine
        assert CardinalityForensicsEngine is not None

    def test_constructor_accepts_path(self):
        from engine import CardinalityForensicsEngine
        engine = CardinalityForensicsEngine(SNAPSHOTS_DIR)
        assert engine is not None

    def test_has_required_methods(self):
        from engine import CardinalityForensicsEngine
        engine = CardinalityForensicsEngine(SNAPSHOTS_DIR)
        assert callable(getattr(engine, 'analyze', None))
        assert callable(getattr(engine, 'get_metric_names', None))
        assert callable(getattr(engine, 'get_snapshot_count', None))


class TestSnapshotCount:

    def test_snapshot_count_matches_files(self):
        from engine import CardinalityForensicsEngine
        engine = CardinalityForensicsEngine(SNAPSHOTS_DIR)
        assert engine.get_snapshot_count() == _count_prom_files()


class TestMetricNames:

    def test_metric_names_sorted(self):
        from engine import CardinalityForensicsEngine
        engine = CardinalityForensicsEngine(SNAPSHOTS_DIR)
        names = engine.get_metric_names()
        assert names == sorted(names), "Metric names must be sorted"

    def test_no_duplicate_names(self):
        from engine import CardinalityForensicsEngine
        engine = CardinalityForensicsEngine(SNAPSHOTS_DIR)
        names = engine.get_metric_names()
        assert len(names) == len(set(names))

    def test_counter_total_suffix_stripped(self):
        """Counters declared with _total should have that suffix removed in base names."""
        from engine import CardinalityForensicsEngine
        engine = CardinalityForensicsEngine(SNAPSHOTS_DIR)
        names = engine.get_metric_names()
        types = _read_type_declarations()
        # Find all TYPE-declared names that are counters ending in _total
        counter_totals = {n for n, t in types.items() if t == 'counter' and n.endswith('_total')}
        for ct in counter_totals:
            base = ct[:-6]  # strip _total
            assert base in names, f"Counter {ct} should have base name {base}"
            assert ct not in names, f"Counter {ct} should not appear with _total suffix"

    def test_histogram_suffixes_not_in_names(self):
        """Histogram sub-metrics should be collapsed to base name."""
        from engine import CardinalityForensicsEngine
        engine = CardinalityForensicsEngine(SNAPSHOTS_DIR)
        names = engine.get_metric_names()
        types = _read_type_declarations()
        histograms = {n for n, t in types.items() if t == 'histogram'}
        for h in histograms:
            assert h in names, f"Histogram base {h} should be in names"
            for suffix in ['_bucket', '_count', '_sum']:
                assert h + suffix not in names, f"{h}{suffix} should not appear separately"

    def test_summary_suffixes_not_in_names(self):
        """Summary sub-metrics should be collapsed to base name."""
        from engine import CardinalityForensicsEngine
        engine = CardinalityForensicsEngine(SNAPSHOTS_DIR)
        names = engine.get_metric_names()
        types = _read_type_declarations()
        summaries = {n for n, t in types.items() if t == 'summary'}
        for s in summaries:
            assert s in names, f"Summary base {s} should be in names"
            for suffix in ['_count', '_sum']:
                assert s + suffix not in names, f"{s}{suffix} should not appear separately"

    def test_expected_number_of_base_names(self):
        """Check we have the right number of distinct base metrics."""
        from engine import CardinalityForensicsEngine
        engine = CardinalityForensicsEngine(SNAPSHOTS_DIR)
        names = engine.get_metric_names()
        types = _read_type_declarations()
        # Count expected: each TYPE declaration = one base metric, but counters
        # with _total get their base computed
        expected_bases = set()
        for n, t in types.items():
            if t == 'counter' and n.endswith('_total'):
                expected_bases.add(n[:-6])
            else:
                expected_bases.add(n)
        assert len(names) == len(expected_bases), \
            f"Expected {len(expected_bases)} base names, got {len(names)}"


class TestExplosionDetection:

    def test_analyze_returns_correct_structure(self):
        from engine import CardinalityForensicsEngine
        engine = CardinalityForensicsEngine(SNAPSHOTS_DIR)
        result = engine.analyze()
        assert isinstance(result, dict)
        for key in ['explosions', 'timeline', 'root_causes', 'remediation']:
            assert key in result, f"Missing key: {key}"

    def test_explosions_have_required_fields(self):
        from engine import CardinalityForensicsEngine
        engine = CardinalityForensicsEngine(SNAPSHOTS_DIR)
        result = engine.analyze()
        for exp in result['explosions']:
            for field in ['metric', 'initial_cardinality', 'peak_cardinality', 'growth_factor']:
                assert field in exp, f"Missing field: {field}"
            assert isinstance(exp['growth_factor'], (int, float))
            assert exp['growth_factor'] > 5.0
            assert exp['peak_cardinality'] > 100

    def test_explosions_sorted_by_growth_factor_desc(self):
        from engine import CardinalityForensicsEngine
        engine = CardinalityForensicsEngine(SNAPSHOTS_DIR)
        result = engine.analyze()
        factors = [e['growth_factor'] for e in result['explosions']]
        assert factors == sorted(factors, reverse=True)

    def test_growth_factor_is_peak_over_initial(self):
        from engine import CardinalityForensicsEngine
        engine = CardinalityForensicsEngine(SNAPSHOTS_DIR)
        result = engine.analyze()
        for exp in result['explosions']:
            computed = exp['peak_cardinality'] / exp['initial_cardinality']
            assert abs(exp['growth_factor'] - round(computed, 2)) < 0.5

    def test_detects_three_explosions(self):
        """The dataset contains exactly 3 metrics that meet the explosion criteria."""
        from engine import CardinalityForensicsEngine
        engine = CardinalityForensicsEngine(SNAPSHOTS_DIR)
        result = engine.analyze()
        assert len(result['explosions']) == 3, \
            f"Expected 3 explosions, got {len(result['explosions'])}"

    def test_all_explosion_metrics_are_valid_base_names(self):
        from engine import CardinalityForensicsEngine
        engine = CardinalityForensicsEngine(SNAPSHOTS_DIR)
        result = engine.analyze()
        valid_names = set(engine.get_metric_names())
        for exp in result['explosions']:
            assert exp['metric'] in valid_names, \
                f"Explosion metric '{exp['metric']}' not in valid base names"

    def test_non_exploding_metrics_excluded(self):
        """Metrics with stable cardinality should not appear in explosions."""
        from engine import CardinalityForensicsEngine
        engine = CardinalityForensicsEngine(SNAPSHOTS_DIR)
        result = engine.analyze()
        detected = {e['metric'] for e in result['explosions']}
        all_names = set(engine.get_metric_names())
        stable = all_names - detected
        # Stable metrics should have at least 1 member
        assert len(stable) > 0, "Some metrics should be stable (not exploding)"

    def test_highest_growth_factor_is_very_large(self):
        """The metric with the largest growth should have a factor > 50."""
        from engine import CardinalityForensicsEngine
        engine = CardinalityForensicsEngine(SNAPSHOTS_DIR)
        result = engine.analyze()
        assert result['explosions'][0]['growth_factor'] > 50


class TestTimeline:

    def test_timeline_keys_match_explosions(self):
        from engine import CardinalityForensicsEngine
        engine = CardinalityForensicsEngine(SNAPSHOTS_DIR)
        result = engine.analyze()
        exp_metrics = {e['metric'] for e in result['explosions']}
        assert set(result['timeline'].keys()) == exp_metrics

    def test_timeline_length_equals_snapshots(self):
        from engine import CardinalityForensicsEngine
        engine = CardinalityForensicsEngine(SNAPSHOTS_DIR)
        result = engine.analyze()
        n = engine.get_snapshot_count()
        for metric, tl in result['timeline'].items():
            assert len(tl) == n, f"{metric}: timeline has {len(tl)} entries, expected {n}"

    def test_timeline_values_are_integers(self):
        from engine import CardinalityForensicsEngine
        engine = CardinalityForensicsEngine(SNAPSHOTS_DIR)
        result = engine.analyze()
        for metric, tl in result['timeline'].items():
            for i, v in enumerate(tl):
                assert isinstance(v, int), f"{metric}[{i}] is {type(v)}, expected int"

    def test_timeline_no_zeros(self):
        """Explosion metrics should never show zero in timeline (interpolation required)."""
        from engine import CardinalityForensicsEngine
        engine = CardinalityForensicsEngine(SNAPSHOTS_DIR)
        result = engine.analyze()
        for metric, tl in result['timeline'].items():
            for i, v in enumerate(tl):
                assert v > 0, f"{metric}[{i}] is 0 — missing snapshots should be interpolated"

    def test_timeline_non_decreasing(self):
        """Explosion metrics grow over time; timeline should be non-decreasing."""
        from engine import CardinalityForensicsEngine
        engine = CardinalityForensicsEngine(SNAPSHOTS_DIR)
        result = engine.analyze()
        for metric, tl in result['timeline'].items():
            for i in range(1, len(tl)):
                assert tl[i] >= tl[i - 1], \
                    f"{metric} timeline decreased at [{i}]: {tl[i-1]} -> {tl[i]}"

    def test_timeline_peak_matches_explosion(self):
        """The max value in the timeline should match peak_cardinality."""
        from engine import CardinalityForensicsEngine
        engine = CardinalityForensicsEngine(SNAPSHOTS_DIR)
        result = engine.analyze()
        exp_dict = {e['metric']: e for e in result['explosions']}
        for metric, tl in result['timeline'].items():
            peak = max(tl)
            assert peak == exp_dict[metric]['peak_cardinality'], \
                f"{metric}: timeline peak {peak} != explosion peak {exp_dict[metric]['peak_cardinality']}"

    def test_interpolation_produces_plateaus(self):
        """When a snapshot is missing, the timeline should have adjacent equal values
        (last-known-value interpolation creates a plateau)."""
        from engine import CardinalityForensicsEngine
        engine = CardinalityForensicsEngine(SNAPSHOTS_DIR)
        result = engine.analyze()
        # At least one timeline should have a plateau where consecutive values are equal
        # (due to scrape failures being interpolated)
        has_plateau = False
        for metric, tl in result['timeline'].items():
            for i in range(1, len(tl)):
                if tl[i] == tl[i - 1] and tl[i] != tl[0]:
                    has_plateau = True
                    break
            if has_plateau:
                break
        assert has_plateau, "Expected at least one interpolation plateau in timelines"


class TestRootCauseAnalysis:

    def test_root_causes_keys_match_explosions(self):
        from engine import CardinalityForensicsEngine
        engine = CardinalityForensicsEngine(SNAPSHOTS_DIR)
        result = engine.analyze()
        exp_metrics = {e['metric'] for e in result['explosions']}
        assert set(result['root_causes'].keys()) == exp_metrics

    def test_root_cause_has_required_fields(self):
        from engine import CardinalityForensicsEngine
        engine = CardinalityForensicsEngine(SNAPSHOTS_DIR)
        result = engine.analyze()
        for metric, rc in result['root_causes'].items():
            for field in ['label', 'unique_values_initial', 'unique_values_peak', 'sample_new_values']:
                assert field in rc, f"Missing field '{field}' for {metric}"
            assert isinstance(rc['label'], str)
            assert isinstance(rc['unique_values_initial'], int)
            assert isinstance(rc['unique_values_peak'], int)
            assert isinstance(rc['sample_new_values'], list)

    def test_root_cause_label_not_structural(self):
        """Root cause labels must not be __name__, le, or quantile."""
        from engine import CardinalityForensicsEngine
        engine = CardinalityForensicsEngine(SNAPSHOTS_DIR)
        result = engine.analyze()
        forbidden = {'__name__', 'le', 'quantile'}
        for metric, rc in result['root_causes'].items():
            assert rc['label'] not in forbidden, \
                f"Structural label '{rc['label']}' should not be root cause for {metric}"

    def test_root_cause_peak_greater_than_initial(self):
        from engine import CardinalityForensicsEngine
        engine = CardinalityForensicsEngine(SNAPSHOTS_DIR)
        result = engine.analyze()
        for metric, rc in result['root_causes'].items():
            assert rc['unique_values_peak'] > rc['unique_values_initial'], \
                f"{metric}: peak {rc['unique_values_peak']} <= initial {rc['unique_values_initial']}"

    def test_root_cause_significant_growth(self):
        """The root cause label should show substantial value-space growth."""
        from engine import CardinalityForensicsEngine
        engine = CardinalityForensicsEngine(SNAPSHOTS_DIR)
        result = engine.analyze()
        for metric, rc in result['root_causes'].items():
            growth = rc['unique_values_peak'] / max(rc['unique_values_initial'], 1)
            assert growth > 5, \
                f"{metric}: root cause label growth factor {growth:.1f} too small"

    def test_sample_new_values_sorted_and_bounded(self):
        from engine import CardinalityForensicsEngine
        engine = CardinalityForensicsEngine(SNAPSHOTS_DIR)
        result = engine.analyze()
        for metric, rc in result['root_causes'].items():
            vals = rc['sample_new_values']
            assert len(vals) <= 10, f"{metric}: too many sample values ({len(vals)})"
            assert vals == sorted(vals), f"{metric}: sample values not sorted"
            if len(vals) > 0:
                assert all(isinstance(v, str) for v in vals)

    def test_root_cause_labels_are_distinct(self):
        """Each exploding metric should have a different root cause label."""
        from engine import CardinalityForensicsEngine
        engine = CardinalityForensicsEngine(SNAPSHOTS_DIR)
        result = engine.analyze()
        labels = [rc['label'] for rc in result['root_causes'].values()]
        assert len(labels) == len(set(labels)), "Root cause labels should be distinct across metrics"


class TestRemediation:

    def test_remediation_count(self):
        from engine import CardinalityForensicsEngine
        engine = CardinalityForensicsEngine(SNAPSHOTS_DIR)
        result = engine.analyze()
        assert len(result['remediation']) == len(result['explosions'])

    def test_remediation_schema(self):
        from engine import CardinalityForensicsEngine
        engine = CardinalityForensicsEngine(SNAPSHOTS_DIR)
        result = engine.analyze()
        for rule in result['remediation']:
            assert isinstance(rule.get('source_labels'), list)
            assert len(rule['source_labels']) >= 1
            assert isinstance(rule.get('regex'), str)
            assert len(rule['regex']) > 0
            assert rule.get('action') == 'drop'
            assert isinstance(rule.get('target_metric'), str)

    def test_remediation_targets_match_explosions(self):
        from engine import CardinalityForensicsEngine
        engine = CardinalityForensicsEngine(SNAPSHOTS_DIR)
        result = engine.analyze()
        exp_metrics = {e['metric'] for e in result['explosions']}
        for rule in result['remediation']:
            assert rule['target_metric'] in exp_metrics

    def test_remediation_source_labels_match_root_causes(self):
        from engine import CardinalityForensicsEngine
        engine = CardinalityForensicsEngine(SNAPSHOTS_DIR)
        result = engine.analyze()
        for rule in result['remediation']:
            target = rule['target_metric']
            if target in result['root_causes']:
                rc_label = result['root_causes'][target]['label']
                assert rc_label in rule['source_labels'], \
                    f"source_labels for {target} should include root cause label '{rc_label}'"

    def test_remediation_regex_is_valid(self):
        from engine import CardinalityForensicsEngine
        engine = CardinalityForensicsEngine(SNAPSHOTS_DIR)
        result = engine.analyze()
        for rule in result['remediation']:
            try:
                re.compile(rule['regex'])
            except re.error as e:
                assert False, f"Invalid regex for {rule['target_metric']}: {rule['regex']} ({e})"

    def test_remediation_regex_matches_new_values(self):
        """Each regex must match >= 90% of the sample new values from root cause analysis."""
        from engine import CardinalityForensicsEngine
        engine = CardinalityForensicsEngine(SNAPSHOTS_DIR)
        result = engine.analyze()
        for rule in result['remediation']:
            target = rule['target_metric']
            if target not in result['root_causes']:
                continue
            samples = result['root_causes'][target]['sample_new_values']
            if not samples:
                continue
            pat = re.compile(rule['regex'])
            matched = sum(1 for v in samples if pat.search(v))
            ratio = matched / len(samples)
            assert ratio >= 0.9, \
                f"Regex for {target} matched only {ratio:.0%} of samples (need >=90%)"


class TestCLI:

    def test_cli_full_output_valid_json(self):
        proc = subprocess.run(
            ['python3', '/app/engine.py', SNAPSHOTS_DIR],
            capture_output=True, text=True, timeout=60
        )
        assert proc.returncode == 0, f"CLI exit code {proc.returncode}: {proc.stderr}"
        data = json.loads(proc.stdout)
        for key in ['explosions', 'timeline', 'root_causes', 'remediation']:
            assert key in data

    def test_cli_summary_mode(self):
        proc = subprocess.run(
            ['python3', '/app/engine.py', SNAPSHOTS_DIR, '--summary'],
            capture_output=True, text=True, timeout=60
        )
        assert proc.returncode == 0, f"CLI summary exit code {proc.returncode}: {proc.stderr}"
        data = json.loads(proc.stdout)
        assert isinstance(data, list)
        for item in data:
            assert 'metric' in item
            assert 'growth_factor' in item

    def test_cli_completes_within_time_limit(self):
        import time
        start = time.time()
        proc = subprocess.run(
            ['python3', '/app/engine.py', SNAPSHOTS_DIR],
            capture_output=True, text=True, timeout=60
        )
        elapsed = time.time() - start
        assert proc.returncode == 0
        assert elapsed < 30, f"CLI took {elapsed:.1f}s, must complete under 30s"


if __name__ == '__main__':
    import pytest
    sys.exit(pytest.main([__file__, '-v']))
