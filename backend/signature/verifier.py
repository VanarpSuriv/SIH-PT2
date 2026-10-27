"""
Digital Signature Verification Module powered by pyHanko.
Evaluates PDF signature integrity, cryptographic validity, signer trust, and tampering detection.

Distinguishes six canonical signature evaluation states:
1. UNSIGNED: No cryptographic signature dictionaries present.
2. INTACT (CRYPTOGRAPHICALLY_VALID_TRUSTED): Byte ranges valid, digest matches PKCS#7 signature, and signer certificate chains to configured AICTE trust root.
3. MODIFIED (INVALID_SIGNATURE): Byte-range digest mismatch or post-signing document alterations detected.
4. UNTRUSTED_SIGNER (UNTRUSTED_CERTIFICATE): Digest matches byte range, but signer certificate cannot be verified against the trusted root.
5. UNAVAILABLE_VALIDATION_INFO: Revocation information or intermediate certificate chain is incomplete or unavailable.
6. UNSUPPORTED_OR_FAILED: Corrupted signature dictionary, unsupported cryptographic algorithm, or parsing exception.

Statutory Notice:
A mathematically valid digital signature does not automatically prove AICTE regulatory authority.
Cryptographic validity and AICTE issuer authorization are verified and reported independently.
"""
import os
import logging
from typing import Dict, Any, Optional

from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.sign.validation import validate_pdf_signature
from pyhanko_certvalidator import ValidationContext
from asn1crypto import x509 as asn1_x509, pem

logger = logging.getLogger("signature_verifier")
SAMPLES_DIR = os.path.dirname(os.path.abspath(__file__))

def _get_validation_context() -> ValidationContext:
    """Load AICTE Root CA as the trusted anchor for pyHanko validation."""
    ca_pem_path = os.path.join(SAMPLES_DIR, "ca_cert.pem")
    if os.path.exists(ca_pem_path):
        with open(ca_pem_path, "rb") as f:
            _, _, der_bytes = pem.unarmor(f.read())
            ca_cert = asn1_x509.Certificate.load(der_bytes)
            return ValidationContext(trust_roots=[ca_cert])
    return ValidationContext(trust_roots=[])

