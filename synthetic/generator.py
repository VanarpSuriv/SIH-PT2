"""
Synthetic PDF and Ground Truth Generator for AICTE EoA Verification.
Generates 25 test cases across 5 document types with planted defects.
"""
import os
import json
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any
import pymupdf
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

CASES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cases")

def create_application_form_pdf(filepath: str, data: Dict[str, Any]) -> None:
    """Generate AICTE EoA Application Form PDF."""
    doc = SimpleDocTemplate(filepath, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#0f2b48'),
        alignment=1, # Center
        spaceAfter=10
    )
    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#1b4965'),
        spaceBefore=10,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#222222')
    )
    bold_style = ParagraphStyle(
        'BoldBody',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#111111')
    )

    story = [
        Paragraph("ALL INDIA COUNCIL FOR TECHNICAL EDUCATION", title_style),
        Paragraph("APPLICATION FOR EXTENSION OF APPROVAL (EoA) 2025-2026", ParagraphStyle('Sub', parent=title_style, fontSize=11, leading=14, textColor=colors.HexColor('#333333'))),
        HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0f2b48'), spaceAfter=15),
        Paragraph("1. INSTITUTION IDENTIFICATION", section_style)
    ]

    ident_data = [
        [Paragraph("Application ID:", bold_style), Paragraph(data["application_id"], body_style),
         Paragraph("Permanent Institute ID:", bold_style), Paragraph(data["permanent_id"], body_style)],
        [Paragraph("Institution Name:", bold_style), Paragraph(data["institution_name"], body_style),
         Paragraph("Application Date:", bold_style), Paragraph(data["application_date"], body_style)],
        [Paragraph("Principal / Director:", bold_style), Paragraph(data["principal_name"], body_style),
         Paragraph("Academic Year:", bold_style), Paragraph("2025-2026", body_style)],
        [Paragraph("Campus Address:", bold_style), Paragraph(data.get("address", "Sector 4, Tech Park, Metro City"), body_style),
         Paragraph("Affiliating University:", bold_style), Paragraph("State Technological University", body_style)]
    ]
    t1 = Table(ident_data, colWidths=[130, 140, 130, 140])
    t1.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8f9fa')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e9ecef')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t1)
    story.append(Spacer(1, 10))

    story.append(Paragraph("2. LAND & INFRASTRUCTURE SUMMARY", section_style))
    land_data = [
        [Paragraph("Total Land Area (Acres):", bold_style), Paragraph(str(data["declared_land_area"]), body_style),
         Paragraph("Land Ownership Type:", bold_style), Paragraph("Ownership / Freehold", body_style)],
        [Paragraph("Total Built-up Area (Sq.m):", bold_style), Paragraph("14250", body_style),
         Paragraph("Number of Instructional Blocks:", bold_style), Paragraph("4", body_style)]
    ]
    t2 = Table(land_data, colWidths=[150, 120, 150, 120])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8f9fa')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e9ecef')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t2)
    story.append(Spacer(1, 10))

    story.append(Paragraph("3. FACULTY & ACADEMIC DECLARATION", section_style))
    fac_data = [
        [Paragraph("Total Declared Faculty Count:", bold_style), Paragraph(str(data["declared_faculty_count"]), body_style),
         Paragraph("Faculty-to-Student Ratio:", bold_style), Paragraph("1:15", body_style)],
        [Paragraph("Approved Programs:", bold_style), Paragraph("UG Engineering & Technology", body_style),
         Paragraph("Total Student Intake:", bold_style), Paragraph("420", body_style)]
    ]
    t3 = Table(fac_data, colWidths=[160, 110, 150, 120])
    t3.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8f9fa')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e9ecef')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t3)
    story.append(Spacer(1, 20))

    story.append(Paragraph("Declaration: I hereby declare that all information furnished above is authentic and true to the best of my knowledge.", ParagraphStyle('Dec', parent=body_style, fontStyle='italic')))
    story.append(Spacer(1, 15))
    story.append(Paragraph(f"Authorized Signatory: Dr. {data['principal_name']}", bold_style))
    story.append(Paragraph("Designation: Principal / Head of Institution", body_style))

    doc.build(story)

