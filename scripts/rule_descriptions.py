"""Rule code → user-friendly Vietnamese description.

Central mapping cho user-facing output across 3 luồng:
    - Batch report (template 08) — cột "Lý do không đạt"
    - Phase 5 Athena comment (human part) — reasoning
    - Dashboard 09 — `reasonHtml` field

Principle #8 (`skill/noti-campaign-approval.md`): KHÔNG show rule code (Rule X.Y / DIM-X.Y / Tier X) ra user.
Agent dùng `to_user_message()` để convert rule code → natural Vietnamese description
trước khi render bất kỳ user-facing text nào.

Audit log (Athena message field structured part) vẫn giữ rule code trong `trg=...` tag —
audit/regression cần exact code, không cần VN description.

Source of truth: edit file này khi muốn đổi wording user-facing. KHÔNG sửa
rời rạc trong tier1_check.py / SKILL templates / dashboard reasonHtml.
"""

# ─── Tier A — Hard checks (script) ────────────────────────────────────────────
USER_DESCRIPTIONS = {
    # Nhóm 1 — Content type & format
    "1.1": "Loại nội dung không thuộc danh sách hợp lệ",
    "1.6": "Loại nội dung không khớp với chủ đề/intent thực tế của campaign",
    "1.7": "Loại EVENT — cần BMC xác nhận thematic context (Lắc Xì/Tết/8-3/...)",
    "1.8": "Đường link mở app không khớp với danh sách màn hình MoMo",

    # Nhóm 2 — Content hard checks
    "2.1": "Tiêu đề vượt giới hạn ký tự cho phép",
    "2.2": "Nội dung vượt giới hạn ký tự cho phép",
    "2.3": "Body có xuống dòng hoặc bullet — cần viết liền mạch",
    "2.4": "Phát hiện thông tin cá nhân nhạy cảm (SĐT/email/CCCD/tài khoản) trong nội dung",
    "2.6": "Có biến không hợp lệ trong nội dung (chỉ chấp nhận ${fullname}, ${lastname})",
    "2.7": "Vi phạm format thuộc nhóm Quan trọng — cần PCS duyệt thủ công (không reject ngay)",
    "2.8": "Nội dung dạng test/placeholder, chưa phải bản chính thức",
    "2.9": "Đã có campaign cùng nội dung + segment trong 7 ngày qua",
    "2.10": "Định dạng push không hợp lệ (cần out-app push, không in-app/Header/Popup)",
    # 2.11 severity-aware — see _DESCRIPTIONS_BY_SEVERITY below
    "2.12": "Có hình ảnh out-app — click link review trước khi duyệt (advisory, không block)",
    "2.13": "Pattern phát hiện: Nội dung có chứa remind voucher, cần human review",
    "2.14": "Tên thương hiệu MoMo viết sai — phải viết đúng 'MoMo' (camelCase, không dấu)",

    # Nhóm 5 — Segment
    "5.1": "Segment vượt 5 triệu — cần Growth + team duyệt nội dung xác nhận song song",
    "5.2": "BU đã có nhiều campaign push trong ngày — cân nhắc stagger để tránh user fatigue",
    "5.3.A": "Segment đang nhắm tới nhóm dưới 18 tuổi cho nội dung giới hạn độ tuổi",
    "5.3.B": "Nội dung tài chính/rủi ro nhưng segment chưa loại trừ nhóm rủi ro (blacklist)",
    "5.3.C": "Điều kiện segment chưa khớp với đối tượng nêu trong nội dung",
    "5.3.D": "Segment nhắm quá rộng + size lớn — cân nhắc thu hẹp để tránh user fatigue",
    "5.5": "Segment chưa loại trừ nhân viên MoMo nội bộ",
    "5.6": "Loại nội dung chưa khớp hành vi segment (đã/chưa dùng dịch vụ)",

    # Nhóm 6 — Routing / SURVEY validation
    "6.5": "Nội dung khảo sát cần CIO duyệt + verify cấu hình (service/refid/form_id/segment cap)",
    "6.5.1": "Khảo sát: service group hoặc service type không khớp chuẩn",
    "6.5.2": "Khảo sát: ref_id không khớp 'onlinepanel_entry'",
    "6.5.3": "Khảo sát: form_id không đúng định dạng UUID v4 hoặc v7 (Survey Public hiện gen v7)",
    "6.5.4": "Khảo sát: segment vượt cap 250K user",
    "6.7": "Priority BYPASS chỉ Platform role dùng — agent không được propose",

    # Tier D routing keys (não phải rule code thực — semantic tag)
    # "Tier D" generic — không emit vào user_summary (đã được cover bởi tag cụ thể quan_trong_pcs_routing/survey_cio_routing/event_thematic_required)
    "Tier D": "",

    # ─── Tier 2 — LLM Judge DIMs ──────────────────────────────────────────────
    "DIM-3.1": "Tiêu đề chưa nêu rõ nội dung/lợi ích chính",
    "DIM-3.2": "Body chỉ lặp lại tiêu đề, chưa bổ sung thông tin mới",
    "DIM-3.3": "Có dùng viết tắt từ ngữ phổ thông",
    "DIM-3.4": "Có từ thông thường bị viết hoa toàn bộ",
    "DIM-3.4b": "Có dấu hiệu sai chính tả — cần approver xác nhận",
    "DIM-3.4c": "Dấu câu chưa đúng quy tắc",
    "DIM-3.4d": "Định dạng tiền tệ/số đếm chưa chuẩn",
    "DIM-3.4e": "Định dạng ngày giờ chưa chuẩn",
    "DIM-3.5": "Emoji không đúng vị trí (đầu Title/Body) hoặc thiếu dấu cách",
    "DIM-3.5b": "Có emoji mới (Unicode 14+) có thể không hiển thị trên thiết bị cũ",
    "DIM-3.6": "Dùng emoji cảnh báo (⚠️ ❗) cho nội dung Ưu đãi — không phù hợp",
    "DIM-3.7": "Lợi ích quảng cáo chưa có số cụ thể hoặc thiếu điều kiện áp dụng",
    "DIM-3.8": "Có từ ngữ tiêu cực mà chưa kèm giải pháp",
    "DIM-3.9": "Angle/tone không phù hợp với loại nội dung",
    "DIM-3.10": "CTA chưa rõ ràng (thiếu động từ hành động cụ thể)",
    "DIM-3.11": "Nội dung có dấu hiệu xâm phạm quyền riêng tư",
    "DIM-3.12": "Push time chưa phù hợp với nội dung Cảnh báo/Dịch vụ bảo trì",
    "DIM-3.15": "Cách dùng personalization token chưa tự nhiên",
    "DIM-3.16": "Con số/hạn mức/giá trị trong nội dung chưa cụ thể",
    "DIM-3.17": "FOMO chưa có anchor cụ thể (thời gian/số lượng)",
    "DIM-3.18": "Tiêu đề chưa khớp với segment đang target",

    "DIM-4.1": "Có cụm từ tuyệt đối ('tốt nhất', 'duy nhất', 'đặc quyền chỉ') — cần verify context",
    "DIM-4.2": "Có ngôn ngữ phân biệt đối xử",
    "DIM-4.3": "Nội dung không có tiếng Việt (toàn bộ tiếng nước ngoài)",
    "DIM-4.4": "Nội dung Vietlott có claim cải thiện tài chính — cần Legal review",
    "DIM-4.5": "Nội dung Vietlott có khuyến mại — cần Legal review",
    "DIM-4.6": "Giá vé máy bay thiếu disclaimer điều kiện",
    "DIM-4.7": "Bảo hiểm: phạm vi mô tả vague, có thể gây hiểu nhầm",
    "DIM-4.8": "Hoàn tiền/cashback chưa có điều kiện rõ ràng",
    "DIM-4.9": "Nội dung sản phẩm tài chính MoMo (Vay Nhanh / Túi Thần Tài / Ví Trả Sau) cần BMC + Legal verify wording",
}

