from io import BytesIO
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock

import pytest

from pdf.exceptions import PDFEncryptedError, PDFInvalidError
from pdf.parser import PDFParser


def test_multiple_links_custom_domains_and_case_sensitive_deduplication(make_pdf):
    urls = (
        "HTTPS://GitHub.COM/Alice", "https://github.com/Alice",
        "https://github.com/alice", "https://github.com/Alice",
        "https://Portfolio.Example/Contact?ref=ABC",
        "https://portfolio.example/Contact?ref=abc",
        "https://tel.example/mailto/help",
    )
    parsed = PDFParser(BytesIO(make_pdf(urls=urls))).parse()

    assert [(link.platform, link.url) for link in parsed.links] == [
        ("github.com", urls[0]), ("github.com", urls[2]),
        ("portfolio.example", urls[4]), ("portfolio.example", urls[5]),
        ("tel.example", urls[6]),
    ]
    assert parsed.content == "First page\n\nSecond page"


@pytest.mark.parametrize("url", [
    "mailto:alice@example.com", "tel:+12345", "ftp://example.com/file",
    "javascript:alert(1)", "file:///tmp/cv.pdf", "example.com",
    "//example.com/path", "https:///missing", "http://", "https://[broken/path",
    "https://bad host.example/path", "https://example.com:bad/path",
    "https://example.com:70000/path", "https://-bad.example/path",
    "https://bad..example/path", "https://example.com\n/path", "https://%zz/path",
    "https://example.com\\evil/path", "",
])
def test_malformed_and_non_web_urls_are_ignored(make_pdf, url):
    parsed = PDFParser(BytesIO(make_pdf(urls=(url,)))).parse()

    assert parsed.links == []


@pytest.mark.parametrize("url, hostname", [
    ("https://Example.COM:8443/Case", "example.com"),
    ("http://127.0.0.1/path", "127.0.0.1"),
    ("https://[2001:db8::1]/path", "2001:db8::1"),
    ("https://b\u00fccher.example/path", "xn--bcher-kva.example"),
])
def test_normalized_hostnames_preserve_original_urls(make_pdf, url, hostname):
    link = PDFParser(BytesIO(make_pdf(urls=(url,)))).parse().links[0]

    assert link.platform == hostname
    assert link.url == url


def test_encrypted_byte_stream_is_rejected(make_pdf):
    with pytest.raises(PDFEncryptedError):
        PDFParser(BytesIO(make_pdf(encrypted=True)))


def test_none_page_text_is_safe_and_page_separators_remain(make_pdf, monkeypatch):
    from pypdf._page import PageObject

    monkeypatch.setattr(
        PageObject,
        "extract_text",
        Mock(side_effect=["first", None, "third"]),
    )
    parsed = PDFParser(BytesIO(make_pdf(texts=("", "", "")))).parse()

    assert parsed.content == "first\n\n\n\nthird"


def test_import_has_no_file_access_or_output(tmp_path):
    backend = str(Path(__file__).resolve().parents[1])
    result = subprocess.run(
        [sys.executable, "-c", "import pdf.parser"], cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": backend}, capture_output=True, text=True,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    assert result.stderr == ""


def test_invalid_pdf_preserves_parser_cause():
    from pypdf.errors import PdfReadError

    with pytest.raises(PDFInvalidError) as caught:
        PDFParser(BytesIO(b"not a PDF"))

    assert isinstance(caught.value.__cause__, PdfReadError)


def test_extraction_errors_are_invalid_but_programming_errors_are_not(
    make_pdf,
    monkeypatch,
):
    from pypdf._page import PageObject
    from pypdf.errors import PdfReadError

    original = PdfReadError("private-document-text")
    parser = PDFParser(BytesIO(make_pdf()))
    monkeypatch.setattr(PageObject, "extract_text", Mock(side_effect=original))

    with pytest.raises(PDFInvalidError) as caught:
        parser.parse()

    assert caught.value.__cause__ is original
    monkeypatch.setattr(
        PageObject,
        "extract_text",
        Mock(side_effect=ValueError("programming failure")),
    )

    with pytest.raises(ValueError):
        parser.parse()


def test_broken_link_reference_is_skipped(make_pdf):
    from pypdf.errors import PdfReadError

    parser = PDFParser(BytesIO(make_pdf()))
    reference = Mock()
    reference.get_object.side_effect = PdfReadError("broken annotation")

    assert parser.extract_links({"/Annots": [reference]}) == []
