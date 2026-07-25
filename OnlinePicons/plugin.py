# -*- coding: utf-8 -*-
from __future__ import print_function

import hashlib
import json
import os
import re
import shutil
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
from Components.MultiContent import (
    MultiContentEntryPixmapAlphaTest,
    MultiContentEntryText,
)
from Components.Pixmap import Pixmap
from Components.ProgressBar import ProgressBar
from Components.config import (
    ConfigSelection,
    ConfigSubsection,
    ConfigText,
    config,
    configfile,
)
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
    eSize,
    gFont,
)

from . import PLUGIN_VERSION


REPOSITORY = "dreamboxone/online-picons"
RAW_BASE = "https://raw.githubusercontent.com/%s/main" % REPOSITORY
LATEST_RELEASE_API = "https://api.github.com/repos/%s/releases/latest" % REPOSITORY
UPDATE_PACKAGE_PREFIX = "enigma2-plugin-extensions-online-picons_"
PRIMARY_PICONS_BASE = "https://thee.ir/picons"
GITHUB_PICONS_BASE = "%s/picons" % RAW_BASE
PICONS_SOURCES = (
    ("main", PRIMARY_PICONS_BASE),
    ("github", GITHUB_PICONS_BASE),
)
INDEX_FILENAME = "index.json"
HEALTH_FILENAME = "health.txt"
HEALTH_EXPECTED = "ONLINE-PICONS-OK"
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
config.plugins.onlinepicons.language = ConfigSelection(
    default="en",
    choices=[("en", "English"), ("fa", "فارسی"), ("ar", "العربية")],
)


