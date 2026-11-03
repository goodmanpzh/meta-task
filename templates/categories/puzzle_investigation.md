### Category: Puzzle Investigation and Cross-Source Reasoning

Tasks where the problem itself is not fully stated upfront. The agent must explore the environment, discover scattered clues across multiple files and data sources, correlate evidence, and piece together a complete picture before producing the final answer. These tasks test exploration ability, cross-referencing skills, and long-context reasoning.

**The examples below are for inspiration only. Be creative and design your own unique task!**

**Task Pattern Ideas**:

*Data Detective / Information Forensics:*
- Given 5-10 files in different formats (SQLite DB, JSON configs, CSV logs, text notes, binary dumps), figure out what happened and produce a structured report
- Reconstruct a timeline of events from fragments scattered across log files, database records, and configuration change history
- Determine which user/process caused a specific outcome by cross-referencing access logs, process lists, and file modification timestamps
- Find the root cause of a data inconsistency by tracing values through a multi-stage transformation pipeline (each stage in a different file)

*Hidden Relationship Discovery:*
- Multiple datasets reference each other via different ID schemes (user_id vs email vs employee_number); discover the mapping and join them
- A system has multiple configuration layers (defaults, overrides, environment-specific); trace how a specific setting gets its final value
- Given partial database exports from different time periods, reconstruct what changed and why
- Discover undocumented dependencies between components by analyzing import graphs, config references, and runtime logs

*Puzzle / Challenge Style:*
- An environment contains encrypted, encoded, or obfuscated data; each piece reveals a clue needed to decode the next
- A multi-step scavenger hunt where solving one file reveals the path or key to the next
- A "broken system" where multiple independent issues interact — the agent must find and fix all of them, but fixing one may reveal or change others
- Given a codebase with intentionally planted inconsistencies, find all of them and explain the pattern

*Audit & Compliance:*
- Audit a system against a set of rules (given in one file) by checking multiple data sources and report all violations
- Verify data integrity across a primary database and multiple backup/replica files, reporting discrepancies with evidence
- Cross-reference financial records, inventory logs, and transaction histories to identify anomalies

*Web Research & Information Retrieval:*
- Look up a specific fact from an online leaderboard, documentation page, or public API (e.g., find the top-ranked model on a benchmark leaderboard as of a specific date)
- Query public REST APIs (PyPI, npm, GitHub, HuggingFace, PDB) to find packages, models, or datasets matching specific criteria
- Retrieve and cross-reference information from multiple online sources to answer a factual question
- Find the correct version, author, or configuration of a tool/library by consulting its online documentation or release history
- Determine the current status of a public service, standard, or specification by fetching and parsing its web page

**Skills & Tools** (tag suggestions for your task):
- Core: `investigation`, `exploration`, `cross-referencing`, `reasoning`, `data-correlation`
- Analysis: `timeline-reconstruction`, `anomaly-detection`, `pattern-matching`, `root-cause-analysis`
- Web research: `web-search`, `information-retrieval`, `api-querying`, `documentation-lookup`
- Tools: `sqlite3`, `jq`, `python`, `grep`, `find`, `diff`, `file`, `xxd`, `strings`, `curl`, `wget`
- Data: `json`, `csv`, `sqlite`, `log-analysis`, `binary-parsing`, `xml`, `html`
- Related: `forensics`, `audit`, `compliance`, `data-integrity`

**Possible Input Data** (be creative with environment files!):
- SQLite databases with multiple related tables
- JSON/YAML configuration files with cross-references
- CSV/TSV data files with partial overlap
- Application logs with timestamps and session IDs
- Binary files containing embedded metadata
- Text files with notes, comments, or documentation fragments
- Git repositories with meaningful commit history
- File system structures where directory layout itself is a clue
- Encoded or compressed intermediate files
- README or NOTES files with partial hints
- Multiple database dumps from different time periods
- Configuration files with include/import chains
- URL lists or API endpoint specifications for online research tasks
- Cached web pages or API response snapshots (for reproducible web research tasks)

**Verification Approaches**:
- Structured output file (JSON/CSV) with discovered facts, timeline, or report
- Specific answers to investigation questions (who, what, when, why)
- Completeness check — all clues/anomalies/violations found
- Correctness of cross-referenced relationships
- Timeline ordering accuracy
- Evidence citation (which file/record supports each finding)
- Exact string match for factual retrieval answers (model names, version numbers, specific values)

**Remember**: The key differentiator of this category is that the agent does NOT know what to do from the instruction alone. It must explore, discover, correlate, and reason. Plant information across many files — no single file should contain the complete answer. Include some red herrings and irrelevant data to test the agent's ability to filter noise. The instruction should describe the goal (e.g., "figure out what happened", "find all anomalies", "produce a reconciliation report") but NOT enumerate the steps or files to check. For web research tasks, the agent must use terminal tools (curl, wget, python requests) to access online resources — ensure the task has a deterministic answer that can be verified, and consider providing cached/snapshot data in the environment as a fallback for reproducibility.
