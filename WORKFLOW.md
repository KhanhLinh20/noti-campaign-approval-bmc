# Chi Tiết Luồng Tự Động Chạy Hiện Tại

> Auto-Review Campaign Workflow — Tự động review & duyệt Noti Campaign → Gửi Google Chat

---

## 📋 Tóm Tắt Luồng

```
┌─────────────────────────────────────────────────────────────┐
│ 1. INPUT: Campaign JSON                                     │
│    - Đọc file campaign_{name}.json hoặc fetch từ MCP        │
│    - Extract: created_by, variants, notification_reference  │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. TIER 1 CHECK (Deterministic Rules)                       │
│    - Call: tier1_check.py với campaign JSON                │
│    - Output: tier1_score, tier1_band, issues, hard_block    │
│    - Check: Title len, Body len, Required fields, etc       │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. TIER 2 CHECK (LLM Judge - Simulated)                     │
│    - Score: 0-100 dựa trên heuristics                      │
│    - Default: 90 nếu Tier1 PASS                            │
│    - Reduce: -5 nếu không có ${...} tokens                │
│    - Reduce: -10 nếu content chứa generic words            │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. VERDICT LOGIC (4-way decision)                           │
│    - Tier1 hard_block → NOT_QUALIFIED ❌                   │
│    - Tier2 < 50 → NOT_QUALIFIED ❌                         │
│    - Tier2 50-84 → WARNING ⚠️                              │
│    - Tier2 ≥ 85 + Quan trọng/SURVEY → HITL 🔵              │
│    - Tier2 ≥ 85 + Other → QUALIFIED ✅                     │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. OIDC USER ID LOOKUP (Google Chat Mention)               │
│    - Get creator_email from campaign.created_by             │
│    - Call OIDC: https://oidc.mservice.io/google-users      │
│    - Params: ?emails=creator_email@domain                   │
│    - Extract: numeric user ID                               │
│    - Cache: Store in USER_ID_CACHE for repeat calls         │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. FORMAT GOOGLE CHAT MESSAGE                               │
│    - Verdict emoji + status text                            │
│    - Creator mention: <users/[numeric-id]>                  │
│    - Campaign name, content type                            │
│    - Tier1 + Tier2 scores                                   │
│    - Issues detail (JSON format)                            │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. SEND TO GOOGLE CHAT                                      │
│    - POST to webhook URL                                    │
│    - Status: success / error / dry_run                      │
│    - Dry-run: Print message, don't actually send            │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 Chi Tiết Từng Step

### Step 1: INPUT - Load Campaign

**Function:** `review_single_campaign(campaign_name, dry_run=False)`

**Input:**
```
campaign_name = "phuclong_giam40k"
dry_run = False / True
```

**File Location:**
```
campaign_{campaign_name}.json
# Example: campaign_phuclong_giam40k.json
```

**Data Extracted:**
```python
campaign_json = {
    "id": "6a8c36b69a97a86d93e7cbf7",
    "name": "AUTOTEST_20301026_phuclong_giam40k",
    "created_by": "nga.nguyen6@mservice.com.vn",  # ← Creator email
    "status": "IN_REVIEW",
    "variants": {
        "control": {
            "caption": "Giảm 40.000đ trà sữa Phúc Long",  # Title
            "body": "Kính mời quý khách...",              # Body
        }
    },
    "notification_reference": {
        "content_type": "PROMOTION",  # Filter: PROMOTION|GAME|etc
        "group": "Unknown"            # Quan trọng / SURVEY / other
    }
}
```

**TODO (Not Implemented Yet):**
- [ ] Replace file read with MCP `list_campaigns(state=IN_REVIEW)`
- [ ] Filter by content_type automatically

---

### Step 2: TIER 1 CHECK - Deterministic Rules

**Function:** `run_tier1_check(campaign)`

**Process:**
1. Call `tier1_check.py` script via subprocess
2. Pass campaign JSON as stdin (pipe)
3. Receive JSON output with scoring

**Script Used:**
```
scripts/tier1_check.py
```

**Output Format:**
```json
{
  "passed": true,
  "hard_block": false,
  "tier1_score": 100,
  "tier1_band": "PASS",
  "issues": [],
  "verdict": "PASS"
}
```

**Scoring Rules (from tier1_check.py):**
- REQ.1: Required fields (Name, Group, Type, Time) → penalty -20 if missing
- TITLE_LEN: Title ≤ 30 chars → penalty based on length
- BODY_LEN: Body ≤ 160 chars → penalty based on length
- And more rules...

**Score Calculation:**
```
tier1_score = 100 - sum(penalties)
If score < 0 → hard_block = true
```

**Output to Console:**
```
→ Running Tier 1 check...
  Tier 1 Score: 100/100 [PASS]
  Issues: 0
