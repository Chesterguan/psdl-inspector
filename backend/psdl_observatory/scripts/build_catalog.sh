#!/usr/bin/env bash
# Generate an Observatory catalog.json from a parquet lake (footers only, no PHI)
# and publish it atomically into a catalog directory the Inspector backend reads.
#
#   build_catalog.sh <parquet-root> <catalog-dir>
set -euo pipefail

ROOT="${1:?usage: build_catalog.sh <parquet-root> <catalog-dir>}"
DEST="${2:?usage: build_catalog.sh <parquet-root> <catalog-dir>}"

if [ ! -d "$ROOT" ]; then
  echo "error: not a directory: $ROOT" >&2
  exit 2
fi

mkdir -p "$DEST"
# Temp dir on the SAME filesystem as DEST so the final rename is atomic.
TMP="$(mktemp -d "${DEST%/}/.catalog.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

python -m psdl_observatory.cli catalog "$ROOT" --out "$TMP" --json
mv -f "$TMP/catalog.json" "$DEST/catalog.json"
echo "wrote $DEST/catalog.json"
