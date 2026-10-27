"""
Automated Test Suite for Dedicated PDF Metadata Extraction and META-* Rules Engine.
Tests:
- Metadata extraction (Creator, Producer, CreationDate, ModDate, PDF version, encryption, page count, SHA-256)
- ASN.1 / PDF-1.7 date parsing, missing timezone warnings, and malformed strings
- META-001 (ModDate precedes CreationDate)
- META-002 (CreationDate postdates Application Date)
- META-003 (Parser syntax warnings)
- API finding retrieval, schema separation (lifecycle, verification, human-review), and tamper-evident audit logging
"""
import os
import sys
import uuid
from datetime import datetime, timezone
import pytest
import pymupdf
from fastapi.testclient import TestClient

# Ensure root workspace is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.main import app, findings_db, applications_db
from backend.tests.conftest import TEST_OFFICER_TOKEN
from backend.models import (
    DocumentType,
    RuleCategory,
    FindingStatus,
    FindingLifecycle,
    ReviewDecision,
    Severity,
    ExtractedField,
)
from backend.metadata.service import extract_pdf_metadata, parse_pdf_date
from backend.ingest.service import extract_pdf_data
from backend.extract.service import extract_document_fields
from backend.rules.engine import RulesEngine
from backend.audit.trail import get_audit_trail

client = TestClient(app)

def create_synthetic_test_pdf(
    file_path: str,
    text: str = "AICTE Test Document",
    creation_date: str = "D:20250110100000+05'30'",
    mod_date: str = "D:20250110103000+05'30'",
    producer: str = "ReportLab PDF Library v3.6.12",
    creator: str = "AICTE Verification Test Harness"
) -> str:
    """Helper to generate a controlled PDF with specific metadata strings."""
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 100), text, fontsize=12)
    
    meta = {
        "producer": producer,
        "creator": creator,
        "creationDate": creation_date,
        "modDate": mod_date,
        "title": "AICTE EoA Regulatory Test Document"
    }
    doc.set_metadata(meta)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    doc.save(file_path)
    doc.close()
    return file_path

def test_extract_pdf_metadata_well_formed(tmp_path):
    """Test standard metadata extraction on a well-formed PDF."""
    pdf_path = str(tmp_path / "normal_doc.pdf")
    create_synthetic_test_pdf(
        pdf_path,
        text="Application Form AICTE",
        creation_date="D:20250201120000+00'00'",
        mod_date="D:20250201121500+00'00'",
        producer="TestProducer 1.0",
        creator="TestCreator 1.0"
    )
    with open(pdf_path, "rb") as f:
        data = f.read()

    meta = extract_pdf_metadata(data, pdf_path)

    assert meta.producer == "TestProducer 1.0"
    assert meta.creator == "TestCreator 1.0"
    assert meta.raw_creation_date == "D:20250201120000+00'00'"
    assert meta.normalized_creation_date == "2025-02-01T12:00:00+00:00"
    assert meta.normalized_mod_date == "2025-02-01T12:15:00+00:00"
    assert meta.is_encrypted is False
    assert meta.page_count == 1
    assert len(meta.sha256_hash) == 64
    assert meta.pdf_version is not None
    assert len(meta.parsing_warnings) == 0

def test_parse_pdf_date_variations():
    """Test date parsing across various compliant and non-compliant formats."""
    # 1. Standard PDF date with timezone
    norm, warns = parse_pdf_date("D:20240315143000+05'30'")
    assert norm == "2024-03-15T14:30:00+05:30"
    assert len(warns) == 0

    # 2. Standard UTC Z date
    norm_z, warns_z = parse_pdf_date("D:20240315143000Z")
    assert norm_z == "2024-03-15T14:30:00+00:00"
    assert len(warns_z) == 0

    # 3. Missing timezone (should default to UTC with warning)
    norm_no_tz, warns_no_tz = parse_pdf_date("D:20240315143000")
    assert norm_no_tz == "2024-03-15T14:30:00+00:00"
    assert any("missing timezone" in w.lower() for w in warns_no_tz)

    # 4. Standard ISO-8601 string
    norm_iso, warns_iso = parse_pdf_date("2024-03-15T14:30:00Z")
    assert norm_iso == "2024-03-15T14:30:00+00:00"

    # 5. Malformed string (should return None with warning, not raise exception)
    norm_malformed, warns_malformed = parse_pdf_date("NotAValidDateString12345")
    assert norm_malformed is None
    assert len(warns_malformed) > 0

    # 6. None or empty
    norm_none, warns_none = parse_pdf_date(None)
    assert norm_none is None
    assert len(warns_none) == 0

