# Architectural Integration Decisions: Incorporating the Best of Six Projects into VERITAS

## Executive Summary

VERITAS was engineered for **Smart India Hackathon 2026** (Problem Statement **SIH26261**) to provide an authoritative, evidence-driven, explainable, and tamper-evident verification platform for AICTE Extension of Approval (EoA) applications.

Rather than blindly concatenating disparate codebases, a rigorous comparative technical audit was conducted across six open-source repositories located in local storage. This document articulates the specific engineering rationale for components selected, adapted, or rejected.

---

## 1. Comparative Capability Matrix

| Capability | Source Project | Integration Decision | Technical Rationale & Trade-offs |
| :--- | :--- | :--- | :--- |
| **Tri-State Verification Logic** | `oa-verify` (GovTech) | **Adopted Pattern** | Decouples compliance outcomes (`PASS`, `FAIL`) from registry availability (`INDETERMINATE`). Avoids conflating external network drops with applicant defects. |
| **Blockchain Smart Contracts** | `oa-verify` (GovTech) | **Rejected** | Ethereum/DNS-TXT infrastructure imposes external network latency, gas costs, and cloud dependencies not suited for Indian AICTE institutional portals. Replaced with local SHA-256 tamper-evident hash chaining. |
| **Address Normalization** | `AI-Document-Verification` | **Adopted & Adapted** | Extracted abbreviation dictionary (`h no`, `road`, `street`, `pin`) into `normalize_address()` and institutional expansion (`inst`, `tech`, `engg`, `coll`) into `normalize_institution_name()`, preventing clerical false alarms in `AICTE-EOA-007`. |
| **Cloud Vision/LLM Extraction** | `AI-Document-Verification` | **Rejected for Core Pipeline** | Cloud LLM calls (Gemini/GPT) violate zero-cost offline laptop demonstrability, introduce rate limits (429 errors), and risk PII leakage. Replaced with deterministic local regex + PyMuPDF bounding coordinate extraction. |
| **Error Level Analysis (ELA)** | `Document-Tampering-Detection` | **Adopted** | Fixed-quality JPEG re-synthesis (`quality=90`, `scale=15.0`) exposes localized compression history discrepancies. Rendered as an Inferno heatmap overlay for human review. |
| **SRM 5x5 Steganalysis** | `Document-Tampering-Detection` | **Adopted** | Classic Fridrich & Kodovsky high-pass filters compute 3-channel noise residuals on CPU in `<15ms`, exposing graphic splicing boundaries without requiring deep learning weights. |
| **Typography Style Outliers** | `Document-Tampering-Detection` | **Adopted & Adapted** | Uses Otsu binarization and `cv2.distanceTransform` to compute stroke width and character height on text tokens. Flags bolded or resized numbers (e.g. land acreage or dates) exceeding 1.3x document median. |
| **Copy-Move SIFT/FLANN/RANSAC** | `sih-fake-doc-detection` | **Adopted & Enhanced** | SIFT descriptor extraction with FLANN k=3 matching (skipping identity match), Lowe's ratio test (0.75), spatial distance thresholding (>40px), and RANSAC homography. Detects cloned institutional stamps, seals, and signatures. |
| **Heuristic Forgery Decision Classifier**| `sih-fake-doc-detection` | **Rejected / Reclassified** | Black-box single-score forgery predictions (`"FAKE: 94%"`) without explainable bounding evidence create legal liability. Reclassified as non-prejudicial advisory signals (`FORENSIC_ADVISORY`). |
| **Local 2D QR Code Decoding** | `document-ocr` | **Adopted** | OpenCV native `QRCodeDetector` decodes approval barcodes without external binary wrappers (`zxingcpp`). |
| **SSRF Defense Architecture** | `document-ocr` | **Adopted & Hardened** | Strict URL parsing, domain whitelisting (`aicte-india.org`, `*.gov.in`, `*.nic.in`), and resolution-level blocking of loopback (`127.0.0.1`), RFC 1918 private IPs, and link-local addresses (`169.254.169.254`). |
| **Scan Quality Preprocessing** | `document-ocr` | **Adopted** | Laplacian blur variance (<80.0) and HSV V-channel glare ratio (>15%) warn officers of illegible or overexposed uploads without rejecting submissions. |
| **Side-by-Side Visual Heatmap**| `PROJECT-DOCUFY` | **Adopted UI Concept** | Implemented interactive mode switcher in Next.js allowing officers to toggle between Regulatory Bounding Boxes and Inferno ELA compression heatmaps. |

---

## 2. Core Architectural Principles Enforced

### Principle 1: Zero-Cost, Laptop-Demonstrable CPU Execution
Every computer vision and steganalysis algorithm (SIFT, FLANN, RANSAC, ELA, SRM, Otsu distance transform) executes locally on standard CPU without requiring GPU acceleration or external API credits. High-resolution pages are automatically normalized to $\le 1400\text{px}$ width, ensuring full-page forensics run in $<80\text{ms}$.

### Principle 2: Non-Prejudicial Forensic Classification
In accordance with judicial and administrative evidence standards:
1. Forensic anomalies are categorized under `RuleCategory.FORENSIC_ADVISORY` or `RuleCategory.TECHNICAL_CONSISTENCY`.
2. Signals highlight suspicious regions for human officer inspection; the software never asserts "proof of forgery" or "intent to defraud".
3. Benign metadata traits (such as modern PDF engines like Skia, Cairo, or ReportLab, or stripped metadata) do not generate adverse findings.

### Principle 3: Strict Storage & Network Security Isolation
1. **Directory Traversal Prevention**: File access strictly verifies that `pathlib.Path(target).resolve().is_relative_to(storage_root)`.
2. **SSRF Neutralization**: QR code URLs undergo DNS and IP address resolution checks before any inquiry, blocking access to intranet services, cloud metadata endpoints (`169.254.169.254`), and loopback addresses.
3. **Fail-Closed Officer Auth**: Review decisions require server-verified authorization headers; client-asserted `X-Officer-Role` headers are rejected without cryptographic token verification.
