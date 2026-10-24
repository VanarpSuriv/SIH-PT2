"""
Evaluation Script for AICTE EoA Verification Pipeline.
Benchmarks extraction accuracy, precision, recall, false-positive rate, and processing latency across all 25 synthetic cases.
"""
import os
import sys

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import time
from typing import Dict, List, Any, Tuple
from rapidfuzz import fuzz

from backend.models import (
    DocumentType,
    FindingStatus,
    Severity
)
from backend.ingest.service import extract_pdf_data
from backend.extract.service import extract_document_fields
from backend.rules.engine import RulesEngine
from backend.verify.adapter import get_verification_adapter

CASES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "synthetic", "cases")

DEFECT_CATEGORIES = [
    "MISSING_DOCUMENT",
    "EXPIRED_CERTIFICATE",
    "NAME_MISMATCH",
    "DATE_CONFLICT",
    "AREA_MISMATCH",
    "FACULTY_MISMATCH",
    "UNAVAILABLE_SOURCE"
]

def map_finding_to_defect_category(rule_id: str, claim: str) -> List[str]:
    """Map rule finding to defect category."""
    cats = []
    if rule_id in ["AICTE-EOA-001", "AICTE-EOA-002", "AICTE-EOA-003", "AICTE-EOA-004"]:
        cats.append("MISSING_DOCUMENT")
    if rule_id == "AICTE-EOA-005":
        # Check if the finding indicates an expired certificate or date conflict
        if "2026" in claim or "conflict" in claim.lower():
            cats.append("DATE_CONFLICT")
        if any(yr in claim for yr in ["2022", "2023", "2024"]):
            cats.append("EXPIRED_CERTIFICATE")
        if not cats:
            cats.append("EXPIRED_CERTIFICATE")
    if rule_id == "AICTE-EOA-006":
        cats.append("EXPIRED_CERTIFICATE")
    if rule_id == "AICTE-EOA-007":
        cats.append("NAME_MISMATCH")
    if rule_id == "AICTE-EOA-008":
        cats.append("NAME_MISMATCH")
    if rule_id == "AICTE-EOA-009":
        cats.append("AREA_MISMATCH")
    if rule_id == "AICTE-EOA-010":
        cats.append("FACULTY_MISMATCH")
    return cats

def normalize_truth_defect(d: str) -> str:
    """Normalize ground truth defect tag to category."""
    if "MISSING" in d:
        return "MISSING_DOCUMENT"
    if "EXPIRED" in d or "OUTDATED" in d:
        return "EXPIRED_CERTIFICATE"
    if "NAME_MISMATCH" in d:
        return "NAME_MISMATCH"
    if "DATE_CONFLICT" in d:
        return "DATE_CONFLICT"
    if "AREA" in d:
        return "AREA_MISMATCH"
    if "FACULTY" in d:
        return "FACULTY_MISMATCH"
    if "SOURCE_UNAVAILABLE" in d or "ISSUER" in d:
        return "UNAVAILABLE_SOURCE"
    return d

