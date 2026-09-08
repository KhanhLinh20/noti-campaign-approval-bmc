#!/usr/bin/env python3
"""render_athena_comment.py — Render canonical Phase 5 Athena comment.

Phase 5 hard enforcement (v1.7.0+ approval sub-skill, v1.9.0+ SKILL) —
generates canonical template-compliant comment cho `update_campaign_action()`.
Eliminate LLM free-form variance across Cowork distributed members.

Pattern (separation of concern):
    LLM Tier 2 Judge    →  verdict + score + reason_vn (creative)
    Phase 4 confirm     →  approver decision (action keyword)
    Script (this file)  →  canonical comment string (deterministic)
                            ↓
    MCP update_campaign_action(comment=<output>)

Input JSON schema:
    {
      "approver_email": "huong.vu4@mservice.com.vn",
      "approver_role": "PCS",                # PCS | BMC | CIO | Growth | Platform Operator
      "action": "APPROVED",                  # APPROVED | REJECTED
      "campaign_name": "260608_...",         # for audit trace, not in body
      "ai_verdict": "HITL_REQUIRED",         # QUALIFIED | WARNING | HITL_REQUIRED | NOT_QUALIFIED
      "ai_agreement": "yes",                 # yes | no
      "score_t1": 100,                       # 0-100 or "N/A"
      "score_t2": 96,                        # 0-100 or "HITL" or "N/A"
      "reasoning_vn": "Title rõ, body cite TT77 hợp lệ, CTA đúng feature.",  # 1-2 sentences
      "reviewer_team": "PCS",                # optional
      "review_note": "PCS team review offline OK",  # required if offline_review=yes
      "offline_review": "yes",               # optional — yes | no (only when action != AI suggest)
      "disagree_reason": "...",              # required if ai_agreement=no
      "priority": "NORMAL",                  # NORMAL | BYPASS (only when action=APPROVED)
      "tags": ["quan_trong_pcs_routing"],    # optional
      "override": false,                     # optional
      "just": "platform_authority",          # optional
      "push_time": 1783486500000,            # MANDATORY (v1.11.4+) — epoch ms UTC (schedule_config.push_time)
      "push_time_ict": "08/07/2026 11:55",   # MANDATORY (v1.11.4+) — output từ timefmt.py, PHẢI khớp
                                             #   format_push_time(push_time). Cấm convert thủ công.
      "tier1_check_output": {                # MANDATORY (v1.8.0+) — output từ tier1_check.py
        "passed": true,                       # forces script chain dependency.
        "hard_block": false,                  # Agent BẮT BUỘC chạy Tier 1 trước
        "hitl_required": true,                # rồi pass output vào payload này.
        "tags": ["quan_trong_pcs_routing"],
        "metadata": {...}
      }
    }

Script chain dependency (v1.8.0+):
    Workflow: tier1_check.py → render_athena_comment.py → MCP update_campaign_action()

    1. agent runs:  TIER1=$(echo $CAMPAIGN | python tier1_check.py --unwrap)
    2. agent runs:  COMMENT=$(echo $PAYLOAD_WITH_TIER1 | python render_athena_comment.py)
    3. agent fires: MCP update_campaign_action(comment=$COMMENT)

    Bước 2 schema validation REJECTS payload thiếu tier1_check_output → agent
    CANNOT generate comment without running Tier 1 first → CANNOT fire MCP without
    valid comment. Forces technical chain dependency vs spec-only mandate.

Output: 3-part canonical Athena comment (UTF-8) to stdout.

Format:
    {Human reasoning natural VN — Approve/Reject by {user} ({role}). ...}
    ---
    [AI-REVIEW v1.2] {structured key=value codes}
    —— [ai_verdict=V] [ai_agreement=yes|no] [offline_review=...] [review_note=...] [reviewer_team=...] [disagree_reason=...]

Usage:
    python scripts/render_athena_comment.py --json '{"approver_email":...}'
    python scripts/render_athena_comment.py --file payload.json
    cat payload.json | python scripts/render_athena_comment.py

Exit code: 0 success / 99 input error / 1 schema validation fail.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure sibling scripts + lib are importable when run from skill root
sys.path.insert(0, str(Path(__file__).parent))
from timefmt import format_push_time, iso_now_vn   # noqa: E402  — shared ICT time formatting (top-level sibling)


# ─── Constants ──────────────────────────────────────────────────────────────
VALID_ACTIONS = {"APPROVED", "REJECTED"}
VALID_VERDICTS = {"QUALIFIED", "WARNING", "HITL_REQUIRED", "NOT_QUALIFIED"}
VALID_AGREEMENT = {"yes", "no"}
VALID_OFFLINE_REVIEW = {"yes", "no"}
VALID_PRIORITY = {"NORMAL", "BYPASS"}

# Approver shortname (for "Approve by huong.vu4" format)
def _shortname(email: str) -> str:
    """Extract username from email (vd 'huong.vu4@mservice.com.vn' → 'huong.vu4')."""
    return email.split("@", 1)[0] if "@" in email else email


# ─── Schema validation ──────────────────────────────────────────────────────
TIER1_REQUIRED_KEYS = {"passed", "hard_block", "hitl_required", "tags", "metadata"}

# push_time_ict phải là giờ ICT chuẩn 'DD/MM/YYYY HH:mm' (hoặc 'N/A' khi không có push_time).
PUSH_TIME_ICT_RE = re.compile(r"^\d{2}/\d{2}/\d{4} \d{2}:\d{2}$")


def _validate_push_time(payload: Dict[str, Any], errors: List[str]) -> None:
    """push_time_ict MANDATORY (v1.11.4+) — force quy đổi qua timefmt.py, cấm convert thủ công.

    Không chỉ require field: cross-check `push_time_ict` PHẢI == `format_push_time(push_time)`.
    Agent phải pass CẢ raw ms (`push_time`) LẪN output script (`push_time_ict`) và 2 giá trị
    khớp nhau → không thể fabricate chuỗi ICT plausible-sounding. Đây là technical enforcement
    của HARD rule "quy đổi push_time chỉ được lấy từ script" (references/noti-campaign-approval.md).
    """
    if "push_time" not in payload or payload.get("push_time") in (None, ""):
        errors.append(
            "Required field 'push_time' missing (v1.11.4+) — epoch ms UTC từ "
            "schedule_config.push_time. Cần để cross-check push_time_ict."
        )
        raw_ms = None
    else:
        try:
            raw_ms = int(payload["push_time"])
        except (TypeError, ValueError):
            errors.append(f"push_time='{payload['push_time']}' phải là epoch milliseconds (int).")
            raw_ms = None

    ict = payload.get("push_time_ict")
    if not ict or not isinstance(ict, str):
        errors.append(
            "push_time_ict MANDATORY (v1.11.4+) — chuỗi ICT lấy verbatim từ "
            "`python scripts/timefmt.py --ms <push_time>`. "
            "CẤM convert thủ công / LLM tự +7h bằng đầu."
        )
        return

    ict = ict.strip()
    if "~" in ict:
        errors.append("push_time_ict CẤM chứa '~' (xấp xỉ) — phải là giờ ICT chuẩn từ timefmt.py.")
        return
    if ict != "N/A" and not PUSH_TIME_ICT_RE.match(ict):
        errors.append(
            f"push_time_ict='{ict}' sai format — phải 'DD/MM/YYYY HH:mm' (giờ ICT) hoặc 'N/A'. "
            f"Lấy verbatim từ timefmt.py, KHÔNG raw epoch / để UTC / tự gõ."
        )
        return

    # Cross-check với raw ms — chống fabricate chuỗi ICT + phát hiện convert sai (off-by-hour, quên +7).
    if raw_ms is not None:
        expected = format_push_time(raw_ms)
        if ict != expected:
            errors.append(
                f"push_time_ict='{ict}' KHÔNG khớp output timefmt.py='{expected}' "
                f"(cho push_time={raw_ms}). Chạy `python scripts/timefmt.py --ms {raw_ms}` "
                f"và copy verbatim field push_time_ict — CẤM tự convert."
            )


def _validate(payload: Dict[str, Any]) -> List[str]:
    """Validate payload schema. Return list of error messages (empty if pass)."""
    errors = []

    # Required fields
    required = ["approver_email", "approver_role", "action", "campaign_name",
                "ai_verdict", "ai_agreement", "reasoning_vn"]
    for f in required:
        if f not in payload or not payload[f]:
            errors.append(f"Required field '{f}' missing or empty")

    # Enum validation
    if payload.get("action") not in VALID_ACTIONS:
        errors.append(f"Invalid action='{payload.get('action')}', must be {VALID_ACTIONS}")
    if payload.get("ai_verdict") not in VALID_VERDICTS:
        errors.append(f"Invalid ai_verdict='{payload.get('ai_verdict')}', must be {VALID_VERDICTS}")
    if payload.get("ai_agreement") not in VALID_AGREEMENT:
        errors.append(f"Invalid ai_agreement='{payload.get('ai_agreement')}', must be {VALID_AGREEMENT}")

    # Conditional required
    if payload.get("ai_agreement") == "no" and not payload.get("disagree_reason"):
        errors.append("disagree_reason MANDATORY when ai_agreement=no")
    if payload.get("offline_review") == "yes" and not payload.get("review_note"):
        errors.append("review_note MANDATORY when offline_review=yes")
    if payload.get("action") == "APPROVED":
        priority = payload.get("priority")
        if priority not in VALID_PRIORITY:
            errors.append(f"priority MANDATORY for APPROVED, must be {VALID_PRIORITY}, got '{priority}'")
    # offline_review enum check
    if "offline_review" in payload and payload["offline_review"] not in VALID_OFFLINE_REVIEW:
        errors.append(f"Invalid offline_review='{payload['offline_review']}', must be {VALID_OFFLINE_REVIEW}")

    # push_time enforcement (v1.11.4+) — force quy đổi qua timefmt.py, cross-check raw ms vs ICT.
    _validate_push_time(payload, errors)

    # Script chain dependency (v1.8.0+) — Fix #5 cho prod failure 10/06/2026:
    # agent CANNOT claim verdict mà KHÔNG show evidence từ tier1_check.py.
    # render_athena_comment REQUIRE tier1_check_output as part of payload
    # → forces script chain → agent BẮT BUỘC chạy Tier 1 trước khi gen comment.
    tier1 = payload.get("tier1_check_output")
    if tier1 is None:
        errors.append(
            "tier1_check_output MANDATORY (v1.8.0+). Agent BẮT BUỘC chạy "
            "scripts/tier1_check.py trước và pass output object vào payload. "
            "Lý do: force script chain dependency — agent CANNOT skip Tier 1 verify."
        )
    elif not isinstance(tier1, dict):
        errors.append(
            f"tier1_check_output phải là dict (JSON object output từ tier1_check.py), "
            f"got {type(tier1).__name__}"
        )
    else:
        missing_keys = TIER1_REQUIRED_KEYS - set(tier1.keys())
        if missing_keys:
            errors.append(
                f"tier1_check_output thiếu keys {missing_keys}. "
                f"Output phải từ tier1_check.py (required keys: {TIER1_REQUIRED_KEYS}). "
                f"Got keys: {sorted(tier1.keys())}"
            )

    return errors


# ─── Render parts ───────────────────────────────────────────────────────────
def _render_human_reasoning(payload: Dict[str, Any]) -> str:
    """Part 1 — natural VN reasoning theo skill template.

    Pattern:
        Approve by {user} ({role}). {1-2 câu key context}. Campaign đủ điều kiện duyệt.
    OR:
        Reject by {user} ({role}). {detail lỗi}.
    """
    user = _shortname(payload["approver_email"])
    role = payload["approver_role"]
    action_verb = "Approve" if payload["action"] == "APPROVED" else "Reject"
    reasoning = payload["reasoning_vn"].strip().rstrip(".")

    if payload["action"] == "APPROVED":
        return f"{action_verb} by {user} ({role}). {reasoning}. Campaign đủ điều kiện duyệt."
    else:
        return f"{action_verb} by {user} ({role}). {reasoning}."


def _render_structured_log(payload: Dict[str, Any]) -> str:
    """Part 2 — `[AI-REVIEW v1.2]` structured key=value codes.

    Format: [AI-REVIEW v1.2] key1=val1 | key2=val2 | ...
    Marker is preamble (SPACE-separated from first field), pipes between fields only.
    """
    fields = []

    # Core fields
    fields.append(f"ai_verdict={payload['ai_verdict']}")
    action_label = "APPROVE" if payload["action"] == "APPROVED" else "REJECT"
    fields.append(f"action={action_label}")

    # Optional fields
    if payload.get("score_t1") is not None:
        fields.append(f"score_t1={payload['score_t1']}")
    if payload.get("score_t2") is not None:
        fields.append(f"score_t2={payload['score_t2']}")

    if payload.get("override") is True:
        fields.append("override=true")
        if payload.get("just"):
            fields.append(f"just={payload['just']}")

    if payload.get("tags"):
        tags_str = ",".join(payload["tags"])
        fields.append(f"trg={tags_str}")

    if payload["action"] == "APPROVED":
        fields.append(f"priority={payload['priority']}")

    if payload.get("reviewer_team"):
        fields.append(f"team={payload['reviewer_team']}")

    fields.append(f"ts={iso_now_vn()}")

    return "[AI-REVIEW v1.2] " + " | ".join(fields)


def _render_audit_footer(payload: Dict[str, Any]) -> str:
    """Part 3 — audit footer schema v2 (AI Agreement tracking)."""
    parts = []
    parts.append(f"[ai_verdict={payload['ai_verdict']}]")
    parts.append(f"[ai_agreement={payload['ai_agreement']}]")

    # Optional fields theo schema v2
    if "offline_review" in payload:
        parts.append(f"[offline_review={payload['offline_review']}]")
    if payload.get("review_note"):
        parts.append(f"[review_note={payload['review_note']}]")
    if payload.get("reviewer_team"):
        parts.append(f"[reviewer_team={payload['reviewer_team']}]")
    if payload.get("ai_agreement") == "no" and payload.get("disagree_reason"):
        parts.append(f"[disagree_reason={payload['disagree_reason']}]")

    return "—— " + " ".join(parts)


# ─── Main render ────────────────────────────────────────────────────────────
def render_comment(payload: Dict[str, Any]) -> str:
    """Render canonical 3-part Athena comment.

    Format:
        {Human reasoning natural VN}
        ---
        {Structured log key=value}
        —— {Audit footer schema v2}
    """
    # Validate first
    errors = _validate(payload)
    if errors:
        raise ValueError("Schema validation failed:\n  - " + "\n  - ".join(errors))

    human = _render_human_reasoning(payload)
    log = _render_structured_log(payload)
    footer = _render_audit_footer(payload)

    return f"{human}\n---\n{log}\n{footer}"


# ─── CLI ────────────────────────────────────────────────────────────────────
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
        description="Render canonical Phase 5 Athena comment template."
    )
    parser.add_argument("--json", help="Inline JSON string")
    parser.add_argument("--file", help="Path đến file JSON")
    args = parser.parse_args()

    # Force UTF-8 output even on Windows cp1252 (đặt sớm để lỗi cũng ra UTF-8).
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    # v1.12.2: LUÔN exit 0 + lỗi (FULL) ra STDOUT — sandbox skill_script coi exit≠0
    # là fail và vứt stdout (chỉ giữ ~500 ký tự stderr). Consumer phân biệt:
    # output bắt đầu bằng "ERROR:" = fail → build lại payload; ngược lại = comment.
    def _fail(msg: str) -> None:
        print(f"ERROR: {msg}")
        sys.exit(0)

    try:
        payload = _load_input(args)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        _fail(f"Input parse failed: {e}")

    try:
        comment = render_comment(payload)
    except ValueError as e:
        _fail(f"Schema validation FAIL:\n{e}")
    except Exception as e:
        _fail(f"Render failed: {type(e).__name__}: {e}")

    print(comment)
    sys.exit(0)


if __name__ == "__main__":
    main()