def create_approval_letter_pdf(filepath: str, data: Dict[str, Any]) -> None:
    """Generate previous year AICTE EoA approval letter."""
    doc = SimpleDocTemplate(filepath, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'LetterHeader',
        parent=styles['Heading1'],
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#1a1a2e'),
        alignment=1,
        spaceAfter=6
    )
    body_style = ParagraphStyle('LBody', parent=styles['Normal'], fontSize=9, leading=13)
    bold_style = ParagraphStyle('LBold', parent=styles['Normal'], fontSize=9, leading=13, fontName='Helvetica-Bold')

    story = [
        Paragraph("ALL INDIA COUNCIL FOR TECHNICAL EDUCATION", title_style),
        Paragraph("(A Statutory Body of the Government of India)", ParagraphStyle('Sub', parent=title_style, fontSize=9, leading=11, fontName='Helvetica-Oblique')),
        Paragraph("Nelson Mandela Marg, Vasant Kunj, New Delhi-110070", ParagraphStyle('Sub2', parent=title_style, fontSize=8, leading=10)),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor('#1a1a2e'), spaceAfter=15),
        Paragraph(f"<b>Letter Order No:</b> {data.get('order_no', 'F.No. Western/1-931829101/2024/EOA')}", bold_style),
        Paragraph(f"<b>Date of Issuance:</b> {data.get('approval_issue_date', '2024-05-15')}", body_style),
        Spacer(1, 10),
        Paragraph("To,", body_style),
        Paragraph("The Principal Secretary / Registrar,", body_style),
        Paragraph(f"{data['approval_letter_institute_name']},", bold_style),
        Spacer(1, 10),
        Paragraph(f"<b>Sub: Extension of Approval (EoA) for Academic Year {data['approved_academic_year']}</b>", ParagraphStyle('Subject', parent=bold_style, fontSize=10, textColor=colors.HexColor('#003366'))),
        Spacer(1, 10),
        Paragraph("Sir / Madam,", body_style),
        Paragraph(f"In terms of the provisions under the All India Council for Technical Education (Grant of Approvals for Technical Institutions) Regulations, the Council hereby conveys the extension of approval to:", body_style),
        Spacer(1, 8)
    ]

    table_data = [
        [Paragraph("Permanent Institute ID:", bold_style), Paragraph(data["approval_letter_permanent_id"], body_style)],
        [Paragraph("Application ID:", bold_style), Paragraph(data.get("approval_letter_app_id", "APP-PRIOR-2024"), body_style)],
        [Paragraph("Name of the Institution:", bold_style), Paragraph(data["approval_letter_institute_name"], body_style)],
        [Paragraph("Approved Academic Year:", bold_style), Paragraph(data["approved_academic_year"], bold_style)],
        [Paragraph("Institution Address:", bold_style), Paragraph(data.get("address", "Sector 4, Tech Park, Metro City"), body_style)],
        [Paragraph("Approved Programs:", bold_style), Paragraph("B.Tech Computer Science, B.Tech Electronics & Comm", body_style)],
        [Paragraph("Status of Council Approval:", bold_style), Paragraph("APPROVED", bold_style)]
    ]
    t = Table(table_data, colWidths=[180, 360])
    t.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#999999')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#dddddd')),
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f1f3f5')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t)
    story.append(Spacer(1, 20))
    story.append(Paragraph("Member Secretary, AICTE", bold_style))
    story.append(Paragraph("All India Council for Technical Education", body_style))

    doc.build(story)