TRANSLATIONS = {
    "fa": {
        "Update": "به‌روزرسانی",
        "Current version: %s": "نسخه نصب‌شده: %s",
        "Latest version: %s": "آخرین نسخه: %s",
        "Checking for the latest version...": "در حال بررسی آخرین نسخه...",
        "Downloading update: %d%%": "در حال دانلود به‌روزرسانی: %d%%",
        "Installing update...": "در حال نصب به‌روزرسانی...",
        "No new version is available.": "نسخه جدیدی برای نصب وجود ندارد.",
        "The update package was not found in the latest release.": "بسته به‌روزرسانی پیدا نشد.",
        "The update could not be completed.": "به‌روزرسانی انجام نشد.",
        "The update check timed out. Please try again.": "مهلت بررسی نسخه جدید به پایان رسید. لطفاً دوباره تلاش کنید.",
        "Update installed successfully. Please restart Enigma2.": "به‌روزرسانی با موفقیت نصب شد. لطفاً Enigma2 را راه‌اندازی مجدد کنید.",
        "Settings": "تنظیمات",
        "Download Picons": "دانلود پیکون‌ها",
        "Language": "زبان",
        "About": "درباره",
        "GREEN": "سبز",
        "OK: Select     EXIT: Close": "OK: انتخاب     EXIT: بستن",
        "Choose language": "انتخاب زبان",
        "OK: Select     EXIT: Back": "OK: انتخاب     EXIT: بازگشت",
        "Choose the destination for downloaded picons": "مسیر ذخیره پیکون‌های دانلودشده را انتخاب کنید",
        "Custom path": "مسیر دلخواه",
        "OK: Select     BLUE: Edit custom path     ": "OK: انتخاب     BLUE: ویرایش مسیر دلخواه     ",
        ": Save": ": ذخیره",
        "Enter picon destination path": "مسیر ذخیره پیکون را وارد کنید",
        "The path must start with /": "مسیر باید با / شروع شود",
        "Picon destination saved:\n%s": "مسیر پیکون ذخیره شد:\n%s",
        "Internet": "اینترنت",
        "Checking...": "در حال بررسی...",
        "Destination: %s": "مسیر: %s",
        "Checking download servers...": "در حال بررسی سرورهای دانلود...",
        "OK: Select/Unselect     ": "OK: انتخاب/لغو انتخاب     ",
        ": Download": ": دانلود",
        "EXIT: Back": "EXIT: بازگشت",
        "Online": "آنلاین",
        "Backup server": "سرور پشتیبان",
        "Offline": "آفلاین",
        "Connected to the main server": "اتصال به سرور اصلی برقرار است",
        "Main server is unavailable; backup server is ready": "سرور اصلی در دسترس نیست؛ سرور پشتیبان آماده است",
        "Neither download server is available": "هیچ‌یک از سرورهای دانلود در دسترس نیست",
        "Downloading is unavailable because no download server is reachable.": "هیچ سرور دانلودی در دسترس نیست؛ امکان دانلود وجود ندارد.",
        "Selected: %s": "انتخاب شد: %s",
        "The download catalog is incomplete. Please reopen this screen.": "فهرست دانلود ناقص است. این صفحه را ببندید و دوباره باز کنید.",
        "Select at least one satellite first.": "ابتدا حداقل یک ماهواره را انتخاب کنید.",
        "A tar.gz extraction tool is not available on this receiver.": "ابزار استخراج tar.gz روی این رسیور موجود نیست.",
        "Downloading selected picons...": "در حال دانلود پیکون‌های انتخاب‌شده...",
        "Downloading: %d%% (%d/%d)": "در حال دانلود: %d%% (%d/%d)",
        "Download completed: %d PNG files": "دانلود کامل شد: %d فایل PNG",
        "Download finished.\n%d files were copied to:\n%s": "دانلود تمام شد.\n%d فایل در مسیر زیر کپی شد:\n%s",
        "Download failed": "دانلود ناموفق بود",
        "The picons could not be downloaded or verified. Please try again.": "دانلود یا اعتبارسنجی پیکون‌ها انجام نشد. لطفاً دوباره تلاش کنید.",
        "Download Picons": "دانلود پیکون‌ها",
        "Version: %s": "نسخه: %s",
        "EXIT: Close": "EXIT: بستن",
    },
    "ar": {
        "Update": "تحديث",
        "Current version: %s": "الإصدار المثبت: %s",
        "Latest version: %s": "أحدث إصدار: %s",
        "Checking for the latest version...": "جارٍ التحقق من أحدث إصدار...",
        "Downloading update: %d%%": "جارٍ تنزيل التحديث: %d%%",
        "Installing update...": "جارٍ تثبيت التحديث...",
        "No new version is available.": "لا يوجد إصدار جديد للتثبيت.",
        "The update package was not found in the latest release.": "لم يتم العثور على حزمة التحديث في أحدث إصدار.",
        "The update could not be completed.": "تعذر إكمال التحديث.",
        "The update check timed out. Please try again.": "انتهت مهلة التحقق من التحديث. يرجى المحاولة مرة أخرى.",
        "Update installed successfully. Please restart Enigma2.": "تم تثبيت التحديث بنجاح. يرجى إعادة تشغيل Enigma2.",
        "Settings": "الإعدادات",
        "Download Picons": "تنزيل البيكونات",
        "Language": "اللغة",
        "About": "حول",
        "GREEN": "أخضر",
        "OK: Select     EXIT: Close": "OK: اختيار     EXIT: إغلاق",
        "Choose language": "اختر اللغة",
        "OK: Select     EXIT: Back": "OK: اختيار     EXIT: رجوع",
        "Choose the destination for downloaded picons": "اختر مسار حفظ البيكونات التي تم تنزيلها",
        "Custom path": "مسار مخصص",
        "OK: Select     BLUE: Edit custom path     ": "OK: اختيار     BLUE: تعديل المسار     ",
        ": Save": ": حفظ",
        "Enter picon destination path": "أدخل مسار حفظ البيكونات",
        "The path must start with /": "يجب أن يبدأ المسار بـ /",
        "Picon destination saved:\n%s": "تم حفظ مسار البيكونات:\n%s",
        "Internet": "الإنترنت",
        "Checking...": "جارٍ التحقق...",
        "Destination: %s": "المسار: %s",
        "Checking download servers...": "جارٍ التحقق من خوادم التنزيل...",
        "OK: Select/Unselect     ": "OK: اختيار/إلغاء     ",
        ": Download": ": تنزيل",
        "EXIT: Back": "EXIT: رجوع",
        "Online": "متصل",
        "Backup server": "خادم احتياطي",
        "Offline": "غير متصل",
        "Connected to the main server": "متصل بالخادم الرئيسي",
        "Main server is unavailable; backup server is ready": "الخادم الرئيسي غير متاح؛ الخادم الاحتياطي جاهز.",
        "Neither download server is available": "لا يتوفر أي خادم تنزيل",
        "Downloading is unavailable because no download server is reachable.": "لا يمكن التنزيل لأن خوادم التنزيل غير متاحة.",
        "Selected: %s": "تم الاختيار: %s",
        "The download catalog is incomplete. Please reopen this screen.": "قائمة التنزيل غير مكتملة. أغلق هذه الشاشة وافتحها مجدداً.",
        "Select at least one satellite first.": "اختر قمراً صناعياً واحداً على الأقل أولاً.",
        "A tar.gz extraction tool is not available on this receiver.": "أداة استخراج tar.gz غير متوفرة على هذا الجهاز.",
        "Downloading selected picons...": "جارٍ تنزيل البيكونات المحددة...",
        "Downloading: %d%% (%d/%d)": "جارٍ التنزيل: %d%% (%d/%d)",
        "Download completed: %d PNG files": "اكتمل التنزيل: %d ملف PNG",
        "Download finished.\n%d files were copied to:\n%s": "اكتمل التنزيل.\nتم نسخ %d ملف إلى:\n%s",
        "Download failed": "فشل التنزيل",
        "The picons could not be downloaded or verified. Please try again.": "تعذر تنزيل الأيقونات أو التحقق منها. يرجى المحاولة مرة أخرى.",
        "Download Picons": "تنزيل الأيقونات",
        "Version: %s": "الإصدار: %s",
        "EXIT: Close": "EXIT: إغلاق",
    },
}


def tr(message):
    language = config.plugins.onlinepicons.language.value
    return TRANSLATIONS.get(language, {}).get(message, message)


