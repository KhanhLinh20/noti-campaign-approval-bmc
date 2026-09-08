# 09 — Dashboard HTML Template README

> **Phiên bản:** v1.4 — 05/2026
> **Companion file:** `09-dashboard-html-template_v1.4.html`
> **Scope:** Hướng dẫn agent (Claude) hoặc engineer fill template HTML để render Cowork artifact dashboard cho Noti Campaign batch review.

---

## 1. Purpose

File `09-dashboard-html-template_v1.4.html` là **HTML/CSS/JS skeleton** cho Cowork artifact dashboard hiển thị kết quả batch review Noti Campaign.

**Companion với file 08:**
- File 08 (`08-batch-review-template_v1.9.md`) → format **chat markdown** (summary table inline trong chat reply)
- File 09 → format **Cowork artifact** (persistent HTML dashboard trong sidebar, có live refresh)

**Tại sao cần file 09:**
- Approver muốn xem lại batch review mà không scroll chat
- Dashboard cần update urgency theo real-time (campaign push trong 24h vs >72h)
- Cần phát hiện state changes (campaign đã rời IN_REVIEW giữa các session)
- Multi-session reuse — Hưn mở dashboard ngày mai vẫn còn

---

## 2. Khi nào dùng

Agent dùng template 09 trong các trường hợp:

| Trigger | Hành động |
|---|---|
| User ping "tạo dashboard batch review" | Read template 09 → fill → push artifact |
| User ping "chạy lại batch review mới" | Read template 09 → judge new data → fill → update artifact với same `id` |
| User ping "cập nhật dashboard" | Re-fetch live → re-judge → fill template → update artifact |
| Scheduled task batch review daily/weekly | Auto-trigger template fill mỗi run |

**KHÔNG dùng template 09 khi:**
- User chỉ hỏi 1 campaign cụ thể (deep-dive) — dùng inline chat reply
- Batch < 3 campaigns — overhead lớn hơn benefit, dùng chat markdown (file 08)
- User explicit yêu cầu chat-only output

---

## 3. Placeholders

Template có **11 placeholders** dạng `{{NAME}}` (double-brace, không space). Agent phải replace **toàn bộ** trước khi push artifact, nếu sót template sẽ render literal `{{...}}`.

**Quick reference 11 placeholders:**

| Group | Placeholder | Purpose |
|---|---|---|
| Identity | `{{ARTIFACT_NAME}}` · `{{ARTIFACT_DESCRIPTION}}` · `{{SUBTITLE}}` | Tên + mô tả artifact |
| Context | `{{SNAPSHOT_TIME_FULL_VN}}` · `{{REVIEWER_EMAIL}}` | Thông tin reviewer + thời điểm snapshot |
| Environment (v1.1+) | `{{ENV}}` · `{{ENV_CLASS}}` · `{{NOTI_MCP_TOOL}}` · `{{NOTI_MCP_SERVER}}` · `{{ATHENA_URL_BASE}}` | Switch UAT/PROD không cần sửa code |
| Data | `{{FOOTER_PATTERN_NOTES}}` · `{{FROZEN_REVIEW_JSON}}` | Patterns batch + review data |

### 3.1 `{{ARTIFACT_NAME}}`

**Type:** String (≤ 50 chars)
**Vị trí:** 3 chỗ — `cowork-artifact-meta.name`, `<title>`, `<h1>` text
**Ví dụ:**
```
"Noti Campaign Review Dash"
"Noti Review — Batch 12/5/2026"
"PCS Review Queue"
```
**Lưu ý:** Tên này hiển thị ở tab Cowork sidebar — keep ngắn để không bị truncate.

### 3.2 `{{ARTIFACT_DESCRIPTION}}`

**Type:** String (≤ 200 chars)
**Vị trí:** `cowork-artifact-meta.description`
**Ví dụ:**
```
"Hybrid dashboard — Live IN_REVIEW + urgency refresh mỗi reload, frozen score từ batch 12/5/2026. Format theo 08-batch-review-template v1.5."
```

### 3.3 `{{SUBTITLE}}`

**Type:** String (≤ 150 chars) — có thể chứa inline text
**Vị trí:** `.hdr .sub` (1 dòng dưới H1)
**Ví dụ:**
```
"Hybrid · Campaign list + urgency: LIVE · Scoring (T1/T2/Verdict): FROZEN snapshot 12/5/2026 11:06"
"Batch 3 — 7 campaigns paylater fee change, push 15/5 09:00-09:15"
```

