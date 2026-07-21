# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading

try:
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError
except ImportError:
    from urllib2 import Request, urlopen, HTTPError

from Components.ActionMap import ActionMap
from Components.Console import Console
from Components.Label import Label
from Components.MenuList import MenuList
from Components.MultiContent import (
    MultiContentEntryPixmapAlphaTest,
    MultiContentEntryText,
)
from Components.Pixmap import Pixmap
from Components.config import ConfigSubsection, ConfigText, config, configfile
from Plugins.Plugin import PluginDescriptor
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Tools.LoadPixmap import LoadPixmap
from twisted.internet import reactor
from enigma import (
    RT_HALIGN_LEFT,
    RT_VALIGN_CENTER,
    eListboxPythonMultiContent,
    eTimer,
    gFont,
)

from . import PLUGIN_VERSION


REPOSITORY = "dreamboxone/online-picons"
RAW_BASE = "https://raw.githubusercontent.com/%s/main" % REPOSITORY
GOOGLE_HOST = "google.com"
GITHUB_HOST = "github.com"
PLUGIN_PATH = os.path.dirname(os.path.abspath(__file__))
PY2 = sys.version_info[0] == 2

try:
    text_type = unicode
except NameError:
    text_type = str


def _menu_text(value):
    """Return the string type expected by DreamOS eListbox content."""
    if PY2 and isinstance(value, text_type):
        return value.encode("utf-8")
    return value


def _set_menu_style(menu, font_size, item_height):
    """Style MenuList content without applying attributes to eListbox."""
    font = gFont("Regular", font_size)
    try:
        menu.l.setFont(font)
    except TypeError:
        try:
            menu.l.setFont(0, font)
        except Exception:
            pass
    except Exception:
        pass
    try:
        menu.l.setItemHeight(item_height)
    except Exception:
        pass


if not hasattr(config.plugins, "onlinepicons"):
    config.plugins.onlinepicons = ConfigSubsection()
config.plugins.onlinepicons.destination = ConfigText(
    default="/media/hdd/picon", fixed_size=False
)


# title, archive stem. Duplicates in the supplied list are intentionally removed.
SATELLITES = [
    ("Picons-220x132-22°W (SES 4)", "22w"),
    ("Picons-220x132-15°W (Telstar 12)", "15w"),
    ("Picons-220x132-14°W (Express AM8)", "14w"),
    ("Picons-220x132-8°W (Eutelsat 8W)", "8w"),
    ("Picons-220x132-7°W (Nilesat 201/301/7W)", "7w"),
    ("Picons-220x132-5°W (Eutelsat 5W)", "5w"),
    ("Picons-220x132-4°W (Dror 1)", "4w"),
    ("Picons-220x132-3°W (ABS 3A)", "3w"),
    ("Picons-220x132-0.8°W (Thor 5/6/7/Intelsat 10-02)", "0.8w"),
    ("Picons-220x132-1.9°E (BulgariaSat 1)", "1.9e"),
    ("Picons-220x132-3°E (Eutelsat 3B)", "3e"),
    ("Picons-220x132-4.9°E (Astra 4A/SES 5)", "4.9e"),
    ("Picons-220x132-7°E (Eutelsat 7B/7C)", "7e"),
    ("Picons-220x132-9°E (Eutelsat 9B)", "9e"),
    ("Picons-220x132-10.0°E (Eutelsat 10B)", "10e"),
    ("Picons-220x132-13.0°E (Hotbird 13F/13G)", "13e"),
    ("Picons-220x132-16.0°E (Eutelsat 16A)", "16e"),
    ("Picons-220x132-17.0°E (Amos 17)", "17e"),
    ("Picons-220x132-19.2°E (Astra 1N/1P)", "19.2e"),
    ("Picons-220x132-26.0°E (Badr 7/8-Es'hail 2)", "26e"),
    ("Picons-220x132-42.0°E (Turksat 3A/4A/5B/6A)", "42e"),
    ("Picons-220x132-46.0°E (Azeraspace 1)", "46e"),
    ("Picons-220x132-52.0°E (TurkmenÄlem/MonacoSat)", "52e"),
    ("Picons-220x132-52.5°E (Al Yah 1)", "52.5e"),
    ("Picons-220x132-53.0°E (Express AM6)", "53e"),
    ("Picons-220x132-62.0°E (Intelsat 39)", "62e"),
    ("Picons-220x132-68.5°E (Intelsat 20/36)", "68.5e"),
    ("Picons-220x132-70.5°E (Eutelsat 70B)", "70.5e"),
    ("Picons-220x132-78.5°E (Thaicom 6/8)", "78.5e"),
    ("Picons-220x132-80.0°E (Express 80)", "80e"),
    ("Picons-220x132-95.0°E (SES 12)", "95e"),
    ("Picons-220x132-100.5°E (Asiasat 5)", "100.5e"),
]


def _timer_start(timer, delay, callback):
    try:
        timer.callback.append(callback)
    except Exception:
        timer.timeout.connect(callback)
    timer.start(delay, True)


def _request(url, method=None, timeout=8):
    headers = {"User-Agent": "OnlinePicons/%s" % PLUGIN_VERSION}
    try:
        request = Request(url, headers=headers, method=method or "GET")
    except TypeError:  # Python 2 Request has no method argument.
        request = Request(url, headers=headers)
        if method:
            request.get_method = lambda: method
    return urlopen(request, timeout=timeout)


def _url_exists(url):
    try:
        response = _request(url, method="HEAD", timeout=8)
        code = getattr(response, "status", response.getcode())
        response.close()
        return 200 <= code < 400
    except HTTPError as error:
        return error.code not in (404, 410) and error.code < 500
    except Exception:
        return False


def _find_archive(stem):
    url = "%s/%s.rar" % (RAW_BASE, stem)
    return url if _url_exists(url) else None


def _archive_stem(title):
    """Derive the RAR name from the orbital position in the visible title."""
    match = re.search(r"Picons-220x132-([0-9]+(?:\.[0-9]+)?)", title)
    if not match:
        return None
    position = match.group(1)
    if "." in position:
        position = position.rstrip("0").rstrip(".")
    orbital_token = title[match.end():].split(" ", 1)[0].upper()
    direction = "e" if "E" in orbital_token else "w"
    return position + direction


def _extractor_available():
    for command in ("unrar", "7z", "7za", "bsdtar"):
        for directory in os.environ.get("PATH", "").split(os.pathsep):
            executable = os.path.join(directory, command)
            if os.path.isfile(executable) and os.access(executable, os.X_OK):
                return True
    return False


