#!/usr/bin/env python3
"""Build a reproducible DreamOS .deb without requiring dpkg-deb."""

import gzip
import io
import os
import argparse
import re
import shutil
import struct
import tarfile
import time
import zlib

ROOT = os.path.abspath(os.path.dirname(__file__))
OUTPUT = os.path.join(ROOT, "dist")
PACKAGE = "enigma2-plugin-extensions-online-picons"
PLUGIN_TARGET = "usr/lib/enigma2/python/Plugins/Extensions/OnlinePicons"


def plugin_version():
    version_file = os.path.join(ROOT, "OnlinePicons", "__init__.py")
    with open(version_file, "r", encoding="utf-8") as source:
        match = re.search(r'^PLUGIN_VERSION\s*=\s*["\']([^"\']+)["\']', source.read(), re.M)
    if not match:
        raise RuntimeError("PLUGIN_VERSION is missing from OnlinePicons/__init__.py")
    return match.group(1)


VERSION = plugin_version()


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
    pixels = [0] * (width * height * 4)

    def set_pixel(x, y, color):
        if 0 <= x < width and 0 <= y < height:
            offset = (y * width + x) * 4
            pixels[offset:offset + 4] = color

    blue = (10, 62, 154, 255)
    cyan = (0, 210, 245, 255)
    white = (255, 255, 255, 255)
    green = (65, 225, 40, 255)

    # Rounded blue badge.
    for y in range(height):
        for x in range(width):
            nearest_x = min(max(x, 14), 113)
            nearest_y = min(max(y, 14), 113)
            if (x - nearest_x) ** 2 + (y - nearest_y) ** 2 <= 14 ** 2:
                set_pixel(x, y, blue)

    # Satellite dish and broadcast waves.
    for y in range(18, 68):
        for x in range(15, 66):
            dx, dy = x - 23, y - 20
            if 25 ** 2 <= dx * dx + dy * dy <= 31 ** 2 and x + y < 94:
                set_pixel(x, y, white)
    for x in range(34, 70):
        set_pixel(x, 62, cyan)
        set_pixel(x, 63, cyan)
    for radius in (18, 28, 38):
        for y in range(8, 58):
            for x in range(56, 108):
                dx, dy = x - 57, y - 57
                distance = (dx * dx + dy * dy) ** 0.5
                if abs(distance - radius) < 1.3 and x >= 57 and y <= 57:
                    set_pixel(x, y, cyan)
    for y in range(21, 34):
        for x in range(98, 111):
            if (x - 104) ** 2 + (y - 27) ** 2 <= 6 ** 2:
                set_pixel(x, y, green)

    # Exact PICONS word in a compact 5x7 bitmap font.
    glyphs = {
        "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
        "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
        "C": ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
        "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
        "N": ("10001", "11001", "11001", "10101", "10011", "10011", "10001"),
        "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    }
    scale = 3
    start_x = 10
    start_y = 88
    for letter in "PICONS":
        for row, bits in enumerate(glyphs[letter]):
            for column, bit in enumerate(bits):
                if bit == "1":
                    for yy in range(scale):
                        for xx in range(scale):
                            set_pixel(
                                start_x + column * scale + xx,
                                start_y + row * scale + yy,
                                white,
                            )
        start_x += 19
    png(path, width, height, pixels)


def make_youtube_icon(path):
    width, height = 120, 68
    pixels = [0] * (width * height * 4)

    def set_pixel(x, y, color):
        if 0 <= x < width and 0 <= y < height:
            offset = (y * width + x) * 4
            pixels[offset:offset + 4] = color

    red = (255, 0, 0, 255)
    white = (255, 255, 255, 255)
    for y in range(height):
        for x in range(width):
            nearest_x = min(max(x, 15), width - 16)
            nearest_y = min(max(y, 12), height - 13)
            if (x - nearest_x) ** 2 + (y - nearest_y) ** 2 <= 12 ** 2:
                set_pixel(x, y, red)
    for y in range(18, 51):
        half_width = (y - 18) // 2 if y <= 34 else (50 - y) // 2
        for x in range(48, 49 + max(0, half_width)):
            set_pixel(x, y, white)
        for x in range(49, 82 - abs(y - 34)):
            if x <= 49 + (y - 18):
                set_pixel(x, y, white)
    png(path, width, height, pixels)


def make_telegram_icon(path):
    width = height = 64
    pixels = [0] * (width * height * 4)
    blue = (35, 158, 216, 255)
    white = (255, 255, 255, 255)

    def set_pixel(x, y, color):
        if 0 <= x < width and 0 <= y < height:
            offset = (y * width + x) * 4
            pixels[offset:offset + 4] = color

    for y in range(height):
        for x in range(width):
            if (x - 32) ** 2 + (y - 32) ** 2 <= 30 ** 2:
                set_pixel(x, y, blue)

    # White paper plane.
    for y in range(15, 47):
        for x in range(12, 53):
            upper = 23 + (x - 12) * 0.28
            lower = 42 - (x - 12) * 0.18
            if upper <= y <= lower and x + y <= 77:
                set_pixel(x, y, white)
    for step in range(27):
        for thickness in range(3):
            set_pixel(22 + step, 39 - step // 2 + thickness, blue)
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
    elif kind == "language":
        for y in range(10, 39):
            for x in range(10, 39):
                dx, dy = x - 24, y - 24
                distance = dx * dx + dy * dy
                if 12 * 12 <= distance <= 15 * 15:
                    set_pixel(x, y, white)
                if abs(dx) <= 1 or abs(dy) <= 1:
                    if distance <= 14 * 14:
                        set_pixel(x, y, white)
                if abs(dx * dx - 40) <= 18 and distance <= 14 * 14:
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


def make_check_icon(path):
    width = height = 32
    pixels = [0] * (width * height * 4)
    green = (35, 210, 85, 255)

    def set_pixel(x, y):
        if 0 <= x < width and 0 <= y < height:
            offset = (y * width + x) * 4
            pixels[offset:offset + 4] = green

    points = []
    for step in range(9):
        points.append((5 + step, 16 + step))
    for step in range(16):
        points.append((13 + step, 24 - step))
    for x, y in points:
        for offset_y in range(-2, 3):
            for offset_x in range(-2, 3):
                set_pixel(x + offset_x, y + offset_y)
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
    parser = argparse.ArgumentParser(description="Build Online Picons packages")
    parser.add_argument(
        "--format",
        choices=("deb", "ipk", "all"),
        default="deb",
        help="package format to build (default: deb)",
    )
    args = parser.parse_args()
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
    make_menu_icon(os.path.join(plugin_stage, "language.png"), "language")
    make_menu_icon(os.path.join(plugin_stage, "about.png"), "about")
    make_dot_icon(os.path.join(plugin_stage, "dot-checking.png"), (125, 125, 125, 255))
    make_dot_icon(os.path.join(plugin_stage, "dot-red.png"), (220, 45, 45, 255))
    make_dot_icon(os.path.join(plugin_stage, "dot-yellow.png"), (235, 190, 20, 255))
    make_dot_icon(os.path.join(plugin_stage, "dot-green.png"), (35, 190, 90, 255))
    make_check_icon(os.path.join(plugin_stage, "check.png"))
    # Social logos are maintained as source assets in OnlinePicons/.

    control_stage = os.path.join(staging, "control")
    os.makedirs(control_stage)
    control_entries = []
    for name in ("control", "postinst", "prerm"):
        mode = 0o755 if name in ("postinst", "prerm") else 0o644
        source = os.path.join(ROOT, "DEBIAN", name)
        target = os.path.join(control_stage, name)
        shutil.copy2(source, target)
        if name == "control":
            with open(target, "r", encoding="utf-8") as control_file:
                control = control_file.read()
            control = re.sub(
                r"^Version:\s*.*$", "Version: " + VERSION, control, flags=re.M
            )
            with open(target, "w", encoding="utf-8", newline="\n") as control_file:
                control_file.write(control)
        control_entries.append((name, target, mode))

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
    formats = ("deb", "ipk") if args.format == "all" else (args.format,)
    output_paths = []
    for package_format in formats:
        output_path = os.path.join(
            OUTPUT, "%s_%s_all.%s" % (PACKAGE, VERSION, package_format)
        )
        with open(output_path, "wb") as package:
            package.write(b"!<arch>\n")
            package.write(ar_member("debian-binary", b"2.0\n"))
            package.write(ar_member("control.tar.gz", control_tar))
            package.write(ar_member("data.tar.gz", data_tar))
        output_paths.append(output_path)
    shutil.rmtree(staging, ignore_errors=True)
    for output_path in output_paths:
        print(output_path)


if __name__ == "__main__":
    main()