# title, archive stem. Every entry has a matching tar.gz archive in index.json.
SATELLITES = [
    ("220x132-15°W (Telstar 12)", "15w"),
    ("220x132-8°W (Eutelsat 8W)", "8w"),
    ("220x132-7°W (Nilesat 201/301/7W)", "7w"),
    ("220x132-4°W (Dror 1)", "4w"),
    ("220x132-0.8°W (Thor 5/6/7/Intelsat 10-02)", "0.8w"),
    ("220x132-1.9°E (BulgariaSat 1)", "1.9e"),
    ("220x132-3°E (Eutelsat 3B)", "3e"),
    ("220x132-4.8°E (Astra 4A/SES 5)", "4.8e"),
    ("220x132-7°E (Eutelsat 7B/7C)", "7e"),
    ("220x132-9°E (Eutelsat 9B)", "9e"),
    ("220x132-13.0°E (Hotbird 13F/13G)", "13e"),
    ("220x132-16.0°E (Eutelsat 16A)", "16e"),
    ("220x132-19.2°E (Astra 1N/1P)", "19.2e"),
    ("220x132-21.5°E (Eutelsat 21B)", "21.5e"),
    ("220x132-23.5°E (Astra 3C)", "23.5e"),
    ("220x132-26.0°E (Badr 7/8-Es'hail 2)", "26e"),
    ("220x132-40.0°E (Express AM7)", "40e"),
    ("220x132-42.0°E (Turksat 3A/4A/5B/6A)", "42e"),
    ("220x132-45.0°E (Azerspace 2/Intelsat 38)", "45e"),
    ("220x132-46.0°E (Azerspace 1)", "46e"),
    ("220x132-52.0°E (TürkmenÄlem/MonacoSat)", "52e"),
    ("220x132-52.5°E (Al Yah 1)", "52.5e"),
    ("220x132-53.0°E (Express AM6)", "53e"),
    ("220x132-56.0°E (Express AT2)", "56e"),
    ("220x132-57.0°E (NSS 12)", "57e"),
    ("220x132-62.0°E (Intelsat 39)", "62e"),
    ("220x132-68.5°E (Intelsat 20/36)", "68.5e"),
    ("220x132-70.5°E (Eutelsat 70B)", "70.5e"),
    ("220x132-78.5°E (Thaicom 6/8)", "78.5e"),
    ("220x132-80.0°E (Express 80)", "80e"),
    ("220x132-97.5°E (G-Sat 9)", "97.5e"),
]


def _timer_start(timer, delay, callback):
    try:
        timer.callback.append(callback)
    except Exception:
        timer.timeout.connect(callback)
    timer.start(delay, True)


def _request(url, method=None, timeout=12):
    headers = {
        "User-Agent": "OnlinePicons/%s" % PLUGIN_VERSION,
        "Cache-Control": "no-cache",
    }
    try:
        request = Request(url, headers=headers, method=method or "GET")
    except TypeError:  # Python 2 Request has no method argument.
        request = Request(url, headers=headers)
        if method:
            request.get_method = lambda: method
    return urlopen(request, timeout=timeout)


def _join_url(base_url, filename):
    return "%s/%s" % (base_url.rstrip("/"), filename.lstrip("/"))


def _read_text(url, timeout=10, max_bytes=1024 * 1024):
    response = _request(url, timeout=timeout)
    try:
        data = response.read(max_bytes + 1)
    finally:
        response.close()
    if len(data) > max_bytes:
        raise RuntimeError("Remote file is too large")
    if not isinstance(data, text_type):
        data = data.decode("utf-8", "replace")
    return data


def _load_catalog_from_source(base_url):
    health = _read_text(
        _join_url(base_url, HEALTH_FILENAME), timeout=8, max_bytes=256
    ).strip()
    if health != HEALTH_EXPECTED:
        raise RuntimeError("Invalid health response")

    raw_index = _read_text(
        _join_url(base_url, INDEX_FILENAME), timeout=12, max_bytes=1024 * 1024
    )
    index_data = json.loads(raw_index)
    if not isinstance(index_data, dict):
        raise RuntimeError("Invalid download catalog")
    if int(index_data.get("schema_version", 0) or 0) != 1:
        raise RuntimeError("Unsupported catalog schema")
    if index_data.get("archive_format") != "tar.gz":
        raise RuntimeError("Unsupported archive format")

    health_info = index_data.get("health") or {}
    expected_health = health_info.get("expected")
    if expected_health and expected_health != HEALTH_EXPECTED:
        raise RuntimeError("Catalog health value does not match")

    file_items = index_data.get("files")
    if not isinstance(file_items, list):
        raise RuntimeError("Catalog has no file list")

    catalog = {}
    archive_pattern = re.compile(
        r"^[0-9]+(?:\.[0-9]+)?[ew]\.tar\.gz$", re.IGNORECASE
    )
    sha_pattern = re.compile(r"^[0-9a-f]{64}$")
    for item in file_items:
        if not isinstance(item, dict) or not item.get("enabled", True):
            continue
        name = item.get("name")
        if not isinstance(name, text_type) or not archive_pattern.match(name):
            raise RuntimeError("Catalog contains an invalid archive name")
        stem = name[:-7].lower()
        position = item.get("satellite_position")
        if position and position.lower() != stem:
            raise RuntimeError("Catalog position does not match archive name")
        try:
            size = int(item.get("size") or 0)
        except (TypeError, ValueError):
            size = 0
        checksum = (item.get("sha256") or "").lower()
        if size <= 0 or not sha_pattern.match(checksum):
            raise RuntimeError("Catalog contains invalid archive metadata")
        catalog[stem] = {
            "name": name,
            "size": size,
            "sha256": checksum,
        }

    expected_stems = set(stem for title, stem in SATELLITES)
    missing_stems = sorted(expected_stems.difference(set(catalog.keys())))
    if missing_stems:
        raise RuntimeError("Catalog is missing: %s" % ", ".join(missing_stems))
    return catalog


