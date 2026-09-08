# 06 — HITL Policy
## Noti Campaign Agent — MoMo Agentic Marketing Platform

> **Phiên bản:** v1.9 — 05/2026 (refine AI Agreement semantic — `agreement` track INTENT respect không phải action match; add offline_review + review_note + reviewer_team audit fields)
> **Scope:** Quy tắc routing Human-in-the-Loop cho Noti Campaign sau khi qua Tier 0 + Tier 1 + Tier 2 evaluation.
> **Nguồn:** `references/` Rules 5.1, 6.1–6.5, 2.7, 3.4b
> **Ngôn ngữ routing:** Content Type 2-layer "Group/ContentType VN" (UI Athena ↔ API). Không còn hệ thống UC.
> **Version history:** xem `CHANGELOG.md` section **HITL Policy**.

---

## AI Agreement Audit Trace v2 (v1.9+) — Cowork only

**Mục đích:** Capture disagree rate giữa approver vs verdict AI để DA aggregate bi-weekly, làm tiền đề cho automation phase tiếp theo.

**Scope:**
- ✅ Cowork users (duyệt qua Claude / skill)
- ❌ Athena UI direct users (không áp dụng — không có hook intercept)

### Semantic định nghĩa lại (v1.9+)

`ai_agreement` track **WHETHER AI INTENT WAS RESPECTED**, không phải "action có giống suggestion verdict tag không". Phân biệt rõ:

**`ai_agreement = yes`** — AI intent respected:
- AI QUALIFIED → approver approves
- AI HITL → team X → **approver thuộc team X** review + approve/reject (HITL outcome positive)
- AI HITL → team X → **cross-team approver coordinate offline** với team X trước khi action (offline_review=yes)
- AI REJECT → approver rejects
- AI WARNING → approver approves WITH offline review

**`ai_agreement = no`** — genuine override (no review path):
- AI HITL → team X → cross-team approver **bypass review** (no offline coordination)
- AI REJECT → approver approves (skip rule)
- AI QUALIFIED → approver rejects without justification
- AI WARNING → approver approves without offline review

### Audit footer schema v2 (expanded)

**BẮT BUỘC khi Cowork user duyệt:**

```
—— [ai_verdict=<V>] [ai_agreement=yes|no] [offline_review=yes|no] [review_note=<text>] [reviewer_team=<team>] [disagree_reason=<text>]
```

| Field | Required | Note |
|---|---|---|
| `ai_verdict` | Always | `QUALIFIED \| WARNING \| HITL_REQUIRED \| NOT_QUALIFIED` |
| `ai_agreement` | Always | `yes` (intent respected) hoặc `no` (genuine override) |
| `offline_review` | Optional — khi action ≠ AI suggest | `yes` (reviewed offline) hoặc `no` |
| `review_note` | **MANDATORY khi `offline_review=yes`** | Brief context (vd "PCS reviewed", "BMC offline OK") |
| `reviewer_team` | Optional — recommend khi action ≠ AI suggest | Approver acting team |
| `disagree_reason` | **MANDATORY khi `ai_agreement=no`** | Natural VN reason |

### Phase 4.0 2-step gate flow

**Bước 1:** Agent show summary table + verdict, ask approver xác nhận:
```
- "agree all" / "agree N1,N2" → action match AI → fire trực tiếp
- "approve/reject N1,N2: ..." → action ≠ AI → agent ASK followup Bước 2
```

**Bước 2 (followup khi action ≠ AI suggest):**
```
Action chị chọn KHÁC với AI suggest cho campaign #N.
Chị đã review offline rồi chưa?
- "yes: <note>"        → offline_review=yes, ai_agreement=yes, capture review_note
- "no, override"       → offline_review=no, ai_agreement=no, capture disagree_reason
```

### DA extract pattern (regex v2)

- `\[ai_verdict=([^\]]+)\]`
- `\[ai_agreement=(yes|no)\]`
- `\[offline_review=(yes|no)\]?` (optional)
- `\[review_note=([^\]]*)\]?`
- `\[reviewer_team=([^\]]+)\]?`
- `\[disagree_reason=([^\]]*)\]?`

