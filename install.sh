#!/bin/sh
set -e

REPOSITORY="dreamboxone/online-picons"
VERSION="1.0.11"
DEB_NAME="enigma2-plugin-extensions-online-picons_${VERSION}_all.deb"
DEB_URL="https://raw.githubusercontent.com/${REPOSITORY}/main/releases/${DEB_NAME}"
TMP_DEB="/tmp/enigma2-plugin-extensions-online-picons.deb"
SETUP_LOG="/tmp/online-picons-setup.log"

extractor_available() {
    command -v unrar >/dev/null 2>&1 ||
        command -v 7z >/dev/null 2>&1 ||
        command -v 7za >/dev/null 2>&1 ||
        command -v bsdtar >/dev/null 2>&1
}

prepare_download_support() {
    if extractor_available; then
        return 0
    fi
    echo "Preparing Online Picons download support..."
    if ! command -v apt-get >/dev/null 2>&1; then
        echo "Error: unable to prepare Online Picons." >&2
        return 1
    fi
    apt-get update >"$SETUP_LOG" 2>&1 || true
    for package in unrar unrar-free p7zip-full p7zip; do
        if apt-get install -y "$package" >>"$SETUP_LOG" 2>&1; then
            break
        fi
    done
    if ! extractor_available; then
        echo "Error: unable to prepare Online Picons. See $SETUP_LOG" >&2
        return 1
    fi
}

echo "Downloading $DEB_URL"
if command -v wget >/dev/null 2>&1; then
    wget -O "$TMP_DEB" "$DEB_URL"
elif command -v curl >/dev/null 2>&1; then
    curl -fL -o "$TMP_DEB" "$DEB_URL"
else
    echo "Error: wget or curl is required." >&2
    exit 1
fi

prepare_download_support
dpkg -i "$TMP_DEB"
echo "Online Picons installed. Restart Enigma2 to show the plugin."
