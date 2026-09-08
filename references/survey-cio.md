# Domain — SURVEY (CIO scope)

> **Phiên bản:** v1.17 — 06/2026 (Rule 6.5.A.3 accept UUID v4 OR v7 — fix Survey Public migration v7 per RFC 9562)
> **Scope:** Rule 6.5 — SURVEY validation (CIO scope) + routing. 5 hard checks (service enum / ref_id / form_id UUID / segment 250K / push cap 500K/day/project) + 3 advisory.
> **Load:** **Lazy** — via `scripts/detect_domain.py` (CT-driven, KHÔNG keyword scan)
> **Trigger:** `content_type=SURVEY` (uppercase normalized)
> **HITL routing:** CIO bắt buộc, không auto-schedule
> **Script coverage:** 4 hard checks implemented trong `scripts/rules.py` `rule_6_5_survey_validation()`. Push cap (check 5) cần MCP cross-aggregation, script không cover.

---

### Rule 6.5 — Khảo sát (SURVEY) validation + CIO routing (v1.10 expanded)
- **Tier:** 🔴 Script (Tier 1 enum/regex/aggregation) + 🔵 HITL (routing CIO)
- **Trigger:** Campaign có `content_type = SURVEY` được submit hoặc reviewed
- **Routing rule (giữ nguyên từ v1.7):** 100% campaign SURVEY phải do CIO duyệt manual, không auto-SCHEDULED bất kể score.

---

#### 6.5.A — Tier 1 Script checks (hard fail nếu sai)

**1. Service group + type enum (cặp API code):**
- REQUIRED: `service_category.service_group == "general"` **AND** `service_category.service_type == "survey_onlinepanel"`
- UI display: "Thiết lập chung / Khảo sát MoMo" (Athena concatenate API code → human label)
- Nếu sai → REJECT
- Error message: `"SURVEY phải dùng Service group 'Thiết lập chung / Khảo sát MoMo' (API: service_group=general + service_type=survey_onlinepanel). Hiện tại: '<actual>'. Sửa trước khi submit."`

**2. Ref ID enum:**
- REQUIRED: `variants.<variant>.notification_reference.ref_id == "onlinepanel_entry"`
- Nếu sai → REJECT

**3. form_id presence + UUID v4 OR v7 format (v1.17+):**
- Parse `variants.<variant>.extra.extra` (JSON string) → có key `form_id`
- REQUIRED: form_id matches regex `^[0-9a-f]{8}-[0-9a-f]{4}-[47][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$`
  - Group 3 first char: `4` (v4) OR `7` (v7 per RFC 9562)
  - Group 4 first char: `[89ab]` (variant — chung cả 2 version)
- Nếu missing → REJECT
- Nếu invalid format (không phải v4 hoặc v7) → REJECT

**Source clarification (v1.17+) — skill KHÔNG distinguish được:**
- Survey Public hiện generate UUID v7 (RFC 9562 — time-ordered UUID spec)
- Link Test legacy có thể còn UUID v4
- **Skill KHÔNG có tool để verify source** của form_id (Public vs Link Test)
- Agent **TUYỆT ĐỐI KHÔNG** claim "form_id từ Public" hoặc "từ Link Test" — đây là fabricated information
- Skill chỉ check **FORMAT** UUID v4/v7 valid, accept cả 2

**Anti-pattern (em đã sai 10/06/2026):**
- ❌ AI claim "form_id từ Link Test" (skill KHÔNG distinguish được)
- ❌ AI claim "form_id UUID valid" mà KHÔNG show evidence từ `tier1_check.py` output
- ❌ AI cite character position sai (vd "ký tự thứ 3 = 7" — actual position 1)
- ✅ Agent BẮT BUỘC quote verbatim từ `tier1_check.py --json` output (xem skill Phase 2 mandate v1.8.0+)

**4. Segment size cap (SURVEY-specific):**
- REQUIRED: `segment.size <= 250_000`
- Threshold riêng cho SURVEY (Rule 5.1 với threshold 5M general không apply)
- Nếu vượt → **HITL → CIO** (CIO confirm hoặc yêu cầu Growth split segment)

**5. Push cap 500K/day/project (cross-campaign aggregation):**

