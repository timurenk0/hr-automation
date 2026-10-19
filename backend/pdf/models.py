from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base

# follow the parser's output structure. 

class PDFDocument(Base):
    """Parsed PDF content; the original file is not stored in this table."""

    __tablename__ = "pdf_documents"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    filename: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    
    links: Mapped[list["PDFLink"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", passive_deletes=True
    )


class PDFLink(Base):
    """Extracted URL that a future scraper job can reference by ID.

    The parser currently identifies reddit, linkedin, and github. Missing links
    produce no rows. Scraping status and results belong to the scraper feature.
    """

    __tablename__ = "pdf_links"
    __table_args__ = (
        UniqueConstraint("document_id", "platform", "url", name="uq_pdf_links_source"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("pdf_documents.id", ondelete="CASCADE"), index=True
    )
    platform: Mapped[str] = mapped_column(String(50))
    url: Mapped[str] = mapped_column(Text)

    # just for python access to the parent object
    document: Mapped[PDFDocument] = relationship(back_populates="links")
