# VERITAS Live Demonstration Runbook (SIH 2026)

## Overview & Five-Step Verification Flow

This runbook guides evaluators and judges through the end-to-end verification of an AICTE Extension of Approval (EoA) application package using **VERITAS**.

```
  [1. Ingest & Hash] ──> [2. Evidence Graph] ──> [3. Rules Engine] ──> [4. CV Forensics] ──> [5. Cryptographic Audit]
   SHA-256 & pyHanko      PyMuPDF Bounding Boxes   Statutory vs Tech    ELA, SRM, SIFT Clone   Tamper-Evident SHA-256 Chain
```

---

## 1. Environment Preparation & Safe Localhost Startup

> [!IMPORTANT]
> **Safe Localhost Isolation Policy**:
> For hackathon demonstration, always bind services to `127.0.0.1` (localhost). Do not bind to `0.0.0.0` on untrusted conference networks. `ENABLE_DEMO_TAMPER` must remain `false` in production environments and is enabled solely for demonstration purposes on localhost.

### Terminal 1: Backend API (FastAPI)
```powershell
# In workspace root
.venv\Scripts\Activate.ps1
$env:OFFICER_AUTH_TOKEN = "demo-sih-2026-officer-token"
$env:ENABLE_DEMO_TAMPER = "true"
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### Terminal 2: Frontend Dashboard (Next.js)
```powershell
cd frontend
$env:NEXT_PUBLIC_OFFICER_TOKEN = "demo-sih-2026-officer-token"
npm run dev
```
Open browser at: `http://localhost:3000`

---

## 2. Five-Step Demonstration Sequence

### Step 1: Ingest & Integrity Gating
1. Navigate to `http://localhost:3000`.
2. Upload the sample synthetic document package from `synthetic/cases/case_01/` *(simulated institutional filing for local demonstration)*:
   - `application_form.pdf`
   - `approval_letter.pdf`
   - `land_document.pdf`
   - `fire_noc.pdf`
   - `faculty_list.pdf`
3. Click **Ingest & Verify Application**.
4. **Demonstrable Proof**:
   - Each file is hashed using **SHA-256** and persisted under tenant-isolated storage (`storage/APP-XXXX`).
   - PyMuPDF extracts full-text, word coordinates, and metadata without cloud dependencies.
   - **pyHanko Digital Signature Inspection**: Evaluates embedded PKCS#7 signatures and distinguishes six states: `UNSIGNED`, `INTACT` (cryptographically valid under trust policy), `MODIFIED` (digest mismatch / tampered), `UNTRUSTED_SIGNER` (untrusted root CA), `UNAVAILABLE_VALIDATION_INFO`, and `UNSUPPORTED_OR_FAILED`.
   - Proves that mathematical signature validity is decoupled from AICTE regulatory authority.

---

### Step 2: Extraction & Evidence Graph
1. Click on the newly ingested application card (`APP-XXXX`).
2. Observe the **Evidence Graph**:
   - Fields extracted include `permanent_id`, `institution_name`, `declared_land_area`, `noc_number`, `valid_to`, `faculty_count`.
   - Each field displays its exact page number and bounding box coordinates `[x0, y0, x1, y1]`.
3. Demonstrates that verification is grounded in verifiable spatial coordinates, eliminating hallucinated text.

---

### Step 3: Rules Engine & Regulatory Traceability
1. View the findings table:
   - **Statutory Mandates**: Grounded in official AICTE Approval Process Handbook (APH) 2024–2027:
     - `AICTE-EOA-002` & `AICTE-EOA-005`: Fire Safety Certificate presence & validity (Chapter VI §6.17(i) & Annexure 2 §2.1(v)).
     - `AICTE-EOA-009`: Land Area Adequacy (Annexure 3 §3.1).
   - **Technical Consistency**: `AICTE-EOA-007` (Entity resolution), `AICTE-EOA-008` (PID check), `AICTE-EOA-006` (Prior year approval order reconciliation).
   - **Metadata Integrity**: `META-001` (ModDate earlier than CreationDate), `META-002` (Creation postdates filing), `META-003` (Parser warnings).
   - **Simulated External Registry Checks**: Note that external registry verification queries local demo fixtures (`fake_issuers.json`). Disconnected or unseeded registries yield `INDETERMINATE` without creating applicant compliance defects.
2. Note that metadata and forensic review flags explicitly state: *"Flagged for technical inspection; does not constitute proof of document forgery."*

---

### Step 4: Computer Vision Forensics & Steganalysis (Preliminary Forensic Screening)
1. Click on any finding to open the **Evidence Detail Inspector**.
2. Notice the **View Mode Toggle**:
   - **Evidence Box**: Renders PyMuPDF highlighted bounding boxes on the original page.
   - **ELA Heatmap**: Renders the **Inferno Error Level Analysis Heatmap**, exposing differential JPEG compression histories as candidate regions for inspection.
3. Observe the **Computer Vision Forensics Diagnostics Card** *(Preliminary Screening Indicators)*:
   - **Mean ELA Residual**: Quantifies localized compression variations.
   - **SRM Steganalysis Energy**: Measures high-frequency noise from Fridrich & Kodovsky 5x5 filters.
   - **Copy-Move Cloned Features**: Displays SIFT + FLANN + RANSAC geometric matches detecting duplicated stamps, seals, or signatures.
   - **Typography Outliers**: Lists short text tokens whose font stroke or height deviates by >30% from dominant body text using Otsu distance transform.
   - **Scan Quality Gating**: Laplacian blur score and HSV glare ratio warn officers of illegible uploads without false alarms on blank pages.
   - **2D QR Code Verification**: Decodes QR barcodes 100% offline with zero outbound network requests; verifies against official `aicte-india.org` / `gov.in` whitelist and strictly blocks SSRF probes (loopback, private subnets, cloud metadata, credentials in URLs, unusual ports).
   - **Advisory Boundary**: Emphasize to evaluators that computer vision detectors serve as advisory screening indicators for human officer scrutiny, never autonomous legal proof of alteration.

---

### Step 5: Cryptographic Audit Trail & Tamper Verification
1. On the application overview page, toggle **Show Audit Trail**.
2. Observe the cryptographic event ledger:
   - Every ingest, rule evaluation, external verification, and review action is cryptographically linked:
     $$\text{hash}_i = \text{SHA-256}(\text{hash}_{i-1} \parallel \text{timestamp} \parallel \text{app\_id} \parallel \text{action} \parallel \text{payload})$$
3. Click **Verify Hash Chain**:
   - Verification badge displays: *"Cryptographic Audit Chain Intact: All events verified from genesis."*
4. **Demonstrating Tamper-Evident Security**:
   - Click **Simulate Unauthorized Tamper (Demo)**.
   - Server validates that `ENABLE_DEMO_TAMPER=true` is set, officer credentials are verified, and `X-Demo-Mode: true` is passed.
   - Direct database payload mutation is simulated without updating the stored SHA-256 hash.
   - Click **Verify Hash Chain** again.
   - System immediately detects discrepancy: *"CHAIN_BROKEN at Event Index #X: Stored hash does not match computed SHA-256."*
   - Explains that this provides mathematical tamper-evidence for administrative integrity.
