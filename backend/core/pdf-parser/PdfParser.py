from pypdf import PdfReader
from pathlib import Path

class PDFParser:
    def __init__(self, filepath: str):
        self.reader = self.__load_pdf(filepath)

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


    def parse(self) -> str:
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

        return [l for l in links if "linkedin" in l][0]
        

pdf = PDFParser("data/cv.pdf").parse()
print("Linked link:", pdf)