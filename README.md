# VERITAS: Evidence-Driven AICTE EoA Application Validation, Document Forensics & Regulatory Compliance Platform

[![Smart India Hackathon 2026](https://img.shields.io/badge/SIH-2026-blue.svg)](https://sih.gov.in)
[![Problem Statement](https://img.shields.io/badge/Problem%20Statement-SIH26261-orange.svg)](https://sih.gov.in)
[![Backend Tests](https://img.shields.io/badge/Backend%20Tests-40%2F40%20Passing-brightgreen.svg)]()
[![Next.js Frontend](https://img.shields.io/badge/Frontend-Next.js%2014%20App%20Router-black.svg)]()
[![Forensic Execution](https://img.shields.io/badge/Forensics%20Latency-%3C80ms%20%2F%20page-success.svg)]()

> **VERITAS** is an explainable, evidence-driven AICTE Extension of Approval (EoA) verification platform. It automates regulatory document validation, extracts exact coordinate-grounded evidence, runs CPU-bounded computer vision forensics (Error Level Analysis, Steganalysis, Copy-Move detection), and tamper-evidently logs every officer determination to a cryptographic SHA-256 hash chain.

---

## 🌟 Key Capabilities

### 1. Statutory Regulatory Traceability
* Grounded strictly in the official **AICTE Approval Process Handbook (APH) 2024–2027**:
  * **Fire Safety Certificate (`AICTE-EOA-002` & `AICTE-EOA-005`)**: Mandatory under **Chapter VI §6.17(i)** and **Annexure 2 §2.1(v)**. Evaluates actual certified `valid_to` against the application filing date.
  * **Land Area Adequacy (`AICTE-EOA-009`)**: Validates declared acreage against conditional norms prescribed in **Annexure 3 §3.1** based on intake and location.
* Distinct separation of statutory mandates from technical consistency checks (`AICTE-EOA-007` entity resolution, `AICTE-EOA-008` PID check) and advisory metadata checks.

### 2. High-Speed Local Computer Vision Forensics (<80ms per page on CPU)
* **Error Level Analysis (ELA)**: Fixed-quality JPEG re-encoding (`quality=90`, `scale=15.0`) exposes localized graphic splicing, rendered via an interactive Inferno colormap heatmap overlay.
* **Spatial Rich Model (SRM) Steganalysis**: 3 classic Fridrich & Kodovsky 5x5 high-pass kernels expose high-frequency noise discrepancies without requiring machine learning model weights.
* **SIFT + FLANN + RANSAC Copy-Move Detection**: Detects cloned institutional stamps, seals, and duplicated signatures using keypoint self-matching ($k=3$) and geometric inlier verification.
* **Typography Style Outlier Detection**: Otsu binarization and `cv2.distanceTransform` calculate token stroke width and character height, flagging bolded or oversized altered numbers/dates.
* **Scan Quality Gating**: Laplacian blur variance (<80.0) and HSV V-channel glare ratio (>15%) identify compromised uploads.
* **Offline 2D QR Code Verification & SSRF Defense**: Locally decodes approval letter QR codes via OpenCV, verifies official regulatory domains (`aicte-india.org`, `*.gov.in`), and blocks loopback, private RFC 1918 subnets, and cloud metadata IPs (`169.254.169.254`).

### 3. Cryptographic Tamper-Evident Audit Trail
* Every ingestion, rule evaluation, external registry check, and human officer review is linked in a SHA-256 hash chain:
  $$\text{hash}_i = \text{SHA-256}(\text{hash}_{i-1} \parallel \text{timestamp} \parallel \text{action} \parallel \text{payload})$$
* Instantaneous verification (`/api/audit/verify`) mathematically proves ledger integrity from the genesis block.

---

## 🚀 Quick Start & Installation

### Prerequisites
* Python 3.12 or 3.13
* Node.js 18+ and npm

### 1. Backend Setup
```powershell
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r backend/requirements.txt
pip install opencv-python

# Set environment variables and launch FastAPI (strictly bind to localhost for demo security)
$env:OFFICER_AUTH_TOKEN = "demo-sih-2026-officer-token"
$env:ENABLE_DEMO_TAMPER = "true"
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Frontend Setup
```powershell
cd frontend
npm install
$env:NEXT_PUBLIC_OFFICER_TOKEN = "demo-sih-2026-officer-token"
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 🧪 Testing & Verification

Run the full automated test suite (40 unit & integration tests):
```powershell
.venv\Scripts\pytest backend/tests/ -v
```

Compile the Next.js production build:
```powershell
npm run build --prefix frontend
```

Execute the 55-case benchmark evaluation:
```powershell
python eval/evaluate.py
```

---

## 📚 Technical Documentation

Detailed architecture reports and runbooks are available in the [`docs/`](docs/) directory:
* [Final Release Gate (`docs/FINAL_RELEASE_GATE.md`)](docs/FINAL_RELEASE_GATE.md): Final release audit, verified test evidence, security boundaries, and production roadmap.
* [Source Project Audit (`docs/SOURCE_PROJECT_AUDIT.md`)](docs/SOURCE_PROJECT_AUDIT.md): Detailed comparative audit of the 6 cloned reference projects.
* [Integration Decisions (`docs/INTEGRATION_DECISIONS.md`)](docs/INTEGRATION_DECISIONS.md): Architectural decisions and selection/rejection rationale.
* [Threat Model (`docs/THREAT_MODEL.md`)](docs/THREAT_MODEL.md): Attack surface analysis, path traversal mitigations, SSRF defenses, and role authorization.
* [Evaluation Report (`docs/EVALUATION_REPORT.md`)](docs/EVALUATION_REPORT.md): Tri-state evaluation metrics across 55 cases, forensic execution latency, and synthetic data disclosures.
* [Demo Runbook (`docs/DEMO_RUNBOOK.md`)](docs/DEMO_RUNBOOK.md): Step-by-step presentation script for the five-step hackathon demo.
* [Licences & Attribution (`docs/LICENCES_AND_ATTRIBUTION.md`)](docs/LICENCES_AND_ATTRIBUTION.md): Third-party notices and open-source acknowledgements.