Algorithm:
```
def check_push_cap(current_campaign):
    # Extract project_id
    project_id = extract_project_id(current_campaign.name)
    
    # Quality check — flag nếu pattern nghi ngờ
    if extract_quality_suspicious(current_campaign.name):
        return {"verdict": "HITL", "suggested_team": "CIO",
                "reason": "Project ID extraction nghi ngờ, CIO confirm thủ công"}
    
    # Push date (UTC+7 calendar day boundary)
    push_date = date(current_campaign.push_time, UTC+7)
    
    # Status filter — chỉ count campaigns thực sự sẽ/đã push
    COUNT_STATUSES = {
        "IN_REVIEW", "APPROVED",
        "SEGMENT_PROCESSING", "ML_PROCESSING",
        "SCHEDULED", "PUSHING", "FINISHED"
    }
    # Exclude: EXPIRED, REJECTED, STOPPED (terminal fail — không push)
    
    # Fetch other campaigns same date + same project + count statuses
    others = list_campaigns(status_in=COUNT_STATUSES, push_date=push_date)
    same_project = [c for c in others
                    if c.name != current_campaign.name
                    and extract_project_id(c.name) == project_id]
    
    # Sum total
    total = sum(c.segment.size for c in same_project) + current_campaign.segment.size
    
    if total > 500_000:
        return {
            "verdict": "HITL",
            "suggested_team": "CIO",
            "reason": f"Project '{project_id}' ngày {push_date}: dự kiến tổng {total/1000:.0f}K user, "
                      f"vượt cap 500K/day/project",
            "related_campaigns": same_project
        }
    return {"verdict": "PASS"}


def extract_project_id(campaign_name: str) -> str:
    # 1. Strip leading date prefix: yyMMdd (6 digits) hoặc yyyyMMdd (8 digits)
    name = re.sub(r'^\d{6,8}_', '', campaign_name)
    # 2. Split by underscore
    tokens = name.split('_')
    # 3. Take first 3 tokens (team_code + project_name + segment_id pattern)
    project_tokens = tokens[:3] if len(tokens) >= 3 else tokens
    return '_'.join(project_tokens)


def extract_quality_suspicious(campaign_name: str) -> bool:
    """Flag pattern nghi ngờ — không match convention CIO."""
    # No date prefix
    if not re.match(r'^\d{6,8}_', campaign_name):
        return True
    # After date strip, < 2 tokens (quá ngắn)
    stripped = re.sub(r'^\d{6,8}_', '', campaign_name)
    if len(stripped.split('_')) < 2:
        return True
    # Ký tự lạ (không phải alphanumeric + underscore + dash)
    if re.search(r'[^a-zA-Z0-9_\-]', stripped):
        return True
    return False
```

**Verdict logic:**
- Vượt cap (`total > 500K`) → HITL → CIO (CIO confirm bypass HOẶC Growth split segment)
- Pattern extraction nghi ngờ → HITL → CIO (manual review project_id)
- Pass → tiếp tục flow Tier 0/2 advisory

**Examples test pattern:**

| Campaign name | project_id extracted | OK? |
|---|---|---|
| `260514_DLS_CrossBorder_A60_SurveyOTA` | `DLS_CrossBorder_A60` | ✓ |
| `260514_DLS_CrossBorder_A60_SurveyuserForeignCountry` | `DLS_CrossBorder_A60` | ✓ MATCH với row trên |
| `260515_DLS_CrossBorder_A60_SurveyOTA` | `DLS_CrossBorder_A60` | ✓ MATCH cross-day |
| `260514_NT_GMC_PROJECT_SUBWALLET_NAME_AND_SERVICE_VALIDATION_ABOVE30_v2` | `NT_GMC_PROJECT` | ✓ (heuristic, NT_GMC = team + project) |
| `survey_test_abc` (không có date prefix) | `survey_test_abc` | ⚠ Flag suspicious → HITL |

---

#### 6.5.B — Tier 0/2 Advisory (informational, KHÔNG block)

**6. Segment exclusion attributes** — DEFERRED, KHÔNG enforce ở skill:

> **Status:** Skill **KHÔNG flag** trong verdict output. CIO **Step 1** (Check condition của segment) đã cover trách nhiệm này — không cần skill nhắc lại.

**Lý do defer:**
- MCP hiện tại không expose tool nhận `segment_name` và trả về include/exclude conditions (đã verify với 8 CDP tools + Noti `get_segments`)
- Athena workflow `athena-eval-segment` mention `athena-search-segment` + `athena-get-segment-info` nhưng 2 tool đó chưa wrap qua MCP
- Skill không có cách auto-check 4 attributes → bỏ qua, không spam reminder