def _command_available(command):
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        executable = os.path.join(directory, command)
        if os.path.isfile(executable) and os.access(executable, os.X_OK):
            return True
    return False


def _extractor_available():
    return _command_available("tar") or _command_available("bsdtar")


def _version_tuple(value):
    return tuple(int(number) for number in re.findall(r"\d+", value or ""))

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
            [],
            enableWrapAround=True,
            content=eListboxPythonMultiContent,
        )
        self["menu"].l.setFont(0, gFont("Regular", 38))
        self["menu"].l.setItemHeight(64)
        self["hint"] = Label("")
        self["actions"] = ActionMap(
            ["OkCancelActions"],
            {"ok": self.open_selected, "cancel": self.close},
            -1,
        )
        self.refresh_language()

    def refresh_language(self, unused=None):
        self["menu"].setList([
            self._menu_entry(tr("Settings"), "settings.png"),
            self._menu_entry(tr("Download Picons"), "download.png"),
            self._menu_entry(tr("Language"), "language.png"),
            self._menu_entry(tr("Update"), "update.png"),
            self._menu_entry(tr("About"), "about.png"),
        ])
        self["hint"].setText(tr("OK: Select     EXIT: Close"))

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
        elif index == 2:
            self.session.openWithCallback(self.refresh_language, LanguageScreen)
        elif index == 3:
            self.session.open(UpdateScreen)
        else:
            self.session.open(AboutScreen)


class LanguageScreen(Screen):
    skin = """
    <screen name="LanguageScreen" position="center,center" size="760,410"
            title="Language">
        <widget name="heading" position="35,25" size="690,48"
                font="Regular;32" halign="center" />
        <widget name="languages" position="90,100" size="580,190"
                scrollbarMode="showNever" />
        <widget name="hint" position="35,340" size="690,35"
                font="Regular;22" halign="center" foregroundColor="#aaaaaa" />
    </screen>
    """

    LANGUAGES = [("en", "English"), ("fa", "فارسی"), ("ar", "العربية")]

    def __init__(self, session):
        Screen.__init__(self, session)
        self.setTitle(tr("Language"))
        self["heading"] = Label(tr("Choose language"))
        self["languages"] = MenuList(
            [], enableWrapAround=True, content=eListboxPythonMultiContent
        )
        self["languages"].l.setFont(0, gFont("Regular", 32))
        self["languages"].l.setItemHeight(58)
        self["hint"] = Label(tr("OK: Select     EXIT: Back"))
        self["actions"] = ActionMap(
            ["OkCancelActions"],
            {"ok": self.select_language, "cancel": self.close},
            -1,
        )
        self.refresh()

    def refresh(self):
        rows = []
        selected_language = config.plugins.onlinepicons.language.value
        for code, label in self.LANGUAGES:
            row = [_menu_text(code)]
            row.append(MultiContentEntryText(
                pos=(15, 0), size=(45, 58), font=0,
                flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                text=_menu_text("X" if code == selected_language else ""),
                color=0x00FF00, color_sel=0x00FF00,
            ))
            row.append(MultiContentEntryText(
                pos=(80, 0), size=(480, 58), font=0,
                flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                text=_menu_text(label),
            ))
            rows.append(row)
        self["languages"].setList(rows)
        for index, item in enumerate(self.LANGUAGES):
            if item[0] == selected_language:
                self["languages"].moveToIndex(index)
                break

    def select_language(self):
        index = self["languages"].getSelectedIndex()
        config.plugins.onlinepicons.language.value = self.LANGUAGES[index][0]
        config.plugins.onlinepicons.language.save()
        configfile.save()
        self.setTitle(tr("Language"))
        self["heading"].setText(tr("Choose language"))
        self["hint"].setText(tr("OK: Select     EXIT: Back"))
        self.refresh()


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
        self.setTitle(tr("Settings"))
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
        self["heading"] = Label(tr("Choose the destination for downloaded picons"))
        self["paths"] = MenuList(
            [],
            enableWrapAround=True,
            content=eListboxPythonMultiContent,
        )
        _set_menu_style(self["paths"], 30, 48)
        self["custom"] = Label("")
        self["keysLeft"] = Label(tr("OK: Select     BLUE: Edit custom path     "))
        self["greenKey"] = Label(tr("GREEN"))
        self["keysRight"] = Label(tr(": Save"))
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
            label = path if index < 2 else tr("Custom path")
            row = [_menu_text(path)]
            row.append(MultiContentEntryText(
                pos=(15, 0), size=(65, 48), font=0,
                flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                text=_menu_text(mark),
            ))
            row.append(MultiContentEntryText(
                pos=(90, 0), size=(755, 48), font=0,
                flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                text=_menu_text(label),
            ))
            rows.append(row)
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
            title=tr("Enter picon destination path"),
            text=self.paths[2],
        )

    def custom_entered(self, value):
        if value:
            value = value.strip()
            if not value.startswith("/"):
                self.session.open(
                    MessageBox,
                    tr("The path must start with /"),
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
            tr("Picon destination saved:\n%s") % destination,
            MessageBox.TYPE_INFO,
            timeout=3,
        )


