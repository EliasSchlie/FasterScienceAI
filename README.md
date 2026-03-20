# FasterScienceAI

An AI agent that speeds up scientific discovery by automatically ingesting academic papers into a structured [Obsidian](https://obsidian.md) knowledge base.

Given a DOI, it downloads the paper, extracts text and metadata, and runs an LLM agent that breaks the paper into atomic proposition notes — each with supporting and contradicting arguments — and integrates them with your existing notes.

## How It Works

```
DOI
 └─► pdf-from-doi        — downloads open-access PDF (arXiv direct or Unpaywall; optional Bright Data proxy)
      └─► add-source-to-vault  — extracts text (PyMuPDF4LLM), fetches metadata (CrossRef/arXiv), writes PDF/raw/md/bib files
           └─► source-digestion-agent  — LangGraph ReAct agent that reads the paper and creates/updates Obsidian notes
```

The agent follows an atomic-notes methodology: every claim from the paper becomes a **Proposition** note (`p/`) with pro/con arguments. Shared concepts get **Concept** notes (`c/`). Existing notes are updated rather than duplicated.

## Packages

| Package | Description |
|---|---|
| `pdf-from-doi` | Downloads open-access PDFs by DOI. Tries arXiv direct first, then Unpaywall. |
| `add-source-to-vault` | Orchestrates download → OCR → metadata → vault file creation. |
| `source-digestion-agent` | LangGraph ReAct agent (OpenAI) that digests a source into atomic Obsidian notes. |

## Tech Stack

- **Python 3.13+**, managed with [uv](https://docs.astral.sh/uv/) (workspace monorepo)
- **LangGraph** + **LangChain** for the ReAct agent loop
- **OpenAI** models (default: `gpt-5-mini`)
- **PyMuPDF4LLM** for PDF → Markdown extraction
- **CrossRef / arXiv APIs** for metadata; **Unpaywall** for open-access PDF URLs
- **MLflow** for agent autologging
- **Bright Data** (optional) as a proxy for paywalled PDFs

## Setup

```bash
# Install uv (if needed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install all workspace packages
uv sync

# Set required env vars
export OPENAI_API_KEY="sk-..."
export OBSIDIAN_VAULT_PATH="/path/to/your/vault"

# Optional — enables Bright Data proxy for paywalled PDFs
export WEB_UNLOCKER_1_KEY="..."
```

## Usage

### Python API

```python
from source_digestion_agent import SourceDigestionAgent

agent = SourceDigestionAgent(
    vault_directory="/path/to/your/vault",
    doi="10.48550/arXiv.1706.03762",  # "Attention Is All You Need"
)

print(agent.invoke("Digest this source", thread_id="session-1"))
```

### Add a source without the agent

```python
from add_source_to_vault import SourceManager

SourceManager(vault_path="/path/to/your/vault").add_source("10.48550/arXiv.1706.03762")
```

### Download a PDF only

```python
from pdf_from_doi.client import PDFFromDOI

PDFFromDOI().download("10.48550/arXiv.1706.03762")
```

### Debug mode (step through every tool call)

```python
agent = SourceDigestionAgent(..., debug=True)
```

## Vault Structure

```
vault/
└── Sources/
    ├── pdfs/    # original PDFs
    ├── raw/     # plain text extracted from PDF
    ├── md/      # structured metadata (title, authors, abstract, DOI, …)
    └── bib/     # BibTeX citation files
└── p/           # Proposition notes
└── c/           # Concept notes
└── s/           # Source notes (created by the agent)
```

## Running Tests

```bash
uv run python test_all.py
```

## License

See [LICENSE](LICENSE).
