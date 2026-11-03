#!/usr/bin/env python3
"""
Agent Material Search Tool

A lightweight tool for searching and downloading open-source materials
(GitHub repos, HuggingFace datasets) from inside a Docker container.
Uses only Python stdlib — zero extra dependencies.

Usage:
    python /app/tools/search_materials.py search-github "flask web framework"
    python /app/tools/search_materials.py search-hf "sentiment analysis"
    python /app/tools/search_materials.py clone pallets/flask
    python /app/tools/search_materials.py download-hf imdb
    python /app/tools/search_materials.py list
    python /app/tools/search_materials.py cleanup [name]
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MATERIALS_DIR = Path("/app/materials")
TOTAL_SIZE_LIMIT_MB = 200  # hard cap on total materials size

# GitHub token pool for round-robin rotation (raises the API rate limit).
_DEFAULT_GITHUB_TOKENS: list[str] = []

# Resolved at runtime
_github_tokens: list[str] = []
_github_token_index: int = 0


def _resolve_github_tokens(cli_token: str | None = None) -> list[str]:
    """Resolve GitHub tokens: CLI flag > env var > built-in defaults.

    Supports comma-separated tokens for multiple token rotation.
    """
    if cli_token:
        return [t.strip() for t in cli_token.split(",") if t.strip()]
    env = os.environ.get("GITHUB_TOKEN")
    if env:
        return [t.strip() for t in env.split(",") if t.strip()]
    return list(_DEFAULT_GITHUB_TOKENS)


def _next_github_token() -> str | None:
    """Get the next token from the pool (round-robin)."""
    global _github_token_index
    if not _github_tokens:
        return None
    token = _github_tokens[_github_token_index % len(_github_tokens)]
    _github_token_index += 1
    return token


def _github_headers() -> dict:
    """Return HTTP headers for GitHub API requests (rotates token on each call)."""
    hdrs = {}
    token = _next_github_token()
    if token:
        hdrs["Authorization"] = f"token {token}"
    return hdrs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _err(msg: str) -> None:
    """Print error to stderr."""
    print(f"ERROR: {msg}", file=sys.stderr)


def _info(msg: str) -> None:
    """Print info to stdout."""
    print(msg)


def _dir_size_mb(path: Path) -> float:
    """Return total size of a directory in MB."""
    total = 0
    for f in path.rglob("*"):
        if f.is_file():
            total += f.stat().st_size
    return total / (1024 * 1024)


def _check_space(extra_mb: float = 0) -> bool:
    """Check whether adding extra_mb would exceed the total size limit."""
    if not MATERIALS_DIR.exists():
        current = 0.0
    else:
        current = _dir_size_mb(MATERIALS_DIR)
    if current + extra_mb > TOTAL_SIZE_LIMIT_MB:
        _err(
            f"Space check failed: current {current:.1f} MB + "
            f"requested {extra_mb:.1f} MB > limit {TOTAL_SIZE_LIMIT_MB} MB. "
            f"Run 'cleanup' to free space."
        )
        return False
    return True


def _api_get(url: str, headers: dict = None, max_retries: int = 3, timeout: int = None) -> dict:
    """Perform a GET request and return parsed JSON.

    Automatically retries on:
    - HTTP 403/429 (rate limit) with longer backoff
    - HTTP 5xx (server error) with short backoff
    - Network errors / timeouts with short backoff
    """
    import time

    # HuggingFace can be slow behind proxies — use longer timeout
    if timeout is None:
        timeout = 60 if "huggingface.co" in url else 30

    for attempt in range(max_retries + 1):
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "search-materials/1.0")
        if headers:
            for k, v in headers.items():
                req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")[:200]
            if e.code in (403, 429) and attempt < max_retries:
                wait = 30 * (attempt + 1)  # 30s, 60s, 90s
                _info(f"Rate limited (HTTP {e.code}). Waiting {wait}s before retry ({attempt + 1}/{max_retries})...")
                time.sleep(wait)
                continue
            if e.code >= 500 and attempt < max_retries:
                wait = 5 * (attempt + 1)  # 5s, 10s, 15s
                _info(f"Server error (HTTP {e.code}). Retrying in {wait}s ({attempt + 1}/{max_retries})...")
                time.sleep(wait)
                continue
            _err(f"HTTP {e.code} from {url}: {body}")
            sys.exit(1)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            if attempt < max_retries:
                wait = 10 * (attempt + 1)  # 10s, 20s, 30s
                reason = getattr(e, "reason", str(e))
                _info(f"Network error: {reason}. Retrying in {wait}s ({attempt + 1}/{max_retries})...")
                time.sleep(wait)
                continue
            _err(f"Request failed for {url}: {e}")
            sys.exit(1)
    _err(f"Max retries exceeded for {url}")
    sys.exit(1)


def _format_size(kb: int) -> str:
    """Format size in KB to human-readable string."""
    if kb < 1024:
        return f"{kb} KB"
    return f"{kb / 1024:.1f} MB"


def _format_number(n: int) -> str:
    """Format large numbers with K/M suffix."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def _table(rows: list[list[str]], headers: list[str]) -> str:
    """Render a simple text table."""
    all_rows = [headers] + rows
    widths = [max(len(str(cell)) for cell in col) for col in zip(*all_rows)]
    sep = "  "
    lines = []
    # header
    lines.append(sep.join(str(h).ljust(w) for h, w in zip(headers, widths)))
    lines.append(sep.join("-" * w for w in widths))
    for row in rows:
        lines.append(sep.join(str(c).ljust(w) for c, w in zip(row, widths)))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def _do_github_search(q: str, limit: int) -> dict:
    """Execute a single GitHub search API call and return the JSON response."""
    params = urllib.parse.urlencode({
        "q": q,
        "sort": "stars",
        "order": "desc",
        "per_page": str(limit),
    })
    url = f"https://api.github.com/search/repositories?{params}"
    return _api_get(url, headers=_github_headers())


