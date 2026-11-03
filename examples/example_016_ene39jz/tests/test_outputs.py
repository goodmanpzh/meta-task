"""Tests for Git repository disaster recovery task.

Verifies that:
1. All three feature branches were restored from bundles
2. The stash was recovered and applied to feature/cache
3. All branches were merged into main with proper conflict resolution
4. The final state includes all features integrated
5. The v2.0.0 tag exists on main
6. Commit graph structure is correct (merge commits with proper parents)
"""

import subprocess
import os
import re

REPO_DIR = "/app/project"


def run_git(*args):
    """Run a git command in the project directory and return stdout."""
    result = subprocess.run(
        ["git"] + list(args),
        cwd=REPO_DIR,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def read_file(path):
    """Read a file relative to the repo directory."""
    full_path = os.path.join(REPO_DIR, path)
    with open(full_path, "r") as f:
        return f.read()


# ============================================================
# Test 1: Feature branches exist
# ============================================================
class TestBranchRestoration:
    def test_feature_auth_branch_exists(self):
        stdout, _, rc = run_git("rev-parse", "--verify", "feature/auth")
        assert rc == 0, "feature/auth branch does not exist"

    def test_feature_cache_branch_exists(self):
        stdout, _, rc = run_git("rev-parse", "--verify", "feature/cache")
        assert rc == 0, "feature/cache branch does not exist"

    def test_feature_monitoring_branch_exists(self):
        stdout, _, rc = run_git("rev-parse", "--verify", "feature/monitoring")
        assert rc == 0, "feature/monitoring branch does not exist"

    def test_main_branch_exists(self):
        stdout, _, rc = run_git("rev-parse", "--verify", "main")
        assert rc == 0, "main branch does not exist"


# ============================================================
# Test 2: Stash recovery and application
# ============================================================
class TestStashRecovery:
    def test_cache_warmup_file_exists_on_cache_branch(self):
        """The recovered stash should have added cache_warmup.py to feature/cache."""
        stdout, _, rc = run_git("ls-tree", "feature/cache", "src/cache_warmup.py")
        assert rc == 0 and "cache_warmup.py" in stdout, (
            "src/cache_warmup.py not found on feature/cache branch"
        )

    def test_cache_warmup_has_correct_content(self):
        """The cache_warmup.py file should contain the CacheWarmer class."""
        stdout, _, rc = run_git("show", "feature/cache:src/cache_warmup.py")
        assert rc == 0
        assert "class CacheWarmer" in stdout, "CacheWarmer class not found in cache_warmup.py"
        assert "def warmup(self" in stdout, "warmup method not found"
        assert "def register_key(self" in stdout, "register_key method not found"
        assert "def schedule_warmup(self" in stdout, "schedule_warmup method not found"

    def test_cache_has_get_or_set(self):
        """The recovered stash should have added get_or_set to cache.py."""
        stdout, _, rc = run_git("show", "feature/cache:src/cache.py")
        assert rc == 0
        assert "get_or_set" in stdout, (
            "get_or_set method not found in cache.py on feature/cache"
        )

    def test_stash_commit_message(self):
        """There should be a commit on feature/cache about the recovered stash."""
        stdout, _, _ = run_git("log", "--oneline", "feature/cache")
        # Check that a commit mentioning the stash/warmup/recovery exists
        lines = stdout.strip().split("\n")
        found = any(
            "stash" in line.lower() or "warmup" in line.lower() or "recover" in line.lower()
            for line in lines
        )
        assert found, (
            f"No commit about stash recovery found on feature/cache. "
            f"Commits: {stdout}"
        )


# ============================================================
# Test 3: Feature files exist on main
# ============================================================
class TestFeatureFilesOnMain:
    def test_auth_py_on_main(self):
        content = read_file("src/auth.py")
        assert "class AuthManager" in content, "AuthManager class not found in src/auth.py"
        assert "def authenticate" in content
        assert "def create_user" in content

    def test_middleware_py_on_main(self):
        content = read_file("src/middleware.py")
        assert "class AuthMiddleware" in content, "AuthMiddleware not found"

    def test_cache_py_on_main(self):
        content = read_file("src/cache.py")
        assert "class LRUCache" in content, "LRUCache class not found"
        assert "get_or_set" in content, "get_or_set method not in cache.py on main"

    def test_cache_warmup_py_on_main(self):
        content = read_file("src/cache_warmup.py")
        assert "class CacheWarmer" in content, "CacheWarmer not found on main"

    def test_monitor_py_on_main(self):
        content = read_file("src/monitor.py")
        assert "class Monitor" in content, "Monitor class not found"
        assert "def record" in content
        assert "def get_average" in content

    def test_utils_has_monitoring_helpers(self):
        content = read_file("src/utils.py")
        assert "def timing_decorator" in content, "timing_decorator not in utils.py"
        assert "def health_check" in content, "health_check not in utils.py"
        # Also verify the original functions are still there
        assert "def parse_duration" in content, "parse_duration missing from utils.py"
        assert "def format_size" in content, "format_size missing from utils.py"
        assert "def retry" in content, "retry missing from utils.py"


# ============================================================
# Test 4: Merged app.py integrates all three systems
# ============================================================
class TestAppIntegration:
    def test_app_imports_auth(self):
        content = read_file("src/app.py")
        assert "AuthManager" in content, "AuthManager not imported in app.py"

    def test_app_imports_cache(self):
        content = read_file("src/app.py")
        assert "LRUCache" in content, "LRUCache not imported in app.py"

    def test_app_imports_monitor(self):
        content = read_file("src/app.py")
        assert "Monitor" in content, "Monitor not imported in app.py"

    def test_app_initializes_all_three(self):
        """The Application.__init__ should set up auth, cache, and monitor."""
        content = read_file("src/app.py")
        assert "self.auth" in content, "self.auth not initialized"
        assert "self.cache" in content, "self.cache not initialized"
        assert "self.monitor" in content, "self.monitor not initialized"

    def test_app_is_valid_python(self):
        """The merged app.py should be valid Python syntax."""
        content = read_file("src/app.py")
        try:
            compile(content, "app.py", "exec")
        except SyntaxError as e:
            assert False, f"app.py has syntax error: {e}"


# ============================================================
# Test 5: Merged config.py has all configuration sections
# ============================================================
class TestConfigIntegration:
    def test_config_has_base_settings(self):
        content = read_file("src/config.py")
        assert "DATABASE_URL" in content
        assert "DEBUG" in content
        assert "SECRET_KEY" in content

    def test_config_has_auth_settings(self):
        content = read_file("src/config.py")
        assert "SESSION_TIMEOUT" in content, "Auth config SESSION_TIMEOUT missing"
        assert "MAX_LOGIN_ATTEMPTS" in content, "Auth config MAX_LOGIN_ATTEMPTS missing"
        assert "PASSWORD_MIN_LENGTH" in content, "Auth config PASSWORD_MIN_LENGTH missing"

    def test_config_has_cache_settings(self):
        content = read_file("src/config.py")
        assert "CACHE_MAX_SIZE" in content, "Cache config CACHE_MAX_SIZE missing"
        assert "CACHE_DEFAULT_TTL" in content, "Cache config CACHE_DEFAULT_TTL missing"
        assert "CACHE_BACKEND" in content, "Cache config CACHE_BACKEND missing"

    def test_config_is_valid_python(self):
        content = read_file("src/config.py")
        try:
            compile(content, "config.py", "exec")
        except SyntaxError as e:
            assert False, f"config.py has syntax error: {e}"


# ============================================================
# Test 6: Git history structure
# ============================================================
class TestGitHistory:
    def test_main_has_merge_commits(self):
        """main branch should have merge commits integrating the features."""
        stdout, _, _ = run_git("log", "--oneline", "--merges", "main")
        merges = [line for line in stdout.strip().split("\n") if line]
        assert len(merges) >= 2, (
            f"Expected at least 2 merge commits on main, found {len(merges)}: {stdout}"
        )

    def test_feature_auth_is_ancestor_of_main(self):
        """feature/auth should be an ancestor of main (merged in)."""
        _, _, rc = run_git("merge-base", "--is-ancestor", "feature/auth", "main")
        assert rc == 0, "feature/auth is not an ancestor of main"

    def test_feature_cache_tip_is_ancestor_of_main(self):
        """The tip of feature/cache (with stash applied) should be ancestor of main."""
        _, _, rc = run_git("merge-base", "--is-ancestor", "feature/cache", "main")
        assert rc == 0, "feature/cache is not an ancestor of main"

    def test_feature_monitoring_is_ancestor_of_main(self):
        """feature/monitoring should be an ancestor of main."""
        _, _, rc = run_git("merge-base", "--is-ancestor", "feature/monitoring", "main")
        assert rc == 0, "feature/monitoring is not an ancestor of main"

    def test_no_conflict_markers_in_tracked_files(self):
        """No tracked files should contain unresolved merge conflict markers."""
        stdout, _, _ = run_git("ls-files")
        for filepath in stdout.strip().split("\n"):
            if not filepath:
                continue
            full_path = os.path.join(REPO_DIR, filepath)
            if os.path.isfile(full_path):
                try:
                    with open(full_path, "r") as f:
                        content = f.read()
                    assert "<<<<<<<" not in content, (
                        f"Conflict marker '<<<<<<' found in {filepath}"
                    )
                    assert ">>>>>>>" not in content, (
                        f"Conflict marker '>>>>>>>' found in {filepath}"
                    )
                except UnicodeDecodeError:
                    pass  # Skip binary files


# ============================================================
# Test 7: Tag verification
# ============================================================
class TestTag:
    def test_v2_tag_exists(self):
        stdout, _, rc = run_git("tag", "-l", "v2.0.0")
        assert "v2.0.0" in stdout, "v2.0.0 tag not found"

    def test_v2_tag_points_to_main(self):
        """The v2.0.0 tag should point to the current main HEAD."""
        tag_hash, _, _ = run_git("rev-parse", "v2.0.0")
        main_hash, _, _ = run_git("rev-parse", "main")
        assert tag_hash == main_hash, (
            f"v2.0.0 tag ({tag_hash}) does not point to main ({main_hash})"
        )


# ============================================================
# Test 8: Working tree is clean
# ============================================================
class TestCleanState:
    def test_working_tree_is_clean(self):
        """The working tree should be clean after the recovery."""
        stdout, _, _ = run_git("status", "--porcelain")
        # Allow the stash ref to be in any state, but working tree should be clean
        assert stdout.strip() == "", (
            f"Working tree is not clean: {stdout}"
        )

    def test_on_main_branch(self):
        """Should be on main branch after recovery."""
        stdout, _, _ = run_git("symbolic-ref", "--short", "HEAD")
        assert stdout == "main", f"Expected to be on main, but on {stdout}"
