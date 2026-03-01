from groq import Groq
import json
import os
import re
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
PROMPT_DIR   = os.path.join(os.path.dirname(__file__), "..", "prompts")

client = None
if GROQ_API_KEY and GROQ_API_KEY != "your_groq_api_key_here":
    client = Groq(api_key=GROQ_API_KEY)
    print("✓ Groq API configured successfully")
else:
    print("(X) GROQ_API_KEY not set. Add it to .env file.")


def _load_prompt(filename: str) -> str:
    try:
        with open(os.path.join(PROMPT_DIR, filename)) as f:
            return f.read()
    except FileNotFoundError:
        return ""


def _call_groq(prompt: str, temperature: float = 0.1, max_tokens: int = 2048) -> str:
    if not client:
        raise Exception("Groq API key not configured. Add GROQ_API_KEY to .env")
    response = client.chat.completions.create(
        model       = "llama-3.3-70b-versatile",
        messages    = [{"role": "user", "content": prompt}],
        temperature = temperature,
        max_tokens  = max_tokens,
    )
    return response.choices[0].message.content


def _parse_json(raw: str) -> Optional[Dict]:
    text = raw.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'```\s*$', '', text, flags=re.MULTILINE)
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find('{')
    end   = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        candidate = text[start:end+1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    try:
        fixed = re.sub(r',\s*([}\]])', r'\1', text[start:end+1] if start != -1 else text)
        return json.loads(fixed)
    except Exception:
        pass

    return None


# ── 1. TENDER EXTRACTION ──────────────────────────────────────
def extract_tender_structure(raw_text: str, sections: Optional[Dict] = None) -> Dict:
    if not client:
        return {"error": "Groq API key not configured. Add GROQ_API_KEY to .env"}

    if sections:
        relevant = ""
        for key in ["eligibility criteria", "eligibility requirement", "pre-qualification",
                    "financial requirement", "documents required", "scope of work"]:
            if key in sections:
                relevant += f"\n\n=== {key.upper()} ===\n{sections[key]}"
        text_to_send = relevant[:6000] if len(relevant) > 500 else raw_text[:6000]
    else:
        text_to_send = raw_text[:6000]

    prompt = f"""You are an expert Indian government procurement analyst with 15 years of experience reading GeM, CPPP, NIC and state portal tender documents.

Your task is to extract ALL eligibility and compliance information from the tender text below into a structured JSON object.

EXTRACTION RULES:
- Read every line carefully — eligibility criteria are often buried in sub-clauses
- Extract EXACT values — do not round, estimate or guess
- For turnover: look for "annual turnover", "average annual turnover", "net worth" clauses
- For experience: look for "similar work", "similar nature", "experience of", "should have executed"
- For certifications: look for ISO, BIS, STQC, OEM, GeM registration, Udyam, NSIC
- For MSME: look for "preference to MSE", "MSE exemption", "Udyam registered"
- For bid security: look for "EMD", "Earnest Money Deposit", "bid security"
- deadline: extract in DD-MM-YYYY format, look for "last date", "closing date", "submission deadline"
- If a value is genuinely not present, use null — never fabricate

OUTPUT FORMAT — return ONLY this JSON, no text before or after, no markdown fences:
{{
  "tender_id": "string or null",
  "title": "full official tender title",
  "issuing_authority": "department/ministry name",
  "deadline": "DD-MM-YYYY or null",
  "estimated_value": "number in INR Lakhs or null",
  "eligibility": {{
    "min_turnover": "number in INR Lakhs or null",
    "turnover_note": "exact clause text or null",
    "years_experience": "number or null",
    "experience_note": "exact clause text describing experience requirement or null",
    "required_certifications": ["list of required certs"],
    "msme_preference": true or false,
    "msme_exemptions": ["list of exemptions for MSMEs if any"],
    "past_project_requirement": "description or null",
    "min_single_project_value": "number in INR Lakhs or null",
    "other_requirements": ["any other eligibility conditions"]
  }},
  "documents_required": ["complete list of documents to submit"],
  "key_clauses": ["important clauses bidders must know"],
  "sector": "IT/Construction/Healthcare/Defence/Education/Supply/Services/Other",
  "bid_security": "amount and format or null",
  "contract_duration": "duration string or null",
  "portal": "GeM/CPPP/NIC/State/Other"
}}

TENDER TEXT:
{text_to_send}"""

    try:
        raw_response = _call_groq(prompt, temperature=0.0, max_tokens=2048)
        parsed = _parse_json(raw_response)

        if parsed is None:
            print(f"WARNING: Could not parse JSON. Raw response preview: {raw_response[:200]}")
            return {
                "tender_id": None,
                "title": "Tender (manual review needed)",
                "issuing_authority": "Unknown",
                "deadline": None,
                "estimated_value": None,
                "eligibility": {
                    "min_turnover": None,
                    "turnover_note": None,
                    "years_experience": None,
                    "experience_note": None,
                    "required_certifications": [],
                    "msme_preference": False,
                    "msme_exemptions": [],
                    "past_project_requirement": None,
                    "min_single_project_value": None,
                    "other_requirements": []
                },
                "documents_required": [],
                "key_clauses": [],
                "sector": "Unknown",
                "bid_security": None,
                "contract_duration": None,
                "portal": "Unknown",
                "_note": "AI extraction failed — please review the raw text manually"
            }

        return parsed

    except Exception as e:
        return {"error": f"Groq API error: {str(e)}"}


# ── 2. BID DRAFT GENERATION ───────────────────────────────────
def generate_bid_draft(tender_data: Dict, company_data: Dict, additional_context: Optional[str] = None) -> str:
    if not client:
        return "Error: Groq API key not configured."

    projects = company_data.get("past_projects", [])
    projects_text = "\n".join([
        f"  • {p.get('name', 'N/A')} — Client: {p.get('client', 'N/A')}, "
        f"Value: Rs.{p.get('value', 0)}L, Completed: {p.get('year', 'N/A')}"
        for p in projects[:5]
    ]) or "  • No past projects listed"

    certs = ", ".join(company_data.get("certifications", [])) or "None listed"
    docs  = ", ".join(tender_data.get("documents_required", [])) or "As per tender"
    elig  = tender_data.get("eligibility", {})

    prompt = f"""You are a senior procurement consultant in India who has helped 200+ MSMEs win government tenders worth over Rs.500 Crore. You write compelling, precise, professionally formatted bid proposals that win contracts.

TENDER DETAILS:
- Title: {tender_data.get('title', 'N/A')}
- Issuing Authority: {tender_data.get('issuing_authority', 'N/A')}
- Sector: {tender_data.get('sector', 'N/A')}
- Estimated Value: Rs.{tender_data.get('estimated_value', 'N/A')} Lakhs
- Contract Duration: {tender_data.get('contract_duration', 'As per tender')}
- Deadline: {tender_data.get('deadline', 'N/A')}
- Min Turnover Required: Rs.{elig.get('min_turnover', 'N/A')} Lakhs
- Experience Required: {elig.get('years_experience', 'N/A')} years
- Required Certifications: {', '.join(elig.get('required_certifications', [])) or 'None specified'}
- MSME Preference: {'Yes' if elig.get('msme_preference') else 'No'}
- Documents Required: {docs}

COMPANY PROFILE:
- Name: {company_data.get('name')}
- MSME Category: {company_data.get('msme_category', 'MSME').upper()}
- Annual Turnover: Rs.{company_data.get('annual_turnover', 0)} Lakhs
- Years in Operation: {company_data.get('years_in_operation', 0)} years
- Certifications Held: {certs}
- GST Number: {company_data.get('gst_number', 'As per records')}
- Registration: {company_data.get('registration_number', 'As per records')}
- Past Projects:
{projects_text}

{f'SPECIAL INSTRUCTIONS: {additional_context}' if additional_context else ''}

WRITING GUIDELINES:
- Use formal, confident government procurement language
- Reference SPECIFIC numbers and facts from the data above — never write generic filler
- Highlight MSME status prominently if applicable
- In past experience, directly connect each project to the tender requirements
- In compliance section, address EACH eligibility criterion one by one
- Make the proposal feel bespoke to this exact tender, not a template
- Use "we" and "our company" — first person plural throughout

Write the complete bid proposal with ALL 9 sections below. Each section must be substantive (minimum 3-4 sentences), specific and reference actual data:

# BID PROPOSAL
## {tender_data.get('title', 'Tender Response')}
### Submitted by: {company_data.get('name')}

---

## 1. COVER LETTER
[Formal opening addressed to {tender_data.get('issuing_authority', 'the Authority')}, reference tender title, express intent to bid, highlight 2-3 key strengths, close with availability for clarifications]

## 2. COMPANY OVERVIEW
[Company name, MSME category, years in operation, turnover, core competencies, geographic presence, mission statement]

## 3. TECHNICAL COMPLIANCE STATEMENT
[Address each eligibility criterion explicitly — turnover, experience, certifications, MSME status — with actual figures showing compliance or near-compliance]

## 4. SCOPE UNDERSTANDING & APPROACH
[Demonstrate deep understanding of the work required, proposed methodology, timeline, key milestones, risk mitigation]

## 5. RELEVANT PAST EXPERIENCE
[Detail each past project — name, client, value, scope, outcomes — and explicitly link it to this tender's requirements]

## 6. TEAM & RESOURCE PLAN
[Key personnel roles, qualifications, dedicated team size, infrastructure and tools available]

## 7. QUALITY ASSURANCE & DELIVERY COMMITMENT
[QA processes, certifications backing them, escalation procedures, SLA commitments, penalty acceptance]

## 8. DECLARATIONS & COMPLIANCE STATEMENTS
[Blacklisting declaration, no conflict of interest, acceptance of all tender terms, EMD/bid security details, signatory authority]

## 9. DOCUMENT INDEX
[Numbered list of all documents being submitted with this proposal]

---
*Authorised Signatory | {company_data.get('name')} | Date: ___________*
"""
    try:
        return _call_groq(prompt, temperature=0.3, max_tokens=4096)
    except Exception as e:
        return f"Error generating draft: {str(e)}"


# ── 3. COPILOT Q&A ────────────────────────────────────────────
def copilot_answer(tender_data: Dict, question: str, conversation_history: List[Dict]) -> str:
    if not client:
        return "Error: Groq API key not configured."

    history_text = ""
    for msg in conversation_history[-8:]:
        role = "Bidder" if msg["role"] == "user" else "Consultant"
        history_text += f"{role}: {msg['content']}\n\n"

    tender_summary = f"""
Tender: {tender_data.get('title', 'N/A')}
Authority: {tender_data.get('issuing_authority', 'N/A')}
Deadline: {tender_data.get('deadline', 'N/A')}
Sector: {tender_data.get('sector', 'N/A')}
Estimated Value: Rs.{tender_data.get('estimated_value', 'N/A')} Lakhs
Min Turnover: Rs.{tender_data.get('eligibility', {}).get('min_turnover', 'N/A')} Lakhs
Experience Required: {tender_data.get('eligibility', {}).get('years_experience', 'N/A')} years
Required Certifications: {', '.join(tender_data.get('eligibility', {}).get('required_certifications', [])) or 'None'}
MSME Preference: {'Yes' if tender_data.get('eligibility', {}).get('msme_preference') else 'No'}
Documents Required: {', '.join(tender_data.get('documents_required', [])) or 'See tender'}
Bid Security: {tender_data.get('bid_security', 'N/A')}
Key Clauses: {'; '.join(tender_data.get('key_clauses', [])) or 'None extracted'}
"""

    prompt = f"""You are an expert Indian government procurement consultant with deep knowledge of:
- GeM portal, CPPP, NIC eProcurement systems
- GFR 2017 rules and CVC guidelines
- MSME procurement policy (25% reservation, EMD exemption, price preference)
- Tender evaluation criteria and L1 bidding
- Consortium and joint venture provisions
- Common disqualification reasons and how to avoid them

TENDER INFORMATION:
{tender_summary}

FULL TENDER DATA:
{json.dumps(tender_data, indent=2)}

{f"CONVERSATION SO FAR:{chr(10)}{history_text}" if history_text else ""}

BIDDER'S QUESTION: {question}

ANSWER GUIDELINES:
- Be direct and specific — lead with the answer, then explain
- Always cite the exact requirement from the tender when relevant
- If the question is about eligibility, give a clear YES/NO/CONDITIONAL verdict first
- If documents are asked about, list them clearly and numbered
- If you're unsure about something not in the tender data, say so honestly
- Keep answers concise (3-6 sentences) unless a detailed explanation is needed
- Use Indian procurement terminology (EMD, L1, GeM, MSME, etc.)
- If there's a risk or important caveat, highlight it clearly
"""
    try:
        return _call_groq(prompt, temperature=0.2, max_tokens=1024)
    except Exception as e:
        return f"Error: {str(e)}"


# ── 4. COMPLIANCE GAP ANALYSIS ────────────────────────────────
def analyze_compliance_gaps(tender_data: Dict, company_data: Dict, gaps: List[Dict]) -> str:
    if not client:
        return "AI analysis unavailable — add GROQ_API_KEY to .env"

    elig = tender_data.get("eligibility", {})
    disqualifying = [g for g in gaps if "DISQUALIFYING" in g.get("severity", "").upper()]
    major         = [g for g in gaps if "MAJOR" in g.get("severity", "").upper()]
    minor         = [g for g in gaps if "MINOR" in g.get("severity", "").upper()]

    gaps_summary = ""
    if disqualifying:
        gaps_summary += f"\nDISQUALIFYING GAPS ({len(disqualifying)}):\n"
        gaps_summary += "\n".join([f"  - {g.get('field')}: {g.get('note', '')}" for g in disqualifying])
    if major:
        gaps_summary += f"\n\nMAJOR GAPS ({len(major)}):\n"
        gaps_summary += "\n".join([f"  - {g.get('field')}: {g.get('note', '')}" for g in major])
    if minor:
        gaps_summary += f"\n\nMINOR GAPS ({len(minor)}):\n"
        gaps_summary += "\n".join([f"  - {g.get('field')}: {g.get('note', '')}" for g in minor])

    prompt = f"""You are India's leading MSME procurement strategist. You have helped hundreds of small businesses navigate government tenders, close eligibility gaps, and win contracts against larger competitors.

TENDER:
- Title: {tender_data.get('title')}
- Authority: {tender_data.get('issuing_authority')}
- Sector: {tender_data.get('sector')}
- Deadline: {tender_data.get('deadline', 'N/A')}
- Min Turnover Required: Rs.{elig.get('min_turnover', 'N/A')} Lakhs
- Experience Required: {elig.get('years_experience', 'N/A')} years
- Required Certifications: {', '.join(elig.get('required_certifications', [])) or 'None'}
- MSME Preference: {'Yes — MSMEs get price preference and EMD exemption' if elig.get('msme_preference') else 'No specific MSME preference mentioned'}

COMPANY:
- Name: {company_data.get('name')}
- MSME Category: {company_data.get('msme_category', 'Not specified').upper()}
- Annual Turnover: Rs.{company_data.get('annual_turnover', 0)} Lakhs
- Years in Operation: {company_data.get('years_in_operation', 0)} years
- Certifications: {', '.join(company_data.get('certifications', [])) or 'None listed'}
- Available Documents: {', '.join(company_data.get('available_documents', [])) or 'None listed'}

IDENTIFIED GAPS:
{gaps_summary if gaps_summary else 'No gaps identified — company appears fully eligible'}

Write a focused 4-paragraph strategic analysis:

PARAGRAPH 1 — OVERALL VERDICT:
Give a clear, honest assessment of the company's chances. Be specific about what works in their favour (MSME status, turnover level, sector experience) and what doesn't. State whether they should bid, bid with caveats, or wait.

PARAGRAPH 2 — CRITICAL GAPS DEEP DIVE:
For each disqualifying or major gap, explain exactly WHY it matters in this tender's context, what the evaluating committee will look for, and the realistic consequence of not addressing it. Be brutally honest — don't soften the blow if a gap is genuinely disqualifying.

PARAGRAPH 3 — ACTION PLAN:
Give 3-5 concrete, time-bound steps to address the gaps. Be specific:
- For missing certifications: name the exact body (QCI, BIS, STQC, NSIC) and realistic timeline
- For turnover shortfall: mention subcontracting, consortium, or waiting for next financial year
- For experience gaps: mention joint ventures with experienced partners, or pilot project approach
- For missing documents: specify exactly what to obtain and from where

PARAGRAPH 4 — STRATEGIC ALTERNATIVES:
If direct bidding is risky, offer 2-3 alternative strategies:
- Consortium formation (who to partner with, how to structure)
- Subcontracting arrangement
- Applying for smaller lots/sub-tenders
- Improving profile for the next tender cycle
- MSME-specific schemes that could help (NSIC, Udyam benefits)

Write with authority and empathy — this company is counting on your advice to make a real business decision.
"""
    try:
        return _call_groq(prompt, temperature=0.4, max_tokens=1500)
    except Exception as e:
        return f"AI analysis failed: {str(e)}"
