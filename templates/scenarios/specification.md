For the `instruction.md` you generate, use a **technical specification** style:

Write precise, direct requirements without background stories. State exactly what needs to be done, with specific formats, constraints, and numbers embedded naturally in sentences. Can include code snippets showing expected interfaces or output formats.

**Key principles**:
- **Direct statement of requirements** — no stories or emotional context
- **Precise formats** — specify exact file formats, field names, types when needed
- **Embedded constraints** — weave limits ("must", "cannot", "under X", "at least Y") into prose naturally
- **Code snippets when helpful** — show expected interface or output format

**Good examples**:

```
Implement the `process_records` function in /app/processor.py. It receives a list of dicts with keys "id" (int), "value" (float), and "timestamp" (ISO 8601 string). Return a dict mapping each unique id to its average value. Handle empty input by returning {}.
```

```
Write a Python script at /app/compress.py that compresses the image at /app/input.png to under 50KB while maintaining at least 0.95 SSIM similarity. Your solution must not use any external libraries beyond PIL and numpy.
```

```
Parse the binary file at /app/data.bin which contains a header (4-byte magic "DATA", 4-byte little-endian record count) followed by records (8-byte double, 4-byte int32 each). Write the sum of all doubles to /app/result.txt as a decimal with 6 decimal places.
```

```
I need you to implement a sorting algorithm in /app/sort.c that can handle 10 million integers in under 2 seconds. You cannot use the standard library qsort - write it from scratch. The input is in /app/numbers.bin (binary format, 4 bytes per int).
```

```
The CSV at /app/input.csv has columns: user_id, action, timestamp. Generate /app/output.json containing an array of objects with user_id and action_count (number of actions per user), sorted by action_count descending.
```

**Remember**: Be precise about formats and constraints but don't over-structure. Technical accuracy in natural prose, not a bulleted checklist.
