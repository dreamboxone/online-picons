# -*- coding: utf-8 -*-
from __future__ import print_function

import base64
import errno
import os
import struct
import tempfile

ASSET_DIRECTORY = os.path.join(tempfile.gettempdir(), "online-picons-assets")

ASSET_DATA = {
    "dot-checking.png": "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAABGUlEQVR42u2Xuw2DMBCGWSBbZYfskB2yQ2hYgJ7SJaJCSkXhAeigZQMnXyQkFDnEEFt3imLpJMuP+8/3+G1n2b9tbEVRHKqqOtZ1fW7b9oLQZ4y5ZMDGmFPf92aaJmetdU3TuMfYU+gzxhxrWBsNmJON43gDoCxLl+f5qrCGtexh71fguHcYhiBgnyHsRccu8K7rrpxkK/CroANdm08eA3xpRLAniBuuiwU+CzqDcoLk2RPzkJxA98dSi+l6XyhWS5QaTnH6pRfAeMtwEEkq8FnA8DImCZLS/csweJMRPodSUxsABlje2ofXUxsAhpcTxA0QD4F4EoqXoTgRqaBi8ctIxXUs/iBR8SRT8ShV8SxX8TFR8zX72XYHUweqL4HiHqEAAAAASUVORK5CYII=",
    "dot-green.png": "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAABJUlEQVR42mNgGAUkAt7zkbwut+pdsh7OyKp9urQWhEFskBhIjmYWh9/rCd/24ey2uz+e/5/9etf/vEez/wPFwBjEBomB5EBqQGqpZjHIZye/3DoJskDras5/hrMBeDFIDUgtSA9IL0WWg4L3+JcbRFmMzSEgvSAzyLJ8wstNE0A+IdVidAwyA2QWyT6nhuXIjiA6JEDxBgo6alkOwyAziUoToMRDTpwTkyZAZhPMatQMemxRgTeLgvIwLXyPHAogO3CWcKCChFaWwzDIDqwlJiiB0DL4kaMBa2IEleegIpXWDgDZAbILa94Hleu0dgDIDqxlwoA7YMCjYMAT4YBnwwEviAZFUTzgldGgqI4HvEEyKJpkg6JROiia5YOiYzJoumbDFgAANvZqeJDNu+sAAAAASUVORK5CYII=",
    "dot-yellow.png": "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAABHklEQVR42u1XSwrCMBDtBXoRz9E79A5deIPeoXvv0QsISsGdCzcVXAiuXOjG5ThvSqFIrGlNmEEMDIR85k3m85Ikyb9NbLRJU9pnGbVFQaeyFEEfYzwXD/iQ53Sta3ociS4ronZJPNYJ+hjDHNbw2nDAONm9aQRgtyBaJ+OCNViLPbz3O3C497b1A3YZgr2sYx74uarkJFOBXwU6WNf0k4cAHxrh6wmJOVwXCrwX6PTJCUmeOTH3yQnW/bnUQrreFYqxEpUajnH6oRcY4z3DgUhigfcCDBdjSvLFdP8wDK5kFD4HpcY2ABiM5a598HpsA4Dh4gR9A9RDoJ6E2mWoTkQmqFj9MjJxHas/SEw8yUw8Sk08y018TMx8zX62PQG/r8rznbuvCQAAAABJRU5ErkJggg==",
    "dot-red.png": "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAABJElEQVR42mNgGAUkgjcWjrwfUnNdPrd0ZX2ZMrMWhEFskBhIjmYWfyytDv95+Oi2P4+f/P++ZsP/z+29/4FiYAxig8RAciA1ILVUsxjks1+Xrp4EWfDOP+L/a11zvBikBqQWpAeklyLLQcH76+JloizG5hCQXpAZZFn+bfHyCSCfkGoxOgaZATKLZJ9Tw3JkRxAdEuA4BwYdtSyHYZCZRKUJUOIhJ86JShNAswlmNWoGPbaowJtFQXmYFr5HDgWQHThLOFBBQivLYRhkB9YSE5RAaBn8yNGANTGCynNQkUprB4DsANmFNe+DynVaOwBkB9YyYcAdMOBRMOCJcMCz4YAXRIOiKB7wymhQVMcD3iAZFE2yQdEoHRTN8kHRMRk0XbNhCwAU5dUsrduXWwAAAABJRU5ErkJggg==",
    "check.png": "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAAvElEQVR42u2Wyw2AIBAFKcFSrMJwpQGLoBR6oAJKsQJ74I74uxhAyLJLomzyjuQNYbKBsT59qGaduI++wqnLhY97hFOVjz42AKApygefJVBOBmAi5QRPsE4qUS6xy2WiXLUw/o5pZby7ZBxaGW8PONRtlTZe5JY/D850xp+3dsUQ1YyPA8QhqhoffoI4BIrxe0kORBXjIRBg4+EQBDu+HEJhbLdcCIO5Yt8gkHd8GgJoPBxCMPabr3Wfr84GFMfzhKWUlKIAAAAASUVORK5CYII=",
}


def asset_path(name):
    return os.path.join(ASSET_DIRECTORY, name)


def ensure_assets():
    try:
        os.makedirs(ASSET_DIRECTORY)
    except OSError as error:
        if error.errno != errno.EEXIST:
            raise

    for name, encoded in ASSET_DATA.items():
        data = base64.b64decode(encoded)
        path = asset_path(name)
        try:
            if os.path.isfile(path) and os.path.getsize(path) == len(data):
                continue
        except OSError:
            pass
        temporary = "%s.tmp-%d" % (path, os.getpid())
        output = open(temporary, "wb")
        try:
            output.write(data)
        finally:
            output.close()
        try:
            os.rename(temporary, path)
        except OSError:
            try:
                os.unlink(path)
            except OSError:
                pass
            os.rename(temporary, path)
    return ASSET_DIRECTORY


def validate_assets():
    expected = set([
        "dot-checking.png",
        "dot-green.png",
        "dot-yellow.png",
        "dot-red.png",
        "check.png",
    ])
    if set(ASSET_DATA) != expected:
        raise RuntimeError("The runtime asset list is incomplete")
    for name, encoded in ASSET_DATA.items():
        data = base64.b64decode(encoded)
        if not data.startswith(b"\x89PNG\r\n\x1a\n"):
            raise RuntimeError("%s is not a PNG file" % name)
        width, height = struct.unpack(">II", data[16:24])
        if (width, height) != (32, 32):
            raise RuntimeError("%s must be 32x32 pixels" % name)
    return True


if __name__ == "__main__":
    validate_assets()
    print("Validated %d runtime PNG assets" % len(ASSET_DATA))