**Backward compat:** Footer v1 (chỉ 3 fields ai_verdict/ai_agreement/disagree_reason) vẫn parse được — DA team treat missing fields as null.

**Implementation chi tiết:** xem `skill/noti-campaign-approval.md` Phase 4.0 + Phase 5 audit footer pattern v2.

---

## Tổng quan — Decision Matrix

| Điều kiện | Kết quả | Approver | Auto? |
|---|---|---|---|
| Tier 0 FAIL — unknown approver (review mode) | BLOCKED | N/A | Không — liên hệ tech admin cấu hình role-mapping.json |
| Tier 0 FAIL — wrong approver (review mode) | BLOCKED + redirect | Expected team | Không — chuyển campaign đến đúng team |
| Tier 1 FAIL (bất kỳ rule nào) | BLOCKED | N/A | Không — yêu cầu sửa |
| Tier 1 format violation + Group Quan trọng | HITL | **PCS** (toàn bộ group Quan trọng) | Không — reviewer sửa + approve thủ công |
| Tier 2 LLM phát hiện typo (DIM-3.4b) | HITL bắt buộc | Theo Group/CT (xem section "Typo HITL — DIM-3.4b" bên dưới) | Không — approver xác nhận typo thật / false positive |
| Score < 50 | REJECT | N/A | Không — yêu cầu sửa |
| Score 50–84 + Bất kỳ content_type | WARNING | Theo Group/CT (bảng dưới) | Không — manual review |
| Score ≥ 85 + Group Quan trọng (Giao dịch/Nhắc nhở/Cảnh báo/Dịch vụ) | PASS | PCS | Không — PCS duyệt bắt buộc |
| Score ≥ 85 + Tương tác/Khảo sát (`SURVEY`) | PASS | CIO | Không — CIO duyệt bắt buộc |
| Score ≥ 85 + Group Ưu đãi hoặc Tương tác (trừ Khảo sát) | PASS | Hệ thống | Có — auto-SCHEDULED |
| Segment > 5 triệu (bất kỳ score nào) | DUAL FLAG | **Growth** + content-group approver (PCS/BMC theo CT) | Không — cả 2 team confirm song song |

---

## Chi tiết Routing theo Content Type

### Nhóm PCS — toàn bộ Group "Quan trọng" (Bắt buộc duyệt manual, kể cả score ≥ 85)

| Group/Content Type VN | API code | Lý do bắt buộc |
|---|---|---|
| Quan trọng/Giao dịch | `TRANSACTION` | Quan trọng — exceptional rule |
| Quan trọng/Nhắc nhở | `REMIND` | Quan trọng — exceptional rule |
| Quan trọng/Cảnh báo | `WARNING` | Quan trọng — exceptional rule |
| Quan trọng/Dịch vụ | `SERVICE` | Quan trọng — exceptional rule |

**Hành động khi route PCS:**
- Campaign submit → agent thông báo Growth "Campaign [tên] đang chờ PCS duyệt"
- Alert PCS tại T-60m (single) hoặc T-90m (A/B test) trước push time
- PCS có deadline duyệt: T-30m (single) hoặc T-60m (A/B test)

---

### Nhóm BMC — Group "Ưu đãi" + "Tương tác" (trừ Khảo sát)

| Group/Content Type VN | API code | Score 50–84 | Score ≥ 85 |
|---|---|---|---|
| Ưu đãi/Khuyến mãi* | `PROMOTION*` | BMC manual review | Auto-SCHEDULED |
| Ưu đãi/Game | `GAME` | BMC manual review | Auto-SCHEDULED |
| Ưu đãi/Quảng cáo | `ADVERTISING` | BMC manual review | Auto-SCHEDULED |
| Ưu đãi/Sự kiện | `EVENT` | BMC manual review | Auto-SCHEDULED |
| Tương tác/Bạn bè | `FRIENDS` | BMC manual review | Auto-SCHEDULED |
| Tương tác/Business Page | `BUSINESS_PAGE` | BMC manual review | Auto-SCHEDULED |
| Tương tác/Social | `SOCIAL` | BMC manual review | Auto-SCHEDULED |

