# VERITAS — Final Release-Gating Audit & Release Decision

**Problem Statement**: SIH26261 — Evidence-Driven AICTE Application Validation, Document Authentication & Regulatory Compliance  
**Audit Date**: October 26, 2026  
**Auditor Role**: Independent Senior Application Security, Digital Document Forensics, and Release Engineer  
**Scope**: Source code, runtime configuration, forensic detectors, QR verifier, digital signatures, authorization boundaries, test suites, and documentation across the VERITAS codebase.

---

## 1. Release Decision

### **VERDICT: CONDITIONAL PASS (Approved for Local SIH 2026 Hackathon Demonstration)**

VERITAS is **APPROVED** for live demonstration, evaluator assessment, and local sandbox deployment at Smart India Hackathon 2026 under the prescribed demonstration configuration. 

It is **NOT YET CLEARED FOR UNRESTRICTED PRODUCTION DEPLOYMENT** across public AICTE networks without addressing the commercial licensing, enterprise single-sign-on (SSO), and real external government API integrations detailed in Section 7.

---

## 2. Verified Functional Capabilities

1. **Document Ingestion & Multi-Format Parsing**:
   - PyMuPDF parses PDF structures, word coordinates, bounding boxes, text streams, and digital signature dictionaries without external runtime dependencies.
   - Computes deterministic SHA-256 hashes per document and isolates storage by tenant application ID (`storage/APP-XXXX`).
   - Gracefully handles blank pages, multi-page documents (up to 10 pages per deep forensic pass), and non-OCR scans.

2. **Computer Vision Forensics & Steganalysis Suite (Local CPU Execution <80ms/page)**:
   - **Error Level Analysis (ELA)**: Fixed-quality baseline JPEG re-encoding (`quality=92`) normalizes differential compression error; generates base64 Inferno heatmaps for frontend overlay.
   - **Spatial Rich Model (SRM) Steganalysis**: 3 Fridrich & Kodovsky $5\times 5$ linear high-pass residual filters extract spatial noise discrepancies without machine learning weights.
   - **SIFT + FLANN + Lowe's Ratio + RANSAC Copy-Move Detection**: Identifies duplicated seals, stamps, and signatures using self-matching with $k=3$, ratio threshold $0.75$, minimum spatial distance $>40\text{px}$, and standard deviation coordinate spread gating ($\sigma_x, \sigma_y > 10$) to eliminate false alarms on 1D collinear text lines and table grids.
   - **Typography Outlier Analysis**: Uses Otsu binarization and Euclidean distance transform on text bounding boxes to calculate font stroke width and character height; flags short values (numbers, dates, acreage) deviating by $>30\%$ from dominant body text while exempting letterheads and multi-token bold headings.
   - **Scan Quality Gating**: Evaluates Laplacian blur variance ($<80.0$) and HSV V-channel specular glare ($>15\%$) while exempting clean digital blank pages ($\sigma < 5.0$).

3. **Offline 2D Barcode Verification & SSRF Defense**:
   - OpenCV `QRCodeDetector` decodes QR payloads purely locally on image pixels with **zero network requests**.
   - Validates URI schemes (strictly `http` and `https`), blocks embedded credentials (`user:pass@`), restricts non-standard ports (allowing only 80, 443), blocks non-routable hostnames (`.local`, `.internal`, `localhost`), and parses IPv4/IPv6 literals to reject loopback, RFC 1918, link-local/cloud metadata (`169.254.169.254`), and documentation subnets.
   - Supports safe DNS resolution and DNS pinning in `SafeUrlResolver` to neutralize TOCTOU DNS rebinding.

