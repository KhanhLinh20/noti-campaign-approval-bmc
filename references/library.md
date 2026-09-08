# Library — Noti Campaign Approval Project

> **Mục đích:** Single source of truth liệt kê TẤT CẢ file trong project kèm version + scope + description ngắn.
>
> **Khi sử dụng:** Mỗi khi cần sửa skill / script / rule / template / data file → agent BẮT BUỘC Read file này TRƯỚC, identify file đúng, reconfirm với user, rồi mới execute edit. Sau khi edit, update version + last updated trong row tương ứng.
>
> **Workflow chi tiết:** Xem `skill/skill-update-process.md`.
>
> **Last updated:** 2026-08-07 · **Library version:** v1.29
>
> **Scope note:** Cột "In zip" chỉ rõ file có nằm trong install zip phân phối không. `local-only` = chỉ owner (huong.vu4) maintain, không distribute.

---

## 1. Skill — Dispatcher & Sub-skills

| Path | Version | Type | In zip | Description | Khi nào touch |
|---|---|---|---|---|---|
| `SKILL.md` | v1.12.4 | Dispatcher | ✅ yes | Entry point Claude reads first. Routes intent → sub-skill (approval / maintenance / packaging). ~145 dòng. v1.11.0 bump cho zip phân phối gồm Rule 2.14/5.3/5.5/5.6 + 3 file mới. **v1.12.1** fix fallback invoke: provider đăng ký script theo **tên trần** (stem, KHÔNG `.py`) — chuẩn hóa mọi chỗ gọi `tier1_check`/`char_count`/`timefmt`, "unknown script" = dính `.py` → bỏ đuôi gọi lại (fix prod failure 08/2026). | Đổi routing logic, thêm sub-skill mới, đổi trigger phrases |
| `skill/noti-campaign-approval.md` | v1.9.2 | Sub-skill (approval) | ✅ yes | Full Phase 0-6 approval flow. **v1.9.0** Phase 2 Segment Condition Audit (Rule 5.3). **v1.9.1** Rule 5.5 staff exclude + Scorecard. **v1.9.2** Rule 5.6 segment hành vi ↔ content_type (BMC 9.0) — inject conditionV2 + dataSource, detect behavioral từ điều kiện (KHÔNG dựa tên segment). v1.6-1.7 HARD rules + render scripts + Rule 2.13. **v1.8.0** Tier 1 evidence mandate + anti-hallucination data citation discipline + script chain dependency (render_athena_comment REQUIRE tier1_check_output) + Rule 6.5.A.3 accept UUID v4 OR v7 — fix prod failure 10/06/2026 (form_id v7 false reject + AI hallucinate position/source). | Đổi phase logic, mandate T1+T2, output behavior, fire gate safety, comment render, rule add, evidence enforcement |
| `skill/skill-update-process.md` | v2.1 | Sub-skill (maintenance) | ❌ **local-only** | Maintenance workflow 6-step. Chỉ owner local maintain skill, approver khác không cần. | Đổi maintenance workflow, anti-patterns, rebuild rules |
| `skill/packaging-install-skill.md` | v1.11.0 | Sub-skill (packaging) | ❌ **local-only** | Workflow đóng gói install zip. Chỉ owner local build zip. **KHÔNG auto-trigger**. Version manual bump match parent SKILL.md. v1.11.0 inclusion +brand.py +segment_audit.py +brand-dictionary.json (42 files). | Đổi inclusion/exclusion list, đổi version sync rule, edit anti-patterns |
| `library.md` | v1.18 | Index | ✅ yes | File này — bảng index tất cả artifacts kèm cột "In zip". | Sau MỌI lần edit file khác (sync version + last updated) |

---

## 2. Guardrails — Core (Always-load, 7 files)

> Load BẮT BUỘC ở Phase 0 (approval flow). Định nghĩa rule logic + Tier mapping + error message.