def test_meta_001_temporal_inconsistency_rule(tmp_path):
    """
    Test META-001: Flag when ModDate strictly precedes CreationDate.
    Planted anomaly: CreationDate = 2025-03-01, ModDate = 2025-01-01 (60 days earlier).
    """
    pdf_path = str(tmp_path / "anomalous_dates.pdf")
    create_synthetic_test_pdf(
        pdf_path,
        text="Affiliation Letter 2024-2025",
        creation_date="D:20250301100000+00'00'",
        mod_date="D:20250101100000+00'00'" # Precedes creation date by 60 days
    )
    with open(pdf_path, "rb") as f:
        data = f.read()

    doc_record, pages = extract_pdf_data(data, "anomalous_dates.pdf", "APP-META-001", pdf_path)
    # Check that metadata service detected temporal anomaly
    assert "MOD_DATE_PRECEDES_CREATION_DATE" in doc_record.metadata.metadata_anomalies

    engine = RulesEngine()
    fields = extract_document_fields(doc_record, pages)
    findings = engine.evaluate("APP-META-001", [doc_record], fields)

    meta_001 = next((f for f in findings if f.rule_id == "META-001"), None)
    assert meta_001 is not None, "Expected META-001 finding to trigger"
    assert meta_001.status == FindingStatus.FLAGGED
    assert meta_001.rule_category == RuleCategory.METADATA_INTEGRITY
    assert meta_001.severity == Severity.MEDIUM
    assert meta_001.metadata_context is not None
    assert "precedes CreationDate" in meta_001.claim
    # Verify non-prejudicial reason
    assert "does not constitute proof of forgery" in meta_001.metadata_context.reason_for_review.lower()
    assert "manual verification" in meta_001.metadata_context.reason_for_review.lower()
    assert "raw_creation_date" in meta_001.metadata_context.original_values

def test_meta_002_creation_postdates_application_rule(tmp_path):
    """
    Test META-002: Flag when document CreationDate postdates declared application date.
    Declared Application Date: 2025-03-15
    Document CreationDate: 2025-04-10 (26 days later)
    """
    pdf_path = str(tmp_path / "retroactive_doc.pdf")
    create_synthetic_test_pdf(
        pdf_path,
        text="Fire Safety NOC Valid To: 2026-03-31",
        creation_date="D:20250410120000+00'00'", # April 2025
        mod_date="D:20250410120500+00'00'"
    )
    with open(pdf_path, "rb") as f:
        data = f.read()

    doc_record, pages = extract_pdf_data(data, "retroactive_doc.pdf", "APP-META-002", pdf_path)
    doc_record.document_type = DocumentType.FIRE_NOC

    # Simulated application field with application_date = 2025-03-15
    app_date_field = ExtractedField(
        name="application_date",
        value="2025-03-15",
        raw_text="2025-03-15",
        document_type=DocumentType.APPLICATION_FORM,
        page_number=1,
        bbox=[50.0, 50.0, 100.0, 70.0],
        confidence=1.0
    )

    engine = RulesEngine()
    findings = engine.evaluate("APP-META-002", [doc_record], [app_date_field])

    meta_002 = next((f for f in findings if f.rule_id == "META-002"), None)
    assert meta_002 is not None, "Expected META-002 finding to trigger"
    assert meta_002.status == FindingStatus.FLAGGED
    assert meta_002.rule_category == RuleCategory.METADATA_INTEGRITY
    assert meta_002.metadata_context is not None
    assert "postdates declared application date" in meta_002.metadata_context.reason_for_review

