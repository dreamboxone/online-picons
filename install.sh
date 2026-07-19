#!/bin/sh
set -e

REPOSITORY="dreamboxone/online-picons"
VERSION="1.0.5"
DEB_NAME="enigma2-plugin-extensions-online-picons_${VERSION}_all.deb"
DEB_URL="https://raw.githubusercontent.com/${REPOSITORY}/main/releases/${DEB_NAME}"
TMP_DEB="/tmp/enigma2-plugin-extensions-online-picons.deb"

echo "Downloading $DEB_URL"
if command -v wget >/dev/null 2>&1; then
    wget -O "$TMP_DEB" "$DEB_URL"
elif command -v curl >/dev/null 2>&1; then
    curl -fL -o "$TMP_DEB" "$DEB_URL"
else
    echo "Error: wget or curl is required." >&2
    exit 1
fi

dpkg -i "$TMP_DEB"
echo "Online Picons installed. Restart Enigma2 to show the plugin."
