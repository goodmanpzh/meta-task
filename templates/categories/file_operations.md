### Category: File Operations and Data Recovery

Tasks involving processing special file formats, extracting data from binary files, recovering corrupted data, and large-scale text manipulation.

**The examples below are for inspiration only. Be creative and design your own unique task!**

**Task Pattern Ideas**:
- Parse and extract data from binary files (ELF sections, PE headers, custom formats)
- Recover data from corrupted or truncated databases (SQLite, WAL recovery)
- Process special file formats (G-code, CAD files, proprietary formats)
- Large-scale text processing with efficient tools (Vim macros for million-line files)
- Extract information from multimedia files (video frame extraction, audio parsing)
- Convert between file formats with specific requirements
- Reverse engineer file formats to extract hidden data
- Implement compression/decompression algorithms
- Parse LaTeX documents and fix formatting issues

**Skills & Tools** (tag suggestions for your task):
- Core: `file-operations`, `coding`, `data-processing`
- Tools: `binwalk`, `hexdump`, `ffmpeg`, `imagemagick`, `readelf`
- Text: `vim`, `vim-macros`, `sed`, `awk`
- Formats: `binary`, `database`, `multimedia`, `archives`

**Possible Input Data** (be creative with environment files!):
- Binary executables (ELF, PE, Mach-O with embedded data to extract)
- Database files (SQLite with WAL, corrupted/truncated databases)
- 3D printing files (G-code with hidden text, STL, OBJ)
- Image files (PNG, JPEG, PPM, BMP with metadata)
- Video/Audio (MP4 requiring frame extraction, WAV requiring transcription)
- Document formats (PDF, DOCX, LaTeX with formatting issues)
- Large text files (CSV with millions of rows for batch editing)
- Archive formats (custom archives, nested compression)
- Scientific formats (HDF5, NetCDF, FITS)
- Compression format specifications (implement matching compressor for given decompressor)

**Verification Approaches**:
- Check extracted data matches expected format and values (JSON output)
- Verify recovered data completeness (row counts, checksums)
- Compare output files byte-for-byte with expected results
- Validate LaTeX compiles without warnings
- Test decompression/compression round-trip

**Remember**: These are just starting points. Create challenges that test file format understanding, data recovery skills, and efficient processing techniques!
