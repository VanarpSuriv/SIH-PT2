"""
Forensic Document Analysis Engine for VERITAS.
Implements:
1. Error Level Analysis (ELA) with fixed-quality JPEG normalization
2. Spatial Rich Model (SRM) 5x5 steganalysis high-pass noise residuals
3. SIFT + FLANN + Lowe's ratio + RANSAC Copy-Move seal/stamp duplication detection
4. Otsu binarization + distanceTransform font stroke and height outlier detection
5. Laplacian blur variance and HSV glare ratio scan quality gating

Advisory notice:
Forensic signals produced by this engine are technical indicators for human review.
They do NOT prove forgery, fraudulent intent, or regulatory non-compliance.
"""
import base64
import io
import math
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
import pymupdf
from PIL import Image

from backend.models import (
    DocumentForensicsResult,
    ExtractedWord,
    ForensicPageResult,
    ForensicTokenDetail,
    PageData,
)

# ---------------------------------------------------------------------------
# Constants & Defaults
# ---------------------------------------------------------------------------
REENCODE_QUALITY = 92
ELA_QUALITY = 90
ELA_SCALE = 15.0
BLUR_THRESHOLD = 80.0
GLARE_V_THRESHOLD = 250
GLARE_PIXEL_RATIO = 0.15
MAX_ANALYSIS_WIDTH = 1400

# Classic Fridrich & Kodovsky SRM 5x5 High-Pass Kernels for Steganalysis
_SRM_KERNELS = [
    np.array(
        [
            [0, 0, 0, 0, 0],
            [0, -1, 2, -1, 0],
            [0, 2, -4, 2, 0],
            [0, -1, 2, -1, 0],
            [0, 0, 0, 0, 0],
        ],
        dtype=np.float32,
    )
    / 4.0,
    np.array(
        [
            [-1, 2, -2, 2, -1],
            [2, -6, 8, -6, 2],
            [-2, 8, -12, 8, -2],
            [2, -6, 8, -6, 2],
            [-1, 2, -2, 2, -1],
        ],
        dtype=np.float32,
    )
    / 12.0,
    np.array(
        [
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
            [0, 1, -2, 1, 0],
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
        ],
        dtype=np.float32,
    )
    / 2.0,
]


def reencode_jpeg(image_bgr: np.ndarray, quality: int = REENCODE_QUALITY) -> np.ndarray:
    """
    Re-encode an image at a fixed JPEG quality to strip prior compression history.
    Normalizes compression artifacts so ELA evaluates localized differential error
    rather than page-wide quantization discrepancies.
    """
    if image_bgr is None or image_bgr.size == 0:
        return image_bgr
    if image_bgr.ndim == 2:
        image_bgr = cv2.cvtColor(image_bgr, cv2.COLOR_GRAY2BGR)
    elif image_bgr.ndim == 3 and image_bgr.shape[2] == 4:
        image_bgr = cv2.cvtColor(image_bgr, cv2.COLOR_BGRA2BGR)
    elif image_bgr.ndim != 3 or image_bgr.shape[2] != 3:
        return image_bgr

    ok, buf = cv2.imencode(".jpg", image_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        return image_bgr
    return cv2.imdecode(buf, cv2.IMREAD_COLOR)


def error_level_analysis(
    image_bgr: np.ndarray,
    quality: int = ELA_QUALITY,
    scale: float = ELA_SCALE,
) -> Tuple[np.ndarray, float, float]:
    """
    Compute single-channel Error Level Analysis (ELA) map in [0, 1].
    Returns (ela_map, mean_residual, max_residual).
    """
    if image_bgr is None or image_bgr.size == 0:
        return np.zeros((0, 0), dtype=np.float32), 0.0, 0.0

    if image_bgr.ndim == 2:
        image_bgr = cv2.cvtColor(image_bgr, cv2.COLOR_GRAY2BGR)
    elif image_bgr.ndim == 3 and image_bgr.shape[2] == 4:
        image_bgr = cv2.cvtColor(image_bgr, cv2.COLOR_BGRA2BGR)

    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(rgb)

    buf = io.BytesIO()
    pil_img.save(buf, format="JPEG", quality=quality)
    buf.seek(0)
    recompressed = np.asarray(Image.open(buf).convert("RGB"))

    diff = np.abs(rgb.astype(np.float32) - recompressed.astype(np.float32))
    ela = diff.max(axis=2) * (scale / 255.0)
    ela = np.clip(ela, 0.0, 1.0).astype(np.float32)

    mean_res = float(np.mean(ela)) if ela.size > 0 else 0.0
    max_res = float(np.max(ela)) if ela.size > 0 else 0.0
    return ela, round(mean_res, 4), round(max_res, 4)


def noise_residual(image_bgr: np.ndarray) -> Tuple[np.ndarray, float]:
    """
    Compute Spatial Rich Model (SRM) 3-kernel high-pass noise residuals.
    Returns (srm_map, total_energy).
    Highlights high-frequency edge splice boundaries without requiring ML weights.
    """
    if image_bgr is None or image_bgr.size == 0:
        return np.zeros((0, 0, 3), dtype=np.float32), 0.0

    if image_bgr.ndim == 2:
        gray = image_bgr.astype(np.float32)
    elif image_bgr.ndim == 3 and image_bgr.shape[2] == 4:
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGRA2GRAY).astype(np.float32)
    else:
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)

    chans = []
    energies = []
    for k in _SRM_KERNELS:
        res = np.abs(cv2.filter2D(gray, ddepth=cv2.CV_32F, kernel=k))
        m = res.max() if res.max() > 1e-6 else 1.0
        norm_res = res / m
        chans.append(norm_res)
        energies.append(float(np.mean(norm_res)))

    srm_map = np.stack(chans, axis=2).astype(np.float32)
    composite_energy = float(np.mean(energies)) if energies else 0.0
    return srm_map, round(composite_energy, 4)


