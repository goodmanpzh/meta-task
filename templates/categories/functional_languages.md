### Category: Functional Languages and Type Systems

Tasks involving functional programming languages, type theory, theorem provers, and language runtime implementations.

**The examples below are for inspiration only. Be creative and design your own unique task!**

**Task Pattern Ideas**:
- Fix garbage collector bugs in functional language runtimes (OCaml GC, Haskell RTS)
- Implement type checkers or type inference algorithms
- Write proofs in theorem provers (Coq, Lean, Agda, Isabelle)
- Build compilers or interpreters for functional languages
- Implement monadic parsers or combinators
- Fix runtime system issues (memory management, FFI bindings)
- Metacircular evaluators for Lisp/Scheme dialects
- Implement lazy evaluation or call-by-need semantics
- Pattern matching compilation and optimization
- Algebraic effects and handlers implementation
- Lambda calculus reduction strategies
- Implement persistent data structures

**Skills & Tools** (tag suggestions for your task):
- Core: `functional-programming`, `type-theory`, `compilers`
- Languages: `ocaml`, `haskell`, `coq`, `lean`, `scheme`, `racket`, `sml`, `f#`
- Concepts: `type-inference`, `garbage-collection`, `lambda-calculus`, `monads`
- Tools: `opam`, `cabal`, `stack`, `dune`, `coqc`

**Possible Input Data** (be creative with environment files!):
- OCaml/Haskell source code with runtime bugs
- Coq/Lean proof files with incomplete proofs
- Language grammar specifications (BNF, parser combinators)
- GC trace logs showing memory issues
- Type system specifications to implement
- Lambda calculus terms for reduction
- Test suites for language conformance
- FFI binding code with memory safety issues
- Scheme/Racket programs for metacircular evaluation

**Verification Approaches**:
- Proof verification (coqc compiles without errors)
- Runtime correctness (no segfaults, correct output)
- Memory safety (no leaks in GC tests)
- Type checker accepts/rejects correct programs
- Interpreter produces correct evaluation results
- Performance on benchmark programs

**Remember**: Functional programming tasks often require understanding of advanced type systems, memory management, and mathematical foundations. Create challenges that test theoretical understanding and practical implementation skills!
