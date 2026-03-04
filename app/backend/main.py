import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from dotenv import load_dotenv

load_dotenv()

from database import create_tables
from routers import auth_router, tender, company, compliance, copilot

app = FastAPI(
    title="JustBidIt API",
    description="AI-powered tender intelligence for Indian MSMEs",
    version="1.0.0"
)

# ── Force CORS headers on every response ─────────────────────
class ForceCORSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Handle preflight
        if request.method == "OPTIONS":
            response = JSONResponse(content={}, status_code=200)
            response.headers["Access-Control-Allow-Origin"]  = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
            response.headers["Access-Control-Allow-Headers"] = "*"
            response.headers["Access-Control-Max-Age"]       = "86400"
            return response

        response = await call_next(request)
        response.headers["Access-Control-Allow-Origin"]  = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response

app.add_middleware(ForceCORSMiddleware)

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

# ── Health ────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "service": "JustBidIt API"}

@app.get("/")
def root():
    return {"message": "JustBidIt API is running. Visit /docs for the API reference."}
