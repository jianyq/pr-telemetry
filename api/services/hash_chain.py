"""Event hash chain for integrity verification."""

import hashlib
import hmac
import json
from typing import Optional


SECRET_KEY = b"pr-telemetry-hmac-secret-key-change-in-production"


def compute_event_hash(event_dict: dict, previous_hash: Optional[str] = None) -> str:
    """
    Compute HMAC hash of an event chained with the previous hash.
    
    Args:
        event_dict: Event as dictionary
        previous_hash: Previous hash in chain (or None for first event)
    
    Returns:
        Hex-encoded HMAC hash
    """
    # Serialize event deterministically
    event_json = json.dumps(event_dict, sort_keys=True, separators=(",", ":"))
    
    # Chain with previous hash
    if previous_hash:
        message = f"{previous_hash}:{event_json}"
    else:
        message = event_json
    
    # Compute HMAC
    h = hmac.new(SECRET_KEY, message.encode("utf-8"), hashlib.sha256)
    return h.hexdigest()


def compute_chain_hash(events: list[dict]) -> Optional[str]:
    """
    Compute hash chain for a list of events.
    
    Args:
        events: List of event dictionaries (ordered by seq)
    
    Returns:
        Final hash in chain, or None if no events
    """
    if not events:
        return None
    
    current_hash = None
    for event in events:
        current_hash = compute_event_hash(event, current_hash)
    
    return current_hash

