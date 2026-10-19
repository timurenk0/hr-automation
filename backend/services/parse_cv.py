from io import BytesIO
from core.pdf_parser.PdfParser import PDFParser
from utility.text_normalizer import normalize_text
from dataclasses import asdict


def parse_cv(file_byte_stream: BytesIO):
    result = PDFParser(file_byte_stream).parse()

    links = result.links
    content = result.content

    clean_content = normalize_text(content)

    return {"links": links, "content": clean_content}
