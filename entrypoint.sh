#!/bin/sh
set -e

# Run database migrations using Alembic
echo "Applying database migrations..."
alembic upgrade head

# Start application
echo "Starting application server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
