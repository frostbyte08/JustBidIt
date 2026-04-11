import google.generativeai as genai
from groq import Groq
import json
import os
import re
import time
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY   = os.getenv("GROQ_API_KEY", "")
PROMPT_DIR     = os.path.join(os.path.dirname(__file__), "..", "prompts")

# ── Setup Gemini ──────────────────────────────────────────────
gemini_model = None
if GEMINI_API_KEY and GEMINI_API_KEY != "your_gemini_api_key_here":
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel("gemini-2.0-flash")
    print("✓ Gemini API configured")
else:
    print("(X) GEMINI_API_KEY not set")

# ── Setup Groq (fallback) ─────────────────────────────────────
groq_client = None
if GROQ_API_KEY and GROQ_API_KEY != "your_groq_api_key_here":
    groq_client = Groq(api_key=GROQ_API_KEY)
    print("✓ Groq API configured (fallback)")
else:
    print("(X) GROQ_API_KEY not set")


def _call_ai(prompt: str, temperature: float = 0.1, max_tokens: int = 2048) -> str:
    """
    Try Gemini first. If rate limited or unavailable, fall back to Groq.
    """
    # Try Gemini first
    if gemini_model:
        try:
            response = gemini_model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                )
            )
            return response.text
        except Exception as e:
            err = str(e).lower()
            if "quota" in err or "rate" in err or "limit" in err or "429" in err:
                print(f"Gemini rate limited — falling back to Groq")
            else:
                print(f"Gemini error: {e} — falling back to Groq")

    # Fall back to Groq
    if groq_client:
        response = groq_client.chat.completions.create(
            model       = "llama-3.3-70b-versatile",
            messages    = [{"role": "user", "content": prompt}],
            temperature = temperature,
            max_tokens  = max_tokens,
        )
        return response.choices[0].message.content

    raise Exception("No AI provider available. Set GEMINI_API_KEY or GROQ_API_KEY in .env")


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
    if not gemini_model and not groq_client:
        return {"error": "No AI provider configured. Add GEMINI_API_KEY or GROQ_API_KEY to .env"}

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
    "experience_note": "exact clause text or null",
    "required_certifications": [],
    "msme_preference": true or false,
    "msme_exemptions": [],
    "past_project_requirement": "description or null",
    "min_single_project_value": "number in INR Lakhs or null",
    "other_requirements": []
  }},
  "documents_required": [],
  "key_clauses": [],
  "sector": "IT/Construction/Healthcare/Defence/Education/Supply/Services/Other",
  "bid_security": "amount and format or null",
  "contract_duration": "duration string or null",
  "portal": "GeM/CPPP/NIC/State/Other"
}}

TENDER TEXT:
{text_to_send}"""

    try:
        raw_response = _call_ai(prompt, temperature=0.0, max_tokens=2048)
        parsed = _parse_json(raw_response)

        if parsed is None:
            print(f"WARNING: Could not parse JSON. Raw: {raw_response[:200]}")
            return {
                "tender_id": None, "title": "Tender (manual review needed)",
                "issuing_authority": "Unknown", "deadline": None, "estimated_value": None,
                "eligibility": {
                    "min_turnover": None, "turnover_note": None, "years_experience": None,
                    "experience_note": None, "required_certifications": [], "msme_preference": False,
                    "msme_exemptions": [], "past_project_requirement": None,
                    "min_single_project_value": None, "other_requirements": []
                },
                "documents_required": [], "key_clauses": [], "sector": "Unknown",
                "bid_security": None, "contract_duration": None, "portal": "Unknown",
                "_note": "AI extraction failed — please review manually"
            }
        return parsed
    except Exception as e:
        return {"error": f"AI error: {str(e)}"}


# ── 2. BID DRAFT GENERATION ───────────────────────────────────
def generate_bid_draft(tender_data: Dict, company_data: Dict, additional_context: Optional[str] = None) -> str:
    if not gemini_model and not groq_client:
        return "Error: No AI provider configured."

    projects = company_data.get("past_projects", [])
    projects_text = "\n".join([
        f"  • {p.get('name', 'N/A')} — Client: {p.get('client', 'N/A')}, "
        f"Value: Rs.{p.get('value', 0)}L, Completed: {p.get('year', 'N/A')}"
        for p in projects[:5]
    ]) or "  • No past projects listed"

    elig = tender_data.get("eligibility", {})
    certs = ", ".join(company_data.get("certifications", [])) or "None listed"
    docs  = ", ".join(tender_data.get("documents_required", [])) or "As per tender"

    prompt = f"""You are a senior procurement consultant in India who has helped 200+ MSMEs win government tenders worth over Rs.500 Crore.

TENDER DETAILS:
- Title: {tender_data.get('title', 'N/A')}
- Issuing Authority: {tender_data.get('issuing_authority', 'N/A')}
- Sector: {tender_data.get('sector', 'N/A')}
- Estimated Value: Rs.{tender_data.get('estimated_value', 'N/A')} Lakhs
- Contract Duration: {tender_data.get('contract_duration', 'As per tender')}
- Deadline: {tender_data.get('deadline', 'N/A')}
- Min Turnover Required: Rs.{elig.get('min_turnover', 'N/A')} Lakhs
- Experience Required: {elig.get('years_experience', 'N/A')} years
- Required Certifications: {', '.join(elig.get('required_certifications', [])) or 'None'}
- MSME Preference: {'Yes' if elig.get('msme_preference') else 'No'}
- Documents Required: {docs}

