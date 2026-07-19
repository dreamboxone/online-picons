#!/usr/bin/env python3
"""Build a reproducible DreamOS .deb without requiring dpkg-deb."""

import gzip
import io
import os
import shutil
import struct
import tarfile
import time
import zlib

ROOT = os.path.abspath(os.path.dirname(__file__))
OUTPUT = os.path.join(ROOT, "dist")
PACKAGE = "enigma2-plugin-extensions-online-picons"
VERSION = "1.0.0"
PLUGIN_TARGET = "usr/lib/enigma2/python/Plugins/Extensions/OnlinePicons"


def png(path, width, height, pixels):
    def chunk(kind, data):
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    raw = b"".join(
        b"\x00" + bytes(bytearray(pixels[y * width * 4:(y + 1) * width * 4]))
        for y in range(height)
    )
    data = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )
    with open(path, "wb") as output:
        output.write(data)


def make_plugin_icon(path):
    width = height = 128
    pixels = []
    for y in range(height):
        for x in range(width):
            dx, dy = x - 64, y - 64
            radius = (dx * dx + dy * dy) ** 0.5
            if radius < 52:
                color = (27, 126, 214, 255)
            else:
                color = (0, 0, 0, 0)
            if 48 < x < 80 and 27 < y < 74:
                color = (255, 255, 255, 255)
            if 38 < x < 90 and 65 < y < 78 and abs(x - 64) < (78 - y) * 2:
                color = (255, 255, 255, 255)
            if 37 < x < 91 and 85 < y < 94:
                color = (255, 255, 255, 255)
            pixels.extend(color)
    png(path, width, height, pixels)


def add_bytes(tar, name, data, mode=0o644):
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mode = mode
    info.mtime = int(os.environ.get("SOURCE_DATE_EPOCH", "1767225600"))
    tar.addfile(info, io.BytesIO(data))


def make_tar(entries):
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.GNU_FORMAT) as tar:
        for name, source, mode in entries:
            with open(source, "rb") as item:
                add_bytes(tar, name, item.read(), mode)
    compressed = io.BytesIO()
    with gzip.GzipFile(fileobj=compressed, mode="wb", mtime=0) as output:
        output.write(raw.getvalue())
    return compressed.getvalue()


def ar_member(name, data, timestamp=0, mode=0o100644):
    encoded_name = (name + "/").ljust(16).encode("ascii")
    header = (
        encoded_name
        + str(timestamp).ljust(12).encode("ascii")
        + b"0     "
        + b"0     "
        + oct(mode)[2:].ljust(8).encode("ascii")
        + str(len(data)).ljust(10).encode("ascii")
        + b"`\n"
    )
    return header + data + (b"\n" if len(data) % 2 else b"")


def main():
    staging = os.path.join(ROOT, ".build")
    shutil.rmtree(staging, ignore_errors=True)
    os.makedirs(staging)
    plugin_stage = os.path.join(staging, "OnlinePicons")
    shutil.copytree(
        os.path.join(ROOT, "OnlinePicons"),
        plugin_stage,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )
    make_plugin_icon(os.path.join(plugin_stage, "plugin.png"))

    control_entries = []
    for name in ("control", "postinst", "prerm"):
        mode = 0o755 if name in ("postinst", "prerm") else 0o644
        control_entries.append((name, os.path.join(ROOT, "DEBIAN", name), mode))

    data_entries = []
    for name in sorted(os.listdir(plugin_stage)):
        source = os.path.join(plugin_stage, name)
        if os.path.isfile(source):
            data_entries.append((
                PLUGIN_TARGET + "/" + name,
                source,
                0o644,
            ))

    control_tar = make_tar(control_entries)
    data_tar = make_tar(data_entries)
    os.makedirs(OUTPUT, exist_ok=True)
    output_path = os.path.join(
        OUTPUT, "%s_%s_all.deb" % (PACKAGE, VERSION)
    )
    with open(output_path, "wb") as package:
        package.write(b"!<arch>\n")
        package.write(ar_member("debian-binary", b"2.0\n"))
        package.write(ar_member("control.tar.gz", control_tar))
        package.write(ar_member("data.tar.gz", data_tar))
    shutil.rmtree(staging, ignore_errors=True)
    print(output_path)


if __name__ == "__main__":
    main()