class DownloadScreen(Screen):
    skin = """
    <screen name="DownloadScreen" position="center,center" size="1180,690"
            title="Download Picons">
        <widget name="online" position="35,15" size="105,45"
                font="Regular;27" valign="center" />
        <widget name="onlineDot" position="145,21" size="32,32"
                pixmap="/usr/lib/enigma2/python/Plugins/Extensions/OnlinePicons/dot-checking.png"
                alphatest="blend" />
        <widget name="connection" position="181,15" size="280,45"
                font="Regular;23" halign="left" valign="center" />
        <widget name="destination" position="470,25" size="675,38"
                font="Regular;21" halign="right" foregroundColor="#aaaaaa" />
        <widget name="satellites" position="35,85" size="1110,490"
                scrollbarMode="showOnDemand" />
        <widget name="progress" position="250,582" size="680,20"
                borderWidth="2" />
        <widget name="status" position="35,608" size="1110,32"
                font="Regular;21" halign="center" />
        <widget name="keysLeft" position="120,648" size="430,30"
                 font="Regular;22" halign="right" />
        <widget name="greenKey" position="550,648" size="78,30"
                 font="Regular;22" halign="center" foregroundColor="#00ff00" />
        <widget name="downloadKey" position="628,648" size="160,30"
                 font="Regular;22" halign="left" />
        <widget name="exitKey" position="815,648" size="180,30"
                font="Regular;22" halign="left" />
    </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.setTitle(tr("Download Picons"))
        self.selected = {}
        self.completed = set()
        self.catalog = {}
        self.download_sources = []
        self.busy = False
        self.connectivity = "checking"
        self.screen_closed = False
        self["online"] = Label(tr("Internet"))
        self["onlineDot"] = Pixmap()
        self["connection"] = Label(tr("Checking..."))
        self["destination"] = Label(
            tr("Destination: %s") % config.plugins.onlinepicons.destination.value
        )
        self["satellites"] = MenuList(
            [],
            enableWrapAround=True,
            content=eListboxPythonMultiContent,
        )
        self["satellites"].l.setFont(0, gFont("Regular", 32))
        self["satellites"].l.setItemHeight(46)
        self["progress"] = ProgressBar()
        self["progress"].setValue(0)
        self["status"] = Label(tr("Checking download servers..."))
        self["keysLeft"] = Label(tr("OK: Select/Unselect     "))
        self["greenKey"] = Label(tr("GREEN"))
        self["downloadKey"] = Label(tr(": Download"))
        self["exitKey"] = Label(tr("EXIT: Back"))
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
        self.onShown.append(self._resize_connection_label)
        self.refresh_list()
        self._run_background("catalog", self._check_download_servers)

    def _cleanup(self):
        self.screen_closed = True

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
        if kind == "catalog":
            self._catalog_finished(success, result)
        elif kind == "download":
            self.busy = False
            self._download_finished(success, result)

    def _check_download_servers(self):
        errors = []
        for source_name, base_url in PICONS_SOURCES:
            try:
                catalog = _load_catalog_from_source(base_url)
                ordered_sources = [(source_name, base_url)]
                ordered_sources.extend(
                    source for source in PICONS_SOURCES
                    if source[0] != source_name
                )
                return source_name, catalog, ordered_sources
            except Exception as error:
                errors.append("%s: %s" % (source_name, error))
        raise RuntimeError("; ".join(errors))

    def _catalog_finished(self, success, result):
        if not success:
            self.catalog = {}
            self.download_sources = []
            self._show_connectivity("offline")
            return
        source_name, self.catalog, self.download_sources = result
        self._show_connectivity(
            "primary" if source_name == "main" else "fallback"
        )

    def _show_connectivity(self, state):
        self.connectivity = state
        if state == "primary":
            self._set_connection_text(tr("Online"))
            self._set_connection_dot("green")
            self["status"].setText(
                tr("Connected to the main server")
            )
        elif state == "fallback":
            self._set_connection_text(tr("Backup server"))
            self._set_connection_dot("yellow")
            self["status"].setText(
                tr("Main server is unavailable; backup server is ready")
            )
        else:
            self._set_connection_text(tr("Offline"))
            self._set_connection_dot("red")
            self["status"].setText(tr("Neither download server is available"))

    def _set_connection_text(self, text):
        self["connection"].setText(text)
        self._resize_connection_label()

    def _resize_connection_label(self):
        try:
            if self["connection"].instance is None:
                return
            text_size = self["connection"].instance.calculateSize()
            width = max(70, min(280, text_size.width() + 8))
            self["connection"].instance.resize(eSize(width, 45))
        except Exception:
            pass

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
            row.append(MultiContentEntryText(
                pos=(42, 0),
                size=(1055, 46),
                font=0,
                flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                text=_menu_text(display_title),
            ))
            rows.append(row)
        self["satellites"].setList(rows)
        if rows:
            self["satellites"].moveToIndex(
                max(0, min(index, len(rows) - 1))
            )

    def toggle_current(self):
        if self.busy:
            return
        if self.connectivity not in ("primary", "fallback"):
            self.session.open(
                MessageBox,
                tr("Downloading is unavailable because no download server is reachable."),
                MessageBox.TYPE_ERROR,
                timeout=5,
            )
            return
        index = self["satellites"].getSelectedIndex()
        title, stem = SATELLITES[index]
        if stem not in self.catalog:
            self.session.open(
                MessageBox,
                tr("The download catalog is incomplete. Please reopen this screen."),
                MessageBox.TYPE_ERROR,
                timeout=6,
            )
            return
        if stem in self.selected:
            del self.selected[stem]
        else:
            self.selected[stem] = title
            self["status"].setText(tr("Selected: %s") % title)
        self.refresh_list()

    def download_selected(self):
        if self.busy:
            return
        if self.connectivity not in ("primary", "fallback"):
            self.session.open(
                MessageBox,
                tr("Downloading is unavailable because no download server is reachable."),
                MessageBox.TYPE_ERROR,
                timeout=5,
            )
            return
        if not self.selected:
            self.session.open(
                MessageBox,
                tr("Select at least one satellite first."),
                MessageBox.TYPE_INFO,
                timeout=5,
            )
            return
        if not _extractor_available():
            self.session.open(
                MessageBox,
                tr("A tar.gz extraction tool is not available on this receiver."),
                MessageBox.TYPE_ERROR,
                timeout=7,
            )
            return
        self._start_download(list(self.selected.keys()))

    def _start_download(self, stems):
        self.busy = True
        self["progress"].setValue(0)
        self["status"].setText(tr("Downloading selected picons..."))
        self._run_background("download", self._download_all, stems)

    def _report_download_progress(self, percent, current, total):
        reactor.callFromThread(
            self._show_download_progress, percent, current, total
        )

    def _show_download_progress(self, percent, current, total):
        if self.screen_closed:
            return
        percent = max(0, min(100, int(percent)))
        self["progress"].setValue(percent)
        self["status"].setText(
            tr("Downloading: %d%% (%d/%d)") % (percent, current, total)
        )

    def _download_one_archive(
        self, metadata, target, item_index, current, total
    ):
        errors = []
        for source_name, base_url in self.download_sources:
            url = _join_url(base_url, metadata["name"])
            try:
                response = _request(url, timeout=45)
                downloaded = 0
                digest = hashlib.sha256()
                try:
                    with open(target, "wb") as output:
                        while True:
                            block = response.read(128 * 1024)
                            if not block:
                                break
                            output.write(block)
                            digest.update(block)
                            downloaded += len(block)
                            item_fraction = min(
                                1.0,
                                float(downloaded) / metadata["size"],
                            )
                            percent = int(
                                (item_index + item_fraction) * 100.0 / total
                            )
                            self._report_download_progress(
                                percent, current, total
                            )
                finally:
                    response.close()

                if downloaded != metadata["size"]:
                    raise RuntimeError("Downloaded size does not match index.json")
                if digest.hexdigest().lower() != metadata["sha256"]:
                    raise RuntimeError("SHA-256 does not match index.json")
                return source_name
            except Exception as error:
                errors.append("%s: %s" % (source_name, error))
                try:
                    os.unlink(target)
                except Exception:
                    pass
        raise RuntimeError(
            "Could not download %s (%s)"
            % (metadata["name"], "; ".join(errors))
        )

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
            total = len(stems)
            for item_index, stem in enumerate(stems):
                current = item_index + 1
                metadata = self.catalog.get(stem)
                if not metadata:
                    raise RuntimeError("Archive is missing from index.json")
                self._report_download_progress(
                    int(item_index * 100.0 / total), current, total
                )
                archive = os.path.join(temp_root, metadata["name"])
                self._download_one_archive(
                    metadata, archive, item_index, current, total
                )

                unpacked = os.path.join(temp_root, "unpacked-" + stem)
                os.makedirs(unpacked)
                self._extract(archive, unpacked)

                archive_png_count = 0
                for root, dirs, files in os.walk(unpacked):
                    for filename in files:
                        if filename.lower().endswith(".png"):
                            shutil.copy2(
                                os.path.join(root, filename),
                                os.path.join(destination, filename),
                            )
                            archive_png_count += 1
                            installed += 1
                if archive_png_count == 0:
                    raise RuntimeError("The archive contains no PNG files")
                completed_stems.append(stem)
                self._report_download_progress(
                    int(current * 100.0 / total), current, total
                )
            return installed, destination, completed_stems
        finally:
            shutil.rmtree(temp_root, ignore_errors=True)

    def _extract(self, archive, destination):
        commands = []
        if _command_available("tar"):
            commands.append(["tar", "-xzf", archive, "-C", destination])
        if _command_available("bsdtar"):
            commands.append(["bsdtar", "-xzf", archive, "-C", destination])
        for command in commands:
            try:
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                process.communicate()
                if process.returncode == 0:
                    return
            except OSError:
                pass
        raise RuntimeError("TAR.GZ extraction failed")

    def _download_finished(self, success, result):
        if success:
            count, destination, completed_stems = result
            self["progress"].setValue(100)
            self["status"].setText(
                tr("Download completed: %d PNG files") % count
            )
            self.session.open(
                MessageBox,
                tr("Download finished.\n%d files were copied to:\n%s")
                % (count, destination),
                MessageBox.TYPE_INFO,
                timeout=7,
            )
            self.completed.update(completed_stems)
            self.selected = {}
            self.refresh_list()
        else:
            self["progress"].setValue(0)
            self["status"].setText(tr("Download failed"))
            self.session.open(
                MessageBox,
                tr("The picons could not be downloaded or verified. Please try again."),
                MessageBox.TYPE_ERROR,
                timeout=8,
            )

class UpdateScreen(Screen):
    skin = """
    <screen name="UpdateScreen" position="center,center" size="900,500"
            title="Update">
        <widget name="heading" position="40,30" size="820,50"
                font="Regular;34" halign="center" />
        <widget name="current" position="85,115" size="730,42"
                font="Regular;28" halign="center" />
        <widget name="latest" position="85,170" size="730,42"
                font="Regular;28" halign="center" />
        <widget name="progress" position="110,250" size="680,28"
                borderWidth="2" />
        <widget name="percent" position="110,290" size="680,38"
                font="Regular;25" halign="center" />
        <widget name="status" position="55,355" size="790,45"
                font="Regular;24" halign="center" />
        <widget name="hint" position="55,445" size="790,32"
                font="Regular;21" halign="center" foregroundColor="#aaaaaa" />
    </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.setTitle(tr("Update"))
        self["heading"] = Label(tr("Update"))
        self["current"] = Label(tr("Current version: %s") % PLUGIN_VERSION)
        self["latest"] = Label(tr("Latest version: %s") % "...")
        self["progress"] = ProgressBar()
        self["progress"].setValue(0)
        self["percent"] = Label("0%")
        self["status"] = Label(tr("Checking for the latest version..."))
        self["hint"] = Label(tr("EXIT: Back"))
        self["actions"] = ActionMap(["OkCancelActions"], {"cancel": self.close}, -1)
        self.started = False
        self.closed = False
        self.check_pending = False
        self.check_timeout_call = None
        self.onShown.append(self.start_update)
        self.onClose.append(self._cleanup)

    def _cleanup(self):
        self.closed = True
        self.check_pending = False
        try:
            if self.check_timeout_call is not None and self.check_timeout_call.active():
                self.check_timeout_call.cancel()
        except Exception:
            pass
        self.check_timeout_call = None

    def start_update(self):
        if self.started:
            return
        self.started = True
        self.check_pending = True
        # reactor.callLater is more reliable than eTimer across Enigma2 images.
        # It also releases the Update screen even if DNS/urlopen hangs in the worker.
        self.check_timeout_call = reactor.callLater(7, self._check_timed_out)
        self._run_background("check", self._check_latest)

    def _check_timed_out(self):
        if self.closed or not self.check_pending:
            return
        self.check_pending = False
        self.check_timeout_call = None
        self["progress"].setValue(0)
        self["percent"].setText("--")
        message = tr("The update check timed out. Please try again.")
        self["status"].setText(message)
        # Keep the message inside this screen; do not open a global Enigma2 dialog.

    def _run_background(self, kind, function, *args):
        def worker():
            try:
                result = function(*args)
                success = True
            except Exception as error:
                result = str(error)
                success = False
            reactor.callFromThread(self._background_finished, kind, success, result)
        thread = threading.Thread(target=worker)
        thread.daemon = True
        thread.start()

    def _check_latest(self):
        raw_release = _read_text(
            LATEST_RELEASE_API,
            timeout=4,
            max_bytes=512 * 1024,
        )
        release_data = json.loads(raw_release)
        if not isinstance(release_data, dict):
            raise RuntimeError("Invalid GitHub release response")

        tag = release_data.get("tag_name")
        if not tag:
            raise RuntimeError("GitHub release has no version tag")
        latest = tag.lstrip("vV")

        # When the installed version is already current, skip package/asset work.
        if _version_tuple(latest) <= _version_tuple(PLUGIN_VERSION):
            return latest, None, None, None

        if _command_available("dpkg"):
            extension, installer = ".deb", "dpkg"
        elif _command_available("opkg"):
            extension, installer = ".ipk", "opkg"
        else:
            raise RuntimeError("No supported package manager was found")

        expected = "%s%s_all%s" % (
            UPDATE_PACKAGE_PREFIX,
            latest,
            extension,
        )
        selected_asset = None
        assets = release_data.get("assets") or []
        if not isinstance(assets, list):
            assets = []

        for asset in assets:
            if not isinstance(asset, dict):
                continue
            if asset.get("name") != expected:
                continue
            download_url = asset.get("browser_download_url")
            if not download_url:
                continue
            try:
                asset_size = int(asset.get("size") or 0)
            except (TypeError, ValueError):
                asset_size = 0
            selected_asset = {
                "name": expected,
                "browser_download_url": download_url,
                "size": asset_size,
            }
            break

        return latest, installer, extension, selected_asset

    def _background_finished(self, kind, success, result):
        if self.closed:
            return
        if kind == "check":
            if not self.check_pending:
                return
            self.check_pending = False
            try:
                if self.check_timeout_call is not None and self.check_timeout_call.active():
                    self.check_timeout_call.cancel()
            except Exception:
                pass
            self.check_timeout_call = None
        if not success:
            # Keep the Update screen responsive and report the error in-place.
            self["progress"].setValue(0)
            self["percent"].setText("--")
            self["status"].setText(tr("The update could not be completed."))
            return
        if kind == "check":
            latest = result[0]
            self["latest"].setText(tr("Latest version: %s") % latest)
            if _version_tuple(latest) <= _version_tuple(PLUGIN_VERSION):
                # No nested MessageBox: show the answer immediately on this screen.
                self["progress"].setValue(100)
                self["percent"].setText("100%")
                self["status"].setText(tr("No new version is available."))
                return
            if result[3] is None:
                message = tr("The update package was not found in the latest GitHub release.")
                self["status"].setText(message)
                self.session.open(MessageBox, message, MessageBox.TYPE_ERROR, timeout=7)
                return
            self["status"].setText(tr("Downloading update: %d%%") % 0)
            self._run_background("install", self._download_and_install, result)
            return
        self["progress"].setValue(100)
        self["percent"].setText("100%")
        message = tr("Update installed successfully. Please restart Enigma2.")
        self["status"].setText(message)
        self.session.open(MessageBox, message, MessageBox.TYPE_INFO, timeout=10)

    def _download_and_install(self, update_info):
        latest, installer, extension, asset = update_info
        url = asset.get("browser_download_url")
        if not url:
            raise RuntimeError("Release asset has no download URL")
        target = "/tmp/online-picons-update%s" % extension
        response = _request(url, timeout=60)
        total = int(asset.get("size") or 0)
        if not total:
            try:
                total = int(response.headers.get("Content-Length") or 0)
            except Exception:
                total = 0
        downloaded = 0
        try:
            package = open(target, "wb")
            try:
                while True:
                    block = response.read(128 * 1024)
                    if not block:
                        break
                    package.write(block)
                    downloaded += len(block)
                    if total:
                        percent = min(99, int(downloaded * 100 / total))
                        reactor.callFromThread(self._show_progress, percent)
            finally:
                package.close()
        finally:
            response.close()
        reactor.callFromThread(self._show_installing)
        command = ["dpkg", "-i", target] if installer == "dpkg" else ["opkg", "install", target]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output = process.communicate()[0]
        try:
            os.unlink(target)
        except Exception:
            pass
        if process.returncode:
            if not isinstance(output, text_type):
                output = output.decode("utf-8", "replace")
            raise RuntimeError(output[-800:])
        return latest

    def _show_progress(self, percent):
        if self.closed:
            return
        self["progress"].setValue(percent)
        self["percent"].setText("%d%%" % percent)
        self["status"].setText(tr("Downloading update: %d%%") % percent)

    def _show_installing(self):
        if self.closed:
            return
        self["progress"].setValue(100)
        self["percent"].setText("100%")
        self["status"].setText(tr("Installing update..."))


