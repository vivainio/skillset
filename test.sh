#!/bin/bash

fail=0

echo "=== Ruff lint ==="
ruff check skillset || fail=1

echo "=== Ruff format ==="
ruff format --check skillset || fail=1

echo "=== Unit + integration tests ==="
pytest tests -v --cov=skillset --cov-report=term-missing || fail=1

if [ "$fail" -eq 1 ]; then
  echo "=== Some checks FAILED ==="  
fi

echo "=== All checks passed ==="
