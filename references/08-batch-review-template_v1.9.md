# 08 — Batch Review Report Template
## Noti Campaign Auto-Approve — Định dạng báo cáo hiển thị trong chat

> **Phiên bản:** v1.9 — 05/2026 (Phase 4.0 2-step gate + audit footer schema v2 — refine AI Agreement semantic: track INTENT respect không phải action match)
> **Scope:** Định dạng chuẩn cho output của Batch Review Mode (Bước 3 trong `skill_v2.1.md`).
> **Mục tiêu:** Dễ đọc, đủ thông tin để approver ra quyết định ngay trong khung chat, không cần mở thêm công cụ nào khác.
> **Vocabulary:** 100% content_type-based (Group + Content Type VN). Không còn hệ thống UC.
>
> **Thay đổi v1.1 (04/2026):** Tách Verdict thành 3 row độc lập — `Tier 1 Script`, `Tier 2 LLM`, `Verdict` (final). Thêm block `🤖 Tier 2 LLM Content Review` (table dimension-level) cho lead card mỗi nhóm content. Bổ sung scoring rubric Tier 1 heuristic (5 dimensions, thang 100). Bảng tóm tắt cuối báo cáo có thêm cột Tier 1 + Tier 2 LLM.
> **Thay đổi v1.2 (04/2026):** Approver derivation và scoring rubric reword theo content_type/group (bỏ reference UC_APPROVER); Verdict icon section rewrite theo Group Quan trọng/Ưu đãi/Tương tác/SURVEY (NGOÀI SCOPE = content_type không nằm 14 code); Content Type mapping bảng giữ tên VN cũ làm reference, chính thức theo bảng 14 trong `05-guardrail-rule-sheet_v1.7.md`.
> **Thay đổi v1.3 (04/2026):** Card header `**#[n]**` thêm clickable link đến Athena UAT detail view (`https://athena.mservice.io/notification-v2/list-view?name=<campaign_name>`) — approver click vào campaign name là mở thẳng trang detail trên Athena, không cần search Alt+K thủ công.
> **Thay đổi v1.4 (04/2026):** **Flip default output sang summary-table-first.** Default batch review = 1 bảng 10 cột (# · Campaign link · CT · Title · Body · T1 · T2 · Verdict · **Lý do không đạt** · Hành động), sắp xếp push_time tăng dần, approver scan nhanh toàn batch. Card 13-row + Tier 2 dim breakdown demoted thành **deep-dive on-demand** (render khi user yêu cầu zoom 1 campaign cụ thể). Cột "Lý do không đạt" tổng hợp mọi DIM/Rule violations inline — value-add chính cho approver.
> **Thay đổi v1.5 (04/2026):** Campaign cell phải compact (~ ≤ 20 ký tự display) — dùng short alias dạng `family_variant` trong link text (VD `vts_personalized`, `ttqt_trung_quoc`, `vietlott_direct`), full name trong URL href. **KHÔNG** dùng `<br>` trong link text (markdown escape thành literal, làm hỏng name). Strip date prefix `YYYYMMDD_` (đã có ở urgency section header). Thêm legend blockquote đầu table giải thích alias cho approver tra. Lý do: auto-width table scale theo cell dài nhất — cột Campaign với full name chiếm space của Body/Lý do.
> **Thay đổi v1.6 (05/2026):** **Add cột "🖼 Ảnh"** sau cột Body — render từ `tier1_check.py` output `metadata.image_url` (v1.4.8+). Cell trống (`—`) khi không có image; markdown link `[filename](url) ⚠️` khi có image + `allow_out_app=true` (advisory tag `image_outapp_review` từ Rule 2.12). Approver **BẮT BUỘC click link visual review trước khi APPROVE** — Phase 4 confirm panel highlight. Lý do: icon nhỏ (vd 600×400) có thể bị iOS render full screen ở out-app push, gây UX lỗi (ảnh stretch dominate notification). URL pattern phân tích không đủ catch — cần human visual check. Bảng update thành 11 cột.
> **Thay đổi v1.7 (05/2026):** **Add Phase 4.0 AI Agreement gate + audit footer pattern.** Trước khi đi lệnh, agent BẮT BUỘC hỏi approver xác nhận đồng ý/không đồng ý với verdict (Cowork only — KHÔNG áp dụng Athena UI direct). Lý do disagree MANDATORY khi `ai_agreement=no`. Phase 5 comment template thêm audit footer line: `—— [ai_verdict=<V>] [ai_agreement=yes|no] [disagree_reason=<text>]`. DA team aggregate bi-weekly để eval disagree rate cho automation phase tiếp theo. Mục đích: capture training data cho automation phase, không phải gate decision making.
> **Thay đổi v1.8 (05/2026):** **Hard mandate Phase 3 — fix Cowork compliance variance.** Per feedback từ distributed members: agent đôi khi render bulleted list thay vì table, hoặc table render nhưng KHÔNG có markdown link wrap campaign cell. Add explicit MANDATE sections: (1) **table-only output** (override "list" trong user prompt — natural language not format instruction); (2) **markdown link wrap BẮT BUỘC** cho mọi Campaign cell với format `[`alias`](base_url/notification-v2/list-view?name=full_name)`; (3) **env-aware URL** (PROD `https://athena.mservice.io` vs UAT `https://athena-uat.mservice.io` — agent infer từ MCP server name); (4) update column count text 10 → 11 (sync v1.6 image col). Recommend (v1.5.1+): dùng `scripts/render_batch_report.py` (Phase 2) để render programmatically thay vì LLM tự build — 100% compliance, không variance.
> **Thay đổi v1.9 (05/2026):** **Phase 4.0 2-step gate + audit footer schema v2.** Per audit honest từ session 2026-05-27: em label `ai_agreement=no` cho case AI HITL → PCS + PCS approver review + approves — sai semantic. `ai_agreement` đúng nghĩa track WHETHER AI INTENT WAS RESPECTED, không phải "action có giống suggestion verdict tag không". Khi HITL → team X + team X review + approves = INTENT RESPECTED = `yes`. Khi cross-team approver bypass review = OVERRIDE = `no`. Phase 4.0 refine 2-step gate: Bước 1 ask đồng ý/không đồng ý → Bước 2 (followup khi action ≠ AI suggest) ask "đã review offline chưa". Audit footer schema v2 expand: thêm 3 fields optional `offline_review` (yes/no), `review_note` (mandatory khi offline_review=yes), `reviewer_team` (recommend khi action ≠ AI suggest). Backward compat: v1 footer (3 fields) vẫn parse được. Phase 5 examples expand 5 patterns: (1) QUALIFIED auto-approve, (2) HITL same-team approve, (3) HITL cross-team với offline coord, (4) HITL genuine override, (5) WARNING với offline review.

---

## Cấu trúc tổng quan (v1.3 — summary-first)

> **Default output:** 1 bảng tóm tắt duy nhất. Cards chi tiết per-campaign chỉ render **on-demand** khi user yêu cầu zoom deep-dive.

### Default — Summary table (BẮT BUỘC)

```
## 📋 Noti Campaigns — IN REVIEW
**Cập nhật:** [DD/MM/YYYY, HH:MM VN] | **Tổng:** N campaigns | **Reviewer:** [email] | **Env:** [UAT | Prod]

> 📊 Tier 1 (Script) — Rule/Title/Body/CT/Routing · Tier 2 (LLM Content Review theo 07-llm-judge-core_v1.12.md)
> Ngưỡng: 🟢 ≥ 90 | 🟡 85–89 | 🟠 50–84 | 🔴 < 50 | 🟣 HITL-triggered | ⛔ EXPIRED
> Cột 🖼 Ảnh: `—` (không có) hoặc `[filename](url) ⚠️` (advisory click review trước duyệt)

| # | Campaign | CT | Title | Body | 🖼 Ảnh | T1 | T2 | Verdict | Lý do không đạt | Hành động |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | [`<name>`](https://athena.mservice.io/notification-v2/list-view?name=<name>) | [CT API code] | [title] | [body truncate nếu > ~100 ký tự] | [—] OR [`[filename](url) ⚠️`] | [icon] [score] | [icon] [score] | [icon] [verdict text] | [diễn giải VN tự nhiên]; ... (— nếu pass) | [hành động cụ thể] |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |

---
> ⚠️ Đây chỉ là kết quả phân tích — chưa có thao tác nào được thực hiện trong Athena.
> Mọi quyết định approve/reject vẫn do approver thực hiện thủ công.
> Tìm campaign: click tên campaign (→ mở Athena UAT detail view).
```

**Sắp xếp rows:** push_time tăng dần (urgent nhất lên đầu). Có thể chèn urgency section header (`### 🚨/📅/🗓️ Push [ngày]`) giữa rows cho các nhóm ngày khác nhau.

### On-demand — Deep-dive card (khi user yêu cầu zoom)

Chỉ render khi user hỏi kỹ 1 campaign cụ thể (VD: "xem chi tiết #5", "deep-dive vietlott_direct"). Format như sau:

```
**#[n]** [`[campaign_name]`](https://athena.mservice.io/notification-v2/list-view?name=[campaign_name])
| | |
|---|---|
| **Content Type**  | [Tên VN] ([API value]) |
| **Title**         | [title] |
| **Body**          | [body] |
| **Push Time**     | [DD/MM/YYYY HH:mm ICT — giờ chuẩn, không `~`/raw epoch] |
| **Deadline duyệt**| [DD/MM HH:MM] |
| **Segment Size**  | [N,NNN] |
| **Approver**      | [CIO / BMC / PCS] |
| **Created by**    | [email] |
| **Tier 1 Script** | [icon] [N1/100] (Rule X/30 · Title X/20 · Body X/20 · Content-Type X/20 · Routing X/10) |
| **Tier 2 LLM**    | [icon] [N2/100] [⚠️ HITL triggered nếu có] |
| **Verdict**       | [icon] [verdict text] |
| **Ghi chú**       | [issues / notes nếu có] |

🤖 **Tier 2 LLM Content Review** — Overall: [icon] [N2/100] [⚠️ HITL triggered]
> Lý do HITL/Routing: [reason text]

| Dimension | Sub-score | Nhận xét | Gợi ý |
|---|---|---|---|
| DIM-3.1 Title clarity | [icon] [score] | [comment] | [suggestion] |
| DIM-3.2 Body complementarity | ... | ... | ... |
| ... | | | |

*Advisory notes:*
- **DIM-3.15 Personalization** — [note]
- **DIM-3.16 Number specificity** — [note]
- **DIM-3.18 Segment-title alignment** — [note]
```

---

## Chi tiết từng field

### Nhóm header
| Field | Nguồn | Format |
|---|---|---|
| Cập nhật | `datetime.now()` UTC+7 | `DD/MM/YYYY, HH:MM VN` |
| Tổng | Count tất cả campaign IN_REVIEW | Số nguyên |
| Scoring rubric block | Bắt buộc — note 2 tầng + ngưỡng màu | Markdown blockquote |

### Nhóm urgency (section headers)
| Nhãn | Điều kiện (push_time tính từ lúc chạy) |
|---|---|
| 🚨 Push hôm nay DD/MM — Deadline cấp bách | push trong 0–10h |
| 📅 Push ngày DD/MM | push trong 10–48h |
| 🗓️ Push DD/MM trở đi | push > 48h |

### Nhóm campaign card
| Field | Nguồn | Ghi chú |
|---|---|---|
| `#n` | Thứ tự, sắp xếp theo push_time tăng dần | |
| Campaign Name | `campaign_name` từ API | Markdown link `[\`<name>\`](https://athena.mservice.io/notification-v2/list-view?name=<name>)` — click mở Athena UAT detail view (v1.3+) |
| Content Type | `content_type` từ `notification_reference` | Hiển thị cả tên VN lẫn API value |
| Title | `variants.control.caption` | |
| Body | `variants.control.body` | |
| Push Time | `schedule_config.push_time` (epoch ms, **UTC**) → quy đổi GMT+7 **BẮT BUỘC qua script** `python scripts/timefmt.py --ms <push_time>` (hoặc `format_push_time()`) | **⛔ LUÔN giờ ICT chuẩn, format `DD/MM/YYYY HH:mm`** — CẤM `~` (xấp xỉ), CẤM raw epoch, CẤM để UTC, **CẤM convert thủ công / LLM tự +7h bằng đầu**. Copy `push_time_ict` từ stdout verbatim. Convert bắt buộc cho cả display lẫn logic (deadline, urgency, stale) — xem HARD rule trong `references/noti-campaign-approval.md` §Anti-hallucination |
| Deadline duyệt | push_time **(đã convert GMT+7)** − 30 phút (single) hoặc − 60 phút (A/B) | Format `DD/MM HH:MM` |
| Segment Size | `segment.size` | Format có dấu phẩy ngăn cách nghìn |
| Approver | Derive từ content_type → group → GROUP_APPROVER mapping (SURVEY → CIO exception) | CIO / BMC / PCS |
| Created by | `created_by` từ API | Email của người tạo campaign |
| **Tier 1 Script** *(mới v1.1)* | Heuristic score 0–100 + breakdown 5 dimensions | Lead card: full breakdown · Follower card: chỉ score |
| **Tier 2 LLM** *(mới v1.1)* | LLM Judge overall_score + HITL flag | Lead card: full block riêng bên dưới · Follower card: "(xem review ở #X)" |
| Verdict | Tổng hợp Tier 1 + Tier 2 → final routing decision | Xem bảng Verdict icons bên dưới |
| Ghi chú | Issues / duplicate warning / out-of-scope note | Bỏ qua nếu không có |

### Tier 1 Script — Scoring rubric (heuristic, thang 100)
| Dimension | Trọng số | Cách tính |
|---|---|---|
| Rule compliance | 30 | -15/error, -5/warning, -2/hitl trigger |
| Title quality | 20 | Length ≤30 chars (10) + attention hook (10) |
| Body quality | 20 | Length ≤120 chars (10) + clear CTA (10) |
| Content-Type alignment | 20 | Text match với declared content_type (full 20 hoặc 0 nếu mismatch SURVEY; partial 10 nếu mismatch khác) |
| Approver routing | 10 | content_type có mapping rõ trong GROUP_APPROVER (derived từ CT_TO_GROUP) → 10 |

> Tier 1 Script chạy local trong `eval.py` (Tier 0 + Tier 1 logic). Heuristic score chỉ dùng để **sắp xếp/highlight** — verdict chính thức vẫn do Tier 2 LLM + Tier 3 routing quyết định.

### Tier 2 LLM Content Review — block riêng (mới v1.1)
Lead card mỗi nhóm content (cùng title+body) hiển thị block riêng `🤖 Tier 2 LLM Content Review`:
- **Overall score** + HITL flag (nếu có)
- **Lý do HITL/Routing** trong blockquote
- **Bảng dimension-level** với 4 cột: `Dimension | Sub-score | Nhận xét | Gợi ý`
  - Sub-score Score-based: 🟢 100 / 🟡 75 / 🟠 50 / 🔴 25 / 🔴 0 (5 mức)
  - HITL-trigger dimension: hiển thị 🟣 HITL thay vì sub-score
- **Advisory notes** (DIM-3.15/3.16/3.18) liệt kê dưới bảng dạng bullet

Follower cards (cùng content) chỉ hiển thị overall score + reference: `🟡 88/100 (xem review ở #X)`.

> **Khi nào chạy Tier 2 thật:** `eval.py` tự gọi `tier2_llm_judge()` khi có `ANTHROPIC_API_KEY` trong env và `skip_llm=False`. Không có key → Claude (agent đang chạy báo cáo) đánh giá manual theo `07-llm-judge-core_v1.12.md` và đặt `tier2_source = "manual"` trong metadata.

### Content Type — mapping tên tiếng Việt
| API value | Tên VN | Nhóm |
|---|---|---|
| `SURVEY` | Khảo sát | Thông báo tương tác |
| `ADVERTISING` | Quảng cáo | Thông báo ưu đãi |
| `PROMOTION` | Khuyến mãi | Thông báo ưu đãi |
| `SOCIAL` | Cộng Đồng | Thông báo tương tác — NGOÀI SCOPE |

### Verdict icons (final, sau khi tổng hợp Tier 1 + Tier 2)
| Icon + text | Ý nghĩa |
|---|---|
| ✅ APPROVED — Tier 2 N/100 | Pass Tier 1 + LLM ≥ 85, Group Ưu đãi hoặc Tương tác (trừ SURVEY) auto-approve, không HITL trigger |
| 🔵 HITL — [team] bắt buộc duyệt thủ công | Content type bắt buộc HITL dù score cao (toàn bộ Group Quan trọng + SURVEY) |
| 🔵 HITL — [team] verify | Tier 2 LLM trigger HITL (DIM-3.7/3.9/4.4/4.5) |
| 🔵 HITL — chờ [team] review | Tier 1 pass, Tier 2 chưa chạy hoặc score 50–84 |
| ❌ REJECTED — Tier 2 N/100 | Score < 50 hoặc Tier 1 fail |
| ⚠️ SEGMENT FLAG | Segment > 5M, cần Growth confirm trước |
| ⛔ NGOÀI SCOPE | Content type không nằm trong danh sách 14 content_type Athena |
| ❓ CẦN XÁC NHẬN | content_type rỗng hoặc không map được |

### Score color legend (dùng cho cả Tier 1 và Tier 2)
| Range | Icon |
|---|---|
| ≥ 90 | 🟢 |
| 85–89 | 🟡 |
| 50–84 | 🟠 |
| < 50 | 🔴 |
| HITL-trigger dimension | 🟣 |

---

## Bảng tóm tắt cuối báo cáo (cập nhật v1.1)

Sau tất cả các campaign, thêm bảng action summary với 2 cột score:

```
## Tóm tắt action

| Nhóm | Số CP | Nội dung | Approver | Tier 1 | Tier 2 LLM | Verdict | Hành động |
|---|---|---|---|---|---|---|---|
| [batch name] | N | [title ngắn] | [team] | [icon score] | [icon score] | [verdict icon] | [action + deadline] |
```

Dưới bảng tóm tắt action, thêm dòng tổng kết:
```
**Tổng kết 2 tầng (Tier 1 TB: [icon score] · Tier 2 LLM TB: [icon score]):**
- ✅ N/M pass Tier 1 Script
- 🤖 N campaigns bị Tier 2 LLM flag HITL trigger
- 🔵 N campaigns route HITL bắt buộc
- ⚠️ N segment > 5M
- ❌ N REJECTED
```

**Ghi chú cuối báo cáo (bắt buộc):**
> ⚠️ Đây chỉ là kết quả phân tích — **chưa có thao tác nào được thực hiện** trong Athena.
> Mọi quyết định approve/reject vẫn do approver thực hiện thủ công.
> Tier 2 LLM review được đánh giá manual khi không có `ANTHROPIC_API_KEY`. Khi enable key, `eval.py` sẽ tự chạy Tier 2 chuẩn hóa.
> Để mở campaign trong Athena: **click trực tiếp vào tên campaign** ở header card (v1.3+ — mở thẳng detail view). Cách cũ: vào tab "In Review" → dùng **Alt+K** search theo tên campaign.

---

## Nhóm campaigns cùng nội dung (multi-segment)

Khi phát hiện nhiều campaigns có cùng title + body (multi-segment batch):
- **Lead card** (campaign đầu tiên trong nhóm): hiển thị card đầy đủ + block `🤖 Tier 2 LLM Content Review` chi tiết
- **Follower cards** (các campaign sau): hiển thị card compact (chỉ Push Time / Deadline / Segment Size / Approver / Created by / Tier 1 / Tier 2 + verdict), reference review về lead: `🟡 N/100 (xem review ở #X)`
- Sau tất cả nhóm: thêm 1 section `### 📦 Nhóm campaigns cùng nội dung` với 1 dòng tổng kết mỗi nhóm:
  > 💡 **#X, …, #Y** (N CP) — *"[title]"* — Tier 1: **[icon score]** · Tier 2 LLM: **[icon score]**. Duyệt đồng loạt.

---

## Quy tắc sắp xếp

1. **Theo push_time tăng dần** — campaign cấp bách nhất lên đầu
2. **Trong cùng push_time:** sắp theo segment_size giảm dần (LIGHT → MEDIUM → HARDCORE → NON_MAU)
3. **Campaigns NGOÀI SCOPE / CẦN XÁC NHẬN:** xếp sau tất cả campaigns có verdict rõ ràng
4. **Lead card của nhóm content:** không nhất thiết là campaign đầu tiên theo push_time — là campaign có index thấp nhất trong nhóm sau khi sort

---

## Changelog template

| Version | Date | Thay đổi chính |
|---|---|---|
| v1.0 | 04/2026 | Khởi tạo template card-per-campaign, urgency grouping, action summary |
| v1.1 | 04/2026 | Tách Verdict thành 3 row (Tier 1 / Tier 2 / Final). Thêm block `🤖 Tier 2 LLM Content Review` (dimension-level table). Bổ sung scoring rubric Tier 1 heuristic. Cập nhật bảng tóm tắt action với 2 cột score. Thêm score color legend. |
| v1.2 | 04/2026 | Xóa hoàn toàn reference UC/UC_APPROVER — Approver derivation dùng content_type → group → GROUP_APPROVER; Verdict icon section rewrite theo Group Quan trọng/Ưu đãi/Tương tác/SURVEY; cross-refs update skill_v2.0.md + 07-llm-judge-core_v1.12.md. |
| v1.3 | 04/2026 | Card header **`#[n]`** thêm clickable Markdown link đến Athena UAT detail view (`https://athena.mservice.io/notification-v2/list-view?name=<campaign_name>`). Footer note cập nhật hướng dẫn mở campaign theo cách click link (cách Alt+K vẫn còn làm fallback). Field doc row "Campaign Name" cập nhật format. |

---

*Tạo: 04/2026 — v1.1*
*Cập nhật: 04/2026 — v1.3: thêm clickable Athena UAT link cho campaign name trong card header*
*File liên quan: skill_v2.1.md · scripts/fetch_campaigns.py · eval.py · 07-llm-judge-core_v1.12.md*

---

## Phase 5 Message Field Examples (verdict templates)

> Concrete examples cho 8 verdict templates trong Phase 5 skill/noti-campaign-approval.md. Approver `huong.vu4` ({role}), timestamp ICT.
>
> **Nguyên tắc (v1.3.0+):** APPROVE = ngắn gọn (1 câu key context + close `"Campaign đủ điều kiện duyệt."`). REJECT = giữ detail lỗi cụ thể cho Owner sửa. Char count target ≤ 800.

### 1. QUALIFIED auto-APPROVE
**Human:** *"Approve by huong.vu4 (Platform Operator). Score 100/100. Campaign đủ điều kiện duyệt."*
**Log:** `[AI-REVIEW v1.2] verdict=QUALIFIED | action=APPROVE | score=100 | priority=NORMAL | ts=2026-05-19T10:30+07`
**Audit footer (v1.9+ schema v2):** `—— [ai_verdict=QUALIFIED] [ai_agreement=yes]`

### 2. HITL → APPROVE (approver thuộc đúng team — KHÔNG `override`)
**Human:** *"Approve by huong.vu4 (PCS). Content_type REMIND = Quan trọng. Campaign đủ điều kiện duyệt."*
**Log:** `[AI-REVIEW v1.2] verdict=HITL_REQUIRED | action=APPROVE | score=90 | trg=quan_trong_pcs_routing | priority=NORMAL | team=PCS | ts=2026-05-19T10:33+07`

### 3. HITL → APPROVE (cross-team align — CÓ `override`)
**Human:** *"Approve by huong.vu4 (Platform Operator). Đã align BMC offline. Campaign đủ điều kiện duyệt."*
**Log:** `[AI-REVIEW v1.2] verdict=HITL_REQUIRED | action=APPROVE | score=75 | override=true | just=cross_team_align_offline | trg=big_segment,sensitive_action | priority=NORMAL | team=BMC | ts=2026-05-19T10:35+07`
**Audit footer (v1.9+ schema v2, 5 patterns):**
```
[1] HITL same-team (PCS approver review + approve HITL → PCS):
—— [ai_verdict=HITL_REQUIRED] [ai_agreement=yes] [reviewer_team=PCS] [review_note=PCS team review offline confirm OK]

[2] HITL cross-team với offline coord (Platform Operator override but coord BMC):
—— [ai_verdict=HITL_REQUIRED] [ai_agreement=yes] [offline_review=yes] [review_note=BMC offline đã review qua Slack] [reviewer_team=PLATFORM_OPERATOR]

[3] HITL genuine override (no review path):
—— [ai_verdict=HITL_REQUIRED] [ai_agreement=no] [offline_review=no] [reviewer_team=PLATFORM_OPERATOR] [disagree_reason=Push còn 10 phút, exercise Platform Operator authority]

[4] WARNING + offline review approve:
—— [ai_verdict=WARNING] [ai_agreement=yes] [offline_review=yes] [review_note=Image rendered OK trên test device]

[5] REJECT skip (genuine override):
—— [ai_verdict=NOT_QUALIFIED] [ai_agreement=no] [offline_review=no] [disagree_reason=Hard rule false positive — title 31 chars do unicode count, approver verify OK manually]
```

### 4. HITL → APPROVE Vietlott (legal partner)
**Human:** *"Approve by huong.vu4 (Platform Operator). Vietlott đối tác chính thức. Campaign đủ điều kiện duyệt."*
**Log:** `[AI-REVIEW v1.2] verdict=HITL_REQUIRED | action=APPROVE | score=95 | override=true | just=platform_authority | trg=vietlott_legal_review | priority=NORMAL | team=BMC | ts=2026-05-19T10:40+07`

### 5. HITL → APPROVE SURVEY (CIO approver — KHÔNG `override`)
**Human:** *"Approve by huong.vu4 (CIO). Survey UX Q2. Campaign đủ điều kiện duyệt."*
**Log:** `[AI-REVIEW v1.2] verdict=HITL_REQUIRED | action=APPROVE | score=95 | priority=NORMAL | team=CIO | ts=2026-05-19T10:42+07`
*(team=CIO đã imply survey_cio_routing — không cần lặp trg)*

### 6. NOT_QUALIFIED REJECT (Tier 1 content fail) — keep detail
**Human:** *"Reject by huong.vu4 (Platform Operator). Title 78 ký tự, vượt giới hạn 30. Body có 2 lỗi chính tả: 'khuyên mãi' (đúng là 'khuyến mãi'), 'vourcher' (đúng là 'voucher'). Owner sửa và resubmit."*
**Log:** `[AI-REVIEW v1.2] verdict=NOT_QUALIFIED | action=REJECT | score=32 | trg=title_too_long,typo_in_body | ts=2026-05-19T10:45+07`

### 7. REJECT cleanup test/stale — keep detail
**Human:** *"Reject by huong.vu4 (Platform Operator) để clean up. Nội dung test ('asdfgh test'), push_time quá hạn từ 2026-02-12."*
**Log:** `[AI-REVIEW v1.2] verdict=NOT_QUALIFIED | action=REJECT | trg=test_content,stale_18mo | ts=2026-05-19T10:50+07`

### 8. REJECT hard block PII — keep detail
**Human:** *"Reject by huong.vu4 (Platform Operator). Body có số điện thoại — vi phạm chính sách bảo mật thông tin cá nhân."*
**Log:** `[AI-REVIEW v1.2] verdict=NOT_QUALIFIED | action=REJECT | trg=pii_detected | ts=2026-05-19T10:52+07`

### Char count verify

| Scenario | Human (v1.2.9) | Human (v1.3.0 mới) | Saved | Total (mới) |
|---|---|---|---|---|
| QUALIFIED auto | ~150 | ~85 | -65 | ~180 |
| HITL same team (PCS) | ~200 | ~92 | -108 | ~272 |
| HITL cross-team override | ~290 | ~95 | -195 | ~325 |
| HITL Vietlott | ~210 | ~100 | -110 | ~265 |
| HITL SURVEY CIO | ~190 | ~75 | -115 | ~230 |
| REJECT Tier 1 (keep) | ~225 | ~220 | 0 | ~360 |
| REJECT cleanup (keep) | ~125 | ~140 | 0 | ~225 |
| Hard block PII (keep) | ~125 | ~120 | 0 | ~215 |

→ APPROVE giảm trung bình **-45%**. REJECT giữ nguyên detail. Tất cả well under 800 char target.
