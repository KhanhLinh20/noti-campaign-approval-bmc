# Auto-Review Results Format (v1.2)

> Kết quả review campaigns được trả ra theo cấu trúc chi tiết, bao gồm: Table view, JSON, và CSV export

---

## 📊 Output Formats

Khi chạy batch mode, kết quả được trả ra dưới 3 hình thức:

### 1. **Table View (Console)**
```
┌──────────────────────────────────────────────────────────────┐
│ CAMPAIGN                       │ TYPE         │ T1  │ T2  │ STATUS
├──────────────────────────────────────────────────────────────┤
│ AUTOTEST_20301026_phuclong_gia │ PROMOTION    │ 100 │  85 │ QUALIFIED
│ OTHER_CAMPAIGN_2               │ FRIEND       │  90 │  72 │ WARNING
└──────────────────────────────────────────────────────────────┘
```

### 2. **JSON Output (Console + stdout)**
```json
{
  "total": 2,
  "summary": {
    "QUALIFIED": 1,
    "WARNING": 1
  },
  "records": [
    {
      "campaign_name": "AUTOTEST_20301026_phuclong_giam40k",
      "content_type": "PROMOTION",
      "service_group": "miniapp",
      "segment_name": "260513_test_la_realtime_001",
      "segment_size": "3",
      "push_time": "1919232000000",
      "title": "Giảm 40.000đ trà sữa Phúc Long",
      "body": "Kính mời quý khách thưởng thức trà sữa Phúc Long...",
      "ref_id": "miniapp_partner",
      "tier1_score": 100,
      "tier2_score": 85,
      "status": "QUALIFIED",
      "comments": "Tier 1: 100/100 [PASS] | Tier 2: 85/100 (simulated) | Verdict: QUALIFIED | ✅ Sent to Google Chat"
    }
  ]
}
```

### 3. **CSV File (Auto-exported)**
**File:** `auto-review-results_YYYYMMDD_HHMMSS.csv`

```csv
campaign_name,content_type,service_group,segment_name,segment_size,push_time,title,body,ref_id,tier1_score,tier2_score,status,comments
AUTOTEST_20301026_phuclong_giam40k,PROMOTION,miniapp,260513_test_la_realtime_001,3,1919232000000,Giảm 40.000đ trà sữa Phúc Long,Kính mời quý khách...,miniapp_partner,100,85,QUALIFIED,"Tier 1: 100/100 [PASS] | Tier 2: 85/100 | Verdict: QUALIFIED | ✅ Sent"
```

---

## 📝 Result Record Fields

Mỗi campaign review sinh ra **1 record** với các field:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `campaign_name` | string | Tên campaign | `AUTOTEST_20301026_phuclong_giam40k` |
| `content_type` | string | Loại nội dung | `PROMOTION`, `FRIEND`, etc |
| `service_group` | string | Service category | `miniapp`, `web`, etc |
| `segment_name` | string | Segment name | `260513_test_la_realtime_001` |
| `segment_size` | string | Segment size (người nhận) | `3`, `1000`, etc |
| `push_time` | string | Thời gian push (ms) | `1919232000000` |
| `title` | string | Tiêu đề notification | `Giảm 40.000đ trà sữa Phúc Long` |
| `body` | string | Nội dung notification | `Kính mời quý khách...` |
| `ref_id` | string | Reference ID | `miniapp_partner` |
| `tier1_score` | int | Tier 1 score (0-100) | `100` |
| `tier2_score` | int | Tier 2 score (0-100) | `85` |
| `status` | string | Verdict | `QUALIFIED`, `WARNING`, etc |
| `comments` | string | Scoring log comments | `Tier 1: 100/100 [PASS] \| Tier 2: 85/100...` |

---

## 🎯 Status Meanings

| Status | Emoji | Meaning | Action |
|--------|-------|---------|--------|
| **QUALIFIED** | ✅ 🟢 | Approved automatically | Ready to push |
| **WARNING** | ⚠️ 🟡 | Needs manual review | Send to reviewer |
| **HITL_REQUIRED** | 🔄 🔵 | Must manually approve | Route to team |
| **NOT_QUALIFIED** | ❌ 🔴 | Rejected | Return to creator |
| **ERROR** | ⚠️ ⚠️ | Processing error | Check logs |

