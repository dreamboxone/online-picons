#!/bin/sh
set -eu

# Build both CPU-independent package formats from the same plugin payload.
# Architecture: all is intentional: the plugin is Python and has no native
# binaries, so the packages install on MIPS, ARM and ARM64 Enigma2 images.
exec python3 "$(dirname "$0")/build_deb.py" --format all