def test_meta_003_parser_warnings_rule(tmp_path):
    """
    Test META-003: Flag documents with non-standard syntax or parsing warnings.
    """
    pdf_path = str(tmp_path / "warning_doc.pdf")
    create_synthetic_test_pdf(
        pdf_path,
        text="Faculty List Document",
        creation_date="D:20250101120000", # Missing timezone offset -> generates warning
        mod_date="D:20250101120500"
    )
    with open(pdf_path, "rb") as f:
        data = f.read()

    doc_record, pages = extract_pdf_data(data, "warning_doc.pdf", "APP-META-003", pdf_path)
    assert len(doc_record.metadata.parsing_warnings) > 0

    engine = RulesEngine()
    findings = engine.evaluate("APP-META-003", [doc_record], [])

    meta_003 = next((f for f in findings if f.rule_id == "META-003"), None)
    assert meta_003 is not None, "Expected META-003 finding to trigger"
    assert meta_003.status == FindingStatus.FLAGGED
    assert meta_003.rule_category == RuleCategory.METADATA_INTEGRITY
    assert meta_003.metadata_context is not None
    assert len(meta_003.metadata_context.parsing_warnings) > 0

def test_api_finding_schema_and_structured_review(tmp_path):
    """
    Integration test:
    1. Upload PDF with metadata anomaly via API
    2. Verify finding schema has separated lifecycle, verification_result, and review
    3. Submit structured reviewer decision (CONFIRMED_DEFECT)
    4. Verify finding transitions to RESOLVED
    5. Verify cryptographic audit chain integrity
    """
    pdf_path = str(tmp_path / "upload_anomalous.pdf")
    create_synthetic_test_pdf(
        pdf_path,
        text="Application Form AICTE EoA 2025-2026 Permanent ID: 1-10023456",
        creation_date="D:20250501100000+00'00'",
        mod_date="D:20250101100000+00'00" # ModDate precedes CreationDate
    )

    with open(pdf_path, "rb") as f:
        files = [("files", ("application_form.pdf", f.read(), "application/pdf"))]
        upload_resp = client.post("/api/upload", data={"institution_name": "Test Engineering College"}, files=files)

    assert upload_resp.status_code == 200
    app_data = upload_resp.json()
    app_id = app_data["id"]

    # Verify metadata was persisted in document record
    assert len(app_data["documents"]) > 0
    doc_meta = app_data["documents"][0]["metadata"]
    assert doc_meta["producer"] is not None
    assert doc_meta["raw_creation_date"] == "D:20250501100000+00'00'"
    assert doc_meta["normalized_creation_date"] == "2025-05-01T10:00:00+00:00"
    assert doc_meta["sha256_hash"] != ""

    # Locate META-001 finding
    findings = app_data["findings"]
    meta_finding = next((f for f in findings if f["rule_id"] == "META-001"), None)
    assert meta_finding is not None, f"Expected META-001 finding in: {[f['rule_id'] for f in findings]}"
    finding_id = meta_finding["id"]

    # 1. Verify schema separation before review
    assert meta_finding["lifecycle"] == "OPEN"
    assert meta_finding["rule_category"] == "METADATA_INTEGRITY"
    assert meta_finding["review"]["decision"] == "UNREVIEWED"
    assert meta_finding["metadata_context"] is not None
    assert "precedes CreationDate" in meta_finding["claim"]

    # 2. Submit structured human review decision
    review_payload = {
        "decision": "CONFIRMED_DEFECT",
        "reviewer_notes": "Forensic timestamp inversion confirmed by inspection officer.",
        "reviewer_id": "OFFICER-TEST-99"
    }
    review_resp = client.post(
        f"/api/findings/{finding_id}/review",
        json=review_payload,
        headers={"Authorization": f"Bearer {TEST_OFFICER_TOKEN}", "X-Officer-Role": "OFFICER"}
    )
    assert review_resp.status_code == 200
    review_result = review_resp.json()
    assert review_result["status"] == "success"
    assert review_result["decision"] == "CONFIRMED_DEFECT"
    assert review_result["lifecycle"] == "RESOLVED"
    assert "audit_event_id" in review_result

    # 3. Retrieve finding again and verify state
    get_resp = client.get(f"/api/findings/{finding_id}")
    assert get_resp.status_code == 200
    updated_finding = get_resp.json()
    assert updated_finding["lifecycle"] == "RESOLVED"
    assert updated_finding["review"]["decision"] == "CONFIRMED_DEFECT"
    assert updated_finding["review"]["reviewer_notes"] == "Forensic timestamp inversion confirmed by inspection officer."
    assert updated_finding["review"]["reviewed_by"] == "OFFICER-TEST-99"

    # 4. Verify Cryptographic Audit Chain
    audit_resp = client.get("/api/audit/verify")
    assert audit_resp.status_code == 200
    chain_status = audit_resp.json()
    assert chain_status["is_valid"] is True
    assert chain_status["total_events"] > 0

