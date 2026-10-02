"""RevOS — Agentic Revenue Decision Engine. FastAPI entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import router
from config import settings

app = FastAPI(
    title=settings.APP_NAME,
    description="AI decision engine for B2B sales teams — predict, prioritize, prescribe, act.",
    version="0.1.0",
)

# Allowed origins including active Next.js development ports (3000 & 3001)
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "https://your-app.vercel.app",  # Production URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):(3000|3001|3002)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root():
    return {
        "name": "RevOS",
        "status": "running",
        "docs": "/docs",
        "endpoints": [
            "/api/deals",
            "/api/deals/{id}",
            "/api/risk/top",
            "/api/forecast",
            "/api/nba/{deal_id}",
            "/api/email/draft",
            "/api/simulator",
            "/api/query",
            "/api/ml/train",
            "/api/dashboard/summary",
            "/api/audit",
        ],
    }


@app.on_event("startup")
async def startup():
    from database import init_db
    init_db()
    print(f"[+] {settings.APP_NAME} started -- database initialized")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)