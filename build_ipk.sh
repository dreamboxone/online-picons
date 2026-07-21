#!/bin/bash
# Shell script to build .IPK for Enigma2 OE2.0

PKG_NAME="enigma2-plugin-extensions-onlinepicons"
VERSION="1.0.0"
ARCH="all"
OUT_DIR="build_tmp"

echo "Building IPK package..."

# Clean old builds
rm -rf $OUT_DIR
rm -f *.ipk

# Create folder structure
mkdir -p $OUT_DIR/CONTROL
mkdir -p $OUT_DIR/usr/lib/enigma2/python/Plugins/Extensions/OnlinePicons

# Copy control files
cp CONTROL/* $OUT_DIR/CONTROL/

# Copy plugin files
cp *.py $OUT_DIR/usr/lib/enigma2/python/Plugins/Extensions/OnlinePicons/ 2>/dev/null || true

# Set permissions
chmod 755 $OUT_DIR/CONTROL/post* 2>/dev/null || true

# Build control.tar.gz and data.tar.gz
cd $OUT_DIR
echo "2.0" > debian-binary

cd CONTROL
tar czvf ../control.tar.gz .
cd ..
rm -rf CONTROL

tar czvf data.tar.gz usr/
rm -rf usr

# Pack into IPK
ar r ../${PKG_NAME}_${VERSION}_${ARCH}.ipk debian-binary control.tar.gz data.tar.gz

cd ..
rm -rf $OUT_DIR

echo "Done! Generated: ${PKG_NAME}_${VERSION}_${ARCH}.ipk"
