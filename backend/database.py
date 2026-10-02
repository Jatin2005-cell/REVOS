from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Date, DateTime,
    Text, Boolean, ForeignKey, Enum as SAEnum
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
from config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    echo=False,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Models ──────────────────────────────────────────────────────────

class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    domain = Column(String(100))
    industry = Column(String(100))
    employee_count = Column(Integer)
    annual_revenue = Column(Float)
    location = Column(String(100))

    contacts = relationship("Contact", back_populates="account")
    deals = relationship("Deal", back_populates="account")


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    email = Column(String(200))
    role = Column(String(100))
    phone = Column(String(50))
    is_champion = Column(Boolean, default=False)
    account_id = Column(Integer, ForeignKey("accounts.id"))

    account = relationship("Account", back_populates="contacts")
    deals = relationship("Deal", back_populates="primary_contact")
    emails = relationship("Email", back_populates="contact")


class Deal(Base):
    __tablename__ = "deals"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(300), nullable=False)
    amount = Column(Float, nullable=False)
    stage = Column(String(50), nullable=False)
    probability = Column(Float, default=50.0)
    close_date = Column(Date, nullable=False)
    created_date = Column(Date, nullable=False)
    owner = Column(String(100))
    product = Column(String(100))
    source = Column(String(50))
    currency = Column(String(10), default="INR")

    # Tracking fields
    close_date_pushed_count = Column(Integer, default=0)
    discount_requested = Column(Float, default=0.0)
    legal_review_started = Column(Boolean, default=False)
    is_closed = Column(Boolean, default=False)
    is_won = Column(Boolean, default=False)

    account_id = Column(Integer, ForeignKey("accounts.id"))
    contact_id = Column(Integer, ForeignKey("contacts.id"))

    account = relationship("Account", back_populates="deals")
    primary_contact = relationship("Contact", back_populates="deals")
    activities = relationship("Activity", back_populates="deal")
    emails = relationship("Email", back_populates="deal")
    transcripts = relationship("CallTranscript", back_populates="deal")


class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    deal_id = Column(Integer, ForeignKey("deals.id"))
    activity_type = Column(String(30))  # email, call, meeting, note
    date = Column(DateTime, nullable=False)
    subject = Column(String(300))
    notes = Column(Text)

    deal = relationship("Deal", back_populates="activities")


class Email(Base):
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, index=True)
    deal_id = Column(Integer, ForeignKey("deals.id"))
    contact_id = Column(Integer, ForeignKey("contacts.id"))
    from_addr = Column(String(200))
    to_addr = Column(String(200))
    subject = Column(String(300))
    body = Column(Text)
    date = Column(DateTime, nullable=False)
    direction = Column(String(10))  # inbound / outbound
    sentiment = Column(Float)       # -1.0 to 1.0
    competitor_mentioned = Column(String(200))

    deal = relationship("Deal", back_populates="emails")
    contact = relationship("Contact", back_populates="emails")


class CallTranscript(Base):
    __tablename__ = "call_transcripts"

    id = Column(Integer, primary_key=True, index=True)
    deal_id = Column(Integer, ForeignKey("deals.id"))
    contact_id = Column(Integer, ForeignKey("contacts.id"))
    date = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer)
    transcript = Column(Text)
    summary = Column(Text)
    objections = Column(Text)
    commitments = Column(Text)
    next_steps = Column(Text)

    deal = relationship("Deal", back_populates="transcripts")


class DealFeature(Base):
    """Pre-computed feature row per deal — the feature store."""
    __tablename__ = "deal_features"

    deal_id = Column(Integer, ForeignKey("deals.id"), primary_key=True)
    stage_age_days = Column(Integer)
    days_since_last_activity = Column(Integer)
    email_count_30d = Column(Integer)
    champion_reply_gap_days = Column(Integer)
    competitor_mentions = Column(Integer)
    meeting_count = Column(Integer)
    call_count = Column(Integer)
    sentiment_score_avg = Column(Float)
    stakeholder_count = Column(Integer)
    discount_requested = Column(Float)
    legal_review_started = Column(Boolean)
    close_date_pushed_count = Column(Integer)
    amount = Column(Float)
    stage_encoded = Column(Integer)
    owner_win_rate = Column(Float)
    account_deal_count = Column(Integer)
    days_to_close = Column(Integer)

    # ML outputs (filled after scoring)
    risk_score = Column(Float)
    risk_label = Column(String(20))


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    deal_id = Column(Integer, ForeignKey("deals.id"), nullable=True)
    action = Column(String(50))       # risk_scored, nba_generated, email_drafted, crm_updated
    detail = Column(Text)
    user = Column(String(100))


def init_db():
    Base.metadata.create_all(bind=engine)
