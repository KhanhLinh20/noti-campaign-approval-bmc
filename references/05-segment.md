# 05 — Segment Rules
## Noti Campaign Agent — Group Nhóm 5

> **Phiên bản:** v1.19 — 06/2026 (add Rule 5.6 — segment hành vi ↔ content_type, BMC 9.0, condition-based)
> **Scope:** Rules 5.1 (segment cap 5M + dual review), 5.2 (BU daily cap ≤10 push/day), 5.3 (segment condition audit), 5.5 (exclude nhân viên MoMo), 5.6 (segment hành vi ↔ content_type / BMC 9.0) + Segment Compliance Scorecard
> **Load:** Always (Phase 0 mandatory)
> **Script coverage:** Rule 5.1 + 5.3.A/B + 5.5 + scorecard ở `scripts/tier1_check.py` / `scripts/segment_audit.py` (cần MCP `athena-get-segment-info` lấy `conditionV2`). Rule 5.2 cần MCP `list_campaigns` aggregation. Rule 5.3.C/D + alignment là Tier 2 LLM.

---

## Nhóm 5 — Segment

### Rule 5.1 — Segment size cap với dual review khi > 5 triệu user
- **Tier:** 🔵 HITL (dual-team)
- **Trigger:** Agent review/submit campaign có segment size > 5,000,000 user
- **Logic (v1.16+ — dual review):** Khi segment vượt 5M, **bắt buộc 2 team confirm song song** trước khi approve:
  1. **Growth** — validate segment definition đúng audience (đúng intent targeting, không bao gồm test/staff/blacklist users)
  2. **Content-group approver** — reconfirm business decision do impact lớn (>5M user nhận noti = exposure cao)
- **Content-group approver mapping (per CT):**

  | CT group | Reconfirm approver |
  |---|---|
  | Quan trọng (TRANSACTION/REMIND/WARNING/SERVICE) | **PCS** |
  | Ưu đãi (PROMOTION_SERVICE/ADVERTISING/EVENT/GAME/PROMOTION/PROMOTION_OUTDATED) | **BMC** |
  | Tương tác (FRIENDS/BUSINESS_PAGE/SOCIAL) | **BMC** |
  | SURVEY | N/A — SURVEY có hard cap 250K riêng (Rule 6.5), không reach 5M được |

- **Hành động:** Agent hiển thị cảnh báo + flag dual HITL cho cả Growth + content-group approver. KHÔNG auto-proceed cho đến khi **cả 2 team** confirm bằng văn bản rõ ràng.
- **Error message:** `"Segment '[tên]' có [N] user — vượt ngưỡng 5 triệu. Cần Growth team validate segment + [PCS/BMC] reconfirm business impact trước khi approve."`
- **Tag (Phase 5 structured log):** `big_segment` (single tag, dual routing implied bởi `team={Growth,PCS}` hoặc `team={Growth,BMC}` notation — comma-separated)
- **Implementation note:**
  - Skill flag campaign với 2 suggested teams (Growth + content-group). Approver thấy cả 2 trong summary table.
  - Audit log thêm field `dual_review=true` khi action=APPROVE với big_segment.
  - PLATFORM_OPERATOR (cross-team) có thể override single-handedly nhưng phải log `override=true | just=platform_authority_dual_skip` để audit trace biết.

---

### Rule 5.2 — Business Unit daily campaign cap (≤10 push noti/ngày/BU)
- **Tier:** 🟡 Warning (Tier 2 — không hard block, advisory)
- **Nguồn:** BMC Rule #16.0 — *"Tối đa 10 campaign push notification active cùng 1 ngày — Alert khi ≥ 4 campaign → stagger"*
- **Trigger:** Phase 2 review campaign — count campaigns đang active trong cùng `owner_account_id` (business account, KHÔNG phải `created_by` email cá nhân — 1 BU có thể có nhiều người tạo)
- **Count logic:**
  ```bash
  # Pseudo Phase 2 implementation:
  # 1. Fetch all campaigns push today (any state)
  list_campaigns(status="IN_REVIEW,APPROVED,SEGMENT_PROCESSING,RUNNING,COMPLETED")
  # 2. Filter:
  #    - push_time in today (00:00 - 23:59 local time ICT)
  #    - owner_account_id = <current campaign's owner_account_id>
  # 3. Count = N
  ```
- **Counted states (in-flight = sẽ deliver hôm nay hoặc đã deliver hôm nay):**
  - ✅ Counted: `IN_REVIEW`, `APPROVED`, `SEGMENT_PROCESSING`, `RUNNING`, `COMPLETED`
  - ❌ NOT counted: `REJECTED`, `STOPPED`, `EXPIRED`, `CREATED` (draft)
