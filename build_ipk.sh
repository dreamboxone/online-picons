#!/bin/sh
set -eu

# Keep the legacy entry point, but use the same builder, payload, package name,
# and PLUGIN_VERSION as the DEB package.
exec python3 "$(dirname "$0")/build_deb.py" --format ipk
