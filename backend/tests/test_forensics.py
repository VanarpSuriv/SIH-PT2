"""
Automated Unit and Integration Tests for Forensic Document Analysis Engine.
Tests:
1. Error Level Analysis (ELA) with fixed-quality JPEG normalization
2. Spatial Rich Model (SRM) 5x5 steganalysis high-pass residuals
3. SIFT + FLANN + Lowe's ratio + RANSAC Copy-Move detection
4. Typography stroke-width and font-height outlier detection
5. Image scan quality assessment (blur and glare)
6. QR Code decoding and strict SSRF defenses (loopback, RFC1918, link-local)
7. Address and institutional name normalization
8. FastAPI forensics endpoints and advisory findings
"""
import io
import os
import numpy as np
import cv2
import pytest
from fastapi.testclient import TestClient

from backend.main import app, process_application_documents
from backend.models import (
    DocumentType,
    ExtractedWord,
    FindingStatus,
    PageData,
    RuleCategory,
)
from backend.forensics.engine import (
    analyze_document_forensics,
    assess_image_quality,
    detect_copy_move,
    detect_typography_outliers,
    error_level_analysis,
    noise_residual,
    reencode_jpeg,
    render_ela_heatmap_base64,
)
from backend.rules.engine import normalize_address, normalize_institution_name, RulesEngine
from backend.verify.qr_verifier import QRCodeVerifier, SafeUrlResolver, is_ip_restricted

client = TestClient(app)


# ---------------------------------------------------------------------------
# 1. Error Level Analysis (ELA) Tests
# ---------------------------------------------------------------------------
def test_ela_computation_and_normalization():
    """Verify ELA computation returns valid single-channel map and bounded statistics."""
    # Synthetic 300x300 image with high-contrast text block
    img = np.full((300, 300, 3), 255, dtype=np.uint8)
    cv2.putText(img, "AICTE TEST", (40, 150), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 3)

    reencoded = reencode_jpeg(img, quality=90)
    assert reencoded.shape == img.shape

    ela_map, mean_res, max_res = error_level_analysis(reencoded, quality=90, scale=15.0)
    assert ela_map.shape == (300, 300)
    assert 0.0 <= mean_res <= 1.0
    assert 0.0 <= max_res <= 1.0

    b64 = render_ela_heatmap_base64(reencoded, ela_map)
    assert b64.startswith("data:image/jpeg;base64,")


# ---------------------------------------------------------------------------
# 2. Spatial Rich Model (SRM) Tests
# ---------------------------------------------------------------------------
def test_srm_noise_residual_energy():
    """Verify SRM steganalysis high-pass kernels produce 3-channel feature maps."""
    img = np.full((200, 200, 3), 240, dtype=np.uint8)
    # Add random noise patch to simulate graphic splice
    img[50:100, 50:100] = np.random.randint(0, 255, (50, 50, 3), dtype=np.uint8)

    srm_map, energy = noise_residual(img)
    assert srm_map.shape == (200, 200, 3)
    assert energy > 0.0