def create_land_document_pdf(filepath: str, data: Dict[str, Any]) -> None:
    """Generate Registered Title Deed / Land Certificate PDF."""
    doc = SimpleDocTemplate(filepath, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('LandHeader', parent=styles['Heading1'], fontSize=13, alignment=1, textColor=colors.HexColor('#332211'))
    body_style = ParagraphStyle('LdBody', parent=styles['Normal'], fontSize=9, leading=13)
    bold_style = ParagraphStyle('LdBold', parent=styles['Normal'], fontSize=9, leading=13, fontName='Helvetica-Bold')

    story = [
        Paragraph("GOVERNMENT OF STATE REVENUE DEPARTMENT", title_style),
        Paragraph("OFFICE OF THE SUB-REGISTRAR - TITLE DEED CERTIFICATE", ParagraphStyle('Sub', parent=title_style, fontSize=10, fontName='Helvetica-Bold')),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor('#664422'), spaceAfter=15),
        Paragraph(f"<b>Registration Deed Number:</b> {data.get('deed_number', 'DEED-2021-REG-8472')}", bold_style),
        Paragraph(f"<b>Date of Registration:</b> {data.get('deed_date', '2021-03-12')}", body_style),
        Spacer(1, 10),
        Paragraph("THIS CERTIFICATE OF TITLE WITNESSETH that the landed property specified hereunder is legally registered in the name of the grantee institution for educational purposes in perpetuity.", body_style),
        Spacer(1, 10)
    ]

    t_data = [
        [Paragraph("Institution / Owner Name:", bold_style), Paragraph(data["land_doc_institute_name"], body_style)],
        [Paragraph("Total Registered Area (Acres):", bold_style), Paragraph(str(data["land_doc_area_acres"]), bold_style)],
        [Paragraph("Survey / Khasra Plot No.:", bold_style), Paragraph(data.get("khasra_no", "Khasra No. 104/2B & 105"), body_style)],
        [Paragraph("Land Use Category:", bold_style), Paragraph("Educational Institutional Campus", body_style)],
        [Paragraph("Encumbrance Status:", bold_style), Paragraph("Free from all encumbrances / Clear Title", body_style)],
        [Paragraph("District & Sub-Division:", bold_style), Paragraph("Metro District, Central Division", body_style)]
    ]
    t = Table(t_data, colWidths=[180, 360])
    t.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#aa8866')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#eeddcc')),
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#fdfaf6')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t)
    story.append(Spacer(1, 20))
    story.append(Paragraph("Sub-Registrar & Competent Land Authority", bold_style))
    story.append(Paragraph("Seal of the Registration Authority", body_style))

    doc.build(story)

def create_fire_noc_pdf(filepath: str, data: Dict[str, Any]) -> None:
    """Generate Fire & Emergency Safety NOC Certificate PDF."""
    doc = SimpleDocTemplate(filepath, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('FireHeader', parent=styles['Heading1'], fontSize=13, alignment=1, textColor=colors.HexColor('#881111'))
    body_style = ParagraphStyle('FBody', parent=styles['Normal'], fontSize=9, leading=13)
    bold_style = ParagraphStyle('FBold', parent=styles['Normal'], fontSize=9, leading=13, fontName='Helvetica-Bold')

    story = [
        Paragraph("DIRECTORATE OF FIRE & EMERGENCY SERVICES", title_style),
        Paragraph("FIRE SAFETY CLEARANCE CERTIFICATE (NOC)", ParagraphStyle('Sub', parent=title_style, fontSize=10, fontName='Helvetica-Bold')),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor('#aa2222'), spaceAfter=15),
        Paragraph(f"<b>Certificate NOC No:</b> {data.get('noc_number', 'NOC-FIRE-2024-9912')}", bold_style),
        Paragraph(f"<b>Date of Inspection / Issue:</b> {data.get('fire_issue_date', '2024-04-10')}", body_style),
        Spacer(1, 10),
        Paragraph("Certified that the educational institutional premises detailed below was inspected by the Fire Safety Officer and found to comply with all mandatory Fire Prevention and Safety measures as per National Building Code (NBC) Part IV.", body_style),
        Spacer(1, 10)
    ]

    t_data = [
        [Paragraph("Name of the Institution:", bold_style), Paragraph(data["fire_noc_institute_name"], body_style)],
        [Paragraph("Campus Location / Address:", bold_style), Paragraph(data.get("address", "Sector 4, Tech Park, Metro City"), body_style)],
        [Paragraph("NOC Issue Date:", bold_style), Paragraph(data.get("fire_issue_date", "2024-04-10"), body_style)],
        [Paragraph("Valid Until / Valid To:", bold_style), Paragraph(data["fire_noc_valid_to"], bold_style)],
        [Paragraph("Inspection Result:", bold_style), Paragraph("COMPLIANT / SATISFACTORY", bold_style)],
        [Paragraph("NOC Issuing Authority:", bold_style), Paragraph("Divisional Fire Officer, City Fire Dept", body_style)]
    ]
    t = Table(t_data, colWidths=[180, 360])
    t.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cc7777')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#f5dada')),
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#fff7f7')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t)
    story.append(Spacer(1, 20))
    story.append(Paragraph("Divisional Fire Officer", bold_style))
    story.append(Paragraph("Fire & Emergency Services Headquarters", body_style))

    doc.build(story)

