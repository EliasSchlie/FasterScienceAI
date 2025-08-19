# pdf-from-doi

Minimal client to fetch an open-access PDF given a DOI (uses Unpaywall, optional Bright Data proxy).

## Examples

Basic usage in code:

```python
from pdf_from_doi.client import PDFFromDOI

PDFFromDOI().download("10.48550/arXiv.1706.03762")
```

Run the bundled example:

```bash
uv run examples/basic_download.py
```
