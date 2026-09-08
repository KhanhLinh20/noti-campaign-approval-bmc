#!/usr/bin/env python3
"""render_batch_report.py — Render canonical markdown batch report.

Phase 2 hard enforcement (v1.5.1+) — generates 11-column summary table
với markdown link wrap consistent. Eliminate LLM variance trên distributed
Cowork users (some agent instances skip link wrap / render bulleted list).

Pattern (separation of concern):
    LLM (Tier 2 Judge) → verdict + score + reason_vn (creative)
    Script (this file) → markdown table render (deterministic)

Input JSON schema:
    {
      "env": "prod" | "uat",            # default "prod"
      "reviewer": "<email>",            # optional, for header
      "snapshot_time": "DD/MM/YYYY HH:MM VN",  # optional
      "campaigns": [
        {
          "name": "<full_campaign_name>",   # from Athena API, used in URL
          "alias": "<family_variant>",      # ≤ 20 chars, display in link text
          "content_type": "PROMOTION" | ...,
          "title": "<title>",
          "body": "<body, truncate if >100>",
          "image_url": "<url or null>",
          "t1_score": 100 | "N/A",
          "t2_score": 91 | "HITL" | "N/A",
          "verdict": "QUALIFIED" | "WARNING" | "HITL_REQUIRED" | "NOT_QUALIFIED" | "EXPIRED",
          "reason_vn": "<natural VN, no rule code>",
          "action": "<action text>"
        },
        ...
      ]
    }

Output: markdown 11-col table to stdout (UTF-8).

Usage:
    python scripts/render_batch_report.py --json '{"env":"prod","campaigns":[...]}'
    python scripts/render_batch_report.py --file batch.json
    cat batch.json | python scripts/render_batch_report.py

Exit code: 0 success / 99 input error.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

# Ensure sibling scripts + lib are importable when run from skill root
sys.path.insert(0, str(Path(__file__).parent))
from timefmt import format_push_time   # noqa: E402  — shared ICT time formatting (top-level sibling)


# ─── Constants ──────────────────────────────────────────────────────────────
ATHENA_URL = {
    "prod": "https://athena.mservice.io",
    "uat": "https://athena-uat.mservice.io",
}

VERDICT_ICON = {
    "QUALIFIED":      "🟢",
    "WARNING":        "🟡",
    "HITL_REQUIRED":  "🟣",
    "NOT_QUALIFIED":  "🔴",
    "EXPIRED":        "⛔",
}

VERDICT_LABEL = {
    "QUALIFIED":      "QUALIFIED",
    "WARNING":        "WARNING",
    "HITL_REQUIRED":  "HITL_REQUIRED",
    "NOT_QUALIFIED":  "NOT_QUALIFIED",
    "EXPIRED":        "EXPIRED",
}


# ─── Helpers ────────────────────────────────────────────────────────────────
def _score_cell(score: Any) -> str:
    """Format score with icon. Accepts int (0-100) or 'N/A' / 'HITL' string."""
    if score == "N/A" or score is None:
        return "❌ N/A"
    if score == "HITL":
        return "🟣 HITL"
    try:
        n = int(score)
    except (TypeError, ValueError):
        return str(score)
    if n >= 90:
        return f"🟢 {n}"
    if n >= 85:
        return f"🟡 {n}"
    if n >= 50:
        return f"🟠 {n}"
    return f"🔴 {n}"


def _verdict_cell(verdict: str) -> str:
    """Format verdict with icon + label."""
    v = verdict.upper() if isinstance(verdict, str) else ""
    icon = VERDICT_ICON.get(v, "❓")
    label = VERDICT_LABEL.get(v, verdict)
    return f"{icon} {label}"


def _image_cell(image_url: str | None) -> str:
    """Format image cell — '—' nếu trống, markdown link nếu có."""
    if not image_url or not str(image_url).strip():
        return "—"
    url = str(image_url).strip()
    # Extract filename from URL for display
    filename = url.rsplit("/", 1)[-1] if "/" in url else "image"
    return f"[{filename}]({url}) ⚠️"


def _truncate(text: str, max_len: int = 100) -> str:
    """Truncate text with ellipsis nếu vượt max_len."""
    if not text:
        return ""
    text = str(text).replace("\n", " ").replace("|", "\\|").strip()
    return text if len(text) <= max_len else text[: max_len - 3] + "..."


def _oneline(text: Any) -> str:
    """Gộp newline, KHÔNG escape pipe (dùng cho layout dọc — không phải cell bảng)."""
    return str(text or "").replace("\n", " ").strip()


def _validate_alias(alias: str) -> str:
    """Enforce alias ≤ 20 chars. Truncate nếu vượt (warning)."""
    if not alias:
        return "unknown"
    if len(alias) <= 20:
        return alias
    # Truncate but flag with marker
    return alias[:17] + "..."


def _campaign_cell(name: str, alias: str, env: str) -> str:
    """Render Campaign cell with mandatory markdown link wrap.

    Format: [`<alias>`](<base_url>/notification-v2/list-view?name=<full_name>)
    """
    safe_alias = _validate_alias(alias)
    base_url = ATHENA_URL.get(env.lower(), ATHENA_URL["prod"])
    return f"[`{safe_alias}`]({base_url}/notification-v2/list-view?name={name})"


# ─── Main render ────────────────────────────────────────────────────────────
def render_report(payload: Dict[str, Any]) -> str:
    """Render canonical 11-column markdown batch report."""
    env = (payload.get("env") or "prod").lower()
    reviewer = payload.get("reviewer", "")
    snapshot_time = payload.get("snapshot_time", "")
    campaigns: List[Dict[str, Any]] = payload.get("campaigns", []) or []

    if not campaigns:
        return "> ⚠️ Không có campaign nào để render. Input array `campaigns` rỗng."

    n = len(campaigns)
    env_label = "Prod" if env == "prod" else "UAT"

    # ─── Header block ───────────────────────────────────────────────
    lines = []
    lines.append(f"## 📋 Noti Campaigns — IN_REVIEW ({n} campaign{'s' if n > 1 else ''})")
    if snapshot_time or reviewer:
        meta = []
        if snapshot_time:
            meta.append(f"**Cập nhật:** {snapshot_time}")
        meta.append(f"**Tổng:** {n} campaign{'s' if n > 1 else ''}")
        if reviewer:
            meta.append(f"**Reviewer:** {reviewer}")
        meta.append(f"**Env:** {env_label}")
        lines.append(" | ".join(meta))
    lines.append("")
    lines.append("> 📊 Tier 1 (Script) — Rule/Title/Body/CT/Routing · Tier 2 (LLM Content Review theo `07-llm-judge-core_v1.12.md`)")
    lines.append("> Ngưỡng: 🟢 ≥ 90 | 🟡 85–89 | 🟠 50–84 | 🔴 < 50 | 🟣 HITL-triggered | ⛔ EXPIRED")
    lines.append("> Cột 🖼 Ảnh: `—` (không có) hoặc `[filename](url) ⚠️` (advisory click review trước duyệt)")
    lines.append("")

    # ─── Table header ───────────────────────────────────────────────
    lines.append("| # | Campaign | CT | Title | Body | 🖼 Ảnh | T1 | T2 | Verdict | Lý do | Hành động |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")

    # ─── Table rows ─────────────────────────────────────────────────
    for i, c in enumerate(campaigns, start=1):
        row = [
            str(i),
            _campaign_cell(c.get("name", ""), c.get("alias", ""), env),
            (c.get("content_type") or "").upper(),
            _truncate(c.get("title", ""), 60),
            _truncate(c.get("body", ""), 100),
            _image_cell(c.get("image_url")),
            _score_cell(c.get("t1_score")),
            _score_cell(c.get("t2_score")),
            _verdict_cell(c.get("verdict", "")),
            _truncate(c.get("reason_vn", "") or "—", 150),
            c.get("action", "—") or "—",
        ]
        lines.append("| " + " | ".join(row) + " |")

    # ─── Footer disclaimer ──────────────────────────────────────────
    lines.append("")
    lines.append("---")
    lines.append("> ⚠️ Đây là kết quả phân tích — chưa có thao tác nào được thực hiện trong Athena.")
    lines.append("> Mọi quyết định approve/reject vẫn do approver thực hiện thủ công.")
    lines.append("> Tìm campaign: click tên trong cột Campaign (→ mở Athena detail view).")
    lines.append("")
    lines.append(f"*Rendered by `scripts/render_batch_report.py` — env={env_label}, {n} campaign{'s' if n > 1 else ''}*")

    return "\n".join(lines)


def render_vertical(payload: Dict[str, Any]) -> str:
    """Layout DỌC (field: value) — cố định, hẹp, KHÔNG tràn ngang.

    Dùng cho side-panel / review 1 campaign (athena-copilot). Bảng 11 cột ngang
    (render_report) chỉ hợp chat full-width + batch nhiều campaign.
    """
    env = (payload.get("env") or "prod").lower()
    campaigns: List[Dict[str, Any]] = payload.get("campaigns", []) or []
    if not campaigns:
        return "> ⚠️ Không có campaign nào để render. Input array `campaigns` rỗng."
    n = len(campaigns)
    env_label = "Prod" if env == "prod" else "UAT"

    lines = [f"## 📋 Review {n} Noti Campaign · {env_label}"]
    for c in campaigns:
        v = (c.get("verdict") or "").upper()
        lines.append("")
        lines.append(f"### {_verdict_cell(v)} — {_campaign_cell(c.get('name', ''), c.get('alias', ''), env)}")
        rows = [
            ("CT", (c.get("content_type") or "").upper()),
            ("Title", _oneline(c.get("title", ""))),
            ("Body", _oneline(c.get("body", ""))),
        ]
        img = _image_cell(c.get("image_url"))
        if img != "—":
            rows.append(("🖼 Ảnh", img))
        if c.get("segment"):
            rows.append(("Segment", _oneline(c.get("segment"))))
        if c.get("push_time_ict"):
            rows.append(("Push", _oneline(c.get("push_time_ict"))))
        rows.append(("T1 / T2", f"{_score_cell(c.get('t1_score'))} / {_score_cell(c.get('t2_score'))}"))
        rows.append(("Lý do", _oneline(c.get("reason_vn")) or "—"))
        rows.append(("Hành động", _oneline(c.get("action")) or "—"))
        for k, val in rows:
            lines.append(f"- **{k}:** {val}")

    lines.append("")
    lines.append("---")
    lines.append("> ⚠️ Kết quả phân tích — chưa thao tác gì trong Athena; approve/reject do người duyệt.")
    lines.append(f"*Rendered by `scripts/render_batch_report.py` (vertical) — {env_label}, {n} campaign{'s' if n > 1 else ''}*")
    return "\n".join(lines)


def _load_input(args) -> Dict[str, Any]:
    """Load JSON từ --json, --file, hoặc stdin. BOM-safe (PowerShell hay chèn BOM)."""
    if args.json:
        return json.loads(args.json.lstrip("﻿"))
    if args.file:
        with open(args.file, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    return json.loads(sys.stdin.read().lstrip("﻿"))


def main():
    parser = argparse.ArgumentParser(
        description="Render canonical 11-column markdown batch report cho Phase 3."
    )
    parser.add_argument("--json", help="Inline JSON string")
    parser.add_argument("--file", help="Path đến file JSON")
    parser.add_argument(
        "--layout", choices=["auto", "vertical", "table"], default="auto",
        help="auto=1 campaign→dọc, ≥2→bảng (default) · vertical=luôn dọc (side-panel) · table=bảng 11 cột",
    )
    args = parser.parse_args()

    # Force UTF-8 output even on Windows cp1252 (đặt sớm để lỗi cũng ra UTF-8).
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    # v1.12.3: LUÔN exit 0 + lỗi ra STDOUT (prefix ERROR:) — sandbox skill_script
    # coi exit≠0 = fail và vứt stdout.
    try:
        payload = _load_input(args)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"ERROR: Input parse failed: {e}")
        sys.exit(0)

    try:
        n = len(payload.get("campaigns", []) or [])
        use_vertical = args.layout == "vertical" or (args.layout == "auto" and n <= 1)
        report = render_vertical(payload) if use_vertical else render_report(payload)
    except Exception as e:
        print(f"ERROR: Render failed: {type(e).__name__}: {e}")
        sys.exit(0)

    print(report)
    sys.exit(0)


if __name__ == "__main__":
    main()
