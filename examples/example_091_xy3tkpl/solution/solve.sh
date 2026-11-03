#!/bin/bash
set -e

cd /app

cat > /app/engine.py << 'PYEOF'
#!/usr/bin/env python3
"""
Metrics Cardinality Explosion Forensics Engine.

Analyzes Prometheus exposition format snapshots to detect cardinality explosions,
identify root causes, reconstruct timelines, and generate remediation rules.
"""

import os
import re
import sys
import json
import glob
from collections import defaultdict


class CardinalityForensicsEngine:
    """Analyzes Prometheus metric snapshots for cardinality explosions."""

    def __init__(self, snapshots_dir):
        self.snapshots_dir = snapshots_dir
        self._snapshots = []
        self._metric_types = {}  # type-declared metric name -> type string
        self._load_snapshots()

    def _load_snapshots(self):
        """Load all snapshot files in order."""
        pattern = os.path.join(self.snapshots_dir, "t_*.prom")
        files = glob.glob(pattern)
        # Sort by snapshot index
        def sort_key(f):
            basename = os.path.basename(f)
            match = re.match(r't_(\d+)\.prom', basename)
            return int(match.group(1)) if match else 0
        files.sort(key=sort_key)
        self._snapshots = []
        for f in files:
            parsed = self._parse_prom_file(f)
            self._snapshots.append(parsed)

    def _parse_prom_file(self, filepath):
        """Parse a Prometheus exposition format file.

        Returns a dict: raw_metric_name -> list of (labels_dict, value_str)
        Also updates self._metric_types from TYPE comments.
        """
        metrics = defaultdict(list)
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if line.startswith('# HELP'):
                    continue
                if line.startswith('# TYPE'):
                    parts = line.split()
                    if len(parts) >= 4:
                        metric_name = parts[2]
                        metric_type = parts[3]
                        self._metric_types[metric_name] = metric_type
                    continue
                # Parse metric line
                match = re.match(r'^([a-zA-Z_:][a-zA-Z0-9_:]*)\{(.*?)\}\s+(.+)$', line)
                if match:
                    name = match.group(1)
                    labels_str = match.group(2)
                    value = match.group(3)
                    labels = self._parse_labels(labels_str)
                    metrics[name].append((labels, value))
                else:
                    match2 = re.match(r'^([a-zA-Z_:][a-zA-Z0-9_:]*)\s+(.+)$', line)
                    if match2:
                        name = match2.group(1)
                        value = match2.group(2)
                        metrics[name].append(({}, value))
        return dict(metrics)

    def _parse_labels(self, labels_str):
        """Parse Prometheus label string like 'key="value",key2="value2"'."""
        labels = {}
        if not labels_str:
            return labels
        i = 0
        while i < len(labels_str):
            # Skip commas and whitespace
            while i < len(labels_str) and labels_str[i] in ', ':
                i += 1
            if i >= len(labels_str):
                break
            # Find key
            eq_pos = labels_str.find('=', i)
            if eq_pos == -1:
                break
            key = labels_str[i:eq_pos].strip()
            # Find opening quote
            quote_start = labels_str.find('"', eq_pos)
            if quote_start == -1:
                break
            # Find closing quote (handling escapes)
            j = quote_start + 1
            value_chars = []
            while j < len(labels_str):
                if labels_str[j] == '\\' and j + 1 < len(labels_str):
                    value_chars.append(labels_str[j + 1])
                    j += 2
                elif labels_str[j] == '"':
                    break
                else:
                    value_chars.append(labels_str[j])
                    j += 1
            value = ''.join(value_chars)
            labels[key] = value
            i = j + 1
        return labels

    def _get_base_metric_name(self, raw_name):
        """Get the base metric name by stripping type-specific suffixes.

        Uses TYPE information to correctly determine base names.
        Rules:
          - Counter: if TYPE-declared name ends with _total, base = name[:-6]
                     The raw metric lines also use the _total name.
          - Histogram: TYPE-declared name is the base. Raw lines have
                       _bucket, _count, _sum suffixes.
          - Summary: TYPE-declared name is the base. Raw lines have
                     _count, _sum suffixes (base lines have quantile label).
          - If no TYPE info, return raw_name unchanged.
        """
        # Direct match: raw_name is itself a TYPE-declared name
        if raw_name in self._metric_types:
            mtype = self._metric_types[raw_name]
            # Counters declared as "foo_total counter" have base name "foo"
            if mtype == 'counter' and raw_name.endswith('_total'):
                return raw_name[:-len('_total')]
            # Summary base lines (with quantile label) use the TYPE name directly
            return raw_name

        # Try stripping suffixes to find the TYPE-declared base
        # Histogram suffixes: _bucket, _count, _sum
        for suffix in ['_bucket', '_count', '_sum']:
            if raw_name.endswith(suffix):
                candidate = raw_name[:-len(suffix)]
                if candidate in self._metric_types:
                    ctype = self._metric_types[candidate]
                    if ctype == 'histogram':
                        return candidate
                    if ctype == 'summary' and suffix in ('_count', '_sum'):
                        return candidate

        # Counter _total check (redundant with direct match but covers edge cases)
        if raw_name.endswith('_total'):
            candidate = raw_name[:-len('_total')]
            if candidate in self._metric_types and self._metric_types[candidate] == 'counter':
                return candidate

        # No type info: return as-is
        return raw_name

    def get_metric_names(self):
        """Returns sorted list of all unique base metric names across snapshots."""
        base_names = set()
        for snapshot in self._snapshots:
            for raw_name in snapshot:
                base = self._get_base_metric_name(raw_name)
                base_names.add(base)
        return sorted(base_names)

    def get_snapshot_count(self):
        """Returns total number of snapshot files."""
        return len(self._snapshots)

    def _count_series_per_metric(self, snapshot):
        """Count unique series per base metric in a single snapshot.

        Each (raw_name, label_combination) pair is one unique series.
        Returns dict: base_metric_name -> count.
        """
        counts = defaultdict(int)
        for raw_name, series_list in snapshot.items():
            base = self._get_base_metric_name(raw_name)
            counts[base] += len(series_list)
        return dict(counts)

    def _get_label_values_per_metric(self, snapshot, base_metric_name):
        """Get all label values for a specific base metric in a snapshot.

        Returns dict: label_name -> set of values
        """
        label_values = defaultdict(set)
        for raw_name, series_list in snapshot.items():
            base = self._get_base_metric_name(raw_name)
            if base != base_metric_name:
                continue
            for labels, _ in series_list:
                for k, v in labels.items():
                    label_values[k].add(v)
        return dict(label_values)

    def analyze(self):
        """Run the full analysis pipeline.

        Returns dict with keys: explosions, timeline, root_causes, remediation.
        """
        if not self._snapshots:
            return {"explosions": [], "timeline": {}, "root_causes": {}, "remediation": []}

        num_snapshots = len(self._snapshots)

        # Step 1: Compute per-snapshot cardinality for each base metric
        # cardinality_timeline[base_name][snapshot_idx] = count or None
        cardinality_timeline = defaultdict(lambda: [None] * num_snapshots)

        for idx, snapshot in enumerate(self._snapshots):
            counts = self._count_series_per_metric(snapshot)
            for base_name, count in counts.items():
                cardinality_timeline[base_name][idx] = count

        # Step 2: Detect explosions
        explosions = []
        for base_name, timeline_raw in cardinality_timeline.items():
            actual_values = [(i, c) for i, c in enumerate(timeline_raw) if c is not None]
            if len(actual_values) < 2:
                continue

            initial = actual_values[0][1]
            if initial == 0:
                continue

            peak = max(c for _, c in actual_values)
            growth_factor = peak / initial

            if growth_factor > 5.0 and peak > 100:
                explosions.append({
                    "metric": base_name,
                    "initial_cardinality": initial,
                    "peak_cardinality": peak,
                    "growth_factor": round(growth_factor, 2)
                })

        explosions.sort(key=lambda x: x["growth_factor"], reverse=True)

        # Step 3: Build timeline with interpolation for missing snapshots
        timeline = {}
        for exp in explosions:
            base_name = exp["metric"]
            raw_timeline = cardinality_timeline[base_name]

            interpolated = []
            last_known = 0
            for val in raw_timeline:
                if val is None:
                    interpolated.append(last_known)
                else:
                    interpolated.append(val)
                    last_known = val
            timeline[base_name] = interpolated

        # Step 4: Root cause analysis
        root_causes = {}
        for exp in explosions:
            base_name = exp["metric"]
            raw_timeline = cardinality_timeline[base_name]

            # Find first and peak snapshot indices (where metric is present)
            first_idx = None
            peak_idx = None
            peak_val = 0
            for i, val in enumerate(raw_timeline):
                if val is not None:
                    if first_idx is None:
                        first_idx = i
                    if val > peak_val:
                        peak_val = val
                        peak_idx = i

            if first_idx is None or peak_idx is None:
                continue

            first_labels = self._get_label_values_per_metric(
                self._snapshots[first_idx], base_name
            )
            peak_labels = self._get_label_values_per_metric(
                self._snapshots[peak_idx], base_name
            )

            # Structural labels to ignore
            ignore_labels = {"__name__", "le", "quantile"}

            best_label = None
            best_increase = 0
            best_initial_count = 0
            best_peak_count = 0

            all_labels = set(first_labels.keys()) | set(peak_labels.keys())
            for label in all_labels:
                if label in ignore_labels:
                    continue
                initial_count = len(first_labels.get(label, set()))
                peak_count = len(peak_labels.get(label, set()))
                increase = peak_count - initial_count
                if increase > best_increase:
                    best_increase = increase
                    best_label = label
                    best_initial_count = initial_count
                    best_peak_count = peak_count

            if best_label is None:
                continue

            initial_values = first_labels.get(best_label, set())
            peak_values = peak_labels.get(best_label, set())
            new_values = sorted(peak_values - initial_values)
            sample_new = new_values[:10]

            root_causes[base_name] = {
                "label": best_label,
                "unique_values_initial": best_initial_count,
                "unique_values_peak": best_peak_count,
                "sample_new_values": sample_new
            }

        # Step 5: Generate remediation rules
        remediation = []
        for exp in explosions:
            base_name = exp["metric"]
            if base_name not in root_causes:
                continue
            rc = root_causes[base_name]
            label = rc["label"]

            # Collect ALL new values across all snapshots
            raw_timeline = cardinality_timeline[base_name]
            first_idx = None
            for i, val in enumerate(raw_timeline):
                if val is not None:
                    first_idx = i
                    break

            initial_values = self._get_label_values_per_metric(
                self._snapshots[first_idx], base_name
            ).get(label, set())

            all_new_values = set()
            for idx, snapshot in enumerate(self._snapshots):
                if idx == first_idx:
                    continue
                current_labels = self._get_label_values_per_metric(snapshot, base_name)
                current_values = current_labels.get(label, set())
                all_new_values.update(current_values - initial_values)

            regex = self._generate_regex_for_values(list(all_new_values))

            remediation.append({
                "source_labels": [label],
                "regex": regex,
                "action": "drop",
                "target_metric": base_name
            })

        return {
            "explosions": explosions,
            "timeline": timeline,
            "root_causes": root_causes,
            "remediation": remediation
        }

    def _generate_regex_for_values(self, values):
        """Generate a regex pattern that matches at least 90% of the given values."""
        if not values:
            return ".*"

        # Check if values look like UUIDs
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        )
        uuid_matches = sum(1 for v in values if uuid_pattern.match(v))
        if uuid_matches >= len(values) * 0.9:
            return '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'

        # Check if values look like IP:port
        ip_port_pattern = re.compile(r'^\d+\.\d+\.\d+\.\d+:\d+$')
        ip_matches = sum(1 for v in values if ip_port_pattern.match(v))
        if ip_matches >= len(values) * 0.9:
            return r'\d+\.\d+\.\d+\.\d+:\d+'

        # Check if values contain colons and slashes (structured key patterns)
        has_special = sum(1 for v in values if ':' in v or '/' in v)
        if has_special >= len(values) * 0.9:
            return r'[a-z]+[:/][a-z0-9/:.]+'

        # Fallback
        return '.+'


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description='Metrics Cardinality Explosion Forensics Engine'
    )
    parser.add_argument(
        'snapshots_dir',
        help='Path to directory containing .prom snapshot files'
    )
    parser.add_argument(
        '--summary',
        action='store_true',
        help='Print only explosion summary'
    )
    args = parser.parse_args()

    engine = CardinalityForensicsEngine(args.snapshots_dir)
    result = engine.analyze()

    if args.summary:
        print(json.dumps(result['explosions'], indent=2))
    else:
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
PYEOF

chmod +x /app/engine.py

echo "Solution written to /app/engine.py"
