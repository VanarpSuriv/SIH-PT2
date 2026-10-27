"""
Independently Authored Held-Out Evaluation Dataset Generator with Hard Negatives.
Generates 15 challenging benchmark test cases with ground-truth planted defects,
borderline valid cases (hard negatives), subtle shortfalls, and metadata variants.
"""
import os
import sys
import json
from datetime import datetime, timedelta
import pymupdf
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

from synthetic.generator import (
    create_application_form_pdf,
    create_approval_letter_pdf,
    create_land_document_pdf,
    create_fire_noc_pdf,
    create_faculty_list_pdf
)

HELD_OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "held_out_cases")

def set_custom_pdf_metadata(pdf_path: str, meta: Dict[str, str]) -> None:
    """Inject specific metadata into an existing PDF file using PyMuPDF."""
    doc = pymupdf.open(pdf_path)
    doc.set_metadata(meta)
    temp_path = pdf_path + ".tmp.pdf"
    doc.save(temp_path)
    doc.close()
    os.replace(temp_path, pdf_path)

def build_held_out_cases():
    os.makedirs(HELD_OUT_DIR, exist_ok=True)
    print(f"Generating 15 held-out evaluation test cases in: {HELD_OUT_DIR}")

    cases_def = [
        # Case 1: Hard Negative - Minor legitimate name abbreviation (RapidFuzz token sort ~88% > 85% threshold)
        {
            "id": "held_out_01",
            "name": "Hard Negative: Legitimate Name Abbreviation (Saint vs St)",
            "institution_name": "St. Anne's Institute of Technology",
            "institution_name_alt": "Saint Anne Institute of Technology",
            "application_id": "APP-HO-01",
            "permanent_id": "1-11223344",
            "application_date": "2025-03-15",
            "principal": "Dr. Angela Dsouza",
            "address": "42 Cathedral Road, Bangalore, Karnataka",
            "land_area": 5.0,
            "land_area_doc": 5.0,
            "noc_valid_to": "2026-03-15",
            "academic_year": "2024-2025",
            "faculty_count": 25,
            "faculty_count_doc": 25,
            "defects": [] # Hard negative: should PASS completely
        },
        # Case 2: Hard Negative - Benign modern open-source tool producer (pdfcpu/Ghostscript)
        {
            "id": "held_out_02",
            "name": "Hard Negative: Open-Source Tool Producer with Valid Timeline",
            "institution_name": "National Institute of Science and Technology",
            "institution_name_alt": "National Institute of Science and Technology",
            "application_id": "APP-HO-02",
            "permanent_id": "1-22334455",
            "application_date": "2025-03-15",
            "principal": "Dr. Ramesh Nair",
            "address": "Tech Campus, Thiruvananthapuram, Kerala",
            "land_area": 6.2,
            "land_area_doc": 6.2,
            "noc_valid_to": "2026-06-30",
            "academic_year": "2024-2025",
            "faculty_count": 30,
            "faculty_count_doc": 30,
            "custom_producer": "pdfcpu v0.4.1 / Ghostscript 10.02.0",
            "creation_date": "D:20250210090000Z",
            "mod_date": "D:20250210091500Z",
            "defects": [] # Hard negative: benign producer must not fail
        },
        # Case 3: Hard Negative - Completely stripped metadata
        {
            "id": "held_out_03",
            "name": "Hard Negative: Completely Stripped Metadata Info Dictionary",
            "institution_name": "Modern Academy of Technology and Research",
            "institution_name_alt": "Modern Academy of Technology and Research",
            "application_id": "APP-HO-03",
            "permanent_id": "1-33445566",
            "application_date": "2025-03-15",
            "principal": "Dr. Sunita Rao",
            "address": "Knowledge Park II, Greater Noida, UP",
            "land_area": 4.5,
            "land_area_doc": 4.5,
            "noc_valid_to": "2026-02-28",
            "academic_year": "2024-2025",
            "faculty_count": 28,
            "faculty_count_doc": 28,
            "strip_metadata": True,
            "defects": [] # Hard negative: missing metadata must not fail
        },
        # Case 4: Hard Defect - Subtle land shortfall (2.41 acres vs 2.50 acres required)
        {
            "id": "held_out_04",
            "name": "Hard Defect: Subtle Land Shortfall (2.41 vs 2.50 Acres)",
            "institution_name": "Zenith Institute of Engineering",
            "institution_name_alt": "Zenith Institute of Engineering",
            "application_id": "APP-HO-04",
            "permanent_id": "1-44556677",
            "application_date": "2025-03-15",
            "principal": "Dr. Vikas Joshi",
            "address": "Sector 18, Urban Corridor, Pune",
            "land_area": 2.50, # Declares 2.50 acres
            "land_area_doc": 2.41, # Actual deed is 2.41 acres (short by 0.09 acres!)
            "noc_valid_to": "2026-04-10",
            "academic_year": "2024-2025",
            "faculty_count": 22,
            "faculty_count_doc": 22,
            "defects": ["AREA_MISMATCH"]
        },
        # Case 5: Hard Defect - Subtle faculty deficit (1 missing Assistant Professor)
        {
            "id": "held_out_05",
            "name": "Hard Defect: Subtle Faculty Deficit (32 declared vs 31 rostered)",
            "institution_name": "Horizon College of Technology",
            "institution_name_alt": "Horizon College of Technology",
            "application_id": "APP-HO-05",
            "permanent_id": "1-55667788",
            "application_date": "2025-03-15",
            "principal": "Dr. Arvind Swaminathan",
            "address": "Gachibowli, Hyderabad, Telangana",
            "land_area": 5.5,
            "land_area_doc": 5.5,
            "noc_valid_to": "2026-05-15",
            "academic_year": "2024-2025",
            "faculty_count": 32, # Declares 32
            "faculty_count_doc": 31, # Roster has 31
            "defects": ["FACULTY_MISMATCH"]
        },
        # Case 6: Hard Defect - PID Digit Transposition (1-8899221100 vs 1-8899221010)
        {
            "id": "held_out_06",
            "name": "Hard Defect: Permanent Institute ID Transposition",
            "institution_name": "Pioneer Institute of Technology",
            "institution_name_alt": "Pioneer Institute of Technology",
            "application_id": "APP-HO-06",
            "permanent_id": "1-8899221100",
            "approval_letter_pid": "1-8899221010", # Transposed
            "application_date": "2025-03-15",
            "principal": "Dr. Preeti Verma",
            "address": "Ring Road, Nagpur, Maharashtra",
            "land_area": 4.8,
            "land_area_doc": 4.8,
            "noc_valid_to": "2026-03-31",
            "academic_year": "2024-2025",
            "faculty_count": 26,
            "faculty_count_doc": 26,
            "defects": ["PID_MISMATCH"]
        },
        # Case 7: Hard Defect - Fire NOC expired 2 days before submission
        {
            "id": "held_out_07",
            "name": "Hard Defect: Fire NOC Expired by 2 Days",
            "institution_name": "Sterling Institute of Engineering",
            "institution_name_alt": "Sterling Institute of Engineering",
            "application_id": "APP-HO-07",
            "permanent_id": "1-66778899",
            "application_date": "2025-03-15",
            "principal": "Dr. Ananya Roy",
            "address": "Salt Lake Sector V, Kolkata, West Bengal",
            "land_area": 5.2,
            "land_area_doc": 5.2,
            "noc_valid_to": "2025-03-13", # 2 days before submission date 2025-03-15!
            "academic_year": "2024-2025",
            "faculty_count": 24,
            "faculty_count_doc": 24,
            "defects": ["EXPIRED_CERTIFICATE"]
        },
        # Case 8: Hard Negative - Fire NOC expiring soon after submission (valid on submission date)
        {
            "id": "held_out_08",
            "name": "Hard Negative: Fire NOC Valid at Submission (Expires 13 Days Later)",
            "institution_name": "Trident College of Engineering",
            "institution_name_alt": "Trident College of Engineering",
            "application_id": "APP-HO-08",
            "permanent_id": "1-77889900",
            "application_date": "2025-03-15",
            "principal": "Dr. Vijay Kulkarni",
            "address": "Industrial Area, Vadodara, Gujarat",
            "land_area": 6.0,
            "land_area_doc": 6.0,
            "noc_valid_to": "2025-03-28", # Valid on 2025-03-15 submission date!
            "academic_year": "2024-2025",
            "faculty_count": 27,
            "faculty_count_doc": 27,
            "defects": [] # Hard negative: Must PASS under AICTE rules
        },
        # Case 9: Hard Defect - Outdated Approval Letter (2023-2024 instead of 2024-2025)
        {
            "id": "held_out_09",
            "name": "Hard Defect: Discontinuous Approval Letter (2023-2024)",
            "institution_name": "Galaxy Institute of Technology",
            "institution_name_alt": "Galaxy Institute of Technology",
            "application_id": "APP-HO-09",
            "permanent_id": "1-88990011",
            "application_date": "2025-03-15",
            "principal": "Dr. Sneha Mehra",
            "address": "Bhopal Bypass Road, Bhopal, MP",
            "land_area": 5.8,
            "land_area_doc": 5.8,
            "noc_valid_to": "2026-05-30",
            "academic_year": "2023-2024", # Missing 2024-2025!
            "faculty_count": 25,
            "faculty_count_doc": 25,
            "defects": ["EXPIRED_CERTIFICATE"]
        },
        # Case 10: Hard Defect - Missing Mandatory Fire Safety NOC
        {
            "id": "held_out_10",
            "name": "Hard Defect: Missing Fire Safety Clearance Certificate",
            "institution_name": "Vanguard Engineering College",
            "institution_name_alt": "Vanguard Engineering College",
            "application_id": "APP-HO-10",
            "permanent_id": "1-99001122",
            "application_date": "2025-03-15",
            "principal": "Dr. Devendra Pandey",
            "address": "Sitapura Industrial Area, Jaipur, Rajasthan",
            "land_area": 7.0,
            "land_area_doc": 7.0,
            "academic_year": "2024-2025",
            "faculty_count": 29,
            "faculty_count_doc": 29,
            "skip_documents": ["fire_noc.pdf"],
            "defects": ["MISSING_DOCUMENT"]
        },
        # Case 11: Hard Defect - Substantial Entity Divergence (Completely Different Trust Name)
        {
            "id": "held_out_11",
            "name": "Hard Defect: Entity Divergence (Vidyapeeth vs Shree Balaji)",
            "institution_name": "Vidyapeeth Engineering Academy",
            "institution_name_alt": "Shree Balaji Education Trust Polytechnic",
            "application_id": "APP-HO-11",
            "permanent_id": "1-10111213",
            "application_date": "2025-03-15",
            "principal": "Dr. Jayant Patil",
            "address": "Solapur Highway, Pune, Maharashtra",
            "land_area": 5.0,
            "land_area_doc": 5.0,
            "noc_valid_to": "2026-04-15",
            "academic_year": "2024-2025",
            "faculty_count": 25,
            "faculty_count_doc": 25,
            "defects": ["NAME_MISMATCH"]
        },
        # Case 12: Hard Defect - META-001 (ModDate Precedes CreationDate by 2,376 hours)
        {
            "id": "held_out_12",
            "name": "Hard Defect: META-001 Temporal Sequence Inversion",
            "institution_name": "Olympus Institute of Technology",
            "institution_name_alt": "Olympus Institute of Technology",
            "application_id": "APP-HO-12",
            "permanent_id": "1-12131415",
            "application_date": "2025-03-15",
            "principal": "Dr. Manoj Saxena",
            "address": "Tech Park Phase 1, Chandigarh",
            "land_area": 5.0,
            "land_area_doc": 5.0,
            "noc_valid_to": "2026-06-01",
            "academic_year": "2024-2025",
            "faculty_count": 25,
            "faculty_count_doc": 25,
            "creation_date": "D:20250310100000+05'30'",
            "mod_date": "D:20241201100000+05'30'", # Precedes creation date by ~100 days
            "defects": ["METADATA_ANOMALY"]
        },
        # Case 13: Hard Defect - META-002 (CreationDate Postdates Application by 41 days)
        {
            "id": "held_out_13",
            "name": "Hard Defect: META-002 Retroactive Post-Filing Creation",
            "institution_name": "Apex Polytechnic College",
            "institution_name_alt": "Apex Polytechnic College",
            "application_id": "APP-HO-13",
            "permanent_id": "1-13141516",
            "application_date": "2025-03-15",
            "principal": "Dr. Shalini Gupta",
            "address": "Civil Lines, Kanpur, UP",
            "land_area": 4.5,
            "land_area_doc": 4.5,
            "noc_valid_to": "2026-03-15",
            "academic_year": "2024-2025",
            "faculty_count": 24,
            "faculty_count_doc": 24,
            "creation_date": "D:20250425120000+05'30'", # 41 days after filing date 2025-03-15!
            "mod_date": "D:20250425120500+05'30'",
            "defects": ["METADATA_ANOMALY"]
        },
        # Case 14: Hard Defect - META-003 (Non-standard ASN.1 Date Syntax / Missing Timezone)
        {
            "id": "held_out_14",
            "name": "Hard Defect: META-003 Syntax Warning (Omitted Timezone)",
            "institution_name": "Summit Institute of Engineering",
            "institution_name_alt": "Summit Institute of Engineering",
            "application_id": "APP-HO-14",
            "permanent_id": "1-14151617",
            "application_date": "2025-03-15",
            "principal": "Dr. Tarun Sen",
            "address": "Grand Trunk Road, Asansol, West Bengal",
            "land_area": 5.1,
            "land_area_doc": 5.1,
            "noc_valid_to": "2026-04-30",
            "academic_year": "2024-2025",
            "faculty_count": 26,
            "faculty_count_doc": 26,
            "creation_date": "D:20250101120000", # Missing timezone offset
            "mod_date": "D:20250101120500",
            "defects": ["METADATA_ANOMALY"]
        },
        # Case 15: Hard Defect - External Registry Source Unavailable
        {
            "id": "held_out_15",
            "name": "Hard Defect: External Registry Source Unavailable",
            "institution_name": "Crest College of Advanced Studies",
            "institution_name_alt": "Crest College of Advanced Studies",
            "application_id": "APP-HO-15",
            "permanent_id": "1-9999999999", # Unregistered PID
            "application_date": "2025-03-15",
            "principal": "Dr. Rohit Mathur",
            "address": "Sector 62, Noida, UP",
            "land_area": 5.0,
            "land_area_doc": 5.0,
            "noc_valid_to": "2026-05-15",
            "academic_year": "2024-2025",
            "faculty_count": 25,
            "faculty_count_doc": 25,
            "defects": ["UNAVAILABLE_SOURCE"]
        }
    ]

    for c in cases_def:
        case_id = c["id"]
        case_dir = os.path.join(HELD_OUT_DIR, case_id)
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
            "khasra_no": "142/5B",
            "land_doc_area_acres": c["land_area_doc"],
            "deed_date": "2018-05-12",
            "deed_number": f"DEED-{case_id.upper()}-8821",
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
                "fire_issue_date": "2024-04-10",
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
                pre_filing_dt = app_dt - timedelta(days=5, hours=3)
                norm_ts = f"D:{pre_filing_dt.strftime('%Y%m%d%H%M%S')}+05'30'"
                meta_dict = {
                    "producer": "VERITAS AICTE Approval System v2025.1",
                    "creator": "Institutional Regulatory Filing Suite",
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

    print("Successfully created 15 held-out evaluation cases.")

if __name__ == "__main__":
    build_held_out_cases()
