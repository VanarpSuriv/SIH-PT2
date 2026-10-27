"""
FastAPI Backend Application for AICTE EoA Document Verification.
Provides endpoints for Upload, Ingest, Extraction, Rules, Verification Adapter, Audit Trail, and Server-side Highlighting.
"""
import os
import uuid
import json
import logging
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, Response, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pymupdf

from backend.models import (
    DocumentType,
    DocumentRecord,
    DocumentForensicsResult,
    ExtractedField,
    Finding,
    FindingStatus,
    Severity,
    RuleCategory,
    FindingLifecycle,
    ReviewDecision,
    HumanReviewDecision,
    MetadataEvidenceContext,
    ApplicationCase,
    VerificationResult,
    VerificationStatus
)
from backend.ingest.service import extract_pdf_data
from backend.extract.service import extract_document_fields
from backend.rules.engine import RulesEngine
from backend.verify.adapter import get_verification_adapter, verify
from backend.audit.trail import get_audit_trail
from backend.signature.verifier import SignatureVerifier
from backend.forensics.engine import analyze_document_forensics

# Setup structured logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("aicte_eoa_backend")

app = FastAPI(
    title="AICTE EoA Document Verification Platform",
    description="Automated regulatory document verification, evidence graphing, rules engine, and tamper-evident audit log.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Upload validation limits
import secrets

MAX_UPLOAD_BYTES = 15 * 1024 * 1024  # 15 MB
ALLOWED_EXTENSIONS = {".pdf"}
PDF_MAGIC_BYTES = b"%PDF-"
ENABLE_DEMO_TAMPER = os.getenv("ENABLE_DEMO_TAMPER", "false").lower() in ("true", "1", "yes")

VALID_OFFICER_ROLES = {"OFFICER", "SCRUTINY_COMMITTEE", "AICTE_ADMIN", "REGIONAL_OFFICER", "INSPECTOR", "REVIEWER"}
REVOKED_TOKENS = {"veritas-officer-token-auth-2025", "test-valid-officer-token-12345"}

def get_configured_officer_token() -> Optional[str]:
    """Retrieve officer authorization token from environment. Fails closed with no hardcoded fallback."""
    raw = os.getenv("OFFICER_AUTH_TOKEN")
    if raw and raw.strip():
        token_val = raw.strip()
        if token_val in REVOKED_TOKENS:
            logger.error(f"Configured OFFICER_AUTH_TOKEN is a known revoked token: {token_val}")
            return None
        return token_val
    return None

def verify_officer_authorization(
    response: Response,
    authorization: Optional[str] = Header(None),
    x_officer_role: Optional[str] = Header(None),
    x_officer_token: Optional[str] = Header(None)
):
    """
    Server-verified authentication and role authorization guard for officer review actions.
    Fails closed if OFFICER_AUTH_TOKEN is not configured on the server.
    Rejects client-asserted X-Officer-Role headers without server token verification.
    Labels shared demo token authentication explicitly in response headers.
    """
    configured_token = get_configured_officer_token()
    if not configured_token:
        raise HTTPException(
            status_code=500,
            detail="Server Security Configuration Error: OFFICER_AUTH_TOKEN environment variable is unconfigured or revoked. System fails closed."
        )

    # 1. Extract bearer or custom token from client
    client_token = None
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() in ("bearer", "apikey"):
            client_token = parts[1]
        elif len(parts) == 1:
            client_token = parts[0]
    elif x_officer_token:
        client_token = x_officer_token.strip()

    # 2. Reject unauthenticated attempts (even if client asserts X-Officer-Role)
    if not client_token:
        raise HTTPException(
            status_code=401,
            detail="Authentication Required: Missing server-verified officer credentials. Client-asserted X-Officer-Role headers without server token are rejected."
        )

    # 3. Constant-time token verification against configured secret
    if not secrets.compare_digest(client_token, configured_token):
        raise HTTPException(
            status_code=401,
            detail="Invalid officer authentication credentials: token verification failed or token has been revoked."
        )

    # 4. Role authorization
    role = (x_officer_role or "OFFICER").strip().upper()
    if role not in VALID_OFFICER_ROLES:
        raise HTTPException(
            status_code=403,
            detail=f"Access Denied: Role '{role}' is not authorized to submit regulatory compliance determinations."
        )

    # 5. Label demo shared token mechanism in response header
    response.headers["X-Auth-Mode"] = "DEMO_SHARED_TOKEN"
    response.headers["X-Officer-Verified-Role"] = role

    return {"authenticated": True, "role": role, "auth_mode": "DEMO_SHARED_TOKEN"}

# In-memory application store (backed by uploaded file storage on disk)
UPLOAD_STORAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "storage")
os.makedirs(UPLOAD_STORAGE_DIR, exist_ok=True)