- **Logic theo count:**
  - `N ≤ 3` → ✅ pass silently
  - `4 ≤ N ≤ 9` → 🟡 **Warning advisory** — suggest stagger schedule, không block. Tag `bu_daily_cap_warning`
  - `N ≥ 10` → 🟠 **HITL re-confirm** — block silent auto-approve, approver verify có justify exception không. Tag `bu_daily_cap_exceeded`
- **Warning message (N=4-9):** `"BU '[owner_account_name hoặc owner_account_id]' đã có [N] campaign active push hôm nay. BMC suggest stagger schedule để tránh user fatigue. Approver có thể proceed nếu intent là batch coordinated."`
- **HITL message (N≥10):** `"BU '[owner_account_id]' đã đạt cap 10 campaign/day (hiện [N]). Approver xác nhận có exception không trước khi approve thêm — vi phạm BMC Rule #16.0 user fatigue policy."`
- **Tag (Phase 5 structured log):** `bu_daily_cap_warning` (4-9) / `bu_daily_cap_exceeded` (≥10)
- **Implementation note:** 
  - MCP `list_campaigns` không filter trực tiếp theo `owner_account_id` — agent fetch + group manually.
  - Cache count trong Phase 1 batch scan để tránh duplicate API call khi review nhiều campaign cùng BU.
  - Edge case: timezone — dùng `today` theo VN UTC+7, không UTC. push_time field là Unix ms, convert ms → date VN trước khi compare.
  - **Counted theo `owner_account_id` (business account), KHÔNG theo `created_by` email** — confirmed semantic theo BMC Rule #16.0.

---

### Rule 5.3 — Segment Condition Audit (v1.17+) — đọc điều kiện cấu thành segment, so với policy duyệt
- **Tier:** 🔴 Script (age/blacklist deterministic) + 🟡 LLM (alignment) — và LLM tự enforce khi no-script (Copilot)
- **Bối cảnh:** Trước đây approver phải **mở segment xem điều kiện bằng tay**. Nay `segment-mcp` đã trả được điều kiện cấu thành segment → agent đọc tự động rồi **so ngược lại policy duyệt để chấm điểm**.
- **Trigger:** Phase 2, mọi campaign. Agent gọi `athena-get-segment-info(segment_name)` → CHỈ lấy `conditionV2.includeConditions` + `conditionV2.excludeConditions` (⚠️ KHÔNG load `Raw config` — response ~73KB, tốn token). Decode `attributeId` + `tagIds` + `operator` + `dateRange`.
- **Cấu trúc `conditionV2` (tham chiếu):**
  ```
  includeConditions[].conditions[] = { operator(AND/OR), attributeId, dateRange, attributeType, tagIds[] }
                                    | custom-SQL { description, outputType, rows[] }
  excludeConditions[].conditions[] = { operator, attributeId, tagIds[] }
  ```

#### 5.3.A — Compliance độ tuổi (age-restricted domain) 🔴 Block / 🔵 HITL
- **Áp dụng domain:** Vietlott/xổ số (Rule 4.4-4.5), FS vay/tín dụng — Vay Nhanh / Ví Trả Sau / PayLater (Rule 4.9), bảo hiểm có giới hạn tuổi (Rule 4.7), rượu/bia nếu có.
- **Logic:**
  - includeConditions chứa tag tuổi **dưới 18** → **Block (NOT_QUALIFIED)**. Mã tag dưới-18 (Athena thật):
    - `user_age_group_lower_18` (attribute `user_age_group_age`)
    - `user_age_age` ∈ {`user_age_15`, `user_age_16`, `user_age_17`} (và nhỏ hơn)
    - `user_age_source_kyc_age` ∈ {`..._15`, `..._16`, `..._17`}
  - Domain age-restricted mà segment **KHÔNG có điều kiện tuổi nào** → **HITL** (không xác nhận được toàn bộ ≥18, cần người verify).
- **Error message (block):** `"Segment target nhóm dưới 18 tuổi cho nội dung giới hạn độ tuổi — vi phạm quy định. Owner sửa segment (loại nhóm <18) và resubmit."`
- **HITL message (no-age):** `"Nội dung giới hạn độ tuổi nhưng segment chưa có điều kiện tuổi — cần xác nhận đối tượng đủ 18+ trước khi duyệt."`
- **Routing:** Vietlott → BMC + Legal · FS → BMC + Legal · insurance → BMC.