### 3.4 `{{SNAPSHOT_TIME_FULL_VN}}`

**Type:** String format `DD/MM/YYYY, HH:MM VN`
**Vị trí:** `.hdr .meta` + footer
**Ví dụ:** `"12/05/2026, 11:06 VN"`
**Cách tính:** Lấy `now()` lúc agent bắt đầu judge batch, format theo locale VN.

### 3.5 `{{REVIEWER_EMAIL}}`

**Type:** String (email)
**Vị trí:** `.hdr .meta`
**Ví dụ:** `"vuquynhhuong03@gmail.com"`
**Cách tính:** Lấy từ user context (Cowork user email).

### 3.6 `{{ENV}}`

**Type:** String — `"UAT"` hoặc `"PROD"`
**Vị trí:** `.hdr .meta` + env-tag badge cạnh title (v1.1+)
**Cách tính:** Hardcoded theo môi trường agent đang chạy.

### 3.6b `{{ENV_CLASS}}` *(v1.1+)*

**Type:** String — `"uat"` hoặc `"prod"` (lowercase CSS class)
**Vị trí:** `<span class="env-tag {{ENV_CLASS}}">`
**Mục đích:** PROD render badge đỏ, UAT render badge vàng cho approver phân biệt nhanh.

### 3.6c `{{NOTI_MCP_TOOL}}` *(v1.1+)*

**Type:** String — fully-qualified MCP tool name
**Ví dụ:**
- UAT: `"mcp__noti-mcp__list_campaigns"`
- PROD: `"mcp__noti-mcp-prod__list_campaigns"`
**Vị trí:** `cowork-artifact-meta.mcpTools[]` + JS `callMcpTool()` + footer reference
**Lưu ý:** Phải khớp với env — gọi tool UAT từ context PROD sẽ trả 401/empty list.

### 3.6d `{{NOTI_MCP_SERVER}}` *(v1.1+)*

**Type:** String — MCP server short name
**Ví dụ:**
- UAT: `"noti-mcp"`
- PROD: `"noti-mcp-prod"`
**Vị trí:** `cowork-artifact-meta.mcpServerNames[]`

### 3.6e `{{ATHENA_URL_BASE}}` *(v1.1+)*

**Type:** URL string (không trailing slash)
**Ví dụ:**
- UAT: `"https://athena-uat.mservice.io"`
- PROD: `"https://athena.mservice.io"`
**Vị trí:** Trong JS `renderCampaignRow` để build link mở campaign detail
**Lưu ý:** Click tên campaign từ UAT dashboard sẽ mở Athena UAT, PROD dashboard mở Athena PROD.

### 3.7 `{{FOOTER_PATTERN_NOTES}}`

**Type:** HTML string (có thể chứa `<b>`, `<code>`, `<br>`, emoji)
**Vị trí:** Footer dưới cùng, ngay trên dòng "Click tên campaign..."
**Mục đích:** Highlight patterns/insights cấp batch (không phải per-campaign).
**Ví dụ:**
```html
🚨 <b>Pattern phát hiện:</b> 9/20 campaigns vi phạm <code>Rule 2.1</code> (title > 30 chars) — pattern lỗi systematic. Đáng flag với owner <code>nga.nguyen6@mservice.com.vn</code>.
```
**Nếu không có pattern đặc biệt:**
```html
<i>Không có pattern bất thường trong batch này.</i>
```

### 3.8 `{{FROZEN_REVIEW_JSON}}`

**Type:** JSON array (KHÔNG có dấu nháy bao ngoài — đây là JS literal)
**Vị trí:** Trong `<script>` cuối file, gán cho `const FROZEN_REVIEW = ...;`

**Schema mỗi phần tử:**