---

## 📋 Comments Field Breakdown

Mỗi record có `comments` là tổng hợp của:

```
Tier 1: {score}/100 [{band}] 
| Tier 2: {score}/100 (simulated) 
| Verdict: {status} 
| ✅ Sent to Google Chat
```

**Ví dụ:**
```
Tier 1: 100/100 [PASS] | Tier 2: 85/100 (simulated) | Verdict: QUALIFIED | ✅ Sent to Google Chat
```

Nếu có issues từ Tier 1:
```
Tier 1: 60/100 [FAIL] | Issue: Title 41 ký tự (vượt quá 30) | Tier 2: 0/100 | Verdict: NOT_QUALIFIED | ✅ Sent to Google Chat
```

---

## 🔍 Content Type Filtering

Chỉ những campaigns với content_type sau được xử lý:

**Ưu đãi (Promotion):**
- `PROMOTION` — Khuyến mãi
- `GAME` — Game/Challenge
- `ADVERTISING` — Quảng cáo
- `EVENT` — Sự kiện

**Tương Tác (Interaction):**
- `FRIEND` — Friend interaction
- `BUSINESS_PAGE` — Business page
- `SOCIAL` — Social features

**Bỏ qua:**
- `SURVEY`, `AWARENESS`, `OTHERS` — Không xử lý tự động

---

## 📤 Usage Examples

### Example 1: Batch mode with dry-run
```bash
python auto_review.py --batch --dry-run
```

**Output:**
- Console: Table + Summary
- JSON: Full results
- CSV: Generated (not sent to chat)

---

### Example 2: Batch mode (production)
```bash
python auto_review.py --batch
```

**Output:**
- Console: Table + Summary
- JSON: Full results with "success" status
- CSV: Generated
- Google Chat: Messages sent to creators ✅

---

### Example 3: Single campaign
```bash
python auto_review.py --campaign-name phuclong_giam40k
```

**Output:**
- Console: Single campaign review
- No batch summary
- No CSV export

---

## 📊 Batch Result Summary Structure

```json
{
  "total": 10,                    // Total campaigns reviewed
  "summary": {
    "QUALIFIED": 7,
    "WARNING": 2,
    "HITL_REQUIRED": 1,
    "NOT_QUALIFIED": 0,
    "ERROR": 0
  },
  "records": [
    { record1 },
    { record2 },
    ...
  ]
}
```

---

## 💾 CSV File Details

**Filename Format:** `auto-review-results_YYYYMMDD_HHMMSS.csv`

**Location:** Same directory as script

**Encoding:** UTF-8

**Columns:** 13 columns (see table above)

**Import to Excel:**
1. Open Excel
2. File → Open → Select CSV
3. Choose UTF-8 encoding
4. Ready to filter/sort

---

## 🎯 Filter & Sort in CSV

**Excel:**
- Add AutoFilter: Data → AutoFilter
- Filter by status: Sort by QUALIFIED only
- Sort by score: Descending Tier 1 score

**Google Sheets:**
- Upload CSV
- Use FILTER function
- Create pivot table for summary

---

## 📈 Metrics

Sau khi batch review xong, có thể tính:

```
Pass Rate = QUALIFIED / Total * 100%
Manual Review Rate = (WARNING + HITL_REQUIRED) / Total * 100%
Reject Rate = NOT_QUALIFIED / Total * 100%
Error Rate = ERROR / Total * 100%

Average Tier 1 Score = SUM(tier1_score) / count
Average Tier 2 Score = SUM(tier2_score) / count
```

---

## 🔄 Workflow Integration

**Scheduler → Batch Mode → Results:**
```
Cron job (hourly)
  ↓
python auto_review.py --batch
  ↓
- Console output (for monitoring)
- JSON output (for logging)
- CSV file (for reporting)
- Google Chat messages (for creators)
```

---

## 🚀 Future Enhancements

- [ ] Database logging (SQLite / BigQuery)
- [ ] Email summary report
- [ ] Dashboard with charts
- [ ] Slack integration for summary
- [ ] Automated approval to MCP (QUALIFIED only)
- [ ] Real Tier 2 LLM Judge (replace simulation)

---

**Last Updated:** 2026-09-08  
**Version:** v1.2 (Detailed Results + CSV Export)