**Hành động khi route BMC (score 50–84):**
- Campaign submit → agent thông báo "Campaign [tên] đang chờ BMC review"
- Alert BMC tại T-60m (single) hoặc T-90m (A/B test)
- BMC có thể approve → auto-SCHEDULED hoặc reject → Growth chỉnh sửa

---

### Nhóm CIO (Bắt buộc duyệt manual — kể cả score ≥ 85)

| Group/Content Type VN | API code | Lý do bắt buộc |
|---|---|---|
| Tương tác/Khảo sát | `SURVEY` | Exceptional rule — không auto-schedule |

**Hành động khi route CIO:**
- Agent chỉ hỗ trợ soạn nội dung noti mời khảo sát, không tạo campaign độc lập
- Campaign submit → agent thông báo Growth "Campaign Khảo sát đang chờ CIO duyệt"
- Growth liên hệ CIO để review
- Không enable auto-SCHEDULED dù score bất kỳ

---

## Segment Size Gate — Dual Review (Rule 5.1, v1.7+)

```
THRESHOLD = 5,000,000

if segment_size > THRESHOLD:
    STATUS = "HOLD — Pending DUAL HITL confirm (Growth + content-group approver)"
    MESSAGE = "Segment '[tên]' có [N] user — vượt ngưỡng 5 triệu.
              Cần Growth team validate segment + [PCS/BMC] reconfirm
              business impact trước khi approve."
    ACTION = Dừng flow, chờ CẢ 2 team confirm bằng văn bản rõ ràng
    NOTE = Rule này áp dụng THÊM vào routing bình thường, không thay thế
```

**Content-group approver mapping (per CT):**

| CT group | Reconfirm approver |
|---|---|
| Quan trọng (TRANSACTION/REMIND/WARNING/SERVICE) | **PCS** |
| Ưu đãi (PROMOTION*/GAME/ADVERTISING/EVENT) | **BMC** |
| Tương tác (FRIENDS/BUSINESS_PAGE/SOCIAL) | **BMC** |
| SURVEY | N/A — SURVEY có hard cap 250K riêng (Rule 6.5), không reach 5M được |

**Workflow:**
1. Agent flag campaign với 2 suggested teams (Growth + content-group)
2. Summary table hiển thị `team={Growth,PCS}` hoặc `team={Growth,BMC}` (comma-separated)
3. Cả 2 team phải confirm trước khi approve
4. PLATFORM_OPERATOR có thể override single-handedly với `override=true | just=platform_authority_dual_skip` — audit trace bắt buộc

**Sau khi cả 2 team confirm:**
- Tiếp tục flow bình thường (submit + routing theo content_type và score)
- Audit log thêm `dual_review=true` khi action=APPROVE
- Lưu confirmation từng team riêng (Growth confirm timestamp + content-group confirm timestamp)

---

## Group Quan trọng — Format Violation HITL (Rule 2.7)

Khi content_type thuộc Group Quan trọng (Giao dịch/Nhắc nhở/Cảnh báo/Dịch vụ) và phát hiện vi phạm format:

```
Rule 2.1 (title dài)  → HITL thay vì REJECT
Rule 2.2 (body dài)   → HITL thay vì REJECT
Rule 2.3 (newline/bullet) → HITL thay vì REJECT
Rule 2.6 (param sai)  → HITL thay vì REJECT
Rule 2.4 (PII)        → LUÔN REJECT, không ngoại lệ
```

**Lý do thiết kế:**
- Nội dung Quan trọng (bảo trì, sự cố) không nên bị tự động block — user cần được thông báo kịp thời
- Reviewer nhận HITL kèm checklist lỗi cụ thể → sửa xong approve ngay

**HITL message format:**
```
"[Format issues detected]
- Rule [X]: [mô tả lỗi]
- Gợi ý: [cách sửa cụ thể]

Nội dung Quan trọng — không thể auto-reject. Reviewer xem xét, sửa và approve thủ công."
```

