"""Constants — single source of truth cho Tier 1 hard rule checks.

KHI RULE CHANGE → update file này, KHÔNG sửa chỗ khác.
Cross-ref: references/ (13 rule files, v1.16+)
"""

# ─── Rule 2.1, 2.2 — Char limits ──────────────────────────────────────────────
TITLE_MAX = 30
BODY_MAX = 120

# ─── Rule 2.6 — Param whitelist (case-sensitive, exact match) ─────────────────
WHITELIST_PARAMS = {"fullname", "lastname"}

# ─── Rule 1.1 — Content type valid codes (14 codes) ───────────────────────────
VALID_CTS = {
    # Group Quan trọng
    "TRANSACTION", "REMIND", "WARNING", "SERVICE",
    # Group Ưu đãi
    "PROMOTION", "PROMOTION_SERVICE", "PROMOTION_OUTDATED",
    "GAME", "ADVERTISING", "EVENT",
    # Group Tương tác
    "FRIENDS", "BUSINESS_PAGE", "SOCIAL", "SURVEY",
}

# Create mode chỉ allow 6 CT (Rule 1.1 create restrict)
CREATE_MODE_CTS = {
    "WARNING", "SERVICE", "PROMOTION_SERVICE",
    "ADVERTISING", "EVENT", "SURVEY",
}

# ─── Rule 2.10 — Blocked formats (must be out-app push) ───────────────────────
BLOCKED_FORMATS = {"push-inapp", "header", "popup", "xbanner", "snackbar"}

# ─── Rule 5.1 — Segment size cap ──────────────────────────────────────────────
SEGMENT_MAX_GENERAL = 5_000_000   # > 5M → dual HITL (Growth + content-group)
SEGMENT_MAX_SURVEY = 250_000      # SURVEY hard cap (Rule 6.5)

# ─── Rule 5.2 — BU daily campaign cap ─────────────────────────────────────────
BU_DAILY_WARNING_THRESHOLD = 4    # ≥4 → warning advisory
BU_DAILY_CAP = 10                  # ≥10 → HITL re-confirm

# ─── Rule 6.5 — SURVEY validation ─────────────────────────────────────────────
SURVEY_PUSH_CAP_PER_PROJECT = 500_000
SURVEY_SERVICE_GROUP = "general"
SURVEY_SERVICE_TYPE = "survey_onlinepanel"
SURVEY_REF_ID = "onlinepanel_entry"

# ─── CT → Group VN mapping ────────────────────────────────────────────────────
CT_TO_GROUP = {
    "TRANSACTION": "Quan trọng",
    "REMIND": "Quan trọng",
    "WARNING": "Quan trọng",
    "SERVICE": "Quan trọng",
    "PROMOTION": "Ưu đãi",
    "PROMOTION_SERVICE": "Ưu đãi",
    "PROMOTION_OUTDATED": "Ưu đãi",
    "GAME": "Ưu đãi",
    "ADVERTISING": "Ưu đãi",
    "EVENT": "Ưu đãi",
    "FRIENDS": "Tương tác",
    "BUSINESS_PAGE": "Tương tác",
    "SOCIAL": "Tương tác",
    "SURVEY": "Tương tác",
}

QUAN_TRONG_CTS = {"TRANSACTION", "REMIND", "WARNING", "SERVICE"}

# CT → Content-group approver (cho dual review Rule 5.1)
CT_TO_APPROVER = {
    "TRANSACTION": "PCS", "REMIND": "PCS", "WARNING": "PCS", "SERVICE": "PCS",
    "PROMOTION": "BMC", "PROMOTION_SERVICE": "BMC", "PROMOTION_OUTDATED": "BMC",
    "GAME": "BMC", "ADVERTISING": "BMC", "EVENT": "BMC",
    "FRIENDS": "BMC", "BUSINESS_PAGE": "BMC", "SOCIAL": "BMC",
    "SURVEY": "CIO",
}

# ─── Rule 2.8 — Test/placeholder detection ────────────────────────────────────
TEST_KEYWORDS = {
    "test", "asdf", "abc", "xxx", "demo", "placeholder",
    "qwerty", "lorem ipsum", "dummy", "sample",
}
SHANNON_ENTROPY_MIN = 1.5  # < này = gibberish

# ─── Promo direct-push keywords (Rule 1.3 + 1.4) ──────────────────────────────
PROMO_DIRECT_KEYWORDS = {
    "nhận voucher", "mở app nhận quà", "direct push", "big campaign",
}

# ─── Rule 2.13 (v1.18+) — Gift card reminder pattern detection ────────────────
# 3-signal AND logic — all 3 phải match để trigger HITL advisory.
# Lý do: ML Promotion side đã có cơ chế remind tự động cho voucher/thẻ quà.
# Noti Campaign side gửi thêm = duplication / over-notification. Force HITL
# verify với BMC (hoặc PCS theo CT default routing).

# Signal 1: Remind-style language
GIFT_REMIND_PATTERNS = {
    "bạn còn", "còn quà", "còn voucher", "còn ưu đãi",
    "đã sẵn sàng", "thu thập ngay", "đừng quên",
    "chưa dùng", "sắp hết", "nhanh kẻo hết",
    "vẫn còn", "kịp dùng", "hôm nay là hạn cuối",
}

