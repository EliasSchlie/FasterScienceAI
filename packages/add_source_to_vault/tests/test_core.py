import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
import requests
from add_source_to_vault import SourceManager


@pytest.fixture
def temp_vault():
    """Create temporary vault directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_source_manager_init(temp_vault):
    """Test SourceManager initialization."""
    manager = SourceManager(str(temp_vault))
    assert manager.vault_path == temp_vault
    
    # Check directories were created
    sources_path = temp_vault / "sources"
    for subdir in ["pdfs", "raw", "md", "bib"]:
        assert (sources_path / subdir).exists()


def test_sanitize_filename():
    """Test filename sanitization."""
    manager = SourceManager("/tmp")
    
    assert manager._sanitize_filename("Test Paper: A Study!") == "test-paper-a-study"
    
    # Test long filename truncation
    long_title = "Very Long Title " * 20
    sanitized_long = manager._sanitize_filename(long_title)
    assert len(sanitized_long) <= 100
    assert sanitized_long.startswith("very-long-title")


@patch('add_source_to_vault.core.requests.get')
def test_get_metadata(mock_get):
    """Test metadata fetching."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "message": {
            "title": ["Test Paper"],
            "author": [{"given": "John", "family": "Doe"}],
            "container-title": ["Test Journal"],
            "published-print": {"date-parts": [[2023]]},
            "abstract": "Test abstract"
        }
    }
    mock_get.return_value = mock_response
    
    manager = SourceManager("/tmp")
    metadata = manager._get_metadata("10.1234/test")
    
    assert metadata["title"] == "Test Paper"
    assert metadata["authors"] == ["John Doe"]
    assert metadata["year"] == "2023"
    assert metadata["doi"] == "10.1234/test"


@patch('add_source_to_vault.core.requests.get')
def test_get_metadata_failure(mock_get):
    """Test metadata fetching when API fails."""
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_get.return_value = mock_response
    
    manager = SourceManager("/tmp")
    metadata = manager._get_metadata("10.1234/nonexistent")
    
    # Should return None when metadata cannot be retrieved
    assert metadata is None


@patch('add_source_to_vault.core.requests.get')
def test_arxiv_metadata(mock_get):
    """Test arXiv metadata fetching."""
    # Mock arXiv API response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b'''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Test arXiv Paper</title>
    <author><name>John Doe</name></author>
    <author><name>Jane Smith</name></author>
    <published>2023-06-15T17:58:24Z</published>
    <summary>This is a test abstract.</summary>
  </entry>