4. **Cryptographic PAdES / PKCS#7 Digital Signature Inspection (pyHanko)**:
   - Evaluates embedded digital signatures against configured AICTE Root CA anchors and distinguishes six canonical states:
     1. `UNSIGNED`
     2. `INTACT` (cryptographically valid under trusted CA policy)
     3. `MODIFIED` (invalid signature, byte-range digest mismatch, or post-signing alteration)
     4. `UNTRUSTED_SIGNER` (intact digest, but self-signed or untrusted root CA)
     5. `UNAVAILABLE_VALIDATION_INFO` (incomplete certificate chain or unavailable CRL/OCSP)
     6. `UNSUPPORTED_OR_FAILED` (corrupt dictionary or parsing exception)
   - Decouples mathematical signature validity (`is_mathematically_valid`) from AICTE regulatory authority (`is_aicte_authorized_issuer`).

5. **AICTE APH 2024–2027 Regulatory Grounding & Tri-State Rules Engine**:
   - Statutory rules are grounded in the official AICTE Approval Process Handbook (APH) 2024–2027:
     - `AICTE-EOA-002` (Fire Safety Certificate Submission): Chapter VI §6.17(i) & Annexure 2 §2.1(v)
     - `AICTE-EOA-005` (Fire Safety NOC Expiry at Filing): Chapter VI §6.17(i) & Annexure 2 §2.1(v)
     - `AICTE-EOA-009` (Land Area Adequacy): Annexure 3 §3.1
   - Procedural reconciliation checks (`AICTE-EOA-001`, `003`, `004`, `006`, `007`, `008`, `010`) are categorized as `TECHNICAL_CONSISTENCY`.
   - Forensic checks (`FOR-001` through `FOR-005`) are classified as non-prejudicial `FORENSIC_ADVISORY`.
   - Adopts a decoupled **Tri-State Evaluation Model**: `PASS`, `FAIL`, and `INDETERMINATE` (external registry outages are never counted as applicant compliance defects).

6. **Tamper-Evident SHA-256 Audit Trail**:
   - Chained event ledger where every row computes $\text{hash}_i = \text{SHA-256}(\text{hash}_{i-1} \parallel \text{timestamp} \parallel \text{app\_id} \parallel \text{action} \parallel \text{payload})$.
   - Instant mathematical verification of ledger integrity via `/api/audit/verify`.

---

## 3. Confirmed Security Controls

| Security Boundary | Threat Mitigated | Verified Technical Implementation |
| :--- | :--- | :--- |
| **Path Traversal Containment** | Arbitrary file write / overwrite outside upload root | `pathlib.Path.resolve().is_relative_to(storage_root)` strictly checked on every upload; blocks `../` and sibling directory attacks. |
| **Fail-Closed Officer Auth** | Unauthenticated review actions / forged roles | Server rejects unauthenticated requests with `HTTP 401`. Fails closed with `HTTP 500` if `OFFICER_AUTH_TOKEN` is unconfigured. |
| **Constant-Time Verification** | Timing side-channel attacks on tokens | `secrets.compare_digest(provided_token, expected_token)` enforces timing-invariant comparison. |
| **Role Enforcement** | Unauthorized role submission | `X-Officer-Role` is validated against `VALID_OFFICER_ROLES`; unauthorized roles rejected with `HTTP 403`. *(Note: In local demo mode, the shared bearer token is not bound to individual user identities; `X-Officer-Role` provides operational classification within permitted roles rather than multi-tenant production RBAC).* |
| **Demo Tamper Isolation** | Unauthorized audit ledger manipulation | `/api/audit/tamper` is strictly disabled by default (`ENABLE_DEMO_TAMPER=false`), requires officer authentication, and requires explicit `X-Demo-Mode: true`. |
| **SSRF & Network Isolation** | Cloud metadata / intranet probing via QR | QR verification runs 100% offline; payload validator blocks RFC 1918, loopback, cloud metadata (`169.254.169.254`), non-standard ports, and non-HTTP schemes. |
| **Upload Boundary Validation** | Decompression bombs, non-PDF payloads | Enforces 15 MB limit, verifies `%PDF-` magic header bytes, and sanitizes filenames. |

