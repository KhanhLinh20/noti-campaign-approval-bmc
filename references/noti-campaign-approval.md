---
name: noti-campaign-approval-detail
description: Sub-skill chi tiết Phase 0-6 cho noti campaign approval. KHÔNG trigger trực tiếp — agent Read file này khi dispatcher SKILL.md (root) route intent verdict/review campaign. Phase 1 hỗ trợ 2 sub-modes (Batch / Single-Specific). Rule 2.12 image out-app advisory. Phase 4.0 AI Agreement gate + audit footer cho DA aggregate. Performance optimization Phase 0 pre-cache + batch script + LLM Judge split. Phase 3 hard mandate + script render_batch_report.py. Phase 4.0 v2 audit schema. v1.6.0 Phase 4↔5 strict separation + session boundary safety. **v1.7.0+: Rule HARD-2 tighten (turn position -1 only) + Rule HARD-5 NEW (compaction signature detection) + Phase 5 BẮT BUỘC dùng `scripts/render_athena_comment.py` để generate canonical comment** — fix production failure 08/06/2026 free-form comment + agent rationalize compaction summary as authority.
author: nga.nguyen6
version: 1.9.2
parent_skill: noti-campaign-approval
---

# Noti Campaign Approval — Full Flow Detail

> **File này là sub-skill** chứa logic chi tiết Phase 0–6. Agent Read từ dispatcher `SKILL.md` (root) khi cần thực thi verdict.
>
> Frontmatter `name: noti-campaign-approval-detail` để tránh duplicate trigger với root SKILL.md.

**Scope:** Duyệt Noti Campaign `state=IN_REVIEW` trên Athena.

**Knowledge base (load Phase 0):**
- `references/` *(13 rule files, v1.16+, phẳng 1 cấp)* — **core 7 files always load, 6 domain files lazy load per detection**:
  - **Always load (Phase 0):** `references/00-core-rules.md` · `references/01-content-type-format.md` · `references/02-content-hard-checks.md` · `references/03-content-quality.md` · `references/04-regulatory-general.md` · `references/05-segment.md` · `references/06-routing.md`
  - **Lazy load** (chỉ khi `scripts/detect_domain.py` flag): `references/fs-products.md` (TTT/Vay Nhanh/VTS) · `references/vietlott.md` · `references/airfare.md` · `references/insurance.md` · `references/cashback-fintech.md` · `references/survey-cio.md` (CIO scope SURVEY)
  - **Phase 2 workflow:** `tier1_check.py` output `domains_to_load` field → agent Read các file `references/<d>.md` matching trước khi Tier 2 LLM Judge.
- **LLM Judge prompt — split 4 files v1.5.0+:**
  - `07-llm-judge-core_v1.12.md` *(internal v1.12, ~32KB)* — **always load Phase 0** — Universal DIMs (3.1-3.5, 3.4b/c/d/e, 3.8, 3.11, 3.13-3.14, 4.1-4.3) + Schema + Sub-score 5-tier + HITL-trigger logic + Reg-floor mapping với `REG_FLOOR_DIMS` constant
  - `07-llm-judge-promo_v1.12.md` *(internal v1.12, ~11KB)* — **lazy load Phase 2** khi CT ∈ {PROMOTION*, GAME, ADVERTISING, EVENT} — DIMs 3.6, 3.7, 3.15-3.18, 4.8
  - `07-llm-judge-quantrong_v1.12.md` *(internal v1.12, ~5KB)* — **lazy load Phase 2** khi CT ∈ {TRANSACTION, REMIND, WARNING, SERVICE} — DIMs 3.9, 3.10, 3.12
  - `07-llm-judge-domain_v1.12.md` *(internal v1.12, ~7KB)* — **lazy load Phase 2** khi `detect_domain.py` match keyword — DIMs 4.4-4.5 (Vietlott), 4.6 (airfare), 4.7 (insurance), 4.9 (FS products)
- `06-hitl-policy_v1.9.md` *(internal v1.7)* — optional — Decision Matrix routing HITL theo Group/Content Type
- `08-batch-review-template_v1.9.md` *(internal v1.5)* — optional — Format reference cho summary table chat markdown + Phase 5 message field examples (concrete VD cho từng verdict template)
- `09-dashboard-html-template_v1.4.html` *(internal v1.4)* — optional — Template HTML cho Cowork artifact (hybrid live+frozen dashboard). Companion với file 08 cho persistent sidebar view. Xem `09-dashboard-template-README.md` để biết cách dùng
- `role-mapping.json` *(internal v2.1)* — optional — Tier 0 client-check reference (PCS/BMC/CIO/PLATFORM_OPERATOR account_id mapping)
- `assets/banned-phrases.json` *(v2026-05-18, Legal/Compliance maintained)* — optional — Reference cho Rule 2.11 banned phrases scan. Format `{phrases: [{pattern, severity, reason, carve_out?}]}`. **KHÔNG preload** Phase 0 (~3KB). Phase 2 load on-demand: `jq -r '.phrases[] | "\(.pattern)\t\(.severity)"' assets/banned-phrases.json` → scan title+body match. Severity blocker → Tier A hard block, critical → Tier C Reg-floor HITL, warning → Tier 2 score deduction.
- `scripts/tier1_check.py` *(v1.4.3+)* — **bắt buộc** — Tier 1 hard rule check CLI (Python). Agent invoke qua công cụ chạy script của runtime (`skill_script`/`script` provider gọi theo tên, HOẶC Bash tool) trong Phase 2: `python scripts/tier1_check.py --unwrap` với stdin = MCP response. Output JSON `{passed, hard_block, hitl_required, issues[] (mỗi item có `user_message` natural VN), advisories[] (v1.4.8+ — image_url review etc.), tags[], user_summary (natural VN cho batch report), domains_to_load[], metadata (gồm image_url v1.4.8+)}`. Exit codes: 0=pass / 1=hard_block / 2=hitl / 99=error. Rules covered: 1.1, 1.8, 2.1, 2.2, 2.3, 2.4, 2.6, 2.8, 2.10, 2.11, **2.12 (v1.4.8+ image advisory)**, 5.1, 6.5, Tier D routing. **NEW v1.4.0:** `domains_to_load` field từ `lib/detect_domain.py` — keyword scan list domain guardrails để Tier 2 LLM load on-demand (tránh load 70KB monolith). **NEW v1.4.8:** Rule 2.12 image out-app advisory — emit tag `image_outapp_review` + extract `image_url` cho Phase 3 batch report column "🖼 Ảnh". **Deterministic — KHÔNG dùng LLM reasoning cho Tier 1.** Xem `scripts/README.md` cho full schema.
- `assets/refid-glossary.tsv` *(v2026-05-18, 2827 unique refids)* — optional — Reference cho Rule 1.8 RefID glossary check (1 file phục vụ cả approve + create skill). Format `name<TAB>refid`. **KHÔNG preload** trong Phase 0 (117KB rarely change). Load on-demand:
  - Phase 2 validate: `awk -F'\t' -v r="<refid>" '$2==r{ok=1;exit} END{exit !ok}' assets/refid-glossary.tsv` → not found → HITL re-confirm
  - Phase 3 enrich (optional UX): `awk -F'\t' -v r="<refid>" '$2==r{print $1}' assets/refid-glossary.tsv` → tên màn để hiển thị summary table
  - Create flow search: `grep -i "<keyword>" assets/refid-glossary.tsv` → candidate refids cho user pick
  
  Source: `assets/MoMo RefID update 18 May 26.xlsx` (từ team Product, cập nhật mỗi đợt release màn mới)

**Distribution:** Files knowledge base distribute trực tiếp trong folder `noti-campaign-approval/` (không bundle zip). Engineer/approver mới checkout/copy folder là có đủ context. Skill load từng file individually theo path tương đối từ disk.

> Convention (v1.2.9+): filename `_vX.Y.md` match latest internal version — rename khi bump. Header bên trong file là source of truth cho version. Xem README.md §2.

**Paired skill:** `noti-campaign-creator` (ngược chiều — tạo campaign).

---

## Phân biệt 2 layer state (quan trọng, không lẫn lộn)

| Layer | Giá trị | Ai quyết định |
|---|---|---|
| **AI review verdict** (hiển thị trong chat) | QUALIFIED / WARNING / HITL_REQUIRED / NOT_QUALIFIED | AI chấm — chỉ là gợi ý cho người duyệt |
| **Athena campaign state** (sau khi đi lệnh) | APPROVED / REJECTED | Người duyệt quyết, AI thực thi |

Verdict AI là **đầu vào** cho quyết định của người duyệt. Athena state là **kết quả** sau khi đi lệnh.

---

## Core principles

1. **AI chỉ review và gợi ý; quyết định approve/reject cuối cùng là của người duyệt.**
2. **4 verdict AI, không binary:** QUALIFIED / WARNING / HITL_REQUIRED / NOT_QUALIFIED.
3. **Luôn hiện confirm panel trước MỌI lệnh approve/reject.** Không auto-execute.
4. **HITL_REQUIRED không approve mặc định.** Gợi ý assign team phù hợp; nếu người duyệt chính là team đó và muốn approve, cần explicit confirm.
5. **Priority confirm bắt buộc** trước approve: NORMAL (default) / BYPASS (với cảnh báo về ML bypass).
6. **Skill không check role permission ở client — Athena enforce permission ở backend** (validate account_id có quyền duyệt content_type tương ứng). MoMo cấp role `PLATFORM_OPERATOR` cross-team cho noti operations, nên Platform Operator thực tế có quyền duyệt mọi CT. Skill skip Tier 0 client-check vì Athena là lớp enforce cuối — nếu user thiếu quyền, MCP sẽ trả error tương ứng (403 / permission denied). Skill chỉ gợi ý team UX (PCS/BMC/CIO/Growth) như assignment hint, **KHÔNG** block action ở client.
7. **Reasoning human-readable** cho người duyệt; structured log `[AI-REVIEW v1.2]` gửi song song vào Athena message field để audit trace.
8. **Không hiển thị số rule** ra user — rule number chỉ dùng internal. Reasoning viết bằng mô tả vi phạm thực tế (VD: "vi phạm Luật Quảng cáo về claim tuyệt đối", không phải "Rule 4.1").
9. **Serial execution, partial failure tolerant.** Fail 1 lệnh không stop batch.

---

## Phase 0 — Init (v1.12.4 — lazy load, tối thiểu round-trip cho runtime hairpin)

