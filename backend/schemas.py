from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional


# ── Response schemas ────────────────────────────────────────────────

class DealOut(BaseModel):
    id: int
    name: str
    amount: float
    stage: str
    probability: float
    close_date: date
    owner: str | None
    account_name: str | None = None
    contact_name: str | None = None
    risk_score: float | None = None
    risk_label: str | None = None

    class Config:
        from_attributes = True


class DealDetail(DealOut):
    created_date: date
    product: str | None
    source: str | None
    currency: str
    close_date_pushed_count: int
    discount_requested: float
    legal_review_started: bool
    risk_reasons: list[str] = []
    nba: list[dict] = []
    email_draft: str | None = None


class RiskResult(BaseModel):
    deal_id: int
    deal_name: str
    risk_score: float
    risk_label: str
    top_reasons: list[dict]  # [{feature, value, impact}]


class ForecastResult(BaseModel):
    period: str
    point_estimate: float
    lower_bound: float
    upper_bound: float
    confidence: float
    by_stage: dict[str, float] = {}


class NBAItem(BaseModel):
    rank: int
    action: str
    reason: str
    expected_impact: str
    priority: str  # high / medium / low


class EmailDraft(BaseModel):
    deal_id: int
    to: str
    subject: str
    body: str
    tone: str


class SimulatorInput(BaseModel):
    add_sdrs: int = 0
    increase_discount_pct: float = 0.0
    add_meetings_per_deal: int = 0
    shorten_cycle_days: int = 0


class SimulatorResult(BaseModel):
    baseline_forecast: float
    adjusted_forecast: float
    delta: float
    delta_pct: float
    cost_estimate: float
    roi: float
    details: list[str]


class QueryRequest(BaseModel):
    question: str
    language: str = "en"


class QueryResponse(BaseModel):
    answer: str
    chart_data: dict | None = None
    deals: list[DealOut] = []
    actions: list[NBAItem] = []
    source: str = ""


class AuditLogOut(BaseModel):
    id: int
    timestamp: datetime
    deal_id: int | None
    action: str
    detail: str | None
    user: str | None

    class Config:
        from_attributes = True
