# Domain — Vietlott / Xổ số

> **Phiên bản:** v1.16 — 05/2026 (split domain rule)
> **Scope:** Rules 4.4, 4.5 — Xổ số/Vietlott regulatory (Nghị định 30/2007)
> **Load:** **Lazy** — via `scripts/detect_domain.py` (constant `_VIETLOTT_KEYWORDS`)
> **Trigger keywords:** vietlott, xổ số, xo so, vé số, ve so, lottery, trúng số, trung so, jackpot
> **HITL routing:** Luôn HITL → BMC + Legal review

---

### Rule 4.4 — Xổ số/Vietlott: không claim cải thiện tài chính
- **Tier:** 🟡 LLM
- **Nguồn:** Nghị định 30/2007/NĐ-CP Điều 21
- **Áp dụng khi:** Nội dung liên quan đến Vietlott, xổ số
- **Câu hỏi cho LLM:** Nội dung có claim rằng tham gia xổ số sẽ cải thiện tài chính không? ("làm giàu", "đảm bảo trúng", "cải thiện thu nhập")

### Rule 4.5 — Xổ số/Vietlott: không khuyến mại
- **Tier:** 🟡 LLM
- **Nguồn:** Nghị định 30/2007/NĐ-CP Điều 22 — nghiêm cấm khuyến mại xổ số dưới mọi hình thức
- **Áp dụng khi:** Nội dung liên quan đến Vietlott, xổ số
- **Câu hỏi cho LLM:** Nội dung có thực hiện khuyến mại xổ số không? ("mua vé nhận quà", "hoàn tiền khi mua vé số", "tặng vé")

