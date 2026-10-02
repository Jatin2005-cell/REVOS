"""Generate 500 synthetic CRM deals + emails + call transcripts.
Run once: python generate_data.py
"""
import random
import json
import csv
import os
from datetime import datetime, timedelta, date

random.seed(42)

# ── Constants ───────────────────────────────────────────────────────

INDUSTRIES = [
    "SaaS", "Fintech", "Healthcare", "E-commerce", "EdTech",
    "Manufacturing", "Logistics", "Media", "Consulting", "Telecom",
]
STAGES = ["Discovery", "Qualification", "Proposal", "Negotiation", "Closed Won", "Closed Lost"]
STAGE_PROB = {"Discovery": 10, "Qualification": 25, "Proposal": 50, "Negotiation": 75, "Closed Won": 100, "Closed Lost": 0}
PRODUCTS = ["RevOS Pro", "RevOS Starter", "RevOS Enterprise", "RevOS Analytics", "RevOS API"]
SOURCES = ["Inbound", "Outbound", "Referral", "Event", "Partner"]
OWNERS = [f"Rep_{i}" for i in range(1, 11)]
COMPETITORS = ["Clari", "Gong", "People.ai", "Salesforce Einstein", "HubSpot AI", ""]
ROLES = ["VP Engineering", "CTO", "Head of Sales", "CFO", "Director IT", "CEO", "Product Manager", "Procurement Lead"]
DOMAINS = [
    "acmetech.com", "betaworks.in", "clearstack.io", "deltaforce.co",
    "ecomsprint.com", "finlabs.in", "growthloop.io", "hyperion.co",
    "infoedge.com", "jetscale.in", "kinetiq.io", "logicworks.co",
    "metaverse.in", "nexatech.io", "omnilayer.co", "prismdata.com",
    "quantleap.in", "raptorx.io", "stratosai.co", "truepathsys.com",
    "ultradev.in", "vantagepoint.io", "wavefront.co", "xeronova.com",
    "yieldmax.in", "zenithops.io", "alphacloud.co", "brightspark.com",
    "corelogic.in", "datavault.io", "edgeflux.co", "fusionware.com",
    "globecast.in", "hexacore.io", "innov8.co", "junctionai.com",
    "keystone.in", "luminance.io", "maplesoft.co", "novabridge.com",
    "orchidtech.in", "pulsenet.io", "qubitlabs.co", "relaystack.com",
    "signalops.in", "terraflow.io", "uplinkai.co", "vertexsys.com",
    "windrose.in", "xyphorai.io",
]
FIRST_NAMES = [
    "Aarav", "Priya", "Rohan", "Sneha", "Vikram", "Anjali", "Karthik",
    "Meera", "Arjun", "Divya", "Rahul", "Pooja", "Aditya", "Nisha",
    "Siddharth", "Kavita", "Manish", "Ritu", "Nikhil", "Swati",
    "James", "Sarah", "Michael", "Emma", "David", "Lisa", "Robert",
    "Jennifer", "William", "Jessica", "Daniel", "Ashley", "Chris", "Amanda",
]
LAST_NAMES = [
    "Sharma", "Patel", "Singh", "Kumar", "Gupta", "Reddy", "Joshi",
    "Verma", "Mehta", "Iyer", "Rao", "Das", "Nair", "Shah",
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis",
]

EMAIL_TEMPLATES_POSITIVE = [
    "Hi {rep}, thanks for the proposal. The team reviewed it and we're keen to move forward. Can we schedule a call this week to discuss next steps?",
    "Great demo yesterday! Our VP was impressed with the forecasting module. Let's discuss pricing for the enterprise tier.",
    "We've completed internal review. Legal is looking at the contract now. Expect sign-off by {date}.",
    "The ROI numbers you shared were compelling. I've looped in our CFO for budget approval.",
    "Quick update — we got budget approval. Let's finalize the SOW this week.",
]
EMAIL_TEMPLATES_NEGATIVE = [
    "Hi {rep}, we need to push the timeline. Budget freeze until next quarter. I'll keep you posted.",
    "We're evaluating {competitor} as well. Can you share a comparison deck?",
    "The team has concerns about integration complexity. We might need to revisit scope.",
    "Sorry for the silence — been caught up with internal reorg. Not sure about the timeline anymore.",
    "Our CTO left the company last week. New leadership wants to re-evaluate all vendor decisions.",
    "We need to put this on hold. There's a hiring freeze and priorities have shifted.",
]
EMAIL_TEMPLATES_NEUTRAL = [
    "Hi {rep}, just checking in. Any updates on the custom integration we discussed?",
    "Can you send over the updated pricing sheet? We need it for our internal review.",
    "Thanks for the follow-up. We're still in discussion internally. Will get back to you soon.",
]

