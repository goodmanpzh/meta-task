### Category: Multi-Component System Orchestration

Tasks where the agent must configure, connect, and coordinate multiple interacting components (services, databases, config files, scripts) that depend on each other. The agent must discover the dependency graph, plan the correct order of operations, and propagate information between components. These tasks test planning ability, dependency reasoning, and systematic execution across a complex environment.

**The examples below are for inspiration only. Be creative and design your own unique task!**

**Task Pattern Ideas**:

*Service Wiring & Configuration:*
- Given 3-5 pre-installed services (database, cache, backend, worker, scheduler), configure them to work together by discovering and setting connection strings, ports, credentials, and shared secrets
- A system where each component's config references outputs of other components (DB creates a user → backend needs those credentials → worker needs the backend URL → scheduler needs the worker queue name)
- Fix a broken multi-service setup where several configurations are wrong or missing — but the agent must figure out the dependency order to debug effectively
- Set up a data pipeline: ingestion script → processing service → database → reporting script, where each stage's output format must match the next stage's input

*Ordered Multi-Step Operations:*
- A database migration that requires: backup first → schema change → data transformation → index rebuild → verification, where each step depends on the previous
- Deploy an application stack: generate certificates → configure database → run migrations → start backend → configure reverse proxy → verify end-to-end
- Set up a build toolchain: install compiler → configure cross-compilation target → build libraries in dependency order → link final binary → run tests
- Configure a monitoring stack: set up metrics collector → configure alerting rules based on service endpoints → create dashboard data sources → verify alerts fire correctly

*Resource Planning & Allocation:*
- Given a set of tasks with dependencies, deadlines, and resource constraints, create an execution plan and carry it out (create files, run scripts, verify outputs)
- Manage a simulated batch processing system: read job definitions → resolve dependencies → execute in correct order → handle failures and retries → produce final report
- Configure storage and caching layers: allocate disk quotas → set up backup schedules → configure retention policies → verify space usage stays within limits

*Integration & Glue Code:*
- Connect systems that use different data formats: one produces XML, another expects JSON, a third uses CSV — write the glue scripts and configure the pipeline
- Set up authentication across services: generate shared keys → distribute to services → configure each service's auth settings → verify cross-service calls work
- Wire up event-driven workflows: configure event producers → set up routing rules → configure consumers → verify end-to-end event flow with test events

**Skills & Tools** (tag suggestions for your task):
- Core: `orchestration`, `configuration`, `multi-component`, `dependency-resolution`, `planning`
- Services: `database`, `redis`, `nginx`, `supervisor`, `cron`, `systemd`
- Config: `yaml`, `json`, `toml`, `ini`, `env-files`, `templates`
- Tools: `python`, `bash`, `curl`, `netcat`, `sqlite3`, `openssl`
- Concepts: `dependency-graph`, `service-discovery`, `health-check`, `connection-string`, `credential-management`
- Related: `devops`, `pipeline`, `automation`, `integration`

**Possible Input Data** (be creative with environment files!):
- Pre-installed services with default (broken or incomplete) configurations
- Configuration templates with placeholder variables that need to be filled
- Documentation files describing each component's expected inputs and outputs
- Database schemas that need to be initialized before services can start
- SSL certificates or keys that need to be generated and distributed
- Scripts that need to be run in a specific order
- Service definition files (supervisor, systemd units, cron entries)
- Environment variable files that need to be populated
- Health check scripts that verify each component
- Dependency specification files (which component needs what)
- Seed data files that must be loaded into specific databases
- Log directories where services write output (useful for debugging)

**Verification Approaches**:
- End-to-end functional test (send request through the full pipeline, verify output)
- Each component health check passes independently
- Data flows correctly between components (test data in → expected output out)
- Configuration files contain correct values (connection strings, ports, credentials match)
- Services are running and responding on expected ports
- Dependency ordering is respected (no component started before its dependencies)
- Integration test: trigger a workflow and verify all stages complete correctly

**Remember**: The key differentiator is that no single component is particularly hard — the challenge is in understanding how they fit together. The agent must explore each component to understand what it needs, plan the correct order, and propagate information (ports, credentials, paths) between them correctly. Include enough components (3-5) that the agent must maintain a mental model of the whole system. Do NOT enumerate the exact steps in the instruction — describe the desired end state and let the agent figure out how to get there.