**Khi nào re-enable:**
- Engineering bổ sung MCP tool `get_segment_conditions(name)` (hoặc tương đương) → skill auto-verify
- Lúc đó update rule này: chuyển từ DEFERRED → Tier 1 Script (hard check 4 attributes trong `excludeHybridConditions`)

**4 attributes cần check (reference cho engineering khi build tool):**
- `user_account_staff_by_group_department` — nhân viên MoMo theo phòng ban (tags: nontech, protech)
- `user_account_staff_by_work_place` — nhân viên MoMo theo thành phố công tác (tags: ha_noi, hcm, da_nang)
- `user_blacklist_risk` — blacklist risk chung (tag: user_blacklist_risk_promotion)
- `user_blacklist_by_project_detail` — blacklist theo từng project

**7. template_variables fallback** (advisory):
- Best practice: nếu `body` chứa `${lastname}` → recommend set `variants.<variant>.template_variables.lastname` với fallback (VD `"bạn"`)
- Đảm bảo render đúng khi user không có lastname data
- Reference: campaign `260514_NT_GMC_PROJECT_SUBWALLET_...` dùng fallback `"bạn"` đúng best practice
- ⚠️ Fallback này CHỈ dùng cho render lúc GỬI THẬT. **KHÔNG** dùng để đếm ký tự title/body — khi đếm, placeholder LUÔN = 0 ký tự (strip), không render fallback rồi cộng vào (xem Rule 2.1/2.2).

**8. Duplicate Protection** (advisory):
- Skill KHÔNG check (config thuộc Survey form, không phải noti campaign)
- CIO verify manually ở Step 3 (push test) trước approve theo CIO 4-step process

---

#### 6.5.C — CIO 4-step approval flow (informational)

Theo CIO rule, approver duyệt SURVEY theo 4 bước:
1. Check condition của segment (skill hỗ trợ 6.5.A.4 + 6.5.B.6)
2. Check trường thông tin của noti (skill hỗ trợ 6.5.A.1/2/3)
3. Push test survey để đảm bảo logic + có set duplicate protection (skill 6.5.B.8 advisory)
4. Approve noti

---

#### 6.5.D — Reference example (campaign verified valid)

Campaign `260514_NT_GMC_PROJECT_SUBWALLET_NAME_AND_SERVICE_VALIDATION_ABOVE30_v2` (Athena prod, FINISHED, CIO offline approved) dùng làm reference cho schema chuẩn:

```json
{
  "content_type": "SURVEY",
  "service_category": {"service_group": "general", "service_type": "survey_onlinepanel"},
  "notification_reference": {"ref_id": "onlinepanel_entry"},
  "variants": {
    "control": {
      "extra": {"extra": "{\"form_id\":\"1ae8dc81-d658-40cd-b8cd-469af874de9e\"}"},
      "template_variables": {"lastname": "bạn"}
    }
  },
  "segment": {"size": 200000},
  "priority": "NORMAL",
  "cap_set_pool": "SURVEY"
}
```

---

#### 6.5.E — Error message + Routing

**Error messages (script-level fail):**
- Sai service: `"SURVEY phải dùng Service group 'Thiết lập chung / Khảo sát MoMo'. Hiện tại: '<actual_combo>'."`
- Sai ref_id: `"SURVEY phải dùng Ref ID 'onlinepanel_entry'. Hiện tại: '<actual>'."`
- Missing form_id: `"SURVEY thiếu form_id trong extra. CIO yêu cầu form_id từ Survey Public (UUID v4)."`
- Invalid form_id format: `"form_id '<value>' không đúng format UUID v4. Đảm bảo copy từ Survey Public, không phải Link Test."`
- Segment > 250K: `"Segment '<name>' có <N> user, vượt cap 250K/segment cho SURVEY. CIO cần confirm bypass hoặc Growth split segment."`
- Vượt cap day/project: (xem error message trong Algorithm 6.5.A.5)

**HITL routing:** Tất cả SURVEY (pass hoặc fail script) → CIO duyệt manual, không auto-SCHEDULED bất kể score Tier 2.

**Implementation note:**
- Cross-campaign aggregation (6.5.A.5) cần gọi `list_campaigns` với date + status filter → có sẵn trong MCP noti-mcp + noti-mcp-prod
- Segment definition check (6.5.B.6) không khả thi ở client — advisory only

---

