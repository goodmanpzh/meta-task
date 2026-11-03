### Category: API Design and Contract

Tasks involving API specification, contract testing, schema evolution, API gateway implementation, and interface design best practices.

**The examples below are for inspiration only. Be creative and design your own unique task!**

**Task Pattern Ideas**:
- Build OpenAPI specification linters with scoring and best practice validation
- Implement API diff tools for breaking change detection
- Create mock server generators from API schemas
- Build API version migration tools (Swagger 2.0 to OpenAPI 3.x)
- Implement GraphQL Federation gateways with schema stitching
- Create gRPC/Protobuf contract evolution validators
- Build API changelog generators from spec diffs
- Implement request/response validation middleware
- Create API compatibility matrix generators
- Build schema coverage analysis tools
- Implement contract testing frameworks (consumer-driven)
- Create API documentation generators
- Build rate limiting and quota management systems
- Implement API versioning strategy validators
- Create GraphQL schema deprecation audit tools

**Skills & Tools** (tag suggestions for your task):
- Core: `api-design`, `openapi`, `graphql`, `grpc`, `rest`
- Protocols: `protobuf`, `json-schema`, `avro`, `thrift`
- Patterns: `contract-testing`, `schema-evolution`, `versioning`, `federation`
- Tools: `swagger`, `spectral`, `apollo`, `pact`, `buf`
- Concepts: `breaking-changes`, `backwards-compatibility`, `deprecation`

**Possible Input Data** (be creative with environment files!):
- OpenAPI/Swagger specification files (YAML/JSON)
- GraphQL SDL schemas
- Protobuf definition files (.proto)
- API request/response logs
- Consumer contract definitions
- API usage analytics data
- Schema version history
- Deprecation schedules
- Rate limit configurations
- API gateway routing rules

**Verification Approaches**:
- Schema validation passes (valid OpenAPI/GraphQL/Protobuf)
- Breaking changes correctly identified
- Generated mock data conforms to schema
- Migration preserves API behavior
- Contract tests pass between versions
- Documentation accuracy and completeness
- Rate limiting behaves correctly under load
- Version routing works as expected
- Deprecation warnings generated correctly

**Remember**: API design tasks should test understanding of backwards compatibility, semantic versioning, and the trade-offs in API evolution strategies!
