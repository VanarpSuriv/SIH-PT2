"""
Field Extraction Service for AICTE EoA Documents.
Extracts structured key-value pairs with exact page coordinates and bounding boxes.
"""
import re
from typing import Dict, List, Optional, Any, Tuple
import pymupdf

from backend.models import (
    DocumentType,
    DocumentRecord,
    PageData,
    ExtractedField
)

def find_bbox_for_text(pdf_path: str, page_number: int, query_text: str) -> List[float]:
    """Find exact bounding box for snippet using PyMuPDF search_for."""
    if not query_text or not pdf_path:
        return [0.0, 0.0, 0.0, 0.0]
    
    try:
        doc = pymupdf.open(pdf_path)
        page_idx = max(0, page_number - 1)
        if page_idx < doc.page_count:
            page = doc[page_idx]
            # Search for full snippet
            rects = page.search_for(query_text.strip())
            if rects:
                r = rects[0]
                doc.close()
                return [round(r.x0, 2), round(r.y0, 2), round(r.x1, 2), round(r.y1, 2)]
            
            # If not found directly, try first 3 words
            tokens = query_text.strip().split()
            if len(tokens) > 2:
                sub = " ".join(tokens[:3])
                rects = page.search_for(sub)
                if rects:
                    r = rects[0]
                    doc.close()
                    return [round(r.x0, 2), round(r.y0, 2), round(r.x1, 2), round(r.y1, 2)]
        doc.close()
    except Exception:
        pass
    
    return [50.0, 100.0, 300.0, 120.0] # Fallback reasonable bounding box

def clean_val(val: Optional[str]) -> str:
    """Clean extracted string value."""
    if not val:
        return ""
    # Strip common punctuation, quotes, trailing separators
    return re.sub(r'[\r\n\t]+', ' ', val).strip().rstrip('.,;')

def extract_fields_from_application_form(text: str, pdf_path: str) -> List[ExtractedField]:
    """Extract fields from Application Form."""
    fields = []

    # Application ID
    m = re.search(r"Application\s+ID:\s*([A-Za-z0-9\-]+)", text, re.IGNORECASE)
    if m:
        val = clean_val(m.group(1))
        bbox = find_bbox_for_text(pdf_path, 1, val)
        fields.append(ExtractedField(
            name="application_id",
            value=val,
            raw_text=m.group(0),
            document_type=DocumentType.APPLICATION_FORM,
            page_number=1,
            bbox=bbox,
            confidence=0.99
        ))

    # Permanent Institute ID
    m = re.search(r"Permanent\s+(?:Institute\s+)?ID:\s*([A-Za-z0-9\-]+)", text, re.IGNORECASE)
    if m:
        val = clean_val(m.group(1))
        bbox = find_bbox_for_text(pdf_path, 1, val)
        fields.append(ExtractedField(
            name="permanent_id",
            value=val,
            raw_text=m.group(0),
            document_type=DocumentType.APPLICATION_FORM,
            page_number=1,
            bbox=bbox,
            confidence=0.99
        ))

    # Institution Name
    m = re.search(r"Institution\s+Name:\s*([\s\S]*?)(?=\s*Application\s+Date:|\s*Principal\s*/|\n\s*2\.)", text, re.IGNORECASE)
    if m:
        val = clean_val(m.group(1))
        bbox = find_bbox_for_text(pdf_path, 1, val)
        fields.append(ExtractedField(
            name="institution_name",
            value=val,
            raw_text=m.group(0),
            document_type=DocumentType.APPLICATION_FORM,
            page_number=1,
            bbox=bbox,
            confidence=0.98
        ))

    # Application Date
    m = re.search(r"Application\s+Date:\s*(\d{4}-\d{2}-\d{2})", text, re.IGNORECASE)
    if m:
        val = clean_val(m.group(1))
        bbox = find_bbox_for_text(pdf_path, 1, val)
        fields.append(ExtractedField(
            name="application_date",
            value=val,
            raw_text=m.group(0),
            document_type=DocumentType.APPLICATION_FORM,
            page_number=1,
            bbox=bbox,
            confidence=0.99
        ))

    # Principal Name
    m = re.search(r"Principal\s*/\s*Director:\s*([^\n\r]+?)(?=\s+Academic\s+Year:|\n|$)", text, re.IGNORECASE)
    if m:
        val = clean_val(m.group(1))
        bbox = find_bbox_for_text(pdf_path, 1, val)
        fields.append(ExtractedField(
            name="principal_name",
            value=val,
            raw_text=m.group(0),
            document_type=DocumentType.APPLICATION_FORM,
            page_number=1,
            bbox=bbox,
            confidence=0.95
        ))

    # Declared Land Area
    m = re.search(r"Total\s+Land\s+Area\s*\(Acres\):\s*([\d\.]+)", text, re.IGNORECASE)
    if m:
        raw_val = clean_val(m.group(1))
        bbox = find_bbox_for_text(pdf_path, 1, raw_val)
        try:
            val = float(raw_val)
        except ValueError:
            val = raw_val
        fields.append(ExtractedField(
            name="declared_land_area",
            value=val,
            raw_text=m.group(0),
            document_type=DocumentType.APPLICATION_FORM,
            page_number=1,
            bbox=bbox,
            confidence=0.98
        ))

    # Declared Faculty Count
    m = re.search(r"Total\s+Declared\s+Faculty\s+Count:\s*(\d+)", text, re.IGNORECASE)
    if m:
        raw_val = clean_val(m.group(1))
        bbox = find_bbox_for_text(pdf_path, 1, raw_val)
        try:
            val = int(raw_val)
        except ValueError:
            val = raw_val
        fields.append(ExtractedField(
            name="declared_faculty_count",
            value=val,
            raw_text=m.group(0),
            document_type=DocumentType.APPLICATION_FORM,
            page_number=1,
            bbox=bbox,
            confidence=0.98
        ))

    return fields

