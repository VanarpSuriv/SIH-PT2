import sys
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class DocumentType(str, Enum):
    APPLICATION_FORM = "application_form"
    APPROVAL_LETTER = "approval_letter"
    LAND_DOCUMENT = "land_document"
    FIRE_NOC = "fire_noc"
    FACULTY_LIST = "faculty_list"
    UNKNOWN = "unknown"

class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"

class FindingStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    FLAGGED = "FLAGGED"
    MANUAL_REVIEW = "MANUAL_REVIEW"

class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    MISMATCH = "mismatch"
    EXPIRED = "expired"
    PENDING = "pending"
    SOURCE_UNAVAILABLE = "source unavailable"
    MANUAL_REVIEW = "manual review"

class BoundingBox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float

class ExtractedWord(BaseModel):
    text: str
    bbox: List[float] # [x0, y0, x1, y1]
    block_no: int = 0
    line_no: int = 0
    word_no: int = 0

class PageData(BaseModel):
    page_number: int # 1-indexed
    width: float
    height: float
    text: str
    words: List[ExtractedWord] = []

class DocumentMetadata(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    creator: Optional[str] = None
    producer: Optional[str] = None
    creation_date: Optional[str] = None
    mod_date: Optional[str] = None
    is_signed: bool = False
    signature_details: Optional[Dict[str, Any]] = None

class DocumentRecord(BaseModel):
    id: str
    application_id: str
    filename: str
    document_type: DocumentType
    sha256_hash: str
    file_path: str
    page_count: int
    metadata: DocumentMetadata
    created_at: str

class ExtractedField(BaseModel):
    name: str
    value: Any
    raw_text: str
    document_type: DocumentType
    document_id: Optional[str] = None
    page_number: int = 1
    bbox: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0]) # [x0, y0, x1, y1]
    confidence: float = 1.0

class VerificationResult(BaseModel):
    issuer: str
    record_id: str
    status: VerificationStatus
    source: str = "SIMULATED"
    message: str
    verified_data: Optional[Dict[str, Any]] = None

class Finding(BaseModel):
    id: str
    application_id: str
    rule_id: str
    rule_version: str = "1.0"
    rule_name: str
    severity: Severity
    status: FindingStatus
    claim: str
    description: str
    fields_involved: List[ExtractedField] = []
    verification_result: Optional[VerificationResult] = None
    user_status: str = "UNREVIEWED" # UNREVIEWED, CONFIRMED, DISMISSED
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class AuditEvent(BaseModel):
    id: str
    timestamp: str
    application_id: str
    action: str
    payload: Dict[str, Any]
    prev_hash: str
    hash: str

class ApplicationCase(BaseModel):
    id: str
    institution_name: str
    application_date: str
    status: str = "PENDING"
    documents: List[DocumentRecord] = []
    findings: List[Finding] = []
    created_at: str
