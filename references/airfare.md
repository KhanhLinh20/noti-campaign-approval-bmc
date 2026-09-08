# Domain — Airfare / Vé máy bay

> **Phiên bản:** v1.16 — 05/2026 (split domain rule)
> **Scope:** Rule 4.6 — Vé máy bay: giá phải có điều kiện rõ
> **Load:** **Lazy** — via `scripts/detect_domain.py` (constant `_AIRFARE_KEYWORDS`)
> **Trigger keywords:** vé máy bay, ve may bay, vé bay, ve bay, flight, airline, vietjet, vietnam airlines, bamboo airways
> **HITL routing:** BMC review

---

### Rule 4.6 — Vé máy bay: giá phải có điều kiện rõ
- **Tier:** 🟡 LLM
- **Nguồn:** Thông tư 44/2024/TT-BGTVT
- **Áp dụng khi:** Nội dung liên quan đến vé máy bay
- **Câu hỏi cho LLM:** Nếu nội dung nêu giá vé cụ thể, có điều kiện áp dụng và disclaimer về thuế/phí chưa bao gồm không? Có claim "giá tốt nhất/rẻ nhất" không rõ điều kiện không?