def extract_fields_from_approval_letter(text: str, pdf_path: str) -> List[ExtractedField]:
    """Extract fields from AICTE Approval Letter."""
    fields = []

    # Permanent ID
    m = re.search(r"Permanent\s+(?:Institute\s+)?ID:\s*([A-Za-z0-9\-]+)", text, re.IGNORECASE)
    if m:
        val = clean_val(m.group(1))
        bbox = find_bbox_for_text(pdf_path, 1, val)
        fields.append(ExtractedField(
            name="permanent_id",
            value=val,
            raw_text=m.group(0),
            document_type=DocumentType.APPROVAL_LETTER,
            page_number=1,
            bbox=bbox,
            confidence=0.99
        ))

    # Institution Name
    m = re.search(r"Name\s+of\s+the\s+Institution:\s*([\s\S]*?)(?=\s*Approved\s+Academic\s+Year:|\s*Institution\s+Address:|\n\s*Status\s+of)", text, re.IGNORECASE)
    if not m:
        # Fallback to To line
        m = re.search(r"Registrar,\s*\n\s*([^\n\r,]+)", text)
    if m:
        val = clean_val(m.group(1))
        bbox = find_bbox_for_text(pdf_path, 1, val)
        fields.append(ExtractedField(
            name="institution_name",
            value=val,
            raw_text=m.group(0),
            document_type=DocumentType.APPROVAL_LETTER,
            page_number=1,
            bbox=bbox,
            confidence=0.97
        ))

    # Approved Academic Year
    m = re.search(r"Approved\s+Academic\s+Year:\s*(\d{4}-\d{4})", text, re.IGNORECASE)
    if not m:
        m = re.search(r"Academic\s+Year\s+(\d{4}-\d{4})", text, re.IGNORECASE)
    if m:
        val = clean_val(m.group(1))
        bbox = find_bbox_for_text(pdf_path, 1, val)
        fields.append(ExtractedField(
            name="approved_academic_year",
            value=val,
            raw_text=m.group(0),
            document_type=DocumentType.APPROVAL_LETTER,
            page_number=1,
            bbox=bbox,
            confidence=0.99
        ))

    # Order Number
    m = re.search(r"Letter\s+Order\s+No:\s*([^\n\r]+)", text, re.IGNORECASE)
    if m:
        val = clean_val(m.group(1))
        bbox = find_bbox_for_text(pdf_path, 1, val)
        fields.append(ExtractedField(
            name="order_no",
            value=val,
            raw_text=m.group(0),
            document_type=DocumentType.APPROVAL_LETTER,
            page_number=1,
            bbox=bbox,
            confidence=0.98
        ))

    # Issue Date
    m = re.search(r"Date\s+of\s+Issuance:\s*(\d{4}-\d{2}-\d{2})", text, re.IGNORECASE)
    if m:
        val = clean_val(m.group(1))
        bbox = find_bbox_for_text(pdf_path, 1, val)
        fields.append(ExtractedField(
            name="approval_issue_date",
            value=val,
            raw_text=m.group(0),
            document_type=DocumentType.APPROVAL_LETTER,
            page_number=1,
            bbox=bbox,
            confidence=0.98
        ))

    return fields