**Routing:**
- Toàn bộ Group Quan trọng (Giao dịch/Nhắc nhở/Cảnh báo/Dịch vụ) → **PCS**
- Không còn ngoại lệ nào thuộc Group Quan trọng route sang BMC.

---

## Typo HITL — DIM-3.4b (v1.5+)

Khi DIM-3.4b (Spelling check) trong Tier 2 LLM phát hiện bất kỳ:
- Lỗi typo tiếng Việt (sai dấu, sai từ, thiếu dấu)
- Lỗi spelling tiếng Anh
- Suspected proper noun (từ viết hoa không khớp brand whitelist)

→ `hitl_triggered: true`, **block auto-approve bất kể score Tier 2 LLM** (kể cả score ≥ 85).

### Routing theo Group/Content Type

| Group/CT của campaign | Approver HITL | Lý do |
|---|---|---|
| Group Quan trọng (Giao dịch/Nhắc nhở/Cảnh báo/Dịch vụ) | **PCS** | Quan trọng đã bắt buộc PCS — typo gộp chung vào HITL queue PCS |
| Group Ưu đãi (Khuyến mãi/Game/Quảng cáo/Sự kiện) | **BMC** | BMC sở hữu Ưu đãi — typo trong copy quảng cáo cần BMC verify |
| Group Tương tác — Bạn bè/Business Page/Social | **BMC** | BMC sở hữu Tương tác (trừ SURVEY) |
| Group Tương tác — Khảo sát (SURVEY) | **CIO** | CIO bắt buộc cho SURVEY — typo gộp chung |

### Lý do thiết kế

- **Không reject thẳng:** LLM có rủi ro false positive (slang, regional spelling, brand mới chưa whitelist, từ tiếng nước ngoài). Reject thẳng → owner mất công resubmit khi không có lỗi thật.
- **Không cho auto-approve:** Typo trong noti push đến hàng nghìn user → mất trust + brand integrity. Phải có human verify.
- **Approver có 2 lựa chọn:**
  1. **Confirm typo thật** → reject + comment cụ thể "Sửa '[X]' thành '[Y]'", owner fix + resubmit
  2. **Confirm false positive** → approve thủ công + comment "Approved with typo flag — '[X]' là [slang/brand/regional], không phải lỗi"

### HITL message format (cho Typo)

```
"[Typo flag from DIM-3.4b]
Phát hiện trong [title/body]:
- '[từ sai]' → gợi ý: '[từ đúng]'
- (Nếu suspected proper noun: 'Từ [X] có vẻ là tên riêng — xác nhận cách viết đúng')

Approver xác nhận:
[ ] Typo thật → reject + yêu cầu owner fix
[ ] False positive (slang/brand/regional) → approve manual + giải thích trong comment"
```

---

## Alert Deadline (Rule 6.4)

### Timeline alert

```
Single Campaign:
├── T-2h:    Submit deadline (system-enforced, agent không cần check)
├── T-60m:   ⚡ Agent gửi alert đến Approver (action required)
├── T-30m:   ❌ Deadline duyệt (hardcoded Athena) — sau đây campaign bị miss
└── T-0:     Push time

A/B Test Campaign:
├── T-2h:    Submit deadline (system-enforced)
├── T-90m:   ⚡ Agent gửi alert đến Approver (action required)
├── T-60m:   ❌ Deadline duyệt (hardcoded Athena)
└── T-0:     Push time
```

### Alert message template

```
[Single Campaign]:
"[Single] Campaign '[tên campaign]' cần được duyệt trước [T-30m timestamp]. Còn [X] phút."

[A/B Test Campaign]:
"[A/B Test] Campaign '[tên campaign]' cần được duyệt trước [T-60m timestamp]. Còn [X] phút."
```

---

## Approver Identity (Tier 0)

> Áp dụng ở **review mode** để xác định ai đang thực hiện review trước khi chạy Tier 1.

### Cơ chế hoạt động

