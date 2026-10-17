from fastapi import File, UploadFile
from routes.router import router
from io import BytesIO
from core.pdf_parser.PdfParser import PDFParser
from dataclasses import asdict


@router.post("/upload-pdf")
async def uploadPDF(pdf: UploadFile = File(...)):
    pdfBytes = await pdf.read()

    pdfStream = BytesIO(pdfBytes)

    content = PDFParser(pdfStream).parse()

    print("content:", content)
    
    return asdict(content)
