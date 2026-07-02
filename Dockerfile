FROM python:3.12-slim

# Set python runtime environmental flags
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

WORKDIR /app

# Install runtime utilities (like curl for container healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source tree and migration directories
COPY app/ app/
COPY migrations/ migrations/
COPY alembic.ini .
COPY seed.py .
COPY entrypoint.sh .

# Configure permission scopes
RUN chmod +x entrypoint.sh

# Expose server port
EXPOSE 8000

# Execute entrypoint
ENTRYPOINT ["./entrypoint.sh"]