# Signal 2: Gift/voucher keywords
GIFT_KEYWORDS = {
    "thẻ quà", "voucher", "quà sinh nhật", "quà tháng",
    "đặc quyền", "gói thành viên", "ưu đãi sinh nhật",
    "quà thành viên", "phần thưởng", "ưu đãi đã nhận",
    "voucher hoàn tiền", "voucher giảm giá",
}

# Signal 3: ref_id signals voucher/gift detail page
REFID_VOUCHER_PATTERNS = {
    "voucher_detail", "gift_detail", "my_vouchers",
    "my_rewards", "membership_benefit", "voucher_list",
    "my_gifts", "vts_voucher", "fs_voucher_detail",
}

# ─── Rule 5.3 (v1.17+) — Segment Condition Audit ──────────────────────────────
# Đọc conditionV2 (từ segment-mcp athena-get-segment-info) → so policy duyệt.

# Domain giới hạn độ tuổi (5.3.A) — segment KHÔNG được target nhóm <18,
# và nếu không có điều kiện tuổi nào → HITL verify 18+.
AGE_RESTRICTED_DOMAINS = {
    "vietlott",          # xổ số — NĐ 30/2007, ≥18
    "fs-products",       # vay/tín dụng — Vay Nhanh / Ví Trả Sau / PayLater
    "insurance",         # bảo hiểm có giới hạn tuổi
}

# Tag tuổi DƯỚI 18 (mã Athena thật — verify qua segment-mcp list/search 26/06/2026).
# Match exact tagId; mở rộng khi taxonomy đổi.
MINOR_AGE_TAGS = {
    "user_age_group_lower_18",
    "user_age_15", "user_age_16", "user_age_17",
    "user_age_source_kyc_15", "user_age_source_kyc_16", "user_age_source_kyc_17",
}
# Pattern bắt mã tuổi <18 dạng số (phòng taxonomy thêm mã mới):
# bắt "_<n>" hoặc "_lower_18" với n ∈ 0..17. Áp cho attribute họ user_age*.
MINOR_AGE_TAG_PATTERN = r"(?:_lower_18$|_(?:[0-9]|1[0-7])$)"

# Attribute họ "tuổi" — để biết segment CÓ điều kiện tuổi hay không (5.3.A no-age).
AGE_ATTRIBUTE_PREFIXES = ("user_age_group_age", "user_age_age", "user_age_source_kyc_age")

# Tag loại trừ rủi ro (5.3.B) — domain tài chính nên có ở excludeConditions.
BLACKLIST_RISK_TAG = "user_blacklist_risk"

# Domain tài chính/rủi ro cần exclude blacklist (5.3.B).
FINANCIAL_RISK_DOMAINS = {
    "fs-products",       # vay/tín dụng
    "cashback-fintech",  # cashback giá trị cao
    "vietlott",          # xổ số
}

# ─── Rule 5.5 (v1.18+) — Exclude nhân viên MoMo (BMC + CIO requirement) ────────
# Segment production push NÊN loại trừ nhân viên MoMo nội bộ.
# Attribute thật (verify segment-mcp 26/06/2026): "danh sách nhân viên MoMo
# chi tiết theo các nhóm phòng ban" (tags _nontech / _protech).
STAFF_EXCLUDE_ATTRS = {
    "user_account_staff_by_group_department",
}
# Match prefix khi exclude dùng attribute họ staff (phòng có biến thể attr khác).
STAFF_ATTR_PREFIX = "user_account_staff"

# ─── Rule 5.6 (BMC 9.0, v1.18+) — Segment hành vi ↔ content_type ───────────────
# CHỈ dựa attribute/điều kiện ĐỌC ĐƯỢC trong segment (conditionV2 + dataSource),
# TUYỆT ĐỐI KHÔNG dựa tên segment (tên do user tự đặt, không đáng tin).
#
# "Đã dùng dịch vụ" (behavioral) khi segment có ≥1 signal:
#   - attribute thuộc họ hành vi/usage (prefix dưới — grounded segment-mcp 26/06/2026)
#   - dateRange là recency window (KHÁC ALWAYS_ACTIVE) → lọc theo hành vi N ngày (vd A30/A90)
#   - custom-SQL condition (description: giao dịch/service code/usage)
#   - dataSource chứa "BIGQUERY" (có query hành vi, không chỉ thuộc tính tĩnh)
BEHAVIORAL_ATTR_PREFIXES = (
    "user_transaction",   # user_transaction_group_service_*, user_transaction_buname_*
    "user_active",        # user_active_in_range, user_active_binding_churn_*
    "user_project",       # user_project_*_usecase_*, ..._continuous_a90_*, vietqr_churn...
)
# dateRange TĨNH (nhân khẩu). Bất kỳ giá trị khác = recency window = behavioral signal.
STATIC_DATERANGES = {"ALWAYS_ACTIVE", "", "NONE"}

# BMC Rule 9.0 mapping content_type (dùng đúng 2 dòng BMC — owner confirm 26/06/2026):
CT_USED_SERVICE = "PROMOTION_SERVICE"   # đã dùng dịch vụ  → ưu đãi dịch vụ
CT_NON_USER = "ADVERTISING"             # chưa dùng dịch vụ → quảng cáo
