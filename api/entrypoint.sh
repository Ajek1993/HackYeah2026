#!/bin/sh
set -e

echo "=== Running tests ==="
pytest tests/ -v --tb=short
echo "=== Tests passed ==="

exec "$@"
