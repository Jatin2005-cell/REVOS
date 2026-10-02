"""Next-Best-Action ranker — for each at-risk deal, rank candidate actions by expected impact."""
from dataclasses import dataclass

CANDIDATE_ACTIONS = [
    {
        "action": "Call champion directly",
        "base_impact": 0.25,
        "triggers": ["champion_reply_gap_days", "days_since_last_activity"],
        "priority": "high",
    },
    {
        "action": "Email economic buyer with ROI deck",
        "base_impact": 0.20,
        "triggers": ["amount", "stage_encoded"],
        "priority": "high",
    },
    {
        "action": "Schedule technical demo for stakeholders",
        "base_impact": 0.18,
        "triggers": ["stakeholder_count", "meeting_count"],
        "priority": "medium",
    },
    {
        "action": "Send competitive comparison deck",
        "base_impact": 0.22,
        "triggers": ["competitor_mentions"],
        "priority": "high",
    },
    {
        "action": "Offer time-limited discount",
        "base_impact": 0.15,
        "triggers": ["discount_requested", "close_date_pushed_count"],
        "priority": "medium",
    },
    {
        "action": "Escalate to sales manager for executive alignment",
        "base_impact": 0.12,
        "triggers": ["stage_age_days", "close_date_pushed_count"],
        "priority": "low",
    },
    {
        "action": "Re-engage with a case study relevant to their industry",
        "base_impact": 0.16,
        "triggers": ["sentiment_score_avg", "email_count_30d"],
        "priority": "medium",
    },
    {
        "action": "Schedule executive sponsor call",
        "base_impact": 0.19,
        "triggers": ["amount", "champion_reply_gap_days"],
        "priority": "high",
    },
]


def rank_actions(deal_features: dict, risk_reasons: list[dict]) -> list[dict]:
    """Rank NBAs for a deal based on its risk factors and feature values."""
    triggered_features = {r["feature"] for r in risk_reasons}
    # Map human names back to feature keys for matching
    reverse_map = {
        "Champion Silence (Days)": "champion_reply_gap_days",
        "Days Since Last Activity": "days_since_last_activity",
        "Competitor Mentions": "competitor_mentions",
        "Close Date Pushed": "close_date_pushed_count",
        "Emails (Last 30d)": "email_count_30d",
        "Avg Email Sentiment": "sentiment_score_avg",
        "Deal Amount": "amount",
        "Pipeline Stage": "stage_encoded",
        "Meetings Held": "meeting_count",
        "Stakeholders Engaged": "stakeholder_count",
        "Discount Requested (%)": "discount_requested",
        "Stage Age": "stage_age_days",
    }
    triggered_keys = {reverse_map.get(f, f) for f in triggered_features}

    scored = []
    for action in CANDIDATE_ACTIONS:
        # Boost if action targets a triggered risk factor
        relevance = sum(1 for t in action["triggers"] if t in triggered_keys)
        score = action["base_impact"] * (1 + relevance * 0.5)

        # Boost high-risk, high-value deals
        if deal_features.get("amount", 0) > 2000000:
            score *= 1.15
        if deal_features.get("champion_reply_gap_days", 0) > 14:
            score *= 1.1

        reason = _build_reason(action, deal_features, triggered_keys)

        scored.append({
            "action": action["action"],
            "score": round(score, 3),
            "reason": reason,
            "expected_impact": f"+{score*100:.0f}% win probability",
            "priority": action["priority"],
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    for i, item in enumerate(scored):
        item["rank"] = i + 1

    return scored[:5]  # Top 5 actions


def _build_reason(action: dict, features: dict, triggered: set) -> str:
    """Generate a contextual reason for the action."""
    triggers = action["triggers"]
    parts = []
    if "champion_reply_gap_days" in triggers and features.get("champion_reply_gap_days", 0) > 7:
        parts.append(f"champion hasn't replied in {features['champion_reply_gap_days']} days")
    if "competitor_mentions" in triggers and features.get("competitor_mentions", 0) > 0:
        parts.append(f"competitor mentioned {features['competitor_mentions']}x")
    if "close_date_pushed_count" in triggers and features.get("close_date_pushed_count", 0) > 0:
        parts.append(f"close date pushed {features['close_date_pushed_count']}x")
    if "days_since_last_activity" in triggers and features.get("days_since_last_activity", 0) > 7:
        parts.append(f"no activity for {features['days_since_last_activity']} days")
    if "sentiment_score_avg" in triggers and features.get("sentiment_score_avg", 0) < 0.2:
        parts.append("email sentiment is low")
    if "email_count_30d" in triggers and features.get("email_count_30d", 0) < 3:
        parts.append(f"only {features['email_count_30d']} emails in last 30 days")
    if "meeting_count" in triggers and features.get("meeting_count", 0) < 2:
        parts.append(f"only {features['meeting_count']} meetings held")
    if "stakeholder_count" in triggers and features.get("stakeholder_count", 0) < 2:
        parts.append("limited stakeholder engagement")

    return "; ".join(parts) if parts else "Proactive engagement recommended based on deal profile"