applications_db: Dict[str, ApplicationCase] = {}
findings_db: Dict[str, Finding] = {}
forensics_db: Dict[str, DocumentForensicsResult] = {}
rules_engine = RulesEngine()
audit_trail = get_audit_trail()
verification_adapter = get_verification_adapter()

def process_application_documents(
    application_id: str,
    institution_name: str,
    doc_tuples: List[tuple[str, bytes]]
) -> ApplicationCase:
    """Core pipeline: Ingest -> Extract -> Forensics -> Verify External Issuers -> Rules Engine -> Audit Trail."""
    docs: List[DocumentRecord] = []
    all_fields: List[ExtractedField] = []
    app_date = "2025-03-15"

    storage_root = Path(UPLOAD_STORAGE_DIR).resolve()
    for filename, file_bytes in doc_tuples:
        target_path_obj = (storage_root / application_id / filename).resolve()
        if not target_path_obj.is_relative_to(storage_root):
            raise HTTPException(status_code=400, detail="Path traversal attempt detected in document path.")
        target_path = str(target_path_obj)
        doc_record, pages = extract_pdf_data(file_bytes, filename, application_id, target_path)
        docs.append(doc_record)
        
        # Field Extraction
        fields = extract_document_fields(doc_record, pages)
        all_fields.extend(fields)

        # Computer Vision Forensics (ELA, SRM, Copy-Move, Typography, Quality)
        try:
            forensics_res = analyze_document_forensics(file_bytes, pages, filename, doc_record.id, application_id)
            forensics_db[doc_record.id] = forensics_res
        except Exception as f_err:
            logger.error(f"Error during forensics analysis of {filename}: {f_err}")

        # Log ingest to audit trail
        audit_trail.log_event(
            application_id=application_id,
            action="DOCUMENT_INGESTED",
            payload={
                "document_id": doc_record.id,
                "filename": filename,
                "document_type": doc_record.document_type.value,
                "sha256_hash": doc_record.sha256_hash,
                "page_count": doc_record.page_count
            }
        )

    # Determine institution name from application form if available
    for fld in all_fields:
        if fld.document_type == DocumentType.APPLICATION_FORM and fld.name == "institution_name":
            institution_name = str(fld.value)
        if fld.document_type == DocumentType.APPLICATION_FORM and fld.name == "application_date":
            app_date = str(fld.value)

    # Rules Engine evaluation with forensics integration
    findings = rules_engine.evaluate(application_id, docs, all_fields, forensics_map=forensics_db)

    # Enrich findings with external registry verification
    for f in findings:
        findings_db[f.id] = f

        # If finding involves permanent_id or fire NOC, query verification adapter
        for fld in f.fields_involved:
            if fld.name == "permanent_id":
                res = verify("AICTE_CENTRAL_PORTAL", str(fld.value))
                f.verification_result = res
                audit_trail.log_event(
                    application_id=application_id,
                    action="ISSUER_VERIFIED",
                    payload={"finding_id": f.id, "issuer": res.issuer, "id": res.record_id, "status": res.status.value}
                )
                break
            elif fld.name == "noc_number" or f.rule_id == "AICTE-EOA-005":
                # Check fire noc
                res = verify("STATE_FIRE_SERVICES_PORTAL", str(fld.value) if fld.name == "noc_number" else "FNOC-REG")
                f.verification_result = res
                audit_trail.log_event(
                    application_id=application_id,
                    action="ISSUER_VERIFIED",
                    payload={"finding_id": f.id, "issuer": res.issuer, "id": res.record_id, "status": res.status.value}
                )
                break

    # Determine overall status
    has_fail = any(f.status == FindingStatus.FAIL for f in findings)
    app_status = "ACTION_REQUIRED" if has_fail else "VERIFIED_COMPLIANT"

    app_case = ApplicationCase(
        id=application_id,
        institution_name=institution_name,
        application_date=app_date,
        status=app_status,
        documents=docs,
        findings=findings,
        created_at=datetime.now(timezone.utc).isoformat()
    )
    applications_db[application_id] = app_case

    audit_trail.log_event(
        application_id=application_id,
        action="APPLICATION_EVALUATED",
        payload={
            "institution_name": institution_name,
            "document_count": len(docs),
            "findings_count": len(findings),
            "status": app_status
        }
    )

    return app_case

