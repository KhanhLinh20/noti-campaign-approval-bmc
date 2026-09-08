# 07 — LLM Judge Prompt — DOMAIN subset
## Noti Campaign Agent — Domain-specific regulatory DIMs (lazy load)

> **Phiên bản:** v1.12 — 05/2026 (split from monolith v1.11)
> **Scope:** DIMs domain-specific regulatory — load qua `scripts/detect_domain.py` keyword match
> **Load:** Lazy — chỉ load DIMs tương ứng domain detected
> **Companion core:** `07-llm-judge-core_v1.12.md` (load đồng thời cho schema + universal DIMs)
>
> **DIMs covered & trigger:**
> | DIM | Trigger keyword (qua detect_domain.py) | Domain |
> |---|---|---|
> | DIM-4.4 / DIM-4.5 | "vietlott" / "xổ số" / "vé số" | Vietlott |
> | DIM-4.6 | "vé máy bay" / "vé bay" / "flight" / hãng hàng không | Airfare |
> | DIM-4.7 | "bảo hiểm" / "insurance" | Insurance |
> | DIM-4.9 | "túi thần tài" / "ttt" / "vay nhanh" / "newton" / "ví trả sau" / "vts" | MoMo FS Products |
>
> **Note:** DIM-4.8 (cashback fintech) chuyển sang `07-llm-judge-promo_v1.12.md` vì cashback thường gắn promotional intent.

---

## Dimensions — Domain-specific

#### [DIM-4.4] No lottery financial improvement claims `[HITL-trigger]`
**Áp dụng khi:** body hoặc title chứa từ khoá "Vietlott", "xổ số", "vé số"
**Nguồn:** Nghị định 30/2007/NĐ-CP Điều 21

> **Cơ chế:** MoMo là đối tác chính thức của Vietlott SMS — agent không thể tự phán xét nội dung xổ số có vi phạm hay không nếu thiếu context về partnership. Mọi content Vietlott cần human xác nhận.

**Câu hỏi:** Nội dung có dấu hiệu claim tài chính liên quan xổ số không?
- 🔵 HITL (luôn trigger khi applicable): Content có từ khoá Vietlott/xổ số → cần approver xác nhận nội dung phù hợp với điều khoản đối tác và NĐ 30/2007 Điều 21
- Ghi rõ `hitl_reason`: "Content liên quan Vietlott/xổ số — cần xác nhận không vi phạm NĐ 30/2007 Điều 21 (không claim cải thiện tài chính)"

#### [DIM-4.5] No lottery promotions `[HITL-trigger]`
**Áp dụng khi:** body hoặc title chứa từ khoá "Vietlott", "xổ số", "vé số"
**Nguồn:** Nghị định 30/2007/NĐ-CP Điều 22

> **Cơ chế:** Tương tự DIM-4.4 — agent không phân biệt được khuyến mại xổ số hợp lệ vs vi phạm nếu không có context đối tác. Luôn route HITL.

**Câu hỏi:** Nội dung có dấu hiệu khuyến mại xổ số không?
- 🔵 HITL (luôn trigger khi applicable): Content có từ khoá Vietlott/xổ số + đề cập quà/hoàn tiền/tặng vé → cần approver xác nhận không vi phạm NĐ 30/2007 Điều 22
- Ghi rõ `hitl_reason`: "Content có yếu tố khuyến mại liên quan xổ số — cần xác nhận không vi phạm NĐ 30/2007 Điều 22"

#### [DIM-4.6] Airfare price with conditions
**Áp dụng khi:** body hoặc title chứa từ khoá liên quan vé máy bay ("vé máy bay", "vé bay", hãng hàng không)
**Nguồn:** Thông tư 44/2024/TT-BGTVT
**Câu hỏi:** Nếu nêu giá vé cụ thể, có điều kiện áp dụng và disclaimer chưa bao gồm thuế/phí không? Có claim "giá rẻ nhất/tốt nhất" không rõ điều kiện không?
- ❌ Fail: "Vé bay từ 99k" mà không có "chưa bao gồm thuế phí" hay điều kiện
- ❌ Fail: "Giá vé rẻ nhất Việt Nam" (superlative không có cơ sở)