def create_faculty_list_pdf(filepath: str, data: Dict[str, Any]) -> None:
    """Generate Faculty Roster and Cadre Ratio PDF."""
    doc = SimpleDocTemplate(filepath, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('FacHeader', parent=styles['Heading1'], fontSize=12, alignment=1, textColor=colors.HexColor('#114422'))
    body_style = ParagraphStyle('FcBody', parent=styles['Normal'], fontSize=8, leading=10)
    bold_style = ParagraphStyle('FcBold', parent=styles['Normal'], fontSize=8, leading=10, fontName='Helvetica-Bold')

    story = [
        Paragraph("AICTE APPROVED FACULTY ROSTER & CADRE DETAILS", title_style),
        Paragraph(f"Institution: {data['faculty_institute_name']} | Application ID: {data['application_id']}", ParagraphStyle('Sub', parent=title_style, fontSize=9, fontName='Helvetica')),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor('#114422'), spaceAfter=10),
        Paragraph(f"<b>Total Count of Approved Faculty Members: {data['faculty_list_count']}</b>", bold_style),
        Spacer(1, 8)
    ]

    headers = [
        Paragraph("S.No", bold_style),
        Paragraph("Faculty Name", bold_style),
        Paragraph("Designation", bold_style),
        Paragraph("Department", bold_style),
        Paragraph("Qualification", bold_style),
        Paragraph("AICTE Faculty ID", bold_style)
    ]
    rows = [headers]

    designations = ["Professor", "Associate Professor", "Assistant Professor"]
    depts = ["Computer Science", "Information Tech", "Electronics & Comm", "Mechanical Eng"]
    names = [
        "Dr. Rajesh Kumar Sharma", "Dr. Anita Desai", "Prof. Vikram Malhotra", "Dr. Sunita Rao",
        "Prof. Amit Patil", "Dr. Neha Verma", "Prof. Manoj Nair", "Dr. Priya Sundaram",
        "Prof. Arun Joshi", "Dr. Kavita Singh", "Prof. Deepak Gupta", "Dr. Shalini Mehta",
        "Prof. Rahul Iyer", "Dr. Pooja Reddy", "Prof. Sanjay Mishra", "Dr. Ananya Sen",
        "Prof. Harish Pillai", "Dr. Meenakshi Swaminathan", "Prof. Rakesh Tiwari", "Dr. Vandana Bose",
        "Prof. Alok Nath", "Dr. Ritu Choudhury", "Prof. Tarun Bhatt", "Dr. Divya Aggarwal",
        "Prof. Suresh Menon", "Dr. Pallavi Kulkarni", "Prof. Vivek Pandey", "Dr. Geeta Pillai",
        "Prof. Sandeep Bansal", "Dr. Rekha Nambiar", "Prof. Gaurav Saxena", "Dr. Swati Ghosh",
        "Prof. Akhil Saxena", "Dr. Preeti Jain", "Prof. Nitin Kapoor"
    ]

    principal_row = [
        Paragraph("1", body_style),
        Paragraph(f"Dr. {data['principal_name']}", bold_style),
        Paragraph("Principal / Director", bold_style),
        Paragraph("Admin & Computer Sci", body_style),
        Paragraph("Ph.D., M.Tech", body_style),
        Paragraph(f"1-{random.randint(10000000, 99999999)}", body_style)
    ]
    rows.append(principal_row)

    count = data['faculty_list_count']
    for i in range(2, count + 1):
        idx = (i - 2) % len(names)
        d_idx = (i - 2) % len(designations)
        dept_idx = (i - 2) % len(depts)
        row = [
            Paragraph(str(i), body_style),
            Paragraph(names[idx], body_style),
            Paragraph(designations[d_idx], body_style),
            Paragraph(depts[dept_idx], body_style),
            Paragraph("Ph.D." if d_idx == 0 else "M.Tech", body_style),
            Paragraph(f"1-{random.randint(10000000, 99999999)}", body_style)
        ]
        rows.append(row)

    t = Table(rows, colWidths=[35, 130, 110, 110, 75, 80])
    t.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#226633')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#d0e6d5')),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#d8eedf')),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t)
    story.append(Spacer(1, 15))
    story.append(Paragraph(f"Verified & Submitted by Head of Institution: Dr. {data['principal_name']}", bold_style))

    doc.build(story)

