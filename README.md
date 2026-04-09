# JustBidIt — AI Tender Intelligence for Indian MSMEs

> Upload any government tender PDF. Get an instant compliance score, identify every gap, and generate a professional bid proposal — all in under 60 seconds.

**Live Demo:** [just-bid-it.vercel.app](https://just-bid-it.vercel.app)

---

## What is JustBidIt?

Indian MSMEs lose crores worth of government contracts every year — not because they're unqualified, but because they can't navigate the complexity of tender documents. A typical GeM or CPPP tender is 40-80 pages of legal and technical language that takes hours to manually review.

JustBidIt automates this entire process:

1. **Upload** any tender PDF from GeM, CPPP, NIC or state portals
2. **Get** an instant AI-powered compliance score against your company profile
3. **See** every gap — disqualifying, major and minor — with actionable fixes
4. **Generate** a complete 9-section professional bid proposal in one click
5. **Ask** the AI copilot any question about the tender in plain language

---

## Features

| Feature | Description |
|---|---|
| PDF Intelligence | Extracts all eligibility criteria, deadlines, documents and key clauses from any tender PDF |
| Compliance Engine | Rule-based 0-100 scoring system with transparent deductions per gap |
| Strategic Analysis | AI-written 4-paragraph analysis with action plan and alternative strategies |
| Bid Draft Generation | Complete 9-section professional proposal personalised to your company |
| AI Copilot | Multi-turn Q&A about the tender — eligibility, documents, EMD, deadlines |
| Tender Search | Live search across GeM and CPPP portals |
| Company Profile | Save once, reuse across all tenders |
| Tender History | All uploaded tenders with status and one-click reanalysis |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | HTML, CSS, Vanilla JavaScript |
| Backend | Python 3.12, FastAPI, Uvicorn |
| Database | SQLite (dev) / PostgreSQL (prod) |
| ORM | SQLAlchemy |
| Authentication | JWT (python-jose), bcrypt (passlib) |
| AI — Primary | Google Gemini 2.0 Flash |
| AI — Fallback | Groq / Llama 3.3 70B |
| PDF Processing | PyMuPDF, pdfplumber |
| Tunneling | Cloudflare Tunnel |
| Frontend Hosting | Vercel |

---

## Project Structure

```
JustBidIt/
├── app/
│   ├── backend/
│   │   ├── main.py               # FastAPI app, CORS, routers
│   │   ├── database.py           # SQLAlchemy setup, SQLite/PostgreSQL
│   │   ├── models.py             # Database models
│   │   ├── schemas.py            # Pydantic schemas
│   │   ├── auth.py               # JWT + bcrypt helpers
│   │   ├── requirements.txt
│   │   ├── Dockerfile
│   │   ├── routers/
│   │   │   ├── auth_router.py    # Register, login, /me
│   │   │   ├── tender.py         # PDF upload + extraction
│   │   │   ├── company.py        # Company profile CRUD
│   │   │   ├── compliance.py     # Scoring engine
│   │   │   ├── copilot.py        # Bid draft + Q&A
│   │   │   └── search.py         # GeM + CPPP search
│   │   └── services/
│   │       ├── gemini_client.py  # Gemini + Groq fallback
│   │       ├── pdf_extractor.py  # PDF text extraction
│   │       └── tender_scraper.py # GeM + CPPP scraper
│   └── frontend/
│       ├── index.html            # Landing page
│       ├── login.html
│       ├── register.html
│       ├── dashboard.html        # Main app
│       ├── proposal.html         # Bid draft + copilot
│       ├── search.html           # Tender search
│       ├── css/
│       │   └── style.css
│       └── js/
│           ├── api.js            # API client + auth
│           ├── dashboard.js      # Dashboard logic
│           └── proposal.js       # Proposal page logic
```

---

## Local Development

### Prerequisites
- Python 3.12+
- Git

### Setup

```bash
# Clone the repo
git clone https://github.com/yourusername/JustBidIt.git
cd JustBidIt/app/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your API keys
```

### Environment Variables

```env
SECRET_KEY=your-long-random-secret-key
GEMINI_API_KEY=your-gemini-api-key
GROQ_API_KEY=your-groq-api-key
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

Get API keys:
- Gemini: [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) — free, no card
- Groq: [console.groq.com](https://console.groq.com) — free, no card

### Run

```bash
# Terminal 1 — Backend
cd app/backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — Frontend
cd app/frontend
python3 -m http.server 3000
```

Open [http://localhost:3000](http://localhost:3000)

### Or use the start script

```bash
# Mac/Linux
chmod +x start.sh
./start.sh

# Windows
start.bat
```

---

## Deployment

### Frontend — Vercel
1. Connect GitHub repo to [vercel.com](https://vercel.com)
2. Set root directory to `app/frontend`
3. Deploy

### Backend — Cloudflare Tunnel (free, no server needed)
```bash
# Install cloudflared
brew install cloudflared  # Mac
# or download from cloudflare.com

# Start backend
uvicorn main:app --host 0.0.0.0 --port 8000

# Expose publicly
cloudflared tunnel --url http://localhost:8000
```

Update `app/frontend/js/api.js` with the tunnel URL.

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/register` | Create account |
| POST | `/auth/login` | Login, returns JWT |
| GET | `/auth/me` | Current user |
| POST | `/tenders/upload` | Upload + extract PDF |
| GET | `/tenders` | List tenders |
| GET | `/tenders/{id}` | Get tender |
| POST | `/companies` | Save company profile |
| GET | `/companies/{id}` | Get company |
| POST | `/compliance/score` | Run compliance check |
| POST | `/copilot/generate-draft` | Generate bid proposal |
| POST | `/copilot/ask` | Ask copilot |
| GET | `/search/tenders` | Search GeM + CPPP |
| GET | `/health` | Health check |

Full interactive docs at `/docs` when running locally.

---

## How It Works

```
PDF Upload
    ↓
Text Extraction (PyMuPDF)
    ↓
AI Structuring (Gemini 2.0 Flash)
    ↓ structured JSON
Rule-Based Compliance Engine
    ↓ score + gaps
AI Strategic Analysis (Gemini 2.0 Flash)
    ↓
Score + Gaps + Analysis → Frontend
    ↓
Bid Draft Generation (on demand)
    ↓
AI Copilot Q&A (multi-turn session)
```

---

## AI Approach

All AI features use **Google Gemini 2.0 Flash** as the primary model with **Groq / Llama 3.3 70B** as an automatic fallback when Gemini rate limits are hit. Users never see an error — the switch is transparent.

Four prompt-engineered AI functions:
- **Extraction** — zero-temperature structured JSON extraction with strict schema
- **Compliance Analysis** — 4-paragraph strategic narrative with action plan
- **Bid Draft** — 9-section proposal with company-specific personalisation
- **Copilot** — domain-expert Q&A with 8-turn conversation memory

All prompts are tuned for the Indian procurement ecosystem — GeM portal, GFR 2017, MSME procurement policy, Udyam registration, EMD exemptions.

---

## Built For

Indian MSMEs — the 63 million small businesses that collectively lose billions in government contracts annually due to procurement complexity.

---

*Built with by Team JustBidIt*
