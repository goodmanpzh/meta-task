For the `instruction.md` you generate, use a **multi-request / kitchen sink** style:

Write as if the user is dumping several related (or semi-related) things they need done in one go. Real users often batch up their asks — "while you're at it, also..." or "oh and one more thing". Some requests depend on each other, some don't. The agent needs to untangle them, figure out the right order, and handle each one.

The tone is someone who's been accumulating a mental list and is now offloading it all at once. It can be a numbered list, a rambling paragraph, or a mix. Some items might be quick, others substantial. The user might not realize some of their asks conflict or depend on each other.

**Good examples**:

```
I need a few things done with the data pipeline:
1. Write an ingestion script that reads the raw JSON files from /app/data/raw/ and loads them into SQLite
2. The schema should normalize the nested objects into separate tables with foreign keys
3. oh and also write a summary report script that queries the DB and produces daily aggregates as a CSV
```

```
hey can you set up the project properly? there's code scattered around /app/src/ but no build system. I need:
- a proper Makefile that compiles everything
- a test runner that discovers and runs the test_*.c files in /app/tests/
- while you're at it, the README needs updating — it still references the old directory structure
```

```
couple things:
- we need a CLI tool that wraps the library in /app/lib/ — should support `search`, `export`, and `stats` subcommands
- also can you add pagination to the search results? the dataset has like 50k entries
- and write a decent --help that actually explains the options
```

```
so for the deployment:
1. write a Dockerfile that builds the Go project in /app/src/ (multi-stage, final image should be small)
2. then a docker-compose.yml that runs the service + a postgres database + redis for caching
3. finally a seed script that populates the database with the test data from /app/testdata/
4. make sure the whole thing comes up with `docker-compose up` and the API responds on port 8080
```

```
The server is running but it needs a few improvements:
- add request logging middleware in JSON format
- implement rate limiting (100 requests per minute per IP)
- add a /metrics endpoint that returns request counts, latency percentiles, and error rates
- the current config is hardcoded, move it to a YAML config file
```

```
Quick list for the analysis project:
- implement the feature extraction pipeline (see /app/docs/features.md for the spec)
- train a basic model using the extracted features
- write a prediction script that loads the model and processes new data from stdin
```

**Remember**: Real users rarely ask for exactly one thing. Mix 2-4 requests of varying size and complexity. Some might share context (same codebase, same server), others might be semi-related. The agent must identify all the asks, handle dependencies between them, and complete each one. Don't over-organize the requests — let them feel natural and slightly messy, like a real person thinking out loud.
