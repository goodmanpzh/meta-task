### Category: Message Queue and Async Processing

Tasks involving message queue systems, asynchronous task processing, event-driven architectures, and pub/sub patterns.

**The examples below are for inspiration only. Be creative and design your own unique task!**

**Task Pattern Ideas**:
- RabbitMQ exchange and binding configuration
- Redis pub/sub and stream processing
- Celery task queue debugging and optimization
- Dead letter queue handling
- Message serialization and deserialization
- Consumer group management
- Message retry and backoff strategies
- Queue priority and routing
- Async task cancellation and cleanup
- Message ordering and deduplication
- Rate limiting in message processing
- Batch message processing optimization
- Event sourcing patterns

**Skills & Tools** (tag suggestions for your task):
- Core: `message-queue`, `async`, `pub-sub`, `event-driven`
- Systems: `rabbitmq`, `redis`, `celery`, `kafka-concepts`
- Protocols: `amqp`, `mqtt`
- Concepts: `exchange`, `binding`, `dead-letter`, `consumer-group`
- Languages: `python`, `javascript`, `go`

**Possible Input Data** (be creative with environment files!):
- RabbitMQ configuration files
- Redis configuration and initial data
- Celery task definitions with bugs
- Message payload samples (JSON, binary)
- Queue topology definitions
- Consumer application code
- Producer scripts
- Routing key configurations
- Dead letter queue contents
- Message schemas

**Verification Approaches**:
- Message delivery confirmation
- Queue depth and consumer lag checks
- Dead letter queue is empty (all processed)
- Message ordering verification
- Consumer acknowledgment correctness
- Retry behavior validation
- Performance benchmarks (throughput, latency)
- No message loss verification

**Remember**: Message queue tasks should test understanding of async patterns, failure handling, and message guarantees. Include scenarios with message failures, retries, and ordering requirements!