COMPANY PROFILE:
- Name: {company_data.get('name')}
- MSME Category: {company_data.get('msme_category', 'MSME').upper()}
- Annual Turnover: Rs.{company_data.get('annual_turnover', 0)} Lakhs
- Years in Operation: {company_data.get('years_in_operation', 0)} years
- Certifications: {certs}
- GST: {company_data.get('gst_number', 'As per records')}
- Past Projects:
{projects_text}

{f'SPECIAL INSTRUCTIONS: {additional_context}' if additional_context else ''}

Write a complete professional bid proposal with ALL 9 sections. Reference specific numbers and facts throughout:

# BID PROPOSAL
## {tender_data.get('title', 'Tender Response')}
### Submitted by: {company_data.get('name')}

## 1. COVER LETTER
## 2. COMPANY OVERVIEW
## 3. TECHNICAL COMPLIANCE STATEMENT
## 4. SCOPE UNDERSTANDING & APPROACH
## 5. RELEVANT PAST EXPERIENCE
## 6. TEAM & RESOURCE PLAN
## 7. QUALITY ASSURANCE
## 8. DECLARATIONS & COMPLIANCE
## 9. DOCUMENT INDEX

---
*Authorised Signatory | {company_data.get('name')} | Date: ___________*
"""
    try:
        return _call_ai(prompt, temperature=0.3, max_tokens=4096)
    except Exception as e:
        return f"Error generating draft: {str(e)}"


# ── 3. COPILOT Q&A ────────────────────────────────────────────
def copilot_answer(tender_data: Dict, question: str, conversation_history: List[Dict]) -> str:
    if not gemini_model and not groq_client:
        return "Error: No AI provider configured."

    history_text = ""
    for msg in conversation_history[-8:]:
        role = "Bidder" if msg["role"] == "user" else "Consultant"
        history_text += f"{role}: {msg['content']}\n\n"

    prompt = f"""You are an expert Indian government procurement consultant.

TENDER:
{json.dumps(tender_data, indent=2)}

{f"CONVERSATION:{chr(10)}{history_text}" if history_text else ""}

QUESTION: {question}

Answer directly and specifically. Give YES/NO/CONDITIONAL verdict for eligibility questions. Be concise.
"""
    try:
        return _call_ai(prompt, temperature=0.2, max_tokens=1024)
    except Exception as e:
        return f"Error: {str(e)}"


# ── 4. COMPLIANCE GAP ANALYSIS ────────────────────────────────
def analyze_compliance_gaps(tender_data: Dict, company_data: Dict, gaps: List[Dict]) -> str:
    if not gemini_model and not groq_client:
        return "AI analysis unavailable — add GEMINI_API_KEY or GROQ_API_KEY to .env"

    elig = tender_data.get("eligibility", {})
    disqualifying = [g for g in gaps if "DISQUALIFYING" in g.get("severity", "").upper()]
    major         = [g for g in gaps if "MAJOR" in g.get("severity", "").upper()]
    minor         = [g for g in gaps if "MINOR" in g.get("severity", "").upper()]

    gaps_summary = ""
    if disqualifying:
        gaps_summary += f"\nDISQUALIFYING ({len(disqualifying)}):\n"
        gaps_summary += "\n".join([f"  - {g.get('field')}: {g.get('note','')}" for g in disqualifying])
    if major:
        gaps_summary += f"\n\nMAJOR ({len(major)}):\n"
        gaps_summary += "\n".join([f"  - {g.get('field')}: {g.get('note','')}" for g in major])
    if minor:
        gaps_summary += f"\n\nMINOR ({len(minor)}):\n"
        gaps_summary += "\n".join([f"  - {g.get('field')}: {g.get('note','')}" for g in minor])

    prompt = f"""You are India's leading MSME procurement strategist.

TENDER: {tender_data.get('title')} | {tender_data.get('issuing_authority')}
REQUIREMENTS: Min Turnover Rs.{elig.get('min_turnover','N/A')}L | Experience: {elig.get('years_experience','N/A')} years | MSME: {'Yes' if elig.get('msme_preference') else 'No'}

COMPANY: {company_data.get('name')} | Turnover: Rs.{company_data.get('annual_turnover',0)}L | Experience: {company_data.get('years_in_operation',0)} years | MSME: {company_data.get('msme_category','N/A')}

GAPS:{gaps_summary if gaps_summary else ' None — fully eligible'}

Write 4 paragraphs:
1. Overall verdict — should they bid?
2. Critical gaps and consequences
3. Time-bound action plan (3-5 specific steps)
4. Alternative strategies (consortium, subcontracting, NSIC schemes)
"""
    try:
        return _call_ai(prompt, temperature=0.4, max_tokens=1500)
    except Exception as e:
        return f"AI analysis failed: {str(e)}"