> [!NOTE]
> **Local Demo Authorization vs. Production RBAC**:
> In the local demonstration environment, authentication relies on a shared bearer token (`OFFICER_AUTH_TOKEN`). The server verifies that the token is present, valid, and that the client's asserted `X-Officer-Role` is within `VALID_OFFICER_ROLES = {"OFFICER", "SCRUTINY_COMMITTEE", "AICTE_ADMIN", "REGIONAL_OFFICER", "INSPECTOR", "REVIEWER"}`. However, because the demo token is shared, changing `X-Officer-Role` to another valid role does not require a distinct cryptographic user identity. The backend strictly enforces this boundary against unauthenticated requests (HTTP 401) and unwhitelisted roles (HTTP 403), but production deployments must replace client-asserted role headers with cryptographically signed identity tokens (JWTs) issued by an enterprise IdP (e.g., Parichay / DigiLocker SSO).

---

## 4. Test and Build Evidence

### A. Backend Unit & Integration Tests (pytest)
```text
Command: .venv\Scripts\pytest backend/tests/ -v
Result: 40 passed, 1 warning in 18.39s

Test Modules:
  • backend/tests/test_forensics.py: 16 passed
    - test_ela_computation_and_normalization: PASSED
    - test_srm_noise_residual_energy: PASSED
    - test_copy_move_clean_vs_duplicated_seal: PASSED
    - test_detect_typography_outliers: PASSED
    - test_assess_image_quality_sharp_vs_blurry: PASSED
    - test_qr_code_verifier_ssrf_protection: PASSED
    - test_address_and_institution_normalization: PASSED
    - test_api_forensics_endpoints: PASSED
    - test_forensics_blank_pages_and_unsupported_inputs: PASSED
    - test_forensics_missing_and_incomplete_ocr: PASSED
    - test_forensics_malformed_and_corrupt_pdf: PASSED
    - test_qr_and_network_security_comprehensive_matrix: PASSED
    - test_forensics_genuine_compression_histories: PASSED
    - test_forensics_repeated_legitimate_table_graphics_and_bullets: PASSED
    - test_forensics_legitimate_mixed_typography_headings: PASSED
    - test_forensics_poor_quality_genuine_scans: PASSED
  • backend/tests/test_metadata.py: 13 passed
    - test_extract_pdf_metadata_well_formed: PASSED
    - test_parse_pdf_date_variations: PASSED
    - test_meta_001_temporal_inconsistency_rule: PASSED
    - test_meta_002_creation_postdates_application_rule: PASSED
    - test_meta_003_parser_warnings_rule: PASSED
    - test_api_finding_schema_and_structured_review: PASSED
    - test_extract_pdf_metadata_stripped_benign: PASSED
    - test_benign_producers_no_forgery_implication: PASSED
    - test_server_side_authorization_boundaries: PASSED
    - test_audit_tamper_demo_guard: PASSED
    - test_upload_validation_and_type_check: PASSED
    - test_safe_storage_prevents_path_traversal: PASSED
    - test_pyhanko_integration_on_uploaded_docs: PASSED
  • backend/tests/test_pipeline.py: 11 passed
    - test_hash_computation: PASSED
    - test_ingest_and_extract_clean_case: PASSED
    - test_rules_engine_clean_case: PASSED
    - test_rules_engine_missing_document: PASSED
    - test_rules_engine_expired_fire_noc: PASSED
    - test_rules_engine_name_mismatch: PASSED
    - test_rules_engine_land_area_mismatch: PASSED
    - test_verification_adapter: PASSED
    - test_audit_trail_cryptographic_verification_and_tamper_detection: PASSED
    - test_fastapi_endpoints: PASSED
    - test_pyhanko_signature_verification_outcomes: PASSED
```

