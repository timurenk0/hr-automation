from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# these are the schemas for response

# these schemas are used for serialization and repsonse schema

class PDFLinkRead(BaseModel):
    """An extracted link nested within its source document's response."""

    # from_attributes = True, allows validation directly from sqlalchemy objects
    # including nested links 

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    platform: str
    url: str

# required content and links, every response must explicitly provide them. 
# empty text and [] are valid for pdfs without extractable content or links

class PDFDocumentRead(BaseModel):
    """A saved PDF document with its extracted links loaded for serialization."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    content: str
    created_at: datetime
    links: list[PDFLinkRead]
