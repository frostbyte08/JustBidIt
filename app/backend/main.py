import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from database import create_tables
from routers import auth_router, tender, company, compliance, copilot

app = FastAPI(
    title="JustBidIt API",
    description="AI-powered tender intelligence for Indian MSMEs",
    version="1.0.0"
)

# ── CORS ──────────────────────────────────────────────────────
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://just-bid-it.vercel.app",
        os.getenv("FRONTEND_URL", ""),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────
app.include_router(auth_router.router)
app.include_router(tender.router)
app.include_router(company.router)
app.include_router(compliance.router)
app.include_router(copilot.router)

# ── Startup ───────────────────────────────────────────────────
@app.on_event("startup")
def startup():
    create_tables()
    print("✓ Database tables ready")

# ── Health check ──────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "service": "JustBidIt API"}

@app.get("/")
def root():
    return {"message": "JustBidIt API is running. Visit /docs for the API reference."}