def cmd_search_github(query: str, limit: int = 10, max_size: int = 0) -> int:
    """Search GitHub repositories by query, sorted by stars.

    If the full query returns no results, automatically retries with
    progressively fewer keywords (dropping from the right) until results
    are found or only one keyword remains.
    """
    q = query
    if max_size > 0:
        q += f" size:<={max_size * 1024}"  # size in KB

    data = _do_github_search(q, limit)
    items = data.get("items", [])
    used_query = query

    # Auto-fallback: drop keywords from the right until we get results
    if not items:
        words = query.split()
        while len(words) > 1 and not items:
            words = words[:-1]
            fallback_q = " ".join(words)
            if max_size > 0:
                fallback_q += f" size:<={max_size * 1024}"
            data = _do_github_search(fallback_q, limit)
            items = data.get("items", [])
            if items:
                used_query = " ".join(words)
                _info(f"(No results for \"{query}\", auto-reduced to \"{used_query}\")")
                _info("Tip: if these results are not relevant, try different or shorter keywords.\n")

    if not items:
        _info(f"No repositories found for \"{query}\".")
        _info("Tip: try shorter or broader keywords, e.g.:")
        words = query.split()
        if len(words) >= 2:
            _info(f'  python /app/tools/search_materials.py search-github "{words[0]}"')
        return 0

    rows = []
    for i, repo in enumerate(items, 1):
        rows.append([
            str(i),
            repo["full_name"],
            _format_number(repo.get("stargazers_count", 0)),
            _format_size(repo.get("size", 0)),
            repo.get("language") or "—",
            (repo.get("description") or "")[:60],
        ])

    _info(f"\nGitHub results for: {used_query}\n")
    _info(_table(rows, ["#", "Repository", "Stars", "Size", "Lang", "Description"]))
    _info(f"\nTotal: {data.get('total_count', 0)} matches (showing top {len(items)})")
    _info(f"\nTo clone a repo:\n  python /app/tools/search_materials.py clone <owner/repo>")
    return 0