class AboutScreen(Screen):
    skin = """
    <screen name="AboutScreen" position="center,center" size="850,520"
            title="About">
        <widget name="youtubeLogo" position="175,45" size="64,64"
                pixmap="/usr/lib/enigma2/python/Plugins/Extensions/OnlinePicons/youtube.png"
                alphatest="blend" scale="1" />
        <widget name="youtubeText" position="270,45" size="480,64"
                font="Regular;28" halign="left" valign="center" />
        <widget name="telegramLogo" position="175,135" size="64,64"
                pixmap="/usr/lib/enigma2/python/Plugins/Extensions/OnlinePicons/telegram.png"
                alphatest="blend" scale="1" />
        <widget name="telegramText" position="270,135" size="480,64"
                font="Regular;28" halign="left" valign="center" />
        <widget name="githubLogo" position="175,225" size="64,64"
                pixmap="/usr/lib/enigma2/python/Plugins/Extensions/OnlinePicons/github.png"
                alphatest="blend" scale="1" />
        <widget name="githubText" position="270,225" size="480,64"
                font="Regular;25" halign="left" valign="center" />
        <widget name="version" position="55,350" size="740,45"
                font="Regular;25" halign="center" valign="center" />
        <widget name="hint" position="35,455" size="780,35"
                font="Regular;21" halign="center" foregroundColor="#aaaaaa" />
    </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.setTitle(tr("About"))
        self["youtubeLogo"] = Pixmap()
        self["youtubeText"] = Label("YouTube: @routekernel")
        self["telegramLogo"] = Pixmap()
        self["telegramText"] = Label(" @RouteKernel1")
        self["githubLogo"] = Pixmap()
        self["githubText"] = Label("github.com/%s" % REPOSITORY)
        self["version"] = Label(tr("Version: %s") % PLUGIN_VERSION)
        self["hint"] = Label(tr("EXIT: Close"))
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
            description="Smart Picons Downloader",
            where=PluginDescriptor.WHERE_PLUGINMENU,
            icon="plugin.png",
            fnc=main,
        )
    ]
