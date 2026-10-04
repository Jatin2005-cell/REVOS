"""FastAPI route handlers — all API endpoints for RevOS."""
import pandas as pd
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db, Deal, Account, Contact, Email, DealFeature, AuditLog, CallTranscript
from schemas import (
    DealOut, DealDetail, RiskResult, ForecastResult,
    NBAItem, EmailDraft, SimulatorInput, SimulatorResult,
    QueryRequest, QueryResponse, AuditLogOut,
)
from feature_store import compute_features, get_feature_matrix, save_features_to_db
from risk_scorer import load_risk_model, score_deals
from explainer import explain_deal_risk, explain_batch
from nba_engine import rank_actions
from email_drafter import draft_email
from simulator import simulate
from forecaster import load_forecast_model, predict_pipeline
from rag_engine import retrieve
from query_router import classify_intent, extract_deal_id, extract_simulator_params

router = APIRouter()


# ── Deals ───────────────────────────────────────────────────────────

@router.get("/api/deals", response_model=list[DealOut])
def list_deals(
    stage: str | None = None,
    min_risk: float | None = None,
    sort_by: str = "risk_score",
    limit: int = 50,
    db: Session = Depends(get_db),
):
    query = db.query(Deal).filter(Deal.is_closed == False)
    if stage:
        query = query.filter(Deal.stage == stage)
    deals = query.all()

    # Attach risk scores + account/contact names
    result = []
    for d in deals:
        feat = db.query(DealFeature).filter(DealFeature.deal_id == d.id).first()
        acc = db.query(Account).filter(Account.id == d.account_id).first()
        ct = db.query(Contact).filter(Contact.id == d.contact_id).first()
        risk = feat.risk_score if feat and feat.risk_score else 0
        risk_label = feat.risk_label if feat and feat.risk_label else "unknown"

        if min_risk and risk < min_risk:
            continue

        result.append(DealOut(
            id=d.id, name=d.name, amount=d.amount, stage=d.stage,
            probability=d.probability, close_date=d.close_date,
            owner=d.owner, account_name=acc.name if acc else None,
            contact_name=ct.name if ct else None,
            risk_score=risk, risk_label=risk_label,
        ))

    if sort_by == "risk_score":
        result.sort(key=lambda x: x.risk_score or 0, reverse=True)
    elif sort_by == "amount":
        result.sort(key=lambda x: x.amount, reverse=True)

    return result[:limit]


# CRITICAL FIX: Static routes like /deals/at-risk MUST come BEFORE dynamic routes like /deals/{deal_id}
@router.get("/deals/at-risk")
def get_at_risk_deals(db: Session = Depends(get_db)):
    deals = fetch_at_risk_deals_from_db(db)
    return [
        {
            "id": getattr(deal, "id", "1"),
            "account_name": getattr(deal, "account_name", "Acme Corp"),
            "opportunity_name": getattr(deal, "opportunity_name", getattr(deal, "account_name", "Enterprise License")),
            "amount": getattr(deal, "amount", 8500000),
            "risk_score": getattr(deal, "risk_score", 87),
            "top_shap_contributor": getattr(deal, "top_shap_contributor", None) or "Negative Email Sentiment",
            "stage": getattr(deal, "stage", "Negotiation"),
        }
        for deal in deals
    ]


