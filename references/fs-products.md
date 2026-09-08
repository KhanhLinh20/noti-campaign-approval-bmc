# Domain — MoMo Financial Services Products

> **Phiên bản:** v1.16 — 05/2026 (split domain rule)
> **Scope:** Rule 4.9 — MoMo FS product wording (BOM Legal scope). 4 sản phẩm: Túi Thần Tài / Vay Nhanh (bao gồm Newton) / Ví Trả Sau / hợp tác BU khác.
> **Load:** **Lazy** — via `scripts/detect_domain.py` (constant `_FS_PRODUCTS_KEYWORDS`)
> **Trigger keywords:** túi thần tài, tui than tai, ttt, vay nhanh, newton, ví trả sau, vi tra sau, vts, paylater, trả sau, tài chính số, fs product
> **HITL routing:** Reg-floor → BMC + Legal
> **Embedded JSON:** Detection patterns + approved wording per product inline below.

---

### Rule 4.9 — MoMo Financial Services product wording (BOM Legal scope)
- **Tier:** 🟡 LLM (Reg-floor eligible)
- **Nguồn:** BOM email 1/4/2026 + MoMo Legal Content Rules
- **Scope:** CHỈ apply cho 4 sản phẩm Legal-review:
  - **Túi Thần Tài (TTT)** — sản phẩm BCC góp vốn với Finsight (KHÔNG phải tiết kiệm)
  - **Vay Nhanh** — bao gồm **Newton** (trả góp Apple, same rules as Vay Nhanh)
  - **Ví Trả Sau (VTS)**
  - Hợp tác BU khác cho 4 products trên
- **NOT scope:** Bảo hiểm (dùng DIM-4.7), Tiết kiệm/Cashback (dùng DIM-4.8), Vietlott (dùng DIM-4.4/4.5), các FS khác.

#### A. Vai trò MoMo (universal cho 4 products)
- ❌ Cấm: "X của MoMo" / "X do MoMo cung cấp" / "X từ MoMo" / "MoMo cung cấp X" / "MoMo phát hành X"
- ✅ Đúng: "X trên MoMo" / "X qua Ứng dụng MoMo" / "X qua MoMo"

#### B. Product-specific patterns
Detection patterns + approved wording embed ở JSON code block bên dưới (single source of truth).

#### C. Universal forbidden
- ❌ "quảng cáo" cho hoạt động truyền thông MoMo
- ❌ Gắn link trong SMS

#### D. Disclaimer policy
> Skill noti **KHÔNG enforce full disclaimer** trong noti body — char limit (Title ≤ 30, Body ≤ 120) không đủ chỗ. Disclaimer enforce ở blog post / trang sản phẩm in-app (BMC + Legal handle, ngoài scope skill này). Skill chỉ check wording compliance: role attribution + blacklist keywords.

**Sub-score:**
- **100:** Wording đúng — dùng "trên MoMo"/"qua MoMo", không blacklist keyword
- **75:** Wording cơ bản đúng, có advisory minor (VD: thiếu mention partner)
- **50:** 1 blacklist nhẹ ("nhận ngay" cho VTS) hoặc role MoMo borderline
- **25:** Có blacklist rõ ("đầu tư"/"hạn mức" cho Vay Nhanh, "tiết kiệm" cho TTT) → **Reg-floor HITL**
- **0:** Vi phạm role attribution (gọi MoMo là provider) hoặc claim sai bản chất sản phẩm → **Reg-floor HITL**

**HITL routing khi vi phạm:** BMC.

**Lý do Reg-floor:** Vi phạm wording 4 sản phẩm Legal-review → trách nhiệm pháp lý MoMo + rủi ro hủy hợp tác với TPBank/MBV/EVNFinance/Mcredit/Vietcredit/Finsight.

**Detection data (embedded — Legal team update trực tiếp inline khi BOM/Legal thay đổi):**