def test_extract_pdf_metadata_stripped_benign(tmp_path):
    """
    Test that the complete absence of metadata is treated as benign.
    Must NOT trigger META-001, META-002, or META-003, and must not imply forgery.
    """
    pdf_path = str(tmp_path / "stripped_doc.pdf")
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 100), "Compliant Document with Stripped Metadata", fontsize=12)
    doc.set_metadata({})  # Completely empty metadata dictionary
    doc.save(pdf_path)
    doc.close()

    with open(pdf_path, "rb") as f:
        data = f.read()

    meta = extract_pdf_metadata(data, pdf_path)
    assert meta.raw_creation_date is None
    assert meta.raw_mod_date is None
    assert meta.normalized_creation_date is None
    assert meta.normalized_mod_date is None
    assert len(meta.metadata_anomalies) == 0

    doc_rec, pages = extract_pdf_data(data, "stripped_doc.pdf", "APP-STRIPPED", pdf_path)
    engine = RulesEngine()
    findings = engine.evaluate("APP-STRIPPED", [doc_rec], [])

    # Verify no META-* rules triggered for missing metadata
    meta_findings = [f for f in findings if f.rule_category == RuleCategory.METADATA_INTEGRITY]
    assert len(meta_findings) == 0, f"Expected 0 metadata flags on stripped document, got: {[f.rule_id for f in meta_findings]}"

def test_benign_producers_no_forgery_implication(tmp_path):
    """
    Test standard open-source and commercial PDF generators.
    The presence of tools like Ghostscript, ReportLab, pdfcpu, or Microsoft Print to PDF
    must never independently trigger forgery findings or compliance failure.
    """
    benign_producers = [
        "ReportLab PDF Library v3.6.12",
        "Ghostscript 10.02.0",
        "pdfcpu v0.4.1",
        "Microsoft: Print To PDF",
        "macOS 14.2 Quartz PDFContext",
        "Google Chrome Headless"
    ]

    for idx, prod in enumerate(benign_producers):
        pdf_path = str(tmp_path / f"benign_{idx}.pdf")
        create_synthetic_test_pdf(
            pdf_path,
            text=f"Valid Document generated by {prod}",
            creation_date="D:20250115100000+00'00'",
            mod_date="D:20250115101000+00'00'",  # Standard 10 min subsequent modification
            producer=prod,
            creator="Institutional Office Suite"
        )
        with open(pdf_path, "rb") as f:
            data = f.read()

        meta = extract_pdf_metadata(data, pdf_path)
        assert meta.producer == prod
        assert len(meta.metadata_anomalies) == 0

        doc_rec, pages = extract_pdf_data(data, f"benign_{idx}.pdf", f"APP-BENIGN-{idx}", pdf_path)
        engine = RulesEngine()
        findings = engine.evaluate(f"APP-BENIGN-{idx}", [doc_rec], [])
        meta_findings = [f for f in findings if f.rule_category == RuleCategory.METADATA_INTEGRITY]
        assert len(meta_findings) == 0, f"Producer '{prod}' erroneously triggered metadata flags: {[f.rule_id for f in meta_findings]}"

