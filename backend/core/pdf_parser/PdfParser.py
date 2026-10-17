from pypdf import PdfReader
from pathlib import Path
from dataclasses import dataclass
from io import BytesIO


@dataclass(slots=True)
class LinkStorage:
    reddit: str | None = None
    linkedin: str | None = None
    github: str | None = None


class PDFParser:
    def __init__(self, file: str | BytesIO):
        self.reader = self.__load_pdf(file)
        self.linkStorage = LinkStorage()

    @staticmethod
    def __load_pdf(file: str | BytesIO) -> Path:
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


    def parse(self) -> LinkStorage:
        pages = self.reader.get_num_pages()

        key = '/Annots'
        uri = '/URI'
        ank = '/A'

        links = []

        for page in range(pages):
            pageObject = self.reader.get_page(page).get_object()

            if key in pageObject.keys():
                ann = pageObject[key]

                for a in ann:
                    u = a.get_object()
                    if uri in u[ank].keys():
                        links.append(u[ank][uri])

        for link in links:
            for field in self.linkStorage.__dataclass_fields__:
                if field in link.lower():
                    setattr(self.linkStorage, field, link)
        
        return self.linkStorage
        

# pdf = PDFParser("data/cv.pdf").parse()
# print("Linked link:", pdf)