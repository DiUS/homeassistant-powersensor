#!/bin/bash
rootdir="$(dirname "$0")/.."
export PYTHONPATH="${rootdir}/custom_components/powersensor"
export PYTHONDONTWRITEBYTECODE=1
pytest "$(dirname "$0")/../tests"