# ---------------------------------------------------------------------------
# 3. Copy-Move Detection Tests
# ---------------------------------------------------------------------------
def test_copy_move_clean_vs_duplicated_seal():
    """Verify SIFT/FLANN/RANSAC separates untampered images from cloned patches."""
    # Create an official-style stamp emblem with rich 2D keypoints
    stamp = np.full((120, 120, 3), 255, dtype=np.uint8)
    cv2.circle(stamp, (60, 60), 55, (0, 0, 150), 3)
    cv2.circle(stamp, (60, 60), 45, (0, 0, 150), 1)
    cv2.putText(stamp, "AICTE", (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 150), 2)
    cv2.putText(stamp, "SEAL", (35, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 150), 2)

    # Clean document image with text and one stamp
    clean_img = np.full((500, 500, 3), 255, dtype=np.uint8)
    cv2.putText(clean_img, "Approval Letter 2024-2025", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    clean_img[150:270, 50:170] = stamp

    clean_res = detect_copy_move(clean_img)
    # Clean image should not trigger suspicious copy-move alert
    assert clean_res["suspicious"] is False
    assert clean_res["geometric_matches"] == 0

    # Intentionally cloned seal: duplicate the stamp at a second location (320, 50)
    tampered_img = clean_img.copy()
    tampered_img[320:440, 50:170] = stamp

    tampered_res = detect_copy_move(tampered_img)
    assert tampered_res["geometric_matches"] >= 6
    assert tampered_res["suspicious"] is True
    assert tampered_res["copy_move_score"] > 0.5


# ---------------------------------------------------------------------------
# 4. Typography Style Outlier Tests
# ---------------------------------------------------------------------------
def test_detect_typography_outliers():
    """Verify Otsu distance-transform flags tokens with anomalous font weight or height."""
    img = np.full((500, 600, 3), 255, dtype=np.uint8)

    # Render regular body text lines
    words = []
    y_pos = 100
    for i in range(8):
        cv2.putText(img, f"Regular body text line {i+1} with standard weight", (50, y_pos),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (30, 30, 30), 1)
        words.append(ExtractedWord(
            text=f"line_{i}",
            bbox=[50.0, float(y_pos - 15), 350.0, float(y_pos + 5)],
            block_no=1, line_no=i, word_no=1
        ))
        y_pos += 40

    # Plant an outlier token: abnormally bold and oversized forged date/figure
    cv2.putText(img, "99.85 ACRES", (50, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 0, 0), 4)
    words.append(ExtractedWord(
        text="99.85 ACRES",
        bbox=[50.0, float(y_pos - 30), 250.0, float(y_pos + 10)],
        block_no=2, line_no=0, word_no=0
    ))

    outlier_count, outliers = detect_typography_outliers(img, words, page_width=600.0, page_height=500.0)
    assert outlier_count >= 1
    assert any("99.85" in o.text for o in outliers)


# ---------------------------------------------------------------------------
# 5. Image Scan Quality Tests
# ---------------------------------------------------------------------------
def test_assess_image_quality_sharp_vs_blurry():
    """Verify Laplacian variance correctly distinguishes sharp from blurry scans."""
    sharp_img = np.zeros((300, 300, 3), dtype=np.uint8)
    for i in range(0, 300, 15):
        cv2.line(sharp_img, (0, i), (300, i), (255, 255, 255), 2)
    sharp_eval = assess_image_quality(sharp_img)
    assert sharp_eval["blur_score"] > 80.0
    assert "IMAGE_TOO_BLURRY" not in sharp_eval["warnings"]

    # Extremely blurred image
    blurry_img = cv2.GaussianBlur(sharp_img, (31, 31), 10.0)
    blurry_eval = assess_image_quality(blurry_img)
    assert blurry_eval["blur_score"] < 80.0
    assert "IMAGE_TOO_BLURRY" in blurry_eval["warnings"]


# ---------------------------------------------------------------------------
# 6. QR Code Decoding and SSRF Defenses
# ---------------------------------------------------------------------------
def test_qr_code_verifier_ssrf_protection():
    """Verify strict SSRF defense: whitelist official domains and reject private IPs."""
    # 1. Official AICTE portal URL -> VERIFIED_OFFICIAL
    res1 = QRCodeVerifier.verify_payload("https://facilities.aicte-india.org/eoa/verify?id=1-12345678")
    assert res1["status"] == "VERIFIED_OFFICIAL"
    assert res1["safe"] is True

    # 2. Official Government NIC portal -> VERIFIED_OFFICIAL
    res2 = QRCodeVerifier.verify_payload("https://services.nic.in/portal/cert/998")
    assert res2["status"] == "VERIFIED_OFFICIAL"
    assert res2["safe"] is True

    # 3. Private IP Address (RFC 1918) -> SSRF_REJECTED
    res3 = QRCodeVerifier.verify_payload("http://192.168.1.1/admin/status")
    assert res3["status"] == "SSRF_REJECTED"
    assert res3["safe"] is False

    # 4. Loopback (127.0.0.1) -> SSRF_REJECTED
    res4 = QRCodeVerifier.verify_payload("http://127.0.0.1:8000/internal")
    assert res4["status"] == "SSRF_REJECTED"
    assert res4["safe"] is False

    # 5. Cloud Metadata Link-Local IP (169.254.169.254) -> SSRF_REJECTED
    res5 = QRCodeVerifier.verify_payload("http://169.254.169.254/latest/meta-data")
    assert res5["status"] == "SSRF_REJECTED"
    assert res5["safe"] is False

    # 6. Disallowed non-HTTP scheme -> SSRF_REJECTED
    res6 = QRCodeVerifier.verify_payload("file:///etc/passwd")
    assert res6["status"] == "SSRF_REJECTED"
    assert res6["safe"] is False

    # 7. External untrusted domain -> EXTERNAL_ADVISORY
    res7 = QRCodeVerifier.verify_payload("https://phishing-portal.xyz/verify")
    assert res7["status"] == "EXTERNAL_ADVISORY"
    assert res7["safe"] is True


# ---------------------------------------------------------------------------
# 7. Normalization Tests (Address & Institution Name)
# ---------------------------------------------------------------------------
def test_address_and_institution_normalization():
    """Verify address and institutional abbreviation expansions eliminate false alarms."""
    # Address normalization
    raw_addr = "H.No. 42/B, Rd. 5, Near Metro St., PIN: 560001"
    norm_addr = normalize_address(raw_addr)
    assert "h no 42 b" in norm_addr
    assert "road 5" in norm_addr
    assert "street" in norm_addr
    assert "pin 560001" in norm_addr

    # Institution name abbreviation expansion
    name1 = "Delhi Inst. of Tech. & Engg."
    norm1 = normalize_institution_name(name1)
    assert "institute" in norm1
    assert "technology" in norm1
    assert "engineering" in norm1


# ---------------------------------------------------------------------------
# 8. API Forensics Endpoints Integration Tests
# ---------------------------------------------------------------------------
def test_api_forensics_endpoints():
    """Verify /api/documents/{id}/forensics and /api/applications/{id}/forensics."""
    # Ingest synthetic clean case
    case_path = os.path.join("synthetic", "cases", "case_01")
    if not os.path.exists(case_path):
        pytest.skip("case_01 not present")

    app_id = "APP-TEST-FORENSIC-01"
    doc_tuples = []
    for fname in ["application_form.pdf", "approval_letter.pdf"]:
        fpath = os.path.join(case_path, fname)
        if os.path.exists(fpath):
            with open(fpath, "rb") as f:
                doc_tuples.append((fname, f.read()))

    case = process_application_documents(app_id, "Apex Institute", doc_tuples)
    assert len(case.documents) >= 1

    doc_id = case.documents[0].id

    # 1. Test document forensics endpoint
    resp = client.get(f"/api/documents/{doc_id}/forensics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["document_id"] == doc_id
    assert len(data["page_results"]) >= 1
    page1 = data["page_results"][0]
    assert "ela_mean_residual" in page1
    assert "heatmap_preview_base64" in page1
    assert page1["heatmap_preview_base64"].startswith("data:image/jpeg;base64,")

    # 2. Test application forensics endpoint
    app_resp = client.get(f"/api/applications/{app_id}/forensics")
    assert app_resp.status_code == 200
    app_data = app_resp.json()
    assert app_data["application_id"] == app_id
    assert app_data["document_count"] >= 1


# ---------------------------------------------------------------------------
# 9. Forensic Edge Cases: Blank Pages, Unsupported Inputs & Missing OCR
# ---------------------------------------------------------------------------
def test_forensics_blank_pages_and_unsupported_inputs():
    """
    Verify forensic algorithms gracefully handle edge cases:
    - Pure white blank pages do not trigger false blur/glare alarms.
    - Zero-size or empty image inputs do not crash.
    - Grayscale (1-channel) and BGRA (4-channel) images are handled seamlessly.
    """
    # 1. Blank digital white page (255)
    blank_white = np.full((400, 400, 3), 255, dtype=np.uint8)
    q_blank = assess_image_quality(blank_white)
    assert q_blank["is_blank_page"] is True
    assert "IMAGE_TOO_BLURRY" not in q_blank["warnings"]
    assert "GLARE_DETECTED" not in q_blank["warnings"]

    # 2. Empty image inputs (0x0)
    empty_img = np.zeros((0, 0, 3), dtype=np.uint8)
    q_empty = assess_image_quality(empty_img)
    assert "INVALID_IMAGE_INPUT" in q_empty["warnings"]

    ela_map, mean_res, max_res = error_level_analysis(empty_img)
    assert mean_res == 0.0
    assert max_res == 0.0

    srm_map, srm_energy = noise_residual(empty_img)
    assert srm_energy == 0.0

    cm_res = detect_copy_move(empty_img)
    assert cm_res["suspicious"] is False
    assert cm_res["status"] == "INSUFFICIENT_FEATURES"

    # 3. 1-channel Grayscale input
    gray_img = np.full((100, 100), 128, dtype=np.uint8)
    cv2.line(gray_img, (10, 10), (90, 90), 0, 2)
    srm_g, srm_g_energy = noise_residual(gray_img)
    assert srm_g_energy >= 0.0

    re_gray = reencode_jpeg(gray_img)
    assert re_gray.ndim == 3  # Normalized to 3 channels

    # 4. 4-channel BGRA input
    bgra_img = np.full((100, 100, 4), 200, dtype=np.uint8)
    cv2.circle(bgra_img, (50, 50), 30, (0, 0, 0, 255), 2)
    ela_bgra, b_mean, b_max = error_level_analysis(bgra_img)
    assert b_mean >= 0.0


def test_forensics_missing_and_incomplete_ocr():
    """
    Verify analyze_document_forensics executes across all PDF pages even when
    the input `pages` OCR structure is completely empty (e.g. scanned image PDF).
    """
    import pymupdf
    # Create an in-memory 2-page PDF
    doc = pymupdf.open()
    p1 = doc.new_page(width=300, height=300)
    p1.draw_rect([20, 20, 100, 100], color=(0, 0, 1), fill=(0.8, 0.8, 1))
    p2 = doc.new_page(width=300, height=300)
    p2.draw_rect([50, 50, 150, 150], color=(1, 0, 0), fill=(1, 0.8, 0.8))
    pdf_bytes = doc.tobytes()
    doc.close()

    # Pass completely empty pages list (simulating unperformed or failed OCR)
    res = analyze_document_forensics(pdf_bytes, pages=[], filename="scanned_no_ocr.pdf", document_id="doc_no_ocr")
    assert res.summary_advisory in ("PASS", "ADVISORY", "REVIEW_RECOMMENDED")
    assert len(res.page_results) == 2  # Both physical pages were analyzed
    assert res.page_results[0].page_number == 1
    assert res.page_results[1].page_number == 2


def test_forensics_malformed_and_corrupt_pdf():
    """
    Verify analyze_document_forensics fails gracefully on malformed / random byte data.
    """
    garbage_bytes = b"NOT_A_VALID_PDF_BINARY_HEADER_1234567890"
    res = analyze_document_forensics(garbage_bytes, pages=[], filename="corrupt.pdf", document_id="doc_bad")
    assert res.summary_advisory == "INDETERMINATE"
    assert "FAILED_TO_RENDER_PDF_PAGES" in res.findings_generated


# ---------------------------------------------------------------------------
# 10. Comprehensive QR and Network Security / SSRF Defense Matrix
# ---------------------------------------------------------------------------
def test_qr_and_network_security_comprehensive_matrix():
    """
    Focused regression tests verifying complete SSRF and network security coverage:
    - IPv4 Loopback (127.0.0.1, 127.0.0.0/8)
    - RFC 1918 Private Ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
    - IPv6 Loopback ([::1])
    - IPv6 Private Unique Local Addresses ([fc00::1])
    - IPv6 Link-Local ([fe80::1])
    - IPv4-Mapped IPv6 ([::ffff:127.0.0.1])
    - Cloud Metadata Link-Local (169.254.169.254, metadata.google.internal)
    - Disallowed non-HTTP/HTTPS schemes (ftp, gopher, file, data, javascript)
    - Credentials in URLs (user:pass@)
    - Unusual / non-standard ports (:22, :6379, :8080)
    - Deceptive hostnames (e.g. aicte-india.org.attacker.com)
    - SafeUrlResolver redirect chain validation
    - DNS resolution failure handling
    """
    # 1. IPv4 Loopback variations
    assert QRCodeVerifier.verify_payload("http://127.0.0.1/admin")["status"] == "SSRF_REJECTED"
    assert QRCodeVerifier.verify_payload("http://127.127.127.127:80/status")["status"] == "SSRF_REJECTED"

    # 2. RFC 1918 Private Subnets
    assert QRCodeVerifier.verify_payload("http://10.0.0.1/internal")["status"] == "SSRF_REJECTED"
    assert QRCodeVerifier.verify_payload("http://172.16.0.5/api")["status"] == "SSRF_REJECTED"
    assert QRCodeVerifier.verify_payload("http://192.168.1.100/router")["status"] == "SSRF_REJECTED"

    # 3. IPv6 Loopback, ULA, and Link-Local
    assert QRCodeVerifier.verify_payload("http://[::1]/internal")["status"] == "SSRF_REJECTED"
    assert QRCodeVerifier.verify_payload("http://[fc00::1]/db")["status"] == "SSRF_REJECTED"
    assert QRCodeVerifier.verify_payload("http://[fe80::1]/link")["status"] == "SSRF_REJECTED"

    # 4. IPv4-Mapped IPv6 loopback and private
    assert QRCodeVerifier.verify_payload("http://[::ffff:127.0.0.1]/")["status"] == "SSRF_REJECTED"
    assert QRCodeVerifier.verify_payload("http://[::ffff:192.168.0.1]/")["status"] == "SSRF_REJECTED"

    # 5. Cloud Metadata (AWS, GCP, Azure 169.254.169.254 & metadata.google.internal)
    assert QRCodeVerifier.verify_payload("http://169.254.169.254/latest/meta-data")["status"] == "SSRF_REJECTED"
    assert QRCodeVerifier.verify_payload("http://metadata.google.internal/computeMetadata/v1/")["status"] == "SSRF_REJECTED"

    # 6. Disallowed Schemes
    assert QRCodeVerifier.verify_payload("file:///etc/shadow")["status"] == "SSRF_REJECTED"
    assert QRCodeVerifier.verify_payload("gopher://127.0.0.1:70/_")["status"] == "SSRF_REJECTED"
    assert QRCodeVerifier.verify_payload("ftp://aicte-india.org/data")["status"] == "SSRF_REJECTED"
    assert QRCodeVerifier.verify_payload("javascript:alert(1)")["status"] == "SSRF_REJECTED"

    # 7. Credentials in URLs
    cred_res = QRCodeVerifier.verify_payload("http://admin:secret123@aicte-india.org/")
    assert cred_res["status"] == "SSRF_REJECTED"
    assert "Credentials" in cred_res["message"]

    # 8. Unusual non-standard ports
    p22_res = QRCodeVerifier.verify_payload("http://aicte-india.org:22/ssh")
    assert p22_res["status"] == "SSRF_REJECTED"
    assert "Unusual port" in p22_res["message"]

    p6379_res = QRCodeVerifier.verify_payload("http://aicte-india.org:6379/redis")
    assert p6379_res["status"] == "SSRF_REJECTED"

    p8080_res = QRCodeVerifier.verify_payload("http://aicte-india.org:8080/alt")
    assert p8080_res["status"] == "SSRF_REJECTED"

    # 9. Deceptive hostnames mimicking official domains
    # A domain like `aicte-india.org.attacker.com` is outside the official whitelist
    deceptive_res = QRCodeVerifier.verify_payload("https://aicte-india.org.attacker.com/eoa", resolve_dns=False)
    assert deceptive_res["status"] == "EXTERNAL_ADVISORY"
    assert deceptive_res["safe"] is True

    # Internal hostnames
    assert QRCodeVerifier.verify_payload("http://localhost/")["status"] == "SSRF_REJECTED"
    assert QRCodeVerifier.verify_payload("http://server.local/")["status"] == "SSRF_REJECTED"
    assert QRCodeVerifier.verify_payload("http://corp.internal/")["status"] == "SSRF_REJECTED"

    # 10. DNS Resolution failure handling
    dns_fail_res = QRCodeVerifier.verify_payload("https://non-existent-subdomain-404-unresolved.aicte-india.org/", resolve_dns=True)
    assert dns_fail_res["status"] == "DNS_RESOLUTION_FAILED"
    assert dns_fail_res["safe"] is False

    # 11. SafeUrlResolver redirect chain validation
    # Valid redirect chain between official endpoints
    valid_chain = SafeUrlResolver.validate_redirect_chain(
        "https://aicte-india.org/eoa",
        ["https://facilities.aicte-india.org/eoa/verify"]
    )
    assert valid_chain["valid"] is True

    # Malicious redirect chain attempting SSRF to private IP
    malicious_chain = SafeUrlResolver.validate_redirect_chain(
        "https://aicte-india.org/eoa",
        ["http://169.254.169.254/computeMetadata/v1/"]
    )
    assert malicious_chain["valid"] is False
    assert "rejected" in malicious_chain["reason"].lower()

    # Malicious redirect chain attempting unusual port
    malicious_port_chain = SafeUrlResolver.validate_redirect_chain(
        "https://aicte-india.org/eoa",
        ["https://aicte-india.org:8443/internal"]
    )
    assert malicious_port_chain["valid"] is False


# ---------------------------------------------------------------------------
# 11. Forensic Robustness: Compression Histories, Graphics & Mixed Typography
# ---------------------------------------------------------------------------
def test_forensics_genuine_compression_histories():
    """
    Verify ELA and SRM behavior across different compression histories.
    Prior JPEG re-encodings at lower quality (Q70, Q85) are normalized by reencode_jpeg
    and produce bounded residuals without algorithmic failure.
    """
    base_img = np.full((350, 450, 3), 250, dtype=np.uint8)
    cv2.putText(base_img, "Government Approval Order 2024", (40, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (20, 20, 20), 2)
    cv2.putText(base_img, "AICTE Mandatory Disclosure Record", (40, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (50, 50, 50), 1)

    for q in [70, 85, 95]:
        ok, buf = cv2.imencode(".jpg", base_img, [int(cv2.IMWRITE_JPEG_QUALITY), q])
        assert ok is True
        compressed = cv2.imdecode(buf, cv2.IMREAD_COLOR)

        # Baseline normalization strips prior generation artifacts
        normalized = reencode_jpeg(compressed, quality=92)
        ela_map, mean_res, max_res = error_level_analysis(normalized)
        srm_map, srm_energy = noise_residual(normalized)

        assert 0.0 <= mean_res <= 1.0
        assert 0.0 <= max_res <= 1.0
        assert srm_energy >= 0.0
        assert ela_map.shape == (350, 450)


def test_forensics_repeated_legitimate_table_graphics_and_bullets():
    """
    Verify that repetitive table structures (grid lines, bullet points, identical cells)
    do NOT trigger false-positive copy-move clone alerts thanks to collinear line
    suppression and 2D spatial dispersion gating.
    """
    table_img = np.full((500, 500, 3), 255, dtype=np.uint8)
    # Draw horizontal and vertical table grid lines
    for y in range(80, 420, 40):
        cv2.line(table_img, (50, y), (450, y), (0, 0, 0), 1)
    for x in range(50, 460, 100):
        cv2.line(table_img, (x, 80), (x, 400), (0, 0, 0), 1)

    # Draw repetitive bullet points
    for y in range(100, 380, 40):
        cv2.circle(table_img, (70, y), 3, (0, 0, 0), -1)
        cv2.putText(table_img, "Item Row", (90, y + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)

    cm_res = detect_copy_move(table_img)
    # Repetitive 1D table grid and bullets must be cleared by collinear/dispersion filtering
    assert cm_res["suspicious"] is False


def test_forensics_legitimate_mixed_typography_headings():
    """
    Verify that legitimate mixed typography (bold multi-token headings, table column titles)
    is recognized as document structure and not falsely flagged as forged token outliers.
    """
    img = np.full((550, 600, 3), 255, dtype=np.uint8)
    words = []

    # 1. Bold multi-token section heading (legitimate structural typography)
    cv2.putText(img, "SECTION A: INSTITUTION DETAILS AND NORMS", (50, 80),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 3)
    heading_tokens = ["SECTION", "A:", "INSTITUTION", "DETAILS", "AND", "NORMS"]
    for i, tok in enumerate(heading_tokens):
        words.append(ExtractedWord(
            text=tok,
            bbox=[float(50 + i * 70), 60.0, float(110 + i * 70), 85.0],
            block_no=1, line_no=0, word_no=i
        ))

    # 2. Standard body text lines
    y_pos = 130
    for l_idx in range(6):
        cv2.putText(img, f"Standard body text description line {l_idx + 1} with regular weight",
                    (50, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (40, 40, 40), 1)
        words.append(ExtractedWord(
            text=f"line_token_{l_idx}",
            bbox=[50.0, float(y_pos - 15), 350.0, float(y_pos + 5)],
            block_no=2, line_no=l_idx, word_no=0
        ))
        y_pos += 45

    outlier_count, outliers = detect_typography_outliers(img, words, page_width=600.0, page_height=550.0)
    # The heading line has >= 60% bold tokens, so it must not trigger false outlier alarms
    assert outlier_count == 0
    assert len(outliers) == 0


def test_forensics_poor_quality_genuine_scans():
    """
    Verify that poor-quality but genuine scans trigger quality gating advisories (blur)
    without causing algorithmic crashes or false copy-move alerts.
    """
    doc_img = np.full((400, 400, 3), 245, dtype=np.uint8)
    cv2.putText(doc_img, "Genuine AICTE Scan", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (30, 30, 30), 1)
    cv2.putText(doc_img, "Land Registration Deed", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (30, 30, 30), 1)

    # Simulate heavy blur from camera motion
    degraded = cv2.GaussianBlur(doc_img, (35, 35), 12.0)
    eval_res = assess_image_quality(degraded)

    assert "IMAGE_TOO_BLURRY" in eval_res["warnings"]
    assert eval_res["blur_score"] < 80.0

    # Ensure copy-move detector runs safely on blurry scan without false alert
    cm = detect_copy_move(degraded)
    assert cm["suspicious"] is False


