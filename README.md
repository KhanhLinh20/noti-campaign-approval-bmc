# Noti Campaign Auto-Review v1.2

Luồng tự động review & duyệt Noti Campaign hàng giờ, gửi kết quả lên Google Chat

## Setup

```bash
cp .env.example .env   # rồi điền GOOGLE_CHAT_WEBHOOK thật
export $(grep -v '^#' .env | xargs)   # hoặc set env var theo cách của bạn
```

Không có `GOOGLE_CHAT_WEBHOOK` thì script vẫn review được nhưng bỏ qua bước gửi chat.

## Quick Start

```bash
# Batch mode
python auto_review.py --batch

# Dry-run (không gửi chat)
python auto_review.py --batch --dry-run

# Single campaign
python auto_review.py --campaign-name CAMPAIGN_NAME
```

## Filter Conditions

Campaigns phải thỏa tất cả điều kiện:
- Content Type: Ưu đãi + Tương Tác
- Name starts with: AUTOTEST_
- Segment Size < 10

## Output

Google Chat message:
- 👤 Creator mention (OIDC user tag)
- 📋 Campaign details
- 📝 Notification content
- 📊 Tier 1 + Tier 2 scores
- 💬 Scoring log comments

## Files

- auto_review.py — Main script
- scripts/tier1_check.py — Tier 1 rules
- scripts/rules.py — Helpers
- WORKFLOW.md — Documentation
- RESULTS_FORMAT.md — Output format
- references/ — Rule details

## Version

v1.2 (2026-09-08)