CALL_OBJECTIONS = [
    "Budget constraints — need to justify ROI to CFO",
    "Competitor offering lower price",
    "Integration concerns with existing stack",
    "Timeline too aggressive for implementation",
    "Need buy-in from more stakeholders",
    "Previous vendor experience was poor, trust issues",
    "Legal review taking longer than expected",
]
CALL_COMMITMENTS = [
    "Will schedule follow-up with VP next Tuesday",
    "Sharing proposal with procurement this week",
    "Internal demo for the team on Thursday",
    "Contract review by end of month",
    "Budget allocation meeting next Monday",
    "Will send technical requirements document",
]

NOW = datetime(2026, 10, 1)


def random_date(start_days_ago: int, end_days_ago: int = 0) -> datetime:
    delta = random.randint(end_days_ago, start_days_ago)
    return NOW - timedelta(days=delta)


def generate_accounts(n: int = 50) -> list[dict]:
    accounts = []
    for i in range(1, n + 1):
        accounts.append({
            "id": i,
            "name": f"{DOMAINS[i-1].split('.')[0].title()} Inc",
            "domain": DOMAINS[i - 1],
            "industry": random.choice(INDUSTRIES),
            "employee_count": random.choice([50, 100, 200, 500, 1000, 2000, 5000]),
            "annual_revenue": round(random.uniform(5, 500) * 100000, 0),  # 5L – 5Cr
            "location": random.choice(["Mumbai", "Bangalore", "Delhi", "Pune", "Hyderabad", "Chennai", "US", "UK"]),
        })
    return accounts


def generate_contacts(accounts: list[dict], per_account: int = 3) -> list[dict]:
    contacts = []
    cid = 1
    for acc in accounts:
        n = random.randint(2, per_account + 1)
        for j in range(n):
            fname = random.choice(FIRST_NAMES)
            lname = random.choice(LAST_NAMES)
            contacts.append({
                "id": cid,
                "name": f"{fname} {lname}",
                "email": f"{fname.lower()}.{lname.lower()}@{acc['domain']}",
                "role": ROLES[j % len(ROLES)],
                "phone": f"+91-{random.randint(70000, 99999)}{random.randint(10000, 99999)}",
                "is_champion": j == 0,
                "account_id": acc["id"],
            })
            cid += 1
    return contacts


def generate_deals(accounts: list[dict], contacts: list[dict], n: int = 500) -> list[dict]:
    deals = []
    contact_by_account = {}
    for c in contacts:
        contact_by_account.setdefault(c["account_id"], []).append(c)

    for i in range(1, n + 1):
        acc = random.choice(accounts)
        acc_contacts = contact_by_account.get(acc["id"], [])
        contact = random.choice(acc_contacts) if acc_contacts else contacts[0]

        stage = random.choices(STAGES, weights=[15, 20, 25, 20, 12, 8])[0]
        created = random_date(180, 10)
        base_close = created + timedelta(days=random.randint(30, 120))
        pushed = random.randint(0, 3) if stage not in ("Closed Won", "Closed Lost") else 0
        close_date = base_close + timedelta(days=pushed * random.randint(7, 21))

        is_won = stage == "Closed Won"
        is_closed = stage in ("Closed Won", "Closed Lost")
        amount = round(random.uniform(2, 80) * 100000, 0)  # 2L – 80L

        deals.append({
            "id": i,
            "name": f"{acc['name']} — {random.choice(PRODUCTS)}",
            "amount": amount,
            "stage": stage,
            "probability": STAGE_PROB[stage],
            "close_date": close_date.strftime("%Y-%m-%d"),
            "created_date": created.strftime("%Y-%m-%d"),
            "owner": random.choice(OWNERS),
            "product": random.choice(PRODUCTS),
            "source": random.choice(SOURCES),
            "currency": "INR",
            "close_date_pushed_count": pushed,
            "discount_requested": round(random.uniform(0, 15), 1) if random.random() < 0.3 else 0.0,
            "legal_review_started": stage in ("Negotiation", "Closed Won") and random.random() < 0.6,
            "is_closed": is_closed,
            "is_won": is_won,
            "account_id": acc["id"],
            "contact_id": contact["id"],
        })
    return deals


def generate_activities(deals: list[dict]) -> list[dict]:
    activities = []
    aid = 1
    for deal in deals:
        created = datetime.strptime(deal["created_date"], "%Y-%m-%d")
        n_activities = random.randint(3, 15)
        for _ in range(n_activities):
            act_date = created + timedelta(days=random.randint(1, (NOW - created).days or 1))
            atype = random.choices(["email", "call", "meeting", "note"], weights=[40, 25, 20, 15])[0]
            activities.append({
                "id": aid,
                "deal_id": deal["id"],
                "activity_type": atype,
                "date": act_date.strftime("%Y-%m-%dT%H:%M:%S"),
                "subject": f"{atype.title()} with {deal['name'][:30]}",
                "notes": "",
            })
            aid += 1
    return activities


