#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Auto-review Noti Campaign workflow — review & approve/reject → Google Chat notification

Usage:
    python auto_review.py [--dry-run] [--campaign-name "CAMPAIGN_NAME"]

Config:
    - Content Types: PROMOTION, GAME, ADVERTISING, EVENT (Ưu đãi)
                     FRIEND, BUSINESS_PAGE, SOCIAL (Tương Tác)
    - Status: IN_REVIEW only
    - Auto-approve if: Tier1 PASS + Tier2 score >= 85 + not Quan Trọng/SURVEY
    - Auto-reject if: Tier1 FAIL or Tier2 score < 50
    - Manual review: Tier2 score 50-84 or HITL triggered
"""
import json
import os
import subprocess
import sys
from typing import Optional

# Fix stdout encoding for Windows (support Vietnamese characters)
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# ============================================================================
# CONFIG
# ============================================================================

# Secrets come from the environment (see .env.example). Never hardcode webhooks here.
GOOGLE_CHAT_WEBHOOK = os.environ.get("GOOGLE_CHAT_WEBHOOK", "")
AUTO_WEBHOOK_USERID = os.environ.get("AUTO_WEBHOOK_USERID", "")
OIDC_USERS_ENDPOINT = os.environ.get("OIDC_USERS_ENDPOINT", "https://oidc.mservice.io/google-users")

# Local cache for user IDs (to avoid repeated API calls)
USER_ID_CACHE = {}

# Content types to review (Ưu đãi + Tương tác)
PROMO_CTS = {"PROMOTION", "GAME", "ADVERTISING", "EVENT"}
INTERACTION_CTS = {"FRIEND", "BUSINESS_PAGE", "SOCIAL"}
TARGET_CTS = PROMO_CTS | INTERACTION_CTS

TIER2_PASS_THRESHOLD = 85
TIER2_MANUAL_THRESHOLD = 50

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def fetch_campaigns_from_mcp(status: str = "IN_REVIEW") -> Optional[list]:
    """Fetch campaigns from MCP (Noti Campaign Manager).

    Returns: List of campaign objects, or None if error
    """
    try:
        # TODO: Replace with actual MCP call when SDK available
        # For now, return empty (placeholder)
        print(f"  ⚠️  MCP integration not yet implemented")
        print(f"     Would fetch: list_campaigns(status='{status}')")
        return None
    except Exception as e:
        print(f"❌ Error fetching campaigns from MCP: {e}", file=sys.stderr)
        return None


def extract_campaign_details(campaign: dict) -> dict:
    """Extract all campaign details for result record.

    Returns: Dict with all campaign metadata
    """
    variants = campaign.get("variants", {})
    control = variants.get("control", {})
    notification_ref = control.get("notification_reference", {}) or campaign.get("notification_reference", {})
    service_cat = campaign.get("service_category", {})
    segment = campaign.get("segment", {})
    schedule = campaign.get("schedule_config", {})

    return {
        "campaign_name": campaign.get("name", ""),
        "content_type": notification_ref.get("content_type", ""),
        "service_group": service_cat.get("service_group", ""),
        "segment_name": segment.get("name", ""),
        "segment_size": segment.get("size", ""),
        "push_time": schedule.get("push_time", ""),
        "title": control.get("caption", ""),
        "body": control.get("body", ""),
        "ref_id": notification_ref.get("ref_id", ""),
        "group": notification_ref.get("group", ""),
    }


def format_result_record(campaign: dict, tier1: dict, tier2: dict, verdict: str, comments: list) -> dict:
    """Format campaign review result as detailed record.

    Returns: Dict with all details for output
    """
    details = extract_campaign_details(campaign)

    return {
        "campaign_name": details["campaign_name"],
        "content_type": details["content_type"],
        "service_group": details["service_group"],
        "segment_name": details["segment_name"],
        "segment_size": details["segment_size"],
        "push_time": details["push_time"],
        "title": details["title"],
        "body": details["body"],
        "ref_id": details["ref_id"],
        "tier1_score": tier1.get("tier1_score", 0),
        "tier2_score": tier2.get("score", 0),
        "status": verdict,
        "comments": " | ".join(comments) if comments else ""
    }


def filter_campaigns(campaigns: list, target_types: set, name_prefix: str = "AUTOTEST_", max_segment_size: int = 10) -> list:
    """Filter campaigns by multiple conditions.

    Conditions:
    1. Content type in target_types (PROMOTION, GAME, ADVERTISING, EVENT, FRIEND, BUSINESS_PAGE, SOCIAL)
    2. Campaign name starts with name_prefix (default: AUTOTEST_)
    3. Segment size < max_segment_size (default: 10)
    """
    if not campaigns:
        return []

    filtered = []
    for campaign in campaigns:
        campaign_name = campaign.get("name", "Unknown")
        content_type = campaign.get("notification_reference", {}).get("content_type", "")
        segment_size_str = campaign.get("segment", {}).get("size", "0")

        # Try to convert segment size to int
        try:
            segment_size = int(segment_size_str)
        except (ValueError, TypeError):
            segment_size = 0

        # Check all conditions
        reasons = []

        # Condition 1: Content type
        if content_type not in target_types:
            reasons.append(f"content_type={content_type} (not in target)")

        # Condition 2: Name prefix
        if not campaign_name.startswith(name_prefix):
            reasons.append(f"name doesn't start with '{name_prefix}'")

        # Condition 3: Segment size
        if segment_size >= max_segment_size:
            reasons.append(f"segment_size={segment_size} (≥ {max_segment_size})")

        if not reasons:
            # All conditions passed
            filtered.append(campaign)
        else:
            # Skip with reason
            print(f"  ⊘ Skipped {campaign_name}: {' | '.join(reasons)}")

    return filtered


def run_tier1_check(campaign_json: dict) -> dict:
    """Run Tier 1 check via tier1_check.py script."""
    try:
        result = subprocess.run(
            ["python", "scripts/tier1_check.py"],
            input=json.dumps({"campaign": campaign_json}),
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            return {"error": f"Tier 1 script failed: {result.stderr}"}
        return json.loads(result.stdout)
    except Exception as e:
        return {"error": f"Tier 1 check error: {str(e)}"}


def simulate_tier2_check(tier1_result: dict, campaign: dict) -> dict:
    """Simulate Tier 2 LLM Judge (placeholder for now).

    In production, this would call LLM Judge with proper prompts.
    For now, return synthetic score based on Tier 1 + simple heuristics.
    """
    if not tier1_result.get("passed"):
        return {"score": 0, "hitl_triggered": False, "issues": []}

    # Simple heuristic: if Tier 1 passes, assume decent quality
    # In production, actually run LLM Judge here
    title = campaign.get("variants", {}).get("control", {}).get("caption", "")
    body = campaign.get("variants", {}).get("control", {}).get("body", "")

    score = 90  # Default good score if T1 passes

    # Reduce if no personalization
    if "${" not in title and "${" not in body:
        score -= 5

    # Reduce if generic wording
    if any(x in body.lower() for x in ["hay", "có", "thử xem"]):
        score -= 10

    return {
        "score": score,
        "hitl_triggered": False,
        "issues": [],
        "note": "Simulated Tier 2 (placeholder)"
    }


def extract_username_from_email(email: str) -> str:
    """Extract username from email address.

    Example: nga.nguyen6@mservice.com.vn → nga.nguyen6
    """
    if "@" in email:
        return email.split("@")[0]
    return email


def format_user_mention(email: str, user_id: Optional[str] = None) -> str:
    """Format user mention for Google Chat.

    Priority:
    1. If user_id available → <users/numeric-id>
    2. Otherwise → <users/email@domain>
    """
    if user_id:
        return f"<users/{user_id}>"
    else:
        return f"<users/{email}>"


def format_chat_message(campaign: dict, tier1: dict, tier2: dict, verdict: str, creator_email: str, user_id: Optional[str] = None, comments: list = None) -> dict:
    """Format Google Chat message with full campaign details + comments log.

    Gửi vào group với tag creator + tất cả chi tiết campaign.
    """
    if comments is None:
        comments = []

    campaign_name = campaign.get("name", "Unknown")
    content_type = campaign.get("notification_reference", {}).get("content_type", "")
    service_group = campaign.get("service_category", {}).get("service_group", "")
    segment = campaign.get("segment", {})
    segment_name = segment.get("name", "")
    segment_size = segment.get("size", "")

    title = campaign.get("variants", {}).get("control", {}).get("caption", "")
    body = campaign.get("variants", {}).get("control", {}).get("body", "")
    ref_id = campaign.get("variants", {}).get("control", {}).get("notification_reference", {}).get("ref_id", "")

    schedule = campaign.get("schedule_config", {})
    push_time = schedule.get("push_time", "")

    # Verdict emoji + color
    verdict_emoji = {
        "QUALIFIED": "🟢",
        "WARNING": "🟡",
        "HITL_REQUIRED": "🔵",
        "NOT_QUALIFIED": "🔴"
    }.get(verdict, "⚪")

    verdict_text = {
        "QUALIFIED": "✅ Đã duyệt (QUALIFIED)",
        "WARNING": "⚠️ Cảnh báo (WARNING)",
        "HITL_REQUIRED": "🔄 Chờ xử lý thủ công (HITL)",
        "NOT_QUALIFIED": "❌ Từ chối (NOT_QUALIFIED)"
    }.get(verdict, "❓ Unknown")

    # Creator mention: use <users/...> format (with ID)
    creator_mention = format_user_mention(creator_email, user_id)

    # Format comments log
    comments_text = "\n".join(f"  • {c}" for c in comments) if comments else "  (no comments)"

    # Build message
    message = {
        "text": f"""{verdict_emoji} *Auto-Review: {verdict_text}*