class OnlinePiconsMain(Screen):
    skin = """
    <screen name="OnlinePiconsMain" position="center,center" size="900,560"
            title="Online Picons">
        <widget name="title" position="45,30" size="810,55"
                font="Regular;38" halign="center" />
        <widget name="menu" position="65,115" size="715,310"
                scrollbarMode="showNever" />
        <widget name="hint" position="45,480" size="810,38"
                font="Regular;22" halign="center" foregroundColor="#aaaaaa" />
    </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self["title"] = Label("Online Picons")
        self["menu"] = MenuList(
            [
                self._menu_entry("Settings", "settings.png"),
                self._menu_entry("Download Picons", "download.png"),
                self._menu_entry("About", "about.png"),
            ],
            enableWrapAround=True,
            content=eListboxPythonMultiContent,
        )
        self["menu"].l.setFont(0, gFont("Regular", 38))
        self["menu"].l.setItemHeight(64)
        self["hint"] = Label("OK: Select     EXIT: Close")
        self["actions"] = ActionMap(
            ["OkCancelActions"],
            {"ok": self.open_selected, "cancel": self.close},
            -1,
        )

    def _menu_entry(self, text, icon):
        return [
            _menu_text(text),
            MultiContentEntryPixmapAlphaTest(
                pos=(8, 8),
                size=(48, 48),
                png=LoadPixmap(
                    cached=True,
                    path=os.path.join(PLUGIN_PATH, icon),
                ),
            ),
            MultiContentEntryText(
                pos=(76, 0),
                size=(627, 64),
                font=0,
                flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                text=_menu_text(text),
            ),
        ]

    def open_selected(self):
        index = self["menu"].getSelectedIndex()
        if index == 0:
            self.session.open(DestinationScreen)
        elif index == 1:
            self.session.open(DownloadScreen)
        else:
            self.session.open(AboutScreen)


class DestinationScreen(Screen):
    skin = """
    <screen name="DestinationScreen" position="center,center" size="1000,590"
            title="Online Picons - Settings">
        <widget name="heading" position="45,25" size="910,45"
                font="Regular;30" halign="center" />
        <widget name="paths" position="65,100" size="870,260"
                scrollbarMode="showNever" />
        <widget name="custom" position="65,385" size="870,55"
                font="Regular;25" halign="left" valign="center"
                backgroundColor="#202020" transparent="0" />
        <widget name="keysLeft" position="130,485" size="390,42"
                font="Regular;22" halign="right" />
        <widget name="greenKey" position="520,485" size="78,42"
                font="Regular;22" halign="center" foregroundColor="#00ff00" />
        <widget name="keysRight" position="598,485" size="270,42"
                font="Regular;22" halign="left" />
    </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.paths = [
            "/media/hdd/picon",
            "/media/usb/picon",
            config.plugins.onlinepicons.destination.value
            if config.plugins.onlinepicons.destination.value not in
            ("/media/hdd/picon", "/media/usb/picon")
            else "/media/picon",
        ]
        saved = config.plugins.onlinepicons.destination.value
        self.selected = self.paths.index(saved) if saved in self.paths else 2
        self["heading"] = Label("Choose the destination for downloaded picons")
        self["paths"] = MenuList([])
        _set_menu_style(self["paths"], 30, 48)
        self["custom"] = Label("")
        self["keysLeft"] = Label("OK: Select     BLUE: Edit custom path     ")
        self["greenKey"] = Label("GREEN")
        self["keysRight"] = Label(": Save")
        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions"],
            {
                "ok": self.select_path,
                "cancel": self.close,
                "blue": self.edit_custom,
                "green": self.save,
            },
            -1,
        )
        self.refresh()

    def refresh(self):
        rows = []
        for index, path in enumerate(self.paths):
            mark = "[X]" if index == self.selected else "[ ]"
            label = path if index < 2 else "Custom path"
            rows.append(_menu_text("%s  %s" % (mark, label)))
        current = self["paths"].getSelectedIndex()
        self["paths"].setList(rows)
        self["paths"].moveToIndex(current)
        self["custom"].setText("  %s" % self.paths[2])

    def select_path(self):
        self.selected = self["paths"].getSelectedIndex()
        if self.selected == 2:
            self.edit_custom()
        else:
            self.refresh()

    def edit_custom(self):
        self.session.openWithCallback(
            self.custom_entered,
            VirtualKeyBoard,
            title="Enter picon destination path",
            text=self.paths[2],
        )

    def custom_entered(self, value):
        if value:
            value = value.strip()
            if not value.startswith("/"):
                self.session.open(
                    MessageBox,
                    "The path must start with /",
                    MessageBox.TYPE_ERROR,
                    timeout=5,
                )
                return
            self.paths[2] = os.path.normpath(value)
            self.selected = 2
            self.refresh()

    def save(self):
        destination = self.paths[self.selected]
        config.plugins.onlinepicons.destination.value = destination
        config.plugins.onlinepicons.destination.save()
        configfile.save()
        self.session.openWithCallback(
            lambda unused=None: self.close(),
            MessageBox,
            "Picon destination saved:\n%s" % destination,
            MessageBox.TYPE_INFO,
            timeout=3,
        )


