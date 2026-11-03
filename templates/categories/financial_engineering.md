### Category: Financial Engineering and Fintech

Tasks involving financial systems, payment processing, settlement systems, risk management, and fintech applications.

**The examples below are for inspiration only. Be creative and design your own unique task!**

**Task Pattern Ideas**:
- Payment settlement and clearing systems
- Financial data reconciliation across multiple sources
- Risk scoring and assessment pipelines
- Invoice processing and validation
- High-precision financial calculations (avoiding floating-point errors)
- Transaction audit trails and compliance
- Currency conversion and exchange rate handling
- Financial report generation
- Order management systems
- Digital currency/CBDC system components
- Anti-fraud detection logic
- Portfolio calculations and rebalancing

**Skills & Tools** (tag suggestions for your task):
- Core: `financial`, `fintech`, `payment`, `settlement`
- Concepts: `high-precision`, `reconciliation`, `audit`, `compliance`
- Libraries: `decimal`, `pandas`, `numpy`
- Formats: `json`, `csv`, `excel`, `xml`
- Related: `cryptography`, `hmac`, `digital-signature`

**Possible Input Data** (be creative with environment files!):
- Transaction logs (JSONL, CSV)
- Bank statement files
- Exchange rate tables
- Invoice documents (PDF, structured data)
- Settlement batch files
- Audit trail logs
- Configuration files for financial rules
- Reference data (account mappings, currency codes)
- Encrypted financial payloads

**Verification Approaches**:
- Exact decimal precision matching
- Reconciliation totals balance check
- Audit hash verification
- Compliance rule validation
- Transaction integrity checks
- Report format and content verification
- Idempotency testing (same input produces same output)

**Remember**: Financial tasks require extreme precision and attention to edge cases. Use Decimal types, handle timezone conversions carefully, and ensure audit trails are complete!
