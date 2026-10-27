# Third-Party Licences & Project Attribution

VERITAS gratefully acknowledges the concepts, algorithms, and open-source foundations adapted from research repositories and libraries. In compliance with open-source software governance, this document records all adapted code, runtime dependencies, licenses, and open review items.

> [!NOTE]
> **Licensing Obligation Notice**:
> The physical removal of the six reference repositories from local disk storage does not terminate copyright attribution obligations. All algorithms, concepts, and normalization patterns adapted into VERITAS remain attributed to their respective upstream authors under their declared open-source terms.

---

## 1. Audited Source Repositories & Adapted Algorithms

### 1. OpenAttestation (`@govtechsg/oa-verify`)
* **Original Author**: Government Technology Agency of Singapore (GovTech)
* **Declared License**: Apache License 2.0
* **Attributed Concepts**:
  - Tri-State Verification Architecture (`PASS`, `FAIL`, `INDETERMINATE`).
  - Strict decoupling of external registry availability from intrinsic document compliance.

### 2. AI-Document-Verification-System
* **Original Author**: Open-Source Contributors
* **Declared License**: MIT-compatible open script
* **Attributed Concepts**:
  - Cross-document entity name and address abbreviation expansion (`normalize_address`, `normalize_institution_name`) to eliminate clerical false alarms.

### 3. Document-Tampering-Detection
* **Original Author**: Academic Forensics Research Community
* **Declared License**: MIT License / Academic Reference
* **Attributed Concepts**:
  - Error Level Analysis (ELA) with baseline JPEG recompression normalization (based on Krawetz, 2007).
  - Spatial Rich Model (SRM) 3-kernel 5x5 steganalysis high-pass noise residuals (Fridrich & Kodovsky, 2012).
  - Typographical font stroke-width and height outlier detection using Otsu binarization and `cv2.distanceTransform`.

### 4. sih-fake-doc-detection
* **Original Author**: SIH Team & Open-Source Contributors
* **Declared License**: MIT License
* **Attributed Concepts**:
  - Scale-Invariant Feature Transform (SIFT) feature extraction, FLANN nearest-neighbor matching ($k=3$), Lowe's ratio test ($0.75$), and RANSAC geometric homography filtering to detect cloned seals, stamps, and duplicated signatures.

### 5. document-ocr
* **Original Author**: Open-Source Contributors
* **Declared License**: Apache License 2.0
* **Attributed Concepts**:
  - Local 2D QR barcode extraction via OpenCV without external binary wrappers.
  - SSRF defense architecture (URI scheme validation, loopback and private RFC 1918 IP address blocking, cloud metadata link-local isolation).
  - Scan quality gating (Laplacian blur variance and HSV glare ratio).

### 6. PROJECT-DOCUFY
* **Original Author**: Open-Source Prototype Contributors
* **Declared License**: MIT License
* **Attributed Concepts**:
  - Visual Inferno ELA heatmap representation for human document review.

---

## 2. Core Runtime Python & Node.js Dependencies

| Library | Declared License | Role in VERITAS Architecture |
| :--- | :--- | :--- |
| **OpenCV (`opencv-python`)** | Apache 2.0 | SIFT feature detection, FLANN matcher, RANSAC homography, JPEG re-encoding, distanceTransform, and QR decoding. |
| **PyMuPDF (`pymupdf` / fitz)** | AGPL v3 / Commercial | Fast C-level PDF parsing, text extraction, word bounding box coordinate mapping, and page pixmap rasterization. |
| **pyHanko** | MIT License | PAdES / PKCS#7 digital signature validation, byte-range digest verification, and ASN.1 certificate chain inspection. |
| **asn1crypto** | MIT License | X.509 certificate parsing and PEM unarmoring for cryptographic trust root anchors. |
| **ReportLab** | BSD License | Synthetic regulatory document generation for test suite evaluation. |
| **RapidFuzz** | MIT License | High-speed C++ token sort ratio entity resolution for cross-document consistency checks. |
| **FastAPI & Uvicorn** | MIT License | Asynchronous REST API framework and ASGI web server. |
| **Pydantic** | MIT License | Strict request/response data validation and schema enforcement. |
| **Next.js & React** | MIT License | Server-rendered officer review dashboard and client state management. |
| **Tailwind CSS & Lucide React** | MIT License | Glassmorphism UI styling and vector iconography. |

---

## 3. Unresolved Upstream Licensing Considerations & Legal Review Items

1. **PyMuPDF Dual-Licensing (AGPL v3 vs. Commercial)**:
   - PyMuPDF is licensed under the GNU Affero General Public License (AGPL) v3, with commercial licenses available from Artifex Software Inc.
   - For internal hackathon evaluation, research, and non-commercial demonstrations, AGPL v3 is fully compatible.
   - *Legal Note for Production Release*: If VERITAS is deployed as a public or institutional network service for AICTE, the platform must either be open-sourced under the AGPL v3 or a commercial licensing agreement must be procured from Artifex Software.

2. **Zero Deep Learning Weight Dependencies**:
   - VERITAS deliberately avoids bundling or depending on opaque machine learning model weights (e.g. YOLO `.pt` or U-Net `.pth` files).
   - All computer vision algorithms (SIFT, FLANN, RANSAC, ELA, SRM, Otsu distance transform) execute via deterministic mathematical implementations, completely eliminating dataset provenance and model weight licensing uncertainties.

3. **Synthetic Dataset Provenance**:
   - All evaluation cases in `synthetic/cases/`, `eval/held_out_cases/`, and `eval/fresh_test_cases/` were programmatically synthesized using ReportLab.
   - No copyrighted real-world institutional or applicant PII documents are bundled in the repository.
