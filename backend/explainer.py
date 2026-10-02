"""SHAP-based deal risk explainer — top reasons why a deal is at risk."""
import shap
import numpy as np
import pandas as pd


def explain_deal_risk(model, X: pd.DataFrame, deal_idx: int, feature_names: list[str]) -> list[dict]:
    """Return top 5 SHAP-based reasons for a single deal's risk score."""
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)

    if isinstance(shap_values, list):
        # Binary classification: use class-1 SHAP values
        sv = shap_values[1][deal_idx]
    else:
        sv = shap_values[deal_idx]

    feature_impacts = list(zip(feature_names, sv, X.iloc[deal_idx].values))
    feature_impacts.sort(key=lambda x: abs(x[1]), reverse=True)

    reasons = []
    for feat, impact, value in feature_impacts[:5]:
        direction = "increases" if impact > 0 else "decreases"
        reasons.append({
            "feature": _human_name(feat),
            "value": _format_value(feat, value),
            "impact": round(float(impact), 3),
            "direction": direction,
            "explanation": _explain_feature(feat, value, impact),
        })
    return reasons


def explain_batch(model, X: pd.DataFrame, feature_names: list[str]) -> dict[int, list[dict]]:
    """Explain all deals. Returns {row_idx: [reasons]}."""
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)

    if isinstance(shap_values, list):
        sv = shap_values[1]
    else:
        sv = shap_values

    result = {}
    for idx in range(len(X)):
        impacts = list(zip(feature_names, sv[idx], X.iloc[idx].values))
        impacts.sort(key=lambda x: abs(x[1]), reverse=True)
        result[idx] = [
            {
                "feature": _human_name(f),
                "value": _format_value(f, v),
                "impact": round(float(imp), 3),
                "explanation": _explain_feature(f, v, imp),
            }
            for f, imp, v in impacts[:3]
        ]
    return result


FEATURE_LABELS = {
    "stage_age_days": "Stage Age",
    "days_since_last_activity": "Days Since Last Activity",
    "email_count_30d": "Emails (Last 30d)",
    "champion_reply_gap_days": "Champion Silence (Days)",
    "competitor_mentions": "Competitor Mentions",
    "meeting_count": "Meetings Held",
    "call_count": "Calls Made",
    "sentiment_score_avg": "Avg Email Sentiment",
    "stakeholder_count": "Stakeholders Engaged",
    "discount_requested": "Discount Requested (%)",
    "legal_review_started": "Legal Review Started",
    "close_date_pushed_count": "Close Date Pushed",
    "amount": "Deal Amount",
    "stage_encoded": "Pipeline Stage",
    "owner_win_rate": "Rep Win Rate",
    "account_deal_count": "Account Deal Count",
    "days_to_close": "Days to Close",
}


def _human_name(feat: str) -> str:
    return FEATURE_LABELS.get(feat, feat.replace("_", " ").title())


def _format_value(feat: str, val) -> str:
    if feat == "amount":
        return f"₹{val/100000:.1f}L"
    if feat in ("sentiment_score_avg", "owner_win_rate"):
        return f"{val:.2f}"
    return str(int(val)) if isinstance(val, (float, np.floating)) and val == int(val) else str(round(float(val), 1))


def _explain_feature(feat: str, val, impact: float) -> str:
    templates = {
        "champion_reply_gap_days": f"Champion hasn't replied in {int(val)} days",
        "competitor_mentions": f"Competitor mentioned {int(val)} times in emails",
        "close_date_pushed_count": f"Close date pushed {int(val)} time(s)",
        "days_since_last_activity": f"No activity for {int(val)} days",
        "sentiment_score_avg": f"Average email sentiment is {'negative' if val < 0 else 'neutral' if val < 0.3 else 'positive'} ({val:.2f})",
        "email_count_30d": f"Only {int(val)} emails in last 30 days",
        "meeting_count": f"{'Only' if val < 3 else ''} {int(val)} meetings held",
        "discount_requested": f"Discount of {val:.1f}% requested",
        "owner_win_rate": f"Rep win rate is {val:.0%}",
        "stage_age_days": f"Deal has been in current stage for {int(val)} days",
    }
    return templates.get(feat, f"{_human_name(feat)} = {_format_value(feat, val)}")