</feed>'''
    mock_get.return_value = mock_response
    
    manager = SourceManager("/tmp")
    metadata = manager._get_arxiv_metadata("10.48550/arXiv.2306.12345")
    
    assert metadata["title"] == "Test arXiv Paper"
    assert metadata["authors"] == ["John Doe", "Jane Smith"]
    assert metadata["journal"] == "arXiv"
    assert metadata["year"] == "2023"
    assert metadata["abstract"] == "This is a test abstract."


def test_source_exists(temp_vault):
    """Test _source_exists method."""
    manager = SourceManager(str(temp_vault))
    
    # Initially no source exists
    assert not manager._source_exists("test-paper")
    
    # Create a PDF file
    pdf_path = temp_vault / "sources" / "pdfs" / "test-paper.pdf"
    pdf_path.write_text("fake pdf content")
    assert manager._source_exists("test-paper")
    
    # Remove PDF, create MD file instead
    pdf_path.unlink()
    md_path = temp_vault / "sources" / "md" / "test-paper.md"
    md_path.write_text("fake md content")
    assert manager._source_exists("test-paper")
    
    # Remove MD, create BIB file instead
    md_path.unlink()
    bib_path = temp_vault / "sources" / "bib" / "test-paper.bib"
    bib_path.write_text("fake bib content")
    assert manager._source_exists("test-paper")


def test_sanitize_filename_edge_cases():
    """Test _sanitize_filename with edge cases."""
    manager = SourceManager("/tmp")
    
    # Empty string
    assert manager._sanitize_filename("") == ""
    
    # Only special characters
    assert manager._sanitize_filename("!@#$%^&*()") == ""
    
    # Leading/trailing whitespace
    assert manager._sanitize_filename("  Leading and Trailing  ") == "leading-and-trailing"


def test_extract_first_author_lastname():
    """Test _extract_first_author_lastname method."""
    manager = SourceManager("/tmp")
    
    # Normal case
    metadata = {"authors": ["John Doe", "Jane Smith"]}
    assert manager._extract_first_author_lastname(metadata) == "doe"
    
    # Single name
    metadata_single = {"authors": ["Einstein"]}
    assert manager._extract_first_author_lastname(metadata_single) == "einstein"
    
    # Multiple parts
    metadata_multiple = {"authors": ["Jean-Claude Van Damme"]}
    assert manager._extract_first_author_lastname(metadata_multiple) == "damme"
    
    # Empty authors
    metadata_empty = {"authors": []}
    assert manager._extract_first_author_lastname(metadata_empty) == "unknown"
    
    # Missing authors key
    metadata_missing = {}
    assert manager._extract_first_author_lastname(metadata_missing) == "unknown"
    
    # Empty string author
    metadata_empty_str = {"authors": [""]}
    assert manager._extract_first_author_lastname(metadata_empty_str) == "unknown"
    
    # Author with special characters
    metadata_special = {"authors": ["José García-Martinez"]}
    assert manager._extract_first_author_lastname(metadata_special) == "garcamartinez"


def test_create_filename():
    """Test _create_filename method."""
    manager = SourceManager("/tmp")
    
    # With year and author
    metadata_with_year = {"title": "Test Paper", "year": "2023", "authors": ["John Doe"]}
    assert manager._create_filename(metadata_with_year) == "2023-doe-test-paper"
    
    # Without year but with author
    metadata_no_year = {"title": "Test Paper", "year": "", "authors": ["John Doe"]}
    assert manager._create_filename(metadata_no_year) == "doe-test-paper"
    
    # Missing year key but with author
    metadata_missing_year = {"title": "Test Paper", "authors": ["John Doe"]}
    assert manager._create_filename(metadata_missing_year) == "doe-test-paper"
    
    # Missing authors
    metadata_no_authors = {"title": "Test Paper", "year": "2023"}
    assert manager._create_filename(metadata_no_authors) == "2023-unknown-test-paper"


def test_create_bibtex():
    """Test _create_bibtex method."""
    manager = SourceManager("/tmp")
    
    # Test with full metadata
    metadata = {
        "title": "Test Paper",
        "authors": ["John Doe", "Jane Smith"],
        "journal": "Test Journal",
        "year": "2023",
        "doi": "10.1234/test"
    }
    
    bib_content = manager._create_bibtex(metadata, "test-paper")
    
    assert "@article{test-paper," in bib_content
    assert "title={Test Paper}" in bib_content
    assert "author={John Doe and Jane Smith}" in bib_content
    assert "journal={Test Journal}" in bib_content
    assert "year={2023}" in bib_content
    assert "doi={10.1234/test}" in bib_content
    
    # Test with empty authors
    metadata_no_authors = metadata.copy()
    metadata_no_authors["authors"] = []
    
    bib_content = manager._create_bibtex(metadata_no_authors, "test-paper")
    assert "author={Unknown}" in bib_content


@patch('add_source_to_vault.core.requests.get')
def test_arxiv_metadata_xml_errors(mock_get):
    """Test _get_arxiv_metadata with XML parsing errors."""
    manager = SourceManager("/tmp")
    
    # Test with malformed XML
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b'<invalid>xml</malformed>'
    mock_get.return_value = mock_response
    
    metadata = manager._get_arxiv_metadata("10.48550/arXiv.2306.12345")
    
    # Should return None when XML cannot be parsed
    assert metadata is None
    
    # Test with empty response
    mock_response.content = b''
    metadata = manager._get_arxiv_metadata("10.48550/arXiv.2306.12345")
    assert metadata is None
    
    # Test with XML but no entry
    mock_response.content = b'''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