| Path | Version | Scope | Description | Khi nào touch |
|---|---|---|---|---|
| `references/00-core-rules.md` | v1.16 | Index + Tier structure | File index 13-file split + Tier A/B/C/D definition + System-Enforced table. Phase 0 load đầu tiên. | Add domain file mới, đổi Tier structure |
| `references/01-content-type-format.md` | v1.17 | Nhóm 1 (Rules 1.1-1.8) | Content type validation, format constraint, RefID glossary check. Rule 1.8 URL refid hợp lệ. **Rule 1.6 axis 1 tighten v1.17+** — explicit gift card reminder pattern HITL trigger complement Rule 2.13 Tier 1 catch. | Add/edit Rule 1.x, đổi content_type list, đổi semantic check |
| `references/02-content-hard-checks.md` | v1.19 | Nhóm 2 (Rules 2.1-2.14) | Title/Body length, PII, format violations, banned phrases, image advisory, gift card reminder, brand integrity. **Rule 2.14 NEW v1.19+** — brand integrity: tên "MoMo" phải viết đúng (camelCase), mọi biến thể (Mô Mô/Momo/MOMO/...) = hard block NOT_QUALIFIED; deterministic + LLM-enforced khi no-script. Script coverage: 2.1/2.2/2.3/2.4/2.6/2.8/2.10/2.11/2.12/2.13/2.14. | Add Rule 2.x, đổi threshold length, đổi PII pattern, đổi advisory behavior, đổi brand enforce |
| `references/03-content-quality.md` | v1.17 | Nhóm 3 (Rules 3.1-3.18) | LLM Judge input — title quality, body, capitalization, spelling, emoji, CTA, FOMO, segment-title alignment. **v1.17+** add cross-ref Rule 2.14 ở 3.4b (brand "MoMo" sai = hard block Tier 1, whitelist 3.4b chỉ cho brand viết đúng). | Add DIM, đổi sub-score threshold, đổi LLM rubric input |
| `references/04-regulatory-general.md` | v1.16 | Nhóm 4 general (Rules 4.1-4.3) | Absolute claims (4.1), discrimination (4.2), Vietnamese language (4.3). Áp dụng mọi campaign. Domain-specific 4.4-4.9 ở các file domain riêng trong `references/`. | Add general regulatory rule, đổi compliance scope |
| `references/05-segment.md` | v1.19 | Nhóm 5 (Rules 5.1-5.3, 5.5-5.6) | Segment cap 5M (5.1), BU daily cap (5.2), condition audit (5.3), exclude nhân viên MoMo (5.5 WARNING), **Rule 5.6 NEW v1.19+** segment hành vi ↔ content_type (BMC 9.0, condition-based KHÔNG dựa tên — behavioral detect qua attribute usage/dateRange recency/custom-SQL/dataSource BIGQUERY; behavioral↔PROMOTION_SERVICE, broad↔ADVERTISING, WARNING) + Segment Compliance Scorecard (field `segment_scorecard`). Script coverage: 5.1, 5.3.A/B, 5.5, 5.6, scorecard. | Đổi cap, audit logic, behavioral prefixes, CT mapping, scorecard |
| `references/06-routing.md` | v1.16 | Nhóm 6 general (Rules 6.1-6.4, 6.7) | Score-based routing, Group/CT routing, deadline alert, priority BYPASS Platform-only. Rule 6.5 SURVEY ở `survey-cio.md`. | Đổi routing matrix, add BYPASS rule, đổi deadline alert |

---

## 3. Guardrails — Domain (Lazy-load, 6 files)

> Load qua `scripts/detect_domain.py` keyword match. Chỉ load domain liên quan thay vì 70KB monolith.