```
1. Decode ATHENA_TOKEN từ config.env
   → lấy account_id và email của reviewer

2. Tra role-mapping.json (schema v2.0 — content_type based):
   PCS  → can_approve.groups: ["Quan trọng"]                       (toàn bộ Group Quan trọng)
   BMC  → can_approve.groups: ["Ưu đãi", "Tương tác"]              (trừ exclude_content_types)
          exclude_content_types: ["SURVEY"]
   CIO  → can_approve.content_types: ["SURVEY"]                    (Khảo sát)

3. Nếu account_id không trong bất kỳ team:
   → BLOCKED: UNKNOWN APPROVER
   → Action: liên hệ tech admin đăng ký trong role-mapping.json

4. Nếu team không có quyền duyệt content_type của campaign:
   → BLOCKED: WRONG APPROVER
   → Action: chuyển campaign đến đúng team

5. Nếu OK → ghi nhận reviewer_team + email, tiếp tục Tier 1
```

### Lưu ý triển khai

- Mỗi approver (PCS, BMC, CIO) phải dùng `ATHENA_TOKEN` cá nhân trong `config.env` của họ — không dùng chung token nhóm.
- Athena đã enforce approval permission ở API level. Tier 0 là lớp cảnh báo sớm (early warning) — không thay thế Athena.
- Nếu `role-mapping.json` chưa cấu hình → bỏ qua Tier 0, log cảnh báo, tiếp tục Tier 1.
- Hướng dẫn cấu hình: xem `admin-setup.md`.

---

## Bypass Policy

> **Tuyệt đối không được dùng Approval type BYPASS trong agent.**

- Type BYPASS chỉ Platform role xử lý case by case
- Khi dùng BYPASS: ML rules không áp dụng, capset bị bỏ qua
- Mọi campaign agent tạo phải dùng Approval type **NORMAL**
- Nếu Growth yêu cầu BYPASS → hướng dẫn liên hệ Platform role qua ticket riêng

---

## Escalation Path

Khi campaign bị block và Growth không tự xử lý được:

```
Block loại                     → Liên hệ
─────────────────────────────────────────
Content type ngoài danh sách   → PCS để tư vấn
In-app format request          → platform-customer-success@mservice.com.vn
Khảo sát (SURVEY)              → CIO team (Growth là đầu mối)
Segment > 5M                 → Growth manager confirm
Bypass request                 → Platform role (ticket riêng)
```

---

*Tạo: 04/2025 — v1.0*
*Cập nhật: 04/2025 — v1.1: thêm Tier 0 Approver Identity; thêm 2 row Decision Matrix (unknown/wrong approver); cập nhật scope note*
*Cập nhật: 04/2025 — v1.2: thêm Rule 2.7 — Content type Quan trọng format violation → HITL (PII vẫn REJECT); cập nhật Decision Matrix; thêm section "Content type Quan trọng — Format Violation HITL"*
*Cập nhật: 04/2026 — v1.3: chuyển sang vocabulary "Group/Content Type VN" (2-layer) — 14 content_type API từ bảng UI Athena; fix Quan trọng/Dịch vụ + Quan trọng/Nhắc nhở route BMC → PCS để nhất quán rule "Quan trọng/* = PCS"; Decision Matrix, bảng Nhóm PCS/BMC/CIO, section Rule 2.7 và pseudo-code Tier 0 đều rewrite theo content_type.*
*Cập nhật: 04/2026 — v1.4: xóa hoàn toàn hệ thống legacy use_case codes — routing 100% content_type/group; role-mapping.json schema v2.0 với groups + content_types + exclude_content_types; pseudo-code Tier 0 và Escalation Path update theo vocabulary mới.*
*Cập nhật: 04/2026 — v1.5: Decision Matrix thêm row "Tier 2 LLM phát hiện typo (DIM-3.4b)" → HITL bắt buộc; thêm section "Typo HITL — DIM-3.4b" với routing table theo Group/CT (PCS/BMC/CIO), lý do thiết kế (false positive risk + brand integrity), HITL message format cho approver có 2 lựa chọn confirm/false-positive.*
*Dựa trên: 05-guardrail-rule-sheet_v1.7.md Rules 5.1, 6.1–6.5*
*File liên quan: skill_v2.1.md · 07-llm-judge-core_v1.12.md · role-mapping.json v2.0 · admin-setup.md*