@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat(), "service": "aicte-eoa-verification"}

@app.get("/api/rules")
def get_regulatory_rules():
    """Retrieve all configured AICTE EoA compliance rules, categories, and handbook citations."""
    return rules_engine.rules_def

@app.get("/api/cases")
def list_synthetic_cases():
    """List available synthetic test cases with ground truth planted defects."""
    cases_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "synthetic", "cases")
    if not os.path.exists(cases_dir):
        return []

    case_items = []
    for item in sorted(os.listdir(cases_dir)):
        case_path = os.path.join(cases_dir, item)
        truth_file = os.path.join(case_path, "truth.json")
        if os.path.isdir(case_path) and os.path.exists(truth_file):
            with open(truth_file, "r", encoding="utf-8") as f:
                truth_data = json.load(f)
            case_items.append(truth_data)
    return case_items

@app.post("/api/cases/{case_id}/load")
def load_synthetic_case(case_id: str):
    """Load and process a synthetic test case directly from disk."""
    cases_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "synthetic", "cases")
    case_path = os.path.join(cases_dir, case_id)
    truth_file = os.path.join(case_path, "truth.json")

    if not os.path.exists(case_path) or not os.path.exists(truth_file):
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")

    with open(truth_file, "r", encoding="utf-8") as f:
        truth_data = json.load(f)

    doc_tuples = []
    for fname in truth_data.get("generated_files", []):
        fpath = os.path.join(case_path, fname)
        if os.path.exists(fpath):
            with open(fpath, "rb") as f:
                doc_tuples.append((fname, f.read()))

    app_id = f"APP-{case_id.upper()}-{uuid.uuid4().hex[:6]}"
    app_case = process_application_documents(
        application_id=app_id,
        institution_name=truth_data.get("institution_name", "Technical Institution"),
        doc_tuples=doc_tuples
    )
    return app_case

