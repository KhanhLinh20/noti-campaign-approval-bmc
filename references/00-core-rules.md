# 05 — Guardrail Rule Sheet
## Noti Campaign Agent — MoMo Agentic Marketing Platform

> **Phiên bản:** v1.16 — 05/2026 (cosmetic sync với 01-06 core files; index/Tier structure unchanged từ v1.15)
> **Nguồn:** Athena Notification Guideline (03/2025) · MoMo Notification Detail Guideline · Notification Content Guideline 2025 (MKT)
> **Scope:** Chỉ áp dụng cho **Noti Campaign** (Delivery Method = Campaign). Noti Template nằm ngoài scope file này.
> **Vocabulary:** 100% content_type-based theo bảng UI Athena (Group + Content Type VN ↔ API code). Không còn hệ thống UC.
> **Không bao gồm:** Rules đã được hệ thống Athena enforce sẵn (capset, timeslot, submit deadline) — xem ghi chú phần System-Enforced ở cuối file.

---

## Cấu trúc Tier

| Tier | Ký hiệu | Mô tả | Ai xử lý |
|---|---|---|---|
| Tier 0 Identity | 🟣 | Auto-detect approver từ JWT, validate quyền — chỉ review mode | Agent tự xử lý |
| Tier 1 Script | 🔴 | Hard check bằng code/regex — block hoặc alert ngay | Agent tự xử lý |
| Tier 2 LLM | 🟡 | Đánh giá ngữ nghĩa qua LLM Judge — trả về score 0–100 | LLM Judge (file 07) |
| Tier 3 HITL | 🔵 | Routing logic — quyết định ai duyệt, điều kiện nào | Config trong hệ thống |

**Score logic:**
- **< 50** → Reject, agent/Growth chỉnh sửa (hoặc tạo manual nếu insist)
- **50–84** → Cảnh báo mức vàng — có thể tiếp tục hoặc chỉnh sửa
- **≥ 85** → Pass, agent tạo không cần confirm (trừ Group Quan trọng và SURVEY)

---


---

## File index — split guardrail v2.0 (Option B deep split)

| File | Scope | Load |
|---|---|---|
| `00-core-rules.md` | Tier structure + system-enforced + index | **Always** |
| `01-content-type-format.md` | Nhóm 1 (Rules 1.1-1.8) | **Always** |
| `02-content-hard-checks.md` | Nhóm 2 (Rules 2.1-2.11, đa số có script) | **Always** |
| `03-content-quality.md` | Nhóm 3 DIM rubric (Rules 3.1-3.18) | **Always** (Tier 2 LLM) |
| `04-regulatory-general.md` | Nhóm 4 general (Rules 4.1, 4.2, 4.3) | **Always** (Tier 2 LLM) |
| `05-segment.md` | Nhóm 5 (Rules 5.1, 5.2) | **Always** |
| `06-routing.md` | Nhóm 6 (Rules 6.1-6.4, 6.7) | **Always** |
| `fs-products.md` | Rule 4.9 (TTT/Vay Nhanh/VTS) | **Lazy** (FS keyword detected) |
| `vietlott.md` | Rules 4.4, 4.5 | **Lazy** (Vietlott keyword) |
| `airfare.md` | Rule 4.6 | **Lazy** (airfare keyword) |
| `insurance.md` | Rule 4.7 | **Lazy** (insurance keyword) |
| `cashback-fintech.md` | Rule 4.8 | **Lazy** (cashback keyword) |
| `survey-cio.md` | Rule 6.5 expanded | **Lazy** (CT=SURVEY) |

**Domain detection:** `scripts/detect_domain.py` keyword scan title+body+CT → return list domains to load.

---

## Ghi chú — System-Enforced Rules (không cần viết guardrail)

> Các rule sau đã được hệ thống Athena enforce sẵn. Engineer **không cần implement** lại. Ghi lại để tránh duplicate effort.

| Rule | Mô tả | Enforce bởi |
|---|---|---|
| Capset Ưu đãi | 3 noti/tuần/user, 1 noti/ngày/user | Athena ML Capset |
| Capset Tương tác | 3 noti/tuần/user | Athena ML Capset |
| Capset Survey | 1 noti/30 ngày/user | Athena ML Capset |
| Capset Quan trọng | Không giới hạn | Athena ML Capset |
| Push time 8AM–9PM | Timeslot dropdown chỉ hiện khung này | Athena UI |
| Timeslot conflict | Không cho chọn timeslot đã có campaign | Athena UI |
| Submit deadline T-2h | Hệ thống tự block sau T-2h | Athena system |
| Submit deadline T-1h30m | Campaign đang edit approval | Athena system |
| Không có ngày cấm | Áp dụng thứ 2–CN, kể cả lễ/tết | Athena system |
| Segment visibility | Chỉ thấy segment cùng account | Athena system |
| Push test | Tool force push test trước khi Submit for Review — campaign chỉ sang được trạng thái "In Review" sau khi đã push test thành công | Athena tool (forced step) |
| Approval permission | Athena validate account_id có quyền approve content_type tương ứng — skill-level Tier 0 check là early warning / UX, Athena là lớp enforce cuối | Athena API (confirmed) |

---

## Pending — Chưa có đủ thông tin

| # | Item | Chờ ai | Ghi chú |
|---|---|---|---|
| P1 | Monitoring thresholds (CTR drop, opt-out spike, complaint rate) | Data Analytics / Growth | Thuộc eval framework — define sau |

---

*Version history: xem `CHANGELOG.md` root folder, section **Guardrail**.*
*Dựa trên: _draft-rule-inventory.md v4*
*File liên quan: references/06-hitl-policy_v1.9.md · references/07-llm-judge-core_v1.12.md · references/08-batch-review-template_v1.9.md · references/09-dashboard-html-template_v1.4.html · references/noti-campaign-approval.md*
*Convention: filename match latest internal version, rename khi bump.*
