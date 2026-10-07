#!/bin/bash
# Rebuild the artwork and copy what the lock screen uses into ../assets/.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
python3 "$here/build.py"
rm -f "$here/../assets"/*.png
for d in "$here"/../build/*/; do
  id=$(basename "$d")
  for f in "$d"*.png; do
    case $(basename "$f") in
      preview*.png | poster.png | bullet.png | hint.png | progress_*.png) continue ;;
    esac
    cp "$f" "$here/../assets/v$id-$(basename "$f")"
  done
done
echo "assets/ updated"