# Severity-aware descriptions (severity → description)
_DESCRIPTIONS_BY_SEVERITY = {
    "2.11": {
        "error":   "Phát hiện cụm từ bị cấm theo Legal/Compliance — không thể duyệt",
        "hitl":    "Phát hiện cụm từ nhạy cảm — cần Legal verify context (có thể có ngoại lệ)",
        "warning": "Có cụm từ borderline ('duy nhất', 'tuyệt đối', ...) — BMC verify khi duyệt",
    },
}

# Tag → semantic description (dùng cho Tier D routing + tags Phase 5)
_TAG_DESCRIPTIONS = {
    "quan_trong_pcs_routing": "Thuộc nhóm Quan trọng — cần PCS duyệt",
    "survey_cio_routing":      "Khảo sát — cần CIO duyệt (không auto-schedule)",
    "event_thematic_required": "Sự kiện thematic — cần BMC xác nhận context",
    "big_segment":             "Segment vượt 5 triệu — cần Growth + team duyệt nội dung xác nhận song song",
    "refid_not_in_whitelist":  "Đường link mở app không khớp với danh sách màn hình MoMo",
    "refid_content_mismatch":  "Đường link mở app không khớp với chủ đề nội dung",
    "emoji_at_start":          "Emoji không nên đặt ở đầu tiêu đề/body",
    "emoji_unicode_modern":    "Có emoji mới có thể không hiển thị trên thiết bị cũ",
    "vietlott_legal_review":   "Nội dung Vietlott — cần Legal review",
    "fs_product_wording":      "Sản phẩm tài chính — cần BMC + Legal verify wording",
    "ct_mismatch":             "Loại nội dung không khớp với intent thực tế",
    "push_cap_exceeded":       "Vượt cap push 500K/ngày/project",
    "title_too_long":          "Tiêu đề vượt giới hạn ký tự",
    "body_too_long":           "Nội dung vượt giới hạn ký tự",
    "typo_in_title":           "Có dấu hiệu sai chính tả trong tiêu đề",
    "typo_in_body":            "Có dấu hiệu sai chính tả trong body",
    "pii_detected":            "Phát hiện thông tin cá nhân trong nội dung",
    "test_content":            "Nội dung dạng test/placeholder",
    "duplicate_segment":       "Đã có campaign cùng nội dung + segment trong 7 ngày",
    "no_cta":                  "Thiếu CTA rõ ràng",
    "cashback_no_conditions":  "Cashback chưa có điều kiện rõ ràng",
    "airfare_no_disclaimer":   "Vé máy bay thiếu disclaimer điều kiện",
    "insurance_vague_scope":   "Bảo hiểm vague phạm vi mô tả",
    "discrimination_language": "Có ngôn ngữ phân biệt đối xử",
    "non_vietnamese":          "Nội dung toàn tiếng nước ngoài",
    "banned_phrase_blocker":   "Phát hiện cụm từ bị cấm theo Legal",
    "banned_phrase_critical":  "Phát hiện cụm từ nhạy cảm cần Legal verify",
    "banned_phrase_warning":   "Có cụm từ borderline cần BMC verify",
    "bu_daily_cap_warning":    "BU đã có nhiều campaign push trong ngày — nên stagger",
    "bu_daily_cap_exceeded":   "BU vượt cap 10 campaign push/ngày",
    "vague_claim":             "Có cụm mơ hồ không có số ('hấp dẫn', 'lớn', ...)",
    "absolute_claim":          "Có claim tuyệt đối ('tốt nhất', 'duy nhất', '100%')",
    "sensitive_action":        "Yêu cầu user action nhạy cảm (OTP/đổi mật khẩu/link ngoài)",
    "image_outapp_review":     "Có hình ảnh out-app — approver click link review trước khi duyệt",
    "gift_card_reminder_duplicate_risk": "Nội dung có chứa remind voucher (có thể duplicate với ML Promotion remind tự động) — cần human review",
    "brand_name_misspelled":   "Tên thương hiệu viết sai chính tả — phải viết đúng theo brand guideline",
    "segment_targets_minor":   "Segment đang nhắm tới nhóm dưới 18 tuổi cho nội dung giới hạn độ tuổi",
    "segment_no_age_condition": "Nội dung giới hạn độ tuổi nhưng segment chưa có điều kiện tuổi — cần xác nhận 18+",
    "segment_no_blacklist_exclude": "Nội dung tài chính/rủi ro nhưng segment chưa loại trừ nhóm rủi ro (blacklist)",
    "segment_content_mismatch": "Điều kiện segment chưa khớp với đối tượng nêu trong nội dung",
    "segment_overbroad":       "Segment nhắm quá rộng + size lớn — cân nhắc thu hẹp",
    "segment_no_staff_exclude": "Segment chưa loại trừ nhân viên MoMo nội bộ",
    "segment_ct_behavior_mismatch": "Loại nội dung chưa khớp hành vi segment (đã/chưa dùng dịch vụ)",
}


