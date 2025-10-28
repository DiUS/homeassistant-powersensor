#!/bin/bash

set -euo pipefail

cur_dir="${PWD}"
this_dir=$(dirname "$0")
root_dir="${this_dir}/.."

cd "${root_dir}" || exit 1

ref="$(git describe --always)"
manifest_ver=$(jq -r .version custom_components/powersensor/manifest.json)
if [ "${ref}" != "v${manifest_ver}" ]
then
  echo "Error: Current git description ${ref} does not match claimed version v${manifest_ver}!"
  exit 1
fi

zipfile="${cur_dir}/powersensor-${ref}.zip" 
zip "${zipfile}" -r \
  hacs.json \
  README.md \
  custom_components/powersensor/* \
  --exclude "**/__pycache__/*" \

relfile="$(realpath -s --relative-to="${cur_dir}" "${zipfile}")"

echo "Packaged as: ${relfile}"
exit 0
