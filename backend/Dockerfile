FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as a non-root user instead of root inside the container.
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Apply DB migrations (idempotent; adopts an existing create_all DB safely) before
# serving. A migration failure aborts startup rather than serving a bad schema.
CMD ["sh", "-c", "python scripts/migrate.py && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
