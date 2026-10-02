"""Load CSV data into SQLAlchemy database and build the revenue graph."""
import csv
import os
from datetime import datetime, date
from sqlalchemy.orm import Session
from database import Account, Contact, Deal, Activity, Email, CallTranscript, init_db, SessionLocal
from rag_engine import index_emails, index_transcripts
from config import settings


def parse_date(val: str) -> date | None:
    if not val:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y"):
        try:
            return datetime.strptime(val, fmt).date()
        except ValueError:
            continue
    return None


def parse_datetime(val: str) -> datetime | None:
    if not val:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(val, fmt)
        except ValueError:
            continue
    return None


def load_csv(filename: str) -> list[dict]:
    path = os.path.join(settings.DATA_DIR, filename)
    if not os.path.exists(path):
        print(f"  [!] {path} not found, skipping")
        return []
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def ingest_all():
    """Load all CSV data into the database and index into ChromaDB."""
    print("Initializing database...")
    init_db()

    db = SessionLocal()
    try:
        _load_accounts(db)
        _load_contacts(db)
        _load_deals(db)
        _load_activities(db)
        emails = _load_emails(db)
        transcripts = _load_transcripts(db)

        print("\nIndexing into ChromaDB...")
        if emails:
            index_emails(emails)
        if transcripts:
            index_transcripts(transcripts)

        print("\n[+] Ingestion complete")
    finally:
        db.close()


def _load_accounts(db: Session):
    rows = load_csv("accounts.csv")
    for r in rows:
        acc = Account(
            id=int(r["id"]),
            name=r["name"],
            domain=r.get("domain", ""),
            industry=r.get("industry", ""),
            employee_count=int(r.get("employee_count", 0)),
            annual_revenue=float(r.get("annual_revenue", 0)),
            location=r.get("location", ""),
        )
        db.merge(acc)
    db.commit()
    print(f"  [+] Loaded {len(rows)} accounts")


def _load_contacts(db: Session):
    rows = load_csv("contacts.csv")
    for r in rows:
        ct = Contact(
            id=int(r["id"]),
            name=r["name"],
            email=r.get("email", ""),
            role=r.get("role", ""),
            phone=r.get("phone", ""),
            is_champion=r.get("is_champion", "").lower() in ("true", "1", "yes"),
            account_id=int(r["account_id"]),
        )
        db.merge(ct)
    db.commit()
    print(f"  [+] Loaded {len(rows)} contacts")


def _load_deals(db: Session):
    rows = load_csv("deals.csv")
    for r in rows:
        deal = Deal(
            id=int(r["id"]),
            name=r["name"],
            amount=float(r["amount"]),
            stage=r["stage"],
            probability=float(r.get("probability", 50)),
            close_date=parse_date(r["close_date"]),
            created_date=parse_date(r["created_date"]),
            owner=r.get("owner", ""),
            product=r.get("product", ""),
            source=r.get("source", ""),
            currency=r.get("currency", "INR"),
            close_date_pushed_count=int(r.get("close_date_pushed_count", 0)),
            discount_requested=float(r.get("discount_requested", 0)),
            legal_review_started=r.get("legal_review_started", "").lower() in ("true", "1", "yes"),
            is_closed=r.get("is_closed", "").lower() in ("true", "1", "yes"),
            is_won=r.get("is_won", "").lower() in ("true", "1", "yes"),
            account_id=int(r["account_id"]),
            contact_id=int(r["contact_id"]),
        )
        db.merge(deal)
    db.commit()
    print(f"  [+] Loaded {len(rows)} deals")


def _load_activities(db: Session):
    rows = load_csv("activities.csv")
    for r in rows:
        act = Activity(
            id=int(r["id"]),
            deal_id=int(r["deal_id"]),
            activity_type=r.get("activity_type", "note"),
            date=parse_datetime(r["date"]),
            subject=r.get("subject", ""),
            notes=r.get("notes", ""),
        )
        db.merge(act)
    db.commit()
    print(f"  [+] Loaded {len(rows)} activities")


def _load_emails(db: Session) -> list[dict]:
    rows = load_csv("emails.csv")
    for r in rows:
        em = Email(
            id=int(r["id"]),
            deal_id=int(r["deal_id"]),
            contact_id=int(r["contact_id"]),
            from_addr=r.get("from_addr", ""),
            to_addr=r.get("to_addr", ""),
            subject=r.get("subject", ""),
            body=r.get("body", ""),
            date=parse_datetime(r["date"]),
            direction=r.get("direction", "inbound"),
            sentiment=float(r.get("sentiment", 0)),
            competitor_mentioned=r.get("competitor_mentioned", ""),
        )
        db.merge(em)
    db.commit()
    print(f"  [+] Loaded {len(rows)} emails")
    return rows


def _load_transcripts(db: Session) -> list[dict]:
    rows = load_csv("call_transcripts.csv")
    for r in rows:
        ct = CallTranscript(
            id=int(r["id"]),
            deal_id=int(r["deal_id"]),
            contact_id=int(r["contact_id"]),
            date=parse_datetime(r["date"]),
            duration_minutes=int(r.get("duration_minutes", 0)),
            transcript=r.get("transcript", ""),
            summary=r.get("summary", ""),
            objections=r.get("objections", ""),
            commitments=r.get("commitments", ""),
            next_steps=r.get("next_steps", ""),
        )
        db.merge(ct)
    db.commit()
    print(f"  [+] Loaded {len(rows)} call transcripts")
    return rows