def test_server_side_authorization_boundaries(tmp_path, monkeypatch):
    """
    Test server-side authorization enforcement on finding review actions:
    1. Unauthenticated requests (no token) rejected with 401.
    2. Forged client-side X-Officer-Role without server token rejected with 401.
    3. Invalid bearer tokens rejected with 401.
    4. Valid token but unauthorized role (APPLICANT) rejected with 403.
    5. Authorized officer with valid token permitted (200).
    """
    pdf_path = str(tmp_path / "auth_test.pdf")
    create_synthetic_test_pdf(pdf_path, creation_date="D:20250401120000+00'00'", mod_date="D:20250101120000+00'00'")
    with open(pdf_path, "rb") as f:
        up_resp = client.post("/api/upload", data={"institution_name": "Auth Test College"}, files=[("files", ("auth.pdf", f.read(), "application/pdf"))])
    app_data = up_resp.json()
    finding_id = app_data["findings"][0]["id"]

    # 1. Reject unauthenticated request (no token, no headers)
    no_auth_resp = client.post(
        f"/api/findings/{finding_id}/review",
        json={"decision": "CONFIRMED_DEFECT", "reviewer_notes": "Unauthenticated attempt"}
    )
    assert no_auth_resp.status_code == 401
    assert "Authentication Required" in no_auth_resp.json()["detail"]

    # 2. Reject forged client-asserted X-Officer-Role without server token
    forged_role_resp = client.post(
        f"/api/findings/{finding_id}/review",
        json={"decision": "CONFIRMED_DEFECT", "reviewer_notes": "Forged role without token"},
        headers={"X-Officer-Role": "OFFICER"}
    )
    assert forged_role_resp.status_code == 401
    assert "Authentication Required" in forged_role_resp.json()["detail"]

    # 3. Reject invalid bearer token
    bearer_resp = client.post(
        f"/api/findings/{finding_id}/review",
        json={"decision": "CONFIRMED_DEFECT", "reviewer_notes": "Attempt with invalid token"},
        headers={"Authorization": "Bearer forged_secret_token_abc"}
    )
    assert bearer_resp.status_code == 401
    assert "Invalid officer authentication credentials" in bearer_resp.json()["detail"]

    # 4. Reject compromised / revoked legacy token
    revoked_resp = client.post(
        f"/api/findings/{finding_id}/review",
        json={"decision": "CONFIRMED_DEFECT", "reviewer_notes": "Attempt with revoked legacy token"},
        headers={"Authorization": "Bearer veritas-officer-token-auth-2025", "X-Officer-Role": "OFFICER"}
    )
    assert revoked_resp.status_code == 401
    assert "revoked" in revoked_resp.json()["detail"].lower()

    # 5. Reject valid token with unauthorized role (e.g. APPLICANT)
    unauth_role_resp = client.post(
        f"/api/findings/{finding_id}/review",
        json={"decision": "CONFIRMED_DEFECT", "reviewer_notes": "Applicant attempting review"},
        headers={"Authorization": f"Bearer {TEST_OFFICER_TOKEN}", "X-Officer-Role": "APPLICANT"}
    )
    assert unauth_role_resp.status_code == 403
    assert "Access Denied" in unauth_role_resp.json()["detail"]

    # 6. Allow authorized officer with valid token & verify demo header labeling
    auth_resp = client.post(
        f"/api/findings/{finding_id}/review",
        json={"decision": "CONFIRMED_DEFECT", "reviewer_notes": "Authorized review by scrutiny officer"},
        headers={"Authorization": f"Bearer {TEST_OFFICER_TOKEN}", "X-Officer-Role": "OFFICER"}
    )
    assert auth_resp.status_code == 200
    assert auth_resp.json()["status"] == "success"
    assert auth_resp.headers.get("x-auth-mode") == "DEMO_SHARED_TOKEN"

    # 7. Fail closed when server secret is unconfigured
    monkeypatch.delenv("OFFICER_AUTH_TOKEN", raising=False)
    fail_closed_resp = client.post(
        f"/api/findings/{finding_id}/review",
        json={"decision": "CONFIRMED_DEFECT", "reviewer_notes": "Review when secret unconfigured"},
        headers={"Authorization": f"Bearer {TEST_OFFICER_TOKEN}", "X-Officer-Role": "OFFICER"}
    )
    assert fail_closed_resp.status_code == 500
    assert "unconfigured" in fail_closed_resp.json()["detail"].lower()

