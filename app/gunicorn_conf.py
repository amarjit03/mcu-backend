import multiprocessing
import os

# Production Gunicorn settings
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"

# Calculate workers dynamically (standard formula: 2 * CPU + 1)
default_workers = multiprocessing.cpu_count() * 2 + 1
workers = int(os.getenv("WEB_CONCURRENCY", default_workers))

# Use Uvicorn worker class for ASGI application serving
worker_class = "uvicorn.workers.UvicornWorker"

# Timeout and keepalive tuning
keepalive = 120
timeout = 120

# Standard out logging for container aggregation
loglevel = "info"
accesslog = "-"
errorlog = "-"
