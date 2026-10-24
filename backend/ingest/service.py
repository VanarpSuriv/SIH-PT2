"""
Document Ingestion Service using PyMuPDF and the dedicated Metadata Service.
Extracts SHA-256 hash, PDF metadata, signature presence, page text, and word bounding boxes.
"""
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
import pymupdf

from backend.models import (
    DocumentType,
    DocumentRecord,
    DocumentMetadata,
    PageData,
    ExtractedWord
)
from backend.metadata.service import extract_pdf_metadata, compute_sha256

def detect_document_type(full_text: str) -> DocumentType:
    """Classify document type based on structural headers and content tokens."""
    upper = full_text.upper()
    if "APPLICATION FOR EXTENSION OF APPROVAL" in upper or "AICTE EXTENSION OF APPROVAL" in upper:
        return DocumentType.APPLICATION_FORM
    if ("FIRE SAFETY" in upper or "DIRECTORATE OF FIRE" in upper or "NOC CERTIFICATE" in upper) and "FIRE" in upper:
        return DocumentType.FIRE_NOC
    if "FACULTY ROSTER" in upper or "APPROVED FACULTY ROSTER" in upper or "CADRE DETAILS" in upper:
        return DocumentType.FACULTY_LIST
    if "SUB-REGISTRAR" in upper or "TITLE DEED" in upper or "LAND CERTIFICATE" in upper:
        return DocumentType.LAND_DOCUMENT
    if "ALL INDIA COUNCIL FOR TECHNICAL EDUCATION" in upper and ("LETTER ORDER" in upper or "CONVEYS THE EXTENSION" in upper or "SUB: EXTENSION" in upper):
        return DocumentType.APPROVAL_LETTER
    
    return DocumentType.UNKNOWN

def extract_pdf_data(file_bytes: bytes, filename: str, application_id: str, storage_path: str) -> Tuple[DocumentRecord, List[PageData]]:
    """
    Ingest a PDF file using PyMuPDF and the dedicated metadata service.
    Calculates SHA-256, extracts metadata, checks signatures, extracts text and word bboxes.
    """
    # 1. Dedicated metadata extraction
    doc_metadata = extract_pdf_metadata(file_bytes, filename)
    sha256_hash = doc_metadata.sha256_hash or compute_sha256(file_bytes)
    
    # 2. Persist binary to storage path
    os.makedirs(os.path.dirname(storage_path), exist_ok=True)
    with open(storage_path, "wb") as f:
        f.write(file_bytes)

    # 3. Extract page text and word bounding coordinates
    doc = pymupdf.open(stream=file_bytes, filetype="pdf")
    page_count = doc.page_count
    pages: List[PageData] = []
    full_text = []

    for page_idx in range(page_count):
        page = doc[page_idx]
        rect = page.rect
        page_text = page.get_text("text")
        full_text.append(page_text)

        # PyMuPDF words: (x0, y0, x1, y1, "word", block_no, line_no, word_no)
        raw_words = page.get_text("words")
        words: List[ExtractedWord] = []
        for w in raw_words:
            if len(w) >= 8:
                words.append(ExtractedWord(
                    text=w[4],
                    bbox=[round(w[0], 2), round(w[1], 2), round(w[2], 2), round(w[3], 2)],
                    block_no=w[5],
                    line_no=w[6],
                    word_no=w[7]
                ))

        pages.append(PageData(
            page_number=page_idx + 1,
            width=round(rect.width, 2),
            height=round(rect.height, 2),
            text=page_text,
            words=words
        ))

    combined_text = "\n".join(full_text)
    doc_type = detect_document_type(combined_text)

    record = DocumentRecord(
        id=f"doc_{uuid.uuid4().hex[:12]}",
        application_id=application_id,
        filename=filename,
        document_type=doc_type,
        sha256_hash=sha256_hash,
        file_path=storage_path,
        page_count=page_count,
        metadata=doc_metadata,
        created_at=datetime.now(timezone.utc).isoformat()
    )

    doc.close()
    return record, pages