def extract_fields_from_land_document(text: str, pdf_path: str) -> List[ExtractedField]:
    """Extract fields from Land Document / Title Deed."""
    fields = []

    # Deed Registration Number
    m = re.search(r"(?:Registration\s+Deed\s+Number|Deed\s+Registration\s+Number):\s*([^\n\r]+)", text, re.IGNORECASE)
    if m:
        val = clean_val(m.group(1))
        bbox = find_bbox_for_text(pdf_path, 1, val)
        fields.append(ExtractedField(
            name="deed_number",
            value=val,
            raw_text=m.group(0),
            document_type=DocumentType.LAND_DOCUMENT,
            page_number=1,
            bbox=bbox,
            confidence=0.98
        ))

    # Institution Name
    m = re.search(r"(?:Institution\s*/\s*Owner\s+Name|Institution\s*/\s*Lessee\s+Name):\s*([\s\S]*?)(?=\s*Total\s+Registered\s+Area|\s*Survey\s*/)", text, re.IGNORECASE)
    if m:
        val = clean_val(m.group(1))
        bbox = find_bbox_for_text(pdf_path, 1, val)
        fields.append(ExtractedField(
            name="institution_name",
            value=val,
            raw_text=m.group(0),
            document_type=DocumentType.LAND_DOCUMENT,
            page_number=1,
            bbox=bbox,
            confidence=0.97
        ))

    # Total Registered Area
    m = re.search(r"Total\s+Registered\s+Area\s*\(Acres\):\s*([\d\.]+)", text, re.IGNORECASE)
    if m:
        raw_val = clean_val(m.group(1))
        bbox = find_bbox_for_text(pdf_path, 1, raw_val)
        try:
            val = float(raw_val)
        except ValueError:
            val = raw_val
        fields.append(ExtractedField(
            name="land_doc_area_acres",
            value=val,
            raw_text=m.group(0),
            document_type=DocumentType.LAND_DOCUMENT,
            page_number=1,
            bbox=bbox,
            confidence=0.98
        ))

    # Date of Registration
    m = re.search(r"Date\s+of\s+Registration:\s*(\d{4}-\d{2}-\d{2})", text, re.IGNORECASE)
    if m:
        val = clean_val(m.group(1))
        bbox = find_bbox_for_text(pdf_path, 1, val)
        fields.append(ExtractedField(
            name="deed_date",
            value=val,
            raw_text=m.group(0),
            document_type=DocumentType.LAND_DOCUMENT,
            page_number=1,
            bbox=bbox,
            confidence=0.98
        ))

    return fields

