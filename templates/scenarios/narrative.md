For the `instruction.md` you generate, use a **scenario-based narrative** style:

**Key principles**:
- **Tell a story** - Set up a realistic workplace situation
- **Use characters** - "Your colleague Marcus", "The intern", "Sarah from the ops team"
- **Explain the situation** - What's happening and what needs to be done
- **Natural flow** - Don't use formal sections, write as connected paragraphs
- **Embedded requirements** - Weave technical details into the narrative

**Good examples**:

```
Your team's lead developer, Marcus, was working on a critical feature branch called `feature/payment-gateway` in the repository at `/app/repo`. The branch contained a series of commits implementing a new payment processing module.

Last Friday, an overzealous intern ran a cleanup script that deleted several branches and aggressively garbage-collected the repository. Marcus is on vacation with no laptop, and the payment gateway feature must ship by Monday. The intern's script deleted the branch reference and expired most of the reflog, but thankfully didn't run a full `git gc --aggressive` — so the commit objects should still be floating around as dangling objects.

You need to recover Marcus's commits (they all have messages starting with `payment:`), reconstruct the branch, and merge it into main. There will be conflicts in `config.yaml` and `src/routes.py` with Sofia's recent changes — resolve them by keeping both sets of changes.
```

```
The data science team has been collecting sensor readings from 200 IoT devices across three warehouses. The raw data lives in `/app/data/sensors/` — one Parquet file per day, going back 90 days. Lisa from the analytics team needs a consolidated dashboard-ready dataset by the end of the week.

The problem is that the devices use three different firmware versions, each with slightly different data schemas (some use Celsius, others Fahrenheit; timestamp formats vary; some devices report humidity as a percentage, others as a decimal). Nobody documented which devices run which firmware.

Your job: build a pipeline that normalizes all the data into a consistent schema, identifies and flags anomalous readings, and produces a clean daily-aggregated dataset that Lisa can plug into her dashboards.
```

```
Your company's DevOps engineer, Raj, started setting up a CI/CD pipeline before going on parental leave. He left notes in `/app/docs/ci_plan.md` and a partially configured setup in `/app/ci/`. The project is a Go microservice at `/app/service/` that needs to be built, tested, and packaged as a Docker image.

Raj got as far as writing the Dockerfile and a basic Makefile but didn't finish the test harness or the deployment script. Your task is to finish what Raj started: make the build work, add the missing test infrastructure, and write a deploy script that builds the image and tags it with the git commit hash.
```

**Remember**: Make it feel like a real workplace situation someone needs help with — building something new, finishing an incomplete project, setting up infrastructure, or processing data for a team. Not a formal specification, but a story with a clear deliverable.