def generate_cases() -> None:
    """Generate 25 synthetic cases with truth.json and PDFs."""
    os.makedirs(CASES_DIR, exist_ok=True)
    random.seed(42)

    base_cases = [
        # Clean cases (1 to 5)
        {"id": "case_01", "name": "Apex Institute of Technology", "defects": []},
        {"id": "case_02", "name": "Silver Oak Engineering College", "defects": []},
        {"id": "case_03", "name": "Vanguard Institute of Science and Technology", "defects": []},
        {"id": "case_04", "name": "Horizon Academy of Engineering", "defects": []},
        {"id": "case_05", "name": "Pinnacle Institute of Technology", "defects": []},

        # Missing Document cases (6 to 8)
        {"id": "case_06", "name": "Beacon Institute of Technology", "defects": ["MISSING_FIRE_NOC"], "missing_doc": "fire_noc"},
        {"id": "case_07", "name": "Crestline Engineering Institute", "defects": ["MISSING_FACULTY_LIST"], "missing_doc": "faculty_list"},
        {"id": "case_08", "name": "Evergreen College of Engineering", "defects": ["MISSING_LAND_DOCUMENT"], "missing_doc": "land_document"},

        # Expired Certificate cases (9 to 11)
        {"id": "case_09", "name": "Zenith Institute of Technology", "defects": ["EXPIRED_FIRE_NOC"], "fire_valid_to": "2023-11-30"},
        {"id": "case_10", "name": "Imperial College of Engineering", "defects": ["EXPIRED_FIRE_NOC"], "fire_valid_to": "2024-02-15"},
        {"id": "case_11", "name": "Summit Institute of Engineering", "defects": ["EXPIRED_APPROVAL_LETTER"], "approved_academic_year": "2019-2020"},

        # Name Mismatch cases (12 to 14)
        {"id": "case_12", "name": "Metropolitan Institute of Technology", "defects": ["NAME_MISMATCH_LAND"], "land_doc_name": "Metropolitan Polytechnic & Vocational Centre"},
        {"id": "case_13", "name": "Global Academy of Technology", "defects": ["NAME_MISMATCH_FIRE"], "fire_noc_name": "Global Educational & Charitable Trust"},
        {"id": "case_14", "name": "Starlight Institute of Engineering", "defects": ["NAME_MISMATCH_APPROVAL"], "approval_letter_name": "Starling Technical Institute"},

        # Date Conflict cases (15 to 17)
        {"id": "case_15", "name": "Trident Institute of Technology", "defects": ["DATE_CONFLICT_APPLICATION"], "app_date": "2026-08-10", "fire_valid_to": "2025-03-31"},
        {"id": "case_16", "name": "Quantum College of Engineering", "defects": ["OUTDATED_APPROVAL_ORDER"], "approved_academic_year": "2021-2022"},
        {"id": "case_17", "name": "Omega Institute of Science & Tech", "defects": ["EXPIRED_FIRE_NOC", "DATE_CONFLICT_APPLICATION"], "fire_valid_to": "2023-01-01", "app_date": "2026-11-20"},

        # Area Mismatch cases (18 to 20)
        {"id": "case_18", "name": "Bluecrest Institute of Technology", "defects": ["LAND_AREA_MISMATCH"], "declared_area": 5.5, "land_doc_area": 2.1},
        {"id": "case_19", "name": "Sterling College of Engineering", "defects": ["LAND_AREA_DEFICIT"], "declared_area": 4.0, "land_doc_area": 1.5}, # AICTE min is 2.5
        {"id": "case_20", "name": "Unity Institute of Technology", "defects": ["LAND_AREA_MISMATCH"], "declared_area": 6.2, "land_doc_area": 3.4},

        # Faculty Mismatch cases (21 to 22)
        {"id": "case_21", "name": "Paramount College of Engineering", "defects": ["FACULTY_COUNT_MISMATCH"], "declared_fac": 30, "roster_fac": 18},
        {"id": "case_22", "name": "Nexus Institute of Technology", "defects": ["FACULTY_COUNT_MISMATCH"], "declared_fac": 25, "roster_fac": 14},

        # Unavailable / Mismatched External Source cases (23 to 25)
        {"id": "case_23", "name": "Solaris Engineering College", "defects": ["SOURCE_UNAVAILABLE"], "issuer_source_fail": True},
        {"id": "case_24", "name": "Matrix Institute of Technology", "defects": ["ISSUER_RECORD_MISMATCH"], "issuer_status_mismatch": True},
        {"id": "case_25", "name": "Orion College of Technology", "defects": ["EXPIRED_FIRE_NOC", "LAND_AREA_MISMATCH"], "fire_valid_to": "2022-05-10", "declared_area": 5.0, "land_doc_area": 2.0}
    ]

    fake_issuers_records = {}

    for idx, c in enumerate(base_cases, 1):
        case_id = f"case_{idx:02d}"
        case_dir = os.path.join(CASES_DIR, case_id)
        os.makedirs(case_dir, exist_ok=True)

        inst_name = c["name"]
        app_id = f"APP-2025-{1000 + idx}"
        perm_id = f"PID-1-{7000000 + idx}"
        principal = f"Anand Sharma {idx}"
        app_date = c.get("app_date", "2025-03-15")
        declared_land = c.get("declared_area", 4.5)
        land_doc_area = c.get("land_doc_area", declared_land)
        declared_fac = c.get("declared_fac", 20)
        roster_fac = c.get("roster_fac", declared_fac)
        fire_valid = c.get("fire_valid_to", "2026-12-31")
        approved_year = c.get("approved_academic_year", "2024-2025")
        
        land_inst_name = c.get("land_doc_name", inst_name)
        fire_inst_name = c.get("fire_noc_name", inst_name)
        appr_inst_name = c.get("approval_letter_name", inst_name)
        missing_doc = c.get("missing_doc", None)

        data = {
            "application_id": app_id,
            "permanent_id": perm_id,
            "institution_name": inst_name,
            "application_date": app_date,
            "principal_name": principal,
            "declared_land_area": declared_land,
            "declared_faculty_count": declared_fac,
            "address": f"Plot {idx * 12}, Tech Institutional Zone, Knowledge City",
            "order_no": f"F.No. Western/1-{perm_id.split('-')[-1]}/2024/EOA",
            "approval_letter_permanent_id": perm_id,
            "approval_letter_institute_name": appr_inst_name,
            "approved_academic_year": approved_year,
            "approval_issue_date": "2024-05-20",
            "deed_number": f"DEED-2021-REG-{8000 + idx}",
            "land_doc_institute_name": land_inst_name,
            "land_doc_area_acres": land_doc_area,
            "noc_number": f"FNOC-2024-DIST-{5000 + idx}",
            "fire_noc_institute_name": fire_inst_name,
            "fire_issue_date": "2024-04-10",
            "fire_noc_valid_to": fire_valid,
            "faculty_institute_name": inst_name,
            "faculty_list_count": roster_fac
        }

        # Generate PDFs (unless missing)
        generated_files = []
        if missing_doc != "application_form":
            fpath = os.path.join(case_dir, "application_form.pdf")
            create_application_form_pdf(fpath, data)
            generated_files.append("application_form.pdf")

        if missing_doc != "approval_letter":
            fpath = os.path.join(case_dir, "approval_letter.pdf")
            create_approval_letter_pdf(fpath, data)
            generated_files.append("approval_letter.pdf")

        if missing_doc != "land_document":
            fpath = os.path.join(case_dir, "land_document.pdf")
            create_land_document_pdf(fpath, data)
            generated_files.append("land_document.pdf")

        if missing_doc != "fire_noc":
            fpath = os.path.join(case_dir, "fire_noc.pdf")
            create_fire_noc_pdf(fpath, data)
            generated_files.append("fire_noc.pdf")

        if missing_doc != "faculty_list":
            fpath = os.path.join(case_dir, "faculty_list.pdf")
            create_faculty_list_pdf(fpath, data)
            generated_files.append("faculty_list.pdf")

        # Set consistent pre-filing metadata on generated files matching application timeline
        try:
            app_dt = datetime.strptime(app_date, "%Y-%m-%d")
        except Exception:
            app_dt = datetime(2025, 3, 15)
        pre_filing_dt = app_dt - timedelta(days=5, hours=2)
        norm_ts = f"D:{pre_filing_dt.strftime('%Y%m%d%H%M%S')}+05'30'"
        for gf in generated_files:
            gpath = os.path.join(case_dir, gf)
            try:
                pdoc = pymupdf.open(gpath)
                pdoc.set_metadata({
                    "producer": "VERITAS AICTE Platform v2025.1",
                    "creator": "Institutional Regulatory Filing Suite",
                    "creationDate": norm_ts,
                    "modDate": norm_ts
                })
                tmp_gpath = gpath + ".tmp.pdf"
                pdoc.save(tmp_gpath)
                pdoc.close()
                os.replace(tmp_gpath, gpath)
            except Exception:
                pass

        # Ground truth
        truth = {
            "case_id": case_id,
            "institution_name": inst_name,
            "application_id": app_id,
            "permanent_id": perm_id,
            "application_date": app_date,
            "expected_defects": c["defects"],
            "planted_defects": c["defects"],
            "clean": len(c["defects"]) == 0,
            "generated_files": generated_files,
            "fields": {
                "application_id": app_id,
                "permanent_id": perm_id,
                "institution_name": inst_name,
                "declared_land_area": declared_land,
                "declared_faculty_count": declared_fac,
                "fire_noc_valid_to": fire_valid,
                "approved_academic_year": approved_year,
                "land_doc_area_acres": land_doc_area,
                "faculty_list_count": roster_fac
            }
        }

        with open(os.path.join(case_dir, "truth.json"), "w", encoding="utf-8") as tf:
            json.dump(truth, tf, indent=2)

        # Issuer mock record
        fake_issuers_records[perm_id] = {
            "issuer": "AICTE_CENTRAL_PORTAL",
            "record_id": perm_id,
            "institution_name": inst_name if not c.get("issuer_status_mismatch") else f"Disputed {inst_name}",
            "status": "SOURCE_UNAVAILABLE" if c.get("issuer_source_fail") else ("MISMATCH" if c.get("issuer_status_mismatch") else "VERIFIED"),
            "approved_academic_year": approved_year,
            "current_eoa_status": "VALID" if "EXPIRED_APPROVAL_LETTER" not in c["defects"] else "EXPIRED"
        }

        # Fire dept issuer record
        fake_issuers_records[data["noc_number"]] = {
            "issuer": "STATE_FIRE_SERVICES_PORTAL",
            "record_id": data["noc_number"],
            "institution_name": fire_inst_name,
            "status": "EXPIRED" if "EXPIRED_FIRE_NOC" in c["defects"] else "VERIFIED",
            "valid_to": fire_valid
        }

    # Save fake issuers database to backend/verify/fake_issuers.json
    backend_verify_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend", "verify")
    os.makedirs(backend_verify_dir, exist_ok=True)
    with open(os.path.join(backend_verify_dir, "fake_issuers.json"), "w", encoding="utf-8") as f:
        json.dump(fake_issuers_records, f, indent=2)

    print(f"Successfully generated 25 synthetic cases with truth.json in {CASES_DIR}")

if __name__ == "__main__":
    generate_cases()