#### 5.3.B — Bắt buộc exclude blacklist/risk 🔵 HITL
- **Áp dụng domain:** tài chính/rủi ro — FS vay, PayLater, cashback giá trị cao, Vietlott.
- **Logic:** excludeConditions **KHÔNG** chứa `user_blacklist_risk` → **HITL** (BMC/Legal verify có cố ý không loại trừ user rủi ro không).
- **HITL message:** `"Nội dung tài chính/rủi ro nhưng segment chưa loại trừ nhóm rủi ro (blacklist) — cần xác nhận trước khi duyệt."`
- **Tag:** `segment_no_blacklist_exclude`

#### 5.3.C — Segment ↔ nội dung khớp không 🟡 Tier 2 (WARNING)
- **Logic (LLM):** so điều kiện segment (location / demographics / behavior) với claim trong title+body. Mismatch rõ → WARNING + giải thích.
  - Ví dụ: body "Ưu đãi riêng Hà Nội" nhưng segment chỉ target HCM → mismatch.
  - Ví dụ: body "dành cho hội viên VIP" nhưng segment target toàn bộ user active → mismatch nhẹ.
- **Tag:** `segment_content_mismatch`

#### 5.3.D — Target quá rộng (advisory) ⚪
- **Logic:** segment chỉ có 1 điều kiện rất rộng (vd chỉ age=mọi nhóm, hoặc chỉ location=toàn quốc) + size lớn (> Rule 5.1 cap) → advisory user-fatigue (bổ trợ Rule 5.1).
- **Tag:** `segment_overbroad`

- **Severity tổng hợp & chấm điểm:**
  | Sub-check | Verdict đóng góp |
  |---|---|
  | 5.3.A include <18 | 🔴 NOT_QUALIFIED (hard block) |
  | 5.3.A no-age (restricted) · 5.3.B no-blacklist | 🟣 HITL_REQUIRED (force, bất kể score) |
  | 5.3.C mismatch | 🟡 WARNING (−điểm Tier 2) |
  | 5.3.D over-broad | ⚪ advisory |
- **Implementation note:** `scripts/segment_audit.py::audit_segment_conditions(condition_v2, content_type, domains)` cover 5.3.A + 5.3.B deterministic. 5.3.C/D là Tier 2 LLM (cần ngữ nghĩa). Constants ở `scripts/constants.py` (AGE_RESTRICTED_DOMAINS, MINOR_AGE_TAGS, BLACKLIST_RISK_TAG, FINANCIAL_RISK_DOMAINS).
- **⚙️ LLM-mode (Copilot / no-script):** Khi không chạy được Python, LLM tự đọc `conditionV2` đã decode + áp 5.3.A/B/C/D theo spec trên. Mã tag dưới-18 + `user_blacklist_risk` đã liệt kê tường minh để LLM match.

---

### Rule 5.5 — Exclude nhân viên MoMo nội bộ (v1.18+) 🟡 WARNING
- **Tier:** 🔴 Script (deterministic) — và LLM tự enforce khi no-script
- **Nguồn:** Yêu cầu chung BMC + CIO — segment production push **nên loại trừ nhân viên MoMo** (tránh nội bộ nhận push marketing thật).
- **Trigger:** Phase 2, mọi campaign có `conditionV2`.
- **Logic:** excludeConditions **KHÔNG** chứa attribute họ nhân viên MoMo → flag WARNING.
  - Attribute thật: `user_account_staff_by_group_department` (tags `_nontech` / `_protech` ...). Match cả prefix `user_account_staff*`.
- **Severity:** 🟡 WARNING — KHÔNG hard block, KHÔNG force HITL. Vào scorecard cho approver tự quyết (1 số campaign nội bộ cố ý include staff).
- **Message:** `"Segment chưa loại trừ nhân viên MoMo nội bộ — cân nhắc exclude trước khi push production."`
- **Tag:** `segment_no_staff_exclude`
- **Implementation:** `scripts/segment_audit.py` (issue WARNING + item scorecard).

---

### Rule 5.6 — Segment hành vi ↔ content_type (BMC Rule 9.0, v1.19+) 🟡 WARNING
- **Tier:** 🔴 Script (deterministic, condition-based) + 🟡 LLM (khớp chính xác dịch vụ)
- **Nguồn:** BMC Rule 9.0 (Critical) — *"User từng dùng dịch vụ → ưu đãi dịch vụ; user chưa dùng → quảng cáo"*.
- **⚠️ NGUYÊN TẮC: chỉ đọc attribute/điều kiện trong `conditionV2` + `dataSource`. TUYỆT ĐỐI KHÔNG dựa tên segment** (tên do user tự đặt — `_A30` trong tên KHÔNG đáng tin).
- **"Đã dùng dịch vụ" (behavioral)** khi segment có ≥1 signal (đọc từ điều kiện):
  - Attribute thuộc họ hành vi: `user_transaction_*`, `user_active_*`, `user_project_*` (grounded segment-mcp)
  - `dateRange` là recency window (KHÁC `ALWAYS_ACTIVE` — vd A30/A60/A90 ở **field dateRange**, không phải tên)
  - Custom-SQL condition (description: giao dịch / service code / usage)
  - `dataSource` chứa `BIGQUERY` (có query hành vi, không chỉ thuộc tính tĩnh)
