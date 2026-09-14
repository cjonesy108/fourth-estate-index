from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import journalists, methodology, outlets, ownership, lookup

app = FastAPI(
    title="Fourth Estate Index API",
    description="Journalistic integrity scoring grounded in the SPJ Code of Ethics.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://fourth-estate-index.vercel.app",
    ],
    allow_origin_regex=r"^chrome-extension://.*$",
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(journalists.router, prefix="/api/journalists", tags=["journalists"])
app.include_router(outlets.router,    prefix="/api/outlets",     tags=["outlets"])
app.include_router(methodology.router, prefix="/api/methodology", tags=["methodology"])
app.include_router(ownership.router,   prefix="/api/ownership",   tags=["ownership"])
app.include_router(lookup.router,      prefix="/api/lookup",      tags=["lookup"])


@app.get("/api/health")
async def health():
    return {"status": "ok"}
