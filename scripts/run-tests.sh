#!/bin/bash
set -euo pipefail
rootdir="$(realpath "$(dirname "$0")/..")"
testsdir="${rootdir}/tests"
cd "${rootdir}/custom_components/powersensor"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=".:${rootdir}:${testsdir}/mocks"
export PYTEST_COVERAGE_DATA_FILE="${testsdir}/.coverage"
pytest \
  --asyncio-mode=auto \
  --cov=. \
  --cov-config="${testsdir}/.coveragerc" \
  --cov-report term-missing \
  --cache-clear \
  --capture=no \
  "${testsdir}" \
  "$@"
