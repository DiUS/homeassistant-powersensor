#!/bin/bash
set -euo pipefail
rootdir="$(realpath "$(dirname "$0")/..")"
testsdir="${rootdir}/tests"
cd "${rootdir}/custom_components/powersensor"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=.
export PYTEST_COVERAGE_DATA_FILE="${testsdir}/.coverage"
pytest --cov=. --cov-config="${testsdir}/.coveragerc" --cache-clear "${testsdir}"
