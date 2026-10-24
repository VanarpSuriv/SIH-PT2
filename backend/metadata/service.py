"""
Dedicated PDF Metadata Extraction and Normalization Service.
Extracts Creator, Producer, CreationDate, ModDate, PDF version, encryption status,
page count, SHA-256 digest, and surface parsing warnings.
"""
import hashlib
import re
import datetime
from typing import Dict, List, Optional, Tuple, Any
import pymupdf

from backend.models import DocumentMetadata

def compute_sha256(data: bytes) -> str:
    """Compute SHA-256 cryptographic digest of raw binary content."""
    hasher = hashlib.sha256()
    hasher.update(data)
    return hasher.hexdigest()

def parse_pdf_date(date_str: Optional[str]) -> Tuple[Optional[str], List[str]]:
    """
    Parse and normalize ASN.1 / PDF-1.7 date strings to standard ISO-8601 with timezone.
    Standard PDF format: D:YYYYMMDDHHmmSSOHH'mm'
    Returns (iso_string, list_of_warnings).
    """
    if not date_str or not isinstance(date_str, str):
        return None, []

    warnings: List[str] = []
    cleaned = date_str.strip()

    # Check if input is standard ISO format rather than PDF ASN.1 format
    if "T" in cleaned or ("-" in cleaned and not cleaned.startswith("D:")):
        try:
            iso_dt = datetime.datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
            if iso_dt.tzinfo is None:
                iso_dt = iso_dt.replace(tzinfo=datetime.timezone.utc)
            return iso_dt.isoformat(), warnings
        except Exception:
            pass

    if cleaned.startswith("D:"):
        cleaned = cleaned[2:]

    # Match standard PDF date components strictly (digits for date parts, followed by timezone)
    pattern = r"^(\d{4})(?:(\d{2})(?:(\d{2})(?:(\d{2})(?:(\d{2})(?:(\d{2}))?)?)?)?)?([+\-Z])?(?:(\d{2})\'?(\d{2})\'?)?$"
    match = re.match(pattern, cleaned)
    if not match:
        return None, [f"Malformed PDF date syntax: '{date_str}'"]

    try:
        year = int(match.group(1))
        month = int(match.group(2) or 1)
        day = int(match.group(3) or 1)
        hour = int(match.group(4) or 0)
        minute = int(match.group(5) or 0)
        second = int(match.group(6) or 0)
        tz_sign = match.group(7)
        tz_hour = int(match.group(8) or 0)
        tz_min = int(match.group(9) or 0)

        # Validate month and day bounds
        if month < 1 or month > 12:
            return None, [f"Invalid month component ({month}) in '{date_str}'"]
        if day < 1 or day > 31:
            return None, [f"Invalid day component ({day}) in '{date_str}'"]

        if tz_sign == "Z":
            tz = datetime.timezone.utc
        elif tz_sign == "+":
            tz = datetime.timezone(datetime.timedelta(hours=tz_hour, minutes=tz_min))
        elif tz_sign == "-":
            tz = datetime.timezone(-datetime.timedelta(hours=tz_hour, minutes=tz_min))
        else:
            tz = datetime.timezone.utc
            warnings.append("Missing timezone indicator in PDF date string; assumed UTC (+00:00)")

        dt = datetime.datetime(year, month, day, hour, minute, second, tzinfo=tz)
        return dt.isoformat(), warnings
    except ValueError as ve:
        return None, [f"Date conversion error for '{date_str}': {str(ve)}"]
    except Exception as e:
        return None, [f"Unexpected error parsing date '{date_str}': {str(e)}"]

def extract_pdf_metadata(file_bytes: bytes, filename: str) -> DocumentMetadata:
    """
    Extract comprehensive metadata, version, encryption, and parsing warnings from a PDF file.
    Does not assume document authenticity or classify anomalies as proof of forgery.
    """
    sha256_hash = compute_sha256(file_bytes)
    parsing_warnings: List[str] = []
    metadata_anomalies: List[str] = []

    try:
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
    except Exception as e:
        parsing_warnings.append(f"PyMuPDF failed to parse document structure: {str(e)}")
        return DocumentMetadata(
            title=filename,
            sha256_hash=sha256_hash,
            parsing_warnings=parsing_warnings,
            metadata_anomalies=["CORRUPTED_PDF_HEADER"]
        )

    meta_raw = doc.metadata or {}
    page_count = doc.page_count
    is_encrypted = bool(doc.is_encrypted)
    pdf_version = meta_raw.get("format") or "PDF 1.4"

    # Extract raw metadata fields
    title = meta_raw.get("title") or filename
    author = meta_raw.get("author")
    creator = meta_raw.get("creator")
    producer = meta_raw.get("producer")

    raw_creation = meta_raw.get("creationDate")
    raw_mod = meta_raw.get("modDate")

    # Clean empty strings
    if creator and creator.strip() in ["", "(unspecified)", "(anonymous)"]:
        creator = None
    if producer and producer.strip() in ["", "(unspecified)", "(anonymous)"]:
        producer = None

    # Parse and normalize dates
    norm_creation, creation_warns = parse_pdf_date(raw_creation)
    norm_mod, mod_warns = parse_pdf_date(raw_mod)

    parsing_warnings.extend(creation_warns)
    parsing_warnings.extend(mod_warns)

    # Detect metadata-level sequence anomalies
    if norm_creation and norm_mod:
        try:
            dt_create = datetime.datetime.fromisoformat(norm_creation)
            dt_mod = datetime.datetime.fromisoformat(norm_mod)
            # Flag if ModDate precedes CreationDate by more than 1 second (to account for subsecond rounding)
            delta_seconds = (dt_mod - dt_create).total_seconds()
            if delta_seconds < -1.0:
                metadata_anomalies.append("MOD_DATE_PRECEDES_CREATION_DATE")
        except Exception:
            pass

    # Signature presence inspection
    sigflags = 0
    is_signed = False
    try:
        sigflags = doc.get_sigflags()
        is_signed = (sigflags > 0)
    except Exception:
        is_signed = False

    sig_details = {"sigflags": sigflags} if is_signed else None

    doc.close()

    return DocumentMetadata(
        title=title,
        author=author,
        creator=creator,
        producer=producer,
        raw_creation_date=raw_creation,
        normalized_creation_date=norm_creation,
        raw_mod_date=raw_mod,
        normalized_mod_date=norm_mod,
        creation_date=norm_creation or raw_creation,
        mod_date=norm_mod or raw_mod,
        pdf_version=pdf_version,
        is_encrypted=is_encrypted,
        page_count=page_count,
        sha256_hash=sha256_hash,
        parsing_warnings=parsing_warnings,
        metadata_anomalies=metadata_anomalies,
        is_signed=is_signed,
        signature_details=sig_details
    )
