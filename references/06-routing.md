# 06 — Approval Routing
## Noti Campaign Agent — Group Nhóm 6 (general routing)

> **Phiên bản:** v1.16 — 05/2026 (split from monolith)
> **Scope:** Rules 6.1, 6.2 (score-based routing), 6.3 (Group/CT routing), 6.4 (deadline alert), 6.7 (priority BYPASS Platform-only)
> **Load:** Always (Phase 0 mandatory)
> **Rule 6.5 SURVEY** (lazy load): chuyển sang `survey-cio.md` vì 200 lines applicable chỉ cho SURVEY campaign.

---

## Nhóm 6 — Approval Routing

> Nguyên tắc: Tất cả campaign phải duyệt type **NORMAL** để apply ML rules đầy đủ. Type **BYPASS** chỉ Platform role xử lý case by case — agent không được propose.

### Rule 6.1 — Score-based routing (Luồng tạo)
- **Tier:** 🔵 HITL
- **Logic:**
  - Score < 50 → **Reject**, trả lý do cụ thể, yêu cầu chỉnh sửa
  - Score 50–84 → **Cảnh báo vàng**, agent/Growth có thể chỉnh hoặc confirm tiếp
  - Score ≥ 85 + Group **KHÔNG phải Quan trọng** và content_type ≠ `SURVEY` → Agent tạo không cần confirm thêm
  - Score ≥ 85 + Group **Quan trọng** → vẫn phải qua Growth review bình thường trước khi submit

### Rule 6.2 — Score-based routing (Luồng duyệt)
- **Tier:** 🔵 HITL
- **Logic:**
  - Score 50–84 → Approver **manual review** (HITL)
  - Score ≥ 85 + non-Quan trọng + non-SURVEY → **Hệ thống tự approve** (auto-SCHEDULED)
  - Score ≥ 85 + Group **Quan trọng** → **PCS duyệt bắt buộc** dù score cao (exceptional rule)
  - Score ≥ 85 + content_type `SURVEY` → **CIO duyệt bắt buộc** dù score cao (exceptional rule)

### Rule 6.3 — Route to approver theo Group/Content Type
- **Tier:** 🔵 HITL
- **Logic (theo group + content_type):**

| Group | Content Type | Approver | Điều kiện |
|---|---|---|---|
| Quan trọng | Giao dịch / Nhắc nhở / Cảnh báo / Dịch vụ | **PCS** | Bắt buộc, dù score ≥ 85 |
| Ưu đãi | Khuyến mãi* / Game / Quảng cáo / Sự kiện | BMC | Score 50–84 manual; ≥85 auto |
| Tương tác | Bạn bè / Business Page / Social | BMC | Score 50–84 manual; ≥85 auto |
| Tương tác | Khảo sát (`SURVEY`) | **CIO** | Bắt buộc, dù score ≥ 85 |

### Rule 6.7 — Priority: chỉ NORMAL hoặc BYPASS, Agent cấm propose BYPASS
- **Tier:** 🔴 Script
- **Trigger:** Agent chuẩn bị submit campaign với priority

**Policy v1.8+ — chỉ chấp nhận 2 priority:**
- **`NORMAL`** — default, apply đầy đủ ML rules + capset + filter + personalization. Agent dùng cho mọi case approve thông thường.
- **`BYPASS`** — Platform role quyết định case-by-case (sự cố, critical announcement). Bỏ qua ML filter + capset relaxed → rủi ro spam nếu dùng sai. Agent **tuyệt đối không propose**.

**`HIGH` đã deprecate khỏi UX skill v1.2+** — dù MCP API vẫn nhận giá trị `HIGH`, policy MoMo standardize chỉ NORMAL/BYPASS để giảm confusion cho Growth + approver. Skill agent không expose option HIGH trong confirm panel.

**Logic:**
- Agent **tuyệt đối không** được propose hoặc chọn `priority=BYPASS` khi `action=APPROVED`
- BYPASS chỉ Platform role (Notification Operator / Platform Operator) quyết định case-by-case
- Auto-select BYPASS bởi AI = rủi ro spam, vi phạm capset

**Scope rule (clarify khi áp dụng):** Rule CHỈ cấm khi `action=APPROVED + priority=BYPASS`. KHÔNG cấm:
- List / view / fetch campaign đang ở state priority=BYPASS (OK)
- Reject / stop campaign BYPASS (OK — cleanup hợp lệ; reject không cần priority param)
- Approve với priority=NORMAL (default, OK)

**Error messages:**
- Agent tự chọn BYPASS: `"Priority BYPASS chỉ dành cho Platform role quyết định case-by-case. Agent dùng priority=NORMAL. Nếu cần BYPASS, liên hệ Platform Customer Success."`
- User chọn HIGH (legacy UI): `"Priority HIGH đã deprecate. Vui lòng dùng NORMAL hoặc liên hệ Platform để đổi sang BYPASS."`

**Implementation note:** Hard block BYPASS trong agent code. UX confirm panel chỉ offer 2 option: NORMAL / BYPASS (kèm warning).

---


### Rule 6.4 — Alert Approver trước deadline
- **Tier:** 🔴 Script (alert)
- **Logic:** Sau khi campaign submit thành công, agent tính countdown và gửi alert:
  - Single campaign: alert khi còn **T-60m** (deadline duyệt là T-30m — hardcoded bởi hệ thống)
  - A/B Test campaign: alert khi còn **T-1h30m** (deadline duyệt là T-1h — hardcoded)
- **Alert message:** `"[Single/A/B] Campaign '[tên]' cần được duyệt trước [giờ]. Còn [X] phút."`
- **Implementation note:** Deadline T-30m và T-1h là hardcoded trong Athena. Agent cần Alert sớm hơn để Approver aware các campaign phải duyệt manual.

---