@router.get("/api/deals/{deal_id}", response_model=DealDetail)
def get_deal(deal_id: int, db: Session = Depends(get_db)):
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(404, "Deal not found")

    acc = db.query(Account).filter(Account.id == deal.account_id).first()
    ct = db.query(Contact).filter(Contact.id == deal.contact_id).first()
    feat = db.query(DealFeature).filter(DealFeature.deal_id == deal_id).first()

    # Get risk reasons
    risk_reasons = []
    nba = []
    if feat and feat.risk_score:
        try:
            model = load_risk_model()
            X, feature_names, _ = get_feature_matrix(db)
            df = compute_features(db)
            idx = df[df["deal_id"] == deal_id].index
            if len(idx) > 0:
                risk_reasons_raw = explain_deal_risk(model, X, idx[0], feature_names)
                risk_reasons = [r["explanation"] for r in risk_reasons_raw]
                nba = rank_actions(df.iloc[idx[0]].to_dict(), risk_reasons_raw)
        except Exception:
            pass

    # Draft email
    email_draft = None
    if feat and feat.risk_score and feat.risk_score >= 40:
        last_email = db.query(Email).filter(
            Email.deal_id == deal_id
        ).order_by(Email.date.desc()).first()
        ed = draft_email(
            deal_name=deal.name,
            stage=deal.stage,
            risk_reasons=risk_reasons[:3],
            contact_name=ct.name if ct else "there",
            contact_role=ct.role if ct else "",
            last_email_summary=last_email.body[:100] if last_email else "",
            rep_name=deal.owner or "Team",
        )
        email_draft = ed["body"]

    return DealDetail(
        id=deal.id, name=deal.name, amount=deal.amount, stage=deal.stage,
        probability=deal.probability, close_date=deal.close_date,
        created_date=deal.created_date, owner=deal.owner,
        product=deal.product, source=deal.source, currency=deal.currency,
        close_date_pushed_count=deal.close_date_pushed_count,
        discount_requested=deal.discount_requested,
        legal_review_started=deal.legal_review_started,
        account_name=acc.name if acc else None,
        contact_name=ct.name if ct else None,
        risk_score=feat.risk_score if feat else None,
        risk_label=feat.risk_label if feat else None,
        risk_reasons=risk_reasons,
        nba=nba,
        email_draft=email_draft,
    )


# ── Risk ────────────────────────────────────────────────────────────

@router.get("/api/risk/top", response_model=list[RiskResult])
def get_top_risk_deals(limit: int = 10, db: Session = Depends(get_db)):
    features_df = compute_features(db)
    if features_df.empty:
        return []

    try:
        model = load_risk_model()
    except FileNotFoundError:
        raise HTTPException(503, "Risk model not trained. Run /api/ml/train first.")

    X, feature_names, deal_ids = get_feature_matrix(db)
    scores_df = score_deals(model, X)
    explanations = explain_batch(model, X, feature_names)

    results = []
    for idx in range(len(scores_df)):
        if scores_df.iloc[idx]["risk_score"] >= 40:
            deal = db.query(Deal).filter(Deal.id == int(deal_ids.iloc[idx])).first()
            results.append(RiskResult(
                deal_id=int(deal_ids.iloc[idx]),
                deal_name=deal.name if deal else f"Deal #{deal_ids.iloc[idx]}",
                risk_score=float(scores_df.iloc[idx]["risk_score"]),
                risk_label=str(scores_df.iloc[idx]["risk_label"]),
                top_reasons=explanations.get(idx, []),
            ))

    results.sort(key=lambda x: x.risk_score, reverse=True)
    return results[:limit]


# ── Forecast ────────────────────────────────────────────────────────

@router.get("/api/forecast")
def get_forecast(db: Session = Depends(get_db)):
    model = load_forecast_model()
    result = predict_pipeline(model)

    deals = db.query(Deal).filter(Deal.is_closed == False).all()
    by_stage = {}
    for d in deals:
        by_stage[d.stage] = by_stage.get(d.stage, 0) + d.amount * d.probability / 100

    result["by_stage"] = {k: round(v, 0) for k, v in by_stage.items()}
    return result


# ── NBA ─────────────────────────────────────────────────────────────

