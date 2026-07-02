FROM python:3.12-slim

# Set python runtime environmental flags
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Install runtime utilities (like curl for container healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency definition files
COPY pyproject.toml uv.lock ./

# Install dependencies using uv into virtualenv
RUN uv sync --frozen --no-cache --no-dev

# Copy source tree and migration directories
COPY app/ app/
COPY migrations/ migrations/
COPY alembic.ini .
COPY entrypoint.sh .

# Configure permission scopes
RUN chmod +x entrypoint.sh

# Expose server port
EXPOSE 8080

# Execute entrypoint
ENTRYPOINT ["./entrypoint.sh"]