| Field | Type | Required | Ví dụ |
|---|---|---|---|
| `n` | int | ✅ | `1` (số thứ tự, ascending theo push_time) |
| `name` | string | ✅ | `"paylater_fee_change_vts_new_t1_260515"` (full campaign name từ API, dùng cho link Athena) |
| `alias` | string | ✅ | `"paylater_vts_new_t1"` (≤ 20 chars, family_variant format) |
| `ct` | string | ✅ | `"SERVICE"` (API code, 1 trong 14 valid CTs) |
| `title` | string | ✅ | `"Cập nhật phí Ví Trả Sau"` (caption gốc) |
| `bodyHtml` | string (HTML) | ✅ | `"Bạn vừa mở Ví Trả Sau gần đây..."` (có thể chứa `<b style="color:#dc2626">word</b>` để highlight typo/issue, hoặc `<code>${lastname}</code>`) |
| `pushTime` | int (unix ms) | ✅ | `1778814000000` (từ `schedule_config.push_time`) |
| `segSize` | int *(v1.1+)* | optional | `1871` (từ `segment.size`). Hiển thị dưới alias dạng "👥 1.871". Nếu >5,000,000 sẽ tự highlight cam + warning emoji ⚠️ theo Rule 5.1 |
| `creator` | string *(v1.3+)* | optional | `"thuy.le6@mservice.com.vn"` (từ `created_by`). Render short username "thuy.le6" trong column Creator + tooltip full email khi hover. Approver click copy để ping owner fix issues |
| `t1` | string | ✅ | `"🟢 95"` (icon + score, score 0–100) |
| `t2` | string | ✅ | `"🟡 85"` hoặc `"🟣 HITL"` hoặc `"❌ N/A"` |
| `vCls` | string | ✅ | `"v-ok"` / `"v-hitl"` / `"v-rej"` (CSS class) |
| `vText` | string | ✅ | `"✅ APPROVED — Tier 2 92/100"` (verdict label) |
| `reasonHtml` | string (HTML) | ✅ | **KHÔNG show số rule/DIM ra user** (skill/noti-campaign-approval.md Principle #8). Dùng nhãn tiếng Việt tự nhiên + mô tả vi phạm thực tế. Ví dụ: `<span class="ops">⚠️ Segment lớn:</span> 6.5 triệu users vượt ngưỡng 5 triệu` thay vì `<span class="ops">Rule 5.1:</span> segment > 5M`. Approver không nhớ code, agent map rule→nguyên nhân |
| `actionHtml` | string (HTML) | ✅ | `"<b>PCS duyệt manual</b>"` (hành động cụ thể cho approver) |

**CSS classes có sẵn cho reasonHtml/actionHtml:**
- `<span class="ops">OPS:</span>` → đỏ bold (operational issue: template, ref_id, segment)
- `<span class="dim">DIM-3.10 = 50</span>` → tím bold (Tier 2 LLM dimension violation)
- `<span class="dash">— (pass)</span>` → xám italic (no issue / dash placeholder)
- `<code>...</code>` → mono background highlight
- `<b style="color:#dc2626">...</b>` → đỏ bold inline (cho typo trong bodyHtml)
- `<b style="color:#ea580c">...</b>` → cam bold (warning level)

**Verdict CSS classes:**
- `v-ok` → xanh lá (APPROVED)
- `v-hitl` → xanh dương (HITL — manual review needed)
- `v-rej` → đỏ (REJECTED)

**Ví dụ 1 entry hoàn chỉnh:**
```json
{
  "n": 3,
  "name": "paylater_fee_change_active30_male_260515",
  "alias": "paylater_active30_m",
  "ct": "SERVICE",
  "title": "Thông báo thay đổi phí Ví Trả Sau",
  "bodyHtml": "Từ 01/06/2026, Ví Trả Sau áp dụng mức phí mới 31.000đ/tháng. Xem chi tiết tại đây.",
  "pushTime": 1778814300000,
  "t1": "🟠 80",
  "t2": "🟡 88",
  "vCls": "v-hitl",
  "vText": "🔵 HITL — PCS (Rule 2.7)",
  "reasonHtml": "<span class=\"dim\">Rule 2.7:</span> title <b>33 chars > 30</b> nhưng Group Quan trọng → HITL thay REJECT; <span class=\"ops\">OPS:</span> segment size <b>0</b> (empty)",
  "actionHtml": "<b>PCS</b> fix title ≤ 30 + segment build"
}
```

---

## 4. Usage Flow

### 4.1 Agent runtime (recommended)

```
┌──────────────────────────────────────────────────────────────┐
│ 1. User ping batch review                                     │
│                                                                │
│ 2. Read /mnt/skill/noti-campaign-approval/                    │
│    09-dashboard-html-template_v1.4.html (template)            │
│                                                                │
│ 3. Fetch noti-mcp:                                            │
│    - list_campaigns(status="IN_REVIEW")                       │
│    - get_campaign_detail(name=...) cho mỗi campaign           │
│                                                                │
│ 4. Sort top 20 theo push_time ASC                             │
│                                                                │
│ 5. Judge mỗi campaign theo file 05 + 07:                      │
│    - T1 score (script rules)                                  │
│    - T2 score (LLM dimensions DIM-3.x/4.x)                    │
│    - Verdict (vCls + vText)                                   │
│    - reasonHtml, actionHtml                                   │
│                                                                │
│ 6. Build FROZEN_REVIEW JSON array                             │
│                                                                │
│ 7. String.replace 7 placeholders bằng giá trị thực:           │
│    {{ARTIFACT_NAME}}     → "Noti Campaign Review Dash"        │
│    {{ARTIFACT_DESCRIPTION}} → "..."                           │
│    {{SUBTITLE}}          → "..."                              │
│    {{SNAPSHOT_TIME_FULL_VN}} → "12/05/2026, 11:06 VN"         │
│    {{REVIEWER_EMAIL}}    → "vuquynhhuong03@gmail.com"         │
│    {{ENV}}               → "UAT"                              │
│    {{FOOTER_PATTERN_NOTES}} → "🚨 <b>...</b>"                 │
│    {{FROZEN_REVIEW_JSON}} → JSON.stringify(array)             │
│                                                                │
│ 8. Write file: /sessions/<id>/noti-review-batch-vN.html       │
│                                                                │
│ 9. Call mcp__cowork__update_artifact:                         │
│    - id: "noti-review-batch-20260422" (hoặc id cũ)            │
│    - html_path: "/sessions/.../vN.html"                       │
│    - update_summary: "Batch N snapshot DD/MM..."              │
│    - mcp_tools: ["mcp__noti-mcp__list_campaigns"]             │
│                                                                │
│ 10. Cowork render artifact trong sidebar                      │
│     User reload → fetch live, merge với frozen, render        │
└──────────────────────────────────────────────────────────────┘
```

### 4.2 Engineer (manual fill cho testing)

```bash
# 1. Copy template
cp 09-dashboard-html-template_v1.4.html /tmp/my-dashboard.html

# 2. Edit replace placeholders (vim/sed/python)
# Ví dụ với sed:
sed -i 's/{{ARTIFACT_NAME}}/My Test Dashboard/g' /tmp/my-dashboard.html

# 3. Replace FROZEN_REVIEW_JSON với JSON array
# (cần manual hoặc Python script vì cần escape JSON)

# 4. Open in browser hoặc upload Cowork qua API
```

---

## 5. Live vs Frozen Elements

| Element | Mode | Cách tính |
|---|---|---|
| Tổng số `IN_REVIEW` (stats top) | 🔵 LIVE | `window.cowork.callMcpTool("mcp__noti-mcp__list_campaigns")` mỗi reload |
| Current time + urgency emoji (🔴/🚨/📅/🗓️) | 🔵 LIVE | `Date.now()` vs `pushTime` |
| State badge (Vẫn IN_REVIEW / Đã rời) | 🔵 LIVE | Compare frozen names với live IN_REVIEW list |
| Banner overdue/gone/new | 🔵 LIVE | Diff frozen vs live |
| T1/T2/Verdict score | ⚪ FROZEN | Snapshot trong `FROZEN_REVIEW` JSON, không re-compute |
| Reason, action text | ⚪ FROZEN | Snapshot |
| Title, body | ⚪ FROZEN | Snapshot lúc judge — nếu owner edit sau snapshot, dashboard không reflect |

---

## 6. Edge cases

### 6.1 Campaign mới xuất hiện trong IN_REVIEW sau snapshot

Banner cam sẽ hiển thị: *"⚠️ N campaigns mới trong IN_REVIEW chưa được score"* với list 5 cái đầu.
Agent xử lý: ping em "chạy batch review mới" để cover.

### 6.2 Campaign frozen đã rời IN_REVIEW

Row bị fade + badge `⚪ Đã rời`. Banner xám list ra.
Có thể là: approved/rejected/expired sau snapshot. Không cần action gì.

### 6.3 Campaign frozen vẫn IN_REVIEW nhưng push_time đã qua

Banner đỏ: *"🔴 N campaigns đã qua giờ push nhưng vẫn IN_REVIEW"*.
Action: Athena thường tự EXPIRED sau push_time + 1 phút. Nếu vẫn IN_REVIEW lâu, có thể là edge case scheduler/permission — báo Platform Admin.

### 6.4 Fetch live API error

Banner đỏ: *"⚠️ Lỗi fetch live data: ..."*. Dashboard fallback hiển thị frozen-only (không có badge state/diff).

### 6.5 FROZEN_REVIEW rỗng `[]`

Dashboard render OK nhưng không có row nào. Stats hiển thị 0. Banner OK.
Use case: dashboard placeholder lúc chưa có batch review.

---

## 7. Common pitfalls

| ❌ Sai | ✅ Đúng |
|---|---|
| Quên escape `"` trong reasonHtml khi gen JSON | Dùng `JSON.stringify()` thay vì string concat |
| Đặt verdict text quá dài → wrap xấu | `vText` ≤ 35 chars; chi tiết để vào `reasonHtml` |
| Quên `n` field hoặc gap số thứ tự | Đảm bảo `n` ascending 1, 2, 3... |
| `vCls` dùng `"v-warn"` (không có class này) | Chỉ dùng `v-ok` / `v-hitl` / `v-rej` |
| Hardcode emoji vào `vText` mà CSS class không match | Pair: `vCls="v-ok"` → emoji ✅ / `v-hitl` → 🔵 / `v-rej` → ❌ |
| Quên replace `{{FROZEN_REVIEW_JSON}}` → render literal | Verify file đã thay hết placeholder trước push |
| Đặt `pushTime` dưới dạng string `"1778814000000"` | Phải là **int** trong JSON (`1778814000000` không quote) |

---

## 8. Cross-references

- **Scoring rubric:** `references/`
- **LLM judge dimensions:** `07-llm-judge-core_v1.12.md`
- **HITL routing decision matrix:** `06-hitl-policy_v1.9.md`
- **Chat markdown format (companion):** `08-batch-review-template_v1.9.md`
- **Skill orchestration:** `skill/noti-campaign-approval.md`
- **Cowork artifact API:** `mcp__cowork__create_artifact`, `mcp__cowork__update_artifact`

---

## 9. Versioning

Filename `09-dashboard-html-template_v1.4.html` có thể frozen khi bump nội bộ. Đọc HTML comment ở đầu file để biết internal version hiện tại.

**Khi nào bump version:**
- Major (v2.0): thay đổi placeholder schema (rename, add required field)
- Minor (v1.1): add optional placeholder, thêm CSS class, fix bug
- Patch: typo, comment

**Khi bump:** update file đồng thời update README + reference trong `skill/noti-campaign-approval.md`.

---

## 10. Changelog

| Version | Date | Thay đổi |
|---|---|---|
| v1.3 | 05/2026 | Add column "Creator" hiển thị short username (trước @) + tooltip full email khi hover. FROZEN_REVIEW schema thêm optional field `creator` (full email từ `campaign.created_by`). Mục đích: approver scan nhanh để ping owner fix issues qua chat/Slack. CSS `.creator` + helper `shortCreator()` trong JS. |
| v1.2 | 05/2026 | Wording cho approver thuần Việt theo skill/noti-campaign-approval.md Core Principle #8 (KHÔNG show số rule/DIM ra user). Legend dashboard rewrite tự nhiên: "Rule compliance 30 + Title 20…" → "check tự động (tiêu đề/body, content type, routing, PII)"; "DIM-3.x / 4.x" → "AI review chất lượng nội dung"; "HITL-trigger" → "cần human duyệt thủ công". `reasonHtml` trong FROZEN_REVIEW phải dùng nhãn tiếng Việt + mô tả vi phạm thực tế. Schema doc note rõ requirement này. |
| v1.1 | 05/2026 | Multi-env support (UAT/PROD) — thêm 4 placeholders mới: `{{ENV_CLASS}}`, `{{NOTI_MCP_TOOL}}`, `{{NOTI_MCP_SERVER}}`, `{{ATHENA_URL_BASE}}`. Add env-tag badge (PROD đỏ / UAT vàng). Add seg-info display segment size dưới alias, highlight >5M theo Rule 5.1. FROZEN_REVIEW schema thêm optional field `segSize`. Column header wording: "Auto-approve" → "Có thể auto-approve", "Lý do không đạt" → "Ghi chú", "Hành động" → "Hành động đề xuất" (đồng bộ pattern "AI advisory ≠ executor"). |
| v1.0 | 05/2026 | Khởi tạo template sau khi iterate qua 3 batch (22/4 → 8/5 → 12/5). 7 placeholders + JSON schema 13 fields. Companion file 08 chat markdown. |

---

*Tạo: 05/2026 — v1.0*
*Companion: `09-dashboard-html-template_v1.4.html`*
*Author: Cowork agent (Claude) — auto-generated theo direction của Hưn*
