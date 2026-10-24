"""
Verification Adapter for External Authority Registries.
Simulates verification calls to AICTE Central Registry, State Revenue / Land Registry, and Fire Dept Portals.
"""
import json
import os
from typing import Optional, Dict, Any

from backend.models import (
    VerificationResult,
    VerificationStatus
)

FAKE_ISSUERS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fake_issuers.json")

class VerificationAdapter:
    """Simulated external registry verification adapter."""

    def __init__(self, db_path: str = FAKE_ISSUERS_PATH):
        self.db_path = db_path
        self._db: Dict[str, Any] = {}
        self.reload()

    def reload(self) -> None:
        """Reload issuer records from disk."""
        if os.path.exists(self.db_path):
            with open(self.db_path, "r", encoding="utf-8") as f:
                self._db = json.load(f)
        else:
            self._db = {}

    def verify(self, issuer: str, record_id: str) -> VerificationResult:
        """
        Verify an identifier against the external issuer registry.
        Always returns source='SIMULATED' and one of the 6 standard statuses:
        'verified', 'mismatch', 'expired', 'pending', 'source unavailable', 'manual review'.
        """
        record_id = str(record_id).strip()
        rec = self._db.get(record_id)

        if not rec:
            return VerificationResult(
                issuer=issuer,
                record_id=record_id,
                status=VerificationStatus.SOURCE_UNAVAILABLE,
                source="SIMULATED",
                message=f"[SIMULATED] Identifier '{record_id}' not found in {issuer} authority database."
            )

        status_str = rec.get("status", "VERIFIED").upper()
        if status_str == "SOURCE_UNAVAILABLE":
            return VerificationResult(
                issuer=issuer,
                record_id=record_id,
                status=VerificationStatus.SOURCE_UNAVAILABLE,
                source="SIMULATED",
                message=f"[SIMULATED] External upstream endpoint for {issuer} is temporarily unresponsive."
            )
        elif status_str == "MISMATCH":
            return VerificationResult(
                issuer=issuer,
                record_id=record_id,
                status=VerificationStatus.MISMATCH,
                source="SIMULATED",
                message=f"[SIMULATED] External registry returned mismatched titleholder data: '{rec.get('institution_name')}'.",
                verified_data=rec
            )
        elif status_str == "EXPIRED":
            return VerificationResult(
                issuer=issuer,
                record_id=record_id,
                status=VerificationStatus.EXPIRED,
                source="SIMULATED",
                message=f"[SIMULATED] External authority lists certificate {record_id} as EXPIRED.",
                verified_data=rec
            )
        elif status_str == "PENDING":
            return VerificationResult(
                issuer=issuer,
                record_id=record_id,
                status=VerificationStatus.PENDING,
                source="SIMULATED",
                message=f"[SIMULATED] Verification request is queued in {issuer} batch processing.",
                verified_data=rec
            )
        elif status_str == "MANUAL_REVIEW":
            return VerificationResult(
                issuer=issuer,
                record_id=record_id,
                status=VerificationStatus.MANUAL_REVIEW,
                source="SIMULATED",
                message=f"[SIMULATED] Flagged by {issuer} automated clearinghouse for manual officer inspection.",
                verified_data=rec
            )
        else:
            return VerificationResult(
                issuer=issuer,
                record_id=record_id,
                status=VerificationStatus.VERIFIED,
                source="SIMULATED",
                message=f"[SIMULATED] Successfully confirmed active registration in {issuer} registry.",
                verified_data=rec
            )

_adapter_instance: Optional[VerificationAdapter] = None

def get_verification_adapter() -> VerificationAdapter:
    """Singleton getter for verification adapter."""
    global _adapter_instance
    if _adapter_instance is None:
        _adapter_instance = VerificationAdapter()
    return _adapter_instance

def verify(issuer: str, record_id: str) -> VerificationResult:
    """Convenience functional interface for verification."""
    return get_verification_adapter().verify(issuer, record_id)
