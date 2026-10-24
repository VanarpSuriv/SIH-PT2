"""
Cryptographic Audit Trail with SHA-256 Hash Chaining.
Ensures tamper-evident logging of all application events and finding actions.
"""
import hashlib
import json
import sqlite3
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any

from backend.models import AuditEvent

GENESIS_HASH = "0" * 64
AUDIT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audit_trail.db")

class AuditTrail:
    """Manages hash-chained audit log with tamper detection."""

    def __init__(self, db_path: str = AUDIT_DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_events (
                    seq_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    id TEXT UNIQUE NOT NULL,
                    timestamp TEXT NOT NULL,
                    application_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    prev_hash TEXT NOT NULL,
                    hash TEXT NOT NULL
                )
            """)
            conn.commit()

    @staticmethod
    def compute_hash(prev_hash: str, payload_str: str, timestamp: str, action: str, event_id: str) -> str:
        """Calculate SHA-256 hash across event attributes and prev_hash."""
        hasher = hashlib.sha256()
        canonical_str = f"{prev_hash}|{payload_str}|{timestamp}|{action}|{event_id}"
        hasher.update(canonical_str.encode("utf-8"))
        return hasher.hexdigest()

    def get_latest_hash(self) -> str:
        """Get the hash of the most recent audit entry, or genesis hash if empty."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT hash FROM audit_events ORDER BY seq_id DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                return row[0]
            return GENESIS_HASH

    def log_event(self, application_id: str, action: str, payload: Dict[str, Any]) -> AuditEvent:
        """Append an event to the hash chain."""
        event_id = f"evt_{uuid.uuid4().hex[:12]}"
        timestamp = datetime.now(timezone.utc).isoformat()
        prev_hash = self.get_latest_hash()
        payload_str = json.dumps(payload, sort_keys=True)
        event_hash = self.compute_hash(prev_hash, payload_str, timestamp, action, event_id)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO audit_events (id, timestamp, application_id, action, payload, prev_hash, hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (event_id, timestamp, application_id, action, payload_str, prev_hash, event_hash))
            conn.commit()

        return AuditEvent(
            id=event_id,
            timestamp=timestamp,
            application_id=application_id,
            action=action,
            payload=payload,
            prev_hash=prev_hash,
            hash=event_hash
        )

    def get_events(self, application_id: Optional[str] = None) -> List[AuditEvent]:
        """Fetch audit events, optionally filtered by application_id."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if application_id:
                cursor.execute("""
                    SELECT id, timestamp, application_id, action, payload, prev_hash, hash
                    FROM audit_events WHERE application_id = ? ORDER BY seq_id ASC
                """, (application_id,))
            else:
                cursor.execute("""
                    SELECT id, timestamp, application_id, action, payload, prev_hash, hash
                    FROM audit_events ORDER BY seq_id ASC
                """)
            rows = cursor.fetchall()

        events = []
        for r in rows:
            events.append(AuditEvent(
                id=r[0],
                timestamp=r[1],
                application_id=r[2],
                action=r[3],
                payload=json.loads(r[4]),
                prev_hash=r[5],
                hash=r[6]
            ))
        return events

    def verify_chain(self) -> Dict[str, Any]:
        """
        Verify the complete cryptographic integrity of the audit log.
        Detects any modified row, altered payload, or broken linkage.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT seq_id, id, timestamp, application_id, action, payload, prev_hash, hash
                FROM audit_events ORDER BY seq_id ASC
            """)
            rows = cursor.fetchall()

        if not rows:
            return {
                "is_valid": True,
                "total_events": 0,
                "message": "Audit chain is empty and valid."
            }

        expected_prev_hash = GENESIS_HASH

        for idx, (seq_id, evt_id, ts, app_id, act, payload_str, prev_h, stored_h) in enumerate(rows):
            # Check prev_hash pointer
            if prev_h != expected_prev_hash:
                return {
                    "is_valid": False,
                    "broken_at_seq": seq_id,
                    "broken_at_index": idx,
                    "event_id": evt_id,
                    "reason": f"Chain link broken at event #{seq_id} ('{evt_id}'). Expected prev_hash '{expected_prev_hash}', found '{prev_h}'."
                }

            # Recompute hash
            recomputed = self.compute_hash(prev_h, payload_str, ts, act, evt_id)
            if recomputed != stored_h:
                return {
                    "is_valid": False,
                    "broken_at_seq": seq_id,
                    "broken_at_index": idx,
                    "event_id": evt_id,
                    "reason": f"Payload tampering detected in event #{seq_id} ('{evt_id}'). Stored hash '{stored_h}' != recomputed '{recomputed}'."
                }

            expected_prev_hash = stored_h

        return {
            "is_valid": True,
            "total_events": len(rows),
            "latest_hash": expected_prev_hash,
            "message": f"Cryptographic integrity verified across all {len(rows)} events."
        }

    def tamper_event_for_demo(self, event_id: str, altered_payload: Dict[str, Any]) -> bool:
        """
        Tamper with an event row's payload without updating its hash.
        Used for the live demo to prove verify_chain detects manipulation.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE audit_events SET payload = ? WHERE id = ?", (json.dumps(altered_payload), event_id))
            conn.commit()
            return cursor.rowcount > 0

_audit_instance: Optional[AuditTrail] = None

def get_audit_trail() -> AuditTrail:
    """Singleton getter for AuditTrail."""
    global _audit_instance
    if _audit_instance is None:
        _audit_instance = AuditTrail()
    return _audit_instance