def evaluate_all_cases() -> Dict[str, Any]:
    """Run full evaluation suite across all cases."""
    rules_engine = RulesEngine()
    verifier = get_verification_adapter()

    total_fields_expected = 0
    total_fields_correct = 0

    confusion_matrix = {
        cat: {"TP": 0, "FP": 0, "FN": 0, "TN": 0} for cat in DEFECT_CATEGORIES
    }

    latencies_ms: List[float] = []

    case_dirs = sorted([d for d in os.listdir(CASES_DIR) if os.path.isdir(os.path.join(CASES_DIR, d))])

    print(f"\n========================================================")
    print(f"  RUNNING BENCHMARK EVALUATION OVER {len(case_dirs)} SYNTHETIC CASES")
    print(f"========================================================\n")

    for case_name in case_dirs:
        case_path = os.path.join(CASES_DIR, case_name)
        truth_file = os.path.join(case_path, "truth.json")
        if not os.path.exists(truth_file):
            continue

        with open(truth_file, "r", encoding="utf-8") as tf:
            truth = json.load(tf)

        t0 = time.perf_counter()

        # Ingest and Extract
        docs = []
        all_fields = []
        for fname in truth.get("generated_files", []):
            fpath = os.path.join(case_path, fname)
            with open(fpath, "rb") as pdf_f:
                content = pdf_f.read()
            doc_rec, pages = extract_pdf_data(content, fname, truth["application_id"], fpath)
            docs.append(doc_rec)
            fields = extract_document_fields(doc_rec, pages)
            all_fields.extend(fields)

        # Field Extraction Accuracy against Ground Truth
        expected_fields = truth.get("fields", {})
        extracted_map = {f.name: f.value for f in all_fields}

        for k, exp_val in expected_fields.items():
            # Only evaluate field if its document was generated
            if k == "fire_noc_valid_to" and "fire_noc.pdf" not in truth["generated_files"]:
                continue
            if k == "land_doc_area_acres" and "land_document.pdf" not in truth["generated_files"]:
                continue
            if k == "approved_academic_year" and "approval_letter.pdf" not in truth["generated_files"]:
                continue
            if k == "faculty_list_count" and "faculty_list.pdf" not in truth["generated_files"]:
                continue

            total_fields_expected += 1
            if k in extracted_map:
                actual_val = extracted_map[k]
                if isinstance(exp_val, float):
                    try:
                        if abs(float(actual_val) - exp_val) < 0.01:
                            total_fields_correct += 1
                    except Exception:
                        pass
                elif str(actual_val).strip() == str(exp_val).strip():
                    total_fields_correct += 1
                elif fuzz.token_sort_ratio(str(actual_val), str(exp_val)) > 90:
                    total_fields_correct += 1

        # Run Rules Engine
        findings = rules_engine.evaluate(truth["application_id"], docs, all_fields)

        # Detect defects from findings
        detected_cats = set()
        for f in findings:
            if f.status == FindingStatus.FAIL:
                cats = map_finding_to_defect_category(f.rule_id, f.claim)
                for c in cats:
                    detected_cats.add(c)

        # Check external verifier for UNAVAILABLE_SOURCE or ISSUER_RECORD_MISMATCH
        perm_id = truth.get("permanent_id")
        if perm_id:
            res = verifier.verify("AICTE_CENTRAL_PORTAL", perm_id)
            if res.status.value in ["source unavailable", "mismatch"]:
                detected_cats.add("UNAVAILABLE_SOURCE")

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        latencies_ms.append(elapsed_ms)

        # Ground truth defects
        raw_planted = truth.get("planted_defects", [])
        ground_truth_cats = set([normalize_truth_defect(d) for d in raw_planted])

        # Update confusion matrix
        for cat in DEFECT_CATEGORIES:
            is_present = cat in ground_truth_cats
            is_detected = cat in detected_cats
            if is_present and is_detected:
                confusion_matrix[cat]["TP"] += 1
            elif not is_present and is_detected:
                confusion_matrix[cat]["FP"] += 1
            elif is_present and not is_detected:
                confusion_matrix[cat]["FN"] += 1
            else:
                confusion_matrix[cat]["TN"] += 1

    extraction_accuracy = (total_fields_correct / total_fields_expected) * 100.0 if total_fields_expected else 100.0
    avg_latency = sum(latencies_ms) / len(latencies_ms) if latencies_ms else 0.0

    print("### PROTOTYPE EVALUATION RESULTS (SLIDE 5 PROMISES)\n")
    print(f"| Metric | Result | Benchmark Target |")
    print(f"| :--- | :--- | :--- |")
    print(f"| **Overall Field Extraction Accuracy** | **{extraction_accuracy:.2f}%** | >= 95.0% |")
    print(f"| **Average Processing Time per Case** | **{avg_latency:.1f} ms** | < 250 ms |")
    print(f"| **Total Test Cases Evaluated** | **{len(case_dirs)} cases** | 20-30 cases |")
    print(f"| **Total Extracted Fields Scored** | **{total_fields_correct}/{total_fields_expected}** | - |\n")

    print("### DEFECT DETECTION PRECISION & RECALL MATRIX\n")
    print("| Defect Category | True Pos (TP) | False Pos (FP) | False Neg (FN) | Precision | Recall | False Pos Rate (FPR) |")
    print("| :--- | :---: | :---: | :---: | :---: | :---: | :---: |")

    tot_tp, tot_fp, tot_fn, tot_tn = 0, 0, 0, 0

    for cat in DEFECT_CATEGORIES:
        cm = confusion_matrix[cat]
        tp, fp, fn, tn = cm["TP"], cm["FP"], cm["FN"], cm["TN"]
        tot_tp += tp
        tot_fp += fp
        tot_fn += fn
        tot_tn += tn

        precision = (tp / (tp + fp)) * 100.0 if (tp + fp) > 0 else 100.0
        recall = (tp / (tp + fn)) * 100.0 if (tp + fn) > 0 else 100.0
        fpr = (fp / (fp + tn)) * 100.0 if (fp + tn) > 0 else 0.0

        print(f"| {cat} | {tp} | {fp} | {fn} | {precision:.1f}% | {recall:.1f}% | {fpr:.1f}% |")

    overall_prec = (tot_tp / (tot_tp + tot_fp)) * 100.0 if (tot_tp + tot_fp) > 0 else 100.0
    overall_rec = (tot_tp / (tot_tp + tot_fn)) * 100.0 if (tot_tp + tot_fn) > 0 else 100.0
    overall_fpr = (tot_fp / (tot_fp + tot_tn)) * 100.0 if (tot_fp + tot_tn) > 0 else 0.0

    print(f"| **MICRO-AVERAGE TOTAL** | **{tot_tp}** | **{tot_fp}** | **{tot_fn}** | **{overall_prec:.1f}%** | **{overall_rec:.1f}%** | **{overall_fpr:.1f}%** |\n")

    return {
        "extraction_accuracy": extraction_accuracy,
        "avg_latency_ms": avg_latency,
        "overall_precision": overall_prec,
        "overall_recall": overall_rec,
        "overall_fpr": overall_fpr,
        "confusion_matrix": confusion_matrix
    }

if __name__ == "__main__":
    evaluate_all_cases()