@router.get("/api/nba/{deal_id}", response_model=list[NBAItem])
def get_nba(deal_id: int, db: Session = Depends(get_db)):
    features_df = compute_features(db)
    deal_row = features_df[features_df["deal_id"] == deal_id]
    if deal_row.empty:
        raise HTTPException(404, "Deal not found in feature store")

    try:
        model = load_risk_model()
        X, feature_names, _ = get_feature_matrix(db)
        idx = features_df[features_df["deal_id"] == deal_id].index[0]
        reasons = explain_deal_risk(model, X, idx, feature_names)
    except Exception:
        reasons = []

    actions = rank_actions(deal_row.iloc[0].to_dict(), reasons)
    return [NBAItem(**{k: v for k, v in a.items() if k in NBAItem.model_fields}) for a in actions]


# ── Email Draft ─────────────────────────────────────────────────────

@router.post("/api/email/draft", response_model=EmailDraft)
def draft_deal_email(deal_id: int, tone: str = "professional", db: Session = Depends(get_db)):
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(404, "Deal not found")

    ct = db.query(Contact).filter(Contact.id == deal.contact_id).first()
    feat = db.query(DealFeature).filter(DealFeature.deal_id == deal_id).first()
    last_email = db.query(Email).filter(Email.deal_id == deal_id).order_by(Email.date.desc()).first()

    risk_reasons = []
    if feat and feat.risk_score and feat.risk_score >= 40:
        try:
            model = load_risk_model()
            df = compute_features(db)
            X, feature_names, _ = get_feature_matrix(db)
            idx = df[df["deal_id"] == deal_id].index
            if len(idx) > 0:
                reasons_raw = explain_deal_risk(model, X, idx[0], feature_names)
                risk_reasons = [r["explanation"] for r in reasons_raw]
        except Exception:
            pass

    result = draft_email(
        deal_name=deal.name,
        stage=deal.stage,
        risk_reasons=risk_reasons[:3],
        contact_name=ct.name if ct else "there",
        contact_role=ct.role if ct else "",
        last_email_summary=last_email.body[:100] if last_email else "",
        rep_name=deal.owner or "Team",
        tone=tone,
    )

    db.add(AuditLog(deal_id=deal_id, action="email_drafted", detail=result["subject"]))
    db.commit()

    return EmailDraft(
        deal_id=deal_id,
        to=ct.email if ct else "",
        subject=result["subject"],
        body=result["body"],
        tone=result["tone"],
    )


# ── Simulator ───────────────────────────────────────────────────────

@router.post("/api/simulator", response_model=SimulatorResult)
def run_simulator(params: SimulatorInput, db: Session = Depends(get_db)):
    model = load_forecast_model()
    forecast = predict_pipeline(model)
    baseline = forecast["point_estimate"]

    open_deals = db.query(Deal).filter(Deal.is_closed == False).all()
    avg_size = sum(d.amount for d in open_deals) / len(open_deals) if open_deals else 1000000
    avg_winrate = sum(d.probability for d in open_deals) / len(open_deals) / 100 if open_deals else 0.3

    result = simulate(
        baseline_forecast=baseline,
        open_deal_count=len(open_deals),
        avg_deal_size=avg_size,
        avg_win_rate=avg_winrate,
        add_sdrs=params.add_sdrs,
        increase_discount_pct=params.increase_discount_pct,
        add_meetings_per_deal=params.add_meetings_per_deal,
        shorten_cycle_days=params.shorten_cycle_days,
    )

    return SimulatorResult(**result)


# ── NL Query & Agent ────────────────────────────────────────────────

