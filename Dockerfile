# ============================================================
# RoadPulse AI - Production Container Specification
# Multi-stage secure build for FastAPI backend & YOLOv8 inference
# ============================================================

FROM python:3.11-slim AS builder

WORKDIR /app

# Install system compilation dependencies & OpenCV runtime libraries
RUN apt-get update && apt-get install --no-install-recommends -y \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies in virtualenv
COPY backend/requirements.txt /app/requirements.txt
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir -r /app/requirements.txt

# Final Runtime Image
FROM python:3.11-slim AS runner

WORKDIR /app

# Install OpenCV and runtime dependencies
RUN apt-get update && apt-get install --no-install-recommends -y \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtualenv from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ENVIRONMENT=production

# Create non-root application user for container security
RUN groupadd -g 1001 appuser && \
    useradd -u 1001 -g appuser -s /bin/bash -m appuser

# Copy application source code
COPY backend /app/backend
COPY ai_models /app/ai_models
COPY dashboard /app/dashboard

# Create writable upload and storage directories
RUN mkdir -p /app/uploads/images /app/uploads/videos /app/uploads/annotated /app/backend/migrations && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

WORKDIR /app/backend

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
