from pypdf import PdfReader
from pathlib import Path
from dataclasses import dataclass
from typing import Literal
from io import BytesIO

# from backend.utility.types import ExtractedLink


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


class PDFParser:
    def __init__(self, file: str | BytesIO):
        self.reader = self.__load_pdf(file)

    @staticmethod
    def __load_pdf(file: str | BytesIO) -> PdfReader:
        try:
            if isinstance(file, BytesIO):
                return PdfReader(file)

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
        except (OSError, ValueError, Exception) as e:
            raise ValueError(f"Invalid PDF filepath: {file}") from e

    def extract_links(self, page_object) -> list[str]:
        links = []

        annotations = page_object.get("/Annots")
        if not annotations:
            return links

        for annotation_ref in annotations:
            annotation = annotation_ref.get_object()

            if annotation.get("/Subtype") != "/Link":
                continue

            action = annotation.get("/A")
            if not action:
                continue

            if action.get("/S") != "/URI":
                continue

            uri = action.get("/URI")

            if uri:

                # Disregard email adresses as external links
                if "mailto" in uri:
                    continue

                # Disregard phone numbers as external links
                if "tel" in uri:
                    continue

                platform = uri.split("/")[2]

                links.append(ExtractedLink(url=str(uri), platform=platform))

        return links

    def parse(self) -> ExtractData:
        content = ""
        links: list[ExtractedLink] = []
        seen_urls: set[str] = set()

        for page in self.reader.pages:
            content += page.extract_text() or ""

            for link in self.extract_links(page):
                normalized_link = link.url.lower().strip()

                if normalized_link and normalized_link not in seen_urls:
                    seen_urls.add(normalized_link)
                    links.append(link)

        return ExtractData(links=links, content=content)


pdf = PDFParser("data/cv2.pdf").parse()
print("Extract Object:", pdf.links)