def to_user_message(rule: str, severity: str = None) -> str:
    """Convert rule code → user-friendly Vietnamese description.

    Args:
        rule: rule code (vd "2.3", "DIM-4.9", "Tier D")
        severity: optional severity ("error"/"hitl"/"warning") cho rule có severity-aware desc

    Returns:
        Natural Vietnamese description (no rule code).
        Fallback: "Vi phạm quy định nội dung" nếu rule không có trong map.
    """
    # Severity-aware first
    if rule in _DESCRIPTIONS_BY_SEVERITY:
        return _DESCRIPTIONS_BY_SEVERITY[rule].get(
            severity, list(_DESCRIPTIONS_BY_SEVERITY[rule].values())[0]
        )
    return USER_DESCRIPTIONS.get(rule, "Vi phạm quy định nội dung")


def tag_to_user_message(tag: str) -> str:
    """Convert tag (Phase 5 structured log tag) → user-friendly Vietnamese.

    Args:
        tag: tag từ Common Dictionary (vd "big_segment", "refid_not_in_whitelist")

    Returns:
        Natural Vietnamese description.
    """
    return _TAG_DESCRIPTIONS.get(tag, tag.replace("_", " "))


def issues_to_user_summary(issues: list[dict], tags: list[str] = None) -> str:
    """Generate user-friendly summary từ issues[] + tags[] cho batch report column.

    Args:
        issues: list issues từ tier1_check output (mỗi item có rule + severity)
        tags: optional list tags từ Tier D routing

    Returns:
        Concatenated Vietnamese descriptions, semicolon-separated.
        Empty string nếu không có issue.
    """
    parts = []
    seen = set()  # avoid duplicate descriptions

    for issue in (issues or []):
        rule = issue.get("rule", "")
        sev = issue.get("severity")
        desc = to_user_message(rule, sev)
        if desc and desc.strip() and desc not in seen:  # skip empty (vd Tier D generic)
            parts.append(desc)
            seen.add(desc)

    for tag in (tags or []):
        desc = tag_to_user_message(tag)
        if desc and desc.strip() and desc not in seen:
            parts.append(desc)
            seen.add(desc)

    return ". ".join(parts) + ("." if parts else "")


# ─── CLI helper for debugging ────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python rule_descriptions.py <rule_code> [severity]")
        print("       python rule_descriptions.py tag <tag_name>")
        sys.exit(1)

    if sys.argv[1] == "tag":
        print(tag_to_user_message(sys.argv[2]))
    else:
        sev = sys.argv[2] if len(sys.argv) > 2 else None
        print(to_user_message(sys.argv[1], sev))