class DownloadScreen(Screen):
    skin = """
    <screen name="DownloadScreen" position="center,center" size="1180,690"
            title="Online Picons - Download Picons">
        <widget name="online" position="35,15" size="105,45"
                font="Regular;27" valign="center" />
        <widget name="onlineDot" position="145,21" size="32,32"
                pixmap="/usr/lib/enigma2/python/Plugins/Extensions/OnlinePicons/dot-checking.png"
                alphatest="blend" />
        <widget name="connection" position="185,15" size="280,45"
                font="Regular;23" valign="center" />
        <widget name="destination" position="470,25" size="675,38"
                font="Regular;21" halign="right" foregroundColor="#aaaaaa" />
        <widget name="satellites" position="35,85" size="1110,490"
                scrollbarMode="showOnDemand" />
        <widget name="status" position="35,585" size="1110,38"
                font="Regular;21" halign="center" />
        <widget name="keysLeft" position="190,635" size="430,35"
                font="Regular;22" halign="right" />
        <widget name="greenKey" position="620,635" size="78,35"
                font="Regular;22" halign="center" foregroundColor="#00ff00" />
        <widget name="keysRight" position="698,635" size="300,35"
                font="Regular;22" halign="left" />
    </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.selected = {}
        self.completed = set()
        self.available_urls = {}
        self.busy = False
        self.connectivity = "checking"
        self.connectivity_check_done = False
        self.ping_pending = set()
        self.ping_results = {}
        self.ping_console = Console()
        self.ping_timeout_timer = eTimer()
        self.probe_console = Console()
        self.probe_timeout_timer = eTimer()
        self.active_probe = None
        self.extractor_console = Console()
        self.pending_download_stems = None
        self.screen_closed = False
        self["online"] = Label("Internet")
        self["onlineDot"] = Pixmap()
        self["connection"] = Label("Checking...")
        self["destination"] = Label(
            "Destination: %s" % config.plugins.onlinepicons.destination.value
        )
        self["satellites"] = MenuList(
            [],
            enableWrapAround=True,
            content=eListboxPythonMultiContent,
        )
        self["satellites"].l.setFont(0, gFont("Regular", 32))
        self["satellites"].l.setItemHeight(46)
        self["status"] = Label("Checking internet connection...")
        self["keysLeft"] = Label("OK: Select/Unselect     ")
        self["greenKey"] = Label("GREEN")
        self["keysRight"] = Label(": Download     EXIT: Back")
        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions"],
            {
                "ok": self.toggle_current,
                "cancel": self.close,
                "green": self.download_selected,
            },
            -1,
        )
        self.onClose.append(self._cleanup)
        self.refresh_list()
        self._start_connectivity_check()

    def _cleanup(self):
        self.screen_closed = True
        try:
            self.ping_timeout_timer.stop()
        except Exception:
            pass
        try:
            self.probe_timeout_timer.stop()
        except Exception:
            pass
        try:
            self.ping_console.killAll()
        except Exception:
            pass
        try:
            self.probe_console.killAll()
        except Exception:
            pass
        try:
            self.extractor_console.killAll()
        except Exception:
            pass

    def _run_background(self, kind, function, *args):
        def runner():
            try:
                result = function(*args)
                success = True
            except Exception as error:
                success = False
                result = str(error)
            reactor.callFromThread(
                self._background_finished,
                kind,
                success,
                result,
            )
        thread = threading.Thread(target=runner)
        thread.daemon = True
        thread.start()

    def _background_finished(self, kind, success, result):
        if self.screen_closed:
            return
        if kind == "download":
            self.busy = False
            self._download_finished(success, result)

    def _start_connectivity_check(self):
        self.ping_pending = set(("google", "github"))
        commands = (
            ("google", "ping -c 1 -W 3 %s" % GOOGLE_HOST),
            ("github", "ping -c 1 -W 3 %s" % GITHUB_HOST),
        )
        _timer_start(
            self.ping_timeout_timer,
            6000,
            self._ping_check_timed_out,
        )
        for key, command in commands:
            try:
                self.ping_console.ePopen(
                    command,
                    self._ping_finished,
                    [key],
                )
            except Exception:
                self.ping_results[key] = False
                self.ping_pending.discard(key)
        if not self.ping_pending:
            self._finish_connectivity_check()

    def _ping_finished(self, output, return_code, extra_args):
        if self.connectivity_check_done:
            return
        key = extra_args[0]
        self.ping_results[key] = return_code == 0
        self.ping_pending.discard(key)
        if not self.ping_pending:
            self._finish_connectivity_check()

    def _ping_check_timed_out(self):
        if self.connectivity_check_done:
            return
        for key in self.ping_pending:
            self.ping_results[key] = False
        self.ping_pending.clear()
        self._finish_connectivity_check()
        try:
            self.ping_console.killAll()
        except Exception:
            pass

    def _finish_connectivity_check(self):
        if self.connectivity_check_done:
            return
        self.connectivity_check_done = True
        try:
            self.ping_timeout_timer.stop()
        except Exception:
            pass
        google = self.ping_results.get("google", False)
        github = self.ping_results.get("github", False)
        if not google:
            state = "offline"
        else:
            state = "online" if github else "google_only"
        self._show_connectivity(state)

    def _show_connectivity(self, state):
        self.connectivity = state
        if state == "online":
            self["connection"].setText("Online")
            self._set_connection_dot("green")
            self["status"].setText("Connected to Google and GitHub")
        elif state == "google_only":
            self["connection"].setText("Limited Internet")
            self._set_connection_dot("yellow")
            self["status"].setText("Internet works, but GitHub is unavailable")
        else:
            self["connection"].setText("Offline")
            self._set_connection_dot("red")
            self["status"].setText("No internet connection")

    def _set_connection_dot(self, color):
        path = os.path.join(PLUGIN_PATH, "dot-%s.png" % color)
        if os.path.exists(path) and self["onlineDot"].instance is not None:
            self["onlineDot"].instance.setPixmapFromFile(path)

    def refresh_list(self):
        index = self["satellites"].getSelectedIndex()
        rows = []
        for title, configured_stem in SATELLITES:
            stem = _archive_stem(title) or configured_stem
            display_title = title
            if PY2 and isinstance(display_title, str):
                display_title = display_title.decode("utf-8")
            selected = stem in self.selected
            row = [_menu_text(stem)]
            if selected:
                row.append(MultiContentEntryText(
                    pos=(6, 0),
                    size=(34, 46),
                    font=0,
                    flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                    text=_menu_text("X"),
                    color=0x00FF00,
                    color_sel=0x00FF00,
                ))
            elif stem in self.completed:
                row.append(MultiContentEntryPixmapAlphaTest(
                    pos=(5, 7),
                    size=(32, 32),
                    png=LoadPixmap(
                        cached=True,
                        path=os.path.join(PLUGIN_PATH, "check.png"),
                    ),
                ))
            else:
                row.append(MultiContentEntryText(
                    pos=(6, 0),
                    size=(34, 46),
                    font=0,
                    flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                    text=_menu_text(""),
                ))
            row.append(
                MultiContentEntryText(
                    pos=(42, 0),
                    size=(1055, 46),
                    font=0,
                    flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                    text=_menu_text(display_title),
                )
            )
            rows.append(row)
        self["satellites"].setList(rows)
        self["satellites"].moveToIndex(index)

    def toggle_current(self):
        if self.busy:
            return
        if self.connectivity != "online":
            self.session.open(
                MessageBox,
                "به دلیل عدم اتصال به اینترنت امکان دانلود Picon وجود ندارد.",
                MessageBox.TYPE_ERROR,
                timeout=5,
            )
            return
        index = self["satellites"].getSelectedIndex()
        title, configured_stem = SATELLITES[index]
        stem = _archive_stem(title) or configured_stem
        if stem in self.selected:
            del self.selected[stem]
            self.refresh_list()
            return
        if stem in self.available_urls:
            self.selected[stem] = title
            self.refresh_list()
            self["status"].setText("Selected: %s" % title)
            return
        self.busy = True
        self["status"].setText("Checking GitHub for %s..." % title)
        url = "%s/%s.rar" % (RAW_BASE, stem)
        self.active_probe = (index, title, stem, url)
        _timer_start(
            self.probe_timeout_timer,
            1900,
            self._probe_timed_out,
        )
        try:
            self.probe_console.ePopen(
                "wget -q --spider -T 2 %s" % url,
                self._probe_command_finished,
                [],
            )
        except Exception:
            self._finish_probe(False)

    def _probe_command_finished(self, output, return_code, extra_args):
        if self.active_probe is not None:
            self._finish_probe(return_code == 0)

    def _probe_timed_out(self):
        if self.active_probe is None:
            return
        self._finish_probe(False)
        try:
            self.probe_console.killAll()
        except Exception:
            pass

    def _finish_probe(self, available):
        if self.active_probe is None:
            return
        try:
            self.probe_timeout_timer.stop()
        except Exception:
            pass
        index, title, stem, url = self.active_probe
        self.active_probe = None
        self.busy = False
        if not available:
            self.session.open(
                MessageBox,
                _menu_text(
                    u"این فایل فعلا وجود ندارد. لطفا بعدا مراجعه نمایید.\n\n"
                    u"This file is not uploaded yet. Please visit us later..."
                ),
                MessageBox.TYPE_INFO,
                timeout=5,
            )
            self["status"].setText("Archive not available: %s" % title)
            return
        self.available_urls[stem] = url
        self.selected[stem] = title
        self.refresh_list()
        self["status"].setText("Selected: %s" % title)

    def download_selected(self):
        if self.busy:
            return
        if self.connectivity != "online":
            self.session.open(
                MessageBox,
                "به دلیل عدم اتصال به اینترنت امکان دانلود Picon وجود ندارد.",
                MessageBox.TYPE_ERROR,
                timeout=5,
            )
            return
        if not self.selected:
            self.session.open(
                MessageBox,
                "ابتدا حداقل یک ماهواره را انتخاب کنید.",
                MessageBox.TYPE_INFO,
                timeout=5,
            )
            return
        stems = list(self.selected.keys())
        if not _extractor_available():
            self.busy = True
            self.pending_download_stems = stems
            self["status"].setText("Preparing download support...")
            command = (
                "sh -c '"
                "LOG=/tmp/online-picons-setup.log; "
                "if command -v opkg >/dev/null 2>&1; then "
                "opkg update >$LOG 2>&1 || true; "
                "for package in unrar unrar-free p7zip; do "
                "opkg install $package >>$LOG 2>&1 && exit 0; "
                "done; "
                "elif command -v apt-get >/dev/null 2>&1; then "
                "apt-get update >$LOG 2>&1 || true; "
                "for package in unrar unrar-free p7zip-full p7zip; do "
                "apt-get install -y $package >>$LOG 2>&1 && exit 0; "
                "done; "
                "fi; exit 1"
                "'"
            )
            try:
                self.extractor_console.ePopen(
                    command,
                    self._extractor_install_finished,
                    [],
                )
            except Exception:
                self._extractor_install_finished("", 1, [])
            return
        self._start_download(stems)

    def _extractor_install_finished(self, output, return_code, extra_args):
        stems = self.pending_download_stems
        self.pending_download_stems = None
        if return_code != 0 or not _extractor_available():
            self.busy = False
            self["status"].setText("Download preparation failed")
            self.session.open(
                MessageBox,
                "امکان آماده‌سازی دانلود وجود ندارد. اتصال اینترنت را بررسی و دوباره تلاش کنید.",
                MessageBox.TYPE_ERROR,
                timeout=7,
            )
            return
        self._start_download(stems)

    def _start_download(self, stems):
        self.busy = True
        self["status"].setText("Downloading selected picons...")
        self._run_background("download", self._download_all, stems)

    def _download_all(self, stems):
        destination = config.plugins.onlinepicons.destination.value
        if not destination.startswith("/"):
            raise RuntimeError("Invalid destination path")
        if not os.path.isdir(destination):
            os.makedirs(destination)
        installed = 0
        completed_stems = []
        temp_root = tempfile.mkdtemp(prefix="online-picons-", dir="/tmp")
        try:
            for stem in stems:
                url = self.available_urls.get(stem) or _find_archive(stem)
                if not url:
                    continue
                extension = os.path.splitext(url)[1].lower()
                archive = os.path.join(temp_root, stem + extension)
                response = _request(url, timeout=45)
                with open(archive, "wb") as output:
                    while True:
                        block = response.read(1024 * 128)
                        if not block:
                            break
                        output.write(block)
                response.close()
                unpacked = os.path.join(temp_root, "unpacked-" + stem)
                os.makedirs(unpacked)
                self._extract(archive, unpacked, extension)
                for root, dirs, files in os.walk(unpacked):
                    for filename in files:
                        if filename.lower().endswith(".png"):
                            shutil.copy2(
                                os.path.join(root, filename),
                                os.path.join(destination, filename),
                            )
                            installed += 1
                completed_stems.append(stem)
            return installed, destination, completed_stems
        finally:
            shutil.rmtree(temp_root, ignore_errors=True)

    def _extract(self, archive, destination, extension):
        commands = [
            ["unrar", "x", "-o+", archive, destination + os.sep],
            ["7z", "x", "-y", "-o" + destination, archive],
            ["7za", "x", "-y", "-o" + destination, archive],
            ["bsdtar", "-xf", archive, "-C", destination],
            ["tar", "-xf", archive, "-C", destination],
        ]
        for command in commands:
            try:
                process = subprocess.Popen(
                    command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
                process.communicate()
                if process.returncode == 0:
                    return
            except OSError:
                pass
        raise RuntimeError(
            "RAR extraction failed"
        )

    def _download_finished(self, success, result):
        if success:
            count, destination, completed_stems = result
            self["status"].setText("Download completed: %d PNG files" % count)
            self.session.open(
                MessageBox,
                "دانلود با موفقیت انجام شد.\n%d فایل در مسیر زیر کپی شد:\n%s"
                % (count, destination),
                MessageBox.TYPE_INFO,
                timeout=7,
            )
            self.completed.update(completed_stems)
            self.selected = {}
            self.refresh_list()
        else:
            self["status"].setText("Download failed")
            self.session.open(
                MessageBox,
                "خطا در دانلود یا آماده‌سازی پیکون‌ها. لطفاً دوباره تلاش کنید.",
                MessageBox.TYPE_ERROR,
                timeout=8,
            )


class AboutScreen(Screen):
    skin = """
    <screen name="AboutScreen" position="center,center" size="850,520"
            title="About">
        <widget name="title" position="35,45" size="780,60"
                font="Regular;38" halign="center" />
        <widget name="youtubeLogo" position="365,115" size="120,68"
                pixmap="/usr/lib/enigma2/python/Plugins/Extensions/OnlinePicons/youtube.png"
                alphatest="blend" />
        <widget name="body" position="55,190" size="740,230"
                font="Regular;27" halign="center" valign="center" />
        <widget name="hint" position="35,455" size="780,35"
                font="Regular;21" halign="center" foregroundColor="#aaaaaa" />
    </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self["title"] = Label("About")
        self["youtubeLogo"] = Pixmap()
        self["body"] = Label(
            "YouTube: @routekernel\n\n"
            "Version: %s\n\n"
            "GitHub: github.com/%s" % (PLUGIN_VERSION, REPOSITORY)
        )
        self["hint"] = Label("EXIT: Close")
        self["actions"] = ActionMap(
            ["OkCancelActions"],
            {"ok": self.close, "cancel": self.close},
            -1,
        )


