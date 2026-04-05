#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_DIR="${ROOT_DIR}/pet_images/src"
OUTPUT_DIR="${ROOT_DIR}/pet_images"
MAX_SIZE="${1:-512}"

if ! command -v magick >/dev/null 2>&1; then
  echo "magick is required but not installed" >&2
  exit 1
fi

if [ ! -d "${SOURCE_DIR}" ]; then
  echo "source directory not found: ${SOURCE_DIR}" >&2
  exit 1
fi

mkdir -p "${OUTPUT_DIR}"
shopt -s nullglob

for image_path in "${SOURCE_DIR}"/*.png; do
  base_name="$(basename "${image_path}")"
  output_path="${OUTPUT_DIR}/${base_name}"
  tmp_path="$(mktemp "${output_path}.XXXXXX")"
  magick "${image_path}" \
    -trim +repage \
    -resize "${MAX_SIZE}x${MAX_SIZE}" \
    -strip \
    -define png:compression-level=9 \
    -define png:compression-filter=5 \
    -define png:compression-strategy=1 \
    "${tmp_path}"
  mv "${tmp_path}" "${output_path}"
done