def detect_copy_move(
    image_bgr: np.ndarray,
    min_matches: int = 6,
    distance_ratio: float = 0.75,
    min_spatial_dist: float = 40.0,
) -> Dict[str, Any]:
    """
    Detect duplicated seals, stamps, or text blocks via SIFT, FLANN matching,
    and RANSAC homography estimation.
    Safeguards against collinear false positives (e.g., table rules, lines).
    """
    if image_bgr is None or image_bgr.size == 0 or image_bgr.shape[0] < 40 or image_bgr.shape[1] < 40:
        return {
            "keypoints": 0,
            "candidate_matches": 0,
            "geometric_matches": 0,
            "copy_move_score": 0.0,
            "suspicious": False,
            "status": "INSUFFICIENT_FEATURES",
        }

    if image_bgr.ndim == 2:
        gray = image_bgr
    elif image_bgr.ndim == 3 and image_bgr.shape[2] == 4:
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGRA2GRAY)
    else:
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)

    h, w = gray.shape[:2]

    sift = cv2.SIFT_create(nfeatures=1200)
    keypoints, descriptors = sift.detectAndCompute(gray, None)

    if descriptors is None or len(keypoints) < 2 * min_matches:
        return {
            "keypoints": len(keypoints) if keypoints else 0,
            "candidate_matches": 0,
            "geometric_matches": 0,
            "copy_move_score": 0.0,
            "suspicious": False,
            "status": "INSUFFICIENT_FEATURES",
        }

    flann = cv2.FlannBasedMatcher(
        dict(algorithm=1, trees=5),
        dict(checks=50),
    )

    try:
        raw_matches = flann.knnMatch(descriptors, descriptors, k=3)
    except Exception:
        return {
            "keypoints": len(keypoints),
            "candidate_matches": 0,
            "geometric_matches": 0,
            "copy_move_score": 0.0,
            "suspicious": False,
            "status": "MATCHER_ERROR",
        }

    candidate_matches = []
    for pair in raw_matches:
        if len(pair) < 3:
            continue
        # In self-matching, pair[0] is the identity match (queryIdx == trainIdx, dist=0).
        # pair[1] is the nearest distinct feature; pair[2] is the second nearest.
        m1, m2 = pair[1], pair[2]
        if m1.queryIdx == m1.trainIdx:
            continue
        if m1.distance < (distance_ratio * m2.distance):
            candidate_matches.append(m1)

    # Filter out matches that are spatially too close (natural texture repetition)
    spatial_matches = []
    for m in candidate_matches:
        pt1 = np.array(keypoints[m.queryIdx].pt, dtype=np.float32)
        pt2 = np.array(keypoints[m.trainIdx].pt, dtype=np.float32)
        if np.linalg.norm(pt1 - pt2) >= min_spatial_dist:
            spatial_matches.append(m)

    geometric_matches = []
    if len(spatial_matches) >= 4:
        src_pts = np.float32([keypoints[m.queryIdx].pt for m in spatial_matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([keypoints[m.trainIdx].pt for m in spatial_matches]).reshape(-1, 1, 2)

        try:
            matrix, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
            if matrix is not None and mask is not None:
                inliers = mask.ravel().astype(bool)
                inlier_matches = [m for m, ok in zip(spatial_matches, inliers) if ok]

                # Safeguard: verify inliers are not strictly 1D collinear lines (e.g. table borders)
                if len(inlier_matches) >= min_matches:
                    pts_x = [keypoints[m.queryIdx].pt[0] for m in inlier_matches]
                    pts_y = [keypoints[m.queryIdx].pt[1] for m in inlier_matches]
                    std_x, std_y = np.std(pts_x), np.std(pts_y)
                    if std_x > 10.0 and std_y > 10.0:
                        geometric_matches = inlier_matches
        except Exception:
            pass

    geo_count = len(geometric_matches)
    match_ratio = geo_count / max(1, len(keypoints))
    norm_matches = min(geo_count / 25.0, 1.0)
    norm_ratio = min(match_ratio / 0.04, 1.0)
    copy_move_score = round(float(0.7 * norm_matches + 0.3 * norm_ratio), 4)

    return {
        "keypoints": len(keypoints),
        "candidate_matches": len(candidate_matches),
        "geometric_matches": geo_count,
        "copy_move_score": copy_move_score,
        "suspicious": geo_count >= min_matches and copy_move_score >= 0.45,
        "status": "COMPLETED",
    }


def detect_typography_outliers(
    image_bgr: np.ndarray,
    words: List[ExtractedWord],
    page_width: float,
    page_height: float,
    header_zone_frac: float = 0.10,
    size_ratio_thresh: float = 1.30,
    stroke_ratio_thresh: float = 1.35,
) -> Tuple[int, List[ForensicTokenDetail]]:
    """
    Flag short tokens (numbers, dates, names) whose stroke width or font height
    deviate significantly from the page's dominant body-text style using Otsu
    binarization and Euclidean distance transform.
    """
    img_h, img_w = image_bgr.shape[:2]
    if not words or img_h == 0 or img_w == 0 or page_width <= 0 or page_height <= 0:
        return 0, []

    scale_x = img_w / page_width
    scale_y = img_h / page_height

    token_features = []
    for w in words:
        if not w.text or len(w.text.strip()) == 0:
            continue
        # Convert PDF points bbox [x0, y0, x1, y1] to image pixels
        bx0 = max(0, int(w.bbox[0] * scale_x))
        by0 = max(0, int(w.bbox[1] * scale_y))
        bx1 = min(img_w, int(w.bbox[2] * scale_x))
        by1 = min(img_h, int(w.bbox[3] * scale_y))

        if bx1 <= bx0 + 2 or by1 <= by0 + 2:
            continue

        crop = image_bgr[by0:by1, bx0:bx1]
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        _, ink = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        token_h = float(by1 - by0)
        if ink.mean() < 1.0:
            stroke_width = 1.0
        else:
            dist = cv2.distanceTransform(ink, cv2.DIST_L2, 3)
            active_dist = dist[ink > 0]
            stroke_width = float(active_dist.mean() * 2) if len(active_dist) > 0 else 1.0

        token_features.append(
            {
                "word": w,
                "text": w.text.strip(),
                "height": token_h,
                "stroke": stroke_width,
                "y0": by0,
                "block_no": getattr(w, "block_no", 0),
                "line_no": getattr(w, "line_no", 0),
            }
        )

    if len(token_features) < 5:
        return 0, []

    # Calculate baseline medians across all body text (excluding header band)
    body_tokens = [t for t in token_features if t["y0"] >= header_zone_frac * img_h]
    if not body_tokens:
        body_tokens = token_features

    median_height = float(np.median([t["height"] for t in body_tokens]))
    median_stroke = float(np.median([t["stroke"] for t in body_tokens]))

    if median_height <= 0 or median_stroke <= 0:
        return 0, []

    # Detect line-level heading/table column header styles (legitimate mixed typography)
    # If >= 60% of tokens in a multi-token line are bold or oversized, treat the line as a legitimate heading
    line_groups: Dict[Tuple[int, int], List[int]] = {}
    for idx, t in enumerate(token_features):
        key = (t["block_no"], t["line_no"])
        line_groups.setdefault(key, []).append(idx)

    heading_token_indices = set()
    for key, indices in line_groups.items():
        if len(indices) >= 2:
            heavy_count = sum(
                1 for i in indices
                if (token_features[i]["stroke"] / median_stroke >= 1.25 or token_features[i]["height"] / median_height >= 1.25)
            )
            if (heavy_count / len(indices)) >= 0.60:
                heading_token_indices.update(indices)

    outliers: List[ForensicTokenDetail] = []
    for idx, t in enumerate(token_features):
        # Exclude header band (logos/titles are legitimately bigger)
        if t["y0"] < header_zone_frac * img_h:
            continue

        # Exclude legitimate multi-token headings or table column labels
        if idx in heading_token_indices:
            continue

        size_ratio = t["height"] / median_height
        stroke_ratio = t["stroke"] / median_stroke

        size_score = max(0.0, (size_ratio - 1.0) / (size_ratio_thresh - 1.0))
        stroke_score = max(0.0, (stroke_ratio - 1.0) / (stroke_ratio_thresh - 1.0))
        style_score = max(size_score, stroke_score)

        # Flag numbers, short values, or words that are unusually bold or tall in otherwise regular text
        is_short = len(t["text"]) <= 20
        is_outlier = is_short and style_score >= 1.0

        if is_outlier:
            outliers.append(
                ForensicTokenDetail(
                    text=t["text"],
                    bbox=t["word"].bbox,
                    size_ratio=round(size_ratio, 2),
                    stroke_ratio=round(stroke_ratio, 2),
                    style_score=round(style_score, 2),
                    style_outlier=True,
                )
            )

    return len(outliers), outliers[:15]


def assess_image_quality(
    image_bgr: np.ndarray,
    blur_threshold: float = BLUR_THRESHOLD,
    glare_v_threshold: int = GLARE_V_THRESHOLD,
    glare_ratio_thresh: float = GLARE_PIXEL_RATIO,
) -> Dict[str, Any]:
    """
    Assess document scan quality:
    - Laplacian variance for blur detection.
    - HSV V-channel thresholding for glare/overexposure detection.
    Safeguards against false positives on clean or blank digital pages.
    """
    if image_bgr is None or image_bgr.size == 0:
        return {
            "blur_score": 0.0,
            "glare_ratio": 0.0,
            "warnings": ["INVALID_IMAGE_INPUT"],
            "is_blank_page": False,
        }

    if image_bgr.ndim == 2:
        gray = image_bgr
        hsv_input = cv2.cvtColor(image_bgr, cv2.COLOR_GRAY2BGR)
    elif image_bgr.ndim == 3 and image_bgr.shape[2] == 4:
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGRA2GRAY)
        hsv_input = cv2.cvtColor(image_bgr, cv2.COLOR_BGRA2BGR)
    else:
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        hsv_input = image_bgr

    # Detect blank or uniform pages: low standard deviation across the page
    # A digital blank white page has std ~ 0 and mean > 240, but is NOT a blurry camera photo or glare!
    pixel_std = float(np.std(gray))
    pixel_mean = float(np.mean(gray))
    is_blank = (pixel_std < 5.0 and pixel_mean > 240.0) or (pixel_std < 2.0)

    blur_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    hsv = cv2.cvtColor(hsv_input, cv2.COLOR_BGR2HSV)
    v_chan = hsv[:, :, 2]
    glare_ratio = float(np.count_nonzero(v_chan > glare_v_threshold) / max(1, v_chan.size))

    warnings = []
    if is_blank:
        # Blank digital page: do not trigger false blur/glare alarms
        return {
            "blur_score": round(blur_var, 2),
            "glare_ratio": round(glare_ratio, 4),
            "warnings": [],
            "is_blank_page": True,
        }

    if blur_var < blur_threshold:
        warnings.append("IMAGE_TOO_BLURRY")
    if glare_ratio > glare_ratio_thresh:
        warnings.append("GLARE_DETECTED")

    return {
        "blur_score": round(blur_var, 2),
        "glare_ratio": round(glare_ratio, 4),
        "warnings": warnings,
        "is_blank_page": False,
    }


def render_ela_heatmap_base64(
    image_bgr: np.ndarray,
    ela_map: np.ndarray,
    max_preview_width: int = 800,
) -> str:
    """
    Render a colorized ELA heat map blended with the original image
    and return as a base64 Data URI for direct frontend inspection.
    """
    if image_bgr is None or image_bgr.size == 0 or ela_map is None or ela_map.size == 0:
        return ""

    if image_bgr.ndim == 2:
        image_bgr = cv2.cvtColor(image_bgr, cv2.COLOR_GRAY2BGR)
    elif image_bgr.ndim == 3 and image_bgr.shape[2] == 4:
        image_bgr = cv2.cvtColor(image_bgr, cv2.COLOR_BGRA2BGR)

    h, w = image_bgr.shape[:2]
    # Downscale for compact web rendering
    if w > max_preview_width:
        ratio = max_preview_width / float(w)
        target_h = int(h * ratio)
        disp_bgr = cv2.resize(image_bgr, (max_preview_width, target_h), interpolation=cv2.INTER_AREA)
        disp_ela = cv2.resize(ela_map, (max_preview_width, target_h), interpolation=cv2.INTER_AREA)
    else:
        disp_bgr = image_bgr
        if ela_map.shape[:2] != (h, w):
            disp_ela = cv2.resize(ela_map, (w, h), interpolation=cv2.INTER_AREA)
        else:
            disp_ela = ela_map

    ela_u8 = np.clip(disp_ela * 255.0, 0, 255).astype(np.uint8)
    heatmap = cv2.applyColorMap(ela_u8, cv2.COLORMAP_INFERNO)

    # 60% heatmap + 40% original image
    blended = cv2.addWeighted(heatmap, 0.65, disp_bgr, 0.35, 0)

    ok, buf = cv2.imencode(".jpg", blended, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
    if not ok:
        return ""
    b64_str = base64.b64encode(buf.tobytes()).decode("ascii")
    return f"data:image/jpeg;base64,{b64_str}"


def analyze_document_forensics(
    file_bytes: bytes,
    pages: List[PageData],
    filename: str = "",
    document_id: str = "",
    application_id: str = "",
) -> DocumentForensicsResult:
    """
    Execute complete forensic pipeline across all pages of a document:
    1. Render PyMuPDF pixmap per page.
    2. Quality assessment (blur, glare).
    3. Error Level Analysis (reencode + diff + heatmap preview).
    4. SRM high-pass noise residuals.
    5. Copy-move detection (SIFT + FLANN + RANSAC).
    6. Typography outlier detection (Otsu + distance transform).
    7. QR code detection and decode.
    Safely processes documents even when OCR text is missing, incomplete, or unextracted.
    """
    page_results: List[ForensicPageResult] = []
    composite_scores: List[float] = []
    generated_findings: List[str] = []

    try:
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
    except Exception:
        return DocumentForensicsResult(
            document_id=document_id,
            filename=filename,
            page_count=len(pages),
            page_results=[],
            summary_advisory="INDETERMINATE",
            overall_score=0.0,
            findings_generated=["FAILED_TO_RENDER_PDF_PAGES"],
        )

    # QR Code detector
    qr_detector = cv2.QRCodeDetector()

    MAX_FORENSIC_PAGES = 10
    page_count = doc.page_count
    pages_to_process = min(page_count, MAX_FORENSIC_PAGES)
    if page_count > MAX_FORENSIC_PAGES:
        generated_findings.append(f"Document contains {page_count} pages; forensic deep scan processed first {MAX_FORENSIC_PAGES} pages.")

    # Iterate through document pages from the PDF catalog directly
    for idx in range(pages_to_process):
        page_num = idx + 1
        page = doc[idx]

        # Match PageData if available; otherwise supply fallback
        matched_page = None
        if pages:
            for p in pages:
                if p.page_number == page_num:
                    matched_page = p
                    break
            if matched_page is None and idx < len(pages):
                matched_page = pages[idx]

        p_words = matched_page.words if matched_page else []
        p_width = matched_page.width if matched_page else round(page.rect.width, 2)
        p_height = matched_page.height if matched_page else round(page.rect.height, 2)

        try:
            # Render page pixmap at 150 DPI for forensic fidelity
            pix = page.get_pixmap(dpi=150)
            img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            if pix.n == 4:
                bgr = cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR)
            elif pix.n == 3:
                bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
            else:
                bgr = cv2.cvtColor(img_np, cv2.COLOR_GRAY2BGR)
        except Exception as render_err:
            generated_findings.append(f"Page {page_num}: Failed to render page image: {render_err}")
            continue

        # Scale down if unusually high resolution to maintain <100ms CPU execution
        h, w = bgr.shape[:2]
        if w > MAX_ANALYSIS_WIDTH:
            scale = MAX_ANALYSIS_WIDTH / float(w)
            bgr = cv2.resize(bgr, (MAX_ANALYSIS_WIDTH, int(h * scale)), interpolation=cv2.INTER_AREA)

        # 1. Image Quality
        quality = assess_image_quality(bgr)

        # 2. ELA
        re_bgr = reencode_jpeg(bgr, quality=REENCODE_QUALITY)
        ela_map, mean_res, max_res = error_level_analysis(re_bgr, quality=ELA_QUALITY, scale=ELA_SCALE)
        heatmap_b64 = render_ela_heatmap_base64(bgr, ela_map)

        # 3. SRM Noise Residual
        _, srm_energy = noise_residual(bgr)

        # 4. Copy-Move
        cm_res = detect_copy_move(bgr)

        # 5. Typography Consistency
        outlier_count, token_outliers = detect_typography_outliers(
            bgr,
            p_words,
            p_width,
            p_height,
        )

        # 6. QR Code Detection
        qr_detected = False
        qr_payload = None
        try:
            qr_ok, qr_points, _ = qr_detector.detectAndDecode(bgr)
            if qr_ok and len(qr_ok.strip()) > 0:
                qr_detected = True
                qr_payload = qr_ok.strip()
        except Exception:
            pass

        # Page-level anomalies
        anomalies = list(quality["warnings"])
        if cm_res["suspicious"]:
            anomalies.append("COPY_MOVE_CLONE_DETECTED")
            generated_findings.append(f"Page {page_num}: Copy-Move duplicate region detected ({cm_res['geometric_matches']} inliers).")
        if outlier_count >= 2:
            anomalies.append("TYPOGRAPHY_FONT_STYLE_OUTLIER")
            generated_findings.append(f"Page {page_num}: {outlier_count} typographical stroke/height outlier(s) detected.")
        if mean_res > 0.08:
            anomalies.append("ELEVATED_COMPRESSION_RESIDUAL")

        page_score = 0.0
        if cm_res["suspicious"]:
            page_score += 0.50
        if outlier_count > 0:
            page_score += min(0.30, outlier_count * 0.10)
        if mean_res > 0.08:
            page_score += 0.20
        page_score = min(1.0, round(page_score, 4))
        composite_scores.append(page_score)

        page_results.append(
            ForensicPageResult(
                page_number=page_num,
                ela_mean_residual=mean_res,
                ela_max_residual=max_res,
                srm_energy=srm_energy,
                copy_move_detected=cm_res["suspicious"],
                copy_move_matches=cm_res["geometric_matches"],
                copy_move_score=cm_res["copy_move_score"],
                blur_score=quality["blur_score"],
                glare_ratio=quality["glare_ratio"],
                qr_detected=qr_detected,
                qr_payload=qr_payload,
                style_outliers_count=outlier_count,
                token_style_outliers=token_outliers,
                anomalies=anomalies,
                heatmap_preview_base64=heatmap_b64,
            )
        )

    doc.close()

    overall = max(composite_scores) if composite_scores else 0.0
    summary = "PASS"
    if overall >= 0.50:
        summary = "REVIEW_RECOMMENDED"
    elif overall >= 0.20:
        summary = "ADVISORY"

    return DocumentForensicsResult(
        document_id=document_id,
        filename=filename,
        page_count=page_count,
        page_results=page_results,
        summary_advisory=summary,
        overall_score=round(overall, 4),
        findings_generated=generated_findings,
    )