def main(session, **kwargs):
    session.open(OnlinePiconsMain)


def Plugins(**kwargs):
    return [
        PluginDescriptor(
            name="Online Picons",
            description="Download 220x132 picons from GitHub",
            where=PluginDescriptor.WHERE_PLUGINMENU,
            icon="plugin.png",
            fnc=main,
        )
    ]
# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading

try:
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError
except ImportError:
    from urllib2 import Request, urlopen, HTTPError

from Components.ActionMap import ActionMap
from Components.Console import Console
from Components.Label import Label
from Components.MenuList import MenuList
from Components.MultiContent import (
    MultiContentEntryPixmapAlphaTest,
    MultiContentEntryText,
)
from Components.Pixmap import Pixmap
from Components.config import ConfigSubsection, ConfigText, config, configfile
from Plugins.Plugin import PluginDescriptor
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Tools.LoadPixmap import LoadPixmap
from twisted.internet import reactor
from enigma import (
    RT_HALIGN_LEFT,
    RT_VALIGN_CENTER,
    eListboxPythonMultiContent,
    eTimer,
    gFont,
)

from . import PLUGIN_VERSION


REPOSITORY = "dreamboxone/online-picons"
RAW_BASE = "https://raw.githubusercontent.com/%s/main" % REPOSITORY
GOOGLE_HOST = "google.com"
GITHUB_HOST = "github.com"
PLUGIN_PATH = os.path.dirname(os.path.abspath(__file__))
PY2 = sys.version_info[0] == 2

