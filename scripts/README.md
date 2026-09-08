# scripts/ — Tier 1 hard rule checks + utilities

> Pure Python deterministic scripts cho Tier 1 hard rule validation.
> **Source of truth** cho rule enforcement — KHÔNG dùng LLM cho hard rules.

---

## Layout

> **Layout phẳng (v1.12.0+):** theo agentskills spec chỉ còn 3 cấp `assets/` · `scripts/` · `references/`.
> Package `lib/` cũ đã dồn thẳng vào `scripts/` — CLI entry + module dùng chung nằm cùng cấp, import trực tiếp (`from rules import ...`).

```
scripts/
│   # CLI entry (chạy qua `python scripts/<file>` hoặc skill_script gọi theo tên):
├── tier1_check.py            ← MAIN CLI entry — Tier 1 hard rule check (single + --batch v1.5.0+)
├── char_count.py             ← CLI đếm ký tự title/body (placeholder ${...} = 0)
├── timefmt.py                ← CLI quy đổi push_time epoch-ms (UTC) → giờ ICT (GMT+7)
├── render_batch_report.py    ← Phase 3 canonical markdown render (v1.5.1+)
├── render_athena_comment.py  ← Phase 5 canonical Athena comment render (v1.7.0+)
├── README.md                 ← this file
│   # module dùng chung (import bởi các CLI trên):
├── constants.py              ← Single source: thresholds, valid sets, CT mapping
├── pii.py                    ← PII regex (phone/email/CCCD/bank)
├── rules.py                  ← Per-rule check functions (1.1, 2.x, 5.1, 6.5, Tier D)
├── banned_phrases.py         ← Rule 2.11 scan (assets/banned-phrases.json)
├── brand.py                  ← Rule 2.14 brand integrity (assets/brand-dictionary.json)
├── refid_glossary.py         ← Rule 1.8 lookup (assets/refid-glossary.tsv)
├── detect_domain.py          ← Keyword detection → list domain guardrails cần load
├── segment_audit.py          ← Rule 5.3/5.5 segment condition audit + scorecard
└── rule_descriptions.py      ← Central VN translation (Principle #8 — no rule code user-facing)
```

---

## `render_batch_report.py` — Phase 3 canonical render (v1.5.1+)

**Purpose:** Eliminate LLM compliance variance trên Cowork distributed members. Agent đôi khi skip markdown link wrap hoặc render bulleted list thay vì table — script enforce 100% format compliance.

**Pattern:**
```
LLM Tier 2 Judge  →  verdict + score + reason_vn  (creative judgment)
       ↓
       Build JSON state                           (agent build input)
       ↓
render_batch_report.py  →  canonical markdown    (deterministic render)
```

**Usage:**
```bash
# Stdin pipe (build JSON state from verdict results)
echo '{"env":"prod","campaigns":[...]}' | python scripts/render_batch_report.py

# Inline JSON
python scripts/render_batch_report.py --json '{"env":"prod","campaigns":[...]}'

# File
python scripts/render_batch_report.py --file batch.json
```

**Input JSON schema:** See script docstring. Required per campaign: `name`, `alias`, `content_type`, `title`, `body`, `t1_score`, `t2_score`, `verdict`, `reason_vn`, `action`. Optional: `image_url`.

**Output:** 11-column markdown table với:
- Header block (snapshot + reviewer + env + ngưỡng legend)
- Mọi Campaign cell wrapped `[`<alias>`](<env_url>/notification-v2/list-view?name=<full_name>)`
- Score color-coded (🟢🟡🟠🔴)
- Verdict icon (🟢🟡🟣🔴⛔)
- Image cell `—` hoặc `[filename](url) ⚠️`
- Footer disclaimer + render attribution

**Env-aware URL:** `env="prod"` → `https://athena.mservice.io` · `env="uat"` → `https://athena-uat.mservice.io`

---

## `render_athena_comment.py` — Phase 5 canonical Athena comment render (v1.7.0+)

**Purpose:** Eliminate LLM free-form comment variance trên Cowork distributed members. Phase 5 message field Athena cần đúng template (Human reasoning + structured log + audit footer schema v2) — script enforce 100% format compliance.

