#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE_DIR="${ROOT_DIR}/pet_images"
MAX_SIZE="${1:-256}"

if ! command -v magick >/dev/null 2>&1; then
  echo "magick is required but not installed" >&2
  exit 1
fi

shopt -s nullglob
for image_path in "${IMAGE_DIR}"/*.png; do
  tmp_path="$(mktemp "${image_path}.XXXXXX")"
  magick "${image_path}" \
    -resize "${MAX_SIZE}x${MAX_SIZE}" \
    -strip \
    -define png:compression-level=9 \
    -define png:compression-filter=5 \
    -define png:compression-strategy=1 \
    "${tmp_path}"
  mv "${tmp_path}" "${image_path}"
done