try:
    text_type = unicode
except NameError:
    text_type = str


def _menu_text(value):
    """Return the string type expected by DreamOS eListbox content."""
    if PY2 and isinstance(value, text_type):
        return value.encode("utf-8")
    return value


def _set_menu_style(menu, font_size, item_height):
    """Style MenuList content without applying attributes to eListbox."""
    font = gFont("Regular", font_size)
    try:
        menu.l.setFont(font)
    except TypeError:
        try:
            menu.l.setFont(0, font)
        except Exception:
            pass
    except Exception:
        pass
    try:
        menu.l.setItemHeight(item_height)
    except Exception:
        pass


if not hasattr(config.plugins, "onlinepicons"):
    config.plugins.onlinepicons = ConfigSubsection()
config.plugins.onlinepicons.destination = ConfigText(
    default="/media/hdd/picon", fixed_size=False
)


# title, archive stem. Duplicates in the supplied list are intentionally removed.
SATELLITES = [
    ("Picons-220x132-22°W (SES 4)", "22w"),
    ("Picons-220x132-15°W (Telstar 12)", "15w"),
    ("Picons-220x132-14°W (Express AM8)", "14w"),
    ("Picons-220x132-8°W (Eutelsat 8W)", "8w"),
    ("Picons-220x132-7°W (Nilesat 201/301/7W)", "7w"),
    ("Picons-220x132-5°W (Eutelsat 5W)", "5w"),
    ("Picons-220x132-4°W (Dror 1)", "4w"),
    ("Picons-220x132-3°W (ABS 3A)", "3w"),
    ("Picons-220x132-0.8°W (Thor 5/6/7/Intelsat 10-02)", "0.8w"),
    ("Picons-220x132-1.9°E (BulgariaSat 1)", "1.9e"),
    ("Picons-220x132-3°E (Eutelsat 3B)", "3e"),
    ("Picons-220x132-4.9°E (Astra 4A/SES 5)", "4.9e"),
    ("Picons-220x132-7°E (Eutelsat 7B/7C)", "7e"),
    ("Picons-220x132-9°E (Eutelsat 9B)", "9e"),
    ("Picons-220x132-10.0°E (Eutelsat 10B)", "10e"),
    ("Picons-220x132-13.0°E (Hotbird 13F/13G)", "13e"),
    ("Picons-220x132-16.0°E (Eutelsat 16A)", "16e"),
    ("Picons-220x132-17.0°E (Amos 17)", "17e"),
    ("Picons-220x132-19.2°E (Astra 1N/1P)", "19.2e"),
    ("Picons-220x132-26.0°E (Badr 7/8-Es'hail 2)", "26e"),
    ("Picons-220x132-42.0°E (Turksat 3A/4A/5B/6A)", "42e"),
    ("Picons-220x132-46.0°E (Azeraspace 1)", "46e"),
    ("Picons-220x132-52.0°E (TurkmenÄlem/MonacoSat)", "52e"),
    ("Picons-220x132-52.5°E (Al Yah 1)", "52.5e"),
    ("Picons-220x132-53.0°E (Express AM6)", "53e"),
    ("Picons-220x132-62.0°E (Intelsat 39)", "62e"),
    ("Picons-220x132-68.5°E (Intelsat 20/36)", "68.5e"),
    ("Picons-220x132-70.5°E (Eutelsat 70B)", "70.5e"),
    ("Picons-220x132-78.5°E (Thaicom 6/8)", "78.5e"),
    ("Picons-220x132-80.0°E (Express 80)", "80e"),
    ("Picons-220x132-95.0°E (SES 12)", "95e"),
    ("Picons-220x132-100.5°E (Asiasat 5)", "100.5e"),
]


def _timer_start(timer, delay, callback):
    try:
        timer.callback.append(callback)
    except Exception:
        timer.timeout.connect(callback)
    timer.start(delay, True)


def _request(url, method=None, timeout=8):
    headers = {"User-Agent": "OnlinePicons/%s" % PLUGIN_VERSION}
    try:
        request = Request(url, headers=headers, method=method or "GET")
    except TypeError:  # Python 2 Request has no method argument.
        request = Request(url, headers=headers)
        if method:
            request.get_method = lambda: method
    return urlopen(request, timeout=timeout)


def _url_exists(url):
    try:
        response = _request(url, method="HEAD", timeout=8)
        code = getattr(response, "status", response.getcode())
        response.close()
        return 200 <= code < 400
    except HTTPError as error:
        return error.code not in (404, 410) and error.code < 500
    except Exception:
        return False


def _find_archive(stem):
    url = "%s/%s.rar" % (RAW_BASE, stem)
    return url if _url_exists(url) else None


def _archive_stem(title):
    """Derive the RAR name from the orbital position in the visible title."""
    match = re.search(r"Picons-220x132-([0-9]+(?:\.[0-9]+)?)", title)
    if not match:
        return None
    position = match.group(1)
    if "." in position:
        position = position.rstrip("0").rstrip(".")
    orbital_token = title[match.end():].split(" ", 1)[0].upper()
    direction = "e" if "E" in orbital_token else "w"
    return position + direction


def _extractor_available():
    for command in ("unrar", "7z", "7za", "bsdtar"):
        for directory in os.environ.get("PATH", "").split(os.pathsep):
            executable = os.path.join(directory, command)
            if os.path.isfile(executable) and os.access(executable, os.X_OK):
                return True
    return False


