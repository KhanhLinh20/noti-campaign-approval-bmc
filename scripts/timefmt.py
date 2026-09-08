#!/usr/bin/env python3
"""Shared time formatting — ICT (Indochina Time = GMT+7).

Single source of truth cho mọi hiển thị/định dạng giờ trong skill. Trước đây
`format_push_time()` bị duplicate trong render_batch_report.py + render_athena_comment.py
→ tách về đây (v1.11.3). Từ v1.11.4 chuyển từ `lib/` ra top-level `scripts/`
vì đã có CLI — thống nhất "mọi script agent chạy trực tiếp đều ở top-level" (như char_count.py).

HARD rule (xem references/noti-campaign-approval.md): push_time LUÔN trả GIỜ CHUẨN ICT,
format `DD/MM/YYYY HH:mm` — CẤM `~` (xấp xỉ), CẤM raw epoch, CẤM để nguyên UTC.
⛔ CẤM convert push_time bằng đầu (LLM tự +7h / tự strftime) — LUÔN đi qua script này.

Dùng timezone-aware `datetime.fromtimestamp(..., tz=ICT)` thay vì
`utcfromtimestamp() + timedelta(hours=7)` (deprecated từ Python 3.12). Kết quả y hệt.

Dùng được 2 cách (mirror char_count.py):
    1. Import:  from timefmt import format_push_time
    2. CLI:     python scripts/timefmt.py --ms 1783486500000
                echo '{"push_time": 1783486500000}' | python scripts/timefmt.py
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta

# Ép UTF-8 cho I/O — tránh UnicodeEncodeError trên console Windows (cp1252).
for _stream in ("stdin", "stdout", "stderr"):
    _s = getattr(sys, _stream, None)
    if _s is not None and hasattr(_s, "reconfigure"):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass

# Indochina Time — múi giờ Việt Nam (GMT+7). Cùng offset với ICT/Bangkok.
ICT = timezone(timedelta(hours=7))

PUSH_TIME_FMT = "%d/%m/%Y %H:%M"   # format chuẩn hiển thị push_time cho approver


def format_push_time(push_time_ms: int | None) -> str:
    """Convert epoch milliseconds (UTC) → 'DD/MM/YYYY HH:mm' giờ ICT (GMT+7).

    Args:
        push_time_ms: Unix epoch milliseconds (từ MCP, UTC). None/0/invalid → "N/A".

    Returns:
        Chuỗi giờ ICT chuẩn (VD "08/07/2026 11:55"), hoặc "N/A" nếu không hợp lệ.
    """
    if not push_time_ms:
        return "N/A"
    try:
        return datetime.fromtimestamp(push_time_ms / 1000, tz=ICT).strftime(PUSH_TIME_FMT)
    except (TypeError, ValueError, OSError, OverflowError):
        return "N/A"


def iso_now_vn() -> str:
    """Thời điểm hiện tại theo ICT dạng ISO ngắn: '2026-06-08T15:40+07' (cho audit log)."""
    return datetime.now(ICT).strftime("%Y-%m-%dT%H:%M+07")


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main(argv=None) -> int:
    """Quy đổi push_time epoch-ms (UTC) → chuỗi ICT chuẩn. In JSON để cite verbatim.

    Đây là NGUỒN DUY NHẤT được phép quy đổi push_time trong flow check campaign —
    cấm LLM tự +7h / tự strftime bằng đầu (xem references/noti-campaign-approval.md).
    """
    parser = argparse.ArgumentParser(
        description="Quy đổi push_time epoch milliseconds (UTC) → giờ ICT (GMT+7)."
    )
    parser.add_argument(
        "--ms", type=int, default=None,
        help="push_time epoch milliseconds (UTC) — vd 1783486500000",
    )
    args = parser.parse_args(argv)

    # Ưu tiên arg CLI; nếu không có thì đọc JSON từ stdin ({"push_time": <ms>}).
    # skill_script đẩy inputs (map) làm JSON stdin → {"push_time": <ms>} khớp trực tiếp.
    if args.ms is None:
        raw = sys.stdin.read().lstrip("﻿").strip()  # bỏ UTF-8 BOM nếu có
        try:
            data = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            data = {}
        push_time_ms = data.get("push_time", data.get("push_time_ms"))
    else:
        push_time_ms = args.ms

    ict = format_push_time(push_time_ms)
    result = {"push_time_ms": push_time_ms, "push_time_ict": ict}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    # LUÔN return 0 — sandbox skill_script coi exit≠0 = fail và vứt stdout.
    # Kết quả N/A đã nằm trong field push_time_ict để consumer tự xử lý.
    return 0


if __name__ == "__main__":
    sys.exit(main())
