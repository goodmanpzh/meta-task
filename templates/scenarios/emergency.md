For the `instruction.md` you generate, use an **urgent / time-pressure** style:

Write as if the task needs to be done urgently. Vary the urgency level — from a calm but firm deadline note to a stressed full-panic message. Include whatever info is needed to start working (paths, configs), but the tone should convey time pressure. The task itself can be building, deploying, configuring, analyzing — anything that has a deadline.

**Vary the urgency:**
- **Calm but firm**: Brief, factual, like a Slack handoff note. Under 500 characters.
- **Stressed**: Short sentences, some frustration, "we needed this yesterday"
- **Full panic**: ALL CAPS, exclamation marks, fragmented, typing fast under pressure

**Good examples** (calm but firm):

```
Demo for the investor meeting is tomorrow at 9am. Need a working dashboard that reads from the SQLite database at /app/data/metrics.db and displays the key charts.

Stack: Python + Flask or Streamlit, whatever's fastest. The database has tables: revenue, users, churn_rate. Dashboard should show monthly trends for each.

Output: a runnable script at /app/dashboard.py that serves on port 8080.
```

```
Client needs the data export by end of day. Raw data is in /app/data/warehouse/ (Parquet files, ~200 tables). They want a single consolidated CSV with all customer transactions from Q4, with columns: customer_id, date, amount, category.

Filter: only transactions > $100. Sort by date descending. Output to /app/output/q4_export.csv.
```

**Good examples** (full panic):

```
THE CONFERENCE TALK IS IN 2 HOURS and the demo environment isn't set up!! I need the ML pipeline running end to end:

1. Load the model from /app/models/classifier.pkl
2. Set up a REST API that accepts image uploads and returns predictions
3. It needs to actually work when I curl it on stage

Server code goes in /app/demo_server.py, must run on port 5000. PLEASE just make it work I don't care if it's pretty
```

```
MIGRATING SERVERS TONIGHT and the new config isn't ready. Need to:
- Convert the old Apache config at /app/old/httpd.conf to Nginx format
- Set up SSL with the certs in /app/certs/
- Configure reverse proxy to forward /api/* to localhost:3000
- Write the config to /app/nginx/nginx.conf

The old server goes offline at midnight. This HAS to be ready.
```

**Remember**: Key technical details (paths, service names, requirements) should be present but may be scattered among urgency. The task is real work that needs doing fast — building, configuring, converting, deploying — not necessarily something broken.
