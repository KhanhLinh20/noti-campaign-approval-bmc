"""Rule 2.11 — Banned phrases scan.

Load assets/banned-phrases.json (Legal/Compliance maintained).
Scan title + body. Return matched phrases với severity.

Severity mapping:
    blocker  → Tier A hard block (NOT_QUALIFIED)
    critical → Tier C Reg-floor HITL_REQUIRED
    warning  → Tier 2 score deduction (-15 to -25)

Fail-open behavior (v1.4.5+): nếu file banned-phrases.json missing, return
passed=True (không block) + cảnh báo 1 lần qua stderr để operator biết safety net mất.
"""
import json
import os
import sys
from pathlib import Path


_FILE_MISSING_WARNED = False


def _warn_file_missing_once() -> None:
    """Log 1 lần khi banned-phrases file missing (fail-open scenario)."""
    global _FILE_MISSING_WARNED
    if not _FILE_MISSING_WARNED:
        print(
            "[WARN] banned-phrases.json missing — Rule 2.11 banned phrases scan skipped "
            "(fail open). Place file at assets/banned-phrases.json to restore safety net.",
            file=sys.stderr,
        )
        _FILE_MISSING_WARNED = True


def _find_banned_phrases_file() -> Path:
    """Tìm file banned-phrases.json từ working dir hoặc skill root."""
    root = Path(__file__).resolve().parents[1]   # skill root (scripts → root)
    candidates = [
        Path("assets/banned-phrases.json"),                     # v1.11.5+ (agentskills spec: knowledge→assets)
        root / "assets" / "banned-phrases.json",
        Path("knowledge/banned-phrases.json"),               # legacy fallback (pre-v1.11.5)
        root / "knowledge" / "banned-phrases.json",
    ]
    for p in candidates:
        if p.is_file():
            return p
    raise FileNotFoundError(
        "banned-phrases.json không tìm thấy. Tried: " + " | ".join(str(c) for c in candidates)
    )


def load_banned_phrases(file_path: Path | None = None) -> list[dict]:
    """Load + return phrases list.

    Dual-runtime: ưu tiên assets/banned-phrases.json (canonical, full-fs runtime
    như Claude Code/Bash). Nếu file không với tới được (sandbox skill_script chỉ
    ship scripts/*.py, KHÔNG có assets/) → fallback sang module `banned_data.py`
    (bản compile từ chính assets/ qua scripts/gen_data.py). Cả 2 miss → FileNotFoundError
    để check_rule_2_11 fail-open.
    """
    try:
        p = file_path or _find_banned_phrases_file()
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f).get("phrases", [])
    except FileNotFoundError:
        pass
    try:
        from banned_data import DATA  # bundled fallback (scripts/banned_data.py)
        return DATA.get("phrases", [])
    except ImportError:
        raise FileNotFoundError(
            "banned-phrases.json không tìm thấy và banned_data.py chưa được bundle."
        )


def scan_banned_phrases(text: str, file_path: Path | None = None) -> list[dict]:
    """Scan text vs banned phrases list. Return list matched items với context.

    Match logic: substring case-insensitive (Legal đảm bảo phrase đủ đặc trưng).
    """
    phrases = load_banned_phrases(file_path)
    text_lower = (text or "").lower()
    matches = []
    for entry in phrases:
        pattern = entry.get("pattern", "")
        if pattern and pattern.lower() in text_lower:
            matches.append({
                "pattern": pattern,
                "severity": entry.get("severity", "warning"),
                "reason": entry.get("reason", ""),
                "carve_out": entry.get("carve_out"),
            })
    return matches


def check_rule_2_11(title: str, body: str, file_path: Path | None = None) -> dict:
    """Rule 2.11 wrapper — return per-rule check dict.

    Priority: blocker > critical > warning. Nếu có nhiều, return cái nặng nhất.
    """
    combined = (title or "") + " " + (body or "")
    try:
        matches = scan_banned_phrases(combined, file_path)
    except FileNotFoundError:
        _warn_file_missing_once()
        return {
            "rule": "2.11",
            "passed": True,
            "severity": "info",
            "message": "banned-phrases.json không tồn tại, skip Rule 2.11 scan."
        }

    if not matches:
        return {"rule": "2.11", "passed": True}

    # Sort by severity priority (blocker first)
    priority = {"blocker": 0, "critical": 1, "warning": 2}
    matches.sort(key=lambda m: priority.get(m["severity"], 99))
    top = matches[0]

    sev_to_label = {
        "blocker": "error",     # Tier A hard block
        "critical": "hitl",      # Tier C Reg-floor HITL
        "warning": "warning",    # Tier 2 score deduction
    }
    severity_label = sev_to_label.get(top["severity"], "warning")
    tag_map = {
        "blocker": "banned_phrase_blocker",
        "critical": "banned_phrase_critical",
        "warning": "banned_phrase_warning",
    }

    return {
        "rule": "2.11",
        "passed": False,
        "severity": severity_label,
        "message": (
            f"Phát hiện banned phrase '{top['pattern']}' (severity={top['severity']}). "
            f"Lý do: {top['reason']}"
            + (f" Carve-out: {top['carve_out']}" if top.get("carve_out") else "")
        ),
        "tag": tag_map.get(top["severity"], "banned_phrase_warning"),
        "all_matches": [m["pattern"] for m in matches],
    }
