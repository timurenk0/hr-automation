from fastapi import File, UploadFile
from routes.router import router
from io import BytesIO
from services.parse_cv import parse_cv


@router.post("/upload-pdf")
async def uploadPDF(pdf: UploadFile = File(...)):
    if pdf.content_type != "application/pdf":
        print("[ERROR] Uploaded file is not in .pdf format")
        return

    if pdf.size > 10 * 1024 * 1024:
        print("[ERROR] Uploaded file exceeds 10MB in size")
        return

    pdf_bytes = await pdf.read()

    pdf_stream = BytesIO(pdf_bytes)

    result = parse_cv(pdf_stream)

    return result
