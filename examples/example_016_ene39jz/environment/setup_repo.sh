#!/bin/bash
set -e

git config --global user.email "dev@example.com"
git config --global user.name "Developer"
git config --global init.defaultBranch main

# ============================================================
# Create the "golden" repository with full history
# ============================================================
mkdir -p /tmp/golden
cd /tmp/golden
git init

# Initial commit: project setup
mkdir -p src tests docs
cat > src/config.py << 'PYEOF'
# Application Configuration
DATABASE_URL = "sqlite:///app.db"
DEBUG = False
LOG_LEVEL = "INFO"
MAX_RETRIES = 3
TIMEOUT = 30
SECRET_KEY = "change-me-in-production"
PYEOF

cat > src/app.py << 'PYEOF'
#!/usr/bin/env python3
"""Main application module."""

from config import DATABASE_URL, DEBUG, LOG_LEVEL

class Application:
    def __init__(self):
        self.db_url = DATABASE_URL
        self.debug = DEBUG
        self.log_level = LOG_LEVEL
        self.plugins = []

    def start(self):
        print(f"Starting app with DB: {self.db_url}")
        print(f"Debug: {self.debug}, Log Level: {self.log_level}")
        for plugin in self.plugins:
            plugin.initialize()
        return True

    def stop(self):
        print("Shutting down...")
        for plugin in self.plugins:
            plugin.cleanup()
        return True

    def register_plugin(self, plugin):
        self.plugins.append(plugin)

if __name__ == "__main__":
    app = Application()
    app.start()
PYEOF

cat > src/utils.py << 'PYEOF'
"""Utility functions."""

def parse_duration(s):
    """Parse a duration string like '5m', '2h', '1d' into seconds."""
    units = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
    if not s:
        return 0
    unit = s[-1].lower()
    if unit in units:
        return int(s[:-1]) * units[unit]
    return int(s)

def format_size(bytes_val):
    """Format bytes into human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_val < 1024:
            return f"{bytes_val:.1f}{unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f}TB"

def retry(func, max_retries=3, delay=1):
    """Retry a function up to max_retries times."""
    last_error = None
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            last_error = e
    raise last_error
PYEOF

cat > tests/test_utils.py << 'PYEOF'
"""Tests for utility functions."""

def test_parse_duration():
    assert parse_duration('5m') == 300
    assert parse_duration('2h') == 7200
    assert parse_duration('1d') == 86400

def test_format_size():
    assert format_size(500) == "500.0B"
    assert format_size(1024) == "1.0KB"
PYEOF

cat > docs/README.md << 'PYEOF'
# MyProject

A sample application for demonstration.

## Setup

1. Install dependencies
2. Configure database
3. Run the application

## Architecture

The application uses a plugin-based architecture.
PYEOF

git add -A
git commit -m "Initial project setup with core modules"

# Second commit on main: add logging
cat > src/logger.py << 'PYEOF'
"""Logging module."""
import logging

def setup_logging(level="INFO"):
    """Configure application logging."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger('myproject')

logger = setup_logging()
PYEOF

git add src/logger.py
git commit -m "Add logging module"

# ============================================================
# Branch: feature/auth - Authentication system
# ============================================================
git checkout -b feature/auth

cat > src/auth.py << 'PYEOF'
"""Authentication module."""
import hashlib
import secrets

class AuthManager:
    def __init__(self):
        self.users = {}
        self.sessions = {}

    def create_user(self, username, password):
        salt = secrets.token_hex(16)
        hashed = hashlib.sha256((password + salt).encode()).hexdigest()
        self.users[username] = {"hash": hashed, "salt": salt, "role": "user"}
        return True

    def authenticate(self, username, password):
        if username not in self.users:
            return None
        user = self.users[username]
        hashed = hashlib.sha256((password + user["salt"]).encode()).hexdigest()
        if hashed == user["hash"]:
            token = secrets.token_urlsafe(32)
            self.sessions[token] = username
            return token
        return None

    def verify_session(self, token):
        return self.sessions.get(token)

    def revoke_session(self, token):
        if token in self.sessions:
            del self.sessions[token]
            return True
        return False