```

---

### Step 3: TIER 2 CHECK - LLM Judge (Simulated)

**Function:** `simulate_tier2_check(tier1, campaign)`

**Current Implementation (PLACEHOLDER):**
```python
def simulate_tier2_check(tier1, campaign):
    if not tier1.get("passed"):
        return {"score": 0, "hitl_triggered": False, "issues": []}
    
    score = 90  # Default good score if T1 passes
    
    # Heuristic 1: Check personalization tokens
    if "${" not in title and "${" not in body:
        score -= 5  # No personalization → penalty -5
    
    # Heuristic 2: Check generic words
    if any(x in body.lower() for x in ["hay", "có", "thử xem"]):
        score -= 10  # Generic wording → penalty -10
    
    return {
        "score": score,
        "hitl_triggered": False,
        "issues": [],
        "note": "Simulated Tier 2 (placeholder)"
    }
```

**TODO (Production):**
- [ ] Replace with real LLM Judge API call
- [ ] Use Claude/GPT for quality assessment
- [ ] Add proper HITL trigger rules

**Output to Console:**
```
→ Running Tier 2 check...
  Tier 2 Score: 85/100
```

---

### Step 4: VERDICT LOGIC - Final Decision

**Function:** `determine_verdict(tier1, tier2, group)`

**Decision Tree:**
```python
if tier1.hard_block:
    return "NOT_QUALIFIED"  # ❌ Hard block → auto reject

if tier1.hitl_required or tier2.hitl_triggered:
    return "HITL_REQUIRED"  # 🔵 HITL triggered → manual review

tier2_score = tier2.score

if tier2_score < 50:
    return "NOT_QUALIFIED"  # ❌ Low quality → reject

if tier2_score < 85:
    return "WARNING"  # ⚠️ Medium quality → needs manual review

# Score >= 85, check group
if group in ["Quan trọng", "SURVEY"]:
    return "HITL_REQUIRED"  # 🔵 Important campaign → always manual

return "QUALIFIED"  # ✅ Good quality + not important → auto approve
```

**Verdict Meanings:**
| Verdict | Emoji | Meaning | Action |
|---------|-------|---------|--------|
| QUALIFIED | ✅ 🟢 | Auto-approved | Ready to push |
| WARNING | ⚠️ 🟡 | Manual review needed | Send to reviewer |
| HITL_REQUIRED | 🔄 🔵 | Must manually approve | Route to team |
| NOT_QUALIFIED | ❌ 🔴 | Rejected | Return to creator |

**Output to Console:**
```
→ Verdict: QUALIFIED
```

---

### Step 5: OIDC USER ID LOOKUP

**Function:** `get_user_id_by_email(email)`

**Process:**
```
Input: email = "nga.nguyen6@mservice.com.vn"
         ↓
1. Check USER_ID_CACHE (in-memory)
   - If found → return cached ID
   
2. If not cached → Call OIDC endpoint
   - URL: https://oidc.mservice.io/google-users
   - Query: ?emails=nga.nguyen6@mservice.com.vn
   - Method: GET
   - Timeout: 10s
   
