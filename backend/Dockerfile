# --- Build Stage ---
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies (includes libs needed by unstructured, pymupdf, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libmagic1 \
    libgl1 \
    libglib2.0-0 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Install CPU-only PyTorch first (prevents pip from resolving the ~5GB CUDA variant)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install project dependencies (cached layer — only rebuilds when pyproject.toml changes)
COPY pyproject.toml README.md ./
RUN mkdir app && touch app/__init__.py && \
    pip install --no-cache-dir . 2>&1 && \
    pip uninstall -y hivemind-rag && \
    rm -rf app

# --- Runtime Stage ---
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies (healthchecks, network diagnostics, doc processing)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    netcat-openbsd \
    libmagic1 \
    libgl1 \
    libglib2.0-0 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV APP_ENV=production

# Expose port
EXPOSE 8000

# Entrypoint
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
