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
VERSION = "1.0.4"
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


def make_menu_icon(path, kind):
    width = height = 48
    pixels = [0] * (width * height * 4)

    def set_pixel(x, y, color):
        if 0 <= x < width and 0 <= y < height:
            offset = (y * width + x) * 4
            pixels[offset:offset + 4] = color

    blue = (40, 132, 220, 255)
    green = (37, 173, 96, 255)
    white = (255, 255, 255, 255)
    color = green if kind == "download" else blue

    for y in range(height):
        for x in range(width):
            dx, dy = x - 24, y - 24
            if dx * dx + dy * dy <= 21 * 21:
                set_pixel(x, y, color)

    if kind == "download":
        for y in range(10, 29):
            for x in range(21, 27):
                set_pixel(x, y, white)
        for y in range(23, 34):
            spread = y - 23
            for x in range(24 - spread, 25 + spread):
                set_pixel(x, y, white)
        for y in range(36, 40):
            for x in range(13, 36):
                set_pixel(x, y, white)
    elif kind == "about":
        for y in range(20, 36):
            for x in range(21, 27):
                set_pixel(x, y, white)
        for y in range(11, 17):
            for x in range(21, 27):
                set_pixel(x, y, white)
    else:
        for y in range(14, 35):
            for x in range(14, 35):
                dx, dy = x - 24, y - 24
                if 9 * 9 <= dx * dx + dy * dy <= 12 * 12:
                    set_pixel(x, y, white)
        for start_x, start_y, end_x, end_y in (
            (21, 7, 27, 15), (21, 33, 27, 41),
            (7, 21, 15, 27), (33, 21, 41, 27),
        ):
            for y in range(start_y, end_y):
                for x in range(start_x, end_x):
                    set_pixel(x, y, white)

    png(path, width, height, pixels)


def make_dot_icon(path, color):
    width = height = 32
    pixels = []
    for y in range(height):
        for x in range(width):
            dx, dy = x - 16, y - 16
            pixels.extend(color if dx * dx + dy * dy <= 13 * 13 else (0, 0, 0, 0))
    png(path, width, height, pixels)


def add_bytes(tar, name, data, mode=0o644):
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mode = mode
    info.mtime = int(os.environ.get("SOURCE_DATE_EPOCH", "1767225600"))
    tar.addfile(info, io.BytesIO(data))


def make_tar(entries, directories=None):
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.GNU_FORMAT) as tar:
        for name in directories or []:
            info = tarfile.TarInfo(name.rstrip("/") + "/")
            info.type = tarfile.DIRTYPE
            info.mode = 0o755
            info.mtime = int(os.environ.get("SOURCE_DATE_EPOCH", "1767225600"))
            tar.addfile(info)
        for name, source, mode in entries:
            with open(source, "rb") as item:
                data = item.read()
                if (
                    source.endswith((".py", ".sh", ".yml", ".yaml"))
                    or os.path.basename(source) in ("control", "postinst", "prerm")
                ):
                    data = data.replace(b"\r\n", b"\n")
                add_bytes(tar, name, data, mode)
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
    make_menu_icon(os.path.join(plugin_stage, "settings.png"), "settings")
    make_menu_icon(os.path.join(plugin_stage, "download.png"), "download")
    make_menu_icon(os.path.join(plugin_stage, "about.png"), "about")
    make_dot_icon(os.path.join(plugin_stage, "dot-checking.png"), (125, 125, 125, 255))
    make_dot_icon(os.path.join(plugin_stage, "dot-red.png"), (220, 45, 45, 255))
    make_dot_icon(os.path.join(plugin_stage, "dot-yellow.png"), (235, 190, 20, 255))
    make_dot_icon(os.path.join(plugin_stage, "dot-green.png"), (35, 190, 90, 255))

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
    data_directories = [
        "usr",
        "usr/lib",
        "usr/lib/enigma2",
        "usr/lib/enigma2/python",
        "usr/lib/enigma2/python/Plugins",
        "usr/lib/enigma2/python/Plugins/Extensions",
        PLUGIN_TARGET,
    ]
    data_tar = make_tar(data_entries, directories=data_directories)
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
