# -*- coding: utf-8 -*-
from __future__ import print_function

import os
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
from Components.Label import Label
from Components.MenuList import MenuList
from Components.Pixmap import Pixmap
from Components.config import ConfigSubsection, ConfigText, config, configfile
from Plugins.Plugin import PluginDescriptor
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.VirtualKeyBoard import VirtualKeyBoard
from enigma import eTimer

from . import PLUGIN_VERSION


REPOSITORY = "dreamboxone/online-picons"
RAW_BASE = "https://raw.githubusercontent.com/%s/main" % REPOSITORY
GOOGLE_CHECK = "https://www.google.com/generate_204"
GITHUB_CHECK = "https://github.com"
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
    ("Picons-220x132-14°W (Express AM44)", "14w"),
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


class OnlinePiconsMain(Screen):
    skin = """
    <screen name="OnlinePiconsMain" position="center,center" size="900,560"
            title="Online Picons">
        <widget name="title" position="45,30" size="810,55"
                font="Regular;38" halign="center" />
        <widget name="menu" position="120,115" size="660,310"
                scrollbarMode="showNever" />
        <widget name="settingsIcon" position="78,122" size="30,30"
                alphatest="blend" />
        <widget name="downloadIcon" position="78,167" size="30,30"
                alphatest="blend" />
        <widget name="aboutIcon" position="78,212" size="30,30"
                alphatest="blend" />
        <widget name="hint" position="45,480" size="810,38"
                font="Regular;22" halign="center" foregroundColor="#aaaaaa" />
    </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self["title"] = Label("Online Picons")
        self["menu"] = MenuList([
            "Settings",
            "Download Picons",
            "About",
        ])
        self["settingsIcon"] = Pixmap()
        self["downloadIcon"] = Pixmap()
        self["aboutIcon"] = Pixmap()
        self["hint"] = Label("OK: Select     EXIT: Close")
        self["actions"] = ActionMap(
            ["OkCancelActions"],
            {"ok": self.open_selected, "cancel": self.close},
            -1,
        )
        self.onLayoutFinish.append(self.load_icons)

    def load_icons(self):
        icons = (
            ("settingsIcon", "settings.png"),
            ("downloadIcon", "download.png"),
            ("aboutIcon", "about.png"),
        )
        for widget, filename in icons:
            path = os.path.join(PLUGIN_PATH, filename)
            if os.path.exists(path):
                self[widget].instance.setPixmapFromFile(path)

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
        <widget name="keys" position="65,485" size="870,42"
                font="Regular;22" halign="center" />
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
        self["custom"] = Label("")
        self["keys"] = Label("OK: Select     BLUE: Edit custom path     GREEN: Save")
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
        <widget name="online" position="35,22" size="105,45"
                font="Regular;27" />
        <widget name="onlineDot" position="145,27" size="28,28"
                alphatest="blend" />
        <widget name="connection" position="185,22" size="280,45"
                font="Regular;23" />
        <widget name="destination" position="470,25" size="675,38"
                font="Regular;21" halign="right" foregroundColor="#aaaaaa" />
        <widget name="satellites" position="35,85" size="1110,490"
                scrollbarMode="showOnDemand" />
        <widget name="status" position="35,585" size="1110,38"
                font="Regular;21" halign="center" />
        <widget name="keys" position="35,635" size="1110,35"
                font="Regular;22" halign="center" />
    </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.selected = {}
        self.available_urls = {}
        self.busy = False
        self.connectivity = "checking"
        self.result_queue = []
        self.poll_timer = eTimer()
        self["online"] = Label("Online")
        self["onlineDot"] = Pixmap()
        self["connection"] = Label("Checking...")
        self["destination"] = Label(
            "Destination: %s" % config.plugins.onlinepicons.destination.value
        )
        self["satellites"] = MenuList([])
        self["status"] = Label("Checking internet connection...")
        self["keys"] = Label("OK: Select/Unselect     GREEN: Download     EXIT: Back")
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
        self.onLayoutFinish.append(lambda: self._set_connection_dot("checking"))
        self.refresh_list()
        _timer_start(self.poll_timer, 150, self.poll_results)
        self._run_background("connectivity", self._check_connectivity)

    def _cleanup(self):
        try:
            self.poll_timer.stop()
        except Exception:
            pass

    def _run_background(self, kind, function, *args):
        def runner():
            try:
                result = function(*args)
                self.result_queue.append((kind, True, result))
            except Exception as error:
                self.result_queue.append((kind, False, str(error)))
        thread = threading.Thread(target=runner)
        thread.daemon = True
        thread.start()

    def poll_results(self):
        while self.result_queue:
            kind, success, result = self.result_queue.pop(0)
            if kind == "connectivity":
                self._show_connectivity(result if success else "offline")
            elif kind == "probe":
                self.busy = False
                self._probe_finished(success, result)
            elif kind == "download":
                self.busy = False
                self._download_finished(success, result)
        self.poll_timer.start(150, True)

    def _check_connectivity(self):
        google = False
        github = False
        try:
            response = _request(GOOGLE_CHECK, timeout=6)
            google = response.getcode() in (200, 204)
            response.close()
        except Exception:
            google = False
        if google:
            try:
                response = _request(GITHUB_CHECK, method="HEAD", timeout=6)
                github = response.getcode() < 500
                response.close()
            except Exception:
                github = False
        if not google:
            return "offline"
        return "online" if github else "google_only"

    def _show_connectivity(self, state):
        self.connectivity = state
        if state == "online":
            self["connection"].setText("Connected")
            self._set_connection_dot("green")
            self["status"].setText("Connected to Google and GitHub")
        elif state == "google_only":
            self["connection"].setText("GitHub unavailable")
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
        for title, stem in SATELLITES:
            display_title = title
            if PY2 and isinstance(display_title, str):
                display_title = display_title.decode("utf-8")
            rows.append(_menu_text(u"%s  %s" % (
                "[X]" if stem in self.selected else "[ ]",
                display_title,
            )))
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
        title, stem = SATELLITES[index]
        if stem in self.selected:
            del self.selected[stem]
            self.refresh_list()
            return
        self.busy = True
        self["status"].setText("Checking GitHub for %s..." % title)
        self._run_background("probe", self._probe_archive, index, title, stem)

    def _probe_archive(self, index, title, stem):
        url = self.available_urls.get(stem) or _find_archive(stem)
        return index, title, stem, url

    def _probe_finished(self, success, result):
        if not success:
            self["status"].setText("GitHub check failed")
            return
        index, title, stem, url = result
        if not url:
            self.session.open(
                MessageBox,
                "این پیکون وجود ندارد؛ لطفاً بعداً برای دانلود مراجعه کنید.",
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
        self.busy = True
        self["status"].setText("Downloading selected picons...")
        stems = list(self.selected.keys())
        self._run_background("download", self._download_all, stems)

    def _download_all(self, stems):
        destination = config.plugins.onlinepicons.destination.value
        if not destination.startswith("/"):
            raise RuntimeError("Invalid destination path")
        if not os.path.isdir(destination):
            os.makedirs(destination)
        installed = 0
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
            return installed, destination
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
            "ابزار استخراج RAR پیدا نشد. لطفاً unrar یا 7z را نصب کنید."
        )

    def _download_finished(self, success, result):
        if success:
            count, destination = result
            self["status"].setText("Download completed: %d PNG files" % count)
            self.session.open(
                MessageBox,
                "دانلود با موفقیت انجام شد.\n%d فایل در مسیر زیر کپی شد:\n%s"
                % (count, destination),
                MessageBox.TYPE_INFO,
                timeout=7,
            )
            self.selected = {}
            self.refresh_list()
        else:
            self["status"].setText("Download failed")
            self.session.open(
                MessageBox,
                "خطا در دانلود یا استخراج پیکون‌ها:\n%s" % result,
                MessageBox.TYPE_ERROR,
                timeout=8,
            )


class AboutScreen(Screen):
    skin = """
    <screen name="AboutScreen" position="center,center" size="850,520"
            title="About Online Picons">
        <widget name="title" position="35,45" size="780,60"
                font="Regular;38" halign="center" />
        <widget name="body" position="55,145" size="740,280"
                font="Regular;27" halign="center" valign="center" />
        <widget name="hint" position="35,455" size="780,35"
                font="Regular;21" halign="center" foregroundColor="#aaaaaa" />
    </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self["title"] = Label("Online Picons")
        self["body"] = Label(
            "YouTube: @routekernel\n\n"
            "Version: %s\n\n"
            "Build year: 2026 / 1405\n\n"
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