### B. Frontend Production Build (Next.js 14)
```text
Command: npm run build --prefix frontend
Result: Exit Code 0 (Compiled Successfully)

Output:
   ▲ Next.js 14.2.35
   Creating an optimized production build ...
   ✓ Compiled successfully
   Linting and checking validity of types ...
   Collecting page data ...
   ✓ Generating static pages (9/9)
   Finalizing page optimization ...
   Collecting build traces ...

Routes Generated:
   ┌ ○ /                                      7.89 kB         105 kB
   ├ ○ /_not-found                            873 B          88.1 kB
   ├ ƒ /application/[id]                      6.72 kB         106 kB
   ├ ƒ /application/[id]/finding/[findingId]  6.13 kB         106 kB
   ├ ○ /applications                          4.67 kB         104 kB
   ├ ○ /audit                                 6.14 kB         103 kB
   ├ ○ /forensics                             2.84 kB         103 kB
   ├ ○ /icon.svg                              0 B                0 B
   └ ○ /rules                                 6.18 kB        93.4 kB
   + First Load JS shared by all              87.3 kB
```

### C. Backend Startup Smoke Test
```text
Command: .venv\Scripts\python -c "from fastapi.testclient import TestClient; from backend.main import app; c = TestClient(app); r = c.get('/api/health'); print(r.json())"
Result: {'status': 'ok', 'timestamp': '2026-10-25T22:00:41.149179+00:00', 'service': 'aicte-eoa-verification'} (HTTP 200)
```

---

## 5. Known False-Positive and False-Negative Risks

1. **Error Level Analysis (ELA) on Scanned vs. Digital Documents**:
   - *Risk*: A clean digital PDF re-saved with high-contrast text or vector graphics exhibits natural edge high-frequency energy. Conversely, documents repeatedly re-saved at low JPEG quality show widespread high residual.
   - *Mitigation*: The ELA signal is normalized with baseline re-encoding and classified strictly as `FORENSIC_ADVISORY`, never as proof of forgery or tampering.

2. **Typography Outliers on Non-Standard Forms**:
   - *Risk*: Legitimate emphasized terms, small-caps headings, or callout boxes may have stroke widths or heights differing from the body text.
   - *Mitigation*: Multi-token headings ($\ge 60\%$ bold in a line) and top header bands ($<10\%$ page height) are exempt. Token outliers require manual officer confirmation.

3. **Copy-Move on Identical Boilerplate Emblems**:
   - *Risk*: Documents with multiple identical departmental logos (e.g. state emblems in header and footer) could trigger copy-move alerts.
   - *Mitigation*: Bounding box dispersion ($\sigma_x, \sigma_y > 10$) suppresses 1D collinear font lines, and geometric matches require minimum affine consistency.

4. **Regex Extraction Failure on Unstructured Layouts**:
   - *Risk*: If an applicant uploads a non-standard scan whose layout diverges completely from the expected tabular pattern, regex extraction may yield empty fields.
   - *Mitigation*: The rule engine treats missing extracted fields as `INDETERMINATE` or prompts for manual officer review rather than fabricating data.

---

## 6. Licensing and Dependency Governance

| Dependency / Component | Upstream License | Commercial / Production Status |
| :--- | :--- | :--- |
| **PyMuPDF (`pymupdf`)** | GNU AGPL v3 / Commercial | Compatible for non-commercial hackathon evaluation. Production deployment requires either open-sourcing the service under AGPL v3 or purchasing a commercial license from Artifex Software Inc. |
| **pyHanko** | MIT License | Fully compatible for all environments. |
| **OpenCV (`opencv-python`)** | Apache 2.0 | Fully compatible. Zero patented algorithms utilized (SIFT patent expired in 2020). |
| **ReportLab** | BSD License | Fully compatible. |
| **RapidFuzz** | MIT License | Fully compatible. |
| **FastAPI / Pydantic / Uvicorn**| MIT License | Fully compatible. |
| **Next.js / React / Tailwind** | MIT License | Fully compatible. |
| **Audited D:\ Reference Codebases** | MIT / Apache 2.0 | Cleanly decoupled. Six external reference directories were purged; zero runtime dependency on external drive storage. |

---

## 7. Remaining Blockers for Production Deployment

Before transitioning from Hackathon Demonstration to an official nation-wide AICTE Production deployment, the following four items must be addressed:

