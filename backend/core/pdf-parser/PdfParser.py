from pypdf import PdfReader
from pathlib import Path
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LinkStorage:
    reddit: str | None = None
    linkedin: str | None = None
    github: str | None = None


class PDFParser:
    def __init__(self, filepath: str):
        self.reader = self.__load_pdf(filepath)
        self.linkStorage = LinkStorage()

    @staticmethod
    def __load_pdf(filepath: str) -> Path:
        try:
            basepath = Path(__file__).resolve().parent
            
            path = Path(basepath / filepath).resolve(strict=True)

            if not path.is_file():
                raise ValueError("Provided path is not a file")

            if path.suffix.lower() != ".pdf":
                raise ValueError("Provided file is not PDF")

            reader = PdfReader(str(path), strict=True) 

            if reader.is_encrypted:
                raise ValueError("Encrypted PDFs are not supported")

            return reader
        except (OSError, ValueError, Exception) as e:
            raise ValueError(f"Invalid PDF filepath: {filepath}") from e


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
        

pdf = PDFParser("data/cv.pdf").parse()
print("Linked link:", pdf)