class SignatureVerifier:
    """Verifies digital signatures on PDF documents using pyHanko and cryptographic anchors."""

    @staticmethod
    def verify_pdf(pdf_path: str) -> Dict[str, Any]:
        """
        Inspect PDF signatures using pyHanko and return structured verification status:
        INTACT, MODIFIED, UNTRUSTED_SIGNER, UNAVAILABLE_VALIDATION_INFO, UNSUPPORTED_OR_FAILED, or UNSIGNED.
        """
        # Resolve path relative to samples directory if not absolute or non-existent
        target_path = pdf_path
        if not os.path.exists(target_path):
            sample_candidate = os.path.join(SAMPLES_DIR, os.path.basename(pdf_path))
            if os.path.exists(sample_candidate):
                target_path = sample_candidate

        if not os.path.exists(target_path):
            return {
                "has_signature": False,
                "status": "UNSIGNED",
                "signer": None,
                "integrity": "N/A",
                "is_mathematically_valid": False,
                "is_trusted_ca": False,
                "is_aicte_authorized_issuer": False,
                "tampering_detected": False,
                "details": f"File '{pdf_path}' not found on disk."
            }

        try:
            vc = _get_validation_context()
            with open(target_path, "rb") as inf:
                reader = PdfFileReader(inf)
                embedded_sigs = reader.embedded_signatures
                if not embedded_sigs:
                    return {
                        "has_signature": False,
                        "status": "UNSIGNED",
                        "signer": None,
                        "integrity": "N/A",
                        "is_mathematically_valid": False,
                        "is_trusted_ca": False,
                        "is_aicte_authorized_issuer": False,
                        "tampering_detected": False,
                        "details": "No cryptographic signature dictionaries found in document catalog."
                    }

                sig = embedded_sigs[0]
                status = validate_pdf_signature(sig, signer_validation_context=vc)
                summary_str = status.summary().upper()

                # Determine signer name from signer cert
                signer_dn = "Unknown Signer"
                issuer_dn = "Unknown Issuer"
                is_aicte_issuer = False

                try:
                    if sig.signer_cert:
                        signer_dn = str(sig.signer_cert.subject.human_friendly)
                        issuer_dn = str(sig.signer_cert.issuer.human_friendly)
                        # Check whether signer certificate subject/issuer actually represents AICTE authority
                        cert_subj_upper = str(sig.signer_cert.subject.native).upper()
                        cert_iss_upper = str(sig.signer_cert.issuer.native).upper()
                        if "AICTE" in cert_subj_upper or "AICTE" in cert_iss_upper:
                            is_aicte_issuer = True
                except Exception:
                    pass

                # Case 1: Tampered / Modified post-signing (Invalid Signature)
                if not status.intact or "INVALID" in summary_str:
                    return {
                        "has_signature": True,
                        "status": "MODIFIED",
                        "signer": signer_dn,
                        "certificate_issuer": issuer_dn,
                        "integrity": "DIGEST_MISMATCH",
                        "is_mathematically_valid": False,
                        "is_trusted_ca": False,
                        "is_aicte_authorized_issuer": False,
                        "tampering_detected": True,
                        "pyhanko_summary": status.summary(),
                        "details": "Byte-range digest verification failed: Document content or page dictionary altered post-signing."
                    }

                # Case 2: Incomplete / Unavailable Validation Information (revocation / intermediate chain)
                elif "UNAVAILABLE" in summary_str or "REVOCATION" in summary_str or "INCOMPLETE" in summary_str:
                    return {
                        "has_signature": True,
                        "status": "UNAVAILABLE_VALIDATION_INFO",
                        "signer": signer_dn,
                        "certificate_issuer": issuer_dn,
                        "integrity": "VALID_DIGEST_INCOMPLETE_CHAIN",
                        "is_mathematically_valid": status.intact,
                        "is_trusted_ca": False,
                        "is_aicte_authorized_issuer": False,
                        "tampering_detected": False,
                        "pyhanko_summary": status.summary(),
                        "details": f"Certificate validation information incomplete or unavailable: {status.summary()}."
                    }

                # Case 3: Intact & Trusted under configured policy
                elif status.intact and getattr(status, "trusted", False) and "UNTRUSTED" not in summary_str:
                    return {
                        "has_signature": True,
                        "status": "INTACT",
                        "signer": signer_dn,
                        "certificate_issuer": issuer_dn,
                        "integrity": "CRYPTOGRAPHICALLY_VERIFIED",
                        "is_mathematically_valid": True,
                        "is_trusted_ca": True,
                        "is_aicte_authorized_issuer": is_aicte_issuer,
                        "tampering_detected": False,
                        "pyhanko_summary": status.summary(),
                        "details": (
                            "All byte ranges valid. Document digest matches embedded PKCS#7 signature and signer is trusted. "
                            f"AICTE Authority Binding: {'CONFIRMED' if is_aicte_issuer else 'NON_AICTE_ISSUER'}."
                        )
                    }

                # Case 4: Untrusted Signer (intact digest, but self-signed or untrusted root)
                elif status.intact and ("UNTRUSTED" in summary_str or not getattr(status, "trusted", False)):
                    return {
                        "has_signature": True,
                        "status": "UNTRUSTED_SIGNER",
                        "signer": signer_dn,
                        "certificate_issuer": issuer_dn,
                        "integrity": "VALID_DIGEST_UNTRUSTED_ROOT",
                        "is_mathematically_valid": True,
                        "is_trusted_ca": False,
                        "is_aicte_authorized_issuer": False,
                        "tampering_detected": False,
                        "pyhanko_summary": status.summary(),
                        "details": "Cryptographic digest matches byte range, but signer certificate cannot be verified against the trusted AICTE root CA."
                    }

                else:
                    return {
                        "has_signature": True,
                        "status": "FLAGGED",
                        "signer": signer_dn,
                        "certificate_issuer": issuer_dn,
                        "integrity": "UNKNOWN",
                        "is_mathematically_valid": status.intact,
                        "is_trusted_ca": False,
                        "is_aicte_authorized_issuer": False,
                        "tampering_detected": not status.intact,
                        "pyhanko_summary": status.summary(),
                        "details": f"Signature evaluation outcome: {status.summary()}"
                    }

        except Exception as e:
            logger.exception(f"Error during pyHanko validation: {e}")
            # Fail closed: never falsely declare an unparseable or error-state signature as INTACT
            return {
                "has_signature": True,
                "status": "UNSUPPORTED_OR_FAILED",
                "signer": None,
                "certificate_issuer": None,
                "integrity": "VALIDATION_FAILED",
                "is_mathematically_valid": False,
                "is_trusted_ca": False,
                "is_aicte_authorized_issuer": False,
                "tampering_detected": True,
                "details": f"Digital signature parsing or verification encountered an error: {str(e)}"
            }
