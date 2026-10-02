"""LLM-powered email drafting for at-risk deal follow-ups."""
from config import settings

SYSTEM_PROMPT = """You are a senior B2B sales executive. Draft concise, professional follow-up emails.
Rules:
- Reference the last conversation naturally
- Address the specific risk without being alarming
- Propose a clear next step
- Keep under 150 words
- Match the requested tone"""


def draft_email(
    deal_name: str,
    stage: str,
    risk_reasons: list[str],
    contact_name: str,
    contact_role: str,
    last_email_summary: str,
    rep_name: str,
    tone: str = "professional",
) -> dict:
    """Draft a follow-up email using LLM or template fallback."""

    # Try LLM first (Gemini)
    api_key = settings.GOOGLE_API_KEY or settings.GEMINI_API_KEY
    if api_key:
        return _draft_with_llm(
            deal_name, stage, risk_reasons, contact_name,
            contact_role, last_email_summary, rep_name, tone, api_key
        )

    # Template fallback (no API key needed for hackathon demo)
    return _draft_with_template(
        deal_name, stage, risk_reasons, contact_name,
        contact_role, last_email_summary, rep_name, tone
    )


def _draft_with_llm(
    deal_name, stage, risk_reasons, contact_name,
    contact_role, last_email_summary, rep_name, tone, api_key
) -> dict:
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.messages import SystemMessage, HumanMessage

    llm = ChatGoogleGenerativeAI(
        model=settings.LLM_MODEL,
        temperature=settings.LLM_TEMPERATURE,
        google_api_key=api_key,
    )

    prompt = f"""Deal: {deal_name}
Stage: {stage}
Risk reasons: {', '.join(risk_reasons)}
Contact: {contact_name}, {contact_role}
Last interaction: {last_email_summary}
Rep name: {rep_name}

Draft a follow-up email that:
1. References the last conversation
2. Addresses the risk subtly
3. Proposes a concrete next step
Tone: {tone}

Return ONLY the email body (no subject line, no salutation markers)."""

    response = llm.invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ])

    if isinstance(response.content, str):
        body = response.content.strip()
    elif isinstance(response.content, list):
        body = "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in response.content
        ).strip()
    else:
        body = str(response.content).strip()

    subject = f"Following up -- {deal_name.split('—')[0].strip()}"

    return {
        "subject": subject,
        "body": body,
        "tone": tone,
    }


def _draft_with_template(
    deal_name, stage, risk_reasons, contact_name,
    contact_role, last_email_summary, rep_name, tone
) -> dict:
    """Rule-based email template — works without LLM API."""
    risk_text = risk_reasons[0] if risk_reasons else "keeping momentum on this"

    if "champion" in risk_text.lower() or "silent" in risk_text.lower():
        body = (
            f"Hi {contact_name},\n\n"
            f"Hope you're doing well. I wanted to follow up on our recent discussion about {deal_name.split('—')[0].strip()}. "
            f"I know things can get busy, but I wanted to make sure we're still aligned on the timeline.\n\n"
            f"Would you have 15 minutes this week for a quick sync? I have some updated ROI numbers "
            f"that I think will be valuable for your team's evaluation.\n\n"
            f"Looking forward to hearing from you.\n\n"
            f"Best,\n{rep_name}"
        )
    elif "competitor" in risk_text.lower():
        body = (
            f"Hi {contact_name},\n\n"
            f"Thanks for the candid conversation last time. I understand you're evaluating multiple options, "
            f"and I appreciate being part of that process.\n\n"
            f"I've put together a comparison deck that highlights where we differentiate — especially around "
            f"{'forecasting accuracy and explainability' if 'revos' in deal_name.lower() else 'our core capabilities'}. "
            f"I'd love to walk you through it.\n\n"
            f"Can we schedule 20 minutes this week?\n\n"
            f"Best,\n{rep_name}"
        )
    elif "push" in risk_text.lower() or "date" in risk_text.lower():
        body = (
            f"Hi {contact_name},\n\n"
            f"I wanted to check in on the {deal_name.split('—')[0].strip()} evaluation. "
            f"I understand timelines can shift, and I want to make sure we're supporting your process.\n\n"
            f"If there are any blockers on your end — budget, technical concerns, or stakeholder alignment — "
            f"I'm happy to help address them directly.\n\n"
            f"Would it help to schedule a brief call with your team this week?\n\n"
            f"Best,\n{rep_name}"
        )
    else:
        body = (
            f"Hi {contact_name},\n\n"
            f"Wanted to touch base on {deal_name.split('—')[0].strip()}. "
            f"We're excited about the potential fit for your team.\n\n"
            f"Based on our last conversation, I've prepared some additional materials that address "
            f"the key points you raised. Would you have time for a quick call this week to go through them?\n\n"
            f"Best,\n{rep_name}"
        )

    company = deal_name.split("—")[0].strip()
    return {
        "subject": f"Following up — {company}",
        "body": body,
        "tone": tone,
    }
