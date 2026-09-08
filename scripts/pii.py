"""PII detection — Rule 2.4.

Detect: VN phone (0xx xxxx xxx), email, CCCD (9 or 12 digits), bank account.
"""
import re

# VN phone: 0 + 9-10 digits, or 84 + 9-10 digits
_PHONE_RE = re.compile(r"(?<!\d)(?:0\d{9,10}|84\d{9,10})(?!\d)")

# Email
_EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

# CCCD: 9 hoặc 12 chữ số liên tiếp (chú ý conflict với year/version → context-aware)
# Conservative: only flag 12-digit (new CCCD format) — 9-digit có thể nhầm với phone
_CCCD_12_RE = re.compile(r"(?<!\d)\d{12}(?!\d)")

# Bank account: 8-19 digits, context "stk", "tài khoản", "số tài khoản"
_BANK_CONTEXT_RE = re.compile(
    r"(?:stk|tk|tài[\s_]*khoản|số[\s_]*tk|account)[\s:#]*(\d{8,19})",
    re.IGNORECASE,
)


def detect_pii(text: str) -> list[tuple[str, str]]:
    """Return list of (pii_type, matched_value) found in text.

    Types: phone, email, cccd, bank
    """
    hits = []

    for m in _PHONE_RE.finditer(text):
        hits.append(("phone", m.group(0)))

    for m in _EMAIL_RE.finditer(text):
        hits.append(("email", m.group(0)))

    for m in _CCCD_12_RE.finditer(text):
        # Avoid double-count: if same span đã trigger phone, skip
        val = m.group(0)
        if not any(h[1] == val for h in hits):
            hits.append(("cccd", val))

    for m in _BANK_CONTEXT_RE.finditer(text):
        hits.append(("bank", m.group(1)))

    return hits


def has_pii(text: str) -> bool:
    """Quick boolean check."""
    return bool(detect_pii(text))
