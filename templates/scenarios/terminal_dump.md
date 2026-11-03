For the `instruction.md` you generate, use a **raw terminal output / terse dump** style:

The user pastes terminal output, data samples, or file contents as the main content, with minimal commentary. The agent must figure out the goal from the context. Vary the amount of user commentary — from zero explanation (just pasted output) to a few sentences.

**Good examples** (minimal commentary):

```
$ cat /app/data/sensor_readings.csv | head -5
timestamp,device_id,temp,humidity,pressure
2024-01-15T08:00:00Z,dev-001,22.4,45.2,1013.2
2024-01-15T08:00:00Z,dev-002,,48.1,1013.1
2024-01-15T08:01:00Z,dev-001,22.5,ERROR,1013.3
2024-01-15T08:01:00Z,dev-003,19.8,52.0,

need to clean this up and produce hourly averages per device
```

```
$ file /app/binary/firmware.bin
/app/binary/firmware.bin: data

$ xxd /app/binary/firmware.bin | head -10
00000000: 7f45 4c46 0101 0100 0000 0000 0000 0000  .ELF............
00000010: 0200 2800 0100 0000 0d02 0100 3400 0000  ..(.........4...

extract the string table and list all function names
```

```
$ python3 /app/benchmark.py
matrix_multiply: 4.23s (1000x1000)
fft_compute: 2.81s (n=1048576)
sort_large: 1.92s (n=5000000)

make these faster. target: each under 1 second
```

**Good examples** (with user's brief description):

```
I've got this dataset at /app/data/genome.fasta — about 50,000 sequences.

$ head -4 /app/data/genome.fasta
>seq_0001 length=342 organism=E.coli
ATGCGATCGATCGATCG...
>seq_0002 length=891 organism=S.aureus
GCTAGCTAGCTAGCTAG...

Need to cluster sequences by similarity (>90% identity) and pick one representative per cluster.
```

```
Here's what the API currently returns:

$ curl localhost:8080/api/users
{"users": [{"id": 1, "name": "alice"}, {"id": 2, "name": "bob"}]}

I need a new endpoint `/api/users/stats` that returns aggregated user activity metrics. The raw activity logs are in `/app/data/activity.jsonl`. The server code is at `/app/server.py`.
```

```
$ tree /app/project/
/app/project/
├── Makefile
├── src/
│   ├── main.c
│   ├── parser.c
│   └── codegen.c
├── include/
│   └── ast.h
└── tests/
    └── input.txt

compile and run this. it's a small compiler — feed it tests/input.txt and see what comes out
```

**Remember**: The pasted output or data IS the instruction context. The user shows what they have and briefly states what they want. The agent must understand the data/output and figure out how to achieve the goal.
