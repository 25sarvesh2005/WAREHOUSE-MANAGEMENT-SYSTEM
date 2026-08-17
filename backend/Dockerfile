# ──────────────────────────────────────────────────────────────────────────────
# Stage 1: builder — install deps into a venv so the runtime stage stays lean
# ──────────────────────────────────────────────────────────────────────────────
FROM python:3.13-slim AS builder

# System deps needed to compile asyncpg / psycopg / bcrypt native extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only the dependency manifest first for Docker layer caching
COPY requirements.txt .

RUN pip install --upgrade pip \
 && pip install --no-cache-dir --prefix=/install -r requirements.txt

# ──────────────────────────────────────────────────────────────────────────────
# Stage 2: runtime — minimal image, no build tools, non-root user
# ──────────────────────────────────────────────────────────────────────────────
FROM python:3.13-slim AS runtime

# Runtime libpq only (no headers or compilers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

WORKDIR /app

# Copy source code
COPY . .

# Create and switch to a non-root user for security
RUN mkdir -p /app/logs \
 && addgroup --system warehouse \
 && adduser --system --ingroup warehouse warehouse \
 && chown -R warehouse:warehouse /app
USER warehouse

# Expose the application port
EXPOSE 8080

# Liveness check — hits the lightweight /health/live endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health/live')" || exit 1

# Default entrypoint — override via docker-compose or cloud platform config
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]
