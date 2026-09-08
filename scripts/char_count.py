#!/usr/bin/env python3
"""Character-count checker — script CHUYÊN TRÁCH đếm ký tự title/body noti.

Đây là "script số ký tự" duy nhất mà flow check campaign gọi tới. Đếm theo
đúng quy tắc v1.11.3:

    Athena trả về template STRING với placeholder ${...} còn nguyên
    (vd caption = "${lastname} ơi, ..."), chỉ render lúc gửi. Theo Rule
    2.1/2.2 mỗi placeholder tính = 0 ký tự → strip ${...} TRƯỚC khi len().
    KHÔNG reverse-sub (không convert chữ thường thành placeholder).

⚠️ SINGLE SOURCE OF TRUTH: logic `strip_placeholders` + thresholds
(`TITLE_MAX`/`BODY_MAX`) import từ `rules.py` + `constants.py` — KHÔNG
định nghĩa lại ở đây để tránh trùng lặp. `tier1_check.py` cũng dùng chung
`rules.strip_placeholders` → cả 2 luôn ra CÙNG 1 con số.

Dùng được 2 cách:
    1. Import:  from char_count import count_chars, check_title, check_body
    2. CLI:     echo '{"title": "...", "body": "..."}' | python char_count.py
                python char_count.py --title "..." --body "..."
"""
import argparse
import json
import sys
from pathlib import Path

# sibling modules importable khi chạy standalone (mirror tier1_check.py)
sys.path.insert(0, str(Path(__file__).parent))
from rules import strip_placeholders          # noqa: E402 — single source of truth
from constants import TITLE_MAX, BODY_MAX      # noqa: E402 — thresholds single source

# Ép UTF-8 cho I/O — tránh UnicodeEncodeError trên console Windows (cp1252).
for _stream in ("stdin", "stdout", "stderr"):
    _s = getattr(sys, _stream, None)
    if _s is not None and hasattr(_s, "reconfigure"):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass


def count_chars(text: str) -> int:
    """Số ký tự Unicode "theo rule" — placeholder ${...} = 0 ký tự.

    Tương đương công thức: raw − (tổng độ dài literal các placeholder).
        VD body "...Đừng để lỡ ${lastname} nhé!"
            raw (đếm ${lastname} literal) = 94
            len("${lastname}")            = 11
            94 − 11                       = 83  ← kết quả này
        len(strip_placeholders(text)) cho ra đúng 83 (regex bỏ HẾT placeholder).

    ⚠️ ĐÂY KHÔNG PHẢI "số ký tự render". Render thực tế thay ${lastname}→"bạn"
    (fallback) sẽ ra 86 — TUYỆT ĐỐI không dùng để đếm. Trừ độ dài LITERAL của
    placeholder (11), KHÔNG trừ độ dài fallback "bạn" (3). Xem Rule 2.1/2.2.
    """
    return len(strip_placeholders(text))


def _check(field: str, text: str, limit: int, rule: str) -> dict:
    n = count_chars(text)
    passed = n <= limit
    result = {
        "field": field,
        "rule": rule,
        "chars": n,
        "limit": limit,
        "passed": passed,
    }
    if not passed:
        result["message"] = (
            f"{field.capitalize()} {n} ký tự (sau khi bỏ placeholder) "
            f"> {limit} (Rule {rule}). Rút gọn còn ≤ {limit}."
        )
    return result


def check_title(title: str) -> dict:
    """Rule 2.1 — Title ≤ 30 ký tự (Unicode, placeholder = 0)."""
    return _check("title", title, TITLE_MAX, "2.1")


def check_body(body: str) -> dict:
    """Rule 2.2 — Body ≤ 120 ký tự (Unicode, placeholder = 0)."""
    return _check("body", body, BODY_MAX, "2.2")


def check(title: str = "", body: str = "") -> dict:
    """Đếm + kiểm tra cả title lẫn body. Trả về dict tổng hợp."""
    t = check_title(title)
    b = check_body(body)
    return {
        "title_len": t["chars"],
        "body_len": b["chars"],
        "passed": t["passed"] and b["passed"],
        "checks": [t, b],
    }


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Đếm ký tự title/body noti (placeholder ${...} = 0 ký tự)."
    )
    parser.add_argument("--title", default=None, help="Title text")
    parser.add_argument("--body", default=None, help="Body text")
    args = parser.parse_args(argv)

    # Ưu tiên arg CLI; nếu không có thì đọc JSON từ stdin.
    if args.title is None and args.body is None:
        raw = sys.stdin.read().lstrip("﻿").strip()  # bỏ UTF-8 BOM nếu có
        if not raw:
            parser.error("Cần --title/--body hoặc JSON qua stdin.")
        data = json.loads(raw)
        title = data.get("title", "")
        body = data.get("body", "")
    else:
        title = args.title or ""
        body = args.body or ""

    result = check(title, body)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
