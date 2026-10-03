#!/bin/sh
set -e
if [ "$APP_ENV" != "production" ]; then
    echo "=== Running tests ==="
    pytest tests/ -v --tb=short
    echo "=== Tests passed ==="
fi
exec "$@"
