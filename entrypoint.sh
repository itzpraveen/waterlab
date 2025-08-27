#!/usr/bin/env sh
set -e

# Default values
PORT=${PORT:-8000}
WEB_CONCURRENCY=${WEB_CONCURRENCY:-3}
WEB_TIMEOUT=${WEB_TIMEOUT:-120}
MAX_REQUESTS=${MAX_REQUESTS:-1000}
MAX_REQUESTS_JITTER=${MAX_REQUESTS_JITTER:-100}
KEEP_ALIVE=${KEEP_ALIVE:-5}

echo "Applying database migrations..."
python manage.py migrate --noinput

# Optionally collect static at runtime (disabled by default)
if [ "${COLLECTSTATIC_ON_START:-0}" = "1" ]; then
  echo "Collecting static files at runtime..."
  python manage.py collectstatic --noinput
fi

# Ensure an admin user exists (idempotent management command)
echo "Ensuring admin user exists (create_admin)..."
python manage.py create_admin || true

echo "Starting gunicorn on port ${PORT} with ${WEB_CONCURRENCY} workers..."
exec gunicorn waterlab.wsgi:application \
  --bind 0.0.0.0:${PORT} \
  --workers ${WEB_CONCURRENCY} \
  --timeout ${WEB_TIMEOUT} \
  --max-requests ${MAX_REQUESTS} \
  --max-requests-jitter ${MAX_REQUESTS_JITTER} \
  --keep-alive ${KEEP_ALIVE} \
  --worker-tmp-dir /dev/shm \
  --access-logfile - \
  --error-logfile -