def _do_hf_search(query: str, limit: int) -> list:
    """Execute a single HuggingFace dataset search API call."""
    params = urllib.parse.urlencode({
        "search": query,
        "sort": "downloads",
        "direction": "-1",
        "limit": str(limit),
    })
    url = f"https://huggingface.co/api/datasets?{params}"
    data = _api_get(url)
    if isinstance(data, list):
        return data
    return []


def cmd_search_hf(query: str, limit: int = 10) -> int:
    """Search HuggingFace datasets by query, sorted by downloads.

    If the full query returns no results, automatically retries with
    progressively fewer keywords (dropping from the right) until results
    are found or only one keyword remains.
    """
    data = _do_hf_search(query, limit)
    used_query = query

    # Auto-fallback: drop keywords from the right until we get results
    if not data:
        words = query.split()
        while len(words) > 1 and not data:
            words = words[:-1]
            fallback_q = " ".join(words)
            data = _do_hf_search(fallback_q, limit)
            if data:
                used_query = fallback_q
                _info(f"(No results for \"{query}\", auto-reduced to \"{used_query}\")")
                _info("Tip: if these results are not relevant, try different or shorter keywords.\n")

    if not data:
        _info(f"No datasets found for \"{query}\".")
        _info("Tip: try shorter or broader keywords, e.g.:")
        words = query.split()
        if len(words) >= 2:
            _info(f'  python /app/tools/search_materials.py search-hf "{words[0]}"')
        return 0

    rows = []
    for i, ds in enumerate(data, 1):
        rows.append([
            str(i),
            ds.get("id", "?"),
            _format_number(ds.get("downloads", 0)),
            str(ds.get("likes", 0)),
            (", ".join(ds.get("tags", []))[:50]) or "—",
        ])

    _info(f"\nHuggingFace dataset results for: {used_query}\n")
    _info(_table(rows, ["#", "Dataset", "Downloads", "Likes", "Tags"]))
    _info(f"\nShowing top {len(data)} results.")
    _info(f"\nTo download a dataset:\n  python /app/tools/search_materials.py download-hf <dataset_id>")
    return 0


def cmd_clone(repo: str, max_size: int = 50) -> int:
    """Shallow-clone a GitHub repo into /app/materials/."""
    if "/" not in repo:
        _err(f"Invalid repo format: '{repo}'. Use owner/repo (e.g. pallets/flask)")
        return 1

    # Check repo size first via API
    url = f"https://api.github.com/repos/{repo}"
    info = _api_get(url, headers=_github_headers())
    size_kb = info.get("size", 0)
    size_mb = size_kb / 1024

    if size_mb > max_size:
        _err(f"Repository {repo} is {size_mb:.1f} MB, exceeds --max-size {max_size} MB.")
        return 1

    if not _check_space(size_mb):
        return 1

    MATERIALS_DIR.mkdir(parents=True, exist_ok=True)
    repo_name = repo.replace("/", "_")
    dest = MATERIALS_DIR / repo_name

    if dest.exists():
        _info(f"Already exists: {dest}")
        return 0

    token = _next_github_token()
    if token:
        clone_url = f"https://x-access-token:{token}@github.com/{repo}.git"
    else:
        clone_url = f"https://github.com/{repo}.git"
    _info(f"Cloning {repo} ({size_mb:.1f} MB) ...")
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", clone_url, str(dest)],
            check=True,
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.CalledProcessError as e:
        _err(f"git clone failed: {e.stderr.strip()}")
        return 1
    except subprocess.TimeoutExpired:
        _err("git clone timed out (300s).")
        return 1

    # Remove .git directory to save space
    git_dir = dest / ".git"
    if git_dir.exists():
        import shutil
        shutil.rmtree(git_dir)

    actual_mb = _dir_size_mb(dest)
    _info(f"Cloned to {dest} ({actual_mb:.1f} MB, .git removed)")
    return 0