#### [DIM-4.7] Insurance scope clarity
**Áp dụng khi:** body hoặc title chứa từ khoá "bảo hiểm"
**Nguồn:** Luật Kinh doanh bảo hiểm
**Câu hỏi:** Nội dung có claim "bảo hiểm toàn diện" hoặc phạm vi bảo hiểm/điều kiện bồi thường không rõ ràng không?
- ❌ Fail: "Bảo hiểm toàn diện chỉ 50k/tháng" (claim phạm vi không có cơ sở)

#### [DIM-4.9] MoMo Financial Services product wording `[Reg-floor eligible, NEW v1.10]`
**Áp dụng khi:** title hoặc body chứa keywords liên quan đến 4 sản phẩm Legal-review:
- Túi Thần Tài / TTT
- Vay Nhanh / Fastmoney / FMOB / Newton
- Ví Trả Sau / VTS

**Nguồn:** BOM email 1/4/2026 (scope) + MoMo Legal Content Rules
**Scope override:** CHỈ apply cho 4 products trên — KHÔNG apply cho insurance (DIM-4.7) / cashback (DIM-4.8) / lottery (DIM-4.4-5) / billpay general.

**Câu hỏi (3 nhóm check — chi tiết detection patterns ở `05-guardrail v1.9 Rule 4.9` JSON code block):**

(A) **Vai trò MoMo:** Wording có gọi MoMo là provider của FS product không? ("X của MoMo" / "X do MoMo cung cấp" / "MoMo phát hành X")

(B) **Product blacklist:** Wording có chứa từ cấm theo product cụ thể?
  - TTT: "sản phẩm tiết kiệm", "lãi suất ổn định", "tỷ suất sinh lời ổn định"...
  - Vay Nhanh / Newton: "đầu tư", "kinh doanh", "xoay vốn", "hạn mức", "được cấp khoản vay"...
  - VTS: "nhận ngay xx triệu" (gây hiểu nhầm có sẵn)
  - Universal: "quảng cáo" cho mọi truyền thông MoMo

(C) **Approved wording:** Wording có dùng pattern đúng không? ("X trên MoMo" / "X qua MoMo" / "trả góp Apple qua Vay Nhanh trên MoMo" cho Newton)

**Sub-score:**
- **100:** Wording đúng — dùng "trên MoMo"/"qua MoMo", không blacklist
- **75:** Wording cơ bản đúng, advisory minor
- **50:** 1 blacklist nhẹ ("nhận ngay" cho VTS) hoặc role MoMo borderline
- **25:** Blacklist rõ ("đầu tư"/"hạn mức" cho Vay Nhanh, "tiết kiệm" cho TTT) — **Reg-floor HITL**
- **0:** Vi phạm role attribution ("MoMo cung cấp X") hoặc claim sai bản chất sản phẩm — **Reg-floor HITL**

**Disclaimer policy (clarify scope):** Skill noti **KHÔNG enforce full disclaimer** trong noti body — char limit 30/120 không đủ chỗ cho disclaimer "[Product] được cung cấp bởi các tổ chức tín dụng uy tín qua Ứng dụng MoMo". Disclaimer enforce ở blog/trang sản phẩm (BMC + Legal handle, ngoài scope skill noti). DIM-4.9 chỉ chấm wording compliance.

**HITL routing khi vi phạm:** BMC.

**Fail examples:**
- ❌ 0: "Mở Túi Thần Tài của MoMo, lãi suất ổn định 7%" (role attribution + tiết kiệm claim)
- ❌ 0: "Vay Nhanh từ MoMo cho mọi nhu cầu đầu tư kinh doanh" (role + đầu tư + Vay MoMo)
- ❌ 25: "Mở Ví Trả Sau trên MoMo, nhận ngay 30 triệu" ("nhận ngay" gây hiểu nhầm)
- ❌ 25: "Vay Nhanh hạn mức đến 50 triệu" ("hạn mức" sai bản chất Vay Nhanh)
- ✅ 100: "Mở Ví Trả Sau trên MoMo, hạn mức đến 30 triệu"
- ✅ 100: "Trả góp Apple qua Vay Nhanh trên MoMo, gói vay đến 30 triệu"