```json
{
  "_version": "1.0 — 04/2026",
  "_source": "BOM Legal scope email 1/4/2026 + MoMo Legal Content Rules",
  "_effective_date": "2026-04-01",
  "_maintainer": "Legal team + Content lead",

  "tui_than_tai": {
    "keywords": ["Túi Thần Tài", "TTT"],
    "provider": "Công ty Cổ phần Finsight",
    "product_nature": "BCC góp vốn hợp tác kinh doanh — sản phẩm tài chính có rủi ro, KHÔNG phải tiết kiệm",
    "blacklist": [
      "Túi Thần Tài của MoMo",
      "Túi Thần Tài do MoMo cung cấp",
      "sản phẩm tiết kiệm",
      "lãi suất ổn định",
      "tỷ suất sinh lời ổn định",
      "tỷ suất sinh lời lên đến",
      "nguồn tiền thanh toán",
      "thanh toán bằng Túi Thần Tài",
      "chuyển tiền bằng Túi Thần Tài"
    ],
    "approved_wording": [
      "Túi Thần Tài trên MoMo",
      "Sản phẩm tài chính có tính rủi ro",
      "Tiền trong Túi có thể sinh lời và thanh toán/chi tiêu"
    ]
  },

  "vay_nhanh": {
    "keywords": ["Vay Nhanh", "Fastmoney", "FMOB", "Newton"],
    "newton_note": "Newton = trả góp Apple electronics qua Vay Nhanh — same rules as Vay Nhanh",
    "providers": ["EVNFinance", "Mcredit", "Vietcredit", "MBV"],
    "product_nature": "Khoản vay tiêu dùng theo món/từng lần, KHÔNG phải hạn mức",
    "blacklist": [
      "Vay Nhanh của MoMo",
      "Vay Nhanh từ MoMo",
      "Vay MoMo",
      "đầu tư",
      "kinh doanh",
      "xoay vốn",
      "được cấp khoản vay",
      "hạn mức",
      "quảng cáo"
    ],
    "approved_wording": [
      "Vay Nhanh trên MoMo",
      "Vay Nhanh qua MoMo",
      "xoay tiền",
      "chủ động tài chính",
      "có thể được cấp",
      "đủ điều kiện đăng ký",
      "số tiền tối đa có thể vay",
      "gói vay lên đến",
      "trả góp Apple qua Vay Nhanh trên MoMo"
    ],
    "sensitive_context_flag": ["EURO", "World Cup", "giải đấu", "cá độ", "đánh bạc", "tỷ số"]
  },

  "vi_tra_sau": {
    "keywords": ["Ví Trả Sau", "VTS"],
    "providers": ["TPBank", "MBV"],
    "product_nature": "Tín dụng tiêu dùng theo hạn mức (TPBank: vay theo hạn mức HOẶC thẻ tín dụng; MBV: thẻ tín dụng)",
    "blacklist": [
      "Ví Trả Sau của MoMo",
      "Ví Trả Sau do MoMo cung cấp",
      "nhận ngay",
      "quảng cáo"
    ],
    "approved_wording": [
      "Ví Trả Sau trên MoMo",
      "hạn mức đến"
    ]
  },

  "universal_forbidden": [
    "MoMo cung cấp Vay Nhanh",
    "MoMo cung cấp Ví Trả Sau",
    "MoMo cung cấp Túi Thần Tài",
    "MoMo cung cấp Newton",
    "MoMo phát hành"
  ],

  "_cross_reference": {
    "_note": "Products NGOÀI scope Rule 4.9 — dùng rule khác trong guardrail",
    "insurance": "DIM-4.7 (bảo hiểm xe máy/ô tô/du lịch...)",
    "savings_cashback": "DIM-4.8 (tiết kiệm online, hoàn tiền)",
    "lottery": "DIM-4.4 + 4.5 (Vietlott)",
    "billpay_utility": "Không có rule FS-specific — general PROMOTION rules"
  }
}
```

**Implementation note:** Skill load Rule 4.9 → parse JSON code block embedded trong section này (single source of truth). Legal team update JSON inline trong guardrail file khi BOM thay đổi scope hoặc Legal cập nhật rules — KHÔNG cần file external.

---

