### Category: Testing and Quality Assurance

Tasks involving test framework implementation, test automation, coverage analysis, regression testing, and software quality engineering.

**The examples below are for inspiration only. Be creative and design your own unique task!**

**Task Pattern Ideas**:
- Implement mutation testing frameworks to evaluate test suite quality
- Build property-based test generators with recursive strategies
- Create test coverage gap analysis tools with risk scoring
- Migrate test suites between frameworks (unittest to pytest, JUnit 4 to 5)
- Implement regression test selection and prioritization algorithms
- Build flaky test detection and isolation tools
- Create test data factories with constraint-based generation
- Implement test impact analysis for code changes
- Build deterministic test execution engines with seed management
- Create integration test harnesses for multi-stage data pipelines
- Implement API contract validation for breaking change detection
- Build benchmark regression detection pipelines
- Create test fixture dependency analyzers
- Implement numerical regression test frameworks with tolerance handling

**Skills & Tools** (tag suggestions for your task):
- Core: `testing`, `quality-assurance`, `test-automation`, `coverage`
- Frameworks: `pytest`, `unittest`, `jest`, `junit`, `hypothesis`
- Analysis: `mutation-testing`, `coverage-analysis`, `regression-detection`
- Concepts: `test-isolation`, `determinism`, `flaky-tests`, `property-based-testing`
- Tools: `coverage.py`, `mutmut`, `pytest-cov`, `gcov`, `lcov`

**Possible Input Data** (be creative with environment files!):
- Source code with existing test suites
- Coverage reports (JSON, XML, lcov format)
- Test execution logs with timing and results
- Complexity metrics (cyclomatic, cognitive)
- Git history for test impact analysis
- Test manifests with metadata (tags, priorities)
- Mutation test results and survival data
- Flaky test historical data
- Benchmark results over time
- API schemas for contract testing

**Verification Approaches**:
- All original tests still pass after migration
- Coverage metrics match expected values
- Mutation score improvements demonstrated
- No false positives in regression detection
- Deterministic execution produces identical results
- Test selection reduces execution time while maintaining coverage
- Generated test data satisfies all constraints
- Report formats match expected schema

**Remember**: Testing tasks should challenge understanding of test theory (coverage criteria, mutation operators, oracle problem) and practical test engineering skills!
