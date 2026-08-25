import hmac


def verify_secret(provided, expected):
    """Constant-time comparison for shared-secret authentication."""
    expected_text = str(expected or "")
    provided_text = str(provided or "")
    if not expected_text:
        return False
    return hmac.compare_digest(provided_text, expected_text)


def resolve_control_token(ws_token=None, udp_token=None):
    """Prefer a dedicated WebSocket token; fall back to the UDP token."""
    return str(ws_token or "").strip() or str(udp_token or "").strip()


def normalize_control_host(host=None):
    """Fail closed to loopback unless a bind address is explicitly configured."""
    value = str(host or "").strip()
    return value or "127.0.0.1"