| Path | Version | Domain | Description | Khi nào touch |
|---|---|---|---|---|
| `references/fs-products.md` | v1.16 | MoMo FS Products | Rule 4.9 — 4 sản phẩm (Túi Thần Tài / Vay Nhanh / Newton / Ví Trả Sau). Embedded JSON detection patterns + approved wording. BOM Legal scope. | Add sản phẩm FS mới, đổi approved wording |
| `references/vietlott.md` | v1.16 | Vietlott / Xổ số | Rules 4.4-4.5 — Nghị định 30/2007 compliance. Luôn HITL → BMC + Legal. | Đổi Vietlott regulatory, add Xổ số rule |
| `references/airfare.md` | v1.16 | Vé máy bay | Rule 4.6 — giá vé phải có điều kiện rõ. BMC review. | Đổi airfare wording rule |
| `references/insurance.md` | v1.16 | Bảo hiểm | Rule 4.7 — không gây hiểu nhầm phạm vi. BMC review. | Đổi insurance compliance |
| `references/cashback-fintech.md` | v1.16 | Cashback / Fintech | Rule 4.8 — hoàn tiền/ưu đãi phải có điều kiện rõ. Reg-floor → BMC. | Đổi cashback wording, add fintech rule |
| `references/survey-cio.md` | v1.17 | SURVEY (CIO) | Rule 6.5 — 5 hard checks (service / refid / form_id UUID v4 hoặc v7 / segment 250K / push cap 500K). **v1.17+ form_id accept v4 OR v7** (Survey Public migrated v7 per RFC 9562). Skill explicit KHÔNG distinguish source. Script coverage 4/5. | Đổi SURVEY threshold, add CIO rule, đổi UUID format |

---

## 4. Policy & LLM Judge

| Path | Version | Type | Description | Khi nào touch |
|---|---|---|---|---|
| `06-hitl-policy_v1.9.md` | v1.9 | HITL routing | Decision Matrix Group/CT → approver team. **AI Agreement Audit Trace v2 (v1.9+)**: refine `ai_agreement` semantic — track INTENT respect (không phải action match). Add 3 fields optional: `offline_review`, `review_note`, `reviewer_team`. 2-step gate Phase 4.0 (Bước 1 đồng ý → Bước 2 followup offline review). | Đổi HITL routing, đổi audit trace schema |
| `07-llm-judge-core_v1.12.md` | v1.12 | Tier 2 LLM rubric (core) | **Always load Phase 0** (v1.5.0+ pre-cache). Universal DIMs (3.1-3.5, 3.4b/c/d/e, 3.8, 3.11, 3.13-3.14, 4.1-4.3) + Schema + Sub-score 5-tier + HITL-trigger + Reg-floor mapping với `REG_FLOOR_DIMS` constant single source of truth. | Add DIM universal, đổi schema, đổi REG_FLOOR_DIMS |
| `07-llm-judge-promo_v1.12.md` | v1.12 | Tier 2 LLM rubric (promo subset) | **Lazy load Phase 2** khi CT ∈ {PROMOTION*, GAME, ADVERTISING, EVENT}. DIMs 3.6 (CTA promo), 3.7 (claim numeric HITL-trigger), 3.15-3.18 (segment/FOMO/number/personalization), 4.8 (cashback). | Add DIM promo, đổi CTA logic, đổi FOMO/cashback rubric |
| `07-llm-judge-quantrong_v1.12.md` | v1.12 | Tier 2 LLM rubric (Quan trọng subset) | **Lazy load Phase 2** khi CT ∈ {TRANSACTION, REMIND, WARNING, SERVICE}. DIMs 3.9 (sensitive action HITL-trigger), 3.10 (CTA clarity), 3.12 (maintenance timing). | Add DIM Quan trọng, đổi sensitive action logic |
| `07-llm-judge-domain_v1.12.md` | v1.12 | Tier 2 LLM rubric (domain subset) | **Lazy load Phase 2** khi `detect_domain.py` match keyword. DIMs 4.4-4.5 (Vietlott NĐ 30/2007), 4.6 (airfare TT 44/2024), 4.7 (insurance Luật KDBH), 4.9 (FS products MoMo Legal). | Add DIM domain, đổi domain rubric/wording |

