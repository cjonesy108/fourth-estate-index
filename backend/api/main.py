from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import journalists, methodology

app = FastAPI(
    title="Fourth Estate Index API",
    description="Journalistic integrity scoring grounded in the SPJ Code of Ethics.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # expand for production
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(journalists.router, prefix="/api/journalists", tags=["journalists"])
app.include_router(methodology.router, prefix="/api/methodology", tags=["methodology"])


@app.get("/api/health")
async def health():
    return {"status": "ok"}
