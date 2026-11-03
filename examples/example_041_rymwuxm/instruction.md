# Broken Data Processing Pipeline

I set up a data processing pipeline using `supervisord` to manage three services: a job queue server, a worker process, and an aggregator. It was all working a week ago, but my colleague made some changes and now nothing runs properly. I can't reach him and I need this fixed urgently.

When I try to start the pipeline with:

```
supervisord -c /etc/supervisor/supervisord.conf
```

And then check the status:

```
supervisorctl status
```

I get errors for every service. The queue server won't start, the worker crashes, and the aggregator times out with no results.

Looking at the logs in `/app/logs/`, I see different errors for each service but I can't make sense of them. The queue server log mentions something about binding, the worker log has permission errors and "too many open files" messages before it dies, and the aggregator just says it can't find any results.

Here's what the pipeline is supposed to do:
1. The **queue server** (`/app/queue_server.py`) loads job files from `/app/data/queue/` and serves them to workers via TCP
2. The **worker** (`/app/worker.py`) pulls jobs from the queue, processes them (statistical computations, transforms, hashing), and writes results to `/app/data/results/`
3. The **aggregator** (`/app/aggregator.py`) collects all results, combines them into a summary, and writes the final output

The supervisord configuration is at `/etc/supervisor/conf.d/pipeline.conf`.

There are 20 job files in `/app/data/queue/` that all need to be processed. When the pipeline is working correctly, the final aggregated output should be written to `/app/output/results.json` and contain all 20 processed job results.

I need all three services to run successfully through supervisord, process all 20 jobs, and produce the final output at `/app/output/results.json`. The output should be a JSON file with a `total_jobs` field equal to 20 and should not be marked as `partial`.

I'm pretty sure the Python scripts themselves are mostly fine - the problems are in the supervisord configuration and how things are wired together. Though I did notice the worker seems to crash with "too many open files" even though there are only 20 jobs - maybe there's a resource issue too?

Please fix whatever is broken and make sure the pipeline completes successfully.
