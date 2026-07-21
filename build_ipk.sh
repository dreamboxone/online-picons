#!/bin/sh
set -eu

PACKAGE="enigma2-plugin-extensions-online-picons"
VERSION="1.0.11-r0"
ARCH="all"
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
BUILD_DIR="$ROOT/.build-ipk"
CONTROL_DIR="$BUILD_DIR/CONTROL"
PLUGIN_DIR="$BUILD_DIR/usr/lib/enigma2/python/Plugins/Extensions/OnlinePicons"
DIST_DIR="$ROOT/dist"
EPOCH=${SOURCE_DATE_EPOCH:-1767225600}
OUTPUT="$DIST_DIR/${PACKAGE}_${VERSION}_${ARCH}.ipk"

cleanup() {
    rm -rf "$BUILD_DIR"
}
trap cleanup EXIT INT TERM

command -v python3 >/dev/null 2>&1 || {
    echo "Error: python3 is required to generate plugin icons." >&2
    exit 1
}
command -v ar >/dev/null 2>&1 || {
    echo "Error: ar (binutils) is required." >&2
    exit 1
}

rm -rf "$BUILD_DIR"
mkdir -p "$CONTROL_DIR" "$PLUGIN_DIR" "$DIST_DIR"

cp "$ROOT/CONTROL/control" "$CONTROL_DIR/control"
cp "$ROOT/CONTROL/postinst" "$CONTROL_DIR/postinst"
cp -R "$ROOT/OnlinePicons/." "$PLUGIN_DIR/"
find "$PLUGIN_DIR" -type d -name __pycache__ -prune -exec rm -rf {} +
find "$PLUGIN_DIR" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete

PYTHONPATH="$ROOT" python3 - "$PLUGIN_DIR" <<'PY'
import os
import sys

from build_deb import (
    make_check_icon,
    make_dot_icon,
    make_menu_icon,
    make_plugin_icon,
    make_youtube_icon,
)

target = sys.argv[1]
make_plugin_icon(os.path.join(target, "plugin.png"))
make_menu_icon(os.path.join(target, "settings.png"), "settings")
make_menu_icon(os.path.join(target, "download.png"), "download")
make_menu_icon(os.path.join(target, "about.png"), "about")
make_dot_icon(os.path.join(target, "dot-checking.png"), (125, 125, 125, 255))
make_dot_icon(os.path.join(target, "dot-red.png"), (220, 45, 45, 255))
make_dot_icon(os.path.join(target, "dot-yellow.png"), (235, 190, 20, 255))
make_dot_icon(os.path.join(target, "dot-green.png"), (35, 190, 90, 255))
make_check_icon(os.path.join(target, "check.png"))
make_youtube_icon(os.path.join(target, "youtube.png"))
PY

for required in plugin.py __init__.py plugin.png settings.png download.png about.png \
    dot-checking.png dot-red.png dot-yellow.png dot-green.png check.png youtube.png; do
    test -s "$PLUGIN_DIR/$required" || {
        echo "Error: missing package file: $required" >&2
        exit 1
    }
done

CONTROL_VERSION=$(sed -n 's/^Version:[[:space:]]*//p' "$CONTROL_DIR/control")
test "$CONTROL_VERSION" = "$VERSION" || {
    echo "Error: CONTROL version ($CONTROL_VERSION) does not match $VERSION." >&2
    exit 1
}

find "$BUILD_DIR" -type d -exec chmod 755 {} +
find "$PLUGIN_DIR" -type f -exec chmod 644 {} +
chmod 644 "$CONTROL_DIR/control"
chmod 755 "$CONTROL_DIR/postinst"

printf '2.0\n' > "$BUILD_DIR/debian-binary"

(
    cd "$CONTROL_DIR"
    tar --sort=name --format=gnu --owner=0 --group=0 --numeric-owner \
        --mtime="@$EPOCH" -czf "$BUILD_DIR/control.tar.gz" .
)
(
    cd "$BUILD_DIR"
    tar --sort=name --format=gnu --owner=0 --group=0 --numeric-owner \
        --mtime="@$EPOCH" -czf "$BUILD_DIR/data.tar.gz" usr
)

rm -f "$OUTPUT"
(
    cd "$BUILD_DIR"
    ar cr "$OUTPUT" debian-binary control.tar.gz data.tar.gz
)

echo "Built: $OUTPUT"
