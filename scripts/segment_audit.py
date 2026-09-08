"""Rule 5.3 + 5.5 (v1.17/1.18+) — Segment Condition Audit + Compliance Scorecard.

Input: `conditionV2` dict lấy từ segment-mcp `athena-get-segment-info`
(chỉ cần `includeConditions` + `excludeConditions`, KHÔNG cần Raw config).

2 output:
  • audit_segment_conditions()  → list issues ảnh hưởng verdict (block/HITL/warning).
      5.3.A compliance tuổi · 5.3.B exclude blacklist · 5.5 exclude nhân viên MoMo.
  • segment_compliance_scorecard() → checklist đạt/chưa-đạt + LÝ DO cho approver
      (so segment với rule BMC/CIO: size, loại nhân viên, loại blacklist, tuổi).

5.3.C (segment↔content alignment) + 5.3.D (over-broad) là Tier 2 LLM — không ở đây.
"""
import re

from constants import (
    AGE_RESTRICTED_DOMAINS, MINOR_AGE_TAGS, MINOR_AGE_TAG_PATTERN,
    AGE_ATTRIBUTE_PREFIXES, BLACKLIST_RISK_TAG, FINANCIAL_RISK_DOMAINS,
    STAFF_EXCLUDE_ATTRS, STAFF_ATTR_PREFIX,
    SEGMENT_MAX_GENERAL, SEGMENT_MAX_SURVEY,
    CT_TO_GROUP, CT_TO_APPROVER,
    BEHAVIORAL_ATTR_PREFIXES, STATIC_DATERANGES, CT_USED_SERVICE, CT_NON_USER,
)

_MINOR_RE = re.compile(MINOR_AGE_TAG_PATTERN)


def _iter_conditions(groups):
    for g in (groups or []):
        for c in (g.get("conditions") or []):
            yield c


def _collect(groups):
    """(attr_tag_pairs, all_tags, attr_set). Bỏ qua custom-SQL rows (không attributeId)."""
    pairs, all_tags, attrs = [], set(), set()
    for c in _iter_conditions(groups):
        attr = c.get("attributeId")
        if not attr:
            continue
        tags = c.get("tagIds") or []
        pairs.append((attr, tags))
        all_tags.update(tags)
        attrs.add(attr)
    return pairs, all_tags, attrs


def _has_minor_tag(include_pairs) -> bool:
    for attr, tags in include_pairs:
        is_age_attr = attr.startswith(AGE_ATTRIBUTE_PREFIXES)
        for t in tags:
            if t in MINOR_AGE_TAGS:
                return True
            if is_age_attr and _MINOR_RE.search(t):
                return True
    return False


def _has_age_condition(include_pairs) -> bool:
    return any(attr.startswith(AGE_ATTRIBUTE_PREFIXES) for attr, _ in include_pairs)


def _has_blacklist_exclude(exc_tags, exc_attrs) -> bool:
    return (BLACKLIST_RISK_TAG in exc_tags
            or BLACKLIST_RISK_TAG in exc_attrs
            or any(BLACKLIST_RISK_TAG in (a or "") for a in exc_attrs))


def _has_staff_exclude(exc_attrs) -> bool:
    return (bool(exc_attrs & STAFF_EXCLUDE_ATTRS)
            or any((a or "").startswith(STAFF_ATTR_PREFIX) for a in exc_attrs))


def _parse(condition_v2):
    inc_pairs, _, _ = _collect(condition_v2.get("includeConditions"))
    _, exc_tags, exc_attrs = _collect(condition_v2.get("excludeConditions"))
    return inc_pairs, exc_tags, exc_attrs


def _is_behavioral_segment(condition_v2, data_source) -> bool:
    """Rule 5.6 (BMC 9.0) — segment có lọc theo HÀNH VI dùng dịch vụ không.

    CHỈ đọc attribute/điều kiện trong conditionV2 + dataSource. KHÔNG dùng tên segment.
    Behavioral khi có ≥1: dataSource BIGQUERY · custom-SQL · attribute họ hành vi ·
    dateRange recency (khác ALWAYS_ACTIVE).
    """
    # Signal: dataSource có BIGQUERY (query hành vi)
    ds = data_source or []
    if isinstance(ds, str):
        ds = [ds]
    if any("BIGQUERY" in str(x).upper() for x in ds):
        return True

    for c in _iter_conditions((condition_v2 or {}).get("includeConditions")):
        attr = c.get("attributeId")
        # Signal: custom-SQL condition (không attributeId, có description/rows) = lọc giao dịch
        if not attr:
            if c.get("description") or c.get("rows"):
                return True
            continue
        # Signal: attribute thuộc họ hành vi/usage
        if attr.startswith(BEHAVIORAL_ATTR_PREFIXES):
            return True
        # Signal: dateRange recency window (khác static) trên bất kỳ điều kiện nào
        dr = (c.get("dateRange") or "").upper()
        if dr and dr not in STATIC_DATERANGES:
            return True
    return False


