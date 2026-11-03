### Category: Bioinformatics and Computational Biology

Tasks involving biological data processing, genomics, molecular modeling, synthetic biology design, protein engineering, drug discovery, and healthcare informatics.

**The examples below are for inspiration only. Be creative and design your own unique task!**

**Task Pattern Ideas**:

*Sequence Analysis & Genomics:*
- DNA/RNA sequence processing and compression
- Sequence alignment algorithms (pairwise, multiple sequence alignment)
- Gene expression data analysis and differential expression
- Variant calling and annotation from sequencing data
- Phylogenetic tree construction from sequence data
- Genome assembly from k-mer or read data

*Synthetic Biology & Cloning:*
- Design PCR primers for Golden Gate assembly with specific restriction enzymes (BsaI-HFv2, BsmBI)
- Design primers for site-directed mutagenesis (Q5 SDM kit, overlap extension PCR)
- Compute primer melting temperatures with primer3 oligotm under specific salt/concentration conditions
- Design gBlock gene fragments with codon optimization and GC content window constraints
- Plan multi-fragment assembly strategies (Gibson, Golden Gate, In-Fusion) for constructing target plasmids
- Verify restriction enzyme cut-site compatibility and design overhangs for one-pot assembly

*Protein Engineering & Structural Biology:*
- Design fusion proteins with specific domain arrangements (tags, linkers, functional domains)
- Select FRET donor/acceptor pairs matching filter cube specifications using fpbase API
- Identify molecule-binding proteins from PDB structure databases via SMILES-based ligand matching
- Identify antibody target proteins from heavy/light chain sequences
- Codon-optimize protein-coding DNA sequences with GC content constraints per sliding window
- Retrieve and process protein sequences from PDB REST API and UniProt

*Molecular Modeling & Drug Discovery:*
- SMILES molecular structure parsing and 3D conformation generation
- Protein structure prediction and analysis
- Drug-target interaction prediction
- Molecular property calculations (logP, MW, TPSA)
- Virtual screening and docking score analysis

*Medical & Healthcare Informatics:*
- Medical image processing (radiomics, histopathology cell segmentation)
- Healthcare data systems (appointment scheduling, patient records)
- Biostatistics and survival analysis
- Clinical trial data analysis
- Metabolic pathway analysis

**Skills & Tools** (tag suggestions for your task):
- Core: `bioinformatics`, `genomics`, `molecular-modeling`, `healthcare`, `biology`, `cloning`
- Synthetic biology: `primer-design`, `golden-gate`, `site-directed-mutagenesis`, `codon-optimization`, `gblock-design`
- Protein engineering: `fusion-protein`, `fret`, `fpbase`, `pdb`, `uniprot`, `antibody`
- Concepts: `sequence-analysis`, `structure-prediction`, `drug-discovery`, `proteins`
- Libraries: `biopython`, `rdkit`, `numpy`, `pandas`, `primer3-py`
- Tools: `primer3`, `oligotm`, `blastp`, `clustalw`, `muscle`
- Formats: `fasta`, `fastq`, `pdb`, `smiles`, `sdf`, `genbank`
- Related: `machine-learning`, `statistics`, `visualization`

**Possible Input Data** (be creative with environment files!):
- DNA/RNA sequences (FASTA format, circular or linear plasmid maps)
- GenBank annotated plasmid files (`.gb`) with feature annotations
- Molecular structures (SMILES strings, PDB files, SDF files)
- Protein sequence databases (subset PDB ID lists, UniProt entries)
- Antibody heavy/light chain sequences (FASTA)
- Restriction enzyme specifications (cut-site patterns, overhang rules)
- Gene expression matrices (CSV, TSV)
- Medical imaging data (DICOM metadata, histopathology slide annotations)
- Patient records (anonymized JSON)
- Drug compound databases
- Phylogenetic data files
- Clinical trial data
- Primer design specifications (target Tm ranges, salt concentrations, annealing constraints)

**Verification Approaches**:
- Primer melting temperature within specified range (validated via primer3 oligotm with exact flags)
- Primer annealing length within min/max bounds
- Correct restriction enzyme recognition sites in amplified fragments
- Assembly product sequence matches expected output plasmid
- GC content within specified window constraints across entire coding sequence
- Protein sequence matches PDB/UniProt reference for specified IDs
- FRET pair emission/excitation wavelengths match filter specifications exactly
- Codon table correctness (back-translate and verify amino acid sequence)
- Sequence alignment scores
- Molecular property calculations (within tolerance)
- Statistical test results (p-values, confidence intervals)
- Classification metrics (AUC, precision, recall)
- Structure validation (bond lengths, angles)
- Output format compliance (standard bioinformatics formats: FASTA, GenBank)

**Remember**: Bioinformatics tasks often involve domain-specific formats and algorithms. Synthetic biology tasks require understanding of real molecular biology workflows (cloning, PCR, enzyme digestion) — ensure biological validity and use appropriate tools (primer3, biopython, REST APIs for PDB/fpbase). Design tasks where verification can be deterministic: exact sequence matches, Tm within tolerance, correct restriction sites, valid assembly plans.
