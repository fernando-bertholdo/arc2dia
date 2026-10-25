#!/bin/sh
# Rebuild skill/arc2dia/scripts/arc2dia.pyz from the arc2dia package with `python3 -m zipapp`.
#
# The archive holds the package's .py files and a __main__.py that passes main()'s exit code on
# (zipapp's own -m option would drop it). File times are pinned so a rebuild of unchanged
# sources gives the same contents.
#
# Usage: scripts/build_skill.sh
#   PYTHON=python3.9 scripts/build_skill.sh        build with another interpreter
#   ARC2DIA_PYZ_OUT=/tmp/x.pyz scripts/build_skill.sh   write somewhere else (tests)
set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
PY=${PYTHON:-python3}
OUT=${ARC2DIA_PYZ_OUT:-"$ROOT/skill/arc2dia/scripts/arc2dia.pyz"}

STAGE=$(mktemp -d "${TMPDIR:-/tmp}/arc2dia-pyz.XXXXXX")
trap 'rm -rf "$STAGE"' EXIT INT TERM

mkdir "$STAGE/arc2dia"
cp "$ROOT"/arc2dia/*.py "$STAGE/arc2dia/"
cat > "$STAGE/__main__.py" <<'EOF'
import sys

from arc2dia.cli import main

sys.exit(main())
EOF
find "$STAGE" -exec touch -t 198001020000 {} +

mkdir -p "$(dirname "$OUT")"
"$PY" -m zipapp "$STAGE" -o "$OUT" -p "/usr/bin/env python3"
chmod 755 "$OUT"
"$PY" "$OUT" --version
echo "built $OUT"
