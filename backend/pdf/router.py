from fastapi import File, UploadFile
from routes.router import router
from io import BytesIO
from services.parse_cv import parse_cv


@router.post("/upload-pdf")
async def uploadPDF(pdf: UploadFile = File(...)):
    print("File name:", pdf.filename)
    print("file extension:", pdf.content_type)
    print("file size:", pdf.size)

    pdf_bytes = await pdf.read()

    pdf_stream = BytesIO(pdf_bytes)

    result = parse_cv(pdf_stream)

    return result
