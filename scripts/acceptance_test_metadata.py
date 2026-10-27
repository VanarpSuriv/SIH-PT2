"""
End-to-End Acceptance Test for AICTE EoA Document Metadata Analysis & Review Pipeline.

Acceptance Criteria:
1. Upload synthetic PDF with deliberately planted metadata inconsistency (ModDate precedes CreationDate).
2. Extract and persist Creator, Producer, CreationDate, ModDate, PDF version, encryption, page count, SHA-256.
3. Trigger the correct executable metadata rule (META-001) with non-prejudicial evidence context.
4. Render server-side evidence image highlighting with PyMuPDF.
5. Persist human reviewer decision (lifecycle transition to RESOLVED) in cryptographic audit log.
6. Verify cryptographic integrity of the audit chain (hash = sha256(prev_hash + payload)).
"""
import os
import sys
import json
import pymupdf
import secrets
from fastapi.testclient import TestClient

# Ensure root workspace is in sys.path
WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WORKSPACE_DIR)

# Generate an unpredictable dynamic secret at runtime for acceptance testing
ACCEPTANCE_OFFICER_TOKEN = secrets.token_hex(32)
os.environ["OFFICER_AUTH_TOKEN"] = ACCEPTANCE_OFFICER_TOKEN

from backend.main import app

