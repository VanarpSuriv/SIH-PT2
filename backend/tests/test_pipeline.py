"""
Unit and Integration Test Suite for AICTE EoA Document Verification System.
Tests ingestion, field extraction, rules engine, verification adapter, cryptographic audit trail, and API endpoints.
"""
import os
import sys
import pytest
from fastapi.testclient import TestClient

# Ensure root workspace is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.tests.conftest import TEST_OFFICER_TOKEN
from backend.main import app
from backend.models import DocumentType, FindingStatus, Severity, VerificationStatus
from backend.ingest.service import extract_pdf_data, compute_sha256
from backend.extract.service import extract_document_fields
from backend.rules.engine import RulesEngine
from backend.verify.adapter import VerificationAdapter
from backend.audit.trail import AuditTrail, GENESIS_HASH

client = TestClient(app)

CASES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "synthetic", "cases")

def test_hash_computation():
    """Verify SHA-256 computation."""
    data = b"AICTE Regulatory Document Content"
    h1 = compute_sha256(data)
    h2 = compute_sha256(data)
    assert len(h1) == 64
    assert h1 == h2

def test_ingest_and_extract_clean_case():
    """Verify end-to-end ingest and extraction on clean case_01."""
    app_pdf = os.path.join(CASES_DIR, "case_01", "application_form.pdf")
    assert os.path.exists(app_pdf)

    with open(app_pdf, "rb") as f:
        content = f.read()

    rec, pages = extract_pdf_data(content, "application_form.pdf", "APP-TEST", app_pdf)
    assert rec.document_type == DocumentType.APPLICATION_FORM
    assert rec.page_count == 1
    assert len(rec.sha256_hash) == 64
    assert len(pages) == 1
    assert len(pages[0].words) > 10

    fields = extract_document_fields(rec, pages)
    field_names = [f.name for f in fields]
    assert "application_id" in field_names
    assert "permanent_id" in field_names
    assert "institution_name" in field_names
    assert "declared_land_area" in field_names
    assert "declared_faculty_count" in field_names

    # Check that bounding box coordinates are non-zero
    for fld in fields:
        assert len(fld.bbox) == 4
        assert fld.bbox[2] >= fld.bbox[0]
        assert fld.bbox[3] >= fld.bbox[1]

def test_rules_engine_clean_case():
    """Verify rules engine passes clean case_01 without critical failures."""
    rules_engine = RulesEngine()
    case_path = os.path.join(CASES_DIR, "case_01")
    
    docs = []
    all_fields = []
    for fname in ["application_form.pdf", "approval_letter.pdf", "land_document.pdf", "fire_noc.pdf", "faculty_list.pdf"]:
        fpath = os.path.join(case_path, fname)
        with open(fpath, "rb") as f:
            d = f.read()
        rec, pages = extract_pdf_data(d, fname, "APP-TEST", fpath)
        docs.append(rec)
        all_fields.extend(extract_document_fields(rec, pages))

    findings = rules_engine.evaluate("APP-TEST", docs, all_fields)
    failed_findings = [f for f in findings if f.status == FindingStatus.FAIL]
    assert len(failed_findings) == 0, f"Expected 0 failures on clean case, got: {[f.claim for f in failed_findings]}"

def test_rules_engine_missing_document():
    """Verify rules engine flags missing Fire NOC in case_06."""
    rules_engine = RulesEngine()
    case_path = os.path.join(CASES_DIR, "case_06")
    
    docs = []
    all_fields = []
    for fname in ["application_form.pdf", "approval_letter.pdf", "land_document.pdf", "faculty_list.pdf"]:
        fpath = os.path.join(case_path, fname)
        if os.path.exists(fpath):
            with open(fpath, "rb") as f:
                d = f.read()
            rec, pages = extract_pdf_data(d, fname, "APP-CASE-06", fpath)
            docs.append(rec)
            all_fields.extend(extract_document_fields(rec, pages))

    findings = rules_engine.evaluate("APP-CASE-06", docs, all_fields)
    fire_noc_find = next((f for f in findings if f.rule_id == "AICTE-EOA-002"), None)
    assert fire_noc_find is not None
    assert fire_noc_find.status == FindingStatus.FAIL
    assert "MISSING" in fire_noc_find.claim

