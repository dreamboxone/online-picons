#!/usr/bin/env python3
"""Build the DreamOS Online Picons .deb package.

The build is self-contained and does not require dpkg-deb. Files already
present in OnlinePicons/ (including plugin.png and menu icons) are copied
unchanged into the package.
"""

import argparse
import gzip
import io
import os
import re
import shutil
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PLUGIN_SOURCE = ROOT / "OnlinePicons"
DEBIAN_SOURCE = ROOT / "DEBIAN"
OUTPUT_DIR = ROOT / "dist"
BUILD_DIR = ROOT / ".build"

PACKAGE = "enigma2-plugin-extensions-online-picons"
PLUGIN_TARGET = "usr/lib/enigma2/python/Plugins/Extensions/OnlinePicons"
SOURCE_DATE_EPOCH = int(os.environ.get("SOURCE_DATE_EPOCH", "1767225600"))

IGNORED_NAMES = {
    "__pycache__",
    ".DS_Store",
    "Thumbs.db",
}
IGNORED_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".swp",
    ".tmp",
}


def plugin_version():
    """Read the authoritative release version from OnlinePicons/__init__.py."""
    init_file = PLUGIN_SOURCE / "__init__.py"
    content = init_file.read_text(encoding="utf-8")
    match = re.search(
        r'^\s*PLUGIN_VERSION\s*=\s*["\']([^"\']+)["\']',
        content,
        re.MULTILINE,
    )
    if not match:
        raise RuntimeError("PLUGIN_VERSION was not found in OnlinePicons/__init__.py")
    return match.group(1).strip()


def package_control(version):
    """Synchronize the package metadata with the plugin release version."""
    control_file = DEBIAN_SOURCE / "control"
    content = control_file.read_text(encoding="utf-8").replace("\r\n", "\n")
    updated, count = re.subn(
        r"^Version:\s*.*$",
        "Version: %s" % version,
        content,
        count=1,
        flags=re.MULTILINE,
    )
    if count != 1:
        raise RuntimeError("Version field was not found in DEBIAN/control")
    return updated.encode("utf-8")


def should_include(path):
    relative_parts = path.relative_to(PLUGIN_SOURCE).parts
    if any(part in IGNORED_NAMES for part in relative_parts):
        return False
    if path.suffix.lower() in IGNORED_SUFFIXES:
        return False
    return True


def add_directory(archive, name, mode=0o755):
    info = tarfile.TarInfo(name.rstrip("/") + "/")
    info.type = tarfile.DIRTYPE
    info.mode = mode
    info.mtime = SOURCE_DATE_EPOCH
    info.uid = 0
    info.gid = 0
    info.uname = "root"
    info.gname = "root"
    archive.addfile(info)


def add_bytes(archive, name, data, mode=0o644):
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mode = mode
    info.mtime = SOURCE_DATE_EPOCH
    info.uid = 0
    info.gid = 0
    info.uname = "root"
    info.gname = "root"
    archive.addfile(info, io.BytesIO(data))


def compressed_tar(writer):
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.GNU_FORMAT) as archive:
        writer(archive)

    output = io.BytesIO()
    with gzip.GzipFile(fileobj=output, mode="wb", mtime=0) as compressed:
        compressed.write(raw.getvalue())
    return output.getvalue()


def build_control_tar(version):
    def write(archive):
        add_bytes(archive, "control", package_control(version), 0o644)
        for filename in ("preinst", "postinst", "prerm", "postrm"):
            source = DEBIAN_SOURCE / filename
            if source.is_file():
                data = source.read_bytes().replace(b"\r\n", b"\n")
                add_bytes(archive, filename, data, 0o755)

    return compressed_tar(write)


def build_data_tar():
    from OnlinePicons.assets import validate_assets

    validate_assets()
    required = (
        PLUGIN_SOURCE / "__init__.py",
        PLUGIN_SOURCE / "plugin.py",
        PLUGIN_SOURCE / "plugin.png",
        PLUGIN_SOURCE / "assets.py",
    )
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError("Required file(s) missing: %s" % ", ".join(missing))

    files = sorted(
        path for path in PLUGIN_SOURCE.rglob("*")
        if path.is_file() and should_include(path)
    )

    def write(archive):
        directories = {
            "usr",
            "usr/lib",
            "usr/lib/enigma2",
            "usr/lib/enigma2/python",
            "usr/lib/enigma2/python/Plugins",
            "usr/lib/enigma2/python/Plugins/Extensions",
            PLUGIN_TARGET,
        }
        for source in files:
            relative = source.relative_to(PLUGIN_SOURCE).as_posix()
            parent = Path(PLUGIN_TARGET, relative).parent
            while parent.as_posix().startswith(PLUGIN_TARGET):
                directories.add(parent.as_posix())
                if parent.as_posix() == PLUGIN_TARGET:
                    break
                parent = parent.parent

        for directory in sorted(directories, key=lambda item: (item.count("/"), item)):
            add_directory(archive, directory)

        for source in files:
            relative = source.relative_to(PLUGIN_SOURCE).as_posix()
            destination = "%s/%s" % (PLUGIN_TARGET, relative)
            data = source.read_bytes()
            if source.suffix.lower() in {".py", ".sh"}:
                data = data.replace(b"\r\n", b"\n")
            mode = 0o755 if source.suffix.lower() == ".sh" else 0o644
            add_bytes(archive, destination, data, mode)

    return compressed_tar(write)


def ar_member(name, data, mode=0o100644):
    header = (
        (name + "/").ljust(16).encode("ascii")
        + str(SOURCE_DATE_EPOCH).ljust(12).encode("ascii")
        + b"0     "
        + b"0     "
        + oct(mode)[2:].ljust(8).encode("ascii")
        + str(len(data)).ljust(10).encode("ascii")
        + b"`\n"
    )
    return header + data + (b"\n" if len(data) % 2 else b"")


def package_payload(control_tar, data_tar):
    output = io.BytesIO()
    output.write(b"!<arch>\n")
    output.write(ar_member("debian-binary", b"2.0\n"))
    output.write(ar_member("control.tar.gz", control_tar))
    output.write(ar_member("data.tar.gz", data_tar))
    return output.getvalue()


def parse_args():
    parser = argparse.ArgumentParser(description="Build Online Picons packages")
    parser.add_argument(
        "--format",
        choices=("deb", "ipk", "all"),
        default="deb",
        help="Package format to build (default: deb)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if not PLUGIN_SOURCE.is_dir():
        raise RuntimeError("OnlinePicons directory was not found beside build_deb.py")
    if not DEBIAN_SOURCE.is_dir():
        raise RuntimeError("DEBIAN directory was not found beside build_deb.py")

    version = plugin_version()
    control_tar = build_control_tar(version)
    data_tar = build_data_tar()
    payload = package_payload(control_tar, data_tar)

    shutil.rmtree(BUILD_DIR, ignore_errors=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for old_package in OUTPUT_DIR.glob("%s_*_all.*" % PACKAGE):
        if old_package.suffix in (".deb", ".ipk"):
            old_package.unlink()

    formats = ("deb", "ipk") if args.format == "all" else (args.format,)
    for extension in formats:
        output_path = OUTPUT_DIR / (
            "%s_%s_all.%s" % (PACKAGE, version, extension)
        )
        output_path.write_bytes(payload)
        print("Built: %s" % output_path)

    print("Version: %s" % version)
    print("Source icon preserved: OnlinePicons/plugin.png")


if __name__ == "__main__":
    main()
