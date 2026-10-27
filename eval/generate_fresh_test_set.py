"""
Independent Fresh Test Dataset Generator for VERITAS Release-Gating Evaluation.
Generates 15 fresh, independent benchmark test cases in `eval/fresh_test_cases/`.
Includes diverse PDF producers, hard negatives (benign clock skews, stripped metadata,
spelling variations, borderline compliance), statutory defects, and advisory metadata anomalies.
"""
import os
import sys
import json
from datetime import datetime, timedelta
import pymupdf
from typing import Dict, Any, List

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from synthetic.generator import (
    create_application_form_pdf,
    create_approval_letter_pdf,
    create_land_document_pdf,
    create_fire_noc_pdf,
    create_faculty_list_pdf
)

FRESH_TEST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fresh_test_cases")

def set_custom_pdf_metadata(pdf_path: str, meta: Dict[str, str]) -> None:
    """Inject specific metadata into an existing PDF file using PyMuPDF."""
    doc = pymupdf.open(pdf_path)
    doc.set_metadata(meta)
    temp_path = pdf_path + ".tmp.pdf"
    doc.save(temp_path)
    doc.close()
    os.replace(temp_path, pdf_path)

def build_fresh_test_cases():
    os.makedirs(FRESH_TEST_DIR, exist_ok=True)
    print(f"Generating 15 independent fresh evaluation cases in: {FRESH_TEST_DIR}")

    cases_def = [
        # Case 1: Hard Negative - Benign LibreOffice / Cairo producer with valid timeline
        {
            "id": "fresh_01",
            "name": "Hard Negative: LibreOffice / Cairo Producer with Normal Timeline",
            "institution_name": "Bharat Institute of Technology and Management",
            "institution_name_alt": "Bharat Institute of Technology and Management",
            "application_id": "APP-FR-01",
            "permanent_id": "1-55112233",
            "application_date": "2025-03-15",
            "principal": "Dr. Rajesh K. Sharma",
            "address": "NH-24, Sitapur Road, Lucknow, UP",
            "land_area": 5.2,
            "land_area_doc": 5.2,
            "noc_valid_to": "2026-03-31",
            "academic_year": "2024-2025",
            "faculty_count": 28,
            "faculty_count_doc": 28,
            "custom_producer": "LibreOffice 7.6.4 / Cairo 1.16.0",
            "creation_date": "D:20250220143000+05'30'",
            "mod_date": "D:20250220143500+05'30'",
            "defects": []  # Hard negative: Must PASS completely
        },
        # Case 2: Hard Negative - Privacy-sanitized stripped metadata dictionary
        {
            "id": "fresh_02",
            "name": "Hard Negative: Stripped Info Dictionary (exiftool sanitization)",
            "institution_name": "Pragati College of Engineering",
            "institution_name_alt": "Pragati College of Engineering",
            "application_id": "APP-FR-02",
            "permanent_id": "1-66223344",
            "application_date": "2025-03-15",
            "principal": "Dr. Nivedita Sen",
            "address": "Plot 12, IT Park, Bhubaneswar, Odisha",
            "land_area": 4.5,
            "land_area_doc": 4.5,
            "noc_valid_to": "2026-06-30",
            "academic_year": "2024-2025",
            "faculty_count": 25,
            "faculty_count_doc": 25,
            "strip_metadata": True,
            "defects": []  # Hard negative: Clean stripped PDF must not trigger forgery flags
        },
        # Case 3: Hard Negative - Benign clock skew (ModDate 15 mins before CreationDate, well within 1h tolerance)
        {
            "id": "fresh_03",
            "name": "Hard Negative: Benign Clock Skew (-15 min drift, within 1h threshold)",
            "institution_name": "Kaveri Engineering Institute",
            "institution_name_alt": "Kaveri Engineering Institute",
            "application_id": "APP-FR-03",
            "permanent_id": "1-77334455",
            "application_date": "2025-03-15",
            "principal": "Dr. M. S. Sundaram",
            "address": "Trichy Road, Coimbatore, Tamil Nadu",
            "land_area": 5.0,
            "land_area_doc": 5.0,
            "noc_valid_to": "2026-04-15",
            "academic_year": "2024-2025",
            "faculty_count": 30,
            "faculty_count_doc": 30,
            "creation_date": "D:20250301103000+05'30'",
            "mod_date": "D:20250301101500+05'30'",  # -15 mins skew (900s < 3600s threshold)
            "defects": []  # Hard negative: Must NOT trigger META-001
        },
        # Case 4: Hard Negative - Legitimate honorific spelling variant (Sri vs Shri, token sort > 90)
        {
            "id": "fresh_04",
            "name": "Hard Negative: Legitimate Honorific Spelling (Sri vs Shri)",
            "institution_name": "Sri Venkateswara Institute of Technology",
            "institution_name_alt": "Shri Venkateswara Institute of Technology",
            "application_id": "APP-FR-04",
            "permanent_id": "1-88445566",
            "application_date": "2025-03-15",
            "principal": "Dr. K. Ramachandra",
            "address": "Tirupati Road, Chittoor, Andhra Pradesh",
            "land_area": 6.5,
            "land_area_doc": 6.5,
            "noc_valid_to": "2026-05-31",
            "academic_year": "2024-2025",
            "faculty_count": 35,
            "faculty_count_doc": 35,
            "defects": []  # Hard negative: Must PASS name matching
        },
        # Case 5: Hard Negative - Fire NOC expiring on academic year cutoff (valid on submission)
        {
            "id": "fresh_05",
            "name": "Hard Negative: Fire NOC Valid at Filing (Expires 2025-06-30)",
            "institution_name": "Amity Technical Campus",
            "institution_name_alt": "Amity Technical Campus",
            "application_id": "APP-FR-05",
            "permanent_id": "1-99556677",
            "application_date": "2025-03-15",
            "principal": "Dr. Alok Verma",
            "address": "Knowledge Park III, Greater Noida, UP",
            "land_area": 7.5,
            "land_area_doc": 7.5,
            "noc_valid_to": "2025-06-30",  # Postdates 2025-03-15 filing
            "academic_year": "2024-2025",
            "faculty_count": 40,
            "faculty_count_doc": 40,
            "defects": []  # Hard negative: Valid at filing date
        },
        # Case 6: Hard Negative - Borderline valid land acreage (declared 4.00 acres, deed has 4.02 acres)
        {
            "id": "fresh_06",
            "name": "Hard Negative: Borderline Valid Land Acreage (4.02 deed vs 4.00 declared)",
            "institution_name": "Sahyadri College of Engineering",
            "institution_name_alt": "Sahyadri College of Engineering",
            "application_id": "APP-FR-06",
            "permanent_id": "1-11667788",
            "application_date": "2025-03-15",
            "principal": "Dr. Prashant Hegde",
            "address": "Adyar, Mangalore, Karnataka",
            "land_area": 4.00,
            "land_area_doc": 4.02,  # Deed exceeds declared by 0.02 acre (compliant)
            "noc_valid_to": "2026-03-31",
            "academic_year": "2024-2025",
            "faculty_count": 26,
            "faculty_count_doc": 26,
            "defects": []  # Hard negative: Deed meets/exceeds requirement
        },
        # Case 7: Hard Negative - macOS Quartz PDFContext producer with valid timestamps
        {
            "id": "fresh_07",
            "name": "Hard Negative: macOS Quartz PDFContext Producer",
            "institution_name": "Malabar Institute of Technology",
            "institution_name_alt": "Malabar Institute of Technology",
            "application_id": "APP-FR-07",
            "permanent_id": "1-22778899",
            "application_date": "2025-03-15",
            "principal": "Dr. C. P. Narayanan",
            "address": "Anjarakandy, Kannur, Kerala",
            "land_area": 5.1,
            "land_area_doc": 5.1,
            "noc_valid_to": "2026-04-30",
            "academic_year": "2024-2025",
            "faculty_count": 24,
            "faculty_count_doc": 24,
            "custom_producer": "macOS Version 14.4 (Build 23E214) Quartz PDFContext",
            "creation_date": "D:20250225110000+05'30'",
            "mod_date": "D:20250225110500+05'30'",
            "defects": []  # Hard negative: Legitimate commercial OS producer
        },
        # Case 8: Statutory Defect - Missing Mandatory Fire Safety Certificate (Annexure 2 §2.1(v))
        {
            "id": "fresh_08",
            "name": "Statutory Defect: Missing Fire Safety Certificate",
            "institution_name": "Shivalik Institute of Engineering",
            "institution_name_alt": "Shivalik Institute of Engineering",
            "application_id": "APP-FR-08",
            "permanent_id": "1-33889900",
            "application_date": "2025-03-15",
            "principal": "Dr. Harpreet Singh",
            "address": "Shimla Bypass Road, Dehradun, Uttarakhand",
            "land_area": 5.5,
            "land_area_doc": 5.5,
            "academic_year": "2024-2025",
            "faculty_count": 28,
            "faculty_count_doc": 28,
            "skip_documents": ["fire_noc.pdf"],
            "defects": ["MISSING_DOCUMENT"]
        },
        # Case 9: Statutory Defect - Expired Fire Safety Certificate (Expired 2024-12-31)
        {
            "id": "fresh_09",
            "name": "Statutory Defect: Expired Fire NOC (Expired prior to filing)",
            "institution_name": "Narmada Valley Institute of Technology",
            "institution_name_alt": "Narmada Valley Institute of Technology",
            "application_id": "APP-FR-09",
            "permanent_id": "1-44990011",
            "application_date": "2025-03-15",
            "principal": "Dr. Deepak Chouhan",
            "address": "Hoshangabad Road, Bhopal, MP",
            "land_area": 5.0,
            "land_area_doc": 5.0,
            "noc_valid_to": "2024-12-31",  # Expired 2.5 months before 2025-03-15 filing
            "academic_year": "2024-2025",
            "faculty_count": 25,
            "faculty_count_doc": 25,
            "defects": ["EXPIRED_CERTIFICATE"]
        },
        # Case 10: Technical Consistency Defect - Entity Name Divergence
        {
            "id": "fresh_10",
            "name": "Technical Defect: Entity Name Divergence (Kalinga vs Coastal Maritime)",
            "institution_name": "Kalinga Institute of Engineering",
            "institution_name_alt": "Southern Coastal Maritime Academy",
            "application_id": "APP-FR-10",
            "permanent_id": "1-55001122",
            "application_date": "2025-03-15",
            "principal": "Dr. B. K. Mohanty",
            "address": "Patia, Bhubaneswar, Odisha",
            "land_area": 6.0,
            "land_area_doc": 6.0,
            "noc_valid_to": "2026-03-31",
            "academic_year": "2024-2025",
            "faculty_count": 30,
            "faculty_count_doc": 30,
            "defects": ["NAME_MISMATCH"]
        },
        # Case 11: Statutory Mandate Defect - Land Area Shortfall vs Declared & Norms (Annexure 3 §3.1)
        {
            "id": "fresh_11",
            "name": "Statutory Defect: Land Area Shortfall (3.20 deed vs 5.00 declared)",
            "institution_name": "Deccan College of Technical Studies",
            "institution_name_alt": "Deccan College of Technical Studies",
            "application_id": "APP-FR-11",
            "permanent_id": "1-66112233",
            "application_date": "2025-03-15",
            "principal": "Dr. Syed Mir Qasim",
            "address": "Mehdipatnam, Hyderabad, Telangana",
            "land_area": 5.00,       # Declared
            "land_area_doc": 3.20,   # Documented: 1.80 acre shortfall
            "noc_valid_to": "2026-05-15",
            "academic_year": "2024-2025",
            "faculty_count": 27,
            "faculty_count_doc": 27,
            "defects": ["AREA_MISMATCH"]
        },
        # Case 12: Advisory Metadata Anomaly - META-001 Temporal Sequence Inversion (-180 days)
        {
            "id": "fresh_12",
            "name": "Advisory Flag: META-001 Temporal Sequence Inversion (-180 days)",
            "institution_name": "Aravalli Academy of Technology",
            "institution_name_alt": "Aravalli Academy of Technology",
            "application_id": "APP-FR-12",
            "permanent_id": "1-77223344",
            "application_date": "2025-03-15",
            "principal": "Dr. Mahendra Rathore",
            "address": "Udaipur Highway, Udaipur, Rajasthan",
            "land_area": 5.0,
            "land_area_doc": 5.0,
            "noc_valid_to": "2026-04-30",
            "academic_year": "2024-2025",
            "faculty_count": 25,
            "faculty_count_doc": 25,
            "creation_date": "D:20250301120000+05'30'",
            "mod_date": "D:20240901120000+05'30'",  # ModDate precedes CreationDate by 181 days!
            "defects": ["METADATA_ANOMALY"]
        },
        # Case 13: Advisory Metadata Anomaly - META-002 Retroactive Post-Filing Creation (+45 days)
        {
            "id": "fresh_13",
            "name": "Advisory Flag: META-002 Retroactive Post-Filing Creation (+45 days)",
            "institution_name": "Himalayan Polytechnic Institute",
            "institution_name_alt": "Himalayan Polytechnic Institute",
            "application_id": "APP-FR-13",
            "permanent_id": "1-88334455",
            "application_date": "2025-03-15",
            "principal": "Dr. Tashi Dorje",
            "address": "Mandi Road, Mandi, Himachal Pradesh",
            "land_area": 4.5,
            "land_area_doc": 4.5,
            "noc_valid_to": "2026-03-31",
            "academic_year": "2024-2025",
            "faculty_count": 22,
            "faculty_count_doc": 22,
            "creation_date": "D:20250430100000+05'30'",  # 46 days after application filing!
            "mod_date": "D:20250430101000+05'30'",
            "defects": ["METADATA_ANOMALY"]
        },
        # Case 14: Advisory Metadata Anomaly - META-003 Non-Standard / Omitted Timezone Syntax
        {
            "id": "fresh_14",
            "name": "Advisory Flag: META-003 Syntax Warning (Omitted Timezone)",
            "institution_name": "Vindhya Institute of Technology",
            "institution_name_alt": "Vindhya Institute of Technology",
            "application_id": "APP-FR-14",
            "permanent_id": "1-99445566",
            "application_date": "2025-03-15",
            "principal": "Dr. Suresh Agrawal",
            "address": "Rewa Road, Satna, MP",
            "land_area": 5.2,
            "land_area_doc": 5.2,
            "noc_valid_to": "2026-05-31",
            "academic_year": "2024-2025",
            "faculty_count": 26,
            "faculty_count_doc": 26,
            "creation_date": "D:20250215120000",  # Missing timezone offset
            "mod_date": "D:20250215121000",
            "defects": ["METADATA_ANOMALY"]
        },
        # Case 15: External Registry Source Unavailable
        {
            "id": "fresh_15",
            "name": "External Registry: Central Portal Source Unavailable",
            "institution_name": "Eastern Frontier Institute of Technology",
            "institution_name_alt": "Eastern Frontier Institute of Technology",
            "application_id": "APP-FR-15",
            "permanent_id": "1-9998887776",  # Unregistered PID
            "application_date": "2025-03-15",
            "principal": "Dr. L. K. Barua",
            "address": "Jalukbari, Guwahati, Assam",
            "land_area": 5.0,
            "land_area_doc": 5.0,
            "noc_valid_to": "2026-06-30",
            "academic_year": "2024-2025",
            "faculty_count": 25,
            "faculty_count_doc": 25,
            "defects": ["UNAVAILABLE_SOURCE"]
        }
    ]

    for c in cases_def:
        case_id = c["id"]
        case_dir = os.path.join(FRESH_TEST_DIR, case_id)
        os.makedirs(case_dir, exist_ok=True)

        app_pid = c["permanent_id"]
        appr_pid = c.get("approval_letter_pid", app_pid)

        # 1. Application Form
        app_file = os.path.join(case_dir, "application_form.pdf")
        app_data = {
            "application_id": c["application_id"],
            "permanent_id": app_pid,
            "institution_name": c["institution_name"],
            "application_date": c["application_date"],
            "principal_name": c["principal"],
            "address": c["address"],
            "declared_land_area": c["land_area"],
            "declared_faculty_count": c["faculty_count"],
        }
        create_application_form_pdf(app_file, app_data)

        # 2. Approval Letter
        appr_file = os.path.join(case_dir, "approval_letter.pdf")
        appr_data = {
            "approval_letter_app_id": c["application_id"],
            "approval_letter_permanent_id": appr_pid,
            "approval_letter_institute_name": c["institution_name"],
            "approved_academic_year": c["academic_year"],
            "address": c["address"],
        }
        create_approval_letter_pdf(appr_file, appr_data)

        # 3. Land Document
        land_file = os.path.join(case_dir, "land_document.pdf")
        land_data = {
            "land_doc_institute_name": c["institution_name_alt"],
            "khasra_no": "205/3A",
            "land_doc_area_acres": c["land_area_doc"],
            "deed_date": "2019-02-18",
            "deed_number": f"DEED-{case_id.upper()}-9902",
        }
        create_land_document_pdf(land_file, land_data)

        # 4. Fire NOC
        skip_docs = c.get("skip_documents", [])
        fire_file = os.path.join(case_dir, "fire_noc.pdf")
        if "fire_noc.pdf" not in skip_docs:
            fire_data = {
                "noc_number": f"FNOC-{case_id.upper()}-2024",
                "fire_noc_institute_name": c["institution_name_alt"],
                "fire_noc_valid_to": c.get("noc_valid_to", "2026-03-31"),
                "fire_issue_date": "2024-05-15",
                "address": c["address"],
            }
            create_fire_noc_pdf(fire_file, fire_data)

        # 5. Faculty List
        faculty_file = os.path.join(case_dir, "faculty_list.pdf")
        fac_count = c["faculty_count_doc"]
        fac_list = []
        cadres = ["Professor", "Associate Professor", "Assistant Professor"]
        for idx in range(fac_count):
            fac_list.append({
                "name": f"Faculty Member {idx+1}",
                "designation": cadres[min(idx // 6, 2)],
                "department": "Computer Science & Engineering",
                "qualification": "Ph.D" if idx < 8 else "M.Tech"
            })
        faculty_data = {
            "faculty_institute_name": c["institution_name"],
            "application_id": c["application_id"],
            "faculty_list_count": fac_count,
            "principal_name": c["principal"],
            "faculty_members": fac_list,
        }
        create_faculty_list_pdf(faculty_file, faculty_data)

        # Apply metadata customizations
        files_to_customize = [app_file, appr_file, land_file, faculty_file]
        if "fire_noc.pdf" not in skip_docs:
            files_to_customize.append(fire_file)

        for fpath in files_to_customize:
            if c.get("strip_metadata"):
                set_custom_pdf_metadata(fpath, {})
            elif c.get("creation_date") or c.get("mod_date") or c.get("custom_producer"):
                meta_dict = {}
                if c.get("custom_producer"):
                    meta_dict["producer"] = c["custom_producer"]
                if c.get("creation_date"):
                    meta_dict["creationDate"] = c["creation_date"]
                if c.get("mod_date"):
                    meta_dict["modDate"] = c["mod_date"]
                set_custom_pdf_metadata(fpath, meta_dict)
            else:
                # Standard benign metadata matching the application timeline (pre-filing)
                app_date_str = c.get("application_date", "2025-03-15")
                try:
                    app_dt = datetime.strptime(app_date_str, "%Y-%m-%d")
                except Exception:
                    app_dt = datetime(2025, 3, 15)
                pre_filing_dt = app_dt - timedelta(days=6, hours=4)
                norm_ts = f"D:{pre_filing_dt.strftime('%Y%m%d%H%M%S')}+05'30'"
                meta_dict = {
                    "producer": "VERITAS AICTE Automated Filing Engine v2025.2",
                    "creator": "Institutional Compliance Suite",
                    "creationDate": norm_ts,
                    "modDate": norm_ts
                }
                set_custom_pdf_metadata(fpath, meta_dict)

        # Write ground truth JSON
        truth_dict = {
            "case_id": case_id,
            "case_name": c["name"],
            "institution_name": c["institution_name"],
            "application_date": c["application_date"],
            "planted_defects": c["defects"],
            "generated_files": [os.path.basename(f) for f in files_to_customize]
        }
        with open(os.path.join(case_dir, "truth.json"), "w", encoding="utf-8") as tf:
            json.dump(truth_dict, tf, indent=2)

    print("Successfully created 15 independent fresh evaluation cases.")

if __name__ == "__main__":
    build_fresh_test_cases()
