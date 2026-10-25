import hashlib
import json


def compute_event_hash(event: dict, previous_hash: str, session_id: str) -> str:
    """Compute the _hash for a single event. Excludes _hash from payload."""
    payload = {k: v for k, v in event.items() if k != "_hash"}
    # Stable serialisation: sorted keys, no extra whitespace
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    hash_input   = payload_json + "|" + previous_hash + "|" + session_id
    return hashlib.sha256(hash_input.encode("utf-8")).hexdigest()


def verify_process_log(log: dict) -> tuple[bool, str]:
    """
    Verify a TWFF process-log.json dict.
    Returns (is_valid: bool, detail_message: str).
    """
    session_id = log.get("session_id", "")
    events     = log.get("events", [])
    prev_hash  = ""

    for i, event in enumerate(events):
        stored_hash   = event.get("_hash", "")
        expected_hash = compute_event_hash(event, prev_hash, session_id)
        # A *missing* _hash must fail exactly like a *mismatched* one — the
        # old `if stored_hash and ...` skipped the check entirely when
        # stored_hash was empty, then silently adopted the freshly-computed
        # hash as the chain's next prev_hash as if it had been correctly
        # chained. That let a hand-fabricated log with no _hash fields at
        # all, or a genuine log with one event altered and its hash (and
        # every downstream hash) simply deleted, both verify as "intact."
        # The chain is only tamper-evident if every event is required to
        # carry a correct hash, not just the ones that happen to have one.
        if not stored_hash or stored_hash != expected_hash:
            return False, (
                f"Hash mismatch at event {i} (type={event.get('type')!r}). "
                f"Expected {expected_hash[:16]}…, got {stored_hash[:16] or '(missing)'}…"
            )
        prev_hash = stored_hash

    # Verify top-level _integrity.head_hash — same fix: a missing head_hash
    # must fail, not pass by skipping the comparison.
    integrity = log.get("_integrity", {})
    head_hash = integrity.get("head_hash", "")
    if not head_hash or head_hash != prev_hash:
        return False, (
            f"_integrity.head_hash mismatch. "
            f"Expected {prev_hash[:16]}…, got {head_hash[:16] or '(missing)'}…"
        )

    return True, f"Log intact — {len(events)} events verified."