3. Parse response
   Response format:
   {
     "nga.nguyen6@mservice.com.vn": {
       "id": "106660292106349566440"
     }
   }
   
4. Extract numeric ID
   - Key: email
   - Field: response[email]["id"]
   
5. Cache result
   - Store in USER_ID_CACHE[email] = numeric_id
   
Output: "106660292106349566440" (string)
```

**User ID Cache:**
```python
USER_ID_CACHE = {
    "nga.nguyen6@mservice.com.vn": "106660292106349566440",
    "phuong.do2@mservice.com.vn": "112675013139919757775",
    # ... more as discovered
}
```

**Fallback:**
- If OIDC fails → return None
- If email not found → print warning, proceed without ID
- Google Chat will use email format if ID unavailable

**Output to Console:**
```
→ Fetching userId for nga.nguyen6@mservice.com.vn...
  ✓ Fetched from OIDC: nga.nguyen6@mservice.com.vn → 106660292106349566440
  ✓ userId: 106660292106349566440
```

---

### Step 6: FORMAT GOOGLE CHAT MESSAGE

**Function:** `format_chat_message(campaign, tier1, tier2, verdict, creator_email, user_id)`

**Message Structure:**
```
🟢 *Auto-Review: ✅ Đã duyệt (QUALIFIED)*

👤 Creator: <users/106660292106349566440>
📋 Campaign: AUTOTEST_20301026_phuclong_giam40k
🎯 Content Type: PROMOTION

📝 *Nội dung:*
Title: Giảm 40.000đ trà sữa Phúc Long
Body: Kính mời quý khách thưởng thức trà sữa Phúc Long với ưu đãi giảm 40.000đ. Tham gia ngay!

📊 *Chấm điểm:*
• Tier 1 (Script): 100/100 [PASS]
• Tier 2 (LLM): 85/100

🔍 *Chi tiết:*
{
  "tier1_issues": [],
  "tier2_issues": []
}
```

**Verdict Emoji Mapping:**
```python
{
    "QUALIFIED": "🟢",         # Green circle
    "WARNING": "🟡",           # Yellow circle
    "HITL_REQUIRED": "🔵",     # Blue circle
    "NOT_QUALIFIED": "🔴"      # Red circle
}
```

**Creator Mention Format:**
```python
if user_id:
    mention = f"<users/{user_id}>"
    # Example: <users/106660292106349566440>
else:
    mention = f"<users/{email}>"
    # Example: <users/nga.nguyen6@mservice.com.vn>
```

**Output to Console:**
```
→ Preparing Google Chat message...
[Shows JSON preview]
```

---

### Step 7: SEND TO GOOGLE CHAT

**Function:** `send_to_google_chat(message)`

**Webhook URL (from env var `GOOGLE_CHAT_WEBHOOK`):**
```
https://chat.googleapis.com/v1/spaces/<SPACE_ID>/messages?key=<KEY>&token=<TOKEN>
```
> Không hardcode webhook vào source. Xem `.env.example`.

**HTTP Request:**
```
POST /v1/spaces/AAQAf9IV-aQ/messages?key=...&token=...
Content-Type: application/json

{
  "text": "🟢 *Auto-Review: ✅ Đã duyệt (QUALIFIED)*\n\n👤 Creator: <users/106660292106349566440>\n..."
}
```

**Response Handling:**
```python
if response.status_code == 200:
    return True   # ✅ Success
else:
    return False  # ❌ Failed
```

**Dry-Run Mode:**
```
if dry_run:
    print("[DRY RUN] Would send to Google Chat:")
    print(json.dumps(message, indent=2, ensure_ascii=False))
    # Don't actually POST
else:
    # Actually send
    send_to_google_chat(message)
```

**Output to Console:**
```
→ Sending to Google Chat...
✅ Message sent to Google Chat!

