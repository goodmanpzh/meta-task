### Category: Git and Version Control

Tasks involving Git repository manipulation, version control operations, and Git internals.

**The examples below are for inspiration only. Be creative and design your own unique task!**

**Task Pattern Ideas**:
- Recover lost commits/branches from reflog or dangling objects
- Clean sensitive data from Git history completely (API keys, passwords)
- Configure Git hooks for automation (pre-commit, post-receive deployment)
- Resolve complex merge conflicts programmatically
- Set up Git servers with specific deployment behaviors (multi-branch to web)
- Migrate repositories while preserving history
- Implement custom Git workflows
- Merge branches from Git bundles with conflict resolution
- Configure multi-remote setups with specific push/pull behaviors

**Skills & Tools** (tag suggestions for your task):
- Core: `git`, `version-control`, `coding`
- Advanced: `git-internals`, `reflog`, `git-hooks`, `git-lfs`, `git-filter-branch`
- Related: `shell-scripting`, `automation`, `ci-cd`, `ssh`

**Possible Input Data** (be creative with environment files!):
- Git bundles (`.bundle`) for portable repository snapshots
- Bare repositories with corrupted or missing objects
- Repositories with intentional "disasters" (deleted branches, force-pushed history)
- Multi-remote setups with divergent histories
- Repositories with binary files and LFS issues
- Submodule/subtree configurations with version mismatches
- Pre-populated reflog with recovery scenarios
- Git hooks scripts (bash/python) needing fixes
- Repositories with sensitive data in history requiring cleanup
- SSH key configurations for server setups

**Verification Approaches**:
- Check file content and existence
- Verify Git history structure (`git log`, `git show`, `git rev-parse`)
- Ensure sensitive data is completely removed (`git fsck`, check all refs and reflog)
- Validate branch/tag states
- Test clone/push/pull functionality
- Verify file checksums match expected values

**Remember**: These are just starting points. Feel free to combine ideas, explore edge cases, or create entirely new challenges in the Git domain!