# ═════════════════════════════════════════════════════════════════════════════
# Issues (ảnh hưởng verdict)
# ═════════════════════════════════════════════════════════════════════════════

def audit_segment_conditions(condition_v2: dict, content_type: str, domains,
                              data_source=None) -> list:
    """5.3.A + 5.3.B + 5.5 + 5.6. `domains` = list domain key (vd ['vietlott'])."""
    if not condition_v2:
        return []
    domains = set(domains or [])
    ct = (content_type or "").upper()
    inc_pairs, exc_tags, exc_attrs = _parse(condition_v2)
    issues = []

    # ── 5.3.A — Compliance độ tuổi ──────────────────────────────────────────
    if domains & AGE_RESTRICTED_DOMAINS:
        if _has_minor_tag(inc_pairs):
            issues.append({"rule": "5.3.A", "passed": False, "severity": "error",
                           "tag": "segment_targets_minor",
                           "message": ("Segment target nhóm dưới 18 tuổi cho nội dung giới hạn độ tuổi "
                                       "(Rule 5.3.A). Owner sửa segment (loại nhóm <18) và resubmit.")})
        elif not _has_age_condition(inc_pairs):
            issues.append({"rule": "5.3.A", "passed": False, "severity": "hitl",
                           "tag": "segment_no_age_condition",
                           "message": ("Nội dung giới hạn độ tuổi nhưng segment chưa có điều kiện tuổi "
                                       "(Rule 5.3.A). Cần xác nhận đối tượng đủ 18+ trước khi duyệt.")})

    # ── 5.3.B — Bắt buộc exclude blacklist/risk ─────────────────────────────
    if domains & FINANCIAL_RISK_DOMAINS and not _has_blacklist_exclude(exc_tags, exc_attrs):
        issues.append({"rule": "5.3.B", "passed": False, "severity": "hitl",
                       "tag": "segment_no_blacklist_exclude",
                       "message": ("Nội dung tài chính/rủi ro nhưng segment chưa loại trừ nhóm rủi ro "
                                   "(blacklist) (Rule 5.3.B). Cần xác nhận trước khi duyệt.")})

    # ── 5.5 — Exclude nhân viên MoMo (BMC + CIO) — WARNING ──────────────────
    if not _has_staff_exclude(exc_attrs):
        issues.append({"rule": "5.5", "passed": False, "severity": "warning",
                       "tag": "segment_no_staff_exclude",
                       "message": ("Segment chưa loại trừ nhân viên MoMo nội bộ (Rule 5.5). "
                                   "Cân nhắc exclude trước khi push production.")})

    # ── 5.6 (BMC 9.0) — Segment hành vi ↔ content_type — WARNING ────────────
    # Chỉ áp dụng cho CT trong mapping BMC: PROMOTION_SERVICE vs ADVERTISING.
    if ct in (CT_USED_SERVICE, CT_NON_USER):
        behavioral = _is_behavioral_segment(condition_v2, data_source)
        if behavioral and ct == CT_NON_USER:
            issues.append({"rule": "5.6", "passed": False, "severity": "warning",
                           "tag": "segment_ct_behavior_mismatch",
                           "message": ("Segment lọc theo hành vi đã dùng dịch vụ nhưng content_type là "
                                       "quảng cáo (Rule 5.6/BMC 9.0) — nên dùng 'ưu đãi dịch vụ'. Approver verify.")})
        elif not behavioral and ct == CT_USED_SERVICE:
            issues.append({"rule": "5.6", "passed": False, "severity": "warning",
                           "tag": "segment_ct_behavior_mismatch",
                           "message": ("Content_type là ưu đãi dịch vụ nhưng segment chưa có điều kiện hành vi "
                                       "dùng dịch vụ (Rule 5.6/BMC 9.0) — nên dùng 'quảng cáo' hoặc bổ sung điều kiện usage. Approver verify.")})

    return issues


# ═════════════════════════════════════════════════════════════════════════════
# Scorecard (hiển thị cho approver — đạt/chưa đạt + lý do)
# ═════════════════════════════════════════════════════════════════════════════