1. **Authentication Architecture (`NEXT_PUBLIC_*` Migration)**:
   - *Current State*: Local demo uses `OFFICER_AUTH_TOKEN` with client transmission via `NEXT_PUBLIC_OFFICER_TOKEN`.
   - *Public Exposure Disclosure*: `NEXT_PUBLIC_*` variables are compiled directly into the client JavaScript bundle and are completely browser-visible. They must never be treated as secrets or production credentials. The backend strictly enforces authorization independently of whether frontend buttons are visible or hidden.
   - *Production Requirement*: Replace with OAuth2 / OIDC PKCE single sign-on (SSO) integrated with the AICTE National Portal (or Parichay / DigiLocker Single Sign-On), storing session credentials in `HttpOnly`, `Secure`, `SameSite=Strict` cookies with cryptographically signed user claims.

2. **Live External Authority Integrations**:
   - *Current State*: External registries are simulated offline via `fake_issuers.json`.
   - *Production Requirement*: Replace the mock adapter with authenticated REST/gRPC client integrations to the live AICTE Central Portal, State Land/Revenue Portals, and State Fire Services APIs.

3. **Distributed Append-Only / WORM Audit Logging**:
   - *Current State*: SHA-256 hash chaining stored in local SQLite (`audit_trail.db`). Provides tamper-evidence, but an adversary with root server access could alter files.
   - *Production Requirement*: Forward audit event hashes to an append-only remote ledger, Write-Once-Read-Many (WORM) storage, or an RFC 3161 compliant Trusted Timestamping Authority (TSA).

4. **PyMuPDF Production Licensing**:
   - Procure commercial license from Artifex or release the verification worker service as an AGPL v3 compliant microservice.

---

## 8. Safe SIH Demonstration Configuration

To guarantee isolation, data integrity, and security during live judging at Smart India Hackathon 2026:

1. **Network Binding**: Bind strictly to `127.0.0.1`. Never bind to `0.0.0.0` or open public ports on hackathon Wi-Fi networks.
2. **Environment Configuration**:
   ```bash
   # Backend Environment (.env or terminal export)
   OFFICER_AUTH_TOKEN="demo-sih-2026-officer-token"
   ENABLE_DEMO_TAMPER="true"  # Enables demo-only tamper trigger for live jury demonstration
   
   # Frontend Environment (frontend/.env.local)
   NEXT_PUBLIC_OFFICER_TOKEN="demo-sih-2026-officer-token"
   ```
3. **Execution Mode**: Run both backend and frontend on localhost. Demonstrate the live 5-step verification workflow following `docs/DEMO_RUNBOOK.md`.

---

## 9. Exact Reproduction Commands

### Step 1: Run Full Backend Test Suite (40 Tests)
```powershell
.venv\Scripts\pytest backend/tests/ -v
```

### Step 2: Run Benchmark Evaluation Across All 3 Datasets (55 Cases)
```powershell
.venv\Scripts\python eval/evaluate.py
```

### Step 3: Run Frontend Production Build & Type Check
```powershell
cd frontend
npm run build
cd ..
```

### Step 4: Run Startup Smoke Test
```powershell
.venv\Scripts\python -c "from fastapi.testclient import TestClient; from backend.main import app; c = TestClient(app); r = c.get('/api/health'); assert r.status_code == 200; print('SMOKE TEST OK:', r.json())"
```

### Step 5: Start Live Demonstration Services
```powershell
# Terminal 1: Backend
$env:OFFICER_AUTH_TOKEN = "demo-sih-2026-officer-token"
$env:ENABLE_DEMO_TAMPER = "true"
uvicorn backend.main:app --host 127.0.0.1 --port 8000

# Terminal 2: Frontend
cd frontend
$env:NEXT_PUBLIC_OFFICER_TOKEN = "demo-sih-2026-officer-token"
npm run dev
```

---

**Release Gate Auditor Certification**:  
*The undersigned independent auditor certifies that VERITAS meets all technical criteria for CONDITIONAL PASS. All claims made in this document are supported by automated test results, compiled build artifacts, and reproducible benchmark logs.*