def cmd_download_hf(
    dataset_id: str,
    max_files: int = 3,
    max_file_size: int = 50,
    file_pattern: str = None,
) -> int:
    """Download files from a HuggingFace dataset."""
    # List files in the dataset via API
    url = f"https://huggingface.co/api/datasets/{dataset_id}/tree/main"
    try:
        files = _api_get(url)
    except SystemExit:
        _err(f"Could not list files for dataset '{dataset_id}'. Check the ID.")
        return 1

    if not isinstance(files, list):
        _err(f"Unexpected API response for dataset '{dataset_id}'.")
        return 1

    # Filter to actual files (not directories)
    file_entries = [f for f in files if f.get("type") == "file"]

    if not file_entries:
        _info(f"No files found in dataset '{dataset_id}'.")
        return 0

    # Apply file pattern filter
    if file_pattern:
        import fnmatch
        file_entries = [
            f for f in file_entries
            if fnmatch.fnmatch(f["path"], file_pattern)
        ]
        if not file_entries:
            _info(f"No files matching '{file_pattern}' in dataset '{dataset_id}'.")
            return 0

    # Skip metadata/boilerplate files — prioritize actual data
    _SKIP_NAMES = {
        ".gitattributes", ".gitignore", "LICENSE", "LICENSE.md",
        "LICENSE.txt", "NOTICE", "NOTICE.md",
    }
    _DATA_EXTENSIONS = {
        ".csv", ".tsv", ".json", ".jsonl", ".parquet", ".arrow",
        ".txt", ".xml", ".sql", ".db", ".sqlite", ".yaml", ".yml",
        ".npy", ".npz", ".pkl", ".pickle", ".feather", ".h5", ".hdf5",
    }

    # Filter by size, skip useless files
    downloadable = []
    for f in file_entries:
        fname = Path(f["path"]).name
        if fname in _SKIP_NAMES:
            continue
        size_bytes = f.get("size", 0)
        size_mb = size_bytes / (1024 * 1024)
        if size_mb <= max_file_size:
            # Score: data files first, then by size ascending
            ext = Path(fname).suffix.lower()
            is_data = ext in _DATA_EXTENSIONS
            downloadable.append((f["path"], size_bytes, size_mb, is_data))

    if not downloadable:
        _info("All files exceed --max-file-size limit or are metadata-only.")
        return 0

    # Sort: data files first, then by size ascending
    downloadable.sort(key=lambda x: (not x[3], x[1]))
    to_download = [(p, s, m) for p, s, m, _ in downloadable[:max_files]]

    total_mb = sum(m for _, _, m in to_download)
    if not _check_space(total_mb):
        return 1

    MATERIALS_DIR.mkdir(parents=True, exist_ok=True)
    ds_name = dataset_id.replace("/", "_")
    dest_dir = MATERIALS_DIR / ds_name
    dest_dir.mkdir(parents=True, exist_ok=True)

    _info(f"\nDownloading {len(to_download)} file(s) from {dataset_id} ...")

    for fpath, size_bytes, size_mb in to_download:
        file_url = (
            f"https://huggingface.co/datasets/{dataset_id}"
            f"/resolve/main/{urllib.parse.quote(fpath)}"
        )
        local_path = dest_dir / Path(fpath).name
        _info(f"  {fpath} ({size_mb:.1f} MB) -> {local_path}")
        try:
            urllib.request.urlretrieve(file_url, str(local_path))
        except Exception as e:
            _err(f"  Failed to download {fpath}: {e}")
            continue

    actual_mb = _dir_size_mb(dest_dir)
    _info(f"\nSaved to {dest_dir} ({actual_mb:.1f} MB)")
    return 0


def cmd_list() -> int:
    """List downloaded materials."""
    if not MATERIALS_DIR.exists() or not any(MATERIALS_DIR.iterdir()):
        _info("No materials downloaded yet.")
        _info(f"Materials directory: {MATERIALS_DIR}")
        return 0

    rows = []
    total = 0.0
    for item in sorted(MATERIALS_DIR.iterdir()):
        if not item.name.startswith("."):
            size = _dir_size_mb(item) if item.is_dir() else item.stat().st_size / (1024 * 1024)
            total += size
            n_files = sum(1 for _ in item.rglob("*") if _.is_file()) if item.is_dir() else 1
            rows.append([
                item.name,
                f"{size:.1f} MB",
                str(n_files),
                "dir" if item.is_dir() else "file",
            ])

    _info(f"\nMaterials in {MATERIALS_DIR}:\n")
    _info(_table(rows, ["Name", "Size", "Files", "Type"]))
    _info(f"\nTotal: {total:.1f} MB / {TOTAL_SIZE_LIMIT_MB} MB limit")
    return 0


