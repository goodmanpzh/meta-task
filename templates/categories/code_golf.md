### Category: Code Golf and Constrained Programming

Tasks requiring implementation under extreme constraints: minimal code size, limited operations, polyglot programming, or creative problem-solving within strict limits.

**The examples below are for inspiration only. Be creative and design your own unique task!**

**Task Pattern Ideas**:
- Implement complex algorithms in minimal bytes (code golf challenges)
- Write programs that work in multiple languages simultaneously (polyglot: C+Python, Rust+C++)
- Implement neural network inference in tiny C programs (<5KB)
- Create graphics/animations under size constraints (demoscene style, path tracing)
- Implement functionality using only regex or SQL
- Write self-modifying or quine-like programs
- Obfuscated code challenges (IOCCC style)
- Implement compression where output must decompress with given decompressor
- Create executables under specific size limits
- Write programs without using certain language features
- Implement algorithms using only bitwise operations
- Create tiny compilers or interpreters

**Skills & Tools** (tag suggestions for your task):
- Core: `code-golf`, `optimization`, `constraints`, `creative-coding`, `polyglot`
- Techniques: `minification`, `compression`, `obfuscation`
- Languages: `c`, `python`, `perl`, `assembly`, `brainfuck`, `rust`
- Tools: `gzip`, `upx`, `strip`, `wc`

**Possible Input Data** (be creative with environment files!):
- Reference implementations (correct but large)
- Size measurement scripts
- Test cases for correctness verification
- Decompressor binaries (for compression golf)
- Multi-language test harnesses (for polyglot verification)
- Baseline programs to optimize/shrink
- Neural network weights to implement inference for
- Image/audio targets for tiny renderers
- Compression targets with size budgets

**Verification Approaches**:
- Verify code size under limit (`wc -c`, `gzip -c | wc -c`)
- Check program produces correct output
- Test polyglot works with multiple interpreters/compilers (gcc AND python)
- Verify no forbidden features/libraries used
- Performance benchmarks (speed still acceptable)
- Output matches reference implementation exactly
- Compressed size verification

**Remember**: Code golf tasks should have clear, measurable constraints. The challenge is achieving correctness while meeting strict limits. Provide baselines to beat and clear measurement methodology!