---

## 5. Templates (Report + Dashboard)

| Path | Version | Type | Description | Khi nào touch |
|---|---|---|---|---|
| `08-batch-review-template_v1.9.md` | v1.9 | Chat report | **Summary-table-first (11 cột)** + hard mandate Phase 3 (table-only/link wrap/env-aware URL). Phase 5 examples v2 (v1.9+) expand 5 patterns audit footer schema v2 — agree, HITL same-team, HITL cross-team offline coord, genuine override, WARNING offline review. | Đổi default format, add column, đổi link enforcement, đổi audit footer pattern |
| `09-dashboard-html-template_v1.4.html` | v1.4 | Cowork dashboard | HTML template optional companion. 7 placeholders + FROZEN_REVIEW schema. JS segBig threshold 5M. Env-tag badge (PROD/UAT). | Đổi JS threshold, add placeholder, đổi schema FROZEN_REVIEW |
| `09-dashboard-template-README.md` | v1.4 | Doc | Hướng dẫn sử dụng dashboard HTML template + schema doc. | Đổi schema doc, add usage section |

---

## 6. Scripts — Tier 1 Hard Rule (Python deterministic)

> Phase 2 invoke qua công cụ chạy script của runtime — `skill_script`/`script` provider gọi theo **tên trần** (`tier1_check`/`char_count`/`timefmt`, **KHÔNG kèm `.py`** vì provider đăng ký theo stem), HOẶC Bash tool `python scripts/tier1_check.py --json '...'`. "unknown script" thường do dính `.py` → bỏ đuôi gọi lại. KHÔNG dùng LLM cho Tier 1.