Result: {
  "status": "success",
  "verdict": "QUALIFIED",
  "message": "Sent to Google Chat",
  "user_id": "106660292106349566440"
}
```

---

## 📊 End-to-End Example Flow

**Input:**
```bash
python auto_review.py --campaign-name phuclong_giam40k
```

**Execution Log:**
```
======================================================================
Reviewing campaign: phuclong_giam40k
======================================================================
✓ Campaign fetched (TODO: implement MCP fetch)
→ Running Tier 1 check...
  Tier 1 Score: 100/100 [PASS]
→ Running Tier 2 check...
  Tier 2 Score: 85/100
→ Verdict: QUALIFIED
→ Fetching userId for nga.nguyen6@mservice.com.vn...
  ✓ Fetched from OIDC: nga.nguyen6@mservice.com.vn → 106660292106349566440
  ✓ userId: 106660292106349566440
→ Preparing Google Chat message...
→ Sending to Google Chat...
✅ Message sent to Google Chat!

======================================================================
Result: {
  "status": "success",
  "verdict": "QUALIFIED",
  "message": "Sent to Google Chat",
  "user_id": "106660292106349566440"
}
======================================================================
```

**Google Chat Received:**
```
🟢 Auto-Review: ✅ Đã duyệt (QUALIFIED)

👤 Creator: @nga.nguyen6  [user tagged]
📋 Campaign: AUTOTEST_20301026_phuclong_giam40k
🎯 Content Type: PROMOTION

📝 Nội dung:
Title: Giảm 40.000đ trà sữa Phúc Long
Body: Kính mời quý khách thưởng thức trà sữa Phúc Long với ưu đãi giảm 40.000đ. Tham gia ngay!

📊 Chấm điểm:
• Tier 1 (Script): 100/100 [PASS]
• Tier 2 (LLM): 85/100

🔍 Chi tiết:
{
  "tier1_issues": [],
  "tier2_issues": []
}
```

---

## ⚙️ Config & Constants

**Hardcoded Values (in auto_review.py):**
```python
GOOGLE_CHAT_WEBHOOK = os.environ.get("GOOGLE_CHAT_WEBHOOK", "")
AUTO_WEBHOOK_USERID = os.environ.get("AUTO_WEBHOOK_USERID", "")
OIDC_USERS_ENDPOINT = os.environ.get("OIDC_USERS_ENDPOINT", "https://oidc.mservice.io/google-users")

# Content types to review
PROMO_CTS = {"PROMOTION", "GAME", "ADVERTISING", "EVENT"}
INTERACTION_CTS = {"FRIEND", "BUSINESS_PAGE", "SOCIAL"}
TARGET_CTS = PROMO_CTS | INTERACTION_CTS

# Tier 2 thresholds
TIER2_PASS_THRESHOLD = 85        # ✅ QUALIFIED if >= 85
TIER2_MANUAL_THRESHOLD = 50      # ⚠️ WARNING if 50-84, else ❌ NOT_QUALIFIED
```

**Environment (DONE):**
- [x] `GOOGLE_CHAT_WEBHOOK` → env var (bắt buộc, không có thì skip gửi chat)
- [x] `AUTO_WEBHOOK_USERID` → env var
- [x] `OIDC_USERS_ENDPOINT` → env var (có default public endpoint)

---

## 🔄 Batch Mode (NEW - v1.2)

**Purpose:** Process multiple IN_REVIEW campaigns in one run

**Usage:**
```bash
# Batch mode with content type filter
python auto_review.py --batch

# Batch mode dry-run (don't send chat)
python auto_review.py --batch --dry-run

# Alias
python auto_review.py --from-mcp
```

**Batch Workflow:**
```
1. fetch_campaigns_from_mcp(status="IN_REVIEW")
   - Placeholder function
   - Ready for real MCP SDK integration
   - Falls back to local test files for now

2. filter_campaigns_by_content_type(campaigns, TARGET_CTS)
   - Only keeps: PROMOTION, GAME, ADVERTISING, EVENT
                 FRIEND, BUSINESS_PAGE, SOCIAL
   - Skips: SURVEY, other types