@app.post("/api/upload")
async def upload_documents(
    institution_name: str = Form("Institutional Applicant"),
    files: List[UploadFile] = File(...)
):
    """
    Upload PDF documents for automated AICTE verification.
    Applies strict file-type validation, size limits (15MB), magic-byte inspection, and safe storage paths.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    app_id = f"APP-{uuid.uuid4().hex[:8].upper()}"
    doc_tuples = []

    for file in files:
        raw_name = file.filename or "uploaded_document.pdf"

        # 1. Extension validation
        ext = os.path.splitext(raw_name)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type for '{raw_name}'. Only PDF documents (.pdf) are permitted."
            )

        content = await file.read()

        # 2. Size boundary validation
        if len(content) == 0:
            raise HTTPException(status_code=400, detail=f"Uploaded file '{raw_name}' is empty (0 bytes).")
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File '{raw_name}' exceeds maximum permitted upload limit of 15MB ({len(content)} bytes)."
            )

        # 3. Magic header byte inspection
        if not content.startswith(PDF_MAGIC_BYTES):
            raise HTTPException(
                status_code=400,
                detail=f"File '{raw_name}' is not a valid PDF binary (missing '%PDF-' magic header bytes)."
            )

        # 4. Safe filename normalization to prevent path traversal
        base_name = os.path.basename(raw_name)
        safe_name = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", base_name)
        if not safe_name.lower().endswith(".pdf"):
            safe_name += ".pdf"

        # Explicit path boundary check to guarantee strict storage directory containment (following symlinks)
        storage_root = Path(UPLOAD_STORAGE_DIR).resolve()
        target_check_obj = (storage_root / app_id / safe_name).resolve()
        if not target_check_obj.is_relative_to(storage_root):
            raise HTTPException(status_code=400, detail="Path traversal attempt detected in filename.")

        doc_tuples.append((safe_name, content))

    app_case = process_application_documents(app_id, institution_name, doc_tuples)
    return app_case

@app.get("/api/applications")
def list_applications():
    """List all ingested applications with status."""
    return list(applications_db.values())

@app.get("/api/applications/{app_id}")
def get_application(app_id: str):
    """Retrieve full application details, documents, and findings."""
    app_case = applications_db.get(app_id)
    if not app_case:
        raise HTTPException(status_code=404, detail="Application not found.")
    return app_case

@app.get("/api/findings/{finding_id}")
def get_finding(finding_id: str):
    """Retrieve specific finding details."""
    finding = findings_db.get(finding_id)
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found.")
    return finding

@app.get("/api/findings/{finding_id}/evidence_image")
def render_evidence_highlight_image(finding_id: str, field_idx: int = Query(0)):
    """
    Server-side evidence highlighting with PyMuPDF.
    Draws highlighted bounding box on PDF page and returns PNG image bytes.
    """
    finding = findings_db.get(finding_id)
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found.")

    if not finding.fields_involved:
        # If completeness finding (e.g. document missing), return empty state indicator
        img_bytes = _generate_placeholder_image(f"Evidence Unavailable: Document Missing ({finding.claim})")
        return Response(content=img_bytes, media_type="image/png")

    idx = max(0, min(field_idx, len(finding.fields_involved) - 1))
    target_field = finding.fields_involved[idx]

    app_case = applications_db.get(finding.application_id)
    if not app_case:
        raise HTTPException(status_code=404, detail="Application case not found.")

    # Locate document record
    doc_rec = None
    if target_field.document_id:
        doc_rec = next((d for d in app_case.documents if d.id == target_field.document_id), None)
    if not doc_rec:
        doc_rec = next((d for d in app_case.documents if d.document_type == target_field.document_type), None)

    if not doc_rec or not os.path.exists(doc_rec.file_path):
        img_bytes = _generate_placeholder_image("Document file not available on disk")
        return Response(content=img_bytes, media_type="image/png")

    try:
        doc = pymupdf.open(doc_rec.file_path)
        page_idx = max(0, target_field.page_number - 1)
        if page_idx >= doc.page_count:
            page_idx = 0
        page = doc[page_idx]

        # Draw highlight on bbox
        bbox = target_field.bbox
        if bbox and len(bbox) == 4 and (bbox[2] > bbox[0]) and (bbox[3] > bbox[1]):
            # Padding around bounding box
            pad = 4.0
            rect = pymupdf.Rect(bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad)
            annot = page.add_rect_annot(rect)
            
            # Severity / Category color
            if finding.rule_category == RuleCategory.METADATA_INTEGRITY:
                annot.set_colors(stroke=(0.85, 0.45, 0.1), fill=(1.0, 0.95, 0.85))
            elif finding.rule_category == RuleCategory.FORENSIC_ADVISORY:
                annot.set_colors(stroke=(0.45, 0.2, 0.85), fill=(0.92, 0.90, 0.98))
            elif finding.severity == Severity.CRITICAL or finding.status == FindingStatus.FAIL:
                annot.set_colors(stroke=(0.85, 0.15, 0.15), fill=(1.0, 0.85, 0.85))
            else:
                annot.set_colors(stroke=(0.15, 0.55, 0.25), fill=(0.85, 0.95, 0.85))
            
            annot.set_border(width=2.0)
            annot.set_opacity(0.4)
            annot.update()

        # If metadata finding, add advisory header banner to page rendering
        if finding.metadata_context:
            banner_rect = pymupdf.Rect(20, 15, page.rect.width - 20, 60)
            page.draw_rect(banner_rect, color=(0.85, 0.45, 0.1), fill=(1.0, 0.96, 0.90), width=1.5)
            banner_text = (
                f"[ METADATA FORENSIC CONTEXT ] Rule: {finding.rule_id} ({finding.rule_name})\n"
                f"Advisory: Flagged for technical review; does not constitute proof of document forgery."
            )
            page.insert_textbox(banner_rect, banner_text, fontsize=8.5, color=(0.45, 0.2, 0.05), align=pymupdf.TEXT_ALIGN_CENTER)
        elif finding.rule_category == RuleCategory.FORENSIC_ADVISORY:
            banner_rect = pymupdf.Rect(20, 15, page.rect.width - 20, 60)
            page.draw_rect(banner_rect, color=(0.45, 0.2, 0.85), fill=(0.95, 0.93, 1.0), width=1.5)
            banner_text = (
                f"[ COMPUTER VISION FORENSIC ADVISORY ] Rule: {finding.rule_id} ({finding.rule_name})\n"
                f"Advisory: Algorithmic forensic signal for officer inspection; does not establish fraudulent intent."
            )
            page.insert_textbox(banner_rect, banner_text, fontsize=8.5, color=(0.25, 0.1, 0.5), align=pymupdf.TEXT_ALIGN_CENTER)

        pix = page.get_pixmap(dpi=130)
        img_bytes = pix.tobytes("png")
        doc.close()
        return Response(content=img_bytes, media_type="image/png")
    except Exception as e:
        logger.error(f"Error highlighting evidence: {e}")
        img_bytes = _generate_placeholder_image(f"Render Error: {str(e)}")
        return Response(content=img_bytes, media_type="image/png")

def _generate_placeholder_image(message: str) -> bytes:
    """Generate simple fallback image with text banner using PyMuPDF."""
    doc = pymupdf.open()
    page = doc.new_page(width=600, height=350)
    rect = pymupdf.Rect(50, 50, 550, 300)
    page.draw_rect(rect, color=(0.8, 0.8, 0.8), fill=(0.95, 0.95, 0.95))
    page.insert_textbox(rect, f"\n\n\n[ AICTE Evidence Graph ]\n\n{message}", fontsize=13, align=pymupdf.TEXT_ALIGN_CENTER)
    pix = page.get_pixmap(dpi=100)
    b = pix.tobytes("png")
    doc.close()
    return b

class ReviewRequest(BaseModel):
    decision: ReviewDecision
    reviewer_notes: str = ""
    reviewer_id: str = "OFFICER-AICTE-01"

@app.post("/api/findings/{finding_id}/review")
def submit_review_decision(
    finding_id: str,
    req: ReviewRequest,
    _auth: Any = Depends(verify_officer_authorization)
):
    """
    Submit structured human reviewer decision on a finding.
    Separates finding lifecycle, issuer-verification status, and reviewer decision.
    Enforces server-side authorization.
    """
    finding = findings_db.get(finding_id)
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found.")

    finding.review.decision = req.decision
    finding.review.reviewer_notes = req.reviewer_notes
    finding.review.reviewed_by = req.reviewer_id
    finding.review.reviewer_id = req.reviewer_id
    finding.review.reviewed_at = datetime.now(timezone.utc).isoformat()
    finding.review.decided_at = finding.review.reviewed_at

    if req.decision in (ReviewDecision.CONFIRMED_DEFECT, ReviewDecision.DISMISSED_BENIGN):
        finding.lifecycle = FindingLifecycle.RESOLVED
        finding.user_status = "CONFIRMED" if req.decision == ReviewDecision.CONFIRMED_DEFECT else "DISMISSED"
    elif req.decision == ReviewDecision.REQUEST_CLARIFICATION:
        finding.lifecycle = FindingLifecycle.IN_REVIEW
        finding.user_status = "IN_REVIEW"
    else:
        finding.lifecycle = FindingLifecycle.OPEN
        finding.user_status = "UNREVIEWED"

    event = audit_trail.log_event(
        application_id=finding.application_id,
        action="FINDING_REVIEWED",
        payload={
            "finding_id": finding.id,
            "rule_id": finding.rule_id,
            "claim": finding.claim,
            "decision": req.decision.value,
            "lifecycle": finding.lifecycle.value,
            "reviewer_notes": req.reviewer_notes,
            "reviewed_by": req.reviewer_id
        }
    )
    return {
        "status": "success",
        "finding_id": finding.id,
        "decision": req.decision.value,
        "lifecycle": finding.lifecycle.value,
        "audit_event_id": event.id
    }

@app.post("/api/findings/{finding_id}/confirm")
def confirm_finding(
    finding_id: str,
    reviewer_notes: str = Form(""),
    _auth: Any = Depends(verify_officer_authorization)
):
    """Reviewer confirms the flagged finding as an authentic violation."""
    finding = findings_db.get(finding_id)
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found.")

    finding.review.decision = ReviewDecision.CONFIRMED_DEFECT
    finding.review.reviewer_notes = reviewer_notes
    finding.review.reviewed_at = datetime.now(timezone.utc).isoformat()
    finding.lifecycle = FindingLifecycle.RESOLVED
    finding.user_status = "CONFIRMED"

    event = audit_trail.log_event(
        application_id=finding.application_id,
        action="FINDING_CONFIRMED",
        payload={
            "finding_id": finding.id,
            "rule_id": finding.rule_id,
            "claim": finding.claim,
            "decision": ReviewDecision.CONFIRMED_DEFECT.value,
            "lifecycle": FindingLifecycle.RESOLVED.value,
            "reviewer_notes": reviewer_notes
        }
    )
    return {"status": "success", "user_status": "CONFIRMED", "audit_event_id": event.id}

@app.post("/api/findings/{finding_id}/dismiss")
def dismiss_finding(
    finding_id: str,
    reviewer_notes: str = Form(""),
    _auth: Any = Depends(verify_officer_authorization)
):
    """Reviewer dismisses the finding with officer justification."""
    finding = findings_db.get(finding_id)
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found.")

    finding.review.decision = ReviewDecision.DISMISSED_BENIGN
    finding.review.reviewer_notes = reviewer_notes
    finding.review.reviewed_at = datetime.now(timezone.utc).isoformat()
    finding.lifecycle = FindingLifecycle.RESOLVED
    finding.user_status = "DISMISSED"

    event = audit_trail.log_event(
        application_id=finding.application_id,
        action="FINDING_DISMISSED",
        payload={
            "finding_id": finding.id,
            "rule_id": finding.rule_id,
            "claim": finding.claim,
            "decision": ReviewDecision.DISMISSED_BENIGN.value,
            "lifecycle": FindingLifecycle.RESOLVED.value,
            "reviewer_notes": reviewer_notes
        }
    )
    return {"status": "success", "user_status": "DISMISSED", "audit_event_id": event.id}

@app.get("/api/audit")
def get_audit_events(application_id: Optional[str] = Query(None)):
    """Fetch tamper-evident hash-chained audit events."""
    return audit_trail.get_events(application_id)

@app.get("/api/audit/verify")
def verify_audit_chain():
    """Verify integrity of the tamper-evident audit log hash chain."""
    return audit_trail.verify_chain()

@app.post("/api/audit/tamper")
def tamper_audit_row(
    event_id: str = Form(...),
    x_demo_mode: Optional[str] = Header(None),
    _auth: Any = Depends(verify_officer_authorization)
):
    """
    Tamper with an event row's payload for live demonstration of cryptographic tamper detection.
    Guarded for demo environments only: requires ENABLE_DEMO_TAMPER=true on server,
    valid officer authorization credentials, and explicit client header 'X-Demo-Mode: true'.
    """
    # Strictly disabled by default: Server environment MUST explicitly enable demo tamper mode
    if not ENABLE_DEMO_TAMPER:
        raise HTTPException(
            status_code=403,
            detail="Audit tampering is strictly disabled by default. Server must be configured with ENABLE_DEMO_TAMPER=true."
        )

    # In enabled demo environments, also require the explicit client demo header
    if not x_demo_mode or x_demo_mode.lower() not in ("true", "1", "yes"):
        raise HTTPException(
            status_code=403,
            detail="Audit tampering requires demonstration authorization header 'X-Demo-Mode: true'."
        )

    altered_payload = {
        "status": "ALTERED_BY_UNAUTHORIZED_ACTOR",
        "timestamp_manipulated": datetime.now(timezone.utc).isoformat(),
        "unauthorized_override": True
    }
    success = audit_trail.tamper_event_for_demo(event_id, altered_payload)
    if not success:
        raise HTTPException(status_code=404, detail="Audit event not found to tamper.")
    return {
        "status": "TAMPERED_FOR_DEMO",
        "tampered_event_id": event_id,
        "message": "Row payload altered directly in DB without updating SHA-256 hash. Call /api/audit/verify to see tamper detection."
    }

@app.get("/api/signature/check")
def check_pdf_signature(sample_type: str = Query("intact")):
    """
    Demonstrate digital signature verification outcomes:
    intact, modified (tampered), or untrusted signer.
    """
    sample_path = f"sample_{sample_type}.pdf"
    res = SignatureVerifier.verify_pdf(sample_path)
    res["source"] = "SIMULATED"
    return res

@app.get("/api/documents/{document_id}/forensics", response_model=DocumentForensicsResult)
def get_document_forensics(document_id: str):
    """
    Retrieve computer vision forensics (ELA heat map, SRM noise residual,
    copy-move duplication, typography consistency, scan quality) for a specific document.
    """
    res = forensics_db.get(document_id)
    if res:
        return res

    # If not in cache, locate document across known applications to compute on demand
    for app_case in applications_db.values():
        doc_rec = next((d for d in app_case.documents if d.id == document_id), None)
        if doc_rec and os.path.exists(doc_rec.file_path):
            try:
                with open(doc_rec.file_path, "rb") as f:
                    fb = f.read()
                _, pages = extract_pdf_data(fb, doc_rec.filename, app_case.id, doc_rec.file_path)
                res = analyze_document_forensics(fb, pages, doc_rec.filename, doc_rec.id, app_case.id)
                forensics_db[document_id] = res
                return res
            except Exception as e:
                logger.error(f"Error computing on-demand forensics for document {document_id}: {e}")
                raise HTTPException(status_code=500, detail=f"Forensics computation failed: {str(e)}")

    raise HTTPException(status_code=404, detail=f"Document with ID '{document_id}' not found.")

@app.get("/api/applications/{application_id}/forensics")
def get_application_forensics(application_id: str):
    """
    Retrieve all document forensic results for an application case.
    """
    app_case = applications_db.get(application_id)
    if not app_case:
        raise HTTPException(status_code=404, detail="Application case not found.")

    results = []
    for doc in app_case.documents:
        res = forensics_db.get(doc.id)
        if not res and os.path.exists(doc.file_path):
            try:
                with open(doc.file_path, "rb") as f:
                    fb = f.read()
                _, pages = extract_pdf_data(fb, doc.filename, application_id, doc.file_path)
                res = analyze_document_forensics(fb, pages, doc.filename, doc.id, application_id)
                forensics_db[doc.id] = res
            except Exception as e:
                logger.error(f"Error computing forensics for doc {doc.id}: {e}")
        if res:
            results.append(res)

    return {
        "application_id": application_id,
        "document_count": len(results),
        "results": results,
    }