> **Nguyên tắc v1.12.4:** athena-copilot/skill_script gọi mỗi `skill_read` là 1 round-trip đắt (hairpin qua extension). Đọc 10 file rule mỗi lần review → 16 tool call → timeout/hang. Nên **KHÔNG eager-load** — chỉ đọc file **đúng lúc cần**. Tổng round-trip: ~6 thay vì ~16.
>
> **Chống bịa vẫn nguyên vẹn:** hard rule do `tier1_check` (script deterministic) enforce — KHÔNG đọc .md không làm giảm độ chính xác (nguyên tắc #1: đếm/soi bằng script, không bằng mắt). Rubric mà LLM thực sự chấm (Tier 2) thì VẪN load đủ ở Phase 2 (chỉ khác: đúng lúc, đúng subset).

1. **KHÔNG đọc spec đã được script enforce** (bỏ eager-load hoàn toàn):
   - `00-core-rules.md`, `02-content-hard-checks.md`, `05-segment.md`, `06-routing.md` — logic đã nằm trong `tier1_check`/`segment_audit` + SKILL.md routing.
   - `assets/banned-phrases.json` (Rule 2.11) + `assets/refid-glossary.tsv` (Rule 1.8, 117KB) — script tự xử lý (data bundle `banned_data.py` + refid agent-side khi cần). **Đừng skill_read file 117KB mỗi lần.**
   - → Chỉ đọc các file này **on-demand** khi cần trích nguyên văn 1 rule cụ thể cho user/comment.

2. **Fetch campaign IN_REVIEW**: `list_campaigns(state=IN_REVIEW)` (batch) hoặc `get_campaign_detail(name)` (single). MCP enforce permission ở backend.

3. **Tier 1 (Phase 2):** invoke `tier1_check` (1 call) → hard rule + routing + `domains_to_load[]`. Đây là nguồn evidence chống bịa.

4. **Tier 2 rubric — load ĐÚNG LÚC + ĐÚNG SUBSET** (KHÔNG bịa điểm — phải có rubric trước khi chấm):
   - `03-content-quality.md` + `04-regulatory-general.md` + `07-llm-judge-core_v1.12.md` — load khi bắt đầu Tier 2 (campaign không hard-block).
   - `07-llm-judge-{quantrong|promo}_v1.12.md` — load **1 subset** theo CT.
   - `07-llm-judge-domain_v1.12.md` + `references/<domain>.md` — chỉ khi `tier1_check` trả `domains_to_load`.
   - `01-content-type-format.md` — chỉ khi nghi CT-mismatch (Rule 1.6 semantic).
   > ⚠️ Nếu chưa load rubric cần thiết mà định chấm Tier 2 → **load trước, KHÔNG đoán điểm**.

**Handle response (sau fetch bước 2):**
- Danh sách trống → báo: "Hiện không có campaign nào ở trạng thái IN_REVIEW."
- Permission error từ MCP → báo: "Bạn không có quyền duyệt campaign. Liên hệ Platform Admin để được hướng dẫn."
- Có data → tiếp Phase 1.

---

## Phase 1 — Campaign Scan (2 sub-modes)

Agent identify mode dựa vào user prompt **TRƯỚC** khi gọi MCP. Logic load + Phase 2-6 **identical** giữa 2 mode — khác chỉ ở entry point Phase 1 và bước tiền-xử lý.

### Mode 1a — BATCH SCAN (default)

**Trigger phrases:**
- "duyệt campaign IN_REVIEW", "duyệt noti hôm nay"
- "có cái nào chờ duyệt không", "list campaign IN_REVIEW"
- "batch approve", "chấm điểm tất cả"
- Không paste tên campaign cụ thể

**Flow:**
1. MCP: `list_campaigns(status=IN_REVIEW)` → array N campaigns
2. **Duplicate detection (2-tier per Rule 2.9):**
   - **Same title+body + same segment** trong 7 ngày → mark `duplicate_hard_block` (→ NOT_QUALIFIED, Tier A)
   - **Same title+body + different segment** → mark `multi_segment_split=true` cho cluster (KHÔNG block, KHÔNG → NOT_QUALIFIED). Phase 3 summary table hiển thị note inline ở row Reasoning: *"💡 Cluster N campaign cùng nội dung, segment khác nhau — Growth split tệp. Có thể duyệt đồng loạt."* Approver scan nhanh nhận biết multi-segment split hợp lệ.
   - Similarity: Jaccard ≥ 90% hoặc hash match.
3. **CT distribution count** theo group hierarchical:
   - Quan trọng (n)
   - Ưu đãi: tổng (m) → trong đó EVENT (k) tách riêng vì cần thematic confirm
   - Tương tác: tổng (p) → trong đó SURVEY (q) tách riêng vì routing CIO
   Dùng để chunking Phase 5 + display group breakdown ở Phase 3.
4. **Team suggestion** cho mỗi campaign (xem bảng Team Mapping bên dưới).
5. Loop từng campaign vào Phase 2.

### Mode 1b — SINGLE / SPECIFIC

**Trigger phrases:**
- "verdict campaign `<name>`", "duyệt campaign `<name>`"
- "duyệt cái này: `<name>`", "chấm điểm `<name>`"
- "duyệt 2-3 cái: `<name_A>`, `<name_B>`, `<name_C>`"
- User paste 1+ campaign name explicit (không có từ "all", "tất cả", "batch")

**Flow:**
1. MCP: `get_campaign_detail(name=X)` cho từng name user cung cấp → 1 đến N objects
   - Nếu MCP trả `status != IN_REVIEW` → cảnh báo user nhưng vẫn xử lý (vd EXPIRED → note không gọi reject được)
2. **Skip** bước 2-4 của batch mode:
   - KHÔNG duplicate detection 7-day (single mode thiếu context array để so sánh)
   - KHÔNG CT distribution count (1-3 campaigns không cần group breakdown)
   - **Team suggestion vẫn run** per-campaign trong Phase 2 (mỗi campaign cần routing độc lập)
3. Vào thẳng Phase 2 cho từng object.

### Shared invariants (cả 2 mode)

- Phase 0 load **identical** (7 guardrails core + role-mapping + library)
- Phase 2 Tier 1 script + Tier 2 LLM **identical** (cùng input format, cùng output schema)
- Phase 4 confirm panel **identical** (luôn reconfirm trước action)
- Phase 5 MCP fire **identical** (`update_campaign_action` per campaign)

---

## Phase 2 — Per-Campaign Review (5-Tier Priority)

Check top-down, match là dừng.

### ⚠️ Hard rule = binary (BẮT BUỘC, không bypass)

Pass thì pass, fail thì fail — `value > limit → BLOCK`, ngược lại **PASS sạch** (không asterisk, không "borderline"). Agent là **executor**, không phải author. **KHÔNG được:** thêm soft warning trên hard pass, bịa limit, invent tag/rule ngoài guardrail, override authority rule sheet. Nghi ngờ limit → Read guardrail trước (không inference). Tag chỉ dùng từ Common Dictionary Phase 5. Vi phạm = bug → retract verdict.

### 🐍 BẮT BUỘC chạy ĐỦ T1 + T2 mỗi lần load+verdict (v1.4.2+, tightened v1.8.0+)

**Quy tắc cứng:** Bất kỳ trigger nào "load campaign + verdict" (single hoặc batch) → agent BẮT BUỘC chạy **CẢ Tier 1 (script) VÀ Tier 2 (LLM Judge)** trước khi output kết quả. **KHÔNG được skip Tier 2** dù Tier 1 đã có kết quả pass/HITL.

### ⛔ Tier 1 evidence mandate (v1.8.0+) — KHÔNG được claim verdict without script output

**Quy tắc cứng:** Agent **BẮT BUỘC** include `tier1_check.py --json` output VERBATIM trong verdict response. KHÔNG được claim "ran script + valid" mà KHÔNG show evidence.

**Anti-pattern (production failure 10/06/2026):**
- ❌ Comment Athena: "form_id UUID valid" — NO evidence từ tier1_check
- ❌ Verdict response: "Tier 1 passed all rules" — KHÔNG show output JSON
- ❌ "Tôi đã verify form_id" — fabricated compliance

**Required pattern:**
```
1. Agent invoke: TIER1_OUTPUT=$(echo $CAMPAIGN | python scripts/tier1_check.py --json '...')
2. Agent SHOW `$TIER1_OUTPUT` JSON verbatim trong response (hoặc parse + cite specific values)
3. Verdict based on TIER1_OUTPUT.passed / hard_block / hitl_required + tags
```

**Technical enforcement (Fix #5 v1.8.0+, mở rộng v1.11.4):** `scripts/render_athena_comment.py` REQUIRE `tier1_check_output` **và** `push_time` + `push_time_ict` trong JSON payload. Schema validation reject payload thiếu field này (hoặc `push_time_ict` không khớp output `timefmt.py`) → agent CANNOT generate Phase 5 comment without Tier 1 evidence + giờ ICT quy đổi bằng script → CANNOT fire MCP. Forces script chain dependency.

### ⛔ Anti-hallucination — Data citation discipline (v1.8.0+)

**⛔ HARD rule — push_time LUÔN trả GIỜ CHUẨN ICT (GMT+7), không ngoại lệ:**

`schedule_config.push_time` từ MCP là epoch milliseconds **UTC (GMT+0)**. Mọi lần hiển thị / tính toán push_time (display cho approver, deadline duyệt push_time − 30/60 phút, urgency 0–10h/10–48h/>48h, stale check) **PHẢI** dùng **giờ ICT chuẩn**:

- **Format bắt buộc:** `DD/MM/YYYY HH:mm` (giờ ICT). **CẤM** kèm `~` (xấp xỉ), **CẤM** hiển thị raw epoch (`(push_time raw: 1783...)`), **CẤM** để nguyên UTC.
- **⛔ BẮT BUỘC quy đổi qua script — CẤM convert thủ công.** Mọi lần quy đổi `push_time` (epoch ms UTC → giờ ICT) PHẢI đi qua `scripts/timefmt.py`, KHÔNG được để LLM tự `+7h` bằng đầu / tự `strftime`. LLM tính epoch ms → datetime **rất hay sai** (off-by-hour, sai ngày, quên `/1000`, quên +7). Cách gọi:
  - **CLI (dùng qua công cụ chạy script của runtime — `skill_script`/`script` provider gọi theo tên `timefmt`, HOẶC Bash tool):** `python scripts/timefmt.py --ms <push_time_ms>` → in JSON `{"push_time_ms":..., "push_time_ict":"08/07/2026 11:55"}`. Copy `push_time_ict` **verbatim** vào bảng. Cũng nhận stdin: `echo '{"push_time": <ms>}' | python scripts/timefmt.py`.
  - **Hoặc import:** `format_push_time(push_time_ms)` (đã dùng bởi `render_batch_report.py` / `render_athena_comment.py`).
- **Chạy `timefmt.py` qua công cụ khả dụng của runtime** (`skill_script`/`script` provider gọi theo tên, HOẶC Bash tool) — **"không có Bash tool" KHÔNG phải lý do bỏ script, PHẢI thử `skill_script` trước.** **Nếu không cơ chế nào chạy được:** **KHÔNG** được ghi giờ đoán bằng đầu. Ghi `⚠️ push_time chưa convert được — cần chạy timefmt.py` và **KHÔNG** kết luận deadline / urgency (0–10h/10–48h/>48h) / stale. (Cùng discipline với "số ký tự chỉ lấy từ script".)

❌ **Sai:** `03:00` (UTC) · `~06/07/2026` · `(push_time raw: 1783486500000)`
✅ **Đúng:** `08/07/2026 11:55` (giờ ICT chuẩn, không `~`, không raw epoch)

---

**Quy tắc cứng cho mọi data citation:**

| Loại citation | Mandate |
|---|---|
| Character position trong string | PHẢI count verbatim từ actual data, NOT fabricate vị trí |
| Field value | PHẢI quote verbatim từ MCP response / script output |
| Source attribution | PHẢI base on skill explicit capability — nếu skill nói "không distinguish được" thì KHÔNG được claim |
| Verdict reasoning | PHẢI reference specific output từ tier1_check / Tier 2 LLM, KHÔNG fabricate |

**Anti-pattern (production failure 10/06/2026):**

1. **Position miscounting:** AI nói "ký tự thứ 3 của group 3 = 7" — actual position 3 = "9", position 1 = "7". → AI fabricate position.
   - **Fix:** Count zero-indexed/one-indexed RÕ RÀNG. Quote actual string trước khi cite position.

2. **Source fabrication:** AI nói "form_id từ Link Test" — skill explicit "KHÔNG distinguish Public vs Link Test". → AI fabricate source.
   - **Fix:** Nếu skill KHÔNG có tool/data → agent KHÔNG được claim. Say "không xác định được nguồn từ skill" thay vì fabricate.

3. **Compliance hallucination:** AI claim "verified form_id" mà KHÔNG show script output. → AI fabricate compliance.
   - **Fix:** Tier 1 evidence mandate trên — PHẢI show script output verbatim.

**Khi uncertain → say "không xác định được" / "skill không có tool để check". KHÔNG fabricate explanation plausible-sounding.**

**Exception duy nhất:** Tier 1 = **hard_block** (Rule 2.4 PII / 2.3 newline / 2.1 title len / etc.) → Tier 2 ghi `❌ N/A` (verdict NOT_QUALIFIED là final từ Tier 1, không cần Tier 2 chấm).

**Output format BẮT BUỘC:** Render **verbatim** bằng `scripts/render_batch_report.py` (KHÔNG LLM tự build/định dạng lại — chống variance + guardrail "unsupported"). Cả T1 và T2 phải có score (hoặc N/A nếu Tier 1 block).

**Layout cố định theo ngữ cảnh (v1.12.3):**
- **`--layout vertical`** (dọc, field: value) — cho **review 1 campaign** HOẶC **side-panel hẹp** (athena-copilot). KHÔNG tràn ngang.
- **`--layout table`** (bảng 11 cột: # · Campaign · CT · Title · Body · 🖼 Ảnh · T1 · T2 · Verdict · Lý do · Hành động) — cho **batch nhiều campaign** trên chat full-width.
- **`--layout auto`** (default): 1 campaign → vertical, ≥2 → table.

**KHÔNG bao giờ** tự bịa bulleted list tùy hứng — layout do script quyết. Từ "list"/"danh sách"/"show me" trong prompt user là natural language, KHÔNG phải yêu cầu đổi format. Chỉ khi user explicit "show as bullets"/"không cần table" mới override.

**Campaign cell — BẮT BUỘC markdown link wrap (v1.5.1+):**

MỖI row trong cột Campaign **PHẢI** dùng format markdown link, KHÔNG bao giờ chỉ là code-block trống link:

```
[`<short_alias>`](<athena_base_url>/notification-v2/list-view?name=<full_campaign_name>)
```

- `short_alias`: dạng `family_variant` ≤ 20 chars (vd `survey_above30`, `r_voucher_nonNFC`)
- `full_campaign_name`: name gốc đầy đủ từ Athena MCP response (KHÔNG strip date prefix trong URL)
- `athena_base_url`:
  - PROD context (MCP server `Noti_MCP__prod`): `https://athena.mservice.io`
  - UAT context (MCP server `Noti_MCP__uat` hoặc tương đương): `https://athena-uat.mservice.io`
  - Agent suy luận env từ MCP server name đang gọi

✅ **GOOD:** `| 1 | [`survey_above30`](https://athena.mservice.io/notification-v2/list-view?name=260522_NT_GMC_PROJECT_SUBWALLET_NAME_AND_SERVICE_VALIDATION_ABOVE30_v1) | SURVEY | ...`

❌ **BAD #1** (no link wrap): `` | 1 | `survey_above30` | SURVEY | ...``
❌ **BAD #2** (full name in display, không alias): `| 1 | [260522_NT_GMC_PROJECT_..._ABOVE30_v1](url) | SURVEY | ...`
❌ **BAD #3** (wrong env URL — UAT trong context PROD): `| 1 | [`survey_above30`](https://athena-uat...) | SURVEY | ...`
❌ **BAD #4** (alias quá dài > 20 chars): `| 1 | [`260522_NT_GMC_PROJECT_FULL_NAME_HERE`](url) | ...`

**Lý do mandate hard:** Cowork members distributed có LLM variance — output không consistent nếu chỉ dựa vào example. Compliance audit: agent self-check trước khi paste table, regex match `\| \d+ \| \[\`[^\`]+\`\]\(http` cho mỗi row.

**Recommend (v1.5.1+):** Dùng `scripts/render_batch_report.py` để render table programmatically thay vì LLM tự build — script enforce 100% compliance, không variance. Xem `scripts/README.md`.

**Cột "Lý do không đạt" BẮT BUỘC dùng natural Vietnamese — KHÔNG show rule code (Principle #8):**
- Lấy từ field `user_summary` trong output `tier1_check.py` (v1.4.3+) — đã dịch sẵn rule code → mô tả VN
- HOẶC gọi `scripts/rule_descriptions.to_user_message(rule, severity)` để translate
- HOẶC gọi `tag_to_user_message(tag)` cho Phase 5 tag → VN
- **TUYỆT ĐỐI KHÔNG paste** `"Rule 2.3: ..."` hoặc `"DIM-3.7 ..."` ra user-facing column
- Source of truth: `scripts/rule_descriptions.py` — sửa wording user-facing chỉ ở đây
- Áp dụng đồng nhất 3 luồng: batch report (template 08) · Phase 5 Athena comment · Dashboard `reasonHtml` (file 09)

**Agent (Claude) là LLM Judge cho Tier 2 (v1.5.0+ split file):** Đọc rubric từ `07-llm-judge-core_v1.12.md` (preloaded Phase 0) + lazy load conditional subset `07-llm-judge-{promo,quantrong,domain}_v1.12.md` theo CT/keyword + `references/03-content-quality.md` + `04-regulatory-general.md` + domain guardrails từ `domains_to_load[]` → chấm DIM-3.x + DIM-4.x → produce score 0-100 + sub_scores + flag HITL trigger.

Agent **PHẢI** invoke `scripts/tier1_check.py` qua **công cụ chạy script của runtime** (`skill_script`/`script` provider — gọi script theo **tên trần** `tier1_check` KHÔNG kèm `.py`; HOẶC Bash tool `python scripts/tier1_check.py` nếu môi trường có) cho Tier A/D hard rule + Tier 1 script-able checks. **TUYỆT ĐỐI KHÔNG** dùng LLM reasoning để check title length, PII regex, segment size, banned phrases, refid lookup, content_type validation. LLM chỉ dùng cho Tier 2 (soft eval qua file 07 LLM Judge).

> ⛔ **HARD — Số ký tự chỉ được lấy từ script, cấm tự đếm.** Mọi con số "X ký tự" trong bảng verdict PHẢI copy verbatim từ `tier1_check.py` stdout (`metadata.title_len`/`body_len`). LLM đếm ký tự tiếng Việt có dấu + khoảng trắng **rất hay sai** (VD thực: title 21 bị đếm 22, body 28 bị đếm 26 do model tự thu gọn khoảng trắng đôi sau khi strip placeholder). Chạy script qua công cụ khả dụng của runtime — **`skill_script`/`script` provider (gọi theo tên) HOẶC Bash tool**; **"không có Bash tool" KHÔNG phải lý do bỏ script, PHẢI thử `skill_script` trước.** **Nếu không cơ chế nào chạy được** → **KHÔNG được ghi số đoán**; ghi "⚠️ chưa verify — cần chạy tier1_check.py" và không kết luận PASS/FAIL rule 2.1/2.2.

### ⛔ Check routing — mỗi loại thông tin PHẢI gọi đúng tool chuyên trách

Khi check 1 campaign, **KHÔNG** được để LLM tự suy luận các số liệu dưới đây. Mỗi loại check bắt buộc đi qua tool tương ứng (single source of truth):

| Loại check | Tool BẮT BUỘC gọi | Lấy giá trị từ | Cấm |
|-----------|-------------------|----------------|-----|
| **Số ký tự** (title/body) | `scripts/char_count.py` (CLI riêng) **hoặc** `tier1_check.py` (`metadata.title_len`/`body_len`) — cả 2 dùng chung `lib.rules.strip_placeholders`, ra CÙNG số | `char_count.py` stdout `title_len`/`body_len` (placeholder ${...} = 0) | LLM tự đếm bằng mắt; render `${lastname}`→"bạn" rồi +3 |
| **Thời gian bắn** (push_time) | `python scripts/timefmt.py --ms <push_time_ms>` (CLI riêng) **hoặc** `timefmt.py::format_push_time()` (dùng bởi `render_batch_report.py` / `render_athena_comment.py`) | `push_time_ict` từ stdout script (`DD/MM/YYYY HH:mm`, +7h từ UTC), copy verbatim | Convert thủ công / LLM tự +7h bằng đầu; để nguyên UTC; raw epoch; kèm `~` |
| **Segment size** | MCP `segment-mcp: athena-get-segment-info(segment_name)` → size + điều kiện; `tier1_check.py` chấm Rule 5.1/5.3/5.5 + `segment_scorecard` | `segment.size` từ MCP response của CHÍNH campaign đó | Reuse segment của campaign khác; LLM đoán size |

**Nguyên tắc chung:** số ký tự → `char_count.py`; thời gian → `timefmt`; segment → `segment-mcp`. Nếu 1 tool không chạy được → ghi "⚠️ chưa verify — cần <tool>", **KHÔNG** đoán số. Char count & thresholds có **1 nguồn duy nhất** (`lib/rules.py` + `lib/constants.py`) — `char_count.py` và `tier1_check.py` đều import từ đó nên không bao giờ lệch nhau.

**Pseudo workflow per BATCH (v1.5.0+ optimized — batch script + conditional LLM load):**

```bash
# 1. Fetch all campaign details (parallel MCP calls)
all_campaigns_json='{"campaigns": [<camp1_data>, <camp2_data>, ...]}'

# 2. BATCH Tier 1 script invocation (v1.5.0+ — 1 Python startup thay vì N×) 
echo "$all_campaigns_json" | python scripts/tier1_check.py --batch > /tmp/tier1_batch.json
# Output: {"batch": true, "count": N, "results": [result1, result2, ...]}

# 3. Parse batch result — per campaign branch theo result.hard_block / hitl_required
jq -c '.results[]' /tmp/tier1_batch.json | while read result; do
  camp_name=$(echo "$result" | jq -r '.metadata.campaign_name')
  ct=$(echo "$result" | jq -r '.metadata.content_type')
  group=$(echo "$result" | jq -r '.metadata.group')
  hard_block=$(echo "$result" | jq -r '.hard_block')
  domains=$(echo "$result" | jq -r '.domains_to_load[]')
  
  if [[ "$hard_block" == "true" ]]; then
    # Tier 2 = N/A, verdict NOT_QUALIFIED final
    continue
  fi
  
  # 4. CONDITIONAL Tier 2 LLM load (v1.5.0+ — chỉ load DIMs relevant với CT)
  llm_context_files=("07-llm-judge-core_v1.12.md")   # always (preloaded Phase 0)
  
  if [[ "$ct" =~ ^(PROMOTION|GAME|ADVERTISING|EVENT) ]]; then
    llm_context_files+=("07-llm-judge-promo_v1.12.md")
  fi
  
  if [[ "$ct" =~ ^(TRANSACTION|REMIND|WARNING|SERVICE)$ ]]; then
    llm_context_files+=("07-llm-judge-quantrong_v1.12.md")
  fi
  
  if [[ -n "$domains" ]]; then
    llm_context_files+=("07-llm-judge-domain_v1.12.md")
    # Plus domain guardrails (already lazy load via detect_domain.py)
  fi
  
  # 5. Invoke Tier 2 LLM Judge với context = core + conditional subsets
  # → Save ~40-50% token vs monolith v1.11 (12K → 6-8K input tokens)
done
```

**Performance impact (v1.5.0+ vs v1.4.9):**
- **Option A (Phase 0 pre-cache)**: Save ~30-50 sec/batch (banned-phrases + refid-glossary + LLM judge core load once)
- **Option B (batch script)**: Save ~5-10 sec/batch (1× Python startup vs 10×)
- **Option C (split LLM judge)**: Save ~5-10 sec/campaign × N (~50-100 sec for 10 campaigns)
- **Total**: 5 min → ~2.5-3 min cho 10 campaigns (~50% faster)

**Backward compat:** `tier1_check.py` single-mode vẫn work — `--batch` là opt-in flag.

**Segment Condition Audit (Rule 5.3, v1.17+) — đọc điều kiện cấu thành segment, so với policy duyệt:**

> Trước đây approver phải **mở segment xem điều kiện bằng tay**. Nay `segment-mcp` trả được điều kiện → agent đọc tự động + chấm điểm.

```bash
# 1b. (TRƯỚC khi tier1_check) Với mỗi campaign có segment → fetch điều kiện segment:
#     Gọi MCP segment-mcp: athena-get-segment-info(segment_name)
#     → CHỈ lấy conditionV2 (include/exclude) + field dataSource
#     → ⚠️ KHÔNG lấy "Raw config" (response ~73KB, tốn token)
#     → inject vào campaign JSON: segment.condition_v2 + segment.data_source
#
#   tier1_check.py tự chạy Rule 5.3.A (tuổi) + 5.3.B (blacklist) + 5.5 (staff)
#   + 5.6 (segment hành vi ↔ content_type) khi condition_v2 có mặt.
```

> **📋 Procedural rule (Nhóm 3) — NO segment reuse across campaigns:**
> `segment_name` truyền vào `athena-get-segment-info` PHẢI lấy **verbatim từ MCP response của chính campaign đó** (`get_campaign_detail` → field `segment`). TUYỆT ĐỐI KHÔNG reuse segment data của campaign khác trong cùng batch hoặc conversation trước — kể cả khi tên campaign và tên segment trông giống nhau. Mỗi campaign = 1 MCP call độc lập.

> **⚠️ Rule 5.6 — chỉ đọc attribute/điều kiện, KHÔNG đọc tên segment.** "Đã dùng dịch vụ" được suy ra từ: attribute họ `user_transaction_*`/`user_active_*`/`user_project_*`, `dateRange` recency (≠ALWAYS_ACTIVE), custom-SQL giao dịch, hoặc `dataSource` có BIGQUERY. Tên segment (kể cả có `_A30`) KHÔNG được dùng làm căn cứ.

- **5.3.A — Compliance độ tuổi:** domain giới hạn tuổi (Vietlott / FS vay / insurance) mà segment include nhóm `user_age_group_lower_18` / `user_age_*_1[0-7]` → **hard block (NOT_QUALIFIED)**; không có điều kiện tuổi nào → **HITL** verify 18+.
- **5.3.B — Exclude blacklist:** domain tài chính/rủi ro (FS vay / cashback / Vietlott) mà excludeConditions không có `user_blacklist_risk` → **HITL** (BMC/Legal).
- **5.3.C/D (Tier 2 LLM):** so điều kiện segment (location/demographics/behavior) với claim trong title+body → mismatch → WARNING; target quá rộng + size lớn → advisory. Agent dùng conditionV2 đã decode làm input cho LLM Judge.
- **5.5 — Exclude nhân viên MoMo (WARNING):** excludeConditions không có `user_account_staff_*` → flag (không block), vào scorecard.
- **🧩 Segment Compliance Scorecard:** `tier1_check.py` output field `segment_scorecard` = checklist segment vs rule BMC/CIO (size / loại nhân viên / loại blacklist / tuổi) với status `pass|fail|warn` + lý do + `overall` đạt/chưa-đạt. **Phase 3 render block scorecard cho approver** để họ thấy ngay "thiếu gì để pass" — thay việc mở segment check tay. Ví dụ:
  ```
  🧩 Segment check (BMC) — chưa đạt (2/4)
     ✅ Size 1.2M < 5M     ❌ Chưa loại nhân viên MoMo
     ❌ Chưa loại blacklist  ✅ Tuổi: chỉ 18+
  ```
- **Token discipline:** chỉ truyền `conditionV2` (include/exclude), KHÔNG truyền raw config. Map `attributeId`/`tagId` → tên hiển thị qua `athena-list-attribute` / `athena-search-attribute-tags` (cache 1 lần/batch) khi cần render cho user.
- **Skip gracefully:** segment không fetch được điều kiện (custom upload list, hoặc MCP lỗi) → Rule 5.3/5.5 + scorecard skip, KHÔNG block; vẫn giữ Rule 5.1 size cap.

**Tier 2 LLM Judge workflow v1.5.0+ (split file, conditional load):**

```
1. Core rubric (always loaded Phase 0): 07-llm-judge-core_v1.12.md
   → Schema, sub-score 5-tier, HITL/Reg-floor logic, DIMs universal 
     (3.1-3.5, 3.4b/c/d/e, 3.8, 3.11, 3.13-3.14, 4.1-4.3)

2. Conditional load Phase 2 per campaign — chỉ DIMs relevant:
   - CT ∈ {PROMOTION*, GAME, ADVERTISING, EVENT} → 07-llm-judge-promo_v1.12.md
       (DIMs 3.6, 3.7, 3.15-3.18, 4.8)
   - CT ∈ {TRANSACTION, REMIND, WARNING, SERVICE} → 07-llm-judge-quantrong_v1.12.md
       (DIMs 3.9, 3.10, 3.12)
   - detect_domain match keyword → 07-llm-judge-domain_v1.12.md
       (DIMs 4.4-4.5 Vietlott, 4.6 airfare, 4.7 insurance, 4.9 FS products)

3. Also load references/03-content-quality.md + 04-regulatory-general.md (always)
   + references/<d>.md cho mỗi domain in domains_to_load[]

4. For each campaign:
     Evaluate DIM rubric (universal + conditional) → sub_score 0/25/50/75/100
     Calculate weighted overall score 0-100
     Flag HITL trigger nếu sub_score ≤ 25 ở DIM Reg-floor eligible (DIM-1.6/4.1/4.2/4.3/4.6/4.7/4.8/4.9 — nguồn chuẩn: REG_FLOOR_DIMS)

5. Output T2 score + sub_score breakdown trong batch table

— Lý do split: giảm 40-50% token input per Tier 2 call (12K → 6-8K), faster LLM response
— Backward compat: REG_FLOOR_DIMS constant trong 07-llm-judge-core (single source of truth)
```

**Lý do split + lazy load:**
- Mỗi turn không load 70KB rules (đa số không apply)
- Context window dành cho Tier 2 LLM Judge tập trung vào rules relevant
- Maintain dễ: rule FS đổi → edit 1 file `fs-products.md`, KHÔNG cần thay file khác

**Script output schema:** `{passed, hard_block, hitl_required, issues[], tags[], metadata}` — xem `scripts/README.md`.

**Lý do bắt buộc:**
- Deterministic (no hallucinate — vd Title ≤ 65 bug)
- Audit replay được (same input → same output)
- Cost 0 token cho Tier 1 (LLM chỉ chạy Tier 2)
- Source of truth: `scripts/constants.py` — rule change = edit 1 chỗ

**Rules KHÔNG script-able → vẫn dùng LLM (Tier 2):** 1.6 CT semantic / 3.x DIMs / 3.4b spelling / 3.5b emoji Unicode / 4.x regulatory. Xem `07-llm-judge-core_v1.12.md` (+ promo/quantrong/domain subsets).

### Tier A — Hard Block → NOT_QUALIFIED

| Check (internal) | Limit (từ guardrail, BẮT BUỘC quote đúng) |
|---|---|
| Title length | **> 30 → BLOCK** (Rule 2.1) |
| Body length | **> 120 → BLOCK** (Rule 2.2) |
| `content_type ∉ 14 valid codes` | Rule 1.1 |
| PII: phone / email / CCCD / bank account | Rule 2.4 |
| Test content: gibberish / keyword test / entropy < 1.5 | Rule 2.8 |
| Duplicate same content+segment 7 ngày | Rule 2.9 case 1 |
| Format: push_inapp=TRUE hoặc Header/Popup/XBanner/Snackbar | Rule 2.10 |
| Banned phrase severity=blocker | Rule 2.11 (scan `banned-phrases.json`) |
| Segment size > 5M (general) / > 250K (SURVEY) | Rule 5.1 / 6.5 |
| Push cap > 500K/day/project (SURVEY only) | Rule 6.5 |

**Không check priority=BYPASS ở đây** — priority confirm ở Phase 4 khi đi lệnh approve.

### Tier B — HITL-Trigger (từ LLM) → HITL_REQUIRED

Dimension đặt `hitl_triggered: true` kích hoạt HITL bất kể overall score (không đóng góp score):
- **Typo VN/EN** hoặc suspected proper noun (DIM-3.4b)
- **Promotional claim sensitive action** — yêu cầu OTP/đổi mật khẩu/gọi số/link ngoài (DIM-3.7 / DIM-3.9)
- **Angle vi phạm group Quan trọng** (Gamification/Emotional Connection — DIM-3.9)
- **Vietlott/xổ số content** (DIM-4.4 financial claim, DIM-4.5 promo) — luôn HITL khi applicable
- **RefID không thuộc glossary** (Rule 1.8) — load on-demand `assets/refid-glossary.tsv`, `awk -F'\t' '$2=="<refid>"'` không match → HITL re-confirm (không hard block, list có thể outdated)
- **RefID landing không khớp chủ đề noti** (Rule 1.6 axis 2) — lookup tên màn từ refid, so sánh keyword với title+body
- **Emoji modern Unicode 14+** (Rule 3.5b) — render risk device cũ, LLM identify từ pretrained
- **Banned phrase severity=critical** (Rule 2.11) — match phrase có carve-out, approver verify context
- **BU vượt 10 campaign push/day** (Rule 5.2) — count per `owner_account_id`, ≥10 → HITL re-confirm

### Tier C — Regulatory Floor → HITL_REQUIRED

Dimension score-based có `sub_score ≤ 25` buộc HITL bất kể overall. Danh sách DIM thuộc Reg-floor được định nghĩa ở constant `REG_FLOOR_DIMS` trong `07-llm-judge-core_v1.12.md` — single source of truth:
- **CT semantic mismatch** (Rule 1.6) — content không khớp content_type
- **Absolute superlative** (DIM-4.1) — "tốt nhất/duy nhất/tuyệt đối/đảm bảo"
- **Kỳ thị/phân biệt đối xử** (DIM-4.2)
- **Nội dung toàn tiếng nước ngoài** (DIM-4.3)
- **Vé máy bay giá thiếu điều kiện** (DIM-4.6) — "Vé từ 99k" không disclaimer
- **Bảo hiểm vague scope** (DIM-4.7) — "bảo hiểm toàn diện"
- **Cashback vague hoặc zero conditions** (DIM-4.8) — "hoàn tiền hấp dẫn" không số / "Hoàn 50% không giới hạn"
- **MoMo FS product wording sai** (DIM-4.9) — Vay Nhanh/TTT/Newton/VTS dùng wording không thuộc BOM Legal approved list ("Vay Nhanh lãi 0%", "TTT tiết kiệm", "VTS nhận ngay 30 triệu"...)

### Tier D — Exception Override → HITL_REQUIRED (dù score ≥ 85)

Check theo thứ tự:

```
1. group=Quan trọng + format violation → PCS
2. group=Quan trọng                    → PCS
3. content_type=SURVEY                 → CIO
4. content_type=EVENT                  → BMC (thematic confirm)
5. segment_size > 5M                   → DUAL: Growth + content-group approver (PCS/BMC theo CT)
```

### Tier E — Score-Based Final

| Score | AI Verdict | Màu hiển thị |
|---|---|---|
| < 50 | NOT_QUALIFIED | 🔴 |
| 50–84 | WARNING | 🟠 |
| 85–89 | QUALIFIED | 🟡 |
| ≥ 90 | QUALIFIED | 🟢 |

> Ngưỡng **verdict** giữ nguyên (QUALIFIED ≥ 85, khớp `06-routing`/`07-core`). Màu chỉ tách trong band QUALIFIED: 🟢 ≥ 90 vs 🟡 85–89, đúng theo Score color legend canonical (`08-batch-review-template_v1.9.md`).

### Output per campaign

```yaml
campaign_id, verdict, score, 
human_reasoning: "Score 87. Title chặt chẽ..."   # user-facing, KHÔNG số rule
top_issues: [...]                                 # internal cho structured log
hitl_trigger, reg_floor_breach, tier_d_exception,
suggested_team: PCS|BMC|CIO|Growth|null
duplicate_info, suggested_action
```

---

## Team Mapping (convention, KHÔNG enforce)

| CT / Condition | Team đề xuất |
|---|---|
| TRANSACTION, REMIND, WARNING, SERVICE (Quan trọng) | **PCS** |
| PROMOTION*, GAME, ADVERTISING, FRIENDS, BUSINESS_PAGE, SOCIAL | **BMC** |
| EVENT | **BMC** (thematic confirm) |
| SURVEY | **CIO** |
| Segment > 5M | **DUAL** — Growth + content-group approver (PCS/BMC theo CT). Cả 2 phải confirm. PLATFORM_OPERATOR có thể override với `just=platform_authority_dual_skip`. |

**Lưu ý:** Athena không enforce permission theo CT. Đây chỉ là gợi ý UX, user có toàn quyền override.

---

## Phase 3 — Summary MD Table

Format bảng chính = **11 cột summary-table-first** (canonical theo `08-batch-review-template_v1.9.md`). Default output cho batch review, deep-dive card 13-row chỉ render khi user yêu cầu zoom 1 campaign cụ thể.

### Output adaptive theo campaign count (v1.4.5+)

| Count | Output default | Cards detail |
|---|---|---|
| **1 campaign** (Single mode) | Bảng 1-row consistent format + section "Campaign info" 12-row dưới bảng | Không cần — info đã đủ chi tiết |
| **2-5 campaigns** | Bảng summary N-row | Render on-demand khi approver hỏi "xem chi tiết #X" |
| **6+ campaigns** (Batch lớn) | Bảng summary mandatory | Render on-demand only |

**Lý do consistent format:** Approver quen 1 layout, không phải re-learn khi count thay đổi. Bảng 1-row cho single mode tránh "tự bịa" output dạng card-only.

```markdown
> 📊 Tier 1 (Script) — Rule/Title/Body/CT/Routing · Tier 2 (LLM Content Review theo 07-llm-judge-core_v1.12.md + conditional subsets)
> Ngưỡng: 🟢 ≥ 90 | 🟡 85–89 | 🟠 50–84 | 🔴 < 50 | 🟣 HITL-triggered | ⛔ EXPIRED

| # | Campaign | CT | Title | Body | 🖼 Ảnh | T1 | T2 | Verdict | Lý do không đạt | Hành động |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | [`xyz_promo`](https://athena.mservice.io/notification-v2/list-view?name=xyz_promo) | PROMOTION_SERVICE | Cuối tuần hoàn 20%, tối đa 100k | Hoàn 20% tối đa 100k cho giao dịch đầu tiên cuối tuần | — | 🟢 100 | 🟢 87 | 🟢 QUALIFIED | — | Approve NORMAL |
| 2 | [`tet_2027`](https://athena.mservice.io/notification-v2/list-view?name=tet_2027) | EVENT | Lắc Xì Tết 2027 sắp về | Đón Tết 2027 cùng MoMo với Lắc Xì... | [Icon.png](https://static.momocdn.net/.../tet27.png) ⚠️ | 🟢 100 | 🟡 82 | 🟣 HITL_REQUIRED | EVENT cần BMC xác nhận thematic context Lắc Xì/Tết — review hình trước duyệt | Assign BMC |
| 3 | [`voucher_best`](https://athena.mservice.io/notification-v2/list-view?name=voucher_best) | ADVERTISING | Voucher tốt nhất tháng | Đảm bảo trúng quà khủng... | — | 🟢 100 | 🔴 32 | 🔴 NOT_QUALIFIED | Vi phạm Luật Quảng cáo về claim tuyệt đối ("tốt nhất"); thiếu cơ chế game cụ thể ("đảm bảo trúng") | Reject |
| 4 | [`survey_cx`](https://athena.mservice.io/notification-v2/list-view?name=survey_cx) | SURVEY | Khảo sát ngắn 1 phút | MoMo muốn nghe ý kiến của bạn... | — | 🟢 100 | 🟢 91 | 🟣 HITL_REQUIRED | Khảo sát — cần CIO duyệt (không auto-schedule) | Assign CIO |
```

**Cột "Lý do không đạt" BẮT BUỘC tiếng Việt tự nhiên, KHÔNG số rule** (Principle #8). Lấy từ `user_summary` của Tier 1 + diễn giải DIM của Tier 2. Full deep-dive card chỉ show khi user hỏi zoom (vd "xem chi tiết #3").

**Cột "🖼 Ảnh" (v1.4.8+)** — render từ `metadata.image_url` của Tier 1 output:
- Trống (`—`) khi campaign không có image_url
- Markdown link `[<filename>](<image_url>) ⚠️` khi có image + `allow_out_app=true` (advisory tag `image_outapp_review`)
- Approver **BẮT BUỘC click link visual review trước khi APPROVE** — Phase 4 confirm panel highlight rõ
- Lý do: icon nhỏ (600×400) có thể bị iOS render full screen ở out-app push → cần human visual check (URL pattern không đủ catch)

**Optional enrich — RefID name lookup (UX nicety, v1.2.9+):**

Khi summary table hoặc drilldown mention refid, agent có thể auto-lookup tên màn từ `assets/refid-glossary.tsv` để approver scan nhanh:

```bash
awk -F'\t' -v r="<refid>" '$2==r{print $1}' assets/refid-glossary.tsv
```

VD hiển thị: `ref_id=check_security (An toàn thiết bị)` thay vì `ref_id=check_security` trống.

Áp dụng khi:
- Drilldown 1 campaign cụ thể (approver hỏi "campaign #3 refid là gì")
- Summary table có cột RefID (option, không default vì cột dài)
- Phase 5 comment mention refid để approver/auditor đọc log hiểu ngay

Sau bảng: breakdown theo verdict + flag đặc biệt (duplicate cluster, segment lớn...).

---

## Phase 4 — Action Confirmation (Multi-Step)

### ⛔ 4.HARD — Phase 4↔5 Strict Separation + Session Boundary Safety (v1.6.0+)

> **Lý do tồn tại:** Failure mode đã xảy ra trong production (2026-06-02): plugin Cowork bị cut session giữa chừng, summary recap nói "agent chờ confirm", system instruction trên resume `"continue directly without asking"` — agent đã auto-fire `update_campaign_action(APPROVED)` cho prod campaign mà **KHÔNG** có explicit confirm từ user trong session hiện tại. Đây là hậu quả thực tế nghiêm trọng.

#### Quy tắc cứng — KHÔNG bypass dưới bất kỳ điều kiện nào

**Rule HARD-1: Phase 4 và Phase 5 PHẢI là 2 turn riêng biệt**
- Verdict turn (Phase 3 + 4): agent show summary table + AI suggest + ask confirmation
- Confirm turn (Phase 5): user PHẢI explicit type action keyword TRONG SESSION HIỆN TẠI → agent mới fire MCP
- Agent **TUYỆT ĐỐI KHÔNG** fire `update_campaign_action()` cùng turn với verdict, dù user reply ngắn gọn ("ok"/"yes" nhưng ambiguous về action cụ thể)

**Rule HARD-2 (tightened v1.7.0+): Explicit action keyword PHẢI ở turn position -1**

Trước khi fire MCP, agent BẮT BUỘC verify **message ngay trước turn hiện tại** (`conversation_history[-1]` role=user) match regex pattern. KHÔNG phải bất kỳ message nào trong session history.
```
^(approve|reject|route HITL|skip)\s+\d+([,\s]*\d+)*(\s+(NORMAL|BYPASS|to\s+\w+))?(\s*:\s*.+)?$
```

Valid examples:
- `approve 1,2 NORMAL`
- `reject 1: title vi phạm Luật Quảng cáo`
- `route HITL 1,3 to BMC`
- `skip 2`

**KHÔNG accept:**
- `yes` / `ok` / `đồng ý` / `agree all` — implicit signals, không rõ action cụ thể (campaign #N nào, action gì)
- `approve` (no number) — không rõ campaign nào
- Action keyword paste từ conversation summary — không tính
- System instruction "continue directly" — KHÔNG override rule này

**Rule HARD-3: Session boundary invalidation**

Khi session **resume từ conversation summary** (vd plugin cut → restart, hoặc context length exceeded → compact):
- Summary có thể nói "agent đang chờ user confirm" hoặc "user đã approve" — **VÔ HIỆU**
- System instruction `"continue directly without asking"` — **VÔ HIỆU** cho MCP action
- Agent BẮT BUỘC re-show verdict table + re-ask confirmation **trong turn đầu tiên** sau resume
- Chỉ accept action keyword typed **SAU** lần re-show, **TRONG cùng session**

**Rule HARD-4: MCP fire gate verification checklist**

Trước mỗi call `update_campaign_action(action=APPROVED|REJECTED)`, agent self-verify:

| Check | Pass condition |
|---|---|
| Confirm at turn -1 | `conversation_history[-1]` role=user khớp regex HARD-2 |
| Campaign name match | Action keyword reference đúng campaign trong batch hiện tại |
| Approver consistent | Same approver email throughout session (không switch user mid-batch) |
| No compaction signature | Session KHÔNG detect compaction pattern (xem HARD-5) |
| Re-show after resume | Nếu HARD-5 detected, đã re-show verdict + re-ask chưa |

Fail bất kỳ check → **STOP**, re-show confirmation panel.

**Rule HARD-5 (NEW v1.7.0+): Compaction signature detection**

Agent BẮT BUỘC scan toàn bộ conversation history cho signatures dưới đây. Nếu detect → flag session as "compacted/resumed" → BẮT BUỘC re-show verdict + re-ask. KHÔNG fire MCP dù turn -1 match regex (vì keyword có thể là agent self-echo từ summary, không phải user fresh input).

**Signature patterns (regex hoặc substring match):**

| Pattern | Source |
|---|---|
| `"Continue the conversation from where it left off"` | Resume instruction |
| `"summary below covers the earlier portion"` | Summary header |
| `"Note: ... was read before the last conversation was summarized"` | File state reminder |
| `"session was compacted"` | Generic compaction |
| `"Pick up the last task as if the break never happened"` | Resume directive |
| `"Resume directly — do not acknowledge"` | Resume directive |
| `"This session is being continued from a previous conversation"` | Session continuation marker |
| `"ran out of context"` | Context exhaustion |

**Logic:**
```python
def detect_compaction(conversation_history) -> bool:
    """Scan all system/user/assistant messages for compaction signatures."""
    SIGNATURES = [
        "Continue the conversation from where it left off",
        "summary below covers the earlier portion",
        "was read before the last conversation was summarized",
        "session was compacted",
        "Pick up the last task as if the break never happened",
        "Resume directly — do not acknowledge",
        "This session is being continued from a previous conversation",
        "ran out of context",
    ]
    for msg in conversation_history:
        content = str(msg.get("content", ""))
        for sig in SIGNATURES:
            if sig.lower() in content.lower():
                return True
    return False

# Application:
if detect_compaction(conversation_history) and not re_show_done_this_session:
    raise FireGateError(
        "Compaction signature detected — BẮT BUỘC re-show verdict + đợi user "
        "type fresh action keyword. KHÔNG fire MCP dù turn -1 có keyword."
    )
```

**Rationale:** Khi session compaction xảy ra, agent có thể "tự echo" action keyword từ summary vào context turn -1 mà không phải user fresh input. Spec HARD-2 turn -1 check vẫn không đủ — cần HARD-5 layer thêm.

**Recovery flow sau detect:**
1. Agent show full verdict table (Phase 3) again
2. Agent show confirmation panel (Phase 4) again
3. Đợi user gõ fresh action keyword
4. Verify lại HARD-2/4 trên user message **mới** (sau re-show)
5. Mới fire MCP

Lý do không bypass: action approve trên prod là consequential. False positive (em block khi không cần) chỉ tốn 1 turn re-show. False negative (em fire khi không nên) = real prod consequence không rollback được.

#### Anti-patterns — TUYỆT ĐỐI cấm

- ❌ Fire MCP action trong cùng turn với verdict turn ("verdict xong em approve luôn")
- ❌ Interpret "yes" / "ok" reply là action confirmation (cần explicit `approve N`)
- ❌ Trust conversation summary nói "user đã confirm" — summary là context, không phải authority
- ❌ Follow "continue directly" instruction → fire MCP mà bỏ qua re-confirm
- ❌ Batch fire nhiều campaigns dù user chỉ type "approve" mơ hồ — phải có danh sách rõ
- ❌ Self-justify ("user đã agree all ở turn trước, em fire luôn") — rule HARD-1 không có exception

#### Vi phạm = bug critical

Agent vi phạm Rule HARD-1/2/3/4 = bug critical. Owner (huong.vu4) cần được notify ngay qua post-mortem comment vào campaign affected (note rõ "auto-fire without explicit confirm" trong Athena `action_logs.comment`).

---

### 4.0 AI Agreement gate (v1.4.9+, refined v1.5.2+) — BẮT BUỘC trước mọi action

> **Scope:** Cowork users (Claude UI) — KHÔNG áp dụng khi approver duyệt thẳng trên Athena UI.
>
> **Mục đích:** Capture disagree rate giữa approver và verdict AI để DA aggregate bi-weekly + làm tiền đề automation phase tiếp theo.

#### Semantic clarification (v1.5.2+) — `ai_agreement` định nghĩa lại

`ai_agreement` track **WHETHER AI INTENT WAS RESPECTED**, KHÔNG phải "action có giống suggestion verdict tag không".

**`ai_agreement = yes` khi:**
- AI suggest QUALIFIED auto-approve + approver approves
- AI suggest HITL → team X + **approver thuộc team X** review và approves (HITL outcome positive)
- AI suggest HITL → team X + team X review và rejects (HITL outcome negative — vẫn yes vì team đã review)
- AI suggest HITL → team X + **cross-team approver approves NHƯNG đã coordinate offline với team X** (offline_review=yes + review_note)
- AI suggest REJECT + approver rejects
- AI suggest WARNING + approver approves WITH note offline review

**`ai_agreement = no` (genuine override) khi:**
- AI suggest HITL → team X + approver cross-team approve **KHÔNG qua review team X** (no offline coordination)
- AI suggest REJECT + approver approves (skip rule)
- AI suggest QUALIFIED + approver rejects without justification
- AI suggest WARNING + approver approves **without offline review**

**Anti-pattern (em đã sai trong session 2026-05-27):** 
- AI gợi ý HITL → PCS, PCS approver review + approve → label `ai_agreement=no` là SAI. Đúng là `yes` (PCS đã review, HITL intent respected).

#### Flow Phase 4.0 — 2-step gate

**Bước 1:** Sau khi show summary table (Phase 3), agent BẮT BUỘC ask approver:

```
Trước khi đi lệnh, vui lòng xác nhận đồng ý/không đồng ý với verdict 
của em (BẮT BUỘC để log audit):

Format reply (chọn 1):
- "agree all"                    → đồng ý + fire theo AI suggest action
- "agree N1,N2 / disagree N3"    → split per campaign
- "approve N1,N2 NORMAL"         → action ≠ AI suggest → agent hỏi tiếp Bước 2
- "reject N1,N2: <lý do>"        → action ≠ AI suggest → agent hỏi tiếp Bước 2
- "disagree N1: <lý do>"         → genuine override (không qua review)
```

**Bước 2 (followup khi action ≠ AI suggest):** Agent BẮT BUỘC ASK:

```
Action chị chọn KHÁC với AI suggest cho campaign #N (AI gợi ý: <verdict_action>).
Chị xác nhận đã review offline rồi chưa?

Format reply:
- "yes: <brief note>"       → reviewed offline → log offline_review=yes, ai_agreement=yes
                              (vd: "PCS team đã confirm", "BMC offline OK", "Legal đã verify")
- "no, override"            → genuine bypass → log offline_review=no, ai_agreement=no
                              → BẮT BUỘC capture disagree_reason
```

**Rule:**
- Approver KHÔNG được skip step này
- Nếu reply không rõ → agent hỏi lại (đừng tự diễn giải)
- `review_note` natural language ngắn (vd "PCS reviewed offline OK", "BMC confirmed via Slack")
- `disagree_reason` natural language (vd "Push time-sensitive, không reach được BMC, fire dưới authority")

### 4.1 Chọn group xử lý

`ask_user_input_v0`: "Xử lý group nào trước?"
Options: `QUALIFIED (N)` / `NOT_QUALIFIED (M)` / `WARNING (P)` / `HITL_REQUIRED (K)` / `Xem lại summary`

### 4.2a QUALIFIED → 3 sub-steps

**Sub-step 1 — Review list:**
```
🟢 N campaigns sắp approve:
- #1 XYZ Promo (87) — Title chặt chẽ, cashback có điều kiện
- #7 ABC Event (85) — Đúng angle, personalization hợp lệ
```

**Sub-step 2 — Priority confirm (BẮT BUỘC):**

`ask_user_input_v0`: "Approve với priority nào?"
- `NORMAL (mặc định, apply đầy đủ ML rules + capset + filter)`
- `BYPASS (⚠️ bỏ qua ML filter + capset + personalization)`
- `Hủy`

**Nếu chọn BYPASS → cảnh báo confirm bổ sung:**
```
⚠️ CẢNH BÁO — Priority BYPASS

N campaigns sẽ đi lệnh với BYPASS:
  • Bỏ qua ML filter (capset theo user disable)
  • Bỏ qua personalization targeting
  • Gửi toàn segment bất kể user đã nhận noti hôm nay
  • Rủi ro spam + opt-out spike

BYPASS chỉ dành cho Platform role case khẩn cấp (sự cố, critical announcement).

Bạn có chắc?
```
Options: `Có, tôi chịu trách nhiệm` / `Không, quay lại NORMAL` / `Hủy`

**Sub-step 3 — Confirm đi lệnh:**
`Đi lệnh tất cả` / `Đi lệnh từng cái (confirm mỗi campaign)` / `Hủy`

**Nếu N > 10:** force chunk 10 cái/lần để tránh rubber-stamp.

### 4.2b NOT_QUALIFIED

List campaigns + lý do → 
Options:
- `Reject tất cả N campaigns`
- `Không, tôi muốn approve một vài cái (chỉ ra campaign nào)` — approve ngược AI verdict khi user cho rằng AI false positive
- `Hủy`

Nếu user chọn approve ngược → gõ justification và vẫn qua priority confirm như 4.2a. Log `verdict_override=true` trong structured log.

### 4.2c HITL_REQUIRED

```
🟠 K campaigns cần team khác xử lý:
- #2 Tết 2027 — BMC xác nhận thematic
- #4 Survey CX — CIO
- #5 Giao dịch lỗi — PCS sửa title dài

Skill KHÔNG approve mặc định các case này. Chọn:
```
Options:
- `Assign offline cho team gợi ý (tôi tự liên hệ)`
- `Tôi chính là team đó — approve một số campaign`
- `Skip`
- `Hủy`

**Nếu chọn approve:** user phải gõ explicit xác nhận theo pattern `"Tôi là {team} và xác nhận approve {campaign}"`. Log `HITL_OVERRIDE_APPROVED` với `override_justification`. Vẫn qua priority confirm như 4.2a.

### 4.2d WARNING

Options: `Approve với note từng cái` / `Reject tất cả` / `Assign team khác` / `Skip`.
Nếu approve → vẫn qua priority confirm sub-step 2 như 4.2a.

---

## Phase 5 — Đi lệnh (Execute)

### ⛔ Fire gate verification — BẮT BUỘC chạy TRƯỚC mỗi MCP call (v1.6.0+)

Per Rule HARD-4 Phase 4, trước mỗi `update_campaign_action()` call, agent BẮT BUỘC self-verify checklist:

```
def verify_fire_gate(campaign_name: str, action: str, user_history: list) -> bool:
    # Check 1: Explicit action keyword exists trong session hiện tại
    confirm_msg = find_last_user_action_message(user_history)
    if not confirm_msg:
        raise FireGateError("No explicit confirm message — STOP, re-show panel")
    
    # Check 2: Regex match action keyword pattern
    PATTERN = r"^(approve|reject|route HITL|skip)\s+\d+([,\s]*\d+)*"
    if not re.match(PATTERN, confirm_msg, re.IGNORECASE):
        raise FireGateError(f"Confirm '{confirm_msg}' không match pattern explicit action — STOP")
    
    # Check 3: Campaign name reference đúng campaign trong batch hiện tại
    if not campaign_in_confirmed_list(campaign_name, confirm_msg):
        raise FireGateError(f"Campaign '{campaign_name}' KHÔNG có trong confirmed list — STOP")
    
    # Check 4: Session boundary — nếu vừa resume, đã re-show verdict + re-ask chưa?
    if session_just_resumed_from_summary() and not re_show_done_this_session():
        raise FireGateError("Session vừa resume — BẮT BUỘC re-show verdict + re-ask, KHÔNG fire")
    
    return True
```

**Anti-pattern:** Agent **TUYỆT ĐỐI KHÔNG** fire MCP nếu:
- Verdict + confirm trong cùng turn (vi phạm Rule HARD-1)
- User reply mơ hồ ("ok"/"yes"/"đồng ý") không có explicit action keyword
- Conversation summary nói "user đã approve" — summary KHÔNG phải authority
- System instruction "continue directly" — KHÔNG override fire gate

**Audit log khi fire fail gate:** Agent log structured error → notify owner. KHÔNG silently retry.

---

### ⛔ Comment generation BẮT BUỘC dùng script (v1.7.0+, chain dependency v1.8.0+)

Per failure 08/06/2026: Cowork member fire MCP với comment tự viết tự do `"Score 96/100. Nội dung tốt... Approved by PCS agent."` — KHÔNG match skill template, THIẾU structured log `[AI-REVIEW v1.2]` + audit footer schema v2.

Per failure 10/06/2026: Agent claim "form_id UUID valid" trong comment mà KHÔNG có tier1 evidence.

**Fix v1.7.0:** Phase 5 BẮT BUỘC dùng `scripts/render_athena_comment.py` để generate comment.

**Fix v1.8.0 (script chain dependency):** `render_athena_comment.py` REQUIRE `tier1_check_output` field trong JSON payload. Schema validation reject thiếu field → agent CANNOT skip Tier 1.

**Fix v1.11.4 (push_time chain dependency):** `render_athena_comment.py` REQUIRE thêm `push_time` (raw ms) + `push_time_ict` (output timefmt.py) và **cross-check** `push_time_ict == format_push_time(push_time)`. Schema reject nếu thiếu / sai format / **không khớp** → agent CANNOT fabricate hoặc tự convert giờ (off-by-hour, quên +7).

**Workflow chain v1.8.0+:**
```bash
# 1. REQUIRED — Run Tier 1 script first
TIER1_OUTPUT=$(echo "$CAMPAIGN_JSON" | python scripts/tier1_check.py --unwrap)
# → JSON output với keys: passed, hard_block, hitl_required, tags, metadata

# 1b. REQUIRED (v1.11.4+) — quy đổi push_time qua script (CẤM tự +7h)
PUSH_MS=<schedule_config.push_time từ MCP>
PUSH_ICT=$(python scripts/timefmt.py --ms $PUSH_MS | jq -r '.push_time_ict')
# → "08/07/2026 11:55" (giờ ICT chuẩn)

# 2. Build JSON payload với verdict + tier1_check_output + push_time (MANDATORY)
PAYLOAD=$(jq -n --argjson tier1 "$TIER1_OUTPUT" --arg ict "$PUSH_ICT" --argjson ms $PUSH_MS '{
  "approver_email": "huong.vu4@mservice.com.vn",
  "approver_role": "PCS",
  "action": "APPROVED",
  "campaign_name": "<name>",
  "ai_verdict": "HITL_REQUIRED",
  "ai_agreement": "yes",
  "score_t1": ($tier1.metadata.title_len),
  "score_t2": 96,
  "reasoning_vn": "<1-2 câu key context — quote specific evidence từ $tier1>",
  "reviewer_team": "PCS",
  "review_note": "PCS team review offline OK",
  "priority": "NORMAL",
  "push_time": $ms,
  "push_time_ict": $ict,
  "tier1_check_output": $tier1
}')

# 3. Render canonical comment via script (REJECT nếu thiếu tier1_check_output / push_time_ict sai)
COMMENT=$(echo "$PAYLOAD" | python scripts/render_athena_comment.py)
# Exit 1 nếu schema validation FAIL → STOP, fix payload, không fire MCP

# 4. Pass comment vào MCP call
call_mcp("update_campaign_action",
    name="<name>",
    action="APPROVED",
    priority="NORMAL",
    comment=$COMMENT
)
```

**Effect:**
- Agent **CANNOT** generate comment without running Tier 1 first (technical block)
- Agent **CANNOT** generate comment với push_time tự convert bằng đầu — `push_time_ict` phải khớp output `timefmt.py` (v1.11.4, cross-check)
- Agent **CANNOT** fire MCP without valid comment from render script
- Chain: `tier1_check.py` + `timefmt.py` → `render_athena_comment.py` → `update_campaign_action()` (technical enforcement, KHÔNG còn spec-only mandate)

**Anti-pattern TUYỆT ĐỐI cấm:**
- ❌ Agent tự viết comment string free-form (vd "Score X/100. Nội dung tốt...")
- ❌ Skip structured log `[AI-REVIEW v1.2]` block
- ❌ Skip audit footer schema v2 (`—— [ai_verdict=...] [ai_agreement=...] ...`)
- ❌ Sai format header (vd "Approved by PCS agent" thay vì "Approve by {user} ({role})")

Script enforce 100% template compliance. **v1.12.2:** script LUÔN exit 0 (sandbox coi exit≠0 = fail + vứt stdout) — **phân biệt qua stdout, KHÔNG dùng `$?`**: output bắt đầu bằng `ERROR:` = schema validation fail → STOP, build lại JSON payload; ngược lại = comment hợp lệ (dùng nguyên cho `update_campaign_action`).

---

Pre-flight mỗi lệnh (sau fire gate pass + comment render): verify verdict + priority + comment.

**Tool duy nhất** dùng cho cả approve và reject: `mcp__noti-mcp__update_campaign_action`. Atomic 1-call (Option A): `APPROVED` đi kèm `priority` cùng 1 request, không tách bước.

```python
ACTION_TOOL = "mcp__noti-mcp__update_campaign_action"

# ──────── APPROVE batch ────────
for campaign in approve_list:
    comment = (
        f"{campaign.human_reasoning}\n"
        f"---\n"
        f"[AI-REVIEW v1.2] ai_verdict=QUALIFIED | athena_action=APPROVE | "
        f"score={campaign.score} | top_dims={','.join(campaign.top_dims)} | "
        f"priority={user_confirmed_priority} | ts={iso_now()}"
    )

    result = call_mcp(ACTION_TOOL,
        name=campaign.name,                 # campaign name (không phải numeric id)
        action="APPROVED",                  # enum
        priority=user_confirmed_priority,   # NORMAL | BYPASS — required khi APPROVED
        comment=comment                     # field `comment`
    )
    # KHÔNG stop batch nếu fail — continue

# ──────── REJECT batch ────────
for campaign in reject_list:
    comment = (
        f"{campaign.human_reasoning}\n"
        f"---\n"
        f"[AI-REVIEW v1.2] ai_verdict=NOT_QUALIFIED | athena_action=REJECT | "
        f"score={campaign.score} | reason={','.join(campaign.fail_reasons)} | ts={iso_now()}"
    )

    result = call_mcp(ACTION_TOOL,
        name=campaign.name,
        action="REJECTED",
        # KHÔNG truyền priority khi action=REJECTED
        comment=comment
    )
```

**Schema reference (từ MCP server, đã verify):**
- `name: string (required)` — campaign name (string, không phải UUID/int)
- `action: string (required)` — `APPROVED | REJECTED | IN_REVIEW | EDIT_APPROVAL | STOPPED | UNBLOCK`
- `priority: BYPASS | NORMAL (default null)` — required khi `action=APPROVED`
- `comment: string (default empty)` — text comment

**Lỗi điển hình cần catch (handle nhưng không stop batch):**
- `C001: Thao tác không hợp lệ` — campaign đã ở terminal state (EXPIRED/COMPLETED/STOPPED/REJECTED) → log lỗi, continue
- `403 permission denied` — token không có quyền → stop batch, báo user liên hệ Platform Admin
- Network timeout → retry 1 lần, sau đó skip campaign + log

**Progress indicator:** batch > 5 → show mỗi 3 campaign "Đã xử lý 3/12, OK 3, lỗi 0".

### Message field Athena = 2 phần ngăn bởi `---` (+ audit footer v1.4.9+, expanded v1.5.2+)

```
{Human reasoning — tiếng Việt tự nhiên, dễ hiểu cho new approver}
---
[AI-REVIEW v1.2] {structured key=value codes cho machine parsing/grep audit}
—— [ai_verdict=<V>] [ai_agreement=yes|no] [offline_review=yes|no] [review_note=<text>] [reviewer_team=<team>] [disagree_reason=<text nếu no>]
```

**Char budget Athena comment field: 1000 chars. Target ≤ 800 chars** để tránh bị cut (Athena truncate hoặc UI display limit).

### Audit footer pattern v2 (v1.5.2+) — AI Agreement Tracking expanded

> **Scope:** Cowork users only — KHÔNG áp dụng cho approver Athena UI direct.
>
> **Mục đích:** DA team aggregate bi-weekly để eval disagree rate cho automation phase tiếp theo.

**Footer line schema v2:**

```
—— [ai_verdict=<V>] [ai_agreement=yes|no] [offline_review=yes|no] [review_note=<text>] [reviewer_team=<team>] [disagree_reason=<text>]
```

**Field reference:**

| Field | Required when | Note |
|---|---|---|
| `ai_verdict` | Always | `QUALIFIED \| WARNING \| HITL_REQUIRED \| NOT_QUALIFIED` |
| `ai_agreement` | Always | `yes` (intent respected) hoặc `no` (genuine override) |
| `offline_review` | Optional — chỉ khi action ≠ AI suggest | `yes` (reviewed offline) hoặc `no` |
| `review_note` | **MANDATORY khi `offline_review=yes`** | Brief context (vd "PCS reviewed", "BMC offline OK") |
| `reviewer_team` | Optional — recommend khi action ≠ AI suggest | `PCS / BMC / CIO / Growth / PLATFORM_OPERATOR` |
| `disagree_reason` | **MANDATORY khi `ai_agreement=no`** | Natural VN, OMIT khi `=yes` |

**Logic compute `ai_agreement`:**

```python
if action == AI_suggested_action:
    ai_agreement = "yes"   # straightforward match
elif action != AI_suggested_action and offline_review == "yes":
    ai_agreement = "yes"   # intent respected via offline route
    # require review_note + recommend reviewer_team
elif action != AI_suggested_action and offline_review == "no":
    ai_agreement = "no"    # genuine override
    # require disagree_reason
```

**Example 1 — Auto-approve QUALIFIED:**
```
Approve by huong.vu4 (Platform Operator). Score 100/100. Campaign đủ điều kiện duyệt.
—— [ai_verdict=QUALIFIED] [ai_agreement=yes]
```

**Example 2 — HITL → PCS, PCS approver reviews + approves (intent respected):**
```
Approve by huong.vu4 (PCS). REMIND security warning segment 82K, push 18:35. Campaign đủ điều kiện duyệt.
—— [ai_verdict=HITL_REQUIRED] [ai_agreement=yes] [reviewer_team=PCS] [review_note=PCS team review offline confirm security messaging OK]
```

**Example 3 — HITL → BMC, cross-team approver với offline coordination:**
```
Approve by huong.vu4 (Platform Operator). Promo biometric auth segment 1.43M, push 17:00. Campaign đủ điều kiện duyệt.
—— [ai_verdict=HITL_REQUIRED] [ai_agreement=yes] [offline_review=yes] [review_note=BMC offline đã review qua Slack] [reviewer_team=PLATFORM_OPERATOR]
```

**Example 4 — HITL → BMC, genuine override (no review):**
```
Approve by huong.vu4 (Platform Operator). Push time-sensitive sát giờ, fire dưới authority Platform Operator. Campaign đủ điều kiện duyệt.
—— [ai_verdict=HITL_REQUIRED] [ai_agreement=no] [offline_review=no] [reviewer_team=PLATFORM_OPERATOR] [disagree_reason=Push còn 10 phút, không reach được BMC, exercise Platform Operator authority]
```

**Example 5 — WARNING + approve with offline review:**
```
Approve by huong.vu4 (BMC). WARNING image advisory — đã check ảnh thủ công OK. Campaign đủ điều kiện duyệt.
—— [ai_verdict=WARNING] [ai_agreement=yes] [offline_review=yes] [review_note=Image rendered OK trên test device]
```

**DA extract pattern (regex v2):**
- `\[ai_verdict=([^\]]+)\]`
- `\[ai_agreement=(yes|no)\]`
- `\[offline_review=(yes|no)\]?` (optional)
- `\[review_note=([^\]]*)\]?`
- `\[reviewer_team=([^\]]+)\]?`
- `\[disagree_reason=([^\]]*)\]?`

**Backward compat:** Audit footer v1 (v1.4.9 schema chỉ 3 fields) vẫn parse được — DA team treat missing fields as null. Footer v2 expand thêm 3 fields optional.

Apply theo schema `athena.action_logs.comment` field.

### Phần 1 — Human reasoning (tiếng Việt tự nhiên)

> **Đối tượng đọc:** approver tự đọc lại, new approver onboard, audit người (Legal/compliance), Growth team follow-up.
>
> **Nguyên tắc viết:**
> - Bắt đầu với hành động + approver: `"Approve by {user} ({role}). ..."` / `"Reject by {user} ({role}). ..."` — bắt buộc attribution để audit trace
> - Format thống nhất English action + Vietnamese body: `Approve by huong.vu4 (Platform Operator). {Lý do tiếng Việt}`
> - 1-2 câu lý do, **tiếng Việt thường ngày, không từ kỹ thuật**
> - Mention team coordination nếu có: VD "đã được BMC và Security xác nhận"
> - Số liệu cụ thể OK: "Segment 1.57M", "Title 44 ký tự", "Score 100/100"
> - **TUYỆT ĐỐI KHÔNG dùng:** "HITL", "override", "Reg-floor", "trigger", "Tier A/B/C", "aligned" — đó là từ kỹ thuật chỉ dành cho structured log
> - **TUYỆT ĐỐI KHÔNG mention** số rule (R5.1, DIM-3.7, Rule 4.9) — đó là codes cho structured log

**Template skeletons theo verdict** (concrete VD examples xem `08-batch-review-template_v1.9.md` §Phase 5 message examples):

**Nguyên tắc (v1.3.0+):**
- **APPROVE**: ngắn gọn — `Approve by {user} ({role}). {1 câu key context}. Campaign đủ điều kiện duyệt.` Key context = mention CT/team/partner/score, KHÔNG enumerate segment size/push time/time-sensitive/...
- **REJECT**: giữ detail lỗi cụ thể (số ký tự, typo, wording sai...) để Owner biết sửa.

| Verdict | Skeleton | Override flag |
|---|---|---|
| **QUALIFIED auto-APPROVE** | `Approve by {user} ({role}). Score {N}/100. Campaign đủ điều kiện duyệt.` | omit |
| **HITL → APPROVE (same team)** | `Approve by {user} ({approver's HITL team}). {Key context = CT/group/scope}. Campaign đủ điều kiện duyệt.` | **omit** (HITL outcome) |
| **HITL → APPROVE (cross-team)** | `Approve by {user} ({role}). Đã align {HITL team} offline. Campaign đủ điều kiện duyệt.` | `override=true \| just=cross_team_align_offline` hoặc `just=platform_authority` |
| **HITL → APPROVE Vietlott** | `Approve by {user} ({role}). Vietlott đối tác chính thức. Campaign đủ điều kiện duyệt.` | per role |
| **HITL → APPROVE SURVEY (CIO)** | `Approve by {user} (CIO). Survey {project_name_ngắn}. Campaign đủ điều kiện duyệt.` | omit |
| **REJECT — Tier 1 content fail** | `Reject by {user} ({role}). {Lý do specific với detail con số/wording sai}. Owner sửa và resubmit.` | n/a |
| **REJECT — cleanup test/stale** | `Reject by {user} ({role}) để clean up. Nội dung test ('{gibberish}'), push_time quá hạn từ {date}.` | n/a |
| **REJECT — hard block PII** | `Reject by {user} ({role}). Body có {PII type} — vi phạm chính sách bảo mật.` | n/a |

### Phần 2 — Structured log (key=value codes cho audit/parsing)

> **Đối tượng:** machine parsing (grep audit, dashboard query), Legal/compliance export, regression analytics. Technical OK nhưng **không dùng số rule** (R{X.Y}, DIM-{X.Y}, Rule {X.Y}) vì approver/auditor không nhớ được số rule. Dùng **plain descriptive tags** thay thế.

**Nguyên tắc cho field `trg` (v1.2.3+):**
- ❌ **KHÔNG dùng:** `R5.1_seg1.57M`, `DIM-3.7_biometric`, `Rule_6.5_survey_routing`
- ✅ **DÙNG plain tags:** `big_segment`, `sensitive_action`, `survey_cio_routing`
- ✅ **Chỉ ghi triggers thực sự shape verdict** — không liệt kê rules pass/không apply. QUALIFIED clean → omit `trg` field.
- ✅ Tag format: `snake_case`, 1-4 từ, descriptive nhưng ngắn

**Nguyên tắc cho field `override` (v1.2.7+ — role-aware):**

`override=true` **CHỈ khi** approver thuộc team **khác** với team AI gợi ý cho HITL.

| Approver team | AI suggested team | Action=APPROVE | `override` flag |
|---|---|---|---|
| PCS | PCS (Quan trọng) | HITL outcome hoàn tất | ❌ KHÔNG ghi |
| BMC | BMC (Ưu đãi/Tương tác) | HITL outcome hoàn tất | ❌ KHÔNG ghi |
| CIO | CIO (SURVEY) | HITL outcome hoàn tất | ❌ KHÔNG ghi |
| PLATFORM_OPERATOR | bất kỳ | Cross-team authority | ⚠️ `override=true` + `just=platform_authority` |
| PCS | BMC | Approver review ngoài domain | ⚠️ `override=true` + `just=cross_team_align_offline` |
| Bất kỳ | NOT_QUALIFIED → APPROVE | Approver bỏ qua reject | ⚠️ `verdict_override=true` + justification |

**Logic check (Phase 5 Pre-execute):**
1. Lookup `approver.account_id` trong `role-mapping.json` → lấy list teams approver thuộc về (PCS / BMC / CIO / PLATFORM_OPERATOR)
2. Nếu `suggested_team` ∈ approver teams → action=APPROVE là HITL outcome chính thức → **omit `override` field**
3. Nếu approver = PLATFORM_OPERATOR (cross-team) → vẫn ghi `override=true` với `just=platform_authority` vì authority đến từ platform role, không từ HITL team membership
4. Nếu approver team ≠ suggested_team → ghi `override=true` + justification cụ thể (vd `just=cross_team_align_offline`)

**Field naming convention (short for char budget):**

| Long form | Short form | Save |
|---|---|---|
| `ai_verdict` | `verdict` | 3 |
| `athena_action` | `action` | 7 |
| `trigger` / `triggers` | `trg` | 5 |
| `override_justification` | `just` (drop quotes nếu safe) | 18 |
| `suggested_team` | `team` | 10 |
| ISO timestamp `2026-05-15T14:29:16+07:00` | `2026-05-15T14:29+07` | 6 |

**Common tag dictionary (reuse cho consistency):**

| Tag | Ý nghĩa | Triggered by |
|---|---|---|
| `big_segment` | Segment vượt cap | > 5M (general → dual review Growth+PCS/BMC) hoặc > 250K (SURVEY) |
| `sensitive_action` | User action nhạy cảm | Biometric / OTP / password / external link |
| `absolute_claim` | Claim tuyệt đối | "100%", "tốt nhất", "duy nhất", "đảm bảo" |
| `vague_claim` | Cụm mơ hồ không số | "hấp dẫn", "lớn", "khủng" |
| `vietlott_legal_review` | Content Vietlott/xổ số cần legal | DIM-4.4 + 4.5 combined |
| `fs_product_wording` | Vi phạm wording 4 FS products | TTT/Vay Nhanh+Newton/VTS |
| `ct_mismatch` | Content_type không khớp nội dung | Rule 1.6 |
| `event_thematic_required` | EVENT cần xác nhận thematic | Rule 1.7 |
| `survey_cio_routing` | SURVEY routing CIO bắt buộc | Rule 6.5 (often implicit từ `team=CIO`) |
| `quan_trong_pcs_routing` | Quan trọng → PCS | Rule 6.3 |
| `push_cap_exceeded` | Vượt 500K/day/project | Rule 6.5 push cap |
| `title_too_long` / `body_too_long` | Vượt ký tự limit | Rule 2.1 / 2.2 |
| `typo_in_body` / `typo_in_title` | Lỗi chính tả | DIM-3.4b |
| `pii_detected` | PII trong content | Rule 2.4 (phone/email/CCCD) |
| `test_content` | Nội dung test/dummy | Rule 2.8 |
| `duplicate_segment` | Trùng nội dung + segment 7d | Rule 2.9 case 1 |
| `no_cta` | Thiếu CTA explicit | DIM-3.10 |
| `cashback_no_conditions` | Cashback không có điều kiện | DIM-4.8 |
| `airfare_no_disclaimer` | Vé bay thiếu disclaimer | DIM-4.6 |
| `insurance_vague_scope` | Bảo hiểm vague phạm vi | DIM-4.7 |
| `discrimination_language` | Ngôn ngữ kỳ thị | DIM-4.2 |
| `non_vietnamese` | Toàn tiếng nước ngoài | DIM-4.3 |
| `refid_not_in_whitelist` | RefID không thuộc MoMo screen whitelist | Rule 1.8 (cần approver re-confirm) |
| `refid_content_mismatch` | RefID landing không khớp chủ đề noti | Rule 1.6 axis 2 (BMC #3.0) |
| `emoji_at_start` | Emoji đứng đầu Title hoặc Body | Rule 3.5 sub-check 3 (BMC #20.0) |
| `emoji_unicode_modern` | Emoji Unicode 14+ render risk device cũ | Rule 3.5b (BMC #20.0) |
| `banned_phrase_blocker` / `banned_phrase_critical` / `banned_phrase_warning` | Phrase thuộc Legal/Compliance blacklist | Rule 2.11 (BMC #23.0) |
| `bu_daily_cap_warning` (4-9) / `bu_daily_cap_exceeded` (≥10) | BU vượt cap campaign/day | Rule 5.2 (BMC #16.0) |

**Templates theo verdict (no rule codes):**

```
QUALIFIED auto-approve (clean — omit trg field):
  [AI-REVIEW v1.2] verdict=QUALIFIED | action=APPROVE | score=100 | priority=NORMAL | ts=2026-05-15T14:29+07

WARNING approve (advisory):
  [AI-REVIEW v1.2] verdict=WARNING | action=APPROVE | score=68 | trg=vague_claim,no_cta | priority=NORMAL | ts=...

HITL assigned (no action yet, route to team):
  [AI-REVIEW v1.2] verdict=HITL_REQUIRED | action=NONE | score=85 | trg=big_segment | team=CIO | ts=...

HITL override approve (compliance/legal aligned):
  [AI-REVIEW v1.2] verdict=HITL_REQUIRED | action=APPROVE | score=75 | override=true | trg=big_segment,sensitive_action,absolute_claim | priority=NORMAL | team=BMC | ts=...

HITL approve SURVEY (CIO routing):
  [AI-REVIEW v1.2] verdict=HITL_REQUIRED | action=APPROVE | score=95 | override=true | priority=NORMAL | team=CIO | ts=...
  (team=CIO đã imply survey_cio_routing — không cần lặp trg)

HITL approve Vietlott:
  [AI-REVIEW v1.2] verdict=HITL_REQUIRED | action=APPROVE | score=95 | override=true | trg=vietlott_legal_review | priority=NORMAL | team=BMC | ts=...

NOT_QUALIFIED reject (Tier 1/2 fail):
  [AI-REVIEW v1.2] verdict=NOT_QUALIFIED | action=REJECT | score=32 | trg=title_too_long,typo_in_body | ts=...

NOT_QUALIFIED override approve (AI false positive):
  [AI-REVIEW v1.2] verdict=NOT_QUALIFIED | action=APPROVE | verdict_override=true | just=AI_false_positive | priority=NORMAL | ts=...

Hard block reject (PII):
  [AI-REVIEW v1.2] verdict=NOT_QUALIFIED | action=REJECT | trg=pii_detected | ts=...

Cleanup reject (stale/expired):
  [AI-REVIEW v1.2] verdict=NOT_QUALIFIED | action=REJECT | trg=test_content,stale_18mo | ts=...
```

### Char count examples (verify against 800 target — sau v1.2.3 plain tags)

| Scenario | Human part | Struct log | Total |
|---|---|---|---|
| QUALIFIED auto (no trg) | ~110 chars | ~95 chars | ~205 ✓ |
| HITL override compliance (3 trg tags) | ~250 chars | ~210 chars | ~460 ✓ |
| HITL approve SURVEY (no trg, team=CIO implies) | ~180 chars | ~140 chars | ~320 ✓ |
| HITL approve Vietlott | ~190 chars | ~165 chars | ~355 ✓ |
| REJECT Tier 1 (2 trg tags) | ~150 chars | ~115 chars | ~265 ✓ |
| Hard block PII | ~120 chars | ~80 chars | ~200 ✓ |

→ Tất cả templates **well under 800 chars**, không bị Athena cut. Plain tags chỉ tiết kiệm ~10 chars nhưng đổi lại **dễ đọc gấp nhiều lần** cho approver/auditor.

---

## Phase 6 — Final Report

```markdown
## ✅ Done duyệt batch

**Approved (Athena state = APPROVED):** 5/5 (priority NORMAL)
- #1, #7, #11 — QUALIFIED → approved
- #6, #9 — WARNING → approved với note

**Rejected (Athena state = REJECTED):** 2/2
- #3, #8 — NOT_QUALIFIED → rejected

**Assigned team khác (HITL_REQUIRED):** 4 — BMC(2), CIO(1), PCS(1)
**Skipped:** 0
**Failures:** 1 — #15 error 403 Athena state changed. Retry manual.

**Audit:** grep `[AI-REVIEW v1.2]` trong Athena message log để trace.
```

---

## Edge cases

1. **User "approve all" mixed verdict:** từ chối, bắt chọn theo group.
2. **User yêu cầu skip confirm panel:** từ chối. Principle #3 luôn confirm.
3. **Danh sách IN_REVIEW trống:** báo rõ "Không có campaign nào chờ duyệt."
4. **Multiple exceptions (Quan trọng + format):** check tier D theo thứ tự, match đầu là dừng.
5. **LLM score conflict hard block:** hard block thắng (VD: score 90 nhưng có PII → NOT_QUALIFIED).
6. **Campaign priority=BYPASS từ input:** review bình thường, confirm lại priority khi đi lệnh.
7. **HITL override approve:** yêu cầu explicit text confirm + justification.
8. **NOT_QUALIFIED user muốn approve ngược:** cho phép với justification, log `verdict_override=true`.
9. **Lệnh MCP fail:** không stop batch, log lỗi, report cuối.

---

## Changelog

Version history: xem `CHANGELOG.md` root folder, section **Skill**.