def test_rules_engine_expired_fire_noc():
    """Verify rules engine flags expired Fire NOC in case_09."""
    rules_engine = RulesEngine()
    case_path = os.path.join(CASES_DIR, "case_09")
    
    docs = []
    all_fields = []
    for fname in ["application_form.pdf", "approval_letter.pdf", "land_document.pdf", "fire_noc.pdf", "faculty_list.pdf"]:
        fpath = os.path.join(case_path, fname)
        with open(fpath, "rb") as f:
            d = f.read()
        rec, pages = extract_pdf_data(d, fname, "APP-CASE-09", fpath)
        docs.append(rec)
        all_fields.extend(extract_document_fields(rec, pages))

    findings = rules_engine.evaluate("APP-CASE-09", docs, all_fields)
    expired_find = next((f for f in findings if f.rule_id == "AICTE-EOA-005"), None)
    assert expired_find is not None
    assert expired_find.status == FindingStatus.FAIL
    assert "expired on" in expired_find.claim

def test_rules_engine_name_mismatch():
    """Verify rules engine flags name mismatch in case_12."""
    rules_engine = RulesEngine()
    case_path = os.path.join(CASES_DIR, "case_12")
    
    docs = []
    all_fields = []
    for fname in ["application_form.pdf", "approval_letter.pdf", "land_document.pdf", "fire_noc.pdf", "faculty_list.pdf"]:
        fpath = os.path.join(case_path, fname)
        with open(fpath, "rb") as f:
            d = f.read()
        rec, pages = extract_pdf_data(d, fname, "APP-CASE-12", fpath)
        docs.append(rec)
        all_fields.extend(extract_document_fields(rec, pages))

    findings = rules_engine.evaluate("APP-CASE-12", docs, all_fields)
    name_find = next((f for f in findings if f.rule_id == "AICTE-EOA-007"), None)
    assert name_find is not None
    assert name_find.status == FindingStatus.FAIL
    assert "discrepancy" in name_find.claim

def test_rules_engine_land_area_mismatch():
    """Verify rules engine flags land area inflation / deficit in case_18."""
    rules_engine = RulesEngine()
    case_path = os.path.join(CASES_DIR, "case_18")
    
    docs = []
    all_fields = []
    for fname in ["application_form.pdf", "approval_letter.pdf", "land_document.pdf", "fire_noc.pdf", "faculty_list.pdf"]:
        fpath = os.path.join(case_path, fname)
        with open(fpath, "rb") as f:
            d = f.read()
        rec, pages = extract_pdf_data(d, fname, "APP-CASE-18", fpath)
        docs.append(rec)
        all_fields.extend(extract_document_fields(rec, pages))

    findings = rules_engine.evaluate("APP-CASE-18", docs, all_fields)
    area_find = next((f for f in findings if f.rule_id == "AICTE-EOA-009"), None)
    assert area_find is not None
    assert area_find.status == FindingStatus.FAIL

def test_verification_adapter():
    """Verify simulated external issuer responses."""
    adapter = VerificationAdapter()
    
    # Existing valid record
    r1 = adapter.verify("AICTE_CENTRAL_PORTAL", "PID-1-7000001")
    assert r1.source == "SIMULATED"
    assert r1.status == VerificationStatus.VERIFIED

    # Non-existent or simulated unavailable
    r2 = adapter.verify("UNKNOWN_PORTAL", "NON_EXISTENT_ID_999")
    assert r2.source == "SIMULATED"
    assert r2.status == VerificationStatus.SOURCE_UNAVAILABLE

