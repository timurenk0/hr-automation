from pypdf import PdfReader
from pathlib import Path
from dataclasses import dataclass
from io import BytesIO
# import re
# import unicodedata


# the parser's platform-keyed links will need conversion into link records
# in the service. 

# we will need to change a bit parser.

@dataclass(slots=True)
class LinkStorage:
    reddit: str | None = None
    linkedin: str | None = None
    github: str | None = None


@dataclass(slots=True)
class ExtractData:
    links: LinkStorage | None = None
    content: str = ""


class PDFParser:
    def __init__(self, file: str | BytesIO):
        self.reader = self.__load_pdf(file)
        self.link_storage = LinkStorage()
        self.extract_data = ExtractData()

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

    def parse(self) -> ExtractData:
        pages = self.reader.get_num_pages()

        key = "/Annots"
        uri = "/URI"
        ank = "/A"

        links = []
        content = ""

        for page in range(pages):
            page_object = self.reader.get_page(page).get_object()
            content += page_object.extract_text()

            if key in page_object.keys():
                ann = page_object[key]

                for a in ann:
                    u = a.get_object()
                    if uri in u[ank].keys():
                        links.append(u[ank][uri])

        for link in links:
            for field in self.link_storage.__dataclass_fields__:
                if field in link.lower():
                    setattr(self.link_storage, field, link)

        setattr(self.extract_data, "links", self.link_storage)
        setattr(self.extract_data, "content", content)

        return self.extract_data


pdf = PDFParser("data/cv.pdf").parse()
print("Extract Object:", pdf)
