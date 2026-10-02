"""Compute 20+ features per deal from the revenue graph."""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from database import Deal, Activity, Email, CallTranscript, Contact, DealFeature, Account

NOW = datetime(2026, 10, 1)

STAGE_MAP = {
    "Discovery": 0, "Qualification": 1, "Proposal": 2,
    "Negotiation": 3, "Closed Won": 4, "Closed Lost": 5,
}


def compute_features(db: Session) -> pd.DataFrame:
    """Build one feature row per open deal."""
    deals = db.query(Deal).filter(Deal.is_closed == False).all()
    if not deals:
        deals = db.query(Deal).all()

    rows = []
    for deal in deals:
        created = datetime.combine(deal.created_date, datetime.min.time())
        close_dt = datetime.combine(deal.close_date, datetime.min.time())

        # Stage age
        stage_age = (NOW - created).days

        # Activities
        activities = db.query(Activity).filter(Activity.deal_id == deal.id).all()
        act_dates = [a.date for a in activities]
        days_since_last = (NOW - max(act_dates)).days if act_dates else 999

        # Emails in last 30 days
        cutoff_30d = NOW - timedelta(days=30)
        emails_30d = db.query(Email).filter(
            Email.deal_id == deal.id, Email.date >= cutoff_30d
        ).count()

        # Champion reply gap
        champion_contact = db.query(Contact).filter(
            Contact.id == deal.contact_id, Contact.is_champion == True
        ).first()
        champ_gap = 999
        if champion_contact:
            last_champ_email = (
                db.query(Email)
                .filter(Email.deal_id == deal.id, Email.contact_id == champion_contact.id, Email.direction == "inbound")
                .order_by(Email.date.desc())
                .first()
            )
            if last_champ_email:
                champ_gap = (NOW - last_champ_email.date).days

        # Competitor mentions
        comp_mentions = db.query(Email).filter(
            Email.deal_id == deal.id,
            Email.competitor_mentioned != "",
            Email.competitor_mentioned != None,
        ).count()

        # Meeting & call counts
        meeting_count = sum(1 for a in activities if a.activity_type == "meeting")
        call_count = db.query(CallTranscript).filter(CallTranscript.deal_id == deal.id).count()

        # Average email sentiment
        deal_emails = db.query(Email).filter(Email.deal_id == deal.id).all()
        sentiments = [e.sentiment for e in deal_emails if e.sentiment is not None]
        avg_sentiment = float(np.mean(sentiments)) if sentiments else 0.0

        # Stakeholder count (unique contacts emailed)
        stakeholders = db.query(Email.contact_id).filter(
            Email.deal_id == deal.id
        ).distinct().count()

        # Owner win rate
        owner_total = db.query(Deal).filter(Deal.owner == deal.owner, Deal.is_closed == True).count()
        owner_won = db.query(Deal).filter(Deal.owner == deal.owner, Deal.is_won == True).count()
        owner_win_rate = (owner_won / owner_total) if owner_total > 0 else 0.5

        # Account deal count
        acc_deals = db.query(Deal).filter(Deal.account_id == deal.account_id).count()

        # Days to close
        days_to_close = (close_dt - NOW).days

        rows.append({
            "deal_id": deal.id,
            "stage_age_days": stage_age,
            "days_since_last_activity": days_since_last,
            "email_count_30d": emails_30d,
            "champion_reply_gap_days": min(champ_gap, 999),
            "competitor_mentions": comp_mentions,
            "meeting_count": meeting_count,
            "call_count": call_count,
            "sentiment_score_avg": round(avg_sentiment, 3),
            "stakeholder_count": stakeholders,
            "discount_requested": deal.discount_requested or 0.0,
            "legal_review_started": deal.legal_review_started or False,
            "close_date_pushed_count": deal.close_date_pushed_count or 0,
            "amount": deal.amount,
            "stage_encoded": STAGE_MAP.get(deal.stage, 0),
            "owner_win_rate": round(owner_win_rate, 3),
            "account_deal_count": acc_deals,
            "days_to_close": days_to_close,
        })

    df = pd.DataFrame(rows)
    return df


def save_features_to_db(db: Session, df: pd.DataFrame):
    """Upsert feature rows into deal_features table."""
    for _, row in df.iterrows():
        existing = db.query(DealFeature).filter(DealFeature.deal_id == int(row["deal_id"])).first()
        if existing:
            for col in row.index:
                if col != "deal_id":
                    setattr(existing, col, row[col])
        else:
            feat = DealFeature(**row.to_dict())
            db.add(feat)
    db.commit()


def get_feature_matrix(db: Session) -> tuple[pd.DataFrame, list[str]]:
    """Return (X, feature_names) ready for ML."""
    df = compute_features(db)
    feature_cols = [
        "stage_age_days", "days_since_last_activity", "email_count_30d",
        "champion_reply_gap_days", "competitor_mentions", "meeting_count",
        "call_count", "sentiment_score_avg", "stakeholder_count",
        "discount_requested", "legal_review_started", "close_date_pushed_count",
        "amount", "stage_encoded", "owner_win_rate", "account_deal_count",
        "days_to_close",
    ]
    X = df[feature_cols].copy()
    X["legal_review_started"] = X["legal_review_started"].astype(int)
    return X, feature_cols, df["deal_id"]