**Pattern:**
```
LLM Tier 2 Judge   →  verdict + score + reason_vn   (creative)
Phase 4 confirm    →  approver decision (action keyword)
        ↓
        Build JSON state                            (agent build input)
        ↓
render_athena_comment.py  →  canonical comment      (deterministic)
        ↓
MCP update_campaign_action(comment=<output>)
```

**Usage:**
```bash
# Inline JSON
python scripts/render_athena_comment.py --json '{"approver_email":"huong.vu4@mservice.com.vn",...}'

# File
python scripts/render_athena_comment.py --file payload.json

# Stdin
cat payload.json | python scripts/render_athena_comment.py
```

**Input JSON schema:** See script docstring. Required: `approver_email`, `approver_role`, `action`, `campaign_name`, `ai_verdict`, `ai_agreement`, `reasoning_vn`. Conditional: `disagree_reason` (when ai_agreement=no), `review_note` (when offline_review=yes), `priority` (when action=APPROVED).

**Output 3-part canonical comment:**
1. Human reasoning natural VN: `"Approve by {user} ({role}). {reasoning}. Campaign đủ điều kiện duyệt."`
2. Structured log: `[AI-REVIEW v1.2] ai_verdict=... | action=... | score=... | priority=... | ts=...`
3. Audit footer schema v2: `—— [ai_verdict=V] [ai_agreement=yes|no] [offline_review=...] [review_note=...] [reviewer_team=...] [disagree_reason=...]`

**Schema validation:**
- Required fields missing → exit 1 + stderr error
- Enum invalid → exit 1
- Conditional mandate violation (vd ai_agreement=no thiếu disagree_reason) → exit 1
- Action=APPROVED thiếu priority → exit 1

**Anti-pattern prevented:**
- ❌ LLM tự viết comment "Score 96/100. Nội dung tốt..." — NO structured log + NO audit footer
- ❌ Comment chỉ có "Approved by PCS agent." — KHÔNG user attribution, KHÔNG context
- ❌ Format khác giữa Cowork members khi distribute skill

→ Script enforce 100% template compliance, không variance.

---

## Script table — 6 nhóm rule checks (mirror create-flow format)

### Nhóm 1 — Content hard checks (5 rules)

| Function | Rule | Khi nào chạy | Vì sao script (không LLM) |
|---|---|---|---|
| `rule_2_1_title_length` | 2.1 — Title ≤ 30 chars | Phase 2 mọi campaign | `len(title) > 30` — pure int compare. LLM hallucinate limit (vd Title ≤ 65 bug trong session TT77) |
| `rule_2_2_body_length` | 2.2 — Body ≤ 120 chars | Phase 2 mọi campaign | Same — int compare. Hard rule binary |
| `rule_2_3_no_newline` | 2.3 — Body không xuống dòng/bullet | Phase 2 mọi campaign | Regex `[\n\r]` + bullet pattern. LLM "thấy đẹp" không catch được \n thật |
| `rule_2_6_param_whitelist` | 2.6 — Chỉ `${fullname}`, `${lastname}` | Phase 2 mọi campaign | Set membership exact case-sensitive. LLM dễ accept variant (Fullname / first_name) sai |
| `rule_2_8_test_content` | 2.8 — Block test/gibberish | Phase 2 mọi campaign | Keyword list + Shannon entropy threshold 1.5. LLM "tha" content test nếu nội dung khác có vẻ ok |

**File:** `rules.py`

### Nhóm 2 — Security/PII (1 module, hard block always)

| Function | Rule | Khi nào chạy | Vì sao script |
|---|---|---|---|
| `detect_pii` + `rule_2_4_pii` | 2.4 — PII detection | Phase 2 mọi campaign | Regex phone (VN format 0/84 + 9-10 digits), email, CCCD 12-digit, bank context. PII = LUÔN hard block kể cả Quan trọng. LLM dễ miss masked phone (vd "098-***-321") hoặc "tha" vì context legitimate |

**File:** `pii.py`