👤 Creator: {creator_mention}
📋 Campaign: {campaign_name}
🎯 Content: {content_type} | Service: {service_group}
📊 Segment: {segment_name} (size: {segment_size})
⏰ Push Time: {push_time}
🔗 Ref ID: {ref_id}

📝 *Nội dung Notification:*
Title: {title}
Body: {body}

📊 *Điểm Số:*
• Tier 1: {tier1.get('tier1_score', 'N/A')}/100 [{tier1.get('tier1_band', 'N/A')}]
• Tier 2: {tier2.get('score', 'N/A')}/100

💬 *Log Chấm Điểm:*
{comments_text}
"""
    }

    return message


def determine_verdict(tier1: dict, tier2: dict, group: str) -> str:
    """Determine final verdict based on Tier 1 + Tier 2 scores."""

    # Tier 1 hard block → NOT_QUALIFIED
    if tier1.get("hard_block"):
        return "NOT_QUALIFIED"

    # Tier 1 or Tier 2 HITL → HITL_REQUIRED
    if tier1.get("hitl_required") or tier2.get("hitl_triggered"):
        return "HITL_REQUIRED"

    tier2_score = tier2.get("score", 0)

    # Score < 50 → NOT_QUALIFIED
    if tier2_score < TIER2_MANUAL_THRESHOLD:
        return "NOT_QUALIFIED"

    # Score 50-84 → WARNING (manual review needed)
    if tier2_score < TIER2_PASS_THRESHOLD:
        return "WARNING"

    # Score >= 85 + not Quan Trọng + not SURVEY → QUALIFIED
    if group != "Quan trọng" and group != "SURVEY":
        return "QUALIFIED"

    # Quan trọng/SURVEY even with high score → HITL (human approval needed)
    return "HITL_REQUIRED"


def get_user_id_by_email(email: str) -> Optional[str]:
    """Get userId from OIDC endpoint (MoMo google-users API).

    Priority:
    1. Check local cache
    2. Call OIDC endpoint: https://oidc.mservice.io/google-users?emails=[email]
    3. Return None if not found
    """
    # Check cache first
    if email in USER_ID_CACHE:
        user_id = USER_ID_CACHE[email]
        print(f"  ✓ Found in cache: {email} → {user_id}")
        return user_id

    # Try OIDC API
    try:
        import requests
        url = f"{OIDC_USERS_ENDPOINT}?emails={email}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Response format: {"email@domain": {"id": "numeric-id"}}
            user_data = data.get(email, {})
            user_id = user_data.get("id")
            if user_id:
                # Cache it
                USER_ID_CACHE[email] = user_id
                print(f"  ✓ Fetched from OIDC: {email} → {user_id}")
                return user_id
            else:
                print(f"⚠️  No user ID found for {email} in OIDC response", file=sys.stderr)
                return None
        else:
            print(f"⚠️  Failed to fetch from OIDC for {email}: {response.status_code}", file=sys.stderr)
            return None
    except Exception as e:
        print(f"⚠️  Error calling OIDC for {email}: {e}", file=sys.stderr)
        return None


def send_to_google_chat(message: dict) -> bool:
    """Send message to Google Chat webhook."""
    if not GOOGLE_CHAT_WEBHOOK:
        print("❌ GOOGLE_CHAT_WEBHOOK is not set (see .env.example)", file=sys.stderr)
        return False
    try:
        import requests
        response = requests.post(
            GOOGLE_CHAT_WEBHOOK,
            json=message,
            timeout=10
        )
        return response.status_code == 200
    except Exception as e:
        print(f"Failed to send Google Chat message: {e}", file=sys.stderr)
        return False


def review_batch_campaigns(campaigns: list, dry_run: bool = False) -> dict:
    """Review multiple campaigns (batch mode).

    Args:
        campaigns: List of campaign JSON objects
        dry_run: If True, don't actually send Google Chat messages

    Returns:
        Summary dict with detailed results
    """
    if not campaigns:
        return {"status": "empty", "message": "No campaigns to review", "records": []}

    print(f"\n{'='*70}")
    print(f"Batch Review: {len(campaigns)} campaign(s)")
    print('='*70)

    records = []  # Detailed result records

    for idx, campaign in enumerate(campaigns, 1):
        campaign_name = campaign.get("name", f"Campaign_{idx}")
        print(f"\n[{idx}/{len(campaigns)}] {campaign_name}")
        print("-" * 70)

        # Review this campaign (returns extended result with comments)
        result = _review_campaign_object(campaign, dry_run=dry_run)

        # Build detailed record
        record = format_result_record(
            campaign,
            result.get("tier1", {}),
            result.get("tier2", {}),
            result.get("verdict", "ERROR"),
            result.get("comments", [])
        )
        records.append(record)

    # Print detailed results table (console only)
    print(f"\n{'='*70}")
    print("DETAILED RESULTS:")
    print('='*70)
    print_results_table(records)

    # Print summary by verdict
    print(f"\n{'='*70}")
    print("SUMMARY BY STATUS:")
    verdict_counts = {}
    for record in records:
        status = record["status"]
        verdict_counts[status] = verdict_counts.get(status, 0) + 1

    for status in ["QUALIFIED", "WARNING", "HITL_REQUIRED", "NOT_QUALIFIED", "ERROR"]:
        count = verdict_counts.get(status, 0)
        if status == "QUALIFIED":
            print(f"  ✅ QUALIFIED: {count}")
        elif status == "WARNING":
            print(f"  ⚠️  WARNING: {count}")
        elif status == "HITL_REQUIRED":
            print(f"  🔵 HITL_REQUIRED: {count}")
        elif status == "NOT_QUALIFIED":
            print(f"  ❌ NOT_QUALIFIED: {count}")
        else:
            print(f"  ⚠️  ERROR: {count}")
    print('='*70)


    return {
        "total": len(campaigns),
        "summary": verdict_counts,
        "records": records
    }


def print_results_table(records: list):
    """Print results as formatted table (vertical layout).

    Shows: Campaign Name | Content Type | Service Group | Segment |
           Title | Tier1 Score | Tier2 Score | Status | Comments
    """
    if not records:
        print("No records to display")
        return

    # Print header
    print(f"\n{'┌' + '─'*150 + '┐'}")
    print(f"│ {'CAMPAIGN':<30} │ {'TYPE':<12} │ {'SERVICE':<15} │ {'T1':<3} │ {'T2':<3} │ {'STATUS':<15} │ {'COMMENTS':<60} │")
    print(f"├{'─'*150}┤")

    # Print rows
    for record in records:
        camp_name = record["campaign_name"][:30]
        content_type = record["content_type"][:12]
        service = record["service_group"][:15]
        t1 = str(record["tier1_score"])[:3]
        t2 = str(record["tier2_score"])[:3]
        status = record["status"][:15]
        comments = record["comments"][:60]

        print(f"│ {camp_name:<30} │ {content_type:<12} │ {service:<15} │ {t1:>3} │ {t2:>3} │ {status:<15} │ {comments:<60} │")

    print(f"└{'─'*150}┘")


def _review_campaign_object(campaign: dict, dry_run: bool = False) -> dict:
    """Review a single campaign object (internal helper).

    Args:
        campaign: Campaign JSON object (not file name)
        dry_run: If True, don't actually send Google Chat

    Returns:
        Result dict with verdict, tier1, tier2, and comments
    """
    campaign_name = campaign.get("name", "Unknown")
    creator_email = campaign.get("created_by", "unknown@mservice.com.vn")
    comments = []

    # Tier 1
    tier1 = run_tier1_check(campaign)
    if "error" in tier1:
        msg = f"Tier 1 error: {tier1['error']}"
        print(f"  ❌ {msg}")
        comments.append(msg)
        return {
            "status": "error",
            "verdict": "ERROR",
            "tier1": {},
            "tier2": {},
            "comments": comments,
            "message": tier1["error"]
        }

    tier1_score = tier1.get("tier1_score", 0)
    tier1_band = tier1.get("tier1_band", "UNKNOWN")
    print(f"  Tier 1: {tier1_score}/100 [{tier1_band}]")
    comments.append(f"Tier 1: {tier1_score}/100 [{tier1_band}]")

    # Add tier1 issues to comments
    if tier1.get("issues"):
        for issue in tier1.get("issues", [])[:2]:  # Max 2 issues
            issue_msg = issue.get("user_message", issue.get("message", "Unknown issue"))
            comments.append(f"  - {issue_msg}")

    # Tier 2
    tier2 = simulate_tier2_check(tier1, campaign)
    tier2_score = tier2.get("score", 0)
    print(f"  Tier 2: {tier2_score}/100")
    comments.append(f"Tier 2: {tier2_score}/100 (simulated)")

    # Verdict
    group = campaign.get("notification_reference", {}).get("group", "Unknown")
    verdict = determine_verdict(tier1, tier2, group)
    print(f"  Verdict: {verdict}")
    comments.append(f"Verdict: {verdict}")

    # Get user ID
    user_id = get_user_id_by_email(creator_email)

    # Format & send (with comments log)
    message = format_chat_message(campaign, tier1, tier2, verdict, creator_email, user_id, comments)

    if dry_run:
        print(f"  [DRY RUN] Would send to Google Chat")
        comments.append("[DRY RUN] Would send to Google Chat")
        return {
            "status": "dry_run",
            "verdict": verdict,
            "tier1": tier1,
            "tier2": tier2,
            "comments": comments,
            "message": "Not sent (dry-run)",
            "user_id": user_id
        }
    else:
        if send_to_google_chat(message):
            print(f"  ✅ Sent to Google Chat")
            comments.append("✅ Sent to Google Chat")
            return {
                "status": "success",
                "verdict": verdict,
                "tier1": tier1,
                "tier2": tier2,
                "comments": comments,
                "message": "Sent",
                "user_id": user_id
            }
        else:
            print(f"  ❌ Failed to send Google Chat")
            comments.append("❌ Failed to send Google Chat")
            return {
                "status": "error",
                "verdict": verdict,
                "tier1": tier1,
                "tier2": tier2,
                "comments": comments,
                "message": "Chat send failed",
                "user_id": user_id
            }


def review_single_campaign(campaign_name: str, dry_run: bool = False) -> dict:
    """Review 1 campaign end-to-end."""

    print(f"\n{'='*70}")
    print(f"Reviewing campaign: {campaign_name}")
    print('='*70)

    # Step 1: Fetch campaign from MCP
    # (In this test, we assume campaign data is passed)
    print("✓ Campaign fetched (TODO: implement MCP fetch)")

    # For testing, load from file
    try:
        with open(f"campaign_{campaign_name.lower()}.json", "r", encoding="utf-8") as f:
            campaign_data = json.load(f)
            campaign = campaign_data.get("campaign", campaign_data)
    except FileNotFoundError:
        print(f"❌ Campaign file not found: campaign_{campaign_name.lower()}.json")
        return {"status": "error", "message": "Campaign file not found"}

    creator_email = campaign.get("created_by", "unknown@mservice.com.vn")

    # Step 2: Run Tier 1
    print("→ Running Tier 1 check...")
    tier1 = run_tier1_check(campaign)
    if "error" in tier1:
        print(f"❌ Tier 1 error: {tier1['error']}")
        return {"status": "error", "message": tier1["error"]}

    print(f"  Tier 1 Score: {tier1.get('tier1_score')}/100 [{tier1.get('tier1_band')}]")
    if tier1.get("issues"):
        print(f"  Issues: {len(tier1['issues'])}")
        for issue in tier1["issues"][:3]:  # Show first 3
            print(f"    - {issue.get('user_message', issue.get('message', 'Unknown'))}")

    # Step 3: Run Tier 2 (or simulate)
    print("→ Running Tier 2 check...")
    tier2 = simulate_tier2_check(tier1, campaign)
    print(f"  Tier 2 Score: {tier2.get('score')}/100")

    # Step 4: Determine verdict
    group = campaign.get("notification_reference", {}).get("group", "Unknown")
    verdict = determine_verdict(tier1, tier2, group)
    print(f"→ Verdict: {verdict}")

    # Step 5: Fetch userId from webhook (if available)
    print(f"→ Fetching userId for {creator_email}...")
    user_id = get_user_id_by_email(creator_email)
    if user_id:
        print(f"  ✓ userId: {user_id}")
    else:
        print(f"  ⚠️  Could not fetch userId, will use email mention")

    # Step 6: Format & send to Google Chat (with comments log)
    print("→ Preparing Google Chat message...")
    comments = []
    comments.append(f"Tier 1: {tier1.get('tier1_score')}/100 [{tier1.get('tier1_band')}]")
    if tier1.get("issues"):
        for issue in tier1.get("issues", [])[:2]:
            issue_msg = issue.get("user_message", issue.get("message", "Unknown issue"))
            comments.append(f"  - {issue_msg}")
    comments.append(f"Tier 2: {tier2.get('score')}/100")
    comments.append(f"Verdict: {verdict}")

    message = format_chat_message(campaign, tier1, tier2, verdict, creator_email, user_id, comments)

    if dry_run:
        print("\n[DRY RUN] Would send to Google Chat:")
        print(json.dumps(message, indent=2, ensure_ascii=False))
        return {"status": "dry_run", "verdict": verdict, "message": "Not sent (dry-run mode)"}
    else:
        print("→ Sending to Google Chat...")
        if send_to_google_chat(message):
            print("✅ Message sent to Google Chat!")
            return {"status": "success", "verdict": verdict, "message": "Sent to Google Chat", "user_id": user_id}
        else:
            print("❌ Failed to send Google Chat message")
            return {"status": "error", "verdict": verdict, "message": "Failed to send chat"}


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Auto-review Noti Campaign workflow")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually send to Google Chat")
    parser.add_argument("--campaign-name", default=None,
                       help="Single campaign name to review (without .json suffix)")
    parser.add_argument("--batch", action="store_true",
                       help="Batch mode: fetch from MCP and review all IN_REVIEW campaigns")
    parser.add_argument("--from-mcp", action="store_true",
                       help="Alias for --batch (fetch from MCP)")

    args = parser.parse_args()

    # Determine mode
    if args.batch or args.from_mcp:
        # ========== BATCH MODE: Fetch from MCP ==========
        print(f"\n{'='*70}")
        print("AUTO-REVIEW BATCH MODE")
        print("="*70)

        print("→ Fetching campaigns from MCP (status=IN_REVIEW)...")
        campaigns = fetch_campaigns_from_mcp(status="IN_REVIEW")

        if campaigns is None:
            # MCP not implemented, try local test files
            print("  ℹ️  MCP not available, using local test files instead...")
            campaigns = [
                json.load(open(f"campaign_phuclong.json", encoding="utf-8")).get("campaign"),
                json.load(open(f"campaign_phuclong_phuong.json", encoding="utf-8")).get("campaign"),
                json.load(open(f"campaign_autotest_large.json", encoding="utf-8")).get("campaign"),  # Test: segment size = 15 (should be filtered)
            ]
            campaigns = [c for c in campaigns if c]  # Remove None

        print(f"→ Filtering campaigns by conditions:")
        print(f"   • Content type: Ưu đãi + Tương Tác")
        print(f"   • Name prefix: AUTOTEST_")
        print(f"   • Segment size: < 10")
        campaigns = filter_campaigns(campaigns, TARGET_CTS, name_prefix="AUTOTEST_", max_segment_size=10)
        print(f"  ✓ {len(campaigns)} campaign(s) match criteria")

        # Review all filtered campaigns
        result = review_batch_campaigns(campaigns, dry_run=args.dry_run)

        print(f"\n{'='*70}")
        print(f"Batch Result: {json.dumps(result, ensure_ascii=False, indent=2)}")
        print('='*70)

    else:
        # ========== SINGLE MODE: Review one campaign ==========
        campaign_name = args.campaign_name or "AUTOTEST_20301026_phuclong_giam40k"
        result = review_single_campaign(campaign_name, dry_run=args.dry_run)

        print(f"\n{'='*70}")
        print(f"Result: {json.dumps(result, ensure_ascii=False, indent=2)}")
        print('='*70)
