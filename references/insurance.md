# Domain — Insurance / Bảo hiểm

> **Phiên bản:** v1.16 — 05/2026 (split domain rule)
> **Scope:** Rule 4.7 — Bảo hiểm: không gây hiểu nhầm phạm vi
> **Load:** **Lazy** — via `scripts/detect_domain.py` (constant `_INSURANCE_KEYWORDS`)
> **Trigger keywords:** bảo hiểm, bao hiem, insurance, bh ô tô, bh xe, bh sức khỏe, bh nhân thọ
> **HITL routing:** BMC review

---

### Rule 4.7 — Bảo hiểm: không gây hiểu nhầm phạm vi
- **Tier:** 🟡 LLM
- **Nguồn:** Luật Kinh doanh bảo hiểm
- **Áp dụng khi:** Nội dung liên quan đến bảo hiểm
- **Câu hỏi cho LLM:** Nội dung có claim "bảo hiểm toàn diện" hoặc phạm vi bảo hiểm/điều kiện bồi thường không rõ ràng không?

