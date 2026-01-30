#!/bin/bash
set -e
root_dir="$(realpath "$(dirname "$0")/..")"
cd "${root_dir}/custom_components"
python3 -m mypy --show-error-codes --show-column-numbers powersensor
cd "${root_dir}"
python3 -m mypy --show-error-codes --show-column-numbers --disable-error-code=import-untyped tests