- **"Chưa dùng / broad"** = chỉ có thuộc tính nhân khẩu (age/location/gender) + toàn `ALWAYS_ACTIVE` + dataSource chỉ `['ATTRIBUTE']`.
- **Logic (chỉ áp dụng khi `content_type` ∈ {PROMOTION_SERVICE, ADVERTISING}):**
  - behavioral + CT=`ADVERTISING` (quảng cáo) → WARNING (nên là `PROMOTION_SERVICE` ưu đãi dịch vụ)
  - non-behavioral + CT=`PROMOTION_SERVICE` (ưu đãi dịch vụ) → WARNING (nên là `ADVERTISING` quảng cáo, hoặc bổ sung điều kiện usage)
- **Severity:** 🟡 WARNING — không block, vào scorecard, approver verify (vì khớp **đúng dịch vụ** trong noti cần đọc ngữ nghĩa = Tier 2 LLM).
- **Tag:** `segment_ct_behavior_mismatch`
- **Implementation:** `scripts/segment_audit.py::_is_behavioral_segment()` + Rule 5.6 trong `audit_segment_conditions()`. Constants: BEHAVIORAL_ATTR_PREFIXES, STATIC_DATERANGES, CT_USED_SERVICE/CT_NON_USER.
- **Phần Tier 2 LLM:** khớp **chính xác dịch vụ** (vd noti airtime ↔ segment lọc giao dịch airtime) — đọc service code trong SQL + so nội dung. Deterministic chỉ phân biệt behavioral-vs-broad; LLM refine đúng dịch vụ.

---

### Segment Compliance Scorecard (v1.18+) — approver thấy "đạt/chưa đạt + lý do"
> Mục tiêu: thay việc approver **mở segment check tay**. Agent so segment với rule BMC/CIO rồi xuất **checklist** đạt/chưa-đạt + lý do cụ thể.

- **Nguồn dữ liệu:** `tier1_check.py` output field `segment_scorecard` (từ `segment_compliance_scorecard()`), có khi đã inject `conditionV2`.
- **Áp dụng có điều kiện theo CT/domain:**
  | Check | Khi nào | Pass = |
  |---|---|---|
  | **Size** | Luôn | ≤5M (BMC) · ≤250K nếu SURVEY (CIO). >5M → ⚠️ warn (dual review), >250K survey → ❌ fail |
  | **Loại nhân viên MoMo** | Luôn | exclude có `user_account_staff_*` (Rule 5.5) |
  | **Loại blacklist** | Domain tài chính/rủi ro | exclude có `user_blacklist_risk` (Rule 5.3.B) |
  | **Tuổi 18+** | Domain age-restricted | không có nhóm <18 + có điều kiện tuổi (Rule 5.3.A) |
  | **Khớp loại nội dung** | CT ∈ {ưu đãi dịch vụ, quảng cáo} | hành vi segment khớp content_type (Rule 5.6/BMC 9.0) |
- **Output shape:** `{team, items:[{label, status: pass|fail|warn, reason}], passed, total, overall: "đạt"|"chưa đạt", fail_reasons[]}`.
- **Hiển thị Phase 3 (cho approver):** với mỗi campaign có scorecard, render block ngắn:
  ```
  🧩 Segment check (BMC) — chưa đạt (2/4)
     ✅ Size 1.2M < 5M
     ❌ Chưa loại nhân viên MoMo
     ❌ Chưa loại nhóm rủi ro (blacklist)
     ✅ Tuổi: chỉ 18+
  ```
- **Quan hệ với verdict:** scorecard là **bảng tổng hợp hiển thị**; phần ảnh hưởng verdict vẫn do issues (5.3.A block · 5.3.A no-age/5.3.B HITL · 5.5 warning). Scorecard giúp approver thấy nhanh "thiếu gì để pass".
- **⚙️ LLM-mode (Copilot):** LLM tự dựng scorecard tương tự từ `conditionV2` đã decode + size, theo bảng checklist trên.

---