def segment_compliance_scorecard(condition_v2: dict, content_type: str,
                                  domains, segment_size: int, data_source=None) -> dict:
    """Checklist segment vs rule BMC/CIO. Trả {team, items[], passed, total, overall, fail_reasons[]}.

    status mỗi item: "pass" | "fail" | "warn".
    Áp dụng có điều kiện: size + staff luôn check; blacklist khi domain tài chính;
    tuổi khi domain age-restricted.
    """
    if not condition_v2:
        return {"available": False}

    ct = (content_type or "").upper()
    domains = set(domains or [])
    team = CT_TO_APPROVER.get(ct, "BMC")
    group = CT_TO_GROUP.get(ct, "")
    is_survey = ct == "SURVEY"
    inc_pairs, exc_tags, exc_attrs = _parse(condition_v2)
    size = int(segment_size or 0)

    items = []

    # 1) Size
    if is_survey:
        ok = size <= SEGMENT_MAX_SURVEY
        items.append({"key": "size", "label": "Size trong ngưỡng CIO (≤250K)",
                      "status": "pass" if ok else "fail",
                      "reason": (f"{size:,} user" + ("" if ok else f" > cap {SEGMENT_MAX_SURVEY:,} (SURVEY hard cap)"))})
    else:
        within = size <= SEGMENT_MAX_GENERAL
        items.append({"key": "size", "label": "Size trong ngưỡng (≤5M)",
                      "status": "pass" if within else "warn",
                      "reason": (f"{size:,} user" + ("" if within else f" > 5M → cần Growth + {team} dual review (Rule 5.1)"))})

    # 2) Exclude nhân viên MoMo (luôn)
    staff_ok = _has_staff_exclude(exc_attrs)
    items.append({"key": "exclude_staff", "label": "Đã loại nhân viên MoMo",
                  "status": "pass" if staff_ok else "fail",
                  "reason": ("Có điều kiện loại trừ nhân viên" if staff_ok
                             else "Chưa thấy điều kiện loại trừ nhân viên MoMo (user_account_staff_*)")})

    # 3) Exclude blacklist (domain tài chính/rủi ro)
    if domains & FINANCIAL_RISK_DOMAINS:
        bl_ok = _has_blacklist_exclude(exc_tags, exc_attrs)
        items.append({"key": "exclude_blacklist", "label": "Đã loại nhóm rủi ro (blacklist)",
                      "status": "pass" if bl_ok else "fail",
                      "reason": ("Có exclude blacklist" if bl_ok
                                 else "Nội dung tài chính/rủi ro nhưng chưa loại trừ blacklist_risk")})

    # 4) Compliance tuổi (domain age-restricted)
    if domains & AGE_RESTRICTED_DOMAINS:
        if _has_minor_tag(inc_pairs):
            items.append({"key": "age", "label": "Tuổi hợp lệ (chỉ 18+)", "status": "fail",
                          "reason": "Đang target nhóm dưới 18 tuổi"})
        elif not _has_age_condition(inc_pairs):
            items.append({"key": "age", "label": "Tuổi hợp lệ (chỉ 18+)", "status": "warn",
                          "reason": "Chưa có điều kiện tuổi — cần xác nhận đủ 18+"})
        else:
            items.append({"key": "age", "label": "Tuổi hợp lệ (chỉ 18+)", "status": "pass",
                          "reason": "Không có nhóm <18 trong điều kiện"})

    # 5) Segment hành vi ↔ content_type (BMC 9.0) — chỉ khi CT ∈ {ưu đãi dịch vụ, quảng cáo}
    if ct in (CT_USED_SERVICE, CT_NON_USER):
        behavioral = _is_behavioral_segment(condition_v2, data_source)
        if ct == CT_USED_SERVICE:
            ok = behavioral
            reason = ("Có điều kiện hành vi dùng dịch vụ" if ok
                      else "CT ưu đãi dịch vụ nhưng segment chưa lọc theo hành vi dùng dịch vụ")
        else:  # CT_NON_USER (quảng cáo)
            ok = not behavioral
            reason = ("Segment không lọc hành vi — hợp quảng cáo" if ok
                      else "Segment đã lọc hành vi dùng dịch vụ — nên dùng ưu đãi dịch vụ thay vì quảng cáo")
        items.append({"key": "ct_behavior", "label": "Segment khớp loại nội dung (đã/chưa dùng dịch vụ)",
                      "status": "pass" if ok else "warn", "reason": reason})

    n_pass = sum(1 for it in items if it["status"] == "pass")
    total = len(items)
    fail_reasons = [it["reason"] for it in items if it["status"] in ("fail", "warn")]
    overall = "đạt" if all(it["status"] == "pass" for it in items) else "chưa đạt"

    return {
        "available": True,
        "team": team,
        "group": group,
        "items": items,
        "passed": n_pass,
        "total": total,
        "overall": overall,
        "fail_reasons": fail_reasons,
    }
