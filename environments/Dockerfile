# Open Research Platform — Canonical Environment
# This Dockerfile is the single authoritative environment definition.
# All other dependency files (requirements.lock, environment.yml) feed into this.

FROM python:3.12-slim

LABEL org.opencontainers.image.title="open-research-platform"
LABEL org.opencontainers.image.description="Reproducible research execution environment"

WORKDIR /app

# System dependencies (add as needed for your research code)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY environments/requirements.lock ./requirements.lock
RUN pip install --no-cache-dir -r requirements.lock

# Copy platform source
COPY src/ ./src/
COPY schemas/ ./schemas/

# Default: run the runner
ENTRYPOINT ["python", "-m", "src.lib.runner"]
