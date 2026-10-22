from io import BytesIO

import pytest
from pypdf import PdfWriter
from pypdf.generic import (
    ArrayObject, DecodedStreamObject, DictionaryObject, NameObject, TextStringObject,
)


@pytest.fixture
def make_pdf():
    def build(texts=("First page", "Second page"), urls=(), encrypted=False):
        writer = PdfWriter()
        for text in texts:
            page = writer.add_blank_page(width=300, height=300)
            if text:
                font = DictionaryObject({
                    NameObject("/Type"): NameObject("/Font"),
                    NameObject("/Subtype"): NameObject("/Type1"),
                    NameObject("/BaseFont"): NameObject("/Helvetica"),
                })
                page[NameObject("/Resources")] = DictionaryObject({
                    NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})
                })
                stream = DecodedStreamObject()
                stream.set_data(f"BT /F1 12 Tf 10 100 Td ({text}) Tj ET".encode())
                page[NameObject("/Contents")] = writer._add_object(stream)
            annotations = [
                DictionaryObject({NameObject("/Subtype"): NameObject("/Link")}),
                DictionaryObject({
                    NameObject("/Subtype"): NameObject("/Link"),
                    NameObject("/A"): DictionaryObject(),
                }),
            ]
            for url in urls:
                annotations.append(DictionaryObject({
                    NameObject("/Subtype"): NameObject("/Link"),
                    NameObject("/A"): DictionaryObject({
                        NameObject("/S"): NameObject("/URI"),
                        NameObject("/URI"): TextStringObject(url),
                    }),
                }))
            page[NameObject("/Annots")] = ArrayObject([
                writer._add_object(annotation) for annotation in annotations
            ])
        if encrypted:
            writer.encrypt("secret")
        output = BytesIO()
        writer.write(output)
        return output.getvalue()
    return build
