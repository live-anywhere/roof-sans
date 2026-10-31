#!/usr/bin/env bash
# Copies the fonts the specimen app declares into assets/fonts/.
# Usage: tool/stage_fonts.sh <roof.ttf> <pretendard-static-dir>
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "usage: $0 <roof.ttf> <pretendard-static-dir>" >&2
  exit 2
fi

roof="$1"
pretendard_dir="$2"
dest="$(cd "$(dirname "$0")/.." && pwd)/assets/fonts"

mkdir -p "$dest"
cp "$roof" "$dest/RoofSansVariable.ttf"
cp "$pretendard_dir/PretendardJP-Regular.ttf" "$dest/"
cp "$pretendard_dir/PretendardJP-Bold.ttf" "$dest/"
echo "staged fonts in $dest"
