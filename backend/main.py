"""
FastAPI Backend Application for AICTE EoA Document Verification.
Provides endpoints for Upload, Ingest, Extraction, Rules, Verification Adapter, Audit Trail, and Server-side Highlighting.
"""
import os
import uuid
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pymupdf

from backend.models import (
    DocumentType,
    DocumentRecord,
    ExtractedField,
    Finding,
    FindingStatus,
    Severity,
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

# Setup structured logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("aicte_eoa_backend")

app = FastAPI(
    title="AICTE EoA Document Verification Platform",
    description="Automated regulatory document verification, evidence graphing, rules engine, and cryptographic audit log.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory application store (backed by uploaded file storage on disk)
UPLOAD_STORAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "storage")
os.makedirs(UPLOAD_STORAGE_DIR, exist_ok=True)

applications_db: Dict[str, ApplicationCase] = {}
findings_db: Dict[str, Finding] = {}
rules_engine = RulesEngine()
audit_trail = get_audit_trail()
verification_adapter = get_verification_adapter()

def process_application_documents(
    application_id: str,
    institution_name: str,
    doc_tuples: List[tuple[str, bytes]]
) -> ApplicationCase:
    """Core pipeline: Ingest -> Extract -> Verify External Issuers -> Rules Engine -> Audit Trail."""
    docs: List[DocumentRecord] = []
    all_fields: List[ExtractedField] = []
    app_date = "2025-03-15"

    for filename, file_bytes in doc_tuples:
        target_path = os.path.join(UPLOAD_STORAGE_DIR, application_id, filename)
        doc_record, pages = extract_pdf_data(file_bytes, filename, application_id, target_path)
        docs.append(doc_record)
        
        # Field Extraction
        fields = extract_document_fields(doc_record, pages)
        all_fields.extend(fields)

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

    # Rules Engine evaluation
    findings = rules_engine.evaluate(application_id, docs, all_fields)

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
    """Upload PDF documents for automated AICTE verification."""
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    app_id = f"APP-{uuid.uuid4().hex[:8].upper()}"
    doc_tuples = []
    for file in files:
        content = await file.read()
        doc_tuples.append((file.filename, content))

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
            
            # Severity color
            if finding.severity == Severity.CRITICAL or finding.status == FindingStatus.FAIL:
                annot.set_colors(stroke=(0.85, 0.15, 0.15), fill=(1.0, 0.85, 0.85))
            else:
                annot.set_colors(stroke=(0.15, 0.55, 0.25), fill=(0.85, 0.95, 0.85))
            
            annot.set_border(width=2.0)
            annot.set_opacity(0.4)
            annot.update()

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

@app.post("/api/findings/{finding_id}/confirm")
def confirm_finding(finding_id: str, reviewer_notes: str = Form("")):
    """Reviewer confirms the flagged finding as an authentic violation."""
    finding = findings_db.get(finding_id)
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found.")

    finding.user_status = "CONFIRMED"
    event = audit_trail.log_event(
        application_id=finding.application_id,
        action="FINDING_CONFIRMED",
        payload={
            "finding_id": finding.id,
            "rule_id": finding.rule_id,
            "claim": finding.claim,
            "reviewer_notes": reviewer_notes
        }
    )
    return {"status": "success", "user_status": "CONFIRMED", "audit_event_id": event.id}

@app.post("/api/findings/{finding_id}/dismiss")
def dismiss_finding(finding_id: str, reviewer_notes: str = Form("")):
    """Reviewer dismisses the finding with officer justification."""
    finding = findings_db.get(finding_id)
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found.")

    finding.user_status = "DISMISSED"
    event = audit_trail.log_event(
        application_id=finding.application_id,
        action="FINDING_DISMISSED",
        payload={
            "finding_id": finding.id,
            "rule_id": finding.rule_id,
            "claim": finding.claim,
            "reviewer_notes": reviewer_notes
        }
    )
    return {"status": "success", "user_status": "DISMISSED", "audit_event_id": event.id}

@app.get("/api/audit")
def get_audit_events(application_id: Optional[str] = Query(None)):
    """Fetch immutable hash-chained audit events."""
    return audit_trail.get_events(application_id)

@app.get("/api/audit/verify")
def verify_audit_chain():
    """Verify cryptographic integrity of the audit log hash chain."""
    return audit_trail.verify_chain()

@app.post("/api/audit/tamper")
def tamper_audit_row(event_id: str = Form(...)):
    """Tamper with an event row's payload for live demonstration of cryptographic tamper detection."""
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
        "message": "Row payload altered directly in DB without updating SHA-256 hash. Call /api/audit/verify to see cryptographic failure detection!"
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