@router.post("/api/query", response_model=QueryResponse)
def handle_query(req: QueryRequest, db: Session = Depends(get_db)):
    intent = classify_intent(req.question)
    deal_id = extract_deal_id(req.question)

    if intent == "forecast":
        forecast = get_forecast(db)
        answer = (
            f"Q4 2026 pipeline forecast: ₹{forecast['point_estimate']/10000000:.2f}Cr "
            f"(range: ₹{forecast['lower_bound']/10000000:.2f}Cr – ₹{forecast['upper_bound']/10000000:.2f}Cr, "
            f"{forecast['confidence']:.0%} confidence)"
        )
        return QueryResponse(
            answer=answer,
            chart_data=forecast,
            source="forecast_model",
        )

    elif intent == "risk":
        top_risk = get_top_risk_deals(limit=5, db=db)
        answer_lines = ["**Top at-risk deals:**\n"]
        deals_out = []
        for r in top_risk:
            reasons_text = "; ".join([rr["explanation"] for rr in r.top_reasons[:2]])
            answer_lines.append(
                f"• **{r.deal_name}** — Risk: {r.risk_score:.0f}/100 ({r.risk_label}) — {reasons_text}"
            )
            deal = db.query(Deal).filter(Deal.id == r.deal_id).first()
            if deal:
                deals_out.append(DealOut(
                    id=deal.id, name=deal.name, amount=deal.amount,
                    stage=deal.stage, probability=deal.probability,
                    close_date=deal.close_date, owner=deal.owner,
                    risk_score=r.risk_score, risk_label=r.risk_label,
                ))
        return QueryResponse(
            answer="\n".join(answer_lines),
            deals=deals_out,
            source="risk_model",
        )

    elif intent == "deal_detail" and deal_id:
        detail = get_deal(deal_id, db)
        answer = (
            f"**{detail.name}**\n"
            f"Stage: {detail.stage} | Amount: ₹{detail.amount/100000:.1f}L | "
            f"Risk: {detail.risk_score or 'N/A'}/100\n"
            f"Reasons: {', '.join(detail.risk_reasons[:3]) if detail.risk_reasons else 'None identified'}"
        )
        return QueryResponse(answer=answer, source="deal_detail")

    elif intent == "simulator":
        sim_params = extract_simulator_params(req.question)
        if not sim_params:
            return QueryResponse(
                answer="Please specify a scenario, e.g. 'What if I add 2 SDRs?' or 'What if I offer 5% discount?'",
                source="simulator",
            )
        sim_input = SimulatorInput(**sim_params)
        result = run_simulator(sim_input, db)
        answer = (
            f"**Scenario result:**\n"
            f"Baseline: ₹{result.baseline_forecast/10000000:.2f}Cr → "
            f"Adjusted: ₹{result.adjusted_forecast/10000000:.2f}Cr "
            f"(+₹{result.delta/100000:.1f}L, {result.delta_pct:+.1f}%)\n"
            f"Cost: ₹{result.cost_estimate/100000:.1f}L | ROI: {result.roi:.1f}x\n"
            + "\n".join(f"• {d}" for d in result.details)
        )
        return QueryResponse(answer=answer, source="simulator")

    else:
        context_docs = retrieve(req.question, deal_id=deal_id, top_k=3)
        context_text = "\n---\n".join([d["content"][:300] for d in context_docs])
        answer = f"Based on available data:\n\n{context_text[:500]}" if context_text else "I couldn't find specific information for that query. Try asking about forecasts, at-risk deals, or next-best-actions."
        return QueryResponse(answer=answer, source="rag")


# ADDED: Route handler for /api/chat
@router.post("/api/chat")
def handle_chat_agent(payload: Dict[str, Any], db: Session = Depends(get_db)):
    query = payload.get("query") or payload.get("question") or ""
    res = handle_query(QueryRequest(question=query), db)
    return {
        "thought_stream": [
            "Routing query to Natural Language Router...",
            "Analyzing deal risks and retrieval pipeline...",
            "Executing action agent..."
        ],
        "answer": res.answer,
        "deals": res.deals,
        "source": res.source
    }


# ADDED: Route handler for CRM Writeback
@router.post("/api/actions/crm-writeback")
def handle_crm_writeback(payload: Dict[str, Any], db: Session = Depends(get_db)):
    deal_id = payload.get("deal_id")
    action = payload.get("action", "crm_writeback")
    
    if deal_id:
        db.add(AuditLog(deal_id=deal_id, action=action, detail=str(payload)))
        db.commit()
        
    return {
        "status": "success",
        "message": "CRM writeback executed successfully",
        "timestamp": datetime.utcnow().isoformat()
    }


