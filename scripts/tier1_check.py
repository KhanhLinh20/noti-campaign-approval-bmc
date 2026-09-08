#!/usr/bin/env python3
"""tier1_check.py — Noti Campaign Tier 1 hard rule check (deterministic).

Usage:
    # Stdin JSON (recommended cho skill agent invoke):
    cat campaign.json | python scripts/tier1_check.py

    # Direct arg:
    python scripts/tier1_check.py --json '{"name":"...","variants":{...}}'

    # File:
    python scripts/tier1_check.py --file campaign.json

Input schema: Athena get_campaign_detail response (full campaign object).
    Required fields:
        - variants.control.caption (title)
        - variants.control.body
        - variants.control.notification_reference.{ref_id, content_type}
        - variants.control.extra.extra (JSON string với form_id cho SURVEY)
        - segment.{name, size}
        - service_category.{service_group, service_type}
        - notification_config.{allow_in_app, allow_out_app, store_noti}

Output: JSON
    {
      "passed": bool,           # overall — no hard block + no hitl
      "hard_block": bool,       # Tier A — Reject required
      "hitl_required": bool,    # Tier C / dual review
      "issues": [
        {"rule": "X.Y", "severity": "error|hitl|warning", "message": "...", ...}
      ],
      "tags": ["big_segment", "refid_not_in_whitelist", ...],
      "metadata": {
        "title_len": int,
        "body_len": int,
        "segment_size": int,
        "content_type": str,
        "group": str,
      }
    }

Exit codes:
    0 — passed (no hard block)
    1 — hard block (REJECT required)
    2 — HITL required (no hard block but needs review)
    99 — script error (invalid input, etc.)

Skill agent flow (per skill/noti-campaign-approval.md Phase 2):
    1. Fetch campaign via mcp__Noti_MCP__*___get_campaign_detail
    2. Pipe response → tier1_check.py
    3. Parse output:
       - hard_block=true → verdict NOT_QUALIFIED (Tier A)
       - hitl_required=true → verdict HITL_REQUIRED (collect tags + route team)
       - passed=true → continue Tier 2 LLM judge
    4. NEVER do Tier 1 check via LLM reasoning — script is source of truth.

Sync: references/ (13 rule files, v1.16+)
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

# Force UTF-8 stdout (Windows cp1252 fix)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", line_buffering=True)

# Ensure sibling modules importable when run from skill root
_DIR = Path(__file__).parent
sys.path.insert(0, str(_DIR))

from rules import (
    rule_1_1_ct_valid,
    rule_2_1_title_length, rule_2_2_body_length, rule_2_3_no_newline,
    rule_2_4_pii, rule_2_6_param_whitelist, rule_2_8_test_content,
    rule_2_10_format, rule_2_12_image_outapp_advisory, rule_2_13_gift_card_reminder_advisory,
    rule_5_1_segment_size, rule_6_5_survey_validation,
    get_group, is_quan_trong, strip_placeholders, get_text_char_count,
)
from banned_phrases import check_rule_2_11
from refid_glossary import check_rule_1_8
from brand import check_rule_2_14
from segment_audit import audit_segment_conditions, segment_compliance_scorecard
from detect_domain import detect_domains
from rule_descriptions import to_user_message, tag_to_user_message, issues_to_user_summary


def _extract_fields(campaign: dict) -> dict:
    """Extract fields cần thiết từ Athena campaign response."""
    variants = campaign.get("variants", {}) or {}
    control = variants.get("control", {}) or {}
    treatment = variants.get("treatment", {}) or {}
    noti_ref = control.get("notification_reference", {}) or {}
    segment = campaign.get("segment", {}) or {}
    notif_config = campaign.get("notification_config", {}) or {}
    service_category = campaign.get("service_category", {}) or {}

    # form_id nested trong control.extra.extra (JSON string cho SURVEY)
    form_id = ""
    extra_str = (control.get("extra", {}) or {}).get("extra", "")
    if isinstance(extra_str, dict):
        form_id = extra_str.get("form_id", "") or ""
    elif isinstance(extra_str, str) and extra_str:
        try:
            extra_obj = json.loads(extra_str)
            form_id = (extra_obj or {}).get("form_id", "") or ""
        except json.JSONDecodeError:
            form_id = ""

    return {
        "title": control.get("caption", "") or "",
        "body": control.get("body", "") or "",
        # Biến thể treatment (A/B test) — v-bmc: Tier 1 check CẢ 2 variant, không chỉ control.
        "treatment_title": treatment.get("caption", "") or "",
        "treatment_body": treatment.get("body", "") or "",
        "has_treatment": bool(treatment.get("caption") or treatment.get("body")),
        # v-bmc: campaign có KHAI là A/B không (để bắt case khai A/B nhưng treatment trống).
        "message_type": (campaign.get("message_type", "") or "").upper(),
        "declared_ab": (
            (campaign.get("message_type", "") or "").upper() == "AB_TEST"
            or "treatment" in variants
        ),
        "ref_id": noti_ref.get("ref_id", "") or "",
        "content_type": (noti_ref.get("content_type", "") or "").upper(),
        "segment_size": int(segment.get("size", 0) or 0),
        "segment_name": segment.get("name", "") or "",
        "notification_config": notif_config,
        "campaign_name": campaign.get("name", "") or "",
        "status": campaign.get("status", "") or "",
        "service_group": service_category.get("service_group", "") or "",
        "service_type": service_category.get("service_type", "") or "",
        # v-bmc: push date & time — trong API là 1 field push_time (epoch ms). "0"/"" = chưa đặt lịch.
        "push_time": str((campaign.get("schedule_config", {}) or {}).get("push_time", "") or "").strip(),
        "schedule_type": ((campaign.get("schedule_config", {}) or {}).get("schedule_type", "") or "").upper(),
        "form_id": form_id,
        "extra": control.get("extra", {}) or {},   # variant.extra (image_url, button_cta1/2)
        # Rule 5.3 (v1.17+) — conditionV2 từ segment-mcp athena-get-segment-info (optional inject).
        # Agent fetch get-segment-info → lấy conditionV2 → đặt vào 1 trong các path dưới.
        "condition_v2": (
            campaign.get("segment_condition_v2")
            or segment.get("condition_v2")
            or segment.get("conditionV2")
            or None
        ),
        # Rule 5.6 (BMC 9.0) — dataSource segment (['ATTRIBUTE','BIGQUERY']...) để detect hành vi.
        "segment_data_source": (
            campaign.get("segment_data_source")
            or segment.get("data_source")
            or segment.get("dataSource")
            or []
        ),
    }


# ── Tier 1 scoring (v-bmc) ───────────────────────────────────────────────────
# Tier 1 giờ trả ĐIỂM 0–100 (như Tier 2), tính deterministic từ severity của issues.
# Penalty theo severity; routing exception (rule "Tier D": Quan trọng/SURVEY/EVENT)
# KHÔNG bị trừ (là phân luồng, không phải lỗi nội dung). Band theo ngưỡng BMC.
_TIER1_PENALTY = {"error": 55, "hitl": 15, "warning": 8}


def _compute_tier1_score(issues: list, advisories: list, hard_block: bool) -> int:
    total = 0
    for it in issues:
        if it.get("rule") == "Tier D":   # routing, không phải defect nội dung → không trừ
            continue
        # issue có thể set `penalty` riêng (vd A/B thiếu variant); mặc định theo severity.
        total += it.get("penalty", _TIER1_PENALTY.get(it.get("severity"), 8))
    total += 3 * len(advisories)
    score = max(0, min(100, 100 - total))
    if hard_block:
        score = min(score, 40)   # có hard rule vi phạm → ép vào band REJECT (<50)
    return score


def _band_of(score: int) -> str:
    """Ngưỡng BMC: PASS ≥ 85 · WARNING 50–84 · REJECT < 50."""
    if score < 50:
        return "REJECT"
    if score <= 84:
        return "WARNING"
    return "PASS"


def _text_checks(title: str, body: str, is_qt: bool, variant: str) -> dict:
    """Chạy các hard-check cấp NỘI DUNG cho 1 variant (control/treatment).

    Tách riêng để check được CẢ 2 biến thể A/B. Mỗi issue gắn `variant` để log rõ.
    Các check cấp campaign (1.1 CT, 2.10 format, refid, segment, survey, routing…)
    KHÔNG nằm đây — chạy 1 lần ở check_campaign.
    """
    issues, tags = [], []
    hard_block = hitl_required = False

    for check in [
        rule_2_1_title_length(title),
        rule_2_2_body_length(body),
        rule_2_3_no_newline(body),
        rule_2_4_pii(title, body),          # PII = luôn hard block
        rule_2_6_param_whitelist(title, body),
        rule_2_8_test_content(title, body),
        check_rule_2_14(title, body),       # Brand integrity
    ]:
        if check["passed"]:
            continue
        rule = check["rule"]
        check["variant"] = variant
        if rule == "2.4":
            hard_block = True
            issues.append(check)
        elif is_qt and rule in ("2.1", "2.2", "2.3", "2.6"):
            check["severity"] = "hitl"
            check["note_rule_2_7"] = "Quan trọng format violation → HITL (Rule 2.7), không reject"
            hitl_required = True
            issues.append(check)
        else:
            hard_block = True
            issues.append(check)

    # Rule 2.11 — Banned phrases (cấp nội dung)
    bp = check_rule_2_11(title, body)
    if not bp["passed"]:
        bp["variant"] = variant
        sev = bp["severity"]
        if sev == "error":
            hard_block = True
            issues.append(bp)
            tags.append(bp.get("tag", "banned_phrase_blocker"))
        elif sev == "hitl":
            hitl_required = True
            issues.append(bp)
            tags.append(bp.get("tag", "banned_phrase_critical"))
        else:
            issues.append(bp)
            tags.append(bp.get("tag", "banned_phrase_warning"))

    return {"issues": issues, "tags": tags,
            "hard_block": hard_block, "hitl_required": hitl_required}


def check_campaign(campaign: dict, mode: str = "review") -> dict:
    """Run all Tier 1 hard rule checks. Return aggregated result."""
    f = _extract_fields(campaign)

    # ─── Template variables & character counting (v1.11.3+) ──────────────────
    # Athena stores/returns the template STRING with placeholders intact
    # (e.g. caption = "${lastname} ơi, ..."), rendering ${lastname}/${fullname}
    # only at send time. So NO reverse-substitution is needed: the length rules
    # (2.1/2.2) and metadata char counts simply strip ${...} (= 0 chars per rule)
    # via strip_placeholders(). Reverse-sub was removed — it wrongly assumed
    # pre-rendered input and could convert literal words back into placeholders.

    issues = []
    tags = []
    hard_block = False
    hitl_required = False

    is_quan_trong_group = is_quan_trong(f["content_type"])

    # ─── REQ.1 (v-bmc) — trường bắt buộc BỎ TRỐNG → HITL ─────────────────────
    # Campaign Name · Service Group · Content Type · Push date · Push time.
    # (Push date & time trong API là 1 field push_time; "0"/"" = chưa đặt lịch.)
    _push_missing = f["push_time"] in ("", "0")
    _required = [
        ("Campaign Name", f["campaign_name"]),
        ("Service Group", f["service_group"]),
        ("Content Type", f["content_type"]),
        ("Push date", "" if _push_missing else f["push_time"]),
        ("Push time", "" if _push_missing else f["push_time"]),
    ]
    for name, val in _required:
        if str(val).strip():
            continue
        hitl_required = True
        tags.append("required_field_empty")
        issues.append({
            "rule": "REQ.1", "passed": False, "severity": "hitl", "penalty": 20,
            "variant": "campaign", "field": name,
            "message": f"Trường bắt buộc '{name}' bỏ trống → cần HITL xác nhận.",
            "user_message": f"Thiếu thông tin bắt buộc: {name} — cần người duyệt bổ sung/xác nhận.",
            "tag": "required_field_empty",
        })

    # ─── Campaign-level hard checks (chạy 1 lần, không theo variant) ──────────
    # Content Type: RỖNG = thiếu field (đã HITL ở REQ.1) → KHÔNG hard_block.
    # Chỉ hard_block khi CT có giá trị nhưng SAI (không hợp lệ).
    ct_check = rule_1_1_ct_valid(f["content_type"], mode)
    if not ct_check["passed"] and f["content_type"].strip():
        ct_check["variant"] = "campaign"
        hard_block = True
        issues.append(ct_check)

    fmt_check = rule_2_10_format(f["notification_config"])
    if not fmt_check["passed"]:
        fmt_check["variant"] = "campaign"
        hard_block = True
        issues.append(fmt_check)

    # ─── Content hard checks — CHẠY CHO CẢ control VÀ treatment (A/B) ─────────
    # (v-bmc fix: trước đây chỉ check control → treatment có lỗi vẫn lọt.)
    def _merge(res):
        nonlocal hard_block, hitl_required
        issues.extend(res["issues"])
        tags.extend(res["tags"])
        hard_block = hard_block or res["hard_block"]
        hitl_required = hitl_required or res["hitl_required"]

    _merge(_text_checks(f["title"], f["body"], is_quan_trong_group, "control"))
    if f["has_treatment"]:
        _merge(_text_checks(f["treatment_title"], f["treatment_body"],
                            is_quan_trong_group, "treatment"))

    # ─── A/B completeness (v-bmc) — khai A/B nhưng treatment TRỐNG/THIẾU → HITL ─
    # Bắt case campaign message_type=AB_TEST mà biến thể 2 để trống (không được auto-approve).
    if f["declared_ab"]:
        tt = strip_placeholders(f["treatment_title"]).strip()
        tb = strip_placeholders(f["treatment_body"]).strip()
        miss = ("cả title lẫn body" if (not tt and not tb)
                else "title" if not tt
                else "body" if not tb
                else "")
        if miss:
            hitl_required = True
            tags.append("ab_variant_incomplete")
            issues.append({
                "rule": "AB.1", "passed": False, "severity": "hitl", "penalty": 40,
                "variant": "treatment",
                "message": f"A/B test (message_type={f['message_type'] or 'AB'}) nhưng biến thể "
                           f"treatment thiếu {miss} → cần HITL xác nhận, không auto-approve.",
                "user_message": f"A/B Test nhưng nội dung thứ 2 (treatment) thiếu {miss} "
                                f"— cần người duyệt xác nhận.",
                "tag": "ab_variant_incomplete",
            })

    # ─── Rule 1.8 — RefID glossary ───────────────────────────────────────────
    refid_check = check_rule_1_8(f["ref_id"])
    if not refid_check["passed"]:
        hitl_required = True
        issues.append(refid_check)
        tags.append(refid_check.get("tag", "refid_not_in_whitelist"))

    # ─── Rule 5.1 — Segment size cap ─────────────────────────────────────────
    seg_check = rule_5_1_segment_size(f["segment_size"], f["content_type"])
    if not seg_check["passed"]:
        if seg_check["severity"] == "error":   # SURVEY hard cap 250K
            hard_block = True
            issues.append(seg_check)
        else:   # HITL (dual review > 5M general)
            hitl_required = True
            issues.append(seg_check)
            tags.append(seg_check.get("tag", "big_segment"))

    # ─── Rule 6.5 — SURVEY validation (5 hard checks) ────────────────────────
    survey_issues = rule_6_5_survey_validation(f)
    for s in survey_issues:
        hard_block = True
        issues.append(s)

    # ─── Rule 2.12 — Image out-app advisory (NOT hard block) ─────────────────
    advisories = []
    img_check = rule_2_12_image_outapp_advisory(f["extra"], f["notification_config"])
    if img_check.get("advisory"):
        advisories.append(img_check)
        tags.append("image_outapp_review")

    # ─── Rule 2.13 — Gift card reminder pattern (HITL trigger, KHÔNG hard block) ─
    gift_check = rule_2_13_gift_card_reminder_advisory(
        f["title"], f["body"], f["ref_id"], f["content_type"]
    )
    if gift_check.get("advisory"):
        hitl_required = True   # force HITL bất kể score
        issues.append(gift_check)
        tags.append(gift_check.get("tag", "gift_card_reminder_duplicate_risk"))

    # ─── Tier D — Exception routing (HITL_REQUIRED dù score ≥ 85) ────────────
    # Quan trọng group → PCS bắt buộc HITL
    if is_quan_trong_group:
        hitl_required = True
        tags.append("quan_trong_pcs_routing")
        issues.append({
            "rule": "Tier D",
            "passed": False,
            "severity": "hitl",
            "message": f"Group Quan trọng (CT={f['content_type']}) → PCS bắt buộc review (Tier D).",
            "tag": "quan_trong_pcs_routing",
        })

    # SURVEY → CIO bắt buộc, không auto-schedule
    if f["content_type"] == "SURVEY":
        hitl_required = True
        tags.append("survey_cio_routing")
        issues.append({
            "rule": "Tier D",
            "passed": False,
            "severity": "hitl",
            "message": "content_type=SURVEY → CIO bắt buộc review (Tier D).",
            "tag": "survey_cio_routing",
        })

    # EVENT → BMC thematic confirm
    if f["content_type"] == "EVENT":
        hitl_required = True
        tags.append("event_thematic_required")
        issues.append({
            "rule": "Tier D",
            "passed": False,
            "severity": "hitl",
            "message": "content_type=EVENT → BMC thematic confirm (Rule 1.7).",
            "tag": "event_thematic_required",
        })

    # ─── Domain detection (v1.4.0+) — return guardrails để Tier 2 LLM load ───
    domains = detect_domains(f["title"], f["body"], f["content_type"])

    # ─── Rule 5.3 + 5.5 (v1.17/1.18+) — Segment condition audit ──────────────
    # Chỉ chạy khi agent đã inject conditionV2 (từ athena-get-segment-info). 5.3.C/D = Tier 2 LLM.
    segment_scorecard = None
    if f.get("condition_v2"):
        ds = f.get("segment_data_source")
        for si in audit_segment_conditions(f["condition_v2"], f["content_type"], domains, ds):
            sev = si["severity"]
            if sev == "error":
                hard_block = True
            elif sev == "hitl":
                hitl_required = True
            # "warning" (vd 5.5 staff, 5.6 ct-behavior) → chỉ append, không block/HITL
            issues.append(si)
            if si.get("tag"):
                tags.append(si["tag"])
        # Scorecard hiển thị cho approver (đạt/chưa đạt + lý do) — so rule BMC/CIO
        segment_scorecard = segment_compliance_scorecard(
            f["condition_v2"], f["content_type"], domains, f["segment_size"], ds
        )

    # ─── Enrich issues với user_message (v1.4.3+ — Principle #8) ─────────────
    # Agent dùng user_message khi render batch report / Phase 5 comment / dashboard.
    # KHÔNG dùng `message` (chứa rule code) cho user-facing output.
    for issue in issues:
        rule = issue.get("rule", "")
        sev = issue.get("severity")
        # Ưu tiên user_message cụ thể đã set trên issue (vd AB.1); nếu chưa có mới map theo rule.
        issue["user_message"] = (
            issue.get("user_message") or to_user_message(rule, sev) or issue.get("message", "")
        )

    # User-friendly summary cho batch report "Lý do không đạt" column
    user_summary = issues_to_user_summary(issues, sorted(set(tags)))

    # ─── Tier 1 score (v-bmc) — điểm 0–100 do script tính, KHÔNG áng chừng ───
    tier1_score = _compute_tier1_score(issues, advisories, hard_block)
    tier1_band = _band_of(tier1_score)

    return {
        "passed": (not hard_block) and (not hitl_required),
        "hard_block": hard_block,
        "hitl_required": hitl_required,
        "tier1_score": tier1_score,      # v-bmc: điểm deterministic 0–100 (như Tier 2)
        "tier1_band": tier1_band,        # PASS ≥85 · WARNING 50–84 · REJECT <50
        "issues": issues,                # mỗi item có: rule + message (technical) + user_message (VN) + variant
        "advisories": advisories,        # v1.4.8+ — không block, approver visual review (vd image_url)
        "segment_scorecard": segment_scorecard,  # v1.18+ — checklist segment vs rule BMC/CIO (đạt/chưa đạt + lý do)
        "tags": sorted(set(tags)),
        "user_summary": user_summary,    # v1.4.3+ — natural VN cho batch report column
        "domains_to_load": domains,
        "metadata": {
            "campaign_name": f["campaign_name"],
            "status": f["status"],
            "title_len": get_text_char_count(f["title"]),   # ${...} = 0 chars (Rule 2.1) — control — single source of truth
            "body_len": get_text_char_count(f["body"]),      # ${...} = 0 chars (Rule 2.2) — control — single source of truth
            # v-bmc: độ dài treatment (A/B) + độ phủ variant đã check
            "treatment_title_len": (get_text_char_count(f["treatment_title"]) if f["has_treatment"] else None),
            "treatment_body_len": (get_text_char_count(f["treatment_body"]) if f["has_treatment"] else None),
            "variants_checked": (["control", "treatment"] if f["has_treatment"] else ["control"]),
            "segment_size": f["segment_size"],
            "content_type": f["content_type"],
            "group": get_group(f["content_type"]),
            "image_url": (f["extra"].get("image_url") or "").strip(),   # v1.4.8+ — cho Phase 3 batch report column
        },
    }


def _strip_bom(text: str) -> str:
    """Bỏ UTF-8 BOM ở đầu chuỗi (PowerShell/Windows hay chèn khi pipe)."""
    return text.lstrip("﻿") if text else text


def _load_input(args) -> dict:
    """Load campaign JSON từ --json, --file, hoặc stdin. BOM-safe."""
    if args.json:
        return json.loads(_strip_bom(args.json))
    if args.file:
        # utf-8-sig tự bỏ BOM nếu file có
        with open(args.file, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    # Default: stdin — đọc raw rồi strip BOM trước khi parse
    return json.loads(_strip_bom(sys.stdin.read()))


def _unwrap_campaign(obj):
    """Auto-unwrap 1 campaign khỏi các wrapper phổ biến — FLAG-FREE.

    Sandbox skill_script KHÔNG truyền được argv flag (--unwrap), và giới hạn 16 key
    inputs top-level. Nên agent bọc campaign trong 1 key: inputs={"campaign": {...}}.
    Hàm này nhận cả 2 wrapper mà không cần cờ:
      {"campaign": {...}}  → skill_script convention (né limit 16 key)
      {"status","data"}    → Athena MCP response wrapper
    Object campaign thật (có `variants`) thì trả nguyên.
    """
    if isinstance(obj, dict):
        if isinstance(obj.get("campaign"), dict):
            return obj["campaign"]
        if isinstance(obj.get("data"), dict) and "variants" not in obj:
            return obj["data"]
    return obj


def _verdict_of(result: dict):
    """(verdict_string, legacy_exit_code) từ 1 result. exit code giờ nằm trong JSON."""
    if result.get("hard_block"):
        return "NOT_QUALIFIED", 1
    if result.get("hitl_required"):
        return "HITL_REQUIRED", 2
    return "PASS", 0


def main():
    parser = argparse.ArgumentParser(
        description="Tier 1 hard rule check cho Noti Campaign (deterministic, no LLM)."
    )
    parser.add_argument("--json", help="Inline JSON string của campaign")
    parser.add_argument("--file", help="Path đến file JSON")
    parser.add_argument(
        "--mode", choices=["review", "create"], default="review",
        help="review=14 valid CTs (default), create=6 CTs restrict"
    )
    parser.add_argument(
        "--pretty", action="store_true",
        help="Pretty-print output JSON (default: compact)"
    )
    parser.add_argument(
        "--unwrap", action="store_true",
        help="Input là Athena MCP response (có wrapping `{status, data}`) → unwrap `data` trước khi check"
    )
    parser.add_argument(
        "--batch", action="store_true",
        help="Batch mode (v1.5.0+): input là {\"campaigns\": [...]} → output {\"batch\": true, \"results\": [...]}. Save Python startup overhead khi check nhiều campaigns."
    )
    args = parser.parse_args()

    # Ép UTF-8 output — tránh UnicodeEncodeError trên console Windows (cp1252).
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    try:
        raw = _load_input(args)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(json.dumps({"error": f"Input parse failed: {e}", "exit_code": 99}), file=sys.stderr)
        sys.exit(99)

    indent = 2 if args.pretty else None

    # ─── BATCH MODE (v1.5.0+) ────────────────────────────────────────────────
    # Input shape: {"campaigns": [campaign1, campaign2, ...]} or
    #              {"campaigns": [{status, data}, ...]} when --unwrap
    # Output: {"batch": true, "count": N, "results": [result1, result2, ...]}
    # Exit code: 0 (all pass) / 1 (any hard_block) / 2 (any hitl) / 99 (error)
    # Auto-detect batch (flag-free): {"campaigns": [...]} → batch, kể cả khi
    # bọc trong {"campaign": {"campaigns":[...]}} hay {"data": {...}}.
    unwrapped = _unwrap_campaign(raw)
    is_batch = args.batch or (isinstance(unwrapped, dict) and isinstance(unwrapped.get("campaigns"), list))

    if is_batch:
        base = unwrapped if isinstance(unwrapped, dict) else raw
        campaigns_raw = base.get("campaigns") if isinstance(base, dict) else base
        if not isinstance(campaigns_raw, list):
            # exit 0 + error trong JSON — sandbox coi exit≠0 là fail và vứt stdout.
            print(json.dumps({"error": "Batch mode requires {\"campaigns\": [...]} array",
                              "verdict": "ERROR", "exit_code": 99}, ensure_ascii=False))
            sys.exit(0)

        results = []
        any_hard_block = False
        any_hitl = False
        for idx, raw_item in enumerate(campaigns_raw):
            campaign = _unwrap_campaign(raw_item)
            try:
                r = check_campaign(campaign, mode=args.mode)
                v, _ = _verdict_of(r)
                r["verdict"] = v
                results.append(r)
                if r["hard_block"]: any_hard_block = True
                if r["hitl_required"]: any_hitl = True
            except Exception as e:
                results.append({
                    "error": f"Check failed at index {idx}: {type(e).__name__}: {e}",
                    "verdict": "ERROR",
                    "campaign_name": (campaign.get("name", "") if isinstance(campaign, dict) else ""),
                })

        # exit_code giờ là FIELD trong JSON (worst-case), KHÔNG phải process exit.
        batch_code = 1 if any_hard_block else (2 if any_hitl else 0)
        batch_verdict = "NOT_QUALIFIED" if any_hard_block else ("HITL_REQUIRED" if any_hitl else "PASS")
        output = {"batch": True, "count": len(results), "results": results,
                  "verdict": batch_verdict, "exit_code": batch_code}
        print(json.dumps(output, indent=indent, ensure_ascii=False))
        sys.exit(0)   # LUÔN 0 — giữ stdout cho skill_script (exit≠0 = mất JSON)

    # ─── SINGLE MODE ─────────────────────────────────────────────────────────
    campaign = unwrapped

    try:
        result = check_campaign(campaign, mode=args.mode)
    except Exception as e:
        print(json.dumps({"error": f"Check failed: {type(e).__name__}: {e}",
                          "verdict": "ERROR", "exit_code": 99}, ensure_ascii=False))
        sys.exit(0)

    # Verdict + exit_code nằm TRONG JSON (đọc `.verdict`/`.exit_code`), KHÔNG dựa
    # process exit — vì sandbox skill_script coi exit≠0 là fail và bỏ stdout.
    v, code = _verdict_of(result)
    result["verdict"] = v
    result["exit_code"] = code
    print(json.dumps(result, indent=indent, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
