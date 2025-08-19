# add-source-to-vault

Automatically add academic sources to your Obsidian vault with structured organization and metadata extraction.

## Overview

This package takes a DOI and automatically downloads, processes, and organizes academic papers into your Obsidian vault with a standardized folder structure. It handles PDF downloads, OCR text extraction, metadata generation, and bibliography creation.

## Features

- **PDF Download**: Uses the `pdf-from-doi` package to fetch open-access PDFs
- **Smart Organization**: Creates a structured folder hierarchy in your vault
- **Smart Text Extraction**: Uses PyMuPDF4LLM to extract clean markdown from PDFs
- **Metadata Extraction**: Fetches metadata from CrossRef and arXiv APIs
- **Bibliography Generation**: Creates BibTeX entries for citations
- **Duplicate Prevention**: Checks for existing sources before processing
- **Future-Ready**: Designed to support website links in addition to DOIs

## Folder Structure

When you add a source, it creates the following structure in your vault:

```
vault/
└── sources/
    ├── pdfs/           # Original PDF files
    ├── raw/            # OCR-extracted raw text
    ├── md/             # Structured metadata (markdown)
    └── bib/            # BibTeX citation files
```

Each file is named using the paper title for easy identification.

## Usage

### Basic Usage

```python
from add_source_to_vault import SourceManager

# Initialize with your vault path
manager = SourceManager(vault_path="/path/to/your/obsidian/vault")

# Add a source by DOI
manager.add_source("10.48550/arXiv.1706.03762")
```

### Command Line Interface

```bash
# Add a source to your vault
add-source-to-vault --vault /path/to/vault --doi "10.48550/arXiv.1706.03762"

# Or use environment variable for vault path
export OBSIDIAN_VAULT_PATH="/path/to/vault"
add-source-to-vault --doi "10.48550/arXiv.1706.03762"
```

## Installation

```bash
uv add add-source-to-vault
```

## Dependencies

- `pdf-from-doi`: For downloading academic PDFs
- `pymupdf4llm`: For clean markdown extraction from PDFs
- `requests`: For metadata fetching
- `bibtexparser`: For BibTeX generation

## File Naming Convention

Files are named using the paper title, sanitized for filesystem compatibility:

- `paper-title.pdf` (in sources/pdfs/)
- `paper-title.txt` (in sources/raw/)
- `paper-title.md` (in sources/md/)
- `paper-title.bib` (in sources/bib/)

## Metadata Structure

The markdown metadata files include:

- Title, authors, journal, publication date
- Abstract
- DOI and URLs
- Keywords/tags
- Citation count (if available)
- Links to related files (PDF, raw text, BibTeX)

## Roadmap

- [ ] Support for website URLs (not just DOIs)
- [ ] Integration with popular citation databases
- [ ] Automatic tag generation based on content
- [ ] Support for different vault structures
- [ ] Batch processing capabilities

## Contributing

This package is part of the FasterScienceAI project. Contributions welcome!
