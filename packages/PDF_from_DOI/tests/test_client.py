import os
import tempfile
import pytest
import dotenv

from pdf_from_doi import PDFFromDOI

# Load .env from current working directory (e.g. repo root when running pytest)
dotenv.load_dotenv()
BRIGHT_WEB_UNLOCKER_KEY = os.getenv("BRIGHT_WEB_UNLOCKER_KEY") or os.getenv("WEB_UNLOCKER_1_KEY")


def test_init():
    with tempfile.TemporaryDirectory() as tmpdir:
        client = PDFFromDOI(output_dir=tmpdir)
        assert client.output_dir == tmpdir
        assert os.path.exists(tmpdir)


def test_sanitize_filename():
    client = PDFFromDOI()
    result = client._sanitize_filename("10.1126/science:test<>file")
    assert result == "10.1126_science_test__file"


def test_download_paper():
    """Test downloading a real open-access paper"""
    with tempfile.TemporaryDirectory() as tmpdir:
        client = PDFFromDOI(output_dir=tmpdir)
        # Using a known open-access DOI from PLOS ONE
        doi = "10.1371/journal.pone.0000308"
        result = client.download(doi)
        
        # The download should succeed for this open-access paper
        assert result is not None, f"Download failed for DOI {doi}"
        assert os.path.exists(result), f"Downloaded file does not exist: {result}"
        assert result.endswith(".pdf"), f"Downloaded file is not a PDF: {result}"
        assert os.path.getsize(result) > 0, f"Downloaded file is empty: {result}"


@pytest.mark.skipif(
    not BRIGHT_WEB_UNLOCKER_KEY,
    reason="Bright Data API key not found in .env",
)
def test_download_paper_with_brightdata():
    """Test downloading a paper using Bright Data webunblocker when API key is available"""
    with tempfile.TemporaryDirectory() as tmpdir:
        client = PDFFromDOI(output_dir=tmpdir, brightdata_api_key=BRIGHT_WEB_UNLOCKER_KEY)
        # Using a known DOI that might require webunblocker
        doi = "10.1037/bul0000021"
        result = client.download(doi)
        assert result is not None, f"Download failed for DOI {doi}"
        assert os.path.exists(result), f"Downloaded file does not exist: {result}"
        assert result.endswith(".pdf"), f"Downloaded file is not a PDF: {result}"
        assert os.path.getsize(result) > 0, f"Downloaded file is empty: {result}"
