from fastapi import FastAPI

# Adım 1 — minimum çalışır FastAPI iskeleti.
# Adım 3'te core/config + structlog + middleware + global exception handler eklenecek.
# Adım 4'te /auth/* endpoint'leri.
app = FastAPI(
    title="MarketLens API",
    version="0.1.0",
    description="Kişisel kripto + emtia karar destek terminali",
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "marketlens-backend"}