3. review_batch_campaigns(filtered_campaigns, dry_run)
   - Loops over each campaign
   - Calls _review_campaign_object() for each
   - Tracks results by verdict

4. Output summary
   - ✅ QUALIFIED count
   - ⚠️ WARNING count
   - 🔵 HITL_REQUIRED count
   - ❌ NOT_QUALIFIED count
   - ⚠️ ERROR count
```

**Example Output:**
```
======================================================================
AUTO-REVIEW BATCH MODE
======================================================================
→ Fetching campaigns from MCP (status=IN_REVIEW)...
→ Filtering by content type (Ưu đãi + Tương Tác)...
  ✓ 2 campaign(s) match criteria

======================================================================
Batch Review: 2 campaign(s)
======================================================================

[1/2] AUTOTEST_20301026_phuclong_giam40k
  Tier 1: 100/100 [PASS]
  Tier 2: 85/100
  Verdict: QUALIFIED
  ✅ Sent to Google Chat

[2/2] AUTOTEST_20301026_phuclong_giam40k
  Tier 1: 100/100 [PASS]
  Tier 2: 85/100
  Verdict: QUALIFIED
  ✅ Sent to Google Chat

======================================================================
SUMMARY:
  ✅ QUALIFIED: 2
  ⚠️  WARNING: 0
  🔵 HITL_REQUIRED: 0
  ❌ NOT_QUALIFIED: 0
  ⚠️  ERROR: 0
======================================================================
```

---

## 🚀 Scheduler (Not Yet Implemented)

**Current:** Manual execution via command line or batch mode

**Planned:**
```bash
# Option A: Cron job (Linux/Mac)
0 * * * * cd /path/to/project && python auto_review.py

# Option B: Windows Task Scheduler
# Task: Run every 1 hour → python auto_review.py

# Option C: Google Cloud Scheduler
# Frequency: Every 1 hour
# HTTP: POST to Cloud Function / App Engine endpoint
```

**TODO:**
- [ ] Loop over `list_campaigns(status=IN_REVIEW)` via MCP
- [ ] Filter by `content_type in TARGET_CTS`
- [ ] Call `review_single_campaign()` for each
- [ ] Collect results (verdicts, errors)
- [ ] Log summary to file

---

## ✅ Current Status vs TODO

**✅ Implemented (v1.2):**
- [x] Single campaign review end-to-end
- [x] Tier 1 check (via tier1_check.py)
- [x] Tier 2 simulation
- [x] Verdict logic (4-way decision)
- [x] OIDC user ID lookup + caching
- [x] Google Chat webhook integration
- [x] User mention with numeric ID
- [x] Dry-run mode
- [x] Error handling
- [x] **Batch mode: process multiple campaigns**
- [x] **Content type filter (Ưu đãi + Tương Tác only)**
- [x] **MCP integration placeholder** (ready for implementation)

**⏳ TODO:**
- [ ] Real MCP integration: `list_campaigns(state=IN_REVIEW)` via SDK
- [ ] Auto-approve logic (QUALIFIED → send approval to MCP)
- [ ] Scheduler setup (cron / CloudScheduler)
- [ ] Logging to file (not just stdout)
- [ ] Retry logic for API failures
- [ ] Monitoring & alerting
- [ ] Real Tier 2 LLM Judge (replace simulation)

---

## 🔗 Files & Dependencies

```
noti-campaign-approval-bmc/
├── auto_review.py              ← Main automation script
├── scripts/
│   ├── tier1_check.py          ← Tier 1 scoring
│   ├── rules.py                ← Rule helpers (character count, etc)
├── campaign_*.json             ← Test campaign files
└── install_v1.11.0/
    └── auto-review/
        ├── auto_review.py      ← Copy of main script
        ├── README.md
        ├── WORKFLOW.md
```

---

**Last Updated:** 2026-09-08  
**Version:** v1.1 (OIDC Integration Complete)