### Nhóm 3 — Configuration validation (3 rules)

| Function | Rule | Khi nào chạy | Vì sao script |
|---|---|---|---|
| `rule_1_1_ct_valid` | 1.1 — CT in 14 valid codes | Phase 2 mọi campaign | Set membership. LLM có thể accept typo CT code (vd "TRANSCATION" vs "TRANSACTION") |
| `rule_2_10_format` | 2.10 — out-app only (no in-app/Header/Popup/XBanner/Snackbar) | Phase 2 mọi campaign | Dict lookup `notification_config.allow_in_app`. Boolean check |
| `check_rule_1_8` | 1.8 — RefID glossary lookup | Phase 2 mọi campaign | File lookup `refid-glossary.tsv` (2827 entries). LLM không nhớ được hết list |

**Files:** `rules.py` + `refid_glossary.py`

### Nhóm 4 — Reference scans (1 module, Legal/Compliance maintained)

| Function | Rule | Khi nào chạy | Vì sao script |
|---|---|---|---|
| `check_rule_2_11` | 2.11 — Banned phrases scan | Phase 2 mọi campaign | Load `assets/banned-phrases.json`, substring case-insensitive scan title+body. Legal update file monthly → script auto-sync, không cần redeploy. 3 severity tiers (blocker/critical/warning) |

**File:** `banned_phrases.py`

### Nhóm 5 — Segment/scale (2 rules)

| Function | Rule | Khi nào chạy | Vì sao script |
|---|---|---|---|
| `rule_5_1_segment_size` | 5.1 — Segment cap 5M + dual review trigger | Phase 2 mọi campaign | Int compare + CT→approver lookup. Dual review tag `team={Growth,PCS/BMC}` emit |
| `rule_6_5_survey_validation` | 6.5 — SURVEY 5 hard checks (service enum / ref_id / UUID v4 / segment 250K / push cap noted) | Phase 2 chỉ SURVEY | service_group/service_type enum match, ref_id exact, UUID v4 regex, segment hard cap |

**File:** `rules.py`

### Nhóm 6 — Tier D routing (1 module)

| Function | Rule | Khi nào chạy | Vì sao script |
|---|---|---|---|
| Tier D inline in `check_campaign()` | Quan trọng→PCS / SURVEY→CIO / EVENT→BMC thematic confirm | Phase 2 sau Tier A pass | Dict lookup `CT_TO_APPROVER`. Always HITL_REQUIRED dù score ≥ 85 (per Rule 6.2 exception) |

**File:** `tier1_check.py` (orchestration layer)

### Nhóm 7 — Domain detection (new v1.4.0+)

| Function | Purpose | Khi nào chạy | Vì sao script |
|---|---|---|---|
| `detect_domains` | Keyword scan title/body/CT → return list domain guardrails | Phase 2 trước Tier 2 LLM | Decide guardrail load on-demand: fs-products / vietlott / airfare / insurance / cashback-fintech / survey-cio. Tránh load 70KB monolith mỗi campaign |

**File:** `detect_domain.py`

---

## `tier1_check.py` — primary skill integration

### Quick usage

```bash
# Stdin pipe từ MCP response:
mcp_response_json | python scripts/tier1_check.py --unwrap --pretty

# File:
python scripts/tier1_check.py --file campaign.json --pretty

# Inline JSON:
python scripts/tier1_check.py --json '{"name":"...","variants":{...}}'
```

### Input

Athena `get_campaign_detail` MCP response (full campaign object). Pass `--unwrap` để strip wrapping `{status, data}`.

### Output JSON

```json
{
  "passed": false,
  "hard_block": true,
  "hitl_required": true,
  "issues": [
    {"rule": "2.1", "passed": false, "severity": "error", "message": "Title 55 ký tự > 30..."},
    {"rule": "5.1", "passed": false, "severity": "hitl", "tag": "big_segment", "dual_review_teams": ["Growth", "BMC"], ...}
  ],
  "tags": ["big_segment", "refid_not_in_whitelist", "quan_trong_pcs_routing"],
  "domains_to_load": ["fs-products"],     // ← NEW v1.4.0+ — domain guardrails để LLM Tier 2 load
  "metadata": {
    "campaign_name": "...",
    "title_len": 55,
    "body_len": 46,
    "segment_size": 6500000,
    "content_type": "PROMOTION_SERVICE",
    "group": "Ưu đãi"
  }
}
```

