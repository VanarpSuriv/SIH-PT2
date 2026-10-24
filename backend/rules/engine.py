"""
AICTE EoA Rules Engine.
Evaluates completeness, expiry, fuzzy cross-document consistency, and metadata integrity rules from YAML.
Explicitly distinguishes statutory mandates from technical consistency checks and metadata review flags.
"""
import os
import uuid
import yaml
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
from rapidfuzz import fuzz

from backend.models import (
    DocumentType,
    DocumentRecord,
    ExtractedField,
    Finding,
    FindingStatus,
    FindingLifecycle,
    HumanReviewDecision,
    MetadataEvidenceContext,
    RuleCategory,
    Severity
)

RULES_YAML_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aicte_eoa_rules.yaml")

class RulesEngine:
    """Evaluates extracted fields and metadata against AICTE EoA compliance rules."""

    def __init__(self, rules_path: str = RULES_YAML_PATH):
        self.rules_path = rules_path
        self.rules_def = self._load_rules()

    def _load_rules(self) -> Dict[str, Any]:
        with open(self.rules_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def evaluate(
        self,
        application_id: str,
        documents: List[DocumentRecord],
        fields: List[ExtractedField]
    ) -> List[Finding]:
        """
        Evaluate all rules against the uploaded documents, extracted fields, and PDF metadata.
        Returns a list of Findings with exact field references, separated lifecycles, and metadata context.
        """
        findings: List[Finding] = []
        doc_type_map = {doc.document_type: doc for doc in documents}
        
        # Organize fields by document_type and field_name
        field_map: Dict[Tuple[DocumentType, str], ExtractedField] = {}
        for fld in fields:
            field_map[(fld.document_type, fld.name)] = fld

        # App form fields
        app_date_fld = field_map.get((DocumentType.APPLICATION_FORM, "application_date"))
        app_date_val = str(app_date_fld.value) if app_date_fld else "2025-03-15"
        app_inst_name_fld = field_map.get((DocumentType.APPLICATION_FORM, "institution_name"))
        app_pid_fld = field_map.get((DocumentType.APPLICATION_FORM, "permanent_id"))
        app_land_fld = field_map.get((DocumentType.APPLICATION_FORM, "declared_land_area"))
        app_fac_fld = field_map.get((DocumentType.APPLICATION_FORM, "declared_faculty_count"))

        for rule in self.rules_def.get("rules", []):
            rule_id = rule["id"]
            rule_version = rule.get("version", "2025.1")
            rule_title = rule["title"]
            severity = Severity(rule["severity"])
            rule_type = rule["rule_type"]
            category_str = rule.get("rule_category", "STATUTORY_MANDATE")
            rule_category = RuleCategory(category_str)
            aph_ref = rule.get("aph_reference")
            description = rule["description"]

            # -------------------------------------------------------------
            # 1. COMPLETENESS RULES (Statutory Document Presence)
            # -------------------------------------------------------------
            if rule_type == "completeness":
                req_doc_str = rule["required_document"]
                req_doc_type = DocumentType(req_doc_str)
                is_present = req_doc_type in doc_type_map
                
                if not is_present:
                    findings.append(Finding(
                        id=f"find_{uuid.uuid4().hex[:10]}",
                        application_id=application_id,
                        rule_id=rule_id,
                        rule_version=rule_version,
                        rule_name=rule_title,
                        rule_category=rule_category,
                        aph_reference=aph_ref,
                        severity=severity,
                        status=FindingStatus.FAIL,
                        lifecycle=FindingLifecycle.OPEN,
                        claim=f"Required document '{req_doc_str.replace('_', ' ').title()}' is MISSING from the application package.",
                        description=description,
                        fields_involved=[]
                    ))
                else:
                    doc_fields = [f for f in fields if f.document_type == req_doc_type]
                    findings.append(Finding(
                        id=f"find_{uuid.uuid4().hex[:10]}",
                        application_id=application_id,
                        rule_id=rule_id,
                        rule_version=rule_version,
                        rule_name=rule_title,
                        rule_category=rule_category,
                        aph_reference=aph_ref,
                        severity=Severity.INFO,
                        status=FindingStatus.PASS,
                        lifecycle=FindingLifecycle.RESOLVED,
                        claim=f"Required document '{req_doc_str.replace('_', ' ').title()}' is present and verified.",
                        description=description,
                        fields_involved=doc_fields[:2]
                    ))

            # -------------------------------------------------------------
            # 2. EXPIRY RULES (Certificate Validity Boundaries)
            # -------------------------------------------------------------
            elif rule_type == "expiry":
                if rule_id == "AICTE-EOA-005": # Fire NOC Expiry
                    fire_valid_fld = field_map.get((DocumentType.FIRE_NOC, "fire_noc_valid_to"))
                    if fire_valid_fld:
                        valid_to_str = str(fire_valid_fld.value)
                        is_expired = False
                        try:
                            valid_dt = datetime.strptime(valid_to_str, "%Y-%m-%d")
                            ref_dt = datetime.strptime(app_date_val, "%Y-%m-%d")
                            if valid_dt < ref_dt:
                                is_expired = True
                        except Exception:
                            is_expired = False

                        inv_fields = [fire_valid_fld]
                        if app_date_fld:
                            inv_fields.append(app_date_fld)

                        if is_expired:
                            findings.append(Finding(
                                id=f"find_{uuid.uuid4().hex[:10]}",
                                application_id=application_id,
                                rule_id=rule_id,
                                rule_version=rule_version,
                                rule_name=rule_title,
                                rule_category=rule_category,
                                aph_reference=aph_ref,
                                severity=severity,
                                status=FindingStatus.FAIL,
                                lifecycle=FindingLifecycle.OPEN,
                                claim=f"Fire Safety NOC expired on {valid_to_str}, which is prior to application submission date ({app_date_val}).",
                                description=description,
                                fields_involved=inv_fields
                            ))
                        else:
                            findings.append(Finding(
                                id=f"find_{uuid.uuid4().hex[:10]}",
                                application_id=application_id,
                                rule_id=rule_id,
                                rule_version=rule_version,
                                rule_name=rule_title,
                                rule_category=rule_category,
                                aph_reference=aph_ref,
                                severity=Severity.INFO,
                                status=FindingStatus.PASS,
                                lifecycle=FindingLifecycle.RESOLVED,
                                claim=f"Fire Safety NOC is valid through {valid_to_str}.",
                                description=description,
                                fields_involved=inv_fields
                            ))

                elif rule_id == "AICTE-EOA-006": # Continuity of Prior Approval
                    appr_year_fld = field_map.get((DocumentType.APPROVAL_LETTER, "approved_academic_year"))
                    if appr_year_fld:
                        year_val = str(appr_year_fld.value)
                        expected_year = rule.get("expected_year_pattern", "2024-2025")
                        if year_val != expected_year:
                            findings.append(Finding(
                                id=f"find_{uuid.uuid4().hex[:10]}",
                                application_id=application_id,
                                rule_id=rule_id,
                                rule_version=rule_version,
                                rule_name=rule_title,
                                rule_category=rule_category,
                                aph_reference=aph_ref,
                                severity=severity,
                                status=FindingStatus.FAIL,
                                lifecycle=FindingLifecycle.OPEN,
                                claim=f"Previous approval letter corresponds to academic year {year_val}, failing continuous approval continuity (expected {expected_year}).",
                                description=description,
                                fields_involved=[appr_year_fld]
                            ))
                        else:
                            findings.append(Finding(
                                id=f"find_{uuid.uuid4().hex[:10]}",
                                application_id=application_id,
                                rule_id=rule_id,
                                rule_version=rule_version,
                                rule_name=rule_title,
                                rule_category=rule_category,
                                aph_reference=aph_ref,
                                severity=Severity.INFO,
                                status=FindingStatus.PASS,
                                lifecycle=FindingLifecycle.RESOLVED,
                                claim=f"Previous approval letter correctly confirms academic year {year_val}.",
                                description=description,
                                fields_involved=[appr_year_fld]
                            ))

            # -------------------------------------------------------------
            # 3. CONSISTENCY RULES (Entity & Metric Cross-Reconciliation)
            # -------------------------------------------------------------
            elif rule_type == "consistency":
                if rule_id == "AICTE-EOA-007": # Institution Name Consistency
                    if app_inst_name_fld:
                        app_name = str(app_inst_name_fld.value)
                        threshold = float(rule.get("similarity_threshold", 85.0))
                        
                        targets = [
                            (DocumentType.LAND_DOCUMENT, "Land Title Deed"),
                            (DocumentType.FIRE_NOC, "Fire Safety NOC"),
                            (DocumentType.APPROVAL_LETTER, "Approval Letter")
                        ]
                        
                        mismatches = []
                        all_matching = True
                        checked_fields = [app_inst_name_fld]

                        for d_type, d_label in targets:
                            other_fld = field_map.get((d_type, "institution_name"))
                            if other_fld:
                                checked_fields.append(other_fld)
                                other_name = str(other_fld.value)
                                score = fuzz.token_sort_ratio(app_name, other_name)
                                if score < threshold:
                                    all_matching = False
                                    mismatches.append(f"{d_label} ('{other_name}' - {score:.1f}% match)")

                        if not all_matching:
                            findings.append(Finding(
                                id=f"find_{uuid.uuid4().hex[:10]}",
                                application_id=application_id,
                                rule_id=rule_id,
                                rule_version=rule_version,
                                rule_name=rule_title,
                                rule_category=rule_category,
                                aph_reference=aph_ref,
                                severity=severity,
                                status=FindingStatus.FAIL,
                                lifecycle=FindingLifecycle.OPEN,
                                claim=f"Institution name discrepancy: Application declares '{app_name}', which does not match {', '.join(mismatches)}.",
                                description=description,
                                fields_involved=checked_fields
                            ))
                        else:
                            findings.append(Finding(
                                id=f"find_{uuid.uuid4().hex[:10]}",
                                application_id=application_id,
                                rule_id=rule_id,
                                rule_version=rule_version,
                                rule_name=rule_title,
                                rule_category=rule_category,
                                aph_reference=aph_ref,
                                severity=Severity.INFO,
                                status=FindingStatus.PASS,
                                lifecycle=FindingLifecycle.RESOLVED,
                                claim=f"Institution name '{app_name}' is consistent across all uploaded documents.",
                                description=description,
                                fields_involved=checked_fields
                            ))

                elif rule_id == "AICTE-EOA-008": # PID Consistency
                    appr_pid_fld = field_map.get((DocumentType.APPROVAL_LETTER, "permanent_id"))
                    if app_pid_fld and appr_pid_fld:
                        p1 = str(app_pid_fld.value).strip()
                        p2 = str(appr_pid_fld.value).strip()
                        if p1 != p2:
                            findings.append(Finding(
                                id=f"find_{uuid.uuid4().hex[:10]}",
                                application_id=application_id,
                                rule_id=rule_id,
                                rule_version=rule_version,
                                rule_name=rule_title,
                                rule_category=rule_category,
                                aph_reference=aph_ref,
                                severity=severity,
                                status=FindingStatus.FAIL,
                                lifecycle=FindingLifecycle.OPEN,
                                claim=f"Permanent Institute ID conflict: Application has '{p1}', but prior approval letter has '{p2}'.",
                                description=description,
                                fields_involved=[app_pid_fld, appr_pid_fld]
                            ))
                        else:
                            findings.append(Finding(
                                id=f"find_{uuid.uuid4().hex[:10]}",
                                application_id=application_id,
                                rule_id=rule_id,
                                rule_version=rule_version,
                                rule_name=rule_title,
                                rule_category=rule_category,
                                aph_reference=aph_ref,
                                severity=Severity.INFO,
                                status=FindingStatus.PASS,
                                lifecycle=FindingLifecycle.RESOLVED,
                                claim=f"Permanent Institute ID '{p1}' strictly matches across records.",
                                description=description,
                                fields_involved=[app_pid_fld, appr_pid_fld]
                            ))

                elif rule_id == "AICTE-EOA-009": # Land Area Adequacy
                    land_doc_fld = field_map.get((DocumentType.LAND_DOCUMENT, "land_doc_area_acres"))
                    if app_land_fld and land_doc_fld:
                        try:
                            dec_val = float(app_land_fld.value)
                            reg_val = float(land_doc_fld.value)
                            min_req = float(rule.get("minimum_required_acres", 2.5))
                            
                            if reg_val < min_req:
                                findings.append(Finding(
                                    id=f"find_{uuid.uuid4().hex[:10]}",
                                    application_id=application_id,
                                    rule_id=rule_id,
                                    rule_version=rule_version,
                                    rule_name=rule_title,
                                    rule_category=rule_category,
                                    aph_reference=aph_ref,
                                    severity=severity,
                                    status=FindingStatus.FAIL,
                                    lifecycle=FindingLifecycle.OPEN,
                                    claim=f"Registered land area ({reg_val} acres) is below the statutory AICTE minimum of {min_req} acres.",
                                    description=description,
                                    fields_involved=[app_land_fld, land_doc_fld]
                                ))
                            elif dec_val > reg_val:
                                findings.append(Finding(
                                    id=f"find_{uuid.uuid4().hex[:10]}",
                                    application_id=application_id,
                                    rule_id=rule_id,
                                    rule_version=rule_version,
                                    rule_name=rule_title,
                                    rule_category=rule_category,
                                    aph_reference=aph_ref,
                                    severity=severity,
                                    status=FindingStatus.FAIL,
                                    lifecycle=FindingLifecycle.OPEN,
                                    claim=f"Land area inflation: Application claims {dec_val} acres, but registered title deed only proves {reg_val} acres.",
                                    description=description,
                                    fields_involved=[app_land_fld, land_doc_fld]
                                ))
                            else:
                                findings.append(Finding(
                                    id=f"find_{uuid.uuid4().hex[:10]}",
                                    application_id=application_id,
                                    rule_id=rule_id,
                                    rule_version=rule_version,
                                    rule_name=rule_title,
                                    rule_category=rule_category,
                                    aph_reference=aph_ref,
                                    severity=Severity.INFO,
                                    status=FindingStatus.PASS,
                                    lifecycle=FindingLifecycle.RESOLVED,
                                    claim=f"Registered land area ({reg_val} acres) satisfies statutory requirements and supports declared campus area ({dec_val} acres).",
                                    description=description,
                                    fields_involved=[app_land_fld, land_doc_fld]
                                ))
                        except ValueError:
                            pass

                elif rule_id == "AICTE-EOA-010": # Faculty Count Consistency
                    roster_count_fld = field_map.get((DocumentType.FACULTY_LIST, "faculty_list_count"))
                    if app_fac_fld and roster_count_fld:
                        try:
                            dec_fac = int(app_fac_fld.value)
                            ros_fac = int(roster_count_fld.value)
                            if dec_fac != ros_fac:
                                findings.append(Finding(
                                    id=f"find_{uuid.uuid4().hex[:10]}",
                                    application_id=application_id,
                                    rule_id=rule_id,
                                    rule_version=rule_version,
                                    rule_name=rule_title,
                                    rule_category=rule_category,
                                    aph_reference=aph_ref,
                                    severity=severity,
                                    status=FindingStatus.FAIL,
                                    lifecycle=FindingLifecycle.OPEN,
                                    claim=f"Faculty cadre mismatch: Application declares {dec_fac} faculty, but submitted roster enumerates {ros_fac} faculty.",
                                    description=description,
                                    fields_involved=[app_fac_fld, roster_count_fld]
                                ))
                            else:
                                findings.append(Finding(
                                    id=f"find_{uuid.uuid4().hex[:10]}",
                                    application_id=application_id,
                                    rule_id=rule_id,
                                    rule_version=rule_version,
                                    rule_name=rule_title,
                                    rule_category=rule_category,
                                    aph_reference=aph_ref,
                                    severity=Severity.INFO,
                                    status=FindingStatus.PASS,
                                    lifecycle=FindingLifecycle.RESOLVED,
                                    claim=f"Faculty roster enumeration ({ros_fac}) perfectly matches declared faculty count ({dec_fac}).",
                                    description=description,
                                    fields_involved=[app_fac_fld, roster_count_fld]
                                ))
                        except ValueError:
                            pass

            # -------------------------------------------------------------
            # 4. METADATA INTEGRITY RULES (Document Lifecycle & Timeline)
            # -------------------------------------------------------------
            elif rule_type == "metadata":
                if rule_id == "META-001": # ModDate Precedes CreationDate
                    for doc in documents:
                        meta = doc.metadata
                        norm_c = meta.normalized_creation_date
                        norm_m = meta.normalized_mod_date
                        if norm_c and norm_m:
                            try:
                                dt_c = datetime.fromisoformat(norm_c)
                                dt_m = datetime.fromisoformat(norm_m)
                                delta_sec = (dt_m - dt_c).total_seconds()
                                if delta_sec < -1.0: # ModDate earlier than CreationDate by > 1s
                                    hours_diff = abs(delta_sec) / 3600.0
                                    evidence_field = ExtractedField(
                                        name="pdf_metadata_timestamps",
                                        value=f"CreationDate: {norm_c} | ModDate: {norm_m}",
                                        raw_text=f"Creation: {meta.raw_creation_date}, Mod: {meta.raw_mod_date}",
                                        document_type=doc.document_type,
                                        document_id=doc.id,
                                        page_number=1,
                                        bbox=[36.0, 36.0, 520.0, 65.0],
                                        confidence=1.0
                                    )
                                    ctx = MetadataEvidenceContext(
                                        original_values={
                                            "raw_creation_date": meta.raw_creation_date,
                                            "raw_mod_date": meta.raw_mod_date,
                                            "creator": meta.creator,
                                            "producer": meta.producer,
                                            "pdf_version": meta.pdf_version,
                                            "sha256": meta.sha256_hash
                                        },
                                        normalized_values={
                                            "normalized_creation_date": norm_c,
                                            "normalized_mod_date": norm_m,
                                            "time_skew_hours": round(hours_diff, 2)
                                        },
                                        rule_triggered=rule_id,
                                        rule_title=rule_title,
                                        reason_for_review=(
                                            f"Document '{doc.filename}' indicates normalized ModDate ({norm_m}) earlier than CreationDate ({norm_c}) "
                                            f"by {hours_diff:.1f} hours. This technical timing anomaly may stem from PDF compiler clock skew, re-saving, "
                                            f"or header restructuring and is flagged for manual verification. It does not constitute proof of forgery."
                                        ),
                                        parsing_warnings=meta.parsing_warnings
                                    )
                                    findings.append(Finding(
                                        id=f"find_{uuid.uuid4().hex[:10]}",
                                        application_id=application_id,
                                        rule_id=rule_id,
                                        rule_version=rule_version,
                                        rule_name=rule_title,
                                        rule_category=rule_category,
                                        aph_reference=aph_ref,
                                        severity=severity,
                                        status=FindingStatus.FLAGGED,
                                        lifecycle=FindingLifecycle.OPEN,
                                        claim=f"Metadata temporal inconsistency in '{doc.filename}': ModDate precedes CreationDate by {hours_diff:.1f} hours.",
                                        description=description,
                                        fields_involved=[evidence_field],
                                        metadata_context=ctx
                                    ))
                            except Exception:
                                pass

                elif rule_id == "META-002": # CreationDate Postdates Application Date
                    for doc in documents:
                        meta = doc.metadata
                        norm_c = meta.normalized_creation_date
                        if norm_c and app_date_val:
                            try:
                                dt_c = datetime.fromisoformat(norm_c)
                                # Application date is YYYY-MM-DD
                                dt_app = datetime.strptime(app_date_val, "%Y-%m-%d").replace(tzinfo=dt_c.tzinfo or timezone.utc)
                                # If creation date is more than 24 hours after application submission date
                                delta_days = (dt_c - dt_app).total_seconds() / 86400.0
                                if delta_days > 1.0:
                                    evidence_field = ExtractedField(
                                        name="creation_date_vs_application_date",
                                        value=f"CreationDate: {norm_c} | ApplicationDate: {app_date_val}",
                                        raw_text=f"Creation: {meta.raw_creation_date}",
                                        document_type=doc.document_type,
                                        document_id=doc.id,
                                        page_number=1,
                                        bbox=[36.0, 36.0, 520.0, 65.0],
                                        confidence=1.0
                                    )
                                    ctx = MetadataEvidenceContext(
                                        original_values={
                                            "raw_creation_date": meta.raw_creation_date,
                                            "declared_application_date": app_date_val,
                                            "producer": meta.producer,
                                            "creator": meta.creator
                                        },
                                        normalized_values={
                                            "normalized_creation_date": norm_c,
                                            "application_date": app_date_val,
                                            "days_post_application": round(delta_days, 1)
                                        },
                                        rule_triggered=rule_id,
                                        rule_title=rule_title,
                                        reason_for_review=(
                                            f"Document '{doc.filename}' CreationDate ({norm_c[:10]}) postdates declared application date ({app_date_val}) "
                                            f"by {delta_days:.1f} days. Indicates retroactive document re-generation or replacement. Flagged for officer review."
                                        ),
                                        parsing_warnings=meta.parsing_warnings
                                    )
                                    findings.append(Finding(
                                        id=f"find_{uuid.uuid4().hex[:10]}",
                                        application_id=application_id,
                                        rule_id=rule_id,
                                        rule_version=rule_version,
                                        rule_name=rule_title,
                                        rule_category=rule_category,
                                        aph_reference=aph_ref,
                                        severity=severity,
                                        status=FindingStatus.FLAGGED,
                                        lifecycle=FindingLifecycle.OPEN,
                                        claim=f"Document creation timestamp ({norm_c[:10]}) in '{doc.filename}' postdates application filing date ({app_date_val}) by {delta_days:.1f} days.",
                                        description=description,
                                        fields_involved=[evidence_field],
                                        metadata_context=ctx
                                    ))
                            except Exception:
                                pass

                elif rule_id == "META-003": # Parsing Warnings
                    for doc in documents:
                        meta = doc.metadata
                        if meta.parsing_warnings:
                            evidence_field = ExtractedField(
                                name="pdf_parsing_warnings",
                                value="; ".join(meta.parsing_warnings),
                                raw_text="; ".join(meta.parsing_warnings),
                                document_type=doc.document_type,
                                document_id=doc.id,
                                page_number=1,
                                bbox=[36.0, 36.0, 520.0, 65.0],
                                confidence=1.0
                            )
                            ctx = MetadataEvidenceContext(
                                original_values={
                                    "raw_creation_date": meta.raw_creation_date,
                                    "raw_mod_date": meta.raw_mod_date,
                                    "parsing_warnings": meta.parsing_warnings
                                },
                                normalized_values={
                                    "warning_count": len(meta.parsing_warnings)
                                },
                                rule_triggered=rule_id,
                                rule_title=rule_title,
                                reason_for_review="Non-standard syntax encountered during PDF metadata extraction (e.g. missing timezone offset or malformed date string).",
                                parsing_warnings=meta.parsing_warnings
                            )
                            findings.append(Finding(
                                id=f"find_{uuid.uuid4().hex[:10]}",
                                application_id=application_id,
                                rule_id=rule_id,
                                rule_version=rule_version,
                                rule_name=rule_title,
                                rule_category=rule_category,
                                aph_reference=aph_ref,
                                severity=severity,
                                status=FindingStatus.FLAGGED,
                                lifecycle=FindingLifecycle.OPEN,
                                claim=f"Metadata normalization warning in '{doc.filename}': {'; '.join(meta.parsing_warnings)}",
                                description=description,
                                fields_involved=[evidence_field],
                                metadata_context=ctx
                            ))

        return findings