PYEOF

# Modify app.py to add auth integration (this will cause conflicts)
cat > src/app.py << 'PYEOF'
#!/usr/bin/env python3
"""Main application module."""

from config import DATABASE_URL, DEBUG, LOG_LEVEL
from auth import AuthManager
from logger import setup_logging, logger

class Application:
    def __init__(self):
        self.db_url = DATABASE_URL
        self.debug = DEBUG
        self.log_level = LOG_LEVEL
        self.plugins = []
        self.auth = AuthManager()
        logger.info("Application initialized with auth")

    def start(self):
        logger.info(f"Starting app with DB: {self.db_url}")
        logger.info(f"Debug: {self.debug}, Log Level: {self.log_level}")
        for plugin in self.plugins:
            plugin.initialize()
        logger.info("Auth system ready")
        return True

    def stop(self):
        logger.info("Shutting down...")
        for plugin in self.plugins:
            plugin.cleanup()
        return True

    def register_plugin(self, plugin):
        self.plugins.append(plugin)
        logger.info(f"Plugin registered: {plugin.__class__.__name__}")

if __name__ == "__main__":
    app = Application()
    app.start()
PYEOF

# Modify config.py to add auth settings
cat > src/config.py << 'PYEOF'
# Application Configuration
DATABASE_URL = "sqlite:///app.db"
DEBUG = False
LOG_LEVEL = "INFO"
MAX_RETRIES = 3
TIMEOUT = 30
SECRET_KEY = "change-me-in-production"

# Auth Configuration
SESSION_TIMEOUT = 3600
MAX_LOGIN_ATTEMPTS = 5
PASSWORD_MIN_LENGTH = 8
PYEOF

git add -A
git commit -m "Add authentication system with session management"

# Second commit on feature/auth
cat > src/middleware.py << 'PYEOF'
"""Request middleware."""

class AuthMiddleware:
    def __init__(self, auth_manager):
        self.auth = auth_manager

    def process_request(self, request):
        token = request.get("Authorization", "").replace("Bearer ", "")
        if not token:
            return {"error": "Missing authentication", "status": 401}
        username = self.auth.verify_session(token)
        if not username:
            return {"error": "Invalid session", "status": 403}
        request["user"] = username
        return None

    def process_response(self, response):
        response["X-Auth-Version"] = "1.0"
        return response
PYEOF

git add src/middleware.py
git commit -m "Add authentication middleware"

# ============================================================
# Branch: feature/cache - Caching system (branches from main)
# ============================================================
git checkout main
git checkout -b feature/cache

cat > src/cache.py << 'PYEOF'
"""Caching module with TTL support."""
import time
from collections import OrderedDict

