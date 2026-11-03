### Category: Data Processing and ETL

Tasks involving data transformation, cleaning, merging, and analysis of structured/unstructured data.

**The examples below are for inspiration only. Be creative and design your own unique task!**

**Task Pattern Ideas**:

*Data Transformation & Cleaning:*
- Clean and normalize messy real-world datasets
- Merge data from multiple sources with conflict resolution
- Parse and transform file formats (CSV, JSON, XML, Parquet)
- Schema migration and evolution
- Data resharding and compression pipelines

*Serialization & Encoding:*
- Binary protocol parsing and construction (custom formats, network protocols)
- Handle byte order issues (big-endian/little-endian conversion)
- Character encoding conversion and detection (UTF-8, Latin-1, shift-JIS)
- Base64/hex encoding and decoding with corruption handling
- Protobuf/Thrift/Avro message parsing without schema
- Compression format handling (gzip, zstd, lz4, brotli)
- Data checksum verification and repair (CRC, MD5, SHA)

*Log & Text Analysis:*
- Log analysis and pattern extraction (by date ranges, severity, patterns)
- Regex-based pattern extraction from logs or text
- Token counting and text statistics for NLP datasets
- Structured log parsing (JSON logs, logfmt, syslog)

*Document Processing:*
- Text extraction from documents (PDF, images, scanned documents via OCR)
- G-code or machine-readable file parsing
- ETL pipeline implementation
- Data validation and quality assurance

**Skills & Tools** (tag suggestions for your task):
- Core: `data-processing`, `coding`, `file-operations`, `etl`, `serialization`
- Tools: `pandas`, `jq`, `awk`, `sed`, `sqlite`, `regex`, `xxd`, `hexdump`
- Formats: `csv`, `json`, `parquet`, `xml`, `jsonl`, `log-analysis`, `protobuf`
- Encoding: `base64`, `iconv`, `chardet`, `binascii`
- Compression: `gzip`, `zstd`, `lz4`, `brotli`
- OCR: `tesseract`, `pytesseract`, `pdf-extraction`

**Possible Input Data** (be creative with environment files!):
- Multi-format data sources (JSON + CSV + Parquet) requiring merge
- Messy CSV files with inconsistent delimiters, mixed encodings
- JSONL streaming logs with nested structures
- Legacy data formats (COBOL copybook `.DAT`, fixed-width text)
- Parquet/Arrow files with complex nested schemas
- XML with namespaces (SOAP, RSS, scientific formats)
- Database exports (SQLite dumps, PostgreSQL `COPY` format)
- Log files with timestamps and severity levels
- Binary files with custom serialization formats
- Files with mixed encodings or BOM issues
- Compressed data with partial corruption
- Protocol buffer messages (with/without schema)
- Base64-encoded payloads with line breaks
- HTML files requiring content extraction
- G-code or machine-readable files
- PDF documents with tables (invoices, receipts, forms)
- HuggingFace datasets for NLP processing
- Financial data (SWIFT messages, FIX protocol logs)

**Verification Approaches**:
- Output file exact match (byte-level or content comparison)
- Check output has correct schema/columns
- Statistical validation (row counts, aggregates, checksums)
- Verify no missing values, correct data types
- Format correctness checks (valid JSON, well-formed CSV)
- Performance on large datasets

**Remember**: These are just starting points. Create realistic data challenges with messy real-world characteristics!