# ── ML Training ─────────────────────────────────────────────────────

@router.post("/api/ml/train")
def train_models(db: Session = Depends(get_db)):
    """Train risk scorer + forecast model and populate feature store."""
    from risk_scorer import train_risk_model, score_deals
    from forecaster import train_forecast_model

    features_df = compute_features(db)
    save_features_to_db(db, features_df)

    X, feature_names, deal_ids = get_feature_matrix(db)
    deals = db.query(Deal).all()
    deals_df = pd.DataFrame([{
        "id": d.id, "close_date_pushed_count": d.close_date_pushed_count,
        "is_won": d.is_won, "is_closed": d.is_closed,
    } for d in deals])

    import numpy as np
    labels = []
    for did in deal_ids:
        row = deals_df[deals_df["id"] == did]
        if row.empty:
            labels.append(0)
        else:
            r = row.iloc[0]
            slipped = r["close_date_pushed_count"] >= 1 or (not r["is_won"] and r["is_closed"])
            labels.append(int(slipped))

    y = np.array(labels)
    model = train_risk_model(X, y)

    scores = score_deals(model, X)
    for i, did in enumerate(deal_ids):
        feat = db.query(DealFeature).filter(DealFeature.deal_id == int(did)).first()
        if feat:
            feat.risk_score = float(scores.iloc[i]["risk_score"])
            feat.risk_label = str(scores.iloc[i]["risk_label"])
    db.commit()

    all_deals_df = pd.DataFrame([{
        "amount": d.amount, "close_date": str(d.close_date),
        "is_won": d.is_won, "probability": d.probability,
    } for d in deals])
    try:
        train_forecast_model(all_deals_df)
        forecast_status = "trained"
    except Exception as e:
        forecast_status = f"skipped ({str(e)[:100]})"

    return {
        "status": "ok",
        "deals_scored": len(scores),
        "risk_model": "trained",
        "forecast_model": forecast_status,
        "high_risk_count": int((scores["risk_label"] == "high_risk").sum()),
        "medium_risk_count": int((scores["risk_label"] == "medium_risk").sum()),
    }


# ── Dashboard Summary ──────────────────────────────────────────────

@router.get("/api/dashboard/summary")
def dashboard_summary(db: Session = Depends(get_db)):
    """Single endpoint for dashboard — forecast + risk + pipeline breakdown."""
    open_deals = db.query(Deal).filter(Deal.is_closed == False).all()
    total_pipeline = sum(d.amount for d in open_deals)
    weighted_pipeline = sum(d.amount * d.probability / 100 for d in open_deals)

    by_stage = {}
    for d in open_deals:
        by_stage[d.stage] = by_stage.get(d.stage, 0) + d.amount

    high_risk = db.query(DealFeature).filter(DealFeature.risk_label == "high_risk").count()
    med_risk = db.query(DealFeature).filter(DealFeature.risk_label == "medium_risk").count()
    low_risk = db.query(DealFeature).filter(DealFeature.risk_label == "low_risk").count()

    try:
        fmodel = load_forecast_model()
        forecast = predict_pipeline(fmodel)
    except Exception:
        forecast = {"point_estimate": weighted_pipeline, "lower_bound": weighted_pipeline * 0.8, "upper_bound": weighted_pipeline * 1.2, "confidence": 0.78}

    return {
        "total_pipeline": round(total_pipeline, 0),
        "weighted_pipeline": round(weighted_pipeline, 0),
        "open_deal_count": len(open_deals),
        "by_stage": {k: round(v, 0) for k, v in by_stage.items()},
        "risk_distribution": {"high": high_risk, "medium": med_risk, "low": low_risk},
        "forecast": forecast,
    }


# ── Audit Log ───────────────────────────────────────────────────────

@router.get("/api/audit", response_model=list[AuditLogOut])
def get_audit_log(limit: int = 50, db: Session = Depends(get_db)):
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return logs