def test_audit_trail_cryptographic_verification_and_tamper_detection(tmp_path):
    """Verify SHA-256 hash chaining and tamper detection."""
    test_db = str(tmp_path / "test_audit.db")
    trail = AuditTrail(db_path=test_db)
    
    # Empty chain is valid
    v0 = trail.verify_chain()
    assert v0["is_valid"] is True
    assert v0["total_events"] == 0

    # Log 3 events
    e1 = trail.log_event("APP-001", "INGEST", {"file": "doc1.pdf"})
    assert e1.prev_hash == GENESIS_HASH

    e2 = trail.log_event("APP-001", "RULE_CHECK", {"rule": "AICTE-EOA-001", "status": "PASS"})
    assert e2.prev_hash == e1.hash

    e3 = trail.log_event("APP-001", "CONFIRM", {"finding_id": "f_123"})
    assert e3.prev_hash == e2.hash

    # Verify pristine chain
    v1 = trail.verify_chain()
    assert v1["is_valid"] is True
    assert v1["total_events"] == 3

    # Tamper with event 2 in the database
    tampered = trail.tamper_event_for_demo(e2.id, {"rule": "AICTE-EOA-001", "status": "TAMPERED_INSPECTION"})
    assert tampered is True

    # Verify chain catches the tamper
    v2 = trail.verify_chain()
    assert v2["is_valid"] is False
    assert v2["event_id"] == e2.id
    assert "tampering detected" in v2["reason"]

def test_fastapi_endpoints():
    """Test FastAPI application endpoints."""
    # 1. Health check
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

    # 2. List synthetic cases
    res = client.get("/api/cases")
    assert res.status_code == 200
    cases = res.json()
    assert len(cases) == 25

    # 3. Load case_01 directly via API
    res = client.post("/api/cases/case_01/load")
    assert res.status_code == 200
    data = res.json()
    app_id = data["id"]
    assert data["institution_name"] == "Apex Institute of Technology"
    assert len(data["documents"]) == 5
    assert len(data["findings"]) > 0

    # 4. Get application by ID
    res = client.get(f"/api/applications/{app_id}")
    assert res.status_code == 200
    assert res.json()["id"] == app_id

    # 5. Get finding and test server-side highlight rendering
    finding_id = data["findings"][0]["id"]
    res = client.get(f"/api/findings/{finding_id}")
    assert res.status_code == 200

    img_res = client.get(f"/api/findings/{finding_id}/evidence_image")
    assert img_res.status_code == 200
    assert img_res.headers["content-type"] == "image/png"
    assert len(img_res.content) > 1000

    # 6. Confirm finding with audit logging
    conf_res = client.post(
        f"/api/findings/{finding_id}/confirm",
        data={"reviewer_notes": "Valid finding"},
        headers={"Authorization": f"Bearer {TEST_OFFICER_TOKEN}", "X-Officer-Role": "OFFICER"}
    )
    assert conf_res.status_code == 200
    assert conf_res.json()["user_status"] == "CONFIRMED"

    # 7. Verify audit chain
    audit_res = client.get("/api/audit/verify")
    assert audit_res.status_code == 200
    assert audit_res.json()["is_valid"] is True

def test_pyhanko_signature_verification_outcomes():
    """Verify pyHanko yields 3 distinct outcomes: intact, modified, and untrusted signer."""
    from backend.signature.verifier import SignatureVerifier

    # 1. Intact and trusted
    r_intact = SignatureVerifier.verify_pdf("sample_intact.pdf")
    assert r_intact["has_signature"] is True
    assert r_intact["status"] == "INTACT"
    assert r_intact["tampering_detected"] is False

    # 2. Modified / Tampered
    r_mod = SignatureVerifier.verify_pdf("sample_tampered.pdf")
    assert r_mod["has_signature"] is True
    assert r_mod["status"] == "MODIFIED"
    assert r_mod["tampering_detected"] is True

    # 3. Untrusted Signer
    r_untrusted = SignatureVerifier.verify_pdf("sample_untrusted.pdf")
    assert r_untrusted["has_signature"] is True
    assert r_untrusted["status"] == "UNTRUSTED_SIGNER"
    assert r_untrusted["tampering_detected"] is False

    # 4. Check endpoint
    res = client.get("/api/signature/check?sample_type=intact")
    assert res.status_code == 200
    assert res.json()["source"] == "SIMULATED"
    assert res.json()["status"] == "INTACT"
