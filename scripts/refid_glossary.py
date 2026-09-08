"""Rule 1.8 — RefID glossary validation.

Lookup assets/refid-glossary.tsv (format: name<TAB>refid, sorted by refid).

Patterns:
    validate_refid(refid)  → bool — refid có trong glossary không
    get_refid_name(refid)  → str  — tên màn từ refid (or empty string)
    search_by_keyword(kw)  → list — list candidate refids matching keyword in name

Fail-open behavior (v1.4.5+): nếu glossary file missing, các function return giá trị
"không block" (validate=True, name="", search=[]) để campaign vẫn xử lý được. KHẨN báo
1 lần qua stderr để operator biết safety net mất.
"""
import sys
from pathlib import Path
from functools import lru_cache


_FILE_MISSING_WARNED = False


def _warn_file_missing_once() -> None:
    """Log 1 lần khi glossary file missing (fail-open scenario)."""
    global _FILE_MISSING_WARNED
    if not _FILE_MISSING_WARNED:
        print(
            "[WARN] refid-glossary.tsv missing — Rule 1.8 RefID validation skipped "
            "(fail open). Place file at assets/refid-glossary.tsv to restore safety net.",
            file=sys.stderr,
        )
        _FILE_MISSING_WARNED = True


def _find_glossary_file() -> Path:
    """Tìm file refid-glossary.tsv từ working dir hoặc skill root."""
    root = Path(__file__).resolve().parents[1]   # skill root (scripts → root)
    candidates = [
        Path("assets/refid-glossary.tsv"),                      # v1.11.5+ (agentskills spec: knowledge→assets)
        root / "assets" / "refid-glossary.tsv",
        Path("knowledge/refid-glossary.tsv"),                # legacy fallback (pre-v1.11.5)
        root / "knowledge" / "refid-glossary.tsv",
    ]
    for p in candidates:
        if p.is_file():
            return p
    raise FileNotFoundError(
        "refid-glossary.tsv không tìm thấy. Tried: " + " | ".join(str(c) for c in candidates)
    )


@lru_cache(maxsize=1)
def _load_glossary() -> dict[str, str]:
    """Load TSV vào dict refid → name (cached for batch run)."""
    p = _find_glossary_file()
    refid_to_name: dict[str, str] = {}
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n\r")
            if not line or line.startswith("#") or line.startswith("name\t"):
                continue
            parts = line.split("\t")
            if len(parts) >= 2:
                name, refid = parts[0], parts[1]
                refid_to_name[refid] = name
    return refid_to_name


def validate_refid(refid: str) -> bool:
    """Return True nếu refid có trong glossary."""
    if not refid:
        return False
    try:
        return refid in _load_glossary()
    except FileNotFoundError:
        _warn_file_missing_once()
        return True  # Fail open — không block, nhưng đã cảnh báo stderr


def get_refid_name(refid: str) -> str:
    """Return tên màn từ refid, '' nếu không match."""
    try:
        return _load_glossary().get(refid, "")
    except FileNotFoundError:
        _warn_file_missing_once()
        return ""


def search_by_keyword(keyword: str) -> list[tuple[str, str]]:
    """Search refids có tên chứa keyword (case-insensitive). Return [(name, refid), ...]."""
    if not keyword:
        return []
    kw_lower = keyword.lower()
    try:
        glossary = _load_glossary()
    except FileNotFoundError:
        _warn_file_missing_once()
        return []
    return [
        (name, refid)
        for refid, name in glossary.items()
        if kw_lower in name.lower()
    ]


def _is_url_refid(refid: str) -> bool:
    """Check refid có phải URL format không.

    URL format hợp lệ (deeplink in-app webview): https://... hoặc http://...
    BU có thể chạy campaign trỏ về trang web in-app với refid dạng URL.
    Trong case này, KHÔNG check glossary (glossary chỉ chứa screen identifier ngắn).
    """
    if not refid:
        return False
    return refid.startswith(("https://", "http://"))


def check_rule_1_8(refid: str) -> dict:
    """Rule 1.8 — RefID typo check (glossary là tham khảo, không hard rule).

    Logic (v1.4.4+ — clarified):
    - refid rỗng → skip
    - refid URL format (https://...) → ✅ pass (hợp lệ, deeplink in-app)
    - refid identifier ngắn:
      - có trong glossary → ✅ pass (bonus: hiển thị tên màn)
      - không trong glossary → 🟡 HITL re-confirm (có thể typo hoặc màn mới)
    """
    if not refid:
        return {
            "rule": "1.8",
            "passed": True,
            "severity": "info",
            "message": "ref_id rỗng, skip Rule 1.8 check."
        }

    # URL format = hợp lệ, không cần glossary (BU dùng deeplink in-app webview)
    if _is_url_refid(refid):
        return {
            "rule": "1.8",
            "passed": True,
            "format": "url",
            "message": "ref_id là URL (deeplink in-app webview) — hợp lệ, không cần check glossary."
        }

    # Identifier format → check glossary cho typo
    try:
        glossary = _load_glossary()
    except FileNotFoundError:
        _warn_file_missing_once()
        return {
            "rule": "1.8",
            "passed": True,
            "severity": "info",
            "message": "refid-glossary.tsv không tồn tại, skip Rule 1.8 scan."
        }

    if refid in glossary:
        return {
            "rule": "1.8",
            "passed": True,
            "name": glossary[refid],   # Bonus: hiển thị tên màn cho approver
        }

    return {
        "rule": "1.8",
        "passed": False,
        "severity": "hitl",   # KHÔNG hard block — list có thể outdated hoặc typo
        "message": (
            f"RefID '{refid}' không có trong MoMo screen glossary. "
            "Có thể typo hoặc màn mới chưa update glossary. Approver xác nhận giùm."
        ),
        "tag": "refid_not_in_whitelist",
    }
