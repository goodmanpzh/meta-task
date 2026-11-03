For the `instruction.md` you generate, use a **structured technical request** style:

Write like a well-structured technical forum post or engineering request. Include context, environment details, what the user has tried so far, and what they need. The user has done some research and describes their situation clearly.

**Key principles**:
- **Start with the goal** — "Goal:", one-line summary
- **Context** — relevant setup, versions, file paths
- **Current state** — what exists, what's been tried
- **Expected outcome** — what the end result should look like
- **No solution** — describe the goal, don't explain how to achieve it

**Good examples**:

```
**Goal:** Build an invoice processing pipeline

I have raw transaction CSVs at `/app/data/transactions/` (about 50 files, each ~5000 rows). Need a pipeline that groups transactions by vendor, calculates subtotals with tax, and produces one invoice per vendor as JSON.

The data has inconsistent vendor name spellings that need normalizing. I tried writing something quick with pandas but the grouping logic got complicated.
```

```
**Goal:** Set up a gRPC key-value store

Need a working gRPC server in Python that implements Get, Put, Delete operations.

Environment:
- Python 3.11
- Need grpcio and grpcio-tools

The server should listen on port 50051 and store data in memory. I've never used gRPC in Python before so starting from scratch here.
```

```
**Goal**: Convert legacy Fortran simulation to Python

There's a numerical simulation at `/app/legacy/simulate.f90` that computes fluid flow through a pipe network. It works but nobody on the team reads Fortran anymore.

Need a Python 3 equivalent that produces the same numerical results (within 1e-6 tolerance). The Fortran code reads its config from `/app/legacy/pipe_network.dat`. I compiled and ran the original to get reference output for comparison.
```

```
**Goal:** Implement a custom memory allocator

Need to implement a simple memory allocator in C that provides `my_malloc()` and `my_free()` with a free list and first-fit strategy.

Requirements:
- Must handle allocations from 1 byte to 1MB
- Should coalesce adjacent free blocks
- Header file at `/app/allocator.h` already defines the interface

I need this for an embedded project where we can't use the standard allocator.
```

**Remember**: Structured and clear. Include enough context that the task is well-defined, but the agent still needs to explore the environment and figure out the implementation approach.
