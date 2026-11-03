For the `instruction.md` you generate, use an **ultra-minimal** style:

**Key principles**:
- **1-3 sentences only** - State the goal directly, nothing more
- **No headers or sections** - Just plain text paragraphs
- **No bullet points** - Write as natural prose
- **Implied constraints** - Embed constraints naturally in the text, don't list them separately

**Good examples**:

```
You need to create a file called "/app/solution.txt" with the word found in "secret_file.txt" in the "secrets.7z" archive.
```

```
I have provided a file called text.gcode. This is a gcode file for a Prusa MK4s. I'm trying to print some text onto an existing object. When I run the print, what will the text show? Write the output to /app/out.txt
```

```
Complete the implementation in find_dominant_eigenvalue_and_eigenvector in /app/eigen.py. The input is a 2D square numpy array with real np.float64 entries, up to size 10x10. Optimize the function such that it consistently runs faster than the reference numpy solution in /app/eval.py.
```

**Remember**: The shorter, the better. Aim for under 50 words total.