def test_audit_tamper_demo_guard(monkeypatch):
    """
    Test that /api/audit/tamper is disabled by default and strictly guarded.
    1. Unauthenticated client rejected with 401.
    2. By default, ENABLE_DEMO_TAMPER is false: tamper endpoint rejects with 403 unconditionally.
    3. When ENABLE_DEMO_TAMPER is enabled on server, demo header is required.
    4. When ENABLE_DEMO_TAMPER is true, valid officer credentials present, and demo header passed, request succeeds.
    """
    import backend.main as main_mod

    # 1. Unauthenticated client rejected with 401 even if X-Demo-Mode: true
    resp_unauth = client.post(
        "/api/audit/tamper",
        data={"event_id": "non_existent_evt"},
        headers={"X-Demo-Mode": "true"}
    )
    assert resp_unauth.status_code == 401
    assert "Authentication Required" in resp_unauth.json()["detail"]

    # 2. Server has demo tamper disabled (default)
    monkeypatch.setattr(main_mod, "ENABLE_DEMO_TAMPER", False)
    resp_disabled = client.post(
        "/api/audit/tamper",
        data={"event_id": "non_existent_evt"},
        headers={
            "X-Demo-Mode": "true",
            "Authorization": f"Bearer {TEST_OFFICER_TOKEN}",
            "X-Officer-Role": "OFFICER"
        }
    )
    assert resp_disabled.status_code == 403
    assert "strictly disabled by default" in resp_disabled.json()["detail"]

    # 3. Server has demo tamper enabled, but client omits or sends false header
    monkeypatch.setattr(main_mod, "ENABLE_DEMO_TAMPER", True)
    resp_no_header = client.post(
        "/api/audit/tamper",
        data={"event_id": "non_existent_evt"},
        headers={
            "X-Demo-Mode": "false",
            "Authorization": f"Bearer {TEST_OFFICER_TOKEN}",
            "X-Officer-Role": "OFFICER"
        }
    )
    assert resp_no_header.status_code == 403
    assert "demonstration authorization header" in resp_no_header.json()["detail"]

    # 4. Server has demo enabled, valid credentials provided, and client provides X-Demo-Mode: true
    resp_demo = client.post(
        "/api/audit/tamper",
        data={"event_id": "non_existent_evt"},
        headers={
            "X-Demo-Mode": "true",
            "Authorization": f"Bearer {TEST_OFFICER_TOKEN}",
            "X-Officer-Role": "OFFICER"
        }
    )
    assert resp_demo.status_code == 404
    assert "Audit event not found" in resp_demo.json()["detail"]

