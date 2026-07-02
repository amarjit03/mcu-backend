#!/bin/sh
set -e

echo "=== BOOTSTRAP: RUNNING DATABASE MIGRATIONS ==="
python -m alembic upgrade head

echo "=== BOOTSTRAP: CHECKING SEED DATA ==="
python -m app.db.seed

echo "=== BOOTSTRAP: STARTING PRODUCTION GUNICORN SERVER ==="
exec gunicorn app.main:app -c app/gunicorn_conf.py
