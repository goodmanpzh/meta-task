For the `instruction.md` you generate, use a **followup / mid-conversation** style:

Write as if the user is picking up from a previous conversation or context that they assume you already know about. They'll reference "that thing from before", "the project we started", or "remember when..." — but no prior conversation actually exists. The agent has to figure out what they're referring to by exploring the environment.

This is how real users talk when they come back to a project — they skip the setup, jump straight into updates or next steps, and assume shared context. The environment itself should contain enough clues (files, partial work, configs, documentation) for the agent to reconstruct what "before" means.

**Good examples**:

```
ok so I got the data ingestion part working from last time. now I need to add the transformation step — the raw CSVs in /app/data/raw/ need to be normalized and joined. check the schema notes I left in /app/docs/transform_spec.md
```

```
remember that parser we were building? I added a few more test cases in /app/tests/. the basic expressions work but it still can't handle nested function calls. can you finish the implementation?
```

```
hey, the prototype from yesterday is in /app/prototype/. it works for the simple case but we need it to scale to the full dataset (~2GB). same approach should work but there might be memory issues with the current implementation.
```

```
so I set up the database schema like we discussed — tables are in /app/schema.sql and I've loaded some sample data. next step is the API layer. we need GET/POST/DELETE for the main resources. flask app skeleton is at /app/api/app.py
```

```
update on the deployment thing: I got the Dockerfile working but the compose setup still needs the networking piece. the services need to talk to each other — web on port 8080, API on 3000, postgres on 5432. my partial docker-compose.yml is in /app/deploy/
```

```
that visualization script is producing output now but the charts need work. can you add proper axis labels, a legend, and export as both PNG and SVG? the script is at /app/viz/generate_charts.py and the data it reads is in /app/viz/results.json
```

**Remember**: The user acts like you've been working on this together. They give updates, mention partial progress, reference decisions that were "already made", or describe next steps to build on previous work. The environment should reflect this backstory — maybe there are partial implementations, schema files, documentation, or config files that tell the story of what happened "before". The agent must piece together the context from the environment, not from the instruction.