class OnlinePiconsMain(Screen):
    skin = """
    <screen name="OnlinePiconsMain" position="center,center" size="900,560"
            title="Online Picons">
        <widget name="title" position="45,30" size="810,55"
                font="Regular;38" halign="center" />
        <widget name="menu" position="65,115" size="715,310"
                scrollbarMode="showNever" />
        <widget name="hint" position="45,480" size="810,38"
                font="Regular;22" halign="center" foregroundColor="#aaaaaa" />
    </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self["title"] = Label("Online Picons")
        self["menu"] = MenuList(
            [
                self._menu_entry("Settings", "settings.png"),
                self._menu_entry("Download Picons", "download.png"),
                self._menu_entry("About", "about.png"),
            ],
            enableWrapAround=True,
            content=eListboxPythonMultiContent,
        )
        self["menu"].l.setFont(0, gFont("Regular", 38))
        self["menu"].l.setItemHeight(64)
        self["hint"] = Label("OK: Select     EXIT: Close")
        self["actions"] = ActionMap(
            ["OkCancelActions"],
            {"ok": self.open_selected, "cancel": self.close},
            -1,
        )

    def _menu_entry(self, text, icon):
        return [
            _menu_text(text),
            MultiContentEntryPixmapAlphaTest(
                pos=(8, 8),
                size=(48, 48),
                png=LoadPixmap(
                    cached=True,
                    path=os.path.join(PLUGIN_PATH, icon),
                ),
            ),
            MultiContentEntryText(
                pos=(76, 0),
                size=(627, 64),
                font=0,
                flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                text=_menu_text(text),
            ),
        ]

    def open_selected(self):
        index = self["menu"].getSelectedIndex()
        if index == 0:
            self.session.open(DestinationScreen)
        elif index == 1:
            self.session.open(DownloadScreen)
        else:
            self.session.open(AboutScreen)


class DestinationScreen(Screen):
    skin = """
    <screen name="DestinationScreen" position="center,center" size="1000,590"
            title="Online Picons - Settings">
        <widget name="heading" position="45,25" size="910,45"
                font="Regular;30" halign="center" />
        <widget name="paths" position="65,100" size="870,260"
                scrollbarMode="showNever" />
        <widget name="custom" position="65,385" size="870,55"
                font="Regular;25" halign="left" valign="center"
                backgroundColor="#202020" transparent="0" />
        <widget name="keysLeft" position="130,485" size="390,42"
                font="Regular;22" halign="right" />
        <widget name="greenKey" position="520,485" size="78,42"
                font="Regular;22" halign="center" foregroundColor="#00ff00" />
        <widget name="keysRight" position="598,485" size="270,42"
                font="Regular;22" halign="left" />
    </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.paths = [
            "/media/hdd/picon",
            "/media/usb/picon",
            config.plugins.onlinepicons.destination.value
            if config.plugins.onlinepicons.destination.value not in
            ("/media/hdd/picon", "/media/usb/picon")
            else "/media/picon",
        ]
        saved = config.plugins.onlinepicons.destination.value
        self.selected = self.paths.index(saved) if saved in self.paths else 2
        self["heading"] = Label("Choose the destination for downloaded picons")
        self["paths"] = MenuList([])
        _set_menu_style(self["paths"], 30, 48)
        self["custom"] = Label("")
        self["keysLeft"] = Label("OK: Select     BLUE: Edit custom path     ")
        self["greenKey"] = Label("GREEN")
        self["keysRight"] = Label(": Save")
        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions"],
            {
                "ok": self.select_path,
                "cancel": self.close,
                "blue": self.edit_custom,
                "green": self.save,
            },
            -1,
        )
        self.refresh()

    def refresh(self):
        rows = []
        for index, path in enumerate(self.paths):
            mark = "[X]" if index == self.selected else "[ ]"
            label = path if index < 2 else "Custom path"
            rows.append(_menu_text("%s  %s" % (mark, label)))
        current = self["paths"].getSelectedIndex()
        self["paths"].setList(rows)
        self["paths"].moveToIndex(current)
        self["custom"].setText("  %s" % self.paths[2])

    def select_path(self):
        self.selected = self["paths"].getSelectedIndex()
        if self.selected == 2:
            self.edit_custom()
        else:
            self.refresh()

    def edit_custom(self):
        self.session.openWithCallback(
            self.custom_entered,
            VirtualKeyBoard,
            title="Enter picon destination path",
            text=self.paths[2],
        )

    def custom_entered(self, value):
        if value:
            value = value.strip()
            if not value.startswith("/"):
                self.session.open(
                    MessageBox,
                    "The path must start with /",
                    MessageBox.TYPE_ERROR,
                    timeout=5,
                )
                return
            self.paths[2] = os.path.normpath(value)
            self.selected = 2
            self.refresh()

    def save(self):
        destination = self.paths[self.selected]
        config.plugins.onlinepicons.destination.value = destination
        config.plugins.onlinepicons.destination.save()
        configfile.save()
        self.session.openWithCallback(
            lambda unused=None: self.close(),
            MessageBox,
            "Picon destination saved:\n%s" % destination,
            MessageBox.TYPE_INFO,
            timeout=3,
        )