def test_upload_validation_and_type_check():
    """
    Test upload type and size boundary checks:
    - Non-PDF extension rejected with 400
    - Empty file rejected with 400
    - Non-PDF binary missing %PDF- header rejected with 400
    """
    # 1. Non-PDF extension
    bad_ext_resp = client.post(
        "/api/upload",
        data={"institution_name": "Test"},
        files=[("files", ("report.docx", b"%PDF-fake content", "application/vnd.openxmlformats"))]
    )
    assert bad_ext_resp.status_code == 400
    assert "Unsupported file type" in bad_ext_resp.json()["detail"]

    # 2. Empty file
    empty_resp = client.post(
        "/api/upload",
        data={"institution_name": "Test"},
        files=[("files", ("empty.pdf", b"", "application/pdf"))]
    )
    assert empty_resp.status_code == 400
    assert "empty (0 bytes)" in empty_resp.json()["detail"]

    # 3. Missing %PDF- magic bytes
    bad_magic_resp = client.post(
        "/api/upload",
        data={"institution_name": "Test"},
        files=[("files", ("corrupted.pdf", b"NOT_A_VALID_PDF_HEADER", "application/pdf"))]
    )
    assert bad_magic_resp.status_code == 400
    assert "missing '%PDF-' magic header" in bad_magic_resp.json()["detail"]

def test_safe_storage_prevents_path_traversal(tmp_path):
    """
    Test that malicious filenames attempting directory traversal (e.g. ../../evil.pdf)
    are sanitized and safely isolated within the storage directory.
    """
    valid_pdf_bytes = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    resp = client.post(
        "/api/upload",
        data={"institution_name": "Path Traversal Test"},
        files=[("files", ("../../evil_traversal.pdf", valid_pdf_bytes, "application/pdf"))]
    )
    assert resp.status_code == 200
    app_data = resp.json()
    assert len(app_data["documents"]) == 1
    doc_rec = app_data["documents"][0]
    # Filename must have path stripped
    assert ".." not in doc_rec["filename"]
    assert doc_rec["filename"].endswith(".pdf")



def test_pyhanko_integration_on_uploaded_docs(tmp_path):
    """
    Test pyHanko digital signature verification directly integrated into the document ingest pipeline:
    1. Unsigned document is cleanly recorded as UNSIGNED (not a signature defect).
    2. Document with valid digital signature is verified as INTACT.
    3. Document with modified digital signature flags DIGITAL_SIGNATURE_TAMPERED anomaly.
    """
    # 1. Test standard unsigned document
    pdf_path = str(tmp_path / "unsigned_test.pdf")
    create_synthetic_test_pdf(pdf_path)
    with open(pdf_path, "rb") as f:
        data = f.read()
    rec, _ = extract_pdf_data(data, "unsigned_test.pdf", "APP-SIG-01", pdf_path)
    assert rec.metadata.is_signed is False
    assert rec.metadata.signature_details.get("status") == "UNSIGNED"
    assert "DIGITAL_SIGNATURE_TAMPERED" not in rec.metadata.metadata_anomalies

    # 2. Test sample_intact.pdf if available
    sig_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "signature")
    intact_sample = os.path.join(sig_dir, "sample_intact.pdf")
    if os.path.exists(intact_sample):
        with open(intact_sample, "rb") as f:
            intact_bytes = f.read()
        intact_rec, _ = extract_pdf_data(intact_bytes, "sample_intact.pdf", "APP-SIG-02", intact_sample)
        assert intact_rec.metadata.is_signed is True
        assert intact_rec.metadata.signature_details.get("status") == "INTACT"

    # 3. Test sample_tampered.pdf if available
    tampered_sample = os.path.join(sig_dir, "sample_tampered.pdf")
    if os.path.exists(tampered_sample):
        with open(tampered_sample, "rb") as f:
            tamp_bytes = f.read()
        tamp_rec, _ = extract_pdf_data(tamp_bytes, "sample_tampered.pdf", "APP-SIG-03", tampered_sample)
        assert tamp_rec.metadata.signature_details.get("status") == "MODIFIED"
        assert "DIGITAL_SIGNATURE_TAMPERED" in tamp_rec.metadata.metadata_anomalies

