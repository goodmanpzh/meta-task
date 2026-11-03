# Metrics Cardinality Explosion Forensics Engine

You are an SRE responding to a Prometheus storage alert. Your monitoring cluster's TSDB has been growing at an alarming rate, and you need to build a forensics engine that analyzes metric snapshots to identify cardinality explosions, pinpoint root causes, and generate remediation configurations.

## Situation

Under `/app/data/snapshots/` you will find a series of metric snapshot files named `t_{N}.prom` where N represents the snapshot index (taken at regular intervals). Each file contains Prometheus exposition format metrics scraped from multiple services. The metrics include standard counters, gauges, histograms, and summaries with various label combinations.

Something went wrong — one or more metrics experienced a **cardinality explosion** where the number of unique time series (unique label-value combinations) grew uncontrollably. Your job is to build a Python analysis engine at `/app/engine.py` that can process these snapshots and produce a complete forensics report.

## Requirements

Your engine must expose a `CardinalityForensicsEngine` class importable from `/app/engine.py`. The constructor takes the path to the snapshots directory as its only argument. The class must implement the following methods:

### `analyze() -> dict`

This is the primary method that runs the full analysis pipeline and returns a dictionary with four top-level keys: `"explosions"`, `"timeline"`, `"root_causes"`, and `"remediation"`.

**Explosion Detection**: The `"explosions"` key must contain a list of dictionaries, one per metric name that experienced a cardinality explosion. A metric is considered to have exploded if its unique series count grew by more than 5x from its initial to peak value AND its peak series count exceeds 100. Each entry must have `"metric"` (the metric name without type suffix — note that histogram and summary metrics have `_bucket`, `_count`, `_sum`, `_total` suffixes that must be normalized to the base metric name), `"initial_cardinality"` (series count in first snapshot), `"peak_cardinality"` (maximum series count across all snapshots), and `"growth_factor"` (float, peak divided by initial). The list must be sorted by growth_factor in descending order.

**Timeline Reconstruction**: The `"timeline"` key must map each exploded metric name to a list of integers representing the series count at each snapshot index. If a metric is absent from a snapshot entirely (due to partial scrape failure), you must interpolate using the last known value rather than treating it as zero — scrape failures are a known issue in this dataset and treating missing data as zero would produce false change-points.

**Root Cause Analysis**: The `"root_causes"` key must map each exploded metric name to a dictionary with `"label"` (the single label whose value space grew the most and is most responsible for the explosion), `"unique_values_initial"` (number of unique values for that label in the first snapshot), `"unique_values_peak"` (number of unique values at peak), and `"sample_new_values"` (a list of up to 10 label values that appeared after the first snapshot, sorted lexicographically). The root cause label is determined by finding which label had the largest absolute increase in unique values between the first and peak snapshots. You must ignore the `__name__`, `le`, and `quantile` labels during root cause analysis since these are structural labels in Prometheus, not user-defined dimensions.

**Remediation Rules**: The `"remediation"` key must contain a list of Prometheus relabeling rule dictionaries, one per exploded metric. Each rule must follow the Prometheus `metric_relabel_configs` schema with fields: `"source_labels"` (list containing the offending label), `"regex"` (a pattern that matches the high-cardinality values — you must generate a regex that matches at least 90% of the new values that appeared after the first snapshot), `"action"` set to `"drop"`, and `"target_metric"` containing the base metric name this rule applies to.

### `get_metric_names() -> list`

Returns a sorted list of all unique base metric names found across all snapshots. Histogram suffixes (`_bucket`, `_count`, `_sum`, `_total`) and summary suffixes (`_count`, `_sum`, `_total`) must be stripped to produce base names. Be careful: a metric named `http_requests_total` has base name `http_requests` only if it is a counter type — you must use the TYPE comments in the exposition format to determine metric types correctly. If no TYPE comment exists for a metric, treat it as untyped and do not strip suffixes.

### `get_snapshot_count() -> int`

Returns the total number of snapshot files found in the directory.

### CLI Interface

Your engine.py must also be executable from the command line. Running `python3 /app/engine.py /app/data/snapshots/` must write the full analysis report as pretty-printed JSON (indent=2) to stdout. Running `python3 /app/engine.py /app/data/snapshots/ --summary` must print only the explosion detection results (the `"explosions"` list) to stdout as JSON.

## Important Details

The snapshot data contains realistic noise you must handle correctly: some label values contain special characters (colons, slashes, dots) that must be properly escaped in your generated regex patterns. Some snapshots may be missing metrics that appeared in earlier or later snapshots due to simulated scrape failures. For cardinality counting purposes, each exposition line (each unique raw metric name + label combination) counts as one series. This means histogram metrics contribute multiple series per logical metric (one per bucket plus `_count` and `_sum`), and summary metrics contribute one per quantile plus `_count` and `_sum`. The `le` and `quantile` labels are structural and must be present in cardinality counts but excluded from root cause analysis.

You must not use any third-party packages — only the Python 3 standard library is allowed. The engine must process the full dataset in under 30 seconds on a single CPU core.

Write your complete solution to `/app/engine.py`.
