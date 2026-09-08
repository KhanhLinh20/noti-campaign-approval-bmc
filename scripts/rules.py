"""Per-rule check functions — pure deterministic.

Each function returns dict:
    {"rule": "X.Y", "passed": bool, "severity": "error|warning|info", "message": str}

Sync: references/ (13 rule files)
"""
import math
import re

from constants import (
    TITLE_MAX, BODY_MAX, WHITELIST_PARAMS,
    VALID_CTS, CREATE_MODE_CTS, BLOCKED_FORMATS,
    SEGMENT_MAX_GENERAL, SEGMENT_MAX_SURVEY,
    BU_DAILY_WARNING_THRESHOLD, BU_DAILY_CAP,
    SURVEY_PUSH_CAP_PER_PROJECT, SURVEY_SERVICE_GROUP, SURVEY_SERVICE_TYPE, SURVEY_REF_ID,
    CT_TO_GROUP, QUAN_TRONG_CTS, CT_TO_APPROVER,
    TEST_KEYWORDS, SHANNON_ENTROPY_MIN, PROMO_DIRECT_KEYWORDS,
    GIFT_REMIND_PATTERNS, GIFT_KEYWORDS, REFID_VOUCHER_PATTERNS,
)
from pii import detect_pii

_NEWLINE_RE = re.compile(r"[\n\r]")
_BULLET_RE = re.compile(r"(?m)^\s*[-•*]\s+|^\s*\d+[\.\)]\s+")
_PARAM_RE = re.compile(r"\$\{([^}]*)\}")
_PLACEHOLDER_RE = re.compile(r"\$\{[^}]*\}")  # Strip placeholders for char count
# Accept UUID v4 OR v7 (Survey Public v7+ per RFC 9562, Link Test còn v4).
# Group 3 first char: "4" (v4) HOẶC "7" (v7). Group 4 first char: [89ab] (variant — chung cả v4 + v7).
# Update v1.8.0+ — fix prod failure 10/06/2026 Survey form_id v7 bị false reject.
_UUID_V4_OR_V7_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[47][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
# Alias backward compat — legacy code dùng _UUID_V4_RE.
_UUID_V4_RE = _UUID_V4_OR_V7_RE


def strip_placeholders(text: str) -> str:
    """Remove ${...} placeholders for character counting.

    Athena stores/returns the template STRING (e.g. "${lastname} ơi, ..."),
    rendering placeholders only at send time. Per Rule 2.1/2.2 a placeholder
    counts as 0 chars, so strip it before len(). Single source of truth for
    both the length rules and the metadata char counts in tier1_check.py.
    """
    return _PLACEHOLDER_RE.sub("", text or "")


def get_text_char_count(text: str) -> int:
    """Get accurate char count (strip placeholders). Single source of truth.

    Used by tier1_check.py metadata + char_count.py CLI. Ensures consistent
    character counting across all tools. Never encode-dependent (pure string ops).
    """
    return len(strip_placeholders(text))


def _pass(rule: str) -> dict:
    return {"rule": rule, "passed": True}


def _fail(rule: str, message: str, severity: str = "error") -> dict:
    return {"rule": rule, "passed": False, "severity": severity, "message": message}


# ═════════════════════════════════════════════════════════════════════════════
# Nhóm 1 — Content Type & Format
# ═════════════════════════════════════════════════════════════════════════════

def rule_1_1_ct_valid(content_type: str, mode: str = "review") -> dict:
    """Rule 1.1 — Content type valid.

    review mode: 14 codes valid
    create mode: 6 codes valid (restrict)
    """
    ct = (content_type or "").upper()
    valid_set = CREATE_MODE_CTS if mode == "create" else VALID_CTS
    if ct not in valid_set:
        return _fail(
            "1.1",
            f"content_type='{ct}' không thuộc {len(valid_set)} codes hợp lệ ({mode} mode). "
            f"Valid: {sorted(valid_set)}"
        )
    return _pass("1.1")


# ═════════════════════════════════════════════════════════════════════════════
# Nhóm 2 — Content Hard Checks
# ═════════════════════════════════════════════════════════════════════════════

def rule_2_1_title_length(title: str) -> dict:
    """Rule 2.1 — Title ≤ 30 chars (Unicode).

    Placeholders ${fullname}, ${lastname} do NOT count (stripped before counting).
    """
    # Strip placeholders (${...} = 0 chars per rule)
    n = len(strip_placeholders(title))
    if n > TITLE_MAX:
        return _fail(
            "2.1",
            f"Title {n} ký tự (after placeholder removal) > {TITLE_MAX} (Rule 2.1). Rút gọn còn ≤ {TITLE_MAX}."
        )
    return _pass("2.1")


def rule_2_2_body_length(body: str) -> dict:
    """Rule 2.2 — Body ≤ 120 chars.

    Placeholders ${fullname}, ${lastname} do NOT count (stripped before counting).
    """
    # Strip placeholders (${...} = 0 chars per rule)
    n = len(strip_placeholders(body))
    if n > BODY_MAX:
        return _fail(
            "2.2",
            f"Body {n} ký tự (after placeholder removal) > {BODY_MAX} (Rule 2.2). Rút gọn còn ≤ {BODY_MAX}."
        )
    return _pass("2.2")


def rule_2_3_no_newline(body: str) -> dict:
    """Rule 2.3 — Body không xuống dòng / bullet."""
    if _NEWLINE_RE.search(body or ""):
        return _fail("2.3", "Body chứa ký tự xuống dòng (Rule 2.3). Viết liền mạch.")
    if _BULLET_RE.search(body or ""):
        return _fail("2.3", "Body chứa bullet/numbered list (Rule 2.3). Viết liền mạch.")
    return _pass("2.3")


def rule_2_4_pii(title: str, body: str) -> dict:
    """Rule 2.4 — PII detection (phone/email/CCCD/bank).

    HARD BLOCK — không exception, kể cả group Quan trọng.
    """
    combined = (title or "") + " " + (body or "")
    hits = detect_pii(combined)
    if hits:
        types = ", ".join(sorted({t for t, _ in hits}))
        return _fail("2.4", f"Phát hiện PII ({types}). Vi phạm chính sách bảo mật (Rule 2.4).")
    return _pass("2.4")


def rule_2_6_param_whitelist(title: str, body: str) -> dict:
    """Rule 2.6 — Param whitelist (chỉ ${fullname}, ${lastname})."""
    combined = (title or "") + " " + (body or "")
    found = _PARAM_RE.findall(combined)
    invalid = []
    for p in found:
        # Strict: no leading/trailing whitespace, exact case-sensitive match
        if p != p.strip() or p not in WHITELIST_PARAMS:
            invalid.append(p)
    if invalid:
        invalid_str = ", ".join(f"${{{p}}}" for p in invalid)
        return _fail(
            "2.6",
            f"Param không hợp lệ: {invalid_str}. Chỉ chấp nhận ${{fullname}}, ${{lastname}} (Rule 2.6)."
        )
    return _pass("2.6")


def _shannon_entropy(text: str) -> float:
    if not text:
        return 0.0
    freq: dict[str, int] = {}
    for c in text:
        freq[c] = freq.get(c, 0) + 1
    n = len(text)
    return -sum((cnt / n) * math.log2(cnt / n) for cnt in freq.values() if cnt > 0)


def rule_2_8_test_content(title: str, body: str) -> dict:
    """Rule 2.8 — Block test/placeholder/gibberish content."""
    combined = ((title or "") + " " + (body or "")).lower().strip()

    # Keyword check
    for kw in TEST_KEYWORDS:
        # Word boundary match (avoid false positive on substring)
        if re.search(rf"\b{re.escape(kw)}\b", combined):
            return _fail(
                "2.8",
                f"Phát hiện test keyword '{kw}' (Rule 2.8). Không submit content test/placeholder."
            )

    # Shannon entropy — gibberish detection (chỉ áp dụng khi text đủ dài)
    if len(combined) > 10:
        entropy = _shannon_entropy(combined)
        if entropy < SHANNON_ENTROPY_MIN:
            return _fail(
                "2.8",
                f"Content entropy {entropy:.2f} < {SHANNON_ENTROPY_MIN} — gibberish detected (Rule 2.8)."
            )

    return _pass("2.8")


def rule_2_10_format(notification_config: dict) -> dict:
    """Rule 2.10 — Format check (must be out-app push, no in-app/header/popup/...).

    Input: notification_config dict từ Athena response.
    Expected: allow_out_app=True, allow_in_app=False, store_noti=True
    """
    nc = notification_config or {}
    if nc.get("allow_in_app") is True:
        return _fail(
            "2.10",
            "Format vi phạm: allow_in_app=TRUE (Rule 2.10). Noti Campaign chỉ dùng out-app push."
        )
    if nc.get("allow_out_app") is False:
        return _fail(
            "2.10",
            "Format vi phạm: allow_out_app=FALSE (Rule 2.10). Phải bật out-app push."
        )
    return _pass("2.10")


def rule_2_12_image_outapp_advisory(extra: dict, notification_config: dict) -> dict:
    """Rule 2.12 — Image out-app advisory (NOT a hard block).

    Khi campaign có image_url + allow_out_app=True → emit advisory để approver
    visual-check hình ảnh trước khi APPROVE. Lý do: icon nhỏ (vd 600x400)
    có thể bị iOS render full screen ở out-app push notification, gây UX lỗi
    (ảnh stretch / dominate notification).

    Input:
        extra: variant.extra dict (chứa image_url)
        notification_config: campaign-level config

    Output: {"rule": "2.12", "passed": True, "advisory": True, ...} khi có image,
            hoặc _pass("2.12") khi không có image.

    Severity: ADVISORY (không hard block, không degrade score).
    Approver tự visual review qua link và quyết định.
    """
    ex = extra or {}
    nc = notification_config or {}
    image_url = (ex.get("image_url") or "").strip()
    out_app_on = nc.get("allow_out_app") is True

    if image_url and out_app_on:
        return {
            "rule": "2.12",
            "passed": True,
            "advisory": True,
            "severity": "info",
            "image_url": image_url,
            "message": (
                f"Có hình ảnh out-app — click link review trước khi duyệt: {image_url}"
            ),
        }
    return _pass("2.12")


def rule_2_13_gift_card_reminder_advisory(title: str, body: str, ref_id: str,
                                            content_type: str) -> dict:
    """Rule 2.13 (v1.18+) — Gift card reminder pattern detection (HITL trigger).

    Detect content pattern "remind dùng thẻ quà / voucher" và force HITL flag
    để approver verify KHÔNG duplicate với ML Promotion remind tự động bên đầu kia.

    Apply: ANY content_type (KHÔNG limit REMIND only) — pattern này có thể xuất
    hiện ở mọi CT khi BU dùng sai routing.

    Routing: FOLLOW CT default (không override):
        - CT=REMIND (Quan trọng) → HITL PCS
        - CT=PROMOTION* (Ưu đãi) → HITL BMC bất kể score
        - CT khác → HITL theo CT_TO_APPROVER mapping

    Logic: AND 3 signals — all phải match để giảm false positive
        Signal 1: remind-style language ("bạn còn", "đã sẵn sàng", ...)
        Signal 2: gift/voucher keywords ("thẻ quà", "voucher", "quà sinh nhật", ...)
        Signal 3: ref_id signals voucher detail page ("voucher_detail", ...)

    Input:
        title, body: campaign content text
        ref_id: notification_reference.ref_id
        content_type: CT (uppercase normalized)

    Output: {"rule": "2.13", "passed": True, "severity": "hitl", "tag": ..., ...}
            khi 3 signals match; _pass("2.13") otherwise.

    Severity: HITL (force human review, KHÔNG hard block, KHÔNG degrade score).
    """
    text = ((title or "") + " " + (body or "")).lower().strip()
    rid = (ref_id or "").lower().strip()

    if not text or not rid:
        return _pass("2.13")

    # Signal 1: remind-style language
    has_remind_lang = any(p in text for p in GIFT_REMIND_PATTERNS)
    # Signal 2: gift/voucher keywords
    has_gift_kw = any(k in text for k in GIFT_KEYWORDS)
    # Signal 3: ref_id signals voucher page
    has_refid_signal = rid in REFID_VOUCHER_PATTERNS

    # AND logic — all 3 signals must match
    if has_remind_lang and has_gift_kw and has_refid_signal:
        return {
            "rule": "2.13",
            "passed": True,
            "advisory": True,
            "severity": "hitl",
            "tag": "gift_card_reminder_duplicate_risk",
            "message": (
                "Pattern phát hiện: Nội dung có chứa remind voucher, cần human review"
            ),
            "user_message": (
                "Pattern phát hiện: Nội dung có chứa remind voucher, cần human review"
            ),
        }

    return _pass("2.13")


# ═════════════════════════════════════════════════════════════════════════════
# Nhóm 5 — Segment
# ═════════════════════════════════════════════════════════════════════════════

def rule_5_1_segment_size(segment_size: int, content_type: str) -> dict:
    """Rule 5.1 — Segment size cap.

    SURVEY: hard cap 250K (Rule 6.5 actually, dual-tracked)
    Others: > 5M → dual HITL (Growth + content-group approver), không hard block
    """
    ct = (content_type or "").upper()
    n = int(segment_size or 0)

    # SURVEY: hard cap (Rule 6.5)
    if ct == "SURVEY":
        if n > SEGMENT_MAX_SURVEY:
            return _fail(
                "6.5",
                f"SURVEY segment {n:,} user > cap {SEGMENT_MAX_SURVEY:,} (Rule 6.5). "
                "SURVEY có hard cap 250K, không thể vượt."
            )
        return _pass("5.1")

    # General: > 5M → dual HITL (KHÔNG hard block, return HITL trigger)
    if n > SEGMENT_MAX_GENERAL:
        approver = CT_TO_APPROVER.get(ct, "BMC")
        return {
            "rule": "5.1",
            "passed": False,
            "severity": "hitl",
            "message": (
                f"Segment {n:,} user > {SEGMENT_MAX_GENERAL:,} (Rule 5.1). "
                f"Cần Growth team validate + {approver} reconfirm business impact (dual review)."
            ),
            "dual_review_teams": ["Growth", approver],
            "tag": "big_segment",
        }
    return _pass("5.1")


# ═════════════════════════════════════════════════════════════════════════════
# Nhóm 6 — Approval Routing (partial — Rule 6.5 SURVEY validation script-able parts)
# ═════════════════════════════════════════════════════════════════════════════

def rule_6_5_survey_validation(f: dict) -> list[dict]:
    """Rule 6.5 — SURVEY validation (5 hard checks).

    Áp dụng khi content_type=SURVEY. Trả list of check results (multi-fail possible).
    Nhận `f` dict từ `_extract_fields` — cùng pattern các rule khác trong file.
    """
    if f["content_type"] != "SURVEY":
        return []  # Not SURVEY, skip

    issues = []

    # Check 1 — service_group + service_type enum
    if f["service_group"] != SURVEY_SERVICE_GROUP:
        issues.append(_fail(
            "6.5.1",
            f"SURVEY: service_group='{f['service_group']}' ≠ '{SURVEY_SERVICE_GROUP}'."
        ))
    if f["service_type"] != SURVEY_SERVICE_TYPE:
        issues.append(_fail(
            "6.5.1",
            f"SURVEY: service_type='{f['service_type']}' ≠ '{SURVEY_SERVICE_TYPE}'."
        ))

    # Check 2 — ref_id
    if f["ref_id"] != SURVEY_REF_ID:
        issues.append(_fail(
            "6.5.2",
            f"SURVEY: ref_id='{f['ref_id']}' ≠ '{SURVEY_REF_ID}'."
        ))

    # Check 3 — form_id UUID v4 OR v7 (v1.8.0+ accept Survey Public v7 per RFC 9562)
    # Survey Public migrated v7, Link Test còn v4 — accept cả 2. Skill KHÔNG distinguish
    # source (Public vs Link Test) — chỉ validate format.
    form_id = f["form_id"]
    if not form_id or not _UUID_V4_OR_V7_RE.match(form_id):
        issues.append(_fail(
            "6.5.3",
            f"SURVEY: form_id='{form_id}' không phải UUID v4 hoặc v7 valid. "
            f"Survey Public hiện gen v7, Link Test gen v4 — cả 2 đều accept."
        ))

    # Check 4 — segment size ≤ 250K (redundancy với rule_5_1_segment_size, giữ ở đây cho hard block đủ context SURVEY)
    if f["segment_size"] > SEGMENT_MAX_SURVEY:
        issues.append(_fail(
            "6.5.4",
            f"SURVEY: segment {f['segment_size']:,} > cap {SEGMENT_MAX_SURVEY:,}."
        ))

    # Check 5 — push cap 500K/day/project: cần cross-campaign aggregation (skip ở script local,
    # implementation note: caller phải fetch list_campaigns + aggregate by project_id)

    return issues


# ═════════════════════════════════════════════════════════════════════════════
# Helpers
# ═════════════════════════════════════════════════════════════════════════════

def get_group(content_type: str) -> str:
    """CT → Group VN."""
    return CT_TO_GROUP.get((content_type or "").upper(), "")


def is_quan_trong(content_type: str) -> bool:
    """Check if CT thuộc group Quan trọng."""
    return (content_type or "").upper() in QUAN_TRONG_CTS


def get_content_group_approver(content_type: str) -> str:
    """CT → approver team cho dual review (Rule 5.1) / general routing."""
    return CT_TO_APPROVER.get((content_type or "").upper(), "BMC")
