from dataclasses import dataclass
from io import BytesIO
<<<<<<< HEAD

# from backend.utility.types import ExtractedLink
=======
from ipaddress import ip_address
from pathlib import Path
import re
from urllib.parse import urlsplit

from pypdf import PdfReader
from pypdf.errors import PdfReadError
>>>>>>> cdf1644f21c86da8b784c81d5b4aa84040a5f9da


@dataclass(slots=True)
class ExtractedLink:
    url: str
    platform: str | None = None
    category: str | None = None


# the parser's platform-keyed links will need conversion into link records
# in the service.

# we will need to change a bit parser.


@dataclass(slots=True)
class ExtractData:
    links: list[ExtractedLink]
    content: str = ""


def _normalize_hostname(hostname: str) -> str:
    """Validate a DNS hostname or IP literal without making network requests."""
    try:
        return str(ip_address(hostname))
    except ValueError:
        hostname = hostname.encode("idna").decode("ascii").lower().rstrip(".")
        labels = hostname.split(".")
        if len(hostname) > 253 or any(
            not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
            for label in labels
        ):
            raise ValueError("Invalid hostname")
        return hostname


class PDFParser:
    def __init__(self, file: str | BytesIO):
        self.reader = self.__load_pdf(file)

    @staticmethod
    def __load_pdf(file: str | BytesIO) -> PdfReader:
        try:
            if isinstance(file, BytesIO):
                reader = PdfReader(file)
            else:
                basepath = Path(__file__).resolve().parent
                path = Path(basepath / file).resolve(strict=True)
                if not path.is_file():
                    raise ValueError("Provided path is not a file")
                if path.suffix.lower() != ".pdf":
                    raise ValueError("Provided file is not PDF")
                reader = PdfReader(str(path), strict=True)
            if reader.is_encrypted:
                raise ValueError("Encrypted PDFs are not supported")
            return reader
        except (OSError, ValueError, PdfReadError) as error:
            raise ValueError(f"Invalid PDF: {error}") from error

    def extract_links(self, page_object) -> list[ExtractedLink]:
        links = []
        annotations = page_object.get("/Annots")
        if not annotations:
            return links

        for annotation_ref in annotations:
            annotation = annotation_ref.get_object()
            if not isinstance(annotation, dict) or annotation.get("/Subtype") != "/Link":
                continue
            action = annotation.get("/A")
            if action is None:
                continue
            action = action.get_object()
            if not isinstance(action, dict) or action.get("/S") != "/URI":
                continue
            uri = action.get("/URI")
            if not isinstance(uri, str) or not uri:
                continue
            # urlsplit silently strips some control characters; reject them first.
            if any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in uri):
                continue
            try:
                parsed = urlsplit(uri)
                if parsed.scheme.lower() not in ("http", "https") or not parsed.hostname:
                    continue
                # Accessing port validates its syntax and range.
                parsed.port
                platform = _normalize_hostname(parsed.hostname)
            except (ValueError, UnicodeError):
                continue
            links.append(ExtractedLink(url=str(uri), platform=platform))
        return links

    def parse(self) -> ExtractData:
        page_texts = []
        links: list[ExtractedLink] = []
        seen_urls: set[tuple] = set()
        for page in self.reader.pages:
            page_texts.append(page.extract_text() or "")
            for link in self.extract_links(page):
                parsed = urlsplit(link.url)
                # Scheme and hostname are case-insensitive; paths, queries,
                # fragments and credentials retain their original case.
                identity = (
                    parsed.scheme.lower(), link.platform, parsed.port,
                    parsed.username, parsed.password, parsed.path,
                    parsed.query, parsed.fragment,
                )
                if identity not in seen_urls:
                    seen_urls.add(identity)
                    links.append(link)
        return ExtractData(links=links, content="\n\n".join(page_texts))
