# Domain — Cashback / Fintech / Ví điện tử

> **Phiên bản:** v1.16 — 05/2026 (split domain rule)
> **Scope:** Rule 4.8 — Cashback/Fintech: hoàn tiền/ưu đãi phải có điều kiện rõ ràng (Reg-floor eligible khi vague)
> **Load:** **Lazy** — via `scripts/detect_domain.py` (constant `_CASHBACK_FINTECH_KEYWORDS`)
> **Trigger keywords:** hoàn tiền, hoan tien, cashback, lãi suất, lai suat, tích lũy, tich luy
> **HITL routing:** BMC review

---

### Rule 4.8 — Fintech/Ví điện tử: hoàn tiền/ưu đãi phải có điều kiện
- **Tier:** 🟡 LLM (Reg-floor eligible)
- **Nguồn:** Quy định NHNN về ví điện tử
- **Áp dụng khi:** Nội dung về hoàn tiền, cashback, lãi suất
- **Câu hỏi cho LLM (v1.8+ — expanded scope):**
  - (a) Nội dung nêu **% hoàn tiền / lãi suất cụ thể** mà không có điều kiện tối thiểu không?
  - (b) Nội dung đề cập "hoàn tiền / cashback / lãi suất" kiểu **vague** ("hấp dẫn", "ưu đãi", "lớn", "khủng") **không có specifics** nào?
  - (c) Có ≥ 1 điều kiện rõ ràng (tối đa X, mỗi giao dịch, chỉ user mới, lần đầu…) không?
- **Sub-score:**
  - **100:** Có ≥ 1 điều kiện rõ ràng ("Hoàn 20% tối đa 100k cho giao dịch đầu tiên")
  - **50:** Có % cụ thể nhưng điều kiện chưa đầy đủ ("Hoàn 20% cho đơn đầu" — thiếu cap)
  - **25:** Vague cashback không specifics ("hoàn tiền hấp dẫn", "cashback ưu đãi") — **Reg-floor HITL**
  - **0:** % cụ thể + zero conditions ("Hoàn 50% không giới hạn") — **Reg-floor HITL**

---

