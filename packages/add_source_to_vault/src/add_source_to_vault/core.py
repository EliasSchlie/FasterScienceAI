import errno
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

import pymupdf4llm
import requests
from pdf_from_doi import PDFFromDOI


class SourceManager:
    """Manages adding academic sources to Obsidian vaults."""
    
    def __init__(self, vault_path: str, brightdata_api_key: str = None):
        self.vault_path = Path(vault_path)
        self.sources_path = self.vault_path / "sources"
        self.pdffromdoi = PDFFromDOI(output_dir=self.sources_path, brightdata_api_key=brightdata_api_key)
    
    def _sanitize_filename(self, title: str) -> str:
        """Convert title to safe filename."""
        return re.sub(r'[^\w\s-]', '', title).strip()[:100].replace(' ', '-').lower()
    
    def _extract_first_author_lastname(self, metadata: dict) -> str:
        """Extract and sanitize first author's last name."""
        authors = metadata.get("authors", [])
        if not authors:
            return "unknown"
        
        # Get first author and extract last name (assumes "First Last" format)
        first_author = authors[0]
        parts = first_author.strip().split()
        if not parts:
            return "unknown"
        
        last_name = parts[-1]  # Take the last part as surname
        # Remove all non-ASCII alphanumeric characters and convert to lowercase
        return re.sub(r'[^a-zA-Z0-9]', '', last_name).lower()
    
    def _create_filename(self, metadata: dict) -> str:
        """Create filename with year and author prefix."""
        title_part = self._sanitize_filename(metadata["title"])
        author_part = self._extract_first_author_lastname(metadata)
        year = metadata.get("year", "")
        
        if year:
            return f"{year}-{author_part}-{title_part}"
        else:
            return f"{author_part}-{title_part}"
    
    def _get_metadata(self, doi: str) -> dict:
        """Fetch paper metadata from DOI. Raises on failure."""
        if "arxiv" in doi.lower():
            return self._get_arxiv_metadata(doi)
        
        url = f"https://api.crossref.org/works/{doi}"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            
            data = response.json()["message"]
        except requests.exceptions.RequestException as e:
            raise requests.exceptions.HTTPError(f"Crossref request failed for DOI {doi}") from e
        except (ValueError, KeyError) as e:
            raise ValueError(f"Invalid Crossref response for DOI {doi}") from e
        
        # Only return metadata if we have at least a title
        if not (title := data.get("title")):
            raise ValueError("Crossref metadata missing title")
            
        metadata = {"title": title[0], "doi": doi}
        
        if authors := data.get("author"):
            metadata["authors"] = [f"{a.get('given', '')} {a.get('family', '')}" for a in authors]
        else:
            metadata["authors"] = []
        
        if journal := data.get("container-title"):
            metadata["journal"] = journal[0]
        else:
            metadata["journal"] = ""
        
        if year := (data.get("published-print", {}).get("date-parts", [[None]])[0][0] or 
                   data.get("published-online", {}).get("date-parts", [[None]])[0][0]):
            metadata["year"] = str(year)
        else:
            metadata["year"] = ""
        
        if abstract := data.get("abstract"):
            metadata["abstract"] = abstract
        else:
            metadata["abstract"] = ""
        
        return metadata
    
    def _get_arxiv_metadata(self, doi: str) -> dict:
        """Fetch metadata for arXiv papers. Raises on failure."""
        arxiv_id = doi.split("arXiv.")[-1]
        url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            entry = root.find("{http://www.w3.org/2005/Atom}entry")
            if entry is None:
                raise LookupError("arXiv response missing entry")
        except requests.exceptions.RequestException as e:
            raise requests.exceptions.HTTPError(f"arXiv request failed for DOI {doi}") from e
        except ET.ParseError as e:
            raise ValueError("Invalid XML from arXiv") from e
        
        # Only return metadata if we can get at least a title
        title_elem = entry.find("{http://www.w3.org/2005/Atom}title")
        if title_elem is None or not title_elem.text:
            raise ValueError("arXiv metadata missing title")
            
        metadata = {
            "title": title_elem.text.strip().replace('\n', ' '),
            "doi": doi,
            "journal": "arXiv",
            "authors": [],
            "year": "",
            "abstract": ""
        }
        
        if author_elems := entry.findall("{http://www.w3.org/2005/Atom}author"):
            authors = [a.find("{http://www.w3.org/2005/Atom}name").text 
                      for a in author_elems if a.find("{http://www.w3.org/2005/Atom}name") is not None]
            if authors:
                metadata["authors"] = authors
        
        abstract_elem = entry.find("{http://www.w3.org/2005/Atom}summary")
        if abstract_elem is not None and abstract_elem.text:
            metadata["abstract"] = abstract_elem.text.strip().replace('\n', ' ')
        
        published_elem = entry.find("{http://www.w3.org/2005/Atom}published")
        if published_elem is not None and published_elem.text:
            year = published_elem.text.split('-')[0]
            if year:
                metadata["year"] = year
        
        return metadata
    
    def _source_exists(self, filename: str) -> bool:
        """Check if source already exists."""
        return all((dir / f"{filename}.{ext}").exists() 
                  for dir, ext in [(self.sources_path, "pdf"), ("s", "md"), (self.sources_path, "txt"), (self.sources_path, "bib")])
    
    def add_source(self, doi: str) -> list[str]:
        """Add source to vault. Returns dict with filename, raw_text, md_content, bib_content if successful, raises on failure."""
        # Get metadata
        metadata = self._get_metadata(doi)
            
        filename = self._create_filename(metadata)
        
        # Check if exists
        if self._source_exists(filename):
            raise FileExistsError(errno.EEXIST, "Source already exists", filename)
        
        # Download PDF
        pdf_path = self.pdffromdoi.download(doi=doi, filename=filename)
        
        try:            
            # Extract text using PyMuPDF4LLM
            raw_text = pymupdf4llm.to_markdown(str(pdf_path))
            (self.sources_path / f"{filename}.txt").write_text(raw_text, encoding="utf-8")
            
            # Create metadata markdown
            md_content = self._create_metadata_md(metadata, filename)
            ("s" / f"{filename}.md").write_text(md_content, encoding="utf-8")
            
            # Create BibTeX
            bib_content = self._create_bibtex(metadata, filename)
            (self.sources_path / f"{filename}.bib").write_text(bib_content, encoding="utf-8")
            
            return {
                "filename": filename,
                "raw_text": raw_text,
                "md_content": md_content,
                "bib_content": bib_content
            }
        except (OSError, PermissionError) as e:
            raise OSError(f"Failed to write files for {filename}") from e
    
    def _create_metadata_md(self, metadata: dict, filename: str) -> str:
        """Create structured metadata markdown from template."""
        template_path = Path(__file__).parent / "templates" / "metadata.md"
        template = template_path.read_text(encoding="utf-8")
        
        # Format authors as YAML list
        if metadata["authors"]:
            authors_yaml = "[" + ", ".join(f'"{author}"' for author in metadata["authors"]) + "]"
        else:
            authors_yaml = '["Unknown"]'
        
        # Format abstract for YAML (escape quotes and handle multiline)
        abstract = metadata.get('abstract', '').replace('"', '\\"').replace('\n', ' ')
        
        return template.format(
            title=metadata['title'],
            authors=authors_yaml,
            journal=metadata['journal'],
            year=metadata['year'],
            doi=metadata['doi'],
            abstract=f'"{abstract}"',
            filename=filename
        )
    
    def _create_bibtex(self, metadata: dict, filename: str) -> str:
        """Create BibTeX entry from template."""
        template_path = Path(__file__).parent / "templates" / "citation.bib"
        template = template_path.read_text(encoding="utf-8")
        
        authors_str = " and ".join(metadata["authors"]) if metadata["authors"] else "Unknown"
        
        return template.format(
            filename=filename,
            title=metadata['title'],
            authors=authors_str,
            journal=metadata['journal'],
            year=metadata['year'],
            doi=metadata['doi']
        )