### Exit codes

| Code | Meaning | Skill action |
|---|---|---|
| `0` | Tier 1 pass | Continue Tier 2 LLM judge với domain guardrails từ `domains_to_load` |
| `1` | Hard block (Tier A violation) | Verdict NOT_QUALIFIED, reject required |
| `2` | HITL required (Tier C/D trigger) | Verdict HITL_REQUIRED, route team |
| `99` | Script error (invalid input, etc.) | Log + fall back to manual review |

---

## NOT covered (cần LLM hoặc MCP)

| Rule | Why | Where |
|---|---|---|
| 1.6 CT semantic mismatch | LLM judgment | `07-llm-judge-core_v1.12.md` Tier 2 |
| 3.x Content quality DIMs | LLM judgment | `07-llm-judge-core_v1.12.md` Tier 2 |
| 3.4b Spell check | LLM judgment | Tier 2 |
| 3.5b Emoji Unicode 14+ | LLM identify | Tier 2 |
| 4.1, 4.2, 4.3 (general regulatory) | LLM judgment | Tier 2 |
| 4.4-4.9 (domain regulatory) | LLM judgment | Tier 2 với domain guardrail lazy-loaded |
| 5.2 BU daily cap | Needs MCP `list_campaigns` aggregation | Phase 2 skill orchestration |
| 6.5.5 SURVEY push cap (500K/day/project) | Needs cross-campaign MCP query | Phase 2 skill orchestration |

---

## Skill integration (skill/noti-campaign-approval.md Phase 2)

Trong Phase 2, **agent BẮT BUỘC invoke `tier1_check.py` qua công cụ chạy script của runtime** (`skill_script`/`script` provider gọi theo **tên trần** `tier1_check` — **KHÔNG kèm `.py`** vì provider đăng ký theo stem; HOẶC Bash tool `python scripts/tier1_check.py` — "không có Bash tool" KHÔNG phải lý do bỏ script, thử `skill_script` trước; "unknown script" thường do dính `.py`, bỏ đuôi rồi gọi lại) cho mỗi campaign — KHÔNG được dùng LLM reasoning để check hard rules:

```bash
# Pseudo Phase 2 step 1: Tier 1 script check + domain detect
# v1.12.2: script LUÔN exit 0 — ĐỌC VERDICT TỪ JSON, KHÔNG dựa $? (sandbox coi
# exit≠0 = fail và vứt stdout). skill_script: bọc inputs={"campaign": {...}}.
python scripts/tier1_check.py --json '<campaign_json>' > /tmp/tier1_result.json
verdict=$(jq -r '.verdict' /tmp/tier1_result.json)   # PASS | HITL_REQUIRED | NOT_QUALIFIED | ERROR
# Parse .verdict (KHÔNG dùng $?):
#   PASS           → continue Tier 2 LLM judge với references/{domains_to_load}.md
#   NOT_QUALIFIED  → build reject comment với issues[]
#   HITL_REQUIRED  → use tags[] cho routing
#   ERROR          → log .error, manual fallback
```

→ Xem skill/noti-campaign-approval.md §Phase 2 cho full flow.

---

## Dependencies

```
Python ≥ 3.10 (for type hints `dict[str, str]`, `list[tuple[str, str]]`)
```

Pure stdlib — không cần install package.

---

## Update rule khi guardrail change

1. Edit `constants.py` (thresholds, valid sets) — single source of truth
2. Nếu add rule mới → add function vào `rules.py` + import vào `tier1_check.py` `check_campaign()`
3. Nếu add domain mới → update `detect_domain.py` keyword list + create `references/<name>.md`
4. Bump guardrail version trong file header
5. Cross-check `tier1_check.py` output trên 1 campaign mẫu để verify
