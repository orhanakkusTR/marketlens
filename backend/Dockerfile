# MarketLens backend (development)
# uv ile bağımlılık yönetimi. Source kod docker-compose tarafından bind-mount edilir.
FROM python:3.12-slim

# uv binary
COPY --from=ghcr.io/astral-sh/uv:0.5.18 /uv /uvx /bin/

# Bazı Python paketleri (asyncpg, bcrypt, lxml vs.) için derleme araçları
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

EXPOSE 8000

# Source kod docker-compose tarafından bind-mount edilir.
# Container açılışında uv sync çalışır:
#  - Eğer uv.lock yoksa, oluşturur ve host'a yazar (commit edilmesi gerekir)
#  - Varsa, .venv'i ona göre günceller
# Sonra uvicorn --reload ile FastAPI başlatılır.
CMD ["sh", "-c", "uv sync && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"]
