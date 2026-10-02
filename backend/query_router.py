"""NL query router — parse user questions and route to the right engine."""
import re

# Intent patterns
INTENT_PATTERNS = {
    "forecast": [
        r"forecast", r"pipeline", r"revenue", r"quarter", r"Q[1-4]",
        r"how much", r"kitna", r"kya hai.*forecast", r"expected revenue",
    ],
    "risk": [
        r"risk", r"at.?risk", r"slip", r"danger", r"concern",
        r"which deals", r"kaunse deals", r"problem deals", r"trouble",
    ],
    "deal_detail": [
        r"deal\s+#?\d+", r"tell me about", r"details? (for|of|about)",
        r"what.?s happening with",
    ],
    "nba": [
        r"what should I do", r"next (best )?action", r"recommend",
        r"kya karna", r"suggest", r"how (to|do I) (fix|save|close)",
    ],
    "simulator": [
        r"what if", r"simulate", r"if I add", r"agar", r"scenario",
        r"impact of", r"what happens",
    ],
    "email": [
        r"draft.*(email|mail)", r"write.*(email|mail)", r"compose",
        r"follow.?up email",
    ],
}


def classify_intent(question: str) -> str:
    """Classify user question into an intent category."""
    q_lower = question.lower().strip()
    scores = {}
    for intent, patterns in INTENT_PATTERNS.items():
        score = sum(1 for p in patterns if re.search(p, q_lower, re.IGNORECASE))
        if score > 0:
            scores[intent] = score

    if not scores:
        return "general"
    return max(scores, key=scores.get)


def extract_deal_id(question: str) -> int | None:
    """Extract deal ID from question if present."""
    match = re.search(r"deal\s*#?\s*(\d+)", question, re.IGNORECASE)
    return int(match.group(1)) if match else None


def extract_simulator_params(question: str) -> dict:
    """Extract what-if parameters from natural language."""
    params = {}
    q = question.lower()

    # SDRs
    sdr_match = re.search(r"add\s+(\d+)\s*sdr", q)
    if sdr_match:
        params["add_sdrs"] = int(sdr_match.group(1))

    # Discount
    disc_match = re.search(r"(\d+(?:\.\d+)?)\s*%?\s*discount", q)
    if disc_match:
        params["increase_discount_pct"] = float(disc_match.group(1))

    # Meetings
    meet_match = re.search(r"add\s+(\d+)\s*meeting", q)
    if meet_match:
        params["add_meetings_per_deal"] = int(meet_match.group(1))

    # Cycle
    cycle_match = re.search(r"(?:shorten|reduce|cut).*?(\d+)\s*day", q)
    if cycle_match:
        params["shorten_cycle_days"] = int(cycle_match.group(1))

    return params
