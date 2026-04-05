#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_DIR="${ROOT_DIR}/pet_images/src"
OUTPUT_DIR="${ROOT_DIR}/pet_stickers"
MAX_SIZE="${1:-512}"
INNER_SIZE="${2:-492}"

if ! command -v magick >/dev/null 2>&1; then
  echo "magick is required but not installed" >&2
  exit 1
fi

mkdir -p "${OUTPUT_DIR}"
shopt -s nullglob

for image_path in "${SOURCE_DIR}"/*.png; do
  base_name="$(basename "${image_path}" .png)"
  output_path="${OUTPUT_DIR}/${base_name}.webp"
  magick "${image_path}" \
    -trim +repage \
    -resize "${INNER_SIZE}x${INNER_SIZE}" \
    -background none \
    -gravity center \
    -extent "${MAX_SIZE}x${MAX_SIZE}" \
    -define webp:method=6 \
    -define webp:lossless=true \
    "${output_path}"
done
