#!/bin/bash
set -euo pipefail
rootdir="$(dirname "$0")/.."
pip install -r "${rootdir}/requirements.test.txt"