| Path | Version | Type | Description | Khi nào touch |
|---|---|---|---|---|
| `scripts/tier1_check.py` | (header sync SKILL) | CLI entry | Aggregator gọi mọi rule check, output JSON với `issues[]` + `user_summary` (VN render). **v1.12.2:** LUÔN exit 0 + `verdict`/`exit_code` trong JSON (sandbox coi exit≠0=fail→vứt stdout); auto-unwrap `{"campaign":…}`/`{status,data}` flag-free (né limit 16 inputs); auto-detect batch. | Wire rule mới vào `check_campaign()`, đổi output schema, **giữ exit 0** |
| `scripts/gen_data.py` | v1.12.2 | Build tool | Compile `assets/banned-phrases.json` + `brand-dictionary.json` → `scripts/banned_data.py` + `brand_data.py` (module .py để ship vào sandbox). Single source = assets/. | Chạy lại sau khi Legal update `assets/*.json` |
| `scripts/banned_data.py` | (generated) | Data module | Bản compile của `assets/banned-phrases.json` (fallback cho `banned_phrases.py` trong sandbox — assets/ không ship). **KHÔNG sửa tay** — regenerate qua `gen_data.py`. | Regenerate khi banned-phrases.json đổi |
| `scripts/brand_data.py` | (generated) | Data module | Bản compile của `assets/brand-dictionary.json` (fallback cho `brand.py` trong sandbox). **KHÔNG sửa tay** — regenerate qua `gen_data.py`. | Regenerate khi brand-dictionary.json đổi |
| `scripts/timefmt.py` | `python scripts/timefmt.py --ms <epoch_ms>` (hoặc stdin JSON `{"push_time":<ms>}`) | CLI entry + shared import | Single source cho format giờ ICT GMT+7 (v1.11.4 chuyển từ `lib/` ra top-level vì có CLI). CLI in JSON `{"push_time_ms","push_time_ict"}` — **script BẮT BUỘC để quy đổi push_time, cấm convert thủ công**. Import: `format_push_time(epoch_ms)` → `DD/MM/YYYY HH:mm` (dùng bởi cả 2 render script) + `iso_now_vn()` (audit ts). Timezone-aware, không dùng `utcfromtimestamp` deprecated. | Đổi format giờ, đổi múi giờ |
| `scripts/constants.py` | — | Single source of truth | TẤT CẢ threshold/cap/max (SEGMENT_MAX_GENERAL=5M, SURVEY_MAX=250K, TITLE_MAX, BODY_MAX...). | MỌI lần đổi threshold (KHÔNG sửa chỗ khác) |
| `scripts/rules.py` | — | Per-rule functions | `rule_X_Y_<name>()` functions cho mỗi rule. Pure deterministic, return dict. | Add rule mới, đổi rule logic, edit error message |
| `scripts/pii.py` | — | Rule 2.4 | Detect VN phone, email, CCCD (9/12 digits), bank account regex. | Đổi PII pattern, add PII type mới |
| `scripts/banned_phrases.py` | — | Rule 2.11 | Load `assets/banned-phrases.json`, scan title+body với severity (blocker/critical/warning). Fail-open behavior (v1.4.5+): file missing → stderr warning 1 lần + skip Rule 2.11. | Đổi load logic, đổi severity behavior, đổi fail-open behavior |
| `scripts/brand.py` | — | Rule 2.14 (v1.19+) | Load `assets/brand-dictionary.json` field `enforce[]`, scan title+body bắt brand viết sai (regex match_pattern, token ≠ canonical → hard block). Fail-open: file missing/regex lỗi → stderr warning 1 lần + skip. | Đổi load logic, đổi fail-open, add brand enforce |
| `scripts/segment_audit.py` | — | Rule 5.3 + 5.5 + 5.6 (v1.17-1.19+) | Parse conditionV2 + dataSource (từ segment-mcp). `audit_segment_conditions()` → issues 5.3.A (tuổi) + 5.3.B (blacklist) + 5.5 (staff WARN) + 5.6 (segment hành vi↔CT WARN). `_is_behavioral_segment()` detect "đã dùng dịch vụ" từ điều kiện (attr usage / dateRange recency / custom-SQL / dataSource BIGQUERY — KHÔNG dựa tên). `segment_compliance_scorecard()` → checklist đạt/chưa-đạt + lý do (size/staff/blacklist/tuổi/khớp-CT). Constants: AGE_*, BLACKLIST_*, FINANCIAL_*, STAFF_*, BEHAVIORAL_ATTR_PREFIXES, CT_USED_SERVICE/CT_NON_USER. 5.3.C/D + khớp-dịch-vụ-chính-xác = Tier 2 LLM. | Đổi taxonomy/domain/staff/behavioral prefixes/CT mapping/scorecard |
| `scripts/refid_glossary.py` | — | Rule 1.8 | Load `assets/refid-glossary.tsv`, validate refid + URL refid skip (`_is_url_refid()`). Fail-open behavior (v1.4.5+): file missing → stderr warning 1 lần + skip Rule 1.8. | Đổi lookup pattern, đổi URL skip logic, đổi fail-open behavior |
| `scripts/detect_domain.py` | — | Phase 2 helper | Keyword scan title+body+CT → return `domains_to_load[]` cho lazy guardrail load. Convention v1.4.6+: mỗi `_<DOMAIN>_KEYWORDS` constant phải mirror với line "Trigger keywords:" trong `references/<d>.md` tương ứng. | Add domain detection, đổi keyword list (BẮT BUỘC sync với domain file) |
| `scripts/rule_descriptions.py` | — | VN translation | Central mapping `rule code → user-friendly VN description` cho 3 luồng (batch report / Phase 5 comment / dashboard). Principle #8. | MỌI lần add rule/DIM mới, đổi wording user-facing |
| `scripts/render_batch_report.py` | v1.6.0 | Phase 3 render | **Canonical markdown render.** Input JSON `{env, campaigns:[{name, alias, ct, title, body, image_url, t1, t2, verdict, reason_vn, action, segment?, push_time_ict?}]}`. **v1.6.0:** `--layout auto\|vertical\|table` — **vertical** (field: value, không tràn) cho single/side-panel, **table** (11 cột) cho batch full-width, auto=1→vertical/≥2→table. Luôn exit 0 + lỗi `ERROR:` ra stdout (sandbox). Enforce link wrap + env-aware URL, eliminate LLM variance. | Đổi schema input, đổi URL pattern, add verdict type, đổi/thêm layout |
| `scripts/render_athena_comment.py` | v1.7.1 | Phase 5 render | **Canonical Athena comment render** cho `update_campaign_action()` (v1.7.0+). Input JSON `{approver_email, approver_role, action, ai_verdict, ai_agreement, reasoning_vn, ...}` → output 3-part comment (Human reasoning + structured log + audit footer schema v2). Schema validation: required fields + conditional mandate (disagree_reason khi ai_agreement=no, review_note khi offline_review=yes, priority khi APPROVED). Eliminate LLM free-form comment variance. | Đổi schema input, đổi template, add audit field |
| `scripts/README.md` | — | Doc | Script CLI usage + 6-nhóm script table + integration guide. | Add script mới, đổi CLI signature |

