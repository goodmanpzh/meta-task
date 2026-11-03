# Help! Our Git Repository Is Broken After a Server Crash

Our build server crashed and now our project repository at `/app/project` is in a really bad state. I've been trying to piece things together but I keep hitting errors.

First, when I try `git stash list` in the repo, I get:

```
fatal: bad object refs/stash
```

I know my coworker Bob had stashed some work-in-progress on the caching feature before the crash. The stash ref exists in `.git/refs/stash` and points to some hash, but git can't find the object. I noticed there's a `.git/lost-found/other/` directory with some git objects in it — I think they might be backup copies of the missing objects, but I don't know how to make git recognize them.

Second, we had three feature branches that were being developed in parallel, but they're all gone from the repo. Luckily, the team members had created git bundle files before the crash:

- `/app/bundles/auth-feature.bundle`
- `/app/bundles/cache-feature.bundle`
- `/app/bundles/monitoring-feature.bundle`

But when I try to import them, I get errors like:

```
error: some prerequisite commits exist in the object store, but are not connected to the repository's history
```

I can't figure out why — the `main` branch seems intact and these bundles were supposedly created relative to `main`.

There's also a `RECOVERY_LOG.txt` in the project root with some notes about what happened.

## What I need

1. **Restore all three feature branches** from the bundle files so they exist as local branches (`feature/auth`, `feature/cache`, `feature/monitoring`)

2. **Recover Bob's stash** — the stash contained work-in-progress additions to the caching system (a new file and modifications to an existing one). Those changes need to be committed on the `feature/cache` branch with the message `"Apply recovered stash: cache warmup and get_or_set"`

3. **Merge all three feature branches into `main`** — the final `main` branch should integrate all the features:
   - The authentication system from `feature/auth` (files: `src/auth.py`, `src/middleware.py`)
   - The caching system from `feature/cache` including the recovered stash (files: `src/cache.py`, `src/cache_warmup.py`)
   - The monitoring system from `feature/monitoring` (files: `src/monitor.py`)
   - The merged `src/app.py` must import and initialize ALL three systems (AuthManager, LRUCache, and Monitor)
   - The merged `src/config.py` must include configuration sections for Auth and Cache (both feature branches modified it with their own settings)
   - The merged `src/utils.py` should include the monitoring helper functions (`timing_decorator` and `health_check`)

4. **Tag the final merge commit** on `main` as `v2.0.0` (a lightweight tag is fine)

When it's all done, `git log --oneline --graph main` should show a history with merge commits integrating all three branches, and `git tag` should list `v2.0.0`.