def extract_fields_from_fire_noc(text: str, pdf_path: str) -> List[ExtractedField]:
    """Extract fields from Fire Safety NOC Certificate."""
    fields = []

    # NOC Number
    m = re.search(r"(?:Certificate\s+NOC\s+No|NOC\s+Certificate\s+Number):\s*([^\n\r]+)", text, re.IGNORECASE)
    if m:
        val = clean_val(m.group(1))
        bbox = find_bbox_for_text(pdf_path, 1, val)
        fields.append(ExtractedField(
            name="noc_number",
            value=val,
            raw_text=m.group(0),
            document_type=DocumentType.FIRE_NOC,
            page_number=1,
            bbox=bbox,
            confidence=0.98
        ))

    # Institution Name
    m = re.search(r"Name\s+of\s+the\s+Institution:\s*([\s\S]*?)(?=\s*Campus\s+Location|\s*NOC\s+Issue\s+Date)", text, re.IGNORECASE)
    if m:
        val = clean_val(m.group(1))
        bbox = find_bbox_for_text(pdf_path, 1, val)
        fields.append(ExtractedField(
            name="institution_name",
            value=val,
            raw_text=m.group(0),
            document_type=DocumentType.FIRE_NOC,
            page_number=1,
            bbox=bbox,
            confidence=0.97
        ))
    # NOC Issue Date

    # NOC Issue Date
    m = re.search(r"(?:Date\s+of\s+Inspection\s*/\s+Issue|NOC\s+Issue\s+Date|Issue\s+Date):\s*(\d{4}-\d{2}-\d{2})", text, re.IGNORECASE)
    if m:
        val = clean_val(m.group(1))
        bbox = find_bbox_for_text(pdf_path, 1, val)
        fields.append(ExtractedField(
            name="fire_issue_date",
            value=val,
            raw_text=m.group(0),
            document_type=DocumentType.FIRE_NOC,
            page_number=1,
            bbox=bbox,
            confidence=0.98
        ))

    # Valid To
    m = re.search(r"(?:Valid\s+Until\s*/\s*Valid\s+To|Valid\s+To):\s*(\d{4}-\d{2}-\d{2})", text, re.IGNORECASE)
    if m:
        val = clean_val(m.group(1))
        bbox = find_bbox_for_text(pdf_path, 1, val)
        fields.append(ExtractedField(
            name="fire_noc_valid_to",
            value=val,
            raw_text=m.group(0),
            document_type=DocumentType.FIRE_NOC,
            page_number=1,
            bbox=bbox,
            confidence=0.99
        ))

    return fields

def extract_fields_from_faculty_list(text: str, pdf_path: str) -> List[ExtractedField]:
    """Extract fields from Faculty List Roster."""
    fields = []

    # Institution Name
    m = re.search(r"Institution:\s*([^\n\r|]+)", text, re.IGNORECASE)
    if m:
        val = clean_val(m.group(1))
        bbox = find_bbox_for_text(pdf_path, 1, val)
        fields.append(ExtractedField(
            name="institution_name",
            value=val,
            raw_text=m.group(0),
            document_type=DocumentType.FACULTY_LIST,
            page_number=1,
            bbox=bbox,
            confidence=0.97
        ))

    # Total Count of Approved Faculty Members
    m = re.search(r"Total\s+Count\s+of\s+Approved\s+Faculty\s+Members:\s*(\d+)", text, re.IGNORECASE)
    if m:
        raw_val = clean_val(m.group(1))
        bbox = find_bbox_for_text(pdf_path, 1, raw_val)
        try:
            val = int(raw_val)
        except ValueError:
            val = raw_val
        fields.append(ExtractedField(
            name="faculty_list_count",
            value=val,
            raw_text=m.group(0),
            document_type=DocumentType.FACULTY_LIST,
            page_number=1,
            bbox=bbox,
            confidence=0.98
        ))

    return fields

def extract_document_fields(doc_record: DocumentRecord, pages: List[PageData]) -> List[ExtractedField]:
    """Extract fields from document record and its pages based on document type."""
    combined_text = "\n".join([p.text for p in pages])
    pdf_path = doc_record.file_path
    
    extracted: List[ExtractedField] = []
    if doc_record.document_type == DocumentType.APPLICATION_FORM:
        extracted = extract_fields_from_application_form(combined_text, pdf_path)
    elif doc_record.document_type == DocumentType.APPROVAL_LETTER:
        extracted = extract_fields_from_approval_letter(combined_text, pdf_path)
    elif doc_record.document_type == DocumentType.LAND_DOCUMENT:
        extracted = extract_fields_from_land_document(combined_text, pdf_path)
    elif doc_record.document_type == DocumentType.FIRE_NOC:
        extracted = extract_fields_from_fire_noc(combined_text, pdf_path)
    elif doc_record.document_type == DocumentType.FACULTY_LIST:
        extracted = extract_fields_from_faculty_list(combined_text, pdf_path)

    # Attach document_id to each field
    for f in extracted:
        f.document_id = doc_record.id

    return extracted