class DownloadScreen(Screen):
    skin = """
    <screen name="DownloadScreen" position="center,center" size="1180,690"
            title="Online Picons - Download Picons">
        <widget name="online" position="35,15" size="105,45"
                font="Regular;27" valign="center" />
        <widget name="onlineDot" position="145,21" size="32,32"
                pixmap="/usr/lib/enigma2/python/Plugins/Extensions/OnlinePicons/dot-checking.png"
                alphatest="blend" />
        <widget name="connection" position="185,15" size="280,45"
                font="Regular;23" valign="center" />
        <widget name="destination" position="470,25" size="675,38"
                font="Regular;21" halign="right" foregroundColor="#aaaaaa" />
        <widget name="satellites" position="35,85" size="1110,490"
                scrollbarMode="showOnDemand" />
        <widget name="status" position="35,585" size="1110,38"
                font="Regular;21" halign="center" />
        <widget name="keysLeft" position="190,635" size="430,35"
                font="Regular;22" halign="right" />
        <widget name="greenKey" position="620,635" size="78,35"
                font="Regular;22" halign="center" foregroundColor="#00ff00" />
        <widget name="keysRight" position="698,635" size="300,35"
                font="Regular;22" halign="left" />
    </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.selected = {}
        self.completed = set()
        self.available_urls = {}
        self.busy = False
        self.connectivity = "checking"
        self.connectivity_check_done = False
        self.ping_pending = set()
        self.ping_results = {}
        self.ping_console = Console()
        self.ping_timeout_timer = eTimer()
        self.probe_console = Console()
        self.probe_timeout_timer = eTimer()
        self.active_probe = None
        self.extractor_console = Console()
        self.pending_download_stems = None
        self.screen_closed = False
        self["online"] = Label("Internet")
        self["onlineDot"] = Pixmap()
        self["connection"] = Label("Checking...")
        self["destination"] = Label(
            "Destination: %s" % config.plugins.onlinepicons.destination.value
        )
        self["satellites"] = MenuList(
            [],
            enableWrapAround=True,
            content=eListboxPythonMultiContent,
        )
        self["satellites"].l.setFont(0, gFont("Regular", 32))
        self["satellites"].l.setItemHeight(46)
        self["status"] = Label("Checking internet connection...")
        self["keysLeft"] = Label("OK: Select/Unselect     ")
        self["greenKey"] = Label("GREEN")
        self["keysRight"] = Label(": Download     EXIT: Back")
        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions"],
            {
                "ok": self.toggle_current,
                "cancel": self.close,
                "green": self.download_selected,
            },
            -1,
        )
        self.onClose.append(self._cleanup)
        self.refresh_list()
        self._start_connectivity_check()

    def _cleanup(self):
        self.screen_closed = True
        try:
            self.ping_timeout_timer.stop()
        except Exception:
            pass
        try:
            self.probe_timeout_timer.stop()
        except Exception:
            pass
        try:
            self.ping_console.killAll()
        except Exception:
            pass
        try:
            self.probe_console.killAll()
        except Exception:
            pass
        try:
            self.extractor_console.killAll()
        except Exception:
            pass

    def _run_background(self, kind, function, *args):
        def runner():
            try:
                result = function(*args)
                success = True
            except Exception as error:
                success = False
                result = str(error)
            reactor.callFromThread(
                self._background_finished,
                kind,
                success,
                result,
            )
        thread = threading.Thread(target=runner)
        thread.daemon = True
        thread.start()

    def _background_finished(self, kind, success, result):
        if self.screen_closed:
            return
        if kind == "download":
            self.busy = False
            self._download_finished(success, result)

    def _start_connectivity_check(self):
        self.ping_pending = set(("google", "github"))
        commands = (
            ("google", "ping -c 1 -W 3 %s" % GOOGLE_HOST),
            ("github", "ping -c 1 -W 3 %s" % GITHUB_HOST),
        )
        _timer_start(
            self.ping_timeout_timer,
            6000,
            self._ping_check_timed_out,
        )
        for key, command in commands:
            try:
                self.ping_console.ePopen(
                    command,
                    self._ping_finished,
                    [key],
                )
            except Exception:
                self.ping_results[key] = False
                self.ping_pending.discard(key)
        if not self.ping_pending:
            self._finish_connectivity_check()

    def _ping_finished(self, output, return_code, extra_args):
        if self.connectivity_check_done:
            return
        key = extra_args[0]
        self.ping_results[key] = return_code == 0
        self.ping_pending.discard(key)
        if not self.ping_pending:
            self._finish_connectivity_check()

    def _ping_check_timed_out(self):
        if self.connectivity_check_done:
            return
        for key in self.ping_pending:
            self.ping_results[key] = False
        self.ping_pending.clear()
        self._finish_connectivity_check()
        try:
            self.ping_console.killAll()
        except Exception:
            pass

    def _finish_connectivity_check(self):
        if self.connectivity_check_done:
            return
        self.connectivity_check_done = True
        try:
            self.ping_timeout_timer.stop()
        except Exception:
            pass
        google = self.ping_results.get("google", False)
        github = self.ping_results.get("github", False)
        if not google:
            state = "offline"
        else:
            state = "online" if github else "google_only"
        self._show_connectivity(state)

    def _show_connectivity(self, state):
        self.connectivity = state
        if state == "online":
            self["connection"].setText("Online")
            self._set_connection_dot("green")
            self["status"].setText("Connected to Google and GitHub")
        elif state == "google_only":
            self["connection"].setText("Limited Internet")
            self._set_connection_dot("yellow")
            self["status"].setText("Internet works, but GitHub is unavailable")
        else:
            self["connection"].setText("Offline")
            self._set_connection_dot("red")
            self["status"].setText("No internet connection")

    def _set_connection_dot(self, color):
        path = os.path.join(PLUGIN_PATH, "dot-%s.png" % color)
        if os.path.exists(path) and self["onlineDot"].instance is not None:
            self["onlineDot"].instance.setPixmapFromFile(path)

    def refresh_list(self):
        index = self["satellites"].getSelectedIndex()
        rows = []
        for title, configured_stem in SATELLITES:
            stem = _archive_stem(title) or configured_stem
            display_title = title
            if PY2 and isinstance(display_title, str):
                display_title = display_title.decode("utf-8")
            selected = stem in self.selected
            row = [_menu_text(stem)]
            if selected:
                row.append(MultiContentEntryText(
                    pos=(6, 0),
                    size=(34, 46),
                    font=0,
                    flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                    text=_menu_text("X"),
                    color=0x00FF00,
                    color_sel=0x00FF00,
                ))
            elif stem in self.completed:
                row.append(MultiContentEntryPixmapAlphaTest(
                    pos=(5, 7),
                    size=(32, 32),
                    png=LoadPixmap(
                        cached=True,
                        path=os.path.join(PLUGIN_PATH, "check.png"),
                    ),
                ))
            else:
                row.append(MultiContentEntryText(
                    pos=(6, 0),
                    size=(34, 46),
                    font=0,
                    flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                    text=_menu_text(""),
                ))
            row.append(
                MultiContentEntryText(
                    pos=(42, 0),
                    size=(1055, 46),
                    font=0,
                    flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                    text=_menu_text(display_title),
                )
            )
            rows.append(row)
        self["satellites"].setList(rows)
        self["satellites"].moveToIndex(index)

    def toggle_current(self):
        if self.busy:
            return
        if self.connectivity != "online":
            self.session.open(
                MessageBox,
                "به دلیل عدم اتصال به اینترنت امکان دانلود Picon وجود ندارد.",
                MessageBox.TYPE_ERROR,
                timeout=5,
            )
            return
        index = self["satellites"].getSelectedIndex()
        title, configured_stem = SATELLITES[index]
        stem = _archive_stem(title) or configured_stem
        if stem in self.selected:
            del self.selected[stem]
            self.refresh_list()
            return
        if stem in self.available_urls:
            self.selected[stem] = title
            self.refresh_list()
            self["status"].setText("Selected: %s" % title)
            return
        self.busy = True
        self["status"].setText("Checking GitHub for %s..." % title)
        url = "%s/%s.rar" % (RAW_BASE, stem)
        self.active_probe = (index, title, stem, url)
        _timer_start(
            self.probe_timeout_timer,
            1900,
            self._probe_timed_out,
        )
        try:
            self.probe_console.ePopen(
                "wget -q --spider -T 2 %s" % url,
                self._probe_command_finished,
                [],
            )
        except Exception:
            self._finish_probe(False)

    def _probe_command_finished(self, output, return_code, extra_args):
        if self.active_probe is not None:
            self._finish_probe(return_code == 0)

    def _probe_timed_out(self):
        if self.active_probe is None:
            return
        self._finish_probe(False)
        try:
            self.probe_console.killAll()
        except Exception:
            pass

    def _finish_probe(self, available):
        if self.active_probe is None:
            return
        try:
            self.probe_timeout_timer.stop()
        except Exception:
            pass
        index, title, stem, url = self.active_probe
        self.active_probe = None
        self.busy = False
        if not available:
            self.session.open(
                MessageBox,
                _menu_text(
                    u"این فایل فعلا وجود ندارد. لطفا بعدا مراجعه نمایید.\n\n"
                    u"This file is not uploaded yet. Please visit us later..."
                ),
                MessageBox.TYPE_INFO,
                timeout=5,
            )
            self["status"].setText("Archive not available: %s" % title)
            return
        self.available_urls[stem] = url
        self.selected[stem] = title
        self.refresh_list()
        self["status"].setText("Selected: %s" % title)

    def download_selected(self):
        if self.busy:
            return
        if self.connectivity != "online":
            self.session.open(
                MessageBox,
                "به دلیل عدم اتصال به اینترنت امکان دانلود Picon وجود ندارد.",
                MessageBox.TYPE_ERROR,
                timeout=5,
            )
            return
        if not self.selected:
            self.session.open(
                MessageBox,
                "ابتدا حداقل یک ماهواره را انتخاب کنید.",
                MessageBox.TYPE_INFO,
                timeout=5,
            )
            return
        stems = list(self.selected.keys())
        if not _extractor_available():
            self.busy = True
            self.pending_download_stems = stems
            self["status"].setText("Preparing download support...")
            command = (
                "sh -c '"
                "apt-get update >/tmp/online-picons-setup.log 2>&1 || true; "
                "apt-get install -y unrar >>/tmp/online-picons-setup.log 2>&1 || "
                "apt-get install -y unrar-free >>/tmp/online-picons-setup.log 2>&1 || "
                "apt-get install -y p7zip-full >>/tmp/online-picons-setup.log 2>&1 || "
                "apt-get install -y p7zip >>/tmp/online-picons-setup.log 2>&1"
                "'"
            )
            try:
                self.extractor_console.ePopen(
                    command,
                    self._extractor_install_finished,
                    [],
                )
            except Exception:
                self._extractor_install_finished("", 1, [])
            return
        self._start_download(stems)

    def _extractor_install_finished(self, output, return_code, extra_args):
        stems = self.pending_download_stems
        self.pending_download_stems = None
        if return_code != 0 or not _extractor_available():
            self.busy = False
            self["status"].setText("Download preparation failed")
            self.session.open(
                MessageBox,
                "امکان آماده‌سازی دانلود وجود ندارد. اتصال اینترنت را بررسی و دوباره تلاش کنید.",
                MessageBox.TYPE_ERROR,
                timeout=7,
            )
            return
        self._start_download(stems)

    def _start_download(self, stems):
        self.busy = True
        self["status"].setText("Downloading selected picons...")
        self._run_background("download", self._download_all, stems)

    def _download_all(self, stems):
        destination = config.plugins.onlinepicons.destination.value
        if not destination.startswith("/"):
            raise RuntimeError("Invalid destination path")
        if not os.path.isdir(destination):
            os.makedirs(destination)
        installed = 0
        completed_stems = []
        temp_root = tempfile.mkdtemp(prefix="online-picons-", dir="/tmp")
        try:
            for stem in stems:
                url = self.available_urls.get(stem) or _find_archive(stem)
                if not url:
                    continue
                extension = os.path.splitext(url)[1].lower()
                archive = os.path.join(temp_root, stem + extension)
                response = _request(url, timeout=45)
                with open(archive, "wb") as output:
                    while True:
                        block = response.read(1024 * 128)
                        if not block:
                            break
                        output.write(block)
                response.close()
                unpacked = os.path.join(temp_root, "unpacked-" + stem)
                os.makedirs(unpacked)
                self._extract(archive, unpacked, extension)
                for root, dirs, files in os.walk(unpacked):
                    for filename in files:
                        if filename.lower().endswith(".png"):
                            shutil.copy2(
                                os.path.join(root, filename),
                                os.path.join(destination, filename),
                            )
                            installed += 1
                completed_stems.append(stem)
            return installed, destination, completed_stems
        finally:
            shutil.rmtree(temp_root, ignore_errors=True)

    def _extract(self, archive, destination, extension):
        commands = [
            ["unrar", "x", "-o+", archive, destination + os.sep],
            ["7z", "x", "-y", "-o" + destination, archive],
            ["7za", "x", "-y", "-o" + destination, archive],
            ["bsdtar", "-xf", archive, "-C", destination],
            ["tar", "-xf", archive, "-C", destination],
        ]
        for command in commands:
            try:
                process = subprocess.Popen(
                    command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
                process.communicate()
                if process.returncode == 0:
                    return
            except OSError:
                pass
        raise RuntimeError(
            "RAR extraction failed"
        )

    def _download_finished(self, success, result):
        if success:
            count, destination, completed_stems = result
            self["status"].setText("Download completed: %d PNG files" % count)
            self.session.open(
                MessageBox,
                "دانلود با موفقیت انجام شد.\n%d فایل در مسیر زیر کپی شد:\n%s"
                % (count, destination),
                MessageBox.TYPE_INFO,
                timeout=7,
            )
            self.completed.update(completed_stems)
            self.selected = {}
            self.refresh_list()
        else:
            self["status"].setText("Download failed")
            self.session.open(
                MessageBox,
                "خطا در دانلود یا آماده‌سازی پیکون‌ها. لطفاً دوباره تلاش کنید.",
                MessageBox.TYPE_ERROR,
                timeout=8,
            )


class AboutScreen(Screen):
    skin = """
    <screen name="AboutScreen" position="center,center" size="850,520"
            title="About">
        <widget name="title" position="35,45" size="780,60"
                font="Regular;38" halign="center" />
        <widget name="youtubeLogo" position="365,115" size="120,68"
                pixmap="/usr/lib/enigma2/python/Plugins/Extensions/OnlinePicons/youtube.png"
                alphatest="blend" />
        <widget name="body" position="55,190" size="740,230"
                font="Regular;27" halign="center" valign="center" />
        <widget name="hint" position="35,455" size="780,35"
                font="Regular;21" halign="center" foregroundColor="#aaaaaa" />
    </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self["title"] = Label("About")
        self["youtubeLogo"] = Pixmap()
        self["body"] = Label(
            "YouTube: @routekernel\n\n"
            "Version: %s\n\n"
            "GitHub: github.com/%s" % (PLUGIN_VERSION, REPOSITORY)
        )
        self["hint"] = Label("EXIT: Close")
        self["actions"] = ActionMap(
            ["OkCancelActions"],
            {"ok": self.close, "cancel": self.close},
            -1,
        )


def main(session, **kwargs):
    session.open(OnlinePiconsMain)


def Plugins(**kwargs):
    return [
        PluginDescriptor(
            name="Online Picons",
            description="Download 220x132 picons from GitHub",
            where=PluginDescriptor.WHERE_PLUGINMENU,
            icon="plugin.png",
            fnc=main,
        )
    ]