class LRUCache:
    def __init__(self, max_size=1000, default_ttl=300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache = OrderedDict()
        self.timestamps = {}

    def get(self, key):
        if key not in self.cache:
            return None
        if self._is_expired(key):
            self.delete(key)
            return None
        self.cache.move_to_end(key)
        return self.cache[key]

    def set(self, key, value, ttl=None):
        if key in self.cache:
            self.cache.move_to_end(key)
        elif len(self.cache) >= self.max_size:
            oldest = next(iter(self.cache))
            self.delete(oldest)
        self.cache[key] = value
        self.timestamps[key] = (time.time(), ttl or self.default_ttl)

    def delete(self, key):
        if key in self.cache:
            del self.cache[key]
        if key in self.timestamps:
            del self.timestamps[key]

    def clear(self):
        self.cache.clear()
        self.timestamps.clear()

    def _is_expired(self, key):
        if key not in self.timestamps:
            return True
        created, ttl = self.timestamps[key]
        return (time.time() - created) > ttl

    def stats(self):
        valid = sum(1 for k in self.cache if not self._is_expired(k))
        return {"total": len(self.cache), "valid": valid, "max_size": self.max_size}
PYEOF

# Modify app.py to add cache integration (different from auth branch - conflict!)
cat > src/app.py << 'PYEOF'
#!/usr/bin/env python3
"""Main application module."""

from config import DATABASE_URL, DEBUG, LOG_LEVEL
from cache import LRUCache
from logger import setup_logging, logger

class Application:
    def __init__(self):
        self.db_url = DATABASE_URL
        self.debug = DEBUG
        self.log_level = LOG_LEVEL
        self.plugins = []
        self.cache = LRUCache()
        logger.info("Application initialized with cache")

    def start(self):
        logger.info(f"Starting app with DB: {self.db_url}")
        logger.info(f"Debug: {self.debug}, Log Level: {self.log_level}")
        for plugin in self.plugins:
            plugin.initialize()
        logger.info(f"Cache ready: {self.cache.stats()}")
        return True

    def stop(self):
        logger.info("Shutting down...")
        self.cache.clear()
        for plugin in self.plugins:
            plugin.cleanup()
        return True

    def register_plugin(self, plugin):
        self.plugins.append(plugin)
        logger.info(f"Plugin registered: {plugin.__class__.__name__}")

if __name__ == "__main__":
    app = Application()
    app.start()
PYEOF

# Modify config.py to add cache settings (different from auth branch - conflict!)
cat > src/config.py << 'PYEOF'
# Application Configuration
DATABASE_URL = "sqlite:///app.db"
DEBUG = False
LOG_LEVEL = "INFO"
MAX_RETRIES = 3
TIMEOUT = 30
SECRET_KEY = "change-me-in-production"

# Cache Configuration
CACHE_MAX_SIZE = 5000
CACHE_DEFAULT_TTL = 600
CACHE_BACKEND = "memory"
PYEOF

git add -A
git commit -m "Add LRU cache with TTL support"

# ============================================================
# Branch: feature/monitoring - Monitoring (branches from main)
# ============================================================
git checkout main
git checkout -b feature/monitoring

cat > src/monitor.py << 'PYEOF'
"""System monitoring module."""
import time
from collections import defaultdict

class Monitor:
    def __init__(self):
        self.metrics = defaultdict(list)
        self.alerts = []
        self.thresholds = {}

    def record(self, metric_name, value):
        self.metrics[metric_name].append({
            "value": value,
            "timestamp": time.time()
        })
        self._check_threshold(metric_name, value)

    def set_threshold(self, metric_name, max_value):
        self.thresholds[metric_name] = max_value

    def _check_threshold(self, metric_name, value):
        if metric_name in self.thresholds:
            if value > self.thresholds[metric_name]:
                self.alerts.append({
                    "metric": metric_name,
                    "value": value,
                    "threshold": self.thresholds[metric_name],
                    "timestamp": time.time()
                })

    def get_average(self, metric_name, window=60):
        now = time.time()
        recent = [
            m["value"] for m in self.metrics[metric_name]
            if now - m["timestamp"] < window
        ]
        if not recent:
            return 0
        return sum(recent) / len(recent)

    def get_alerts(self, since=None):
        if since is None:
            return self.alerts
        return [a for a in self.alerts if a["timestamp"] >= since]

    def summary(self):
        result = {}
        for name, values in self.metrics.items():
            vals = [v["value"] for v in values]
            result[name] = {
                "count": len(vals),
                "avg": sum(vals) / len(vals) if vals else 0,
                "min": min(vals) if vals else 0,
                "max": max(vals) if vals else 0,
            }
        return result
PYEOF

# Modify utils.py to add monitoring helpers
cat > src/utils.py << 'PYEOF'
"""Utility functions."""

def parse_duration(s):
    """Parse a duration string like '5m', '2h', '1d' into seconds."""
    units = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
    if not s:
        return 0
    unit = s[-1].lower()
    if unit in units:
        return int(s[:-1]) * units[unit]
    return int(s)

def format_size(bytes_val):
    """Format bytes into human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_val < 1024:
            return f"{bytes_val:.1f}{unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f}TB"

def retry(func, max_retries=3, delay=1):
    """Retry a function up to max_retries times."""
    last_error = None
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            last_error = e
    raise last_error

def timing_decorator(func):
    """Decorator to measure function execution time."""
    import time
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start
        return result, duration
    wrapper.__name__ = func.__name__
    return wrapper

def health_check(components):
    """Check health of all components, return status dict."""
    status = {}
    for name, component in components.items():
        try:
            if hasattr(component, 'stats'):
                status[name] = {"healthy": True, "stats": component.stats()}
            else:
                status[name] = {"healthy": True}
        except Exception as e:
            status[name] = {"healthy": False, "error": str(e)}
    return status
PYEOF

git add -A
git commit -m "Add monitoring system with alerts and thresholds"

# ============================================================
# Now create the "stash" content on feature/cache
# ============================================================
git checkout feature/cache

cat > src/cache_warmup.py << 'PYEOF'
"""Cache warmup module for pre-loading frequently accessed data."""

class CacheWarmer:
    def __init__(self, cache, data_source):
        self.cache = cache
        self.data_source = data_source
        self.warmup_keys = []

    def register_key(self, key, loader_func, ttl=None):
        self.warmup_keys.append({
            "key": key,
            "loader": loader_func,
            "ttl": ttl
        })

    def warmup(self):
        results = {"success": 0, "failed": 0}
        for entry in self.warmup_keys:
            try:
                value = entry["loader"]()
                self.cache.set(entry["key"], value, entry["ttl"])
                results["success"] += 1
            except Exception:
                results["failed"] += 1
        return results

    def schedule_warmup(self, interval=300):
        """Schedule periodic cache warmup."""
        import threading
        def _run():
            while True:
                self.warmup()
                import time
                time.sleep(interval)
        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        return thread
PYEOF

# Also add get_or_set to cache.py
cat >> src/cache.py << 'PYEOF'

    def get_or_set(self, key, loader_func, ttl=None):
        """Get from cache or compute and store."""
        value = self.get(key)
        if value is not None:
            return value
        value = loader_func()
        self.set(key, value, ttl)
        return value
PYEOF

# Create the stash commit using git low-level commands
git add -A
STASH_TREE=$(git write-tree)
STASH_PARENT=$(git rev-parse HEAD)
STASH_COMMIT=$(echo "WIP on feature/cache: cache warmup and get_or_set" | git commit-tree $STASH_TREE -p $STASH_PARENT)
echo "STASH_COMMIT=$STASH_COMMIT"

# Reset the working tree (undo the staged changes)
git reset --hard HEAD

# ============================================================
# Create bundles for the feature branches
# ============================================================
mkdir -p /tmp/bundles

git bundle create /tmp/bundles/auth-feature.bundle main..feature/auth
git bundle create /tmp/bundles/cache-feature.bundle main..feature/cache
git bundle create /tmp/bundles/monitoring-feature.bundle main..feature/monitoring

# ============================================================
# Now create the "damaged" repository at /app/project
# ============================================================
mkdir -p /app/project
cd /app/project
git init

# Pull just main branch
git pull /tmp/golden main

# ============================================================
# Store stash objects as loose objects in lost-found
# We need to extract the stash commit and its unique tree/blobs
# ============================================================
mkdir -p /app/project/.git/lost-found/other

# Create a temporary repo to get loose objects from the golden repo
cd /tmp/golden

# Get the objects unique to the stash commit (not in feature/cache)
STASH_OBJECTS=$(git rev-list --objects $STASH_COMMIT ^feature/cache | awk '{print $1}')

# For each object, extract it and copy to lost-found
for OBJ_HASH in $STASH_OBJECTS; do
    # Use git cat-file to get type and content, then create loose object
    OBJ_TYPE=$(git cat-file -t $OBJ_HASH)
    prefix=$(echo $OBJ_HASH | cut -c1-2)
    suffix=$(echo $OBJ_HASH | cut -c3-)
    mkdir -p /app/project/.git/lost-found/other/$prefix
    # Use git's internal format: type + space + size + null + content
    # We can copy from the golden repo's object store
    # First, let's try to find it as a loose object or extract from pack
    python3 -c "
import subprocess, zlib, os, sys

obj_hash = '$OBJ_HASH'
# Get object content using git cat-file
result = subprocess.run(['git', 'cat-file', '-t', obj_hash], capture_output=True, text=True)
obj_type = result.stdout.strip()
result = subprocess.run(['git', 'cat-file', obj_type, obj_hash], capture_output=True)
content = result.stdout
# Git object format: 'type size\0content'
header = f'{obj_type} {len(content)}\0'.encode()
raw = header + content
compressed = zlib.compress(raw)
prefix = obj_hash[:2]
suffix = obj_hash[2:]
out_dir = f'/app/project/.git/lost-found/other/{prefix}'
os.makedirs(out_dir, exist_ok=True)
with open(f'{out_dir}/{suffix}', 'wb') as f:
    f.write(compressed)
"
done

# Also store the stash commit object itself in lost-found
python3 -c "
import subprocess, zlib, os

obj_hash = '$STASH_COMMIT'
result = subprocess.run(['git', 'cat-file', '-t', obj_hash], capture_output=True, text=True)
obj_type = result.stdout.strip()
result = subprocess.run(['git', 'cat-file', obj_type, obj_hash], capture_output=True)
content = result.stdout
header = f'{obj_type} {len(content)}\0'.encode()
raw = header + content
compressed = zlib.compress(raw)
prefix = obj_hash[:2]
suffix = obj_hash[2:]
out_dir = f'/app/project/.git/lost-found/other/{prefix}'
os.makedirs(out_dir, exist_ok=True)
with open(f'{out_dir}/{suffix}', 'wb') as f:
    f.write(compressed)
print(f'Stash commit {obj_hash} stored in lost-found')
"

# ============================================================
# Create a broken stash ref
# ============================================================
cd /app/project
echo "$STASH_COMMIT" > .git/refs/stash

# ============================================================
# Create recovery log
# ============================================================
cat > /app/project/RECOVERY_LOG.txt << 'TXTEOF'
Recovery Log
========================
Repository suffered data loss on the build server.

What we know:
- The main branch appears intact
- Three feature branches were being developed:
  * feature/auth - Authentication system (Alice)
  * feature/cache - Caching layer (Bob)
  * feature/monitoring - Monitoring system (Charlie)
- Bob had stashed some work-in-progress before the crash
- Team members had created git bundles of their work before the incident

Available bundle files:
- /app/bundles/auth-feature.bundle
- /app/bundles/cache-feature.bundle
- /app/bundles/monitoring-feature.bundle

The bundles were created relative to main, so they should be importable.

There's also a backup of some git objects in .git/lost-found/other/
that might contain Bob's stashed changes.

Goal: Restore all branches, recover the stash, merge everything into
main properly, and tag the result as v2.0.0.
TXTEOF

git add RECOVERY_LOG.txt
git commit -m "Add recovery log"

# ============================================================
# Move bundles to /app/bundles
# ============================================================
mkdir -p /app/bundles
cp /tmp/bundles/*.bundle /app/bundles/

# ============================================================
# Save metadata for validation (will be cleaned up by Dockerfile)
# ============================================================
echo "$STASH_COMMIT" > /tmp/metadata_stash_hash.txt
cd /tmp/golden
echo "$(git rev-parse feature/auth)" > /tmp/metadata_auth_head.txt
echo "$(git rev-parse feature/cache)" > /tmp/metadata_cache_head.txt
echo "$(git rev-parse feature/monitoring)" > /tmp/metadata_monitoring_head.txt
echo "$(git rev-parse main)" > /tmp/metadata_main_head.txt

# ============================================================
# Clean up golden repo
# ============================================================
rm -rf /tmp/golden /tmp/golden-bare /tmp/bundles /tmp/main-bundle.bundle

echo "=== Setup complete ==="
echo "Stash hash: $STASH_COMMIT"