---

## 7. Data files (KHÔNG bump SKILL version)

| Path | Version | Type | Description | Khi nào touch |
|---|---|---|---|---|
| `assets/banned-phrases.json` | 2026-05-18 | Data (Legal) | Banned phrases list với severity. Field `_version` (date), `_source`, `phrases[]`. Script `banned_phrases.py` load. | Legal sync — add từ cấm mới, đổi severity, đổi carve_out |
| `assets/refid-glossary.tsv` | 2026-05-18 | Data (Product) | 2827 unique refids, format `name<TAB>refid`. Source `MoMo RefID update <date>.xlsx`. Script `refid_glossary.py` load. | Product release màn mới — regenerate TSV từ xlsx |
| `assets/brand-dictionary.json` | 2026-06-26 | Data (Brand) | Rule 2.14 brand integrity + Rule 3.4b whitelist. `enforce[]` (brand bắt buộc viết đúng — canonical + match_pattern) + `known_partner_brands[]` (whitelist KHÔNG flag chính tả). Script `brand.py` load. | Content team — add brand enforce mới, đổi canonical/pattern, add partner brand |
| `role-mapping.json` | v2.2 | Config (admin) | Team account_ids (PCS / BMC / CIO / PLATFORM_OPERATOR). Field `_version` + `_changelog` + `_accounts_note` (v2.2+ document placeholder state). Tier 0 lookup. | Team approver mới, đổi can_approve scope, add team |
| `assets/MoMo RefID update 18 May 26.xlsx` | 18 May 26 | Source raw | Source xlsx từ Product → regenerate TSV. | Replace mỗi đợt release |
| `assets/BMC_Noti_Approval_Rules.xlsx` | — | Source raw | Source rule BMC (banned phrases, daily cap, dual review). | Reference khi Legal/BMC sync rule |
| `assets/CIO - Rule tạo_ duyệt noti cho survey.xlsx` | — | Source raw | Source rule CIO SURVEY scope (Rule 6.5). | Reference khi CIO sync |
| `assets/[Content Rules] Sản phẩm FS .pdf` | — | Source raw | Source rule FS products (BOM Legal). Reference cho Rule 4.9. | Reference khi BOM update wording |

---

## 8. Config & Docs