def generate_emails(deals: list[dict], contacts: list[dict]) -> list[dict]:
    emails = []
    eid = 1
    contact_map = {c["id"]: c for c in contacts}

    for deal in deals:
        contact = contact_map.get(deal["contact_id"], contacts[0])
        rep_email = f"{deal['owner'].lower()}@revos.ai"
        n_emails = random.randint(2, 10)
        created = datetime.strptime(deal["created_date"], "%Y-%m-%d")

        for j in range(n_emails):
            edate = created + timedelta(days=random.randint(1, max((NOW - created).days, 2)))
            direction = random.choice(["inbound", "outbound"])
            competitor = random.choice(COMPETITORS)

            # Pick template based on deal health
            if deal["stage"] in ("Closed Won",) or (deal["close_date_pushed_count"] == 0 and random.random() < 0.6):
                tmpl = random.choice(EMAIL_TEMPLATES_POSITIVE)
                sentiment = round(random.uniform(0.3, 1.0), 2)
            elif deal["close_date_pushed_count"] >= 2 or deal["stage"] == "Closed Lost":
                tmpl = random.choice(EMAIL_TEMPLATES_NEGATIVE)
                sentiment = round(random.uniform(-1.0, -0.1), 2)
            else:
                tmpl = random.choice(EMAIL_TEMPLATES_NEUTRAL + EMAIL_TEMPLATES_POSITIVE)
                sentiment = round(random.uniform(-0.3, 0.6), 2)

            body = tmpl.format(
                rep=deal["owner"],
                competitor=competitor if competitor else "a competitor",
                date=(edate + timedelta(days=7)).strftime("%B %d"),
            )

            emails.append({
                "id": eid,
                "deal_id": deal["id"],
                "contact_id": deal["contact_id"],
                "from_addr": contact["email"] if direction == "inbound" else rep_email,
                "to_addr": rep_email if direction == "inbound" else contact["email"],
                "subject": f"Re: {deal['name'][:40]}",
                "body": body,
                "date": edate.strftime("%Y-%m-%dT%H:%M:%S"),
                "direction": direction,
                "sentiment": sentiment,
                "competitor_mentioned": competitor if competitor and random.random() < 0.3 else "",
            })
            eid += 1
    return emails


def generate_call_transcripts(deals: list[dict]) -> list[dict]:
    transcripts = []
    tid = 1
    for deal in deals:
        n_calls = random.randint(0, 4)
        created = datetime.strptime(deal["created_date"], "%Y-%m-%d")
        for _ in range(n_calls):
            cdate = created + timedelta(days=random.randint(5, max((NOW - created).days, 6)))
            objections = random.sample(CALL_OBJECTIONS, k=random.randint(0, 3))
            commitments = random.sample(CALL_COMMITMENTS, k=random.randint(0, 2))

            transcript_text = (
                f"Call with {deal['name']}.\n"
                f"Discussed pricing and timeline.\n"
                + (f"Objections raised: {'; '.join(objections)}.\n" if objections else "")
                + (f"Commitments: {'; '.join(commitments)}.\n" if commitments else "")
                + f"Next steps: Follow up on {(cdate + timedelta(days=3)).strftime('%B %d')}."
            )

            transcripts.append({
                "id": tid,
                "deal_id": deal["id"],
                "contact_id": deal["contact_id"],
                "date": cdate.strftime("%Y-%m-%dT%H:%M:%S"),
                "duration_minutes": random.randint(10, 45),
                "transcript": transcript_text,
                "summary": f"Discovery/negotiation call for {deal['name'][:30]}",
                "objections": json.dumps(objections),
                "commitments": json.dumps(commitments),
                "next_steps": f"Follow up by {(cdate + timedelta(days=3)).strftime('%B %d')}",
            })
            tid += 1
    return transcripts


def save_csv(data: list[dict], filename: str):
    if not data:
        return
    os.makedirs("data", exist_ok=True)
    path = os.path.join("data", filename)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    print(f"  [+] {path} ({len(data)} rows)")


def main():
    print("Generating synthetic RevOS data...")

    accounts = generate_accounts(50)
    contacts = generate_contacts(accounts)
    deals = generate_deals(accounts, contacts, 500)
    activities = generate_activities(deals)
    emails = generate_emails(deals, contacts)
    transcripts = generate_call_transcripts(deals)

    save_csv(accounts, "accounts.csv")
    save_csv(contacts, "contacts.csv")
    save_csv(deals, "deals.csv")
    save_csv(activities, "activities.csv")
    save_csv(emails, "emails.csv")
    save_csv(transcripts, "call_transcripts.csv")

    print(f"\nDone. Totals:")
    print(f"  Accounts:    {len(accounts)}")
    print(f"  Contacts:    {len(contacts)}")
    print(f"  Deals:       {len(deals)}")
    print(f"  Activities:  {len(activities)}")
    print(f"  Emails:      {len(emails)}")
    print(f"  Transcripts: {len(transcripts)}")


if __name__ == "__main__":
    main()
