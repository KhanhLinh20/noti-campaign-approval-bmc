# 04 — Regulatory General (LLM Judge Input)
## Noti Campaign Agent — Group Nhóm 4 (general rules)

> **Phiên bản:** v1.16 — 05/2026 (split from monolith)
> **Scope:** Rules 4.1 (absolute claims), 4.2 (discrimination), 4.3 (Vietnamese language) — áp dụng MỌI campaign
> **Load:** Always (Tier 2 LLM Judge)
> **Domain-specific** (lazy load): Rules 4.4-4.9 ở các file domain riêng trong `references/` (`fs-products.md`, `vietlott.md`, `airfare.md`, `insurance.md`, `cashback-fintech.md`, `survey-cio.md`). Xem 00-core-rules index.

---

## Nhóm 4 — Regulatory (LLM Judge Input)

> Các rule này cũng là input cho LLM Judge — xử lý chung trong file 07. Tách riêng nhóm để dễ maintain khi luật thay đổi.

### Rule 4.1 — Không gây hiểu lầm về sản phẩm/dịch vụ (absolute product claims)
- **Tier:** 🟡 LLM (Reg-floor eligible)
- **Nguồn:** Luật Quảng cáo 2012 Điều 8
- **Scope (v1.8+ — phân biệt rõ với Rule 3.7):** Rule 4.1 tập trung vào **absolute product claims / superlatives không có cơ sở** — vi phạm Luật Quảng cáo.
- **Câu hỏi cho LLM:** Nội dung có claim absolute/superlative mà không có cơ sở pháp lý hoặc third-party verification không?
- **Sub-score:**
  - **0:** Claim absolute rõ ràng — "**tốt nhất**", "**duy nhất**", "**số 1**", "**hàng đầu**", "**không ai sánh bằng**", "**tuyệt đối**", "**đảm bảo**", "**100% an toàn**", "**ưu đãi nhất**" — vi phạm Luật Quảng cáo → **Reg-floor HITL**
  - **25:** Claim sai sự thật nhẹ, cần sửa (VD: mô tả tính năng chưa có)
  - **75:** Mild superlative có thể chấp nhận ("một trong những", "rất tốt")
  - **100:** Không có claim tuyệt đối
- **Phân biệt với Rule 3.7:**
  - **Rule 4.1** (đây): superlatives/absolute → vi phạm Luật Quảng cáo (Reg-floor)
  - **Rule 3.7:** số cụ thể thiếu điều kiện → vi phạm Content Guideline promotional

### Rule 4.2 — Không kỳ thị, phân biệt đối xử
- **Tier:** 🟡 LLM
- **Nguồn:** Luật Quảng cáo 2012 Điều 8, khoản 6
- **Câu hỏi cho LLM:** Nội dung có ngôn ngữ kỳ thị dân tộc, tôn giáo, giới tính, người khuyết tật không?

### Rule 4.3 — Nội dung phải có tiếng Việt
- **Tier:** 🟡 LLM
- **Nguồn:** Luật Quảng cáo 2012 (quy định ngôn ngữ)
- **Câu hỏi cho LLM:** Nội dung có hoàn toàn bằng tiếng nước ngoài không? (Tên thương hiệu quốc tế được phép)