| Path | Version | Type | Description | Khi nào touch |
|---|---|---|---|---|
| `README.md` | (sync SKILL) | Doc | Project overview, folder tree, 5-Tier diagram, install guide. | Add folder mới, đổi install flow, đổi version reference |
| `admin-setup.md` | — | Doc (admin) | Tech admin setup — JWT token decode, account_id lookup, config.env, MCP integration. | Đổi setup flow, add config option mới |
| `CHANGELOG.md` | — | Doc (audit) | Component-scoped changelog (Skill / Guardrail / HITL Policy / LLM Judge / Dashboard / Role-mapping / Data files). | MỌI lần bump version → BẮT BUỘC add entry |
| `config.env.example` | — | Template | Env var template (ATHENA_TOKEN, MCP server URL, base URLs). | Add env var mới |
| `config.env` | — | Secret (local) | Actual env values với token thật. KHÔNG commit. | Token refresh (per admin-setup) |
| `.claude/settings.local.json` | — | Claude Code config | Allowlist commands cho Bash tool. | Add command mới cần allow |
| `docs/DA_AUDIT_PIPELINE_SPEC.md` | v1.0 (10/06/2026) | Spec (admin-only) | DA team external audit pipeline spec — hourly cron check Athena `action_logs` regex compliance + anti-pattern detection + Slack alert + daily email summary. NOT included trong install zip (admin coordinate). | Đổi audit regex patterns, đổi alert routing, sync khi skill audit footer schema thay đổi |

---

## 9. Install zip (output artifact)

> **Convention:** Chỉ **1 zip duy nhất** tồn tại trong folder tại mọi thời điểm. Bump version → BẮT BUỘC remove zip cũ. Xem `skill/packaging-install-skill.md` §6.
>
> **Scope:** Zip chỉ chứa ~34 files cho approval flow runtime. 2 admin sub-skills (`skill-update-process.md` + `packaging-install-skill.md`) là local-only, KHÔNG include.
>
> **KHÔNG auto-rebuild** sau edit — chỉ rebuild khi user explicit yêu cầu.

| Path | Version | Description |
|---|---|---|
| `noti-campaign-approval.zip` (+ copy `_v1.12.4.zip`) | v1.12.4 | Current install bundle (**46 files**). Rebuild 2026-08-07. **v1.12.4:** Phase 0 lazy-load (bỏ eager-load 00/02/05/06 + banned/refid → giảm 16→~6 tool call, fix hang). **v1.12.3:** Output discipline + `--layout vertical` side-panel. Approval runtime only — exclude 2 admin sub-skills + `docs/` + config.env + xlsx/pdf + `__pycache__`. **v1.12.2:** script self-contained cho sandbox skill_script (+gen_data.py +banned_data.py +brand_data.py, tier1_check luôn exit 0 + verdict JSON + auto-unwrap `{campaign}`). **v1.12.1:** tên trần stem KHÔNG `.py`. Kèm fix cũ (Rule 2.14 brand, 5.3/5.5/5.6 segment audit + Scorecard, UUID v4/v7, anti-hallucination). |
| `noti-campaign-approval_v1.12.0.zip` | v1.12.0 | Previous bundle giữ lại theo yêu cầu (dựng từ git HEAD). Flatten cấu trúc 3 cấp (agentskills spec) + fallback-invoke note, TRƯỚC fix tên trần v1.12.1. |
| `noti-campaign-approval_v1.11.6_backup.zip` | v1.11.6 | Backup force-added (git-tracked). |

---

## Maintenance checklist (mỗi lần edit)

Sau khi edit 1 file:

1. **Edit file** theo logic user
2. **Bump version** trong file (frontmatter / header / `_version` field)
3. **Update library row tương ứng**:
   - Cột Version → new version
   - Cột Description → nếu scope thay đổi
4. **Update header `Last updated` + `Library version`** của file `library.md` này
5. **Add changelog entry** trong `CHANGELOG.md` section đúng component
6. **Cross-file consistency check** — grep stale references
7. **Rebuild install zip** nếu touch SKILL/guardrail/script/template (xem skill-update-process.md để biết điều kiện)

---

*Owner: huong.vu4 (Platform Customer Success). Skill author: nga.nguyen6.*