</feed>'''
    metadata = manager._get_arxiv_metadata("10.48550/arXiv.2306.12345")
    assert metadata is None


@patch('add_source_to_vault.core.pymupdf4llm.to_markdown')
@patch.object(SourceManager, '_source_exists')
def test_add_source_success(mock_source_exists, mock_to_markdown, temp_vault):
    """Test successful add_source flow."""
    mock_source_exists.return_value = False
    mock_to_markdown.return_value = "Extracted text content"
    
    # Mock PDFFromDOI
    manager = SourceManager(str(temp_vault))
    manager.pdffromdoi = MagicMock()
    manager.pdffromdoi.download.return_value = "/tmp/downloaded.pdf"
    
    # Mock metadata
    with patch.object(manager, '_get_metadata') as mock_get_metadata:
        mock_get_metadata.return_value = {
            "title": "Test Paper",
            "authors": ["John Doe"],
            "journal": "Test Journal",
            "year": "2023",
            "doi": "10.1234/test",
            "abstract": "Test abstract"
        }
        
        result = manager.add_source("10.1234/test")
        
        assert result == "2023-doe-test-paper"
        mock_get_metadata.assert_called_once_with("10.1234/test")
        manager.pdffromdoi.download.assert_called_once_with(doi="10.1234/test", filename="2023-doe-test-paper")
        mock_to_markdown.assert_called_once()
        
        # Check files were created
        assert (temp_vault / "sources" / "raw" / "2023-doe-test-paper.txt").exists()
        assert (temp_vault / "sources" / "md" / "2023-doe-test-paper.md").exists()
        assert (temp_vault / "sources" / "bib" / "2023-doe-test-paper.bib").exists()


@patch.object(SourceManager, '_source_exists')
def test_add_source_already_exists(mock_source_exists, temp_vault):
    """Test add_source when source already exists."""
    mock_source_exists.return_value = True
    
    manager = SourceManager(str(temp_vault))
    
    with patch.object(manager, '_get_metadata') as mock_get_metadata:
        mock_get_metadata.return_value = {"title": "Test Paper"}
        
        result = manager.add_source("10.1234/test")
        
        assert result is None
        mock_get_metadata.assert_called_once()


@patch.object(SourceManager, '_source_exists')
def test_add_source_pdf_download_fails(mock_source_exists, temp_vault):
    """Test add_source when PDF download fails."""
    mock_source_exists.return_value = False
    
    manager = SourceManager(str(temp_vault))
    manager.pdffromdoi = MagicMock()
    manager.pdffromdoi.download.return_value = None  # Download fails
    
    with patch.object(manager, '_get_metadata') as mock_get_metadata:
        mock_get_metadata.return_value = {"title": "Test Paper", "year": "", "authors": []}
        
        result = manager.add_source("10.1234/test")
        
        assert result is None
        manager.pdffromdoi.download.assert_called_once_with(doi="10.1234/test", filename="unknown-test-paper")


def test_init_with_brightdata_key(temp_vault):
    """Test SourceManager initialization with brightdata_api_key."""
    api_key = "test_api_key"
    
    with patch('add_source_to_vault.core.PDFFromDOI') as mock_pdf_from_doi:
        manager = SourceManager(str(temp_vault), brightdata_api_key=api_key)
        
        mock_pdf_from_doi.assert_called_once_with(
            output_dir=manager.sources_path / "pdfs",
            brightdata_api_key=api_key
        )


@patch('add_source_to_vault.core.requests.get')
def test_get_metadata_network_error(mock_get):
    """Test _get_metadata when network request raises an exception."""
    mock_get.side_effect = requests.exceptions.RequestException("Network error")
    
    manager = SourceManager("/tmp")
    
    # Should handle network errors gracefully and return None
    metadata = manager._get_metadata("10.1234/test")
    
    assert metadata is None


@patch('add_source_to_vault.core.requests.get')
def test_get_metadata_invalid_json(mock_get):
    """Test _get_metadata with invalid JSON response."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.side_effect = ValueError("Invalid JSON")
    mock_get.return_value = mock_response
    
    manager = SourceManager("/tmp")
    
    # Should handle JSON parsing errors gracefully and return None
    metadata = manager._get_metadata("10.1234/test")
    
    assert metadata is None


def test_get_metadata_missing_fields():
    """Test _get_metadata with missing fields in response."""
    manager = SourceManager("/tmp")
    
    with patch('add_source_to_vault.core.requests.get') as mock_get:
        # Test with minimal response data - should still work if we have a title
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {
                # Only title, missing everything else
                "title": ["Minimal Paper"]
            }
        }
        mock_get.return_value = mock_response
        
        metadata = manager._get_metadata("10.1234/test")
        
        assert metadata["title"] == "Minimal Paper"
        assert metadata["authors"] == []  # Should handle missing authors
        assert metadata["journal"] == ""  # Should handle missing journal
        assert metadata["year"] == ""     # Should handle missing year
        assert metadata["doi"] == "10.1234/test"
        assert metadata["abstract"] == "" # Should handle missing abstract
        
        # Test with completely missing title - should return None
        mock_response.json.return_value = {
            "message": {
                # No title at all
                "authors": ["Some Author"]
            }
        }
        
        metadata = manager._get_metadata("10.1234/test")
        assert metadata is None


@patch('add_source_to_vault.core.pymupdf4llm.to_markdown')
@patch.object(SourceManager, '_source_exists')
def test_add_source_file_write_error(mock_source_exists, mock_to_markdown, temp_vault):
    """Test add_source when file writing fails."""
    mock_source_exists.return_value = False
    mock_to_markdown.return_value = "Extracted text content"
    
    # Create manager first to ensure directories exist
    manager = SourceManager(str(temp_vault))
    manager.pdffromdoi = MagicMock()
    manager.pdffromdoi.download.return_value = "/tmp/downloaded.pdf"
    
    # Now make one of the directories read-only to simulate write error
    raw_dir = temp_vault / "sources" / "raw"
    raw_dir.chmod(0o444)  # Read-only
    
    try:
        with patch.object(manager, '_get_metadata') as mock_get_metadata:
            mock_get_metadata.return_value = {
                "title": "Test Paper",
                "authors": ["John Doe"],
                "journal": "Test Journal", 
                "year": "2023",
                "doi": "10.1234/test",
                "abstract": "Test abstract"
            }
            
            # Should handle file write errors gracefully and return None
            result = manager.add_source("10.1234/test")
            assert result is None
    finally:
        # Clean up - restore permissions
        raw_dir.chmod(0o755)


@patch.object(SourceManager, '_source_exists')
def test_add_source_metadata_fails(mock_source_exists, temp_vault):
    """Test add_source when metadata retrieval fails."""
    mock_source_exists.return_value = False
    
    manager = SourceManager(str(temp_vault))
    
    with patch.object(manager, '_get_metadata') as mock_get_metadata:
        mock_get_metadata.return_value = None  # Metadata retrieval fails
        
        result = manager.add_source("10.1234/test")
        
        assert result is None
        mock_get_metadata.assert_called_once_with("10.1234/test")
        # PDF download should not be attempted if metadata fails


def test_template_integration():
    """Integration test to verify templates work with real file system."""
    manager = SourceManager("/tmp")
    
    # Test metadata that should work with real templates
    metadata = {
        "title": "Integration Test Paper",
        "authors": ["Test Author"],
        "journal": "Test Journal",
        "year": "2023",
        "doi": "10.1234/integration",
        "abstract": "This is an integration test abstract."
    }
    
    filename = "integration-test"
    
    # These should not raise exceptions when using real template files
    try:
        md_content = manager._create_metadata_md(metadata, filename)
        bib_content = manager._create_bibtex(metadata, filename)
    except Exception as e:
        pytest.fail(f"Template integration failed: {e}")
    
    # Basic sanity checks
    assert len(md_content) > 0
    assert len(bib_content) > 0
    assert "Integration Test Paper" in md_content


def test_template_files_exist_and_valid():
    """Test that template files exist and have valid format strings."""
    from pathlib import Path
    import tempfile
    
    manager = SourceManager("/tmp")
    
    # Check template files exist
    md_template_path = Path(__file__).parent.parent / "src" / "add_source_to_vault" / "templates" / "metadata.md"
    bib_template_path = Path(__file__).parent.parent / "src" / "add_source_to_vault" / "templates" / "citation.bib"
    
    assert md_template_path.exists(), f"Metadata template not found at {md_template_path}"
    assert bib_template_path.exists(), f"BibTeX template not found at {bib_template_path}"
    
    # Check template format strings are valid by attempting to format them
    md_template = md_template_path.read_text()
    bib_template = bib_template_path.read_text()
    
    test_data = {
        "title": "Test",
        "authors": "Test Author", 
        "journal": "Test Journal",
        "year": "2023",
        "doi": "10.1234/test",
        "abstract": "Test abstract",
        "filename": "test"
    }
    
    try:
        md_template.format(**test_data)
    except KeyError as e:
        pytest.fail(f"Metadata template has invalid format string: {e}")
    except Exception as e:
        pytest.fail(f"Metadata template formatting failed: {e}")
        
    try:
        bib_template.format(**test_data)  
    except KeyError as e:
        pytest.fail(f"BibTeX template has invalid format string: {e}")
    except Exception as e:
        pytest.fail(f"BibTeX template formatting failed: {e}")


@patch.object(SourceManager, '_source_exists')
def test_add_source_end_to_end_integration(mock_source_exists, temp_vault):
    """End-to-end integration test that creates actual files."""
    mock_source_exists.return_value = False
    
    manager = SourceManager(str(temp_vault))
    
    # Mock the PDF download and text extraction to avoid external dependencies
    with patch.object(manager.pdffromdoi, 'download') as mock_download, \
         patch('add_source_to_vault.core.pymupdf4llm.to_markdown') as mock_to_markdown:
        
        mock_download.return_value = "/fake/path.pdf"
        mock_to_markdown.return_value = "Fake extracted text"
        
        # Mock metadata retrieval
        with patch.object(manager, '_get_metadata') as mock_get_metadata:
            mock_get_metadata.return_value = {
                "title": "Real Integration Test",
                "authors": ["Alice Smith", "Bob Jones"],
                "journal": "Integration Journal",
                "year": "2023", 
                "doi": "10.1234/real-test",
                "abstract": "This tests the real template integration with actual file creation."
            }
            
            # This should work end-to-end without exceptions
            result = manager.add_source("10.1234/real-test")
            
            # Should return the filename
            assert result == "2023-smith-real-integration-test"
            
            # Files should actually be created with real template content
            md_file = temp_vault / "sources" / "md" / f"{result}.md"
            bib_file = temp_vault / "sources" / "bib" / f"{result}.bib" 
            raw_file = temp_vault / "sources" / "raw" / f"{result}.txt"
            
            assert md_file.exists()
            assert bib_file.exists()
            assert raw_file.exists()
            
            # Check actual file content uses templates correctly
            md_content = md_file.read_text()
            bib_content = bib_file.read_text()
            
            # Should contain YAML frontmatter
            assert md_content.startswith("---")
            assert "authors:" in md_content
            assert "Alice Smith" in md_content
            assert "# Real Integration Test" in md_content
            
            # Should contain proper BibTeX
            assert "@article{" in bib_content
            assert "title={Real Integration Test}" in bib_content
