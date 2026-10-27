# VERITAS Threat Model & Security Architecture

## 1. Threat Vectors and Attack Surfaces

As an automated regulatory compliance, digital document forensics, and audit platform for technical education institutions, VERITAS defends against both applicant fraud and external adversarial exploitation.

```
       [ Malicious PDF Upload ]                [ Attacker Manipulating QR Code ]
                 │                                              │
                 ▼                                              ▼
    ┌───────────────────────────┐                  ┌───────────────────────────┐
    │  Ingestion & Storage      │                  │  Offline QR Code Verifier │
    │  • Path Traversal         │                  │  • SSRF to Cloud Metadata │
    │  • Decompression Bombs    │                  │  • Private Subnet Probing │
    │  • Sibling Prefix Escapes │                  │  • Disallowed URI Schemes │
    │  • MIME/Magic Byte Mismatch│                 │  • Embedded Credentials   │
    └─────────────┬─────────────┘                  └─────────────┬─────────────┘
                  │                                              │
                  ▼                                              ▼
    ┌───────────────────────────┐                  ┌───────────────────────────┐
    │  PyMuPDF & Steganalysis   │                  │  Officer Authorization    │
    │  • Memory Exhaustion      │                  │  • Forged X-Officer-Role  │
    │  • Collinear FP Flooding  │                  │  • NEXT_PUBLIC_* Leakage  │
    │  • Unhandled Blank Pages  │                  │  • Demo Mode Isolation    │
    └─────────────┬─────────────┘                  └─────────────┬─────────────┘
                  │                                              │
                  ▼                                              ▼
    ┌──────────────────────────────────────────────────────────────────────────┐
    │       Cryptographic Audit Trail (SHA-256 Tamper-Evident Hash Chain)      │
    │       • Direct SQLite Manipulation  • Row Modification Detection        │
    │       • Note: Tamper-Evident Ledger; Not Distributed Immutable Ledger    │
    └──────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Threat Analysis & Verified Mitigations

### Threat 1: Malicious Document Ingestion & Storage Escape
* **Attack Scenario**: An attacker uploads a file named `../../../../etc/passwd` or `../storage_evil/payload.pdf` to overwrite system files or escape the tenant storage boundary.
* **Vulnerability in Naive Code**: Using `os.path.abspath(target).startswith(BASE_DIR)` allows sibling-directory bypasses (e.g., `BASE_DIR = "/app/storage"` matches `"/app/storage_evil/payload"`).
* **VERITAS Mitigation**:
  - Employs Python 3.12+ `pathlib.Path.resolve().is_relative_to(storage_root)`. This fully resolves symbolic links and strictly enforces path containment within the designated application tenant directory.
  - Enforces `MAX_UPLOAD_BYTES = 15 * 1024 * 1024` (15 MB), rejects 0-byte uploads, normalizes filenames with regex `[^a-zA-Z0-9_\-\.]`, and inspects `%PDF-` file magic header bytes before invoking PDF parsers.

---

### Threat 2: Server-Side Request Forgery (SSRF) via QR Barcodes
* **Attack Scenario**: An applicant crafts an approval letter with an embedded 2D QR barcode linking to cloud instance metadata (`http://169.254.169.254/latest/meta-data`), local loopback (`http://127.0.0.1:8000`), internal databases (`http://192.168.1.1:6379`), IPv6 loopback (`http://[::1]`), or internal hostnames (`http://metadata.google.internal`).
* **Vulnerability in Naive Code**: Automatic client fetches or unvalidated URL parsing allow attackers to exfiltrate cloud credentials, query intranet services, or perform port scanning.
* **VERITAS Implementation & Scope (`backend/verify/qr_verifier.py`)**:
  - **100% Offline QR Decoding**: OpenCV's `cv2.QRCodeDetector()` executes purely locally on rendered image bitmaps. QR decoding itself **never** makes network requests.
  - **Scheme Whitelist**: Strictly restricts schemes to `http` and `https`. Disallows `file://`, `gopher://`, `ftp://`, `data:`, `javascript:`, and all other protocols.
  - **Embedded Credentials Blocked**: URLs containing userinfo (e.g. `http://user:password@host`) are immediately rejected.
  - **Port Gating**: Only standard web ports (80, 443, or omitted) are permitted. Non-standard ports (e.g. `:22`, `:6379`, `:8080`, `:8443`) trigger immediate rejection (`SSRF_REJECTED`).
  - **Restricted Hostnames & Suffixes**: Explicitly blocks `localhost`, `ip6-localhost`, `ip6-loopback`, `metadata.google.internal`, `instance-data`, and internal suffixes (`.local`, `.localhost`, `.internal`, `.corp`, `.onion`).
  - **Comprehensive IP Subnet Filtering**: Validates IPv4 and IPv6 addresses using Python `ipaddress`. Blocks:
    - Loopback: `127.0.0.0/8`, `::1`
    - RFC 1918 Private Subnets: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`
    - IPv6 Unique Local Addresses (ULA): `fc00::/7`
    - Link-Local / Cloud Metadata: `169.254.0.0/16`, `fe80::/10`
    - IPv4-Mapped IPv6: `::ffff:127.0.0.1`, `::ffff:192.168.0.1` (mapped IPv4 address is explicitly extracted and filtered)
    - Carrier-Grade NAT (RFC 6598): `100.64.0.0/10`
    - Multicast, unspecified (`0.0.0.0`, `::`), and reserved blocks
  - **Safe DNS Resolution & Rebinding Check**: For domain names, resolves addresses safely via `socket.getaddrinfo`. If any resolved IP belongs to a restricted subnet, the request is blocked (`SSRF_REJECTED`). If DNS resolution fails, it reports `DNS_RESOLUTION_FAILED`.
  - **Redirect Chain Validation (`SafeUrlResolver`)**: If URL resolution is performed, every redirect hop is independently validated against the SSRF filter before connecting, preventing redirect-based perimeter bypasses.
  - *Explicit Boundary Statement*: Outbound network requests to external third-party servers are disabled by default. The system operates in an offline, air-gapped posture during standard verification.

---

### Threat 3: Forged Officer Determinations, Authorization Bypass & Credential Exposure
* **Attack Scenario**: A malicious client submits HTTP POST requests to `/api/findings/{id}/review`, `/confirm`, or `/dismiss` with forged `X-Officer-Role: AICTE_ADMIN` or arbitrary review decisions without valid credentials.
* **Vulnerability in Naive Code**: Trusting client-supplied role headers or exposing shared secrets via frontend client bundles (`NEXT_PUBLIC_*`).
* **VERITAS Mitigation (`backend/main.py`)**:
  - **Fail-Closed Server Guard**: If `OFFICER_AUTH_TOKEN` is unset, empty, or a known revoked token on the server, all protected endpoints fail closed with `HTTP 500`.
  - **Server-Side Token Verification**: Client authorization tokens are compared against the configured server secret using constant-time comparison (`secrets.compare_digest`), preventing timing attacks.
  - **Rejection of Client-Asserted Roles**: Client-supplied `X-Officer-Role` headers are rejected with `HTTP 401` unless accompanied by a valid server-verified bearer token.
  - **Role Boundary Enforcement**: Even with a valid token, roles outside `VALID_OFFICER_ROLES` (`OFFICER`, `SCRUTINY_COMMITTEE`, `AICTE_ADMIN`, `REGIONAL_OFFICER`, `INSPECTOR`, `REVIEWER`) are rejected with `HTTP 403`.
  - **Critical Disclosure on `NEXT_PUBLIC_*` Variables**:
    > [!WARNING]
    > **Frontend Secret Handling Notice**: Next.js automatically inlines any variable prefixed with `NEXT_PUBLIC_` into client-side JavaScript bundles. Therefore, `NEXT_PUBLIC_OFFICER_TOKEN` must **never** be treated as a confidential secret in production. In VERITAS, `NEXT_PUBLIC_OFFICER_TOKEN` is used strictly as a localhost developer-mode convenience. For production deployments, officer credentials must be supplied via authenticated session storage, secure cookies, or an interactive officer login flow.

---

### Threat 4: Audit Trail Database Manipulation & Ledger Semantics
* **Attack Scenario**: A rogue database administrator or insider modifies rows in the SQLite audit database to confirm fraudulent institutional applications retroactively.
* **VERITAS Mitigation (`backend/audit/trail.py`)**:
  - Every audit entry forms a cryptographic hash chain:
    $$\text{hash}_i = \text{SHA-256}(\text{hash}_{i-1} \parallel \text{timestamp} \parallel \text{app\_id} \parallel \text{action} \parallel \text{payload})$$
  - The verification endpoint `/api/audit/verify` re-computes the entire chain from the genesis block (`0`*64). Any direct SQL mutation, row deletion, or timestamp tampering immediately invalidates downstream hashes and flags the exact modified event index.
  - **Demo Tamper Endpoint Isolation (`/api/audit/tamper`)**:
    - Strictly disabled by default: requires server environment `ENABLE_DEMO_TAMPER=true`.
    - Protected by server-side officer authorization (`verify_officer_authorization`).
    - Requires explicit client confirmation header `X-Demo-Mode: true`.
  - **Semantics Disclosure**:
    > [!NOTE]
    > **Tamper-Evident vs. Immutable Ledger**: VERITAS implements a **tamper-evident hash chain**, meaning any unauthorized modification is mathematically detectable upon verification. It is **not** an immutable distributed ledger or non-repudiation system, as an attacker with full root filesystem access could theoretically rewrite the entire SQLite database file and recompute hashes from genesis in the absence of an external trusted timestamping authority (TSA) or hardware security module (HSM).

---

### Threat 5: Digital Signature Spoofing & Semantic Grounding
* **Attack Scenario**: An altered document is presented with a fake digital signature seal rendered as a static bitmap image, or signed with an arbitrary self-signed certificate.
* **VERITAS Mitigation (`backend/signature/verifier.py`)**:
  - Integrates pyHanko (`pyhanko.pdf_utils` and `pyhanko.sign`) to inspect the PDF binary structure.
  - Verifies whether real cryptographic PKCS#7 / CMS byte ranges exist and checks whether the byte range covers the entire file or has appended post-signing modifications.
  - Evaluates the signer certificate against the configured AICTE Root CA anchor (`ca_cert.pem`).
  - **Six Canonical States Distinguished**:
    1. `UNSIGNED`: No signature dictionary exists in the document catalog.
    2. `INTACT`: Cryptographically valid signature under configured trust policy (byte ranges intact, digest matches PKCS#7, and signer chains to trusted root CA).
    3. `MODIFIED`: Invalid signature (byte-range digest mismatch or post-signing byte modifications detected).
    4. `UNTRUSTED_SIGNER`: Cryptographic digest matches byte range, but signer certificate is self-signed or not anchored in trusted root.
    5. `UNAVAILABLE_VALIDATION_INFO`: Certificate chain or revocation data is incomplete or unavailable.
    6. `UNSUPPORTED_OR_FAILED`: Parsing exception, corrupt signature dictionary, or unsupported algorithm.
  - **Semantic Grounding**:
    > [!IMPORTANT]
    > **Decoupling Mathematical Validity from AICTE Authorization**: A mathematically valid signature proves that bytes were not altered since signing by the private key holder. It does **not** prove that the signer is an authorized AICTE official. VERITAS independently verifies and reports `is_mathematically_valid`, `is_trusted_ca`, and `is_aicte_authorized_issuer`.

---

## 3. Computer Vision Forensics Limitations & False-Positive Boundaries

| Forensic Detector | Algorithm & Method | Intended Detection | Known False-Positive Risk | VERITAS Risk Control |
| :--- | :--- | :--- | :--- | :--- |
| **Error Level Analysis (ELA)** | Fixed-Quality JPEG Recompression (`quality=90`) + Differencing | Localized compression history differences (spliced graphics) | Normal text antialiasing, high-frequency line art, re-saved scanned PDFs | Baseline normalization (`reencode_jpeg`); results classified as advisory `FORENSIC_ADVISORY`, never proof of forgery. |
| **SRM Steganalysis** | 3-Kernel 5x5 High-Pass Noise Residuals | Micro-boundary edge splicing artifacts | Legitimate stamps, textured paper backgrounds, scanner sensor noise | Filtered for energy averages; reported as non-prejudicial visual heatmap. |
| **Copy-Move Duplication** | SIFT + FLANN + Lowe's Ratio (0.75) + RANSAC | Cloned seals, stamps, and duplicated signatures | Repeated legitimate table rules, gridlines, boilerplate headers | Spatial distance threshold (>40px); spatial standard deviation check ($\text{std}_x > 10$, $\text{std}_y > 10$) excludes 1D collinear table lines. |
| **Typography Consistency** | Otsu Binarization + Euclidean Distance Transform | Inconsistent font stroke width and character height (pasted numbers) | Legitimate bold headers, titles, table headers, footnotes, emphasis | Baseline median computed on body text; header zone excluded; short token filtering; classified as advisory review indicators. |
| **Scan Quality Gating** | Laplacian Variance + HSV V-Channel Glare | Blurry or overexposed camera captures | Digital blank pages, sparse end pages | Blank page detector checks pixel standard deviation ($\text{std} < 5$); skips blur/glare alarms on clean digital pages. |