def run_acceptance_test():
    print("=" * 80)
    print("VERITAS AICTE EoA PLATFORM - ACCEPTANCE TEST SUITE")
    print("Scenario: Deliberately Planted PDF Metadata Inconsistency")
    print("=" * 80)

    client = TestClient(app)

    # Step 1: Generate synthetic PDF with planted metadata inconsistency
    print("\n[Step 1] Generating synthetic PDF with planted temporal metadata anomaly...")
    test_pdf_path = os.path.join(WORKSPACE_DIR, "storage_test_metadata_inconsistency.pdf")
    
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842) # A4
    page.insert_textbox(
        pymupdf.Rect(50, 50, 545, 200),
        "ALL INDIA COUNCIL FOR TECHNICAL EDUCATION\n"
        "EXTENSION OF APPROVAL (EoA) APPLICATION 2025-2026\n\n"
        "Institution: Apex Institute of Advanced Technology\n"
        "Permanent ID: 1-9876543210\n"
        "Application Date: 2025-03-15\n"
        "Declared Land Area: 7.5 Acres",
        fontsize=12
    )

    # Deliberate planted anomaly: ModDate is Jan 1, 2025; CreationDate is April 1, 2025
    # ModDate precedes CreationDate by 90 days!
    planted_creation = "D:20250401120000+05'30'"
    planted_mod = "D:20250101120000+05'30'"
    planted_producer = "VERITAS Synthetic Planted Defect Generator v2.0"
    planted_creator = "AICTE Regulatory Test Framework"

    doc.set_metadata({
        "producer": planted_producer,
        "creator": planted_creator,
        "creationDate": planted_creation,
        "modDate": planted_mod,
        "title": "Application Form - Planted Metadata Discrepancy"
    })
    doc.save(test_pdf_path)
    doc.close()

    print(f"  Created test PDF: {test_pdf_path}")
    print(f"  Planted CreationDate : {planted_creation}")
    print(f"  Planted ModDate      : {planted_mod} (Precedes CreationDate by ~2160 hours)")
    print(f"  Planted Producer     : {planted_producer}")

    # Step 2: Upload to API
    print("\n[Step 2] Ingesting PDF via POST /api/upload...")
    with open(test_pdf_path, "rb") as f:
        files = [("files", ("application_form_anomaly.pdf", f.read(), "application/pdf"))]
        upload_resp = client.post(
            "/api/upload",
            data={"institution_name": "Apex Institute of Advanced Technology"},
            files=files
        )

    assert upload_resp.status_code == 200, f"Upload failed with {upload_resp.status_code}: {upload_resp.text}"
    app_data = upload_resp.json()
    app_id = app_data["id"]
    print(f"  Application Ingested Successfully: ID = {app_id}")
    print(f"  Overall Compliance Status        : {app_data['status']}")

    # Step 3: Verify Metadata Extraction & Persistence
    print("\n[Step 3] Verifying Extracted Document Metadata...")
    assert len(app_data["documents"]) > 0
    doc_record = app_data["documents"][0]
    meta = doc_record["metadata"]

    print(f"  - Producer           : {meta.get('producer')}")
    print(f"  - Creator            : {meta.get('creator')}")
    print(f"  - Raw CreationDate   : {meta.get('raw_creation_date')}")
    print(f"  - Normalized Creation: {meta.get('normalized_creation_date')}")
    print(f"  - Raw ModDate        : {meta.get('raw_mod_date')}")
    print(f"  - Normalized ModDate : {meta.get('normalized_mod_date')}")
    print(f"  - PDF Version        : {meta.get('pdf_version')}")
    print(f"  - Page Count         : {meta.get('page_count')}")
    print(f"  - SHA-256 Digest     : {meta.get('sha256_hash')}")
    print(f"  - Encryption Status  : {meta.get('is_encrypted')}")
    print(f"  - Metadata Anomalies : {meta.get('metadata_anomalies')}")

    assert meta["producer"] == planted_producer
    assert meta["raw_creation_date"] == planted_creation
    assert meta["raw_mod_date"] == planted_mod
    assert meta["normalized_creation_date"] == "2025-04-01T12:00:00+05:30"
    assert meta["normalized_mod_date"] == "2025-01-01T12:00:00+05:30"
    assert "MOD_DATE_PRECEDES_CREATION_DATE" in meta["metadata_anomalies"]
    assert len(meta["sha256_hash"]) == 64

    # Step 4: Verify META-001 Rule Evaluation & Evidence Record
    print("\n[Step 4] Verifying Triggered Metadata Rule (META-001)...")
    findings = app_data["findings"]
    meta_finding = next((f for f in findings if f["rule_id"] == "META-001"), None)
    assert meta_finding is not None, f"Expected META-001 finding in: {[f['rule_id'] for f in findings]}"
    
    finding_id = meta_finding["id"]
    print(f"  - Finding ID         : {finding_id}")
    print(f"  - Rule ID            : {meta_finding['rule_id']} (v{meta_finding['rule_version']})")
    print(f"  - Rule Name          : {meta_finding['rule_name']}")
    print(f"  - Rule Category      : {meta_finding['rule_category']}")
    print(f"  - Severity           : {meta_finding['severity']}")
    print(f"  - Status             : {meta_finding['status']}")
    print(f"  - Lifecycle          : {meta_finding['lifecycle']}")
    print(f"  - Claim              : {meta_finding['claim']}")

    # Verify separated schema
    assert meta_finding["rule_category"] == "METADATA_INTEGRITY"
    assert meta_finding["status"] == "FLAGGED"
    assert meta_finding["lifecycle"] == "OPEN"
    assert meta_finding["review"]["decision"] == "UNREVIEWED"

    # Verify Evidence Context & Non-Prejudicial Characterization
    ctx = meta_finding["metadata_context"]
    assert ctx is not None
    print(f"  - Reason for Review  : {ctx['reason_for_review']}")
    print(f"  - Original Values    : {ctx['original_values']}")
    print(f"  - Normalized Values  : {ctx['normalized_values']}")
    assert "does not constitute proof of forgery" in ctx["reason_for_review"].lower()
    assert "manual verification" in ctx["reason_for_review"].lower()

    # Step 5: Server-Side Highlighting & Visual Evidence
    print("\n[Step 5] Testing Server-Side Evidence Image Highlighting (GET /api/findings/{id}/evidence_image)...")
    img_resp = client.get(f"/api/findings/{finding_id}/evidence_image?field_idx=0")
    assert img_resp.status_code == 200
    assert img_resp.headers["content-type"] == "image/png"
    assert len(img_resp.content) > 1000
    print(f"  Evidence image successfully rendered: {len(img_resp.content)} bytes PNG")

    # Step 6: Structured Human Review Decision
    print("\n[Step 6] Submitting Officer Review Decision (POST /api/findings/{id}/review)...")
    review_notes = "Officer verified PDF header timestamps. ModDate anomaly confirmed as potential compile-time timing discrepancy."
    review_resp = client.post(
        f"/api/findings/{finding_id}/review",
        headers={
            "Authorization": f"Bearer {ACCEPTANCE_OFFICER_TOKEN}",
            "X-Officer-Role": "OFFICER"
        },
        json={
            "decision": "CONFIRMED_DEFECT",
            "reviewer_notes": review_notes,
            "reviewer_id": "AICTE-CHIEF-INSPECTOR-42"
        }
    )
    assert review_resp.status_code == 200
    review_data = review_resp.json()
    assert review_data["status"] == "success"
    assert review_data["decision"] == "CONFIRMED_DEFECT"
    assert review_data["lifecycle"] == "RESOLVED"
    audit_event_id = review_data["audit_event_id"]
    print(f"  Review Decision Recorded: Decision = CONFIRMED_DEFECT, Lifecycle = RESOLVED")
    print(f"  Audit Event ID          : {audit_event_id}")

    # Verify updated finding in GET endpoint
    fetch_resp = client.get(f"/api/findings/{finding_id}")
    assert fetch_resp.status_code == 200
    f_updated = fetch_resp.json()
    assert f_updated["lifecycle"] == "RESOLVED"
    assert f_updated["review"]["decision"] == "CONFIRMED_DEFECT"
    assert f_updated["review"]["reviewer_notes"] == review_notes
    assert f_updated["review"]["reviewed_by"] == "AICTE-CHIEF-INSPECTOR-42"

    # Step 7: Cryptographic Audit Trail Verification
    print("\n[Step 7] Verifying Tamper-Evident Hash Chain (GET /api/audit/verify)...")
    audit_chain_resp = client.get("/api/audit/verify")
    assert audit_chain_resp.status_code == 200
    chain_info = audit_chain_resp.json()
    print(f"  - Cryptographically Valid: {chain_info['is_valid']}")
    print(f"  - Total Chain Events      : {chain_info['total_events']}")
    print(f"  - Latest Block Hash       : {chain_info.get('latest_hash', 'N/A')[:24]}...")
    print(f"  - Verification Message    : {chain_info.get('message')}")
    assert chain_info["is_valid"] is True

    # Clean up test artifact
    if os.path.exists(test_pdf_path):
        os.remove(test_pdf_path)

    print("\n" + "=" * 80)
    print("ALL ACCEPTANCE CRITERIA SUCCESSFULLY VERIFIED AND COMPLIANT!")
    print("=" * 80)

if __name__ == "__main__":
    run_acceptance_test()
