"""Rule 2.14 — Brand integrity check (v1.19+, deterministic).

Load `assets/brand-dictionary.json`, scan title+body để bắt tên thương hiệu
viết sai. Brand "MoMo" CHỈ có 1 cách viết đúng (camelCase, không dấu) — mọi biến
thể (Mô Mô, Momo, MOMO, Mo Mo, momo, mômô, ...) → hard block NOT_QUALIFIED.

Logic: với mỗi brand trong `enforce[]`, dùng `match_pattern` (regex case-insensitive)
tìm mọi token cùng hình dạng; token nào KHÁC chính xác `canonical` → vi phạm.

Fail-open (giống Rule 2.11 / 1.8): file missing/invalid regex → stderr warning 1 lần
+ skip Rule 2.14 (return pass). KHÔNG để lỗi data chặn cả pipeline.
"""
import json
import re
import sys
from pathlib import Path

def _find_brand_file() -> Path:
    """Tìm brand-dictionary.json (v1.11.5+ ở assets/ theo agentskills spec, fallback knowledge/)."""
    root = Path(__file__).resolve().parents[1]   # skill root (scripts → root)
    candidates = [
        Path("assets/brand-dictionary.json"),
        root / "assets" / "brand-dictionary.json",
        Path("knowledge/brand-dictionary.json"),             # legacy fallback (pre-v1.11.5)
        root / "knowledge" / "brand-dictionary.json",
    ]
    for p in candidates:
        if p.is_file():
            return p
    return candidates[1]   # canonical path for error message


_BRAND_FILE = _find_brand_file()

_warned = False
_cache = None  # list[tuple[canonical:str, compiled_regex, reason:str]]


def _warn_once(msg: str) -> None:
    global _warned
    if not _warned:
        print(f"[brand.py] WARNING: {msg} — skip Rule 2.14.", file=sys.stderr)
        _warned = True


def _load_enforce():
    """Load + compile enforce[] từ JSON. Cache sau lần đầu. Fail-open → []."""
    global _cache
    if _cache is not None:
        return _cache
    # Dual-runtime: assets/brand-dictionary.json (canonical) trước; nếu không với
    # tới (sandbox skill_script không ship assets/) → fallback module brand_data.py
    # (compile từ assets/ qua scripts/gen_data.py).
    data = None
    try:
        with open(_BRAND_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        try:
            from brand_data import DATA as _EMBEDDED
            data = _EMBEDDED
        except ImportError as e:
            _warn_once(f"Cannot load brand data (file + embedded đều miss): {e}")
            _cache = []
            return _cache

    compiled = []
    for b in data.get("enforce", []):
        canonical = b.get("canonical", "")
        pat = b.get("match_pattern", "")
        if not canonical or not pat:
            continue
        try:
            rx = re.compile(pat, re.IGNORECASE | re.UNICODE)
        except re.error as e:
            _warn_once(f"Bad regex for brand '{canonical}': {e}")
            continue
        compiled.append((canonical, rx, b.get("reason", "")))
    _cache = compiled
    return _cache


def check_rule_2_14(title: str, body: str) -> dict:
    """Rule 2.14 — Brand integrity. Hard block khi brand viết sai chính tả.

    Returns standard shape:
        {"rule": "2.14", "passed": False, "severity": "error",
         "tag": "brand_name_misspelled", "message": ...}  khi có vi phạm
        {"rule": "2.14", "passed": True}                   khi pass
    """
    enforce = _load_enforce()
    if not enforce:
        return {"rule": "2.14", "passed": True}

    combined = (title or "") + " " + (body or "")
    wrongs = []          # list[(matched, canonical)]
    seen = set()
    for canonical, rx, _reason in enforce:
        for m in rx.finditer(combined):
            matched = m.group(0)
            if matched != canonical and matched not in seen:
                seen.add(matched)
                wrongs.append((matched, canonical))

    if wrongs:
        detail = "; ".join(f"'{w}' → '{c}'" for w, c in wrongs)
        return {
            "rule": "2.14",
            "passed": False,
            "severity": "error",
            "tag": "brand_name_misspelled",
            "message": (
                f"Tên thương hiệu viết sai: {detail} (Rule 2.14). "
                f"Phải viết đúng theo brand guideline. Owner sửa và resubmit."
            ),
        }
    return {"rule": "2.14", "passed": True}
