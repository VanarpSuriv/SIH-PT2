"""
Forensic Document Analysis Package for VERITAS.
Implements Error Level Analysis (ELA), Spatial Rich Model (SRM) noise residuals,
Otsu distance-transform typography stroke/height consistency, SIFT/RANSAC copy-move detection,
and scan quality assessment.
"""
from backend.forensics.engine import (
    analyze_document_forensics,
    error_level_analysis,
    noise_residual,
    detect_copy_move,
    detect_typography_outliers,
    assess_image_quality,
)

__all__ = [
    "analyze_document_forensics",
    "error_level_analysis",
    "noise_residual",
    "detect_copy_move",
    "detect_typography_outliers",
    "assess_image_quality",
]