def cmd_cleanup(name: str = None) -> int:
    """Remove downloaded materials."""
    import shutil

    if not MATERIALS_DIR.exists():
        _info("Nothing to clean up.")
        return 0

    if name:
        target = MATERIALS_DIR / name
        if not target.exists():
            _err(f"Not found: {target}")
            return 1
        size = _dir_size_mb(target) if target.is_dir() else target.stat().st_size / (1024 * 1024)
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
        _info(f"Removed {name} ({size:.1f} MB freed)")
    else:
        size = _dir_size_mb(MATERIALS_DIR)
        shutil.rmtree(MATERIALS_DIR)
        MATERIALS_DIR.mkdir(parents=True, exist_ok=True)
        _info(f"Cleaned all materials ({size:.1f} MB freed)")

    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Search and download materials for task generation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--token",
        default=None,
        help="GitHub personal access token (overrides GITHUB_TOKEN env and built-in default)"
    )
    sub = parser.add_subparsers(dest="command")

    # search-github
    p_sg = sub.add_parser("search-github", help="Search GitHub repositories")
    p_sg.add_argument("query", help="Search query")
    p_sg.add_argument("--limit", type=int, default=10, help="Max results (default: 10)")
    p_sg.add_argument("--max-size", type=int, default=0, help="Repo size limit in MB for search filter (default: 0 = no filter)")

    # search-hf
    p_shf = sub.add_parser("search-hf", help="Search HuggingFace datasets")
    p_shf.add_argument("query", help="Search query")
    p_shf.add_argument("--limit", type=int, default=10, help="Max results (default: 10)")

    # clone
    p_cl = sub.add_parser("clone", help="Clone a GitHub repo to /app/materials/")
    p_cl.add_argument("repo", help="Repository as owner/repo (e.g. pallets/flask)")
    p_cl.add_argument("--max-size", type=int, default=50, help="Repo size limit in MB (default: 50)")

    # download-hf
    p_dhf = sub.add_parser("download-hf", help="Download HuggingFace dataset files")
    p_dhf.add_argument("dataset_id", help="Dataset ID (e.g. imdb, squad)")
    p_dhf.add_argument("--max-files", type=int, default=3, help="Max files to download (default: 3)")
    p_dhf.add_argument("--max-file-size", type=int, default=50, help="Max single file size in MB (default: 50)")
    p_dhf.add_argument("--file", dest="file_pattern", help="File name filter pattern (e.g. '*.csv')")

    # list
    sub.add_parser("list", help="List downloaded materials")

    # cleanup
    p_clean = sub.add_parser("cleanup", help="Remove downloaded materials")
    p_clean.add_argument("name", nargs="?", default=None, help="Specific material to remove (default: all)")

    args = parser.parse_args()

    # Resolve GitHub tokens: --token > GITHUB_TOKEN env > built-in defaults
    global _github_tokens
    _github_tokens = _resolve_github_tokens(args.token)

    if not args.command:
        parser.print_help()
        return 1

    if args.command == "search-github":
        return cmd_search_github(args.query, args.limit, args.max_size)
    elif args.command == "search-hf":
        return cmd_search_hf(args.query, args.limit)
    elif args.command == "clone":
        return cmd_clone(args.repo, args.max_size)
    elif args.command == "download-hf":
        return cmd_download_hf(
            args.dataset_id, args.max_files, args.max_file_size, args.file_pattern
        )
    elif args.command == "list":
        return cmd_list()
    elif args.command == "cleanup":
        return cmd_cleanup(args.name)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
