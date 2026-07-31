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
from .assets import asset_path, ensure_assets


REPOSITORY = "dreamboxone/online-picons"
RAW_BASE = "https://raw.githubusercontent.com/%s/main" % REPOSITORY
LATEST_RELEASE_API = "https://api.github.com/repos/%s/releases/latest" % REPOSITORY
LATEST_RELEASE_PAGE = "https://github.com/%s/releases/latest" % REPOSITORY
LATEST_VERSION_FILE = "%s/OnlinePicons/__init__.py" % RAW_BASE
UPDATE_PACKAGE_PREFIX = "enigma2-plugin-extensions-online-picons_"
PRIMARY_PICONS_BASE = "http://thee.ir/picons"
GITHUB_PICONS_BASE = "%s/picons" % RAW_BASE
PICONS_SOURCES = (
    ("main", PRIMARY_PICONS_BASE),
    ("github", GITHUB_PICONS_BASE),
)
INDEX_FILENAME = "index.json"
LATEST_UPDATES_FILENAME = "RSS/latest_updates.txt"
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


def _set_text(component, value):
    """Set live label text safely on Python 2 DreamOS images."""
    component.setText(_menu_text(value))


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
    choices=[("en", "English"), ("fa", "ÙØ§Ø±Ø³ÛŒ"), ("ar", "Ø§Ù„Ø¹Ø±Ø¨ÙŠØ©")],
)


TRANSLATIONS = {
    "fa": {
        "Update": "Ø¨Ù‡â€ŒØ±ÙˆØ²Ø±Ø³Ø§Ù†ÛŒ",
        "Current version: %s": "Ù†Ø³Ø®Ù‡ Ù†ØµØ¨â€ŒØ´Ø¯Ù‡: %s",
        "Latest version: %s": "Ø¢Ø®Ø±ÛŒÙ† Ù†Ø³Ø®Ù‡: %s",
        "Checking for the latest version...": "Ø¯Ø± Ø­Ø§Ù„ Ø¨Ø±Ø±Ø³ÛŒ Ø¢Ø®Ø±ÛŒÙ† Ù†Ø³Ø®Ù‡...",
        "Downloading update: %d%%": "Ø¯Ø± Ø­Ø§Ù„ Ø¯Ø§Ù†Ù„ÙˆØ¯ Ø¨Ù‡â€ŒØ±ÙˆØ²Ø±Ø³Ø§Ù†ÛŒ: %d%%",
        "Installing update...": "Ø¯Ø± Ø­Ø§Ù„ Ù†ØµØ¨ Ø¨Ù‡â€ŒØ±ÙˆØ²Ø±Ø³Ø§Ù†ÛŒ...",
        "No new version is available.": "Ù†Ø³Ø®Ù‡ Ø¬Ø¯ÛŒØ¯ÛŒ Ø¨Ø±Ø§ÛŒ Ù†ØµØ¨ ÙˆØ¬ÙˆØ¯ Ù†Ø¯Ø§Ø±Ø¯.",
        "The update package was not found in the latest release.": "Ø¨Ø³ØªÙ‡ Ø¨Ù‡â€ŒØ±ÙˆØ²Ø±Ø³Ø§Ù†ÛŒ Ù¾ÛŒØ¯Ø§ Ù†Ø´Ø¯.",
        "The update could not be completed.": "Ø¨Ù‡â€ŒØ±ÙˆØ²Ø±Ø³Ø§Ù†ÛŒ Ø§Ù†Ø¬Ø§Ù… Ù†Ø´Ø¯.",
        "The update check timed out. Please try again.": "Ù…Ù‡Ù„Øª Ø¨Ø±Ø±Ø³ÛŒ Ù†Ø³Ø®Ù‡ Ø¬Ø¯ÛŒØ¯ Ø¨Ù‡ Ù¾Ø§ÛŒØ§Ù† Ø±Ø³ÛŒØ¯. Ù„Ø·ÙØ§Ù‹ Ø¯ÙˆØ¨Ø§Ø±Ù‡ ØªÙ„Ø§Ø´ Ú©Ù†ÛŒØ¯.",
        "Update installed successfully. Please restart Enigma2.": "Ø¨Ù‡â€ŒØ±ÙˆØ²Ø±Ø³Ø§Ù†ÛŒ Ø¨Ø§ Ù…ÙˆÙÙ‚ÛŒØª Ù†ØµØ¨ Ø´Ø¯. Ù„Ø·ÙØ§Ù‹ Enigma2 Ø±Ø§ Ø±Ø§Ù‡â€ŒØ§Ù†Ø¯Ø§Ø²ÛŒ Ù…Ø¬Ø¯Ø¯ Ú©Ù†ÛŒØ¯.",
        "Settings": "ØªÙ†Ø¸ÛŒÙ…Ø§Øª",
        "Download Picons": "Ø¯Ø§Ù†Ù„ÙˆØ¯ Ù¾ÛŒÚ©ÙˆÙ†â€ŒÙ‡Ø§",
        "Language": "Ø²Ø¨Ø§Ù†",
        "About": "Ø¯Ø±Ø¨Ø§Ø±Ù‡",
        "Latest Updates": "Ø§Ø®Ø¨Ø§Ø± Ø¨Ù‡â€ŒØ±ÙˆØ²Ø±Ø³Ø§Ù†ÛŒâ€ŒÙ‡Ø§",
        "Loading latest updates...": "Ø¯Ø± Ø­Ø§Ù„ Ø¯Ø±ÛŒØ§ÙØª Ø§Ø®Ø¨Ø§Ø± Ø¨Ù‡â€ŒØ±ÙˆØ²Ø±Ø³Ø§Ù†ÛŒâ€ŒÙ‡Ø§...",
        "Latest updates loaded.": "Ø¢Ø®Ø±ÛŒÙ† Ø§Ø®Ø¨Ø§Ø± Ø¨Ù‡â€ŒØ±ÙˆØ²Ø±Ø³Ø§Ù†ÛŒ Ø¯Ø±ÛŒØ§ÙØª Ø´Ø¯.",
        "Updates cannot be checked right now.": "Ø¯Ø± Ø­Ø§Ù„ Ø­Ø§Ø¶Ø± Ø§Ù…Ú©Ø§Ù† Ø¨Ø±Ø±Ø³ÛŒ ÙˆØ¬ÙˆØ¯ Ù†Ø¯Ø§Ø±Ø¯.",
        "GREEN": "Ø³Ø¨Ø²",
        "OK: Select     EXIT: Close": "OK: Ø§Ù†ØªØ®Ø§Ø¨     EXIT: Ø¨Ø³ØªÙ†",
        "Choose language": "Ø§Ù†ØªØ®Ø§Ø¨ Ø²Ø¨Ø§Ù†",
        "OK: Select     EXIT: Back": "OK: Ø§Ù†ØªØ®Ø§Ø¨     EXIT: Ø¨Ø§Ø²Ú¯Ø´Øª",
        "Choose the destination for downloaded picons": "Ù…Ø³ÛŒØ± Ø°Ø®ÛŒØ±Ù‡ Ù¾ÛŒÚ©ÙˆÙ†â€ŒÙ‡Ø§ÛŒ Ø¯Ø§Ù†Ù„ÙˆØ¯Ø´Ø¯Ù‡ Ø±Ø§ Ø§Ù†ØªØ®Ø§Ø¨ Ú©Ù†ÛŒØ¯",
        "Custom path": "Ù…Ø³ÛŒØ± Ø¯Ù„Ø®ÙˆØ§Ù‡",
        "OK: Select     BLUE: Edit custom path     ": "OK: Ø§Ù†ØªØ®Ø§Ø¨     BLUE: ÙˆÛŒØ±Ø§ÛŒØ´ Ù…Ø³ÛŒØ± Ø¯Ù„Ø®ÙˆØ§Ù‡     ",
        ": Save": ": Ø°Ø®ÛŒØ±Ù‡",
        "Enter picon destination path": "Ù…Ø³ÛŒØ± Ø°Ø®ÛŒØ±Ù‡ Ù¾ÛŒÚ©ÙˆÙ† Ø±Ø§ ÙˆØ§Ø±Ø¯ Ú©Ù†ÛŒØ¯",
        "The path must start with /": "Ù…Ø³ÛŒØ± Ø¨Ø§ÛŒØ¯ Ø¨Ø§ / Ø´Ø±ÙˆØ¹ Ø´ÙˆØ¯",
        "Picon destination saved:\n%s": "Ù…Ø³ÛŒØ± Ù¾ÛŒÚ©ÙˆÙ† Ø°Ø®ÛŒØ±Ù‡ Ø´Ø¯:\n%s",
        "Internet": "Ø§ÛŒÙ†ØªØ±Ù†Øª",
        "Checking...": "Ø¯Ø± Ø­Ø§Ù„ Ø¨Ø±Ø±Ø³ÛŒ...",
        "Destination: %s": "Ù…Ø³ÛŒØ±: %s",
        "Checking download servers...": "Ø¯Ø± Ø­Ø§Ù„ Ø¨Ø±Ø±Ø³ÛŒ Ø³Ø±ÙˆØ±Ù‡Ø§ÛŒ Ø¯Ø§Ù†Ù„ÙˆØ¯...",
        "OK: Select/Unselect     ": "OK: Ø§Ù†ØªØ®Ø§Ø¨/Ù„ØºÙˆ Ø§Ù†ØªØ®Ø§Ø¨     ",
        ": Download": "Download :",
        "EXIT: Back": "EXIT: Ø¨Ø§Ø²Ú¯Ø´Øª",
        "Online": "Ø¢Ù†Ù„Ø§ÛŒÙ†",
        "Backup server": "Ø³Ø±ÙˆØ± Ù¾Ø´ØªÛŒØ¨Ø§Ù†",
        "Offline": "Ø¢ÙÙ„Ø§ÛŒÙ†",
        "Connected to the main server": "Ø§ØªØµØ§Ù„ Ø¨Ù‡ Ø³Ø±ÙˆØ± Ø§ØµÙ„ÛŒ Ø¨Ø±Ù‚Ø±Ø§Ø± Ø§Ø³Øª",
        "Main server is unavailable; backup server is ready": "Ø³Ø±ÙˆØ± Ø§ØµÙ„ÛŒ Ø¯Ø± Ø¯Ø³ØªØ±Ø³ Ù†ÛŒØ³ØªØ› Ø³Ø±ÙˆØ± Ù¾Ø´ØªÛŒØ¨Ø§Ù† Ø¢Ù…Ø§Ø¯Ù‡ Ø§Ø³Øª",
        "Neither download server is available": "Ù‡ÛŒÚ†â€ŒÛŒÚ© Ø§Ø² Ø³Ø±ÙˆØ±Ù‡Ø§ÛŒ Ø¯Ø§Ù†Ù„ÙˆØ¯ Ø¯Ø± Ø¯Ø³ØªØ±Ø³ Ù†ÛŒØ³Øª",
        "Downloading is unavailable because no download server is reachable.": "Ù‡ÛŒÚ† Ø³Ø±ÙˆØ± Ø¯Ø§Ù†Ù„ÙˆØ¯ÛŒ Ø¯Ø± Ø¯Ø³ØªØ±Ø³ Ù†ÛŒØ³ØªØ› Ø§Ù…Ú©Ø§Ù† Ø¯Ø§Ù†Ù„ÙˆØ¯ ÙˆØ¬ÙˆØ¯ Ù†Ø¯Ø§Ø±Ø¯.",
        "Selected: %s": "Ø§Ù†ØªØ®Ø§Ø¨ Ø´Ø¯: %s",
        "The download catalog is incomplete. Please reopen this screen.": "ÙÙ‡Ø±Ø³Øª Ø¯Ø§Ù†Ù„ÙˆØ¯ Ù†Ø§Ù‚Øµ Ø§Ø³Øª. Ø§ÛŒÙ† ØµÙØ­Ù‡ Ø±Ø§ Ø¨Ø¨Ù†Ø¯ÛŒØ¯ Ùˆ Ø¯ÙˆØ¨Ø§Ø±Ù‡ Ø¨Ø§Ø² Ú©Ù†ÛŒØ¯.",
        "Select at least one satellite first.": "Ø§Ø¨ØªØ¯Ø§ Ø­Ø¯Ø§Ù‚Ù„ ÛŒÚ© Ù…Ø§Ù‡ÙˆØ§Ø±Ù‡ Ø±Ø§ Ø§Ù†ØªØ®Ø§Ø¨ Ú©Ù†ÛŒØ¯.",
        "A tar.gz extraction tool is not available on this receiver.": "Ø§Ø¨Ø²Ø§Ø± Ø§Ø³ØªØ®Ø±Ø§Ø¬ tar.gz Ø±ÙˆÛŒ Ø§ÛŒÙ† Ø±Ø³ÛŒÙˆØ± Ù…ÙˆØ¬ÙˆØ¯ Ù†ÛŒØ³Øª.",
        "Downloading selected picons...": "Ø¯Ø± Ø­Ø§Ù„ Ø¯Ø§Ù†Ù„ÙˆØ¯ Ù¾ÛŒÚ©ÙˆÙ†â€ŒÙ‡Ø§ÛŒ Ø§Ù†ØªØ®Ø§Ø¨â€ŒØ´Ø¯Ù‡...",
        "Downloading: %d%% (%d/%d)": "Ø¯Ø± Ø­Ø§Ù„ Ø¯Ø§Ù†Ù„ÙˆØ¯: %d%% (%d/%d)",
        "Download completed: %d PNG files": "Ø¯Ø§Ù†Ù„ÙˆØ¯ Ú©Ø§Ù…Ù„ Ø´Ø¯: %d ÙØ§ÛŒÙ„ PNG",
        "Download finished.\n%d files were copied to:\n%s": "Ø¯Ø§Ù†Ù„ÙˆØ¯ ØªÙ…Ø§Ù… Ø´Ø¯.\n%d ÙØ§ÛŒÙ„ Ø¯Ø± Ù…Ø³ÛŒØ± Ø²ÛŒØ± Ú©Ù¾ÛŒ Ø´Ø¯:\n%s",
        "Download failed": "Ø¯Ø§Ù†Ù„ÙˆØ¯ Ù†Ø§Ù…ÙˆÙÙ‚ Ø¨ÙˆØ¯",
        "The picons could not be downloaded or verified. Please try again.": "Ø¯Ø§Ù†Ù„ÙˆØ¯ ÛŒØ§ Ø§Ø¹ØªØ¨Ø§Ø±Ø³Ù†Ø¬ÛŒ Ù¾ÛŒÚ©ÙˆÙ†â€ŒÙ‡Ø§ Ø§Ù†Ø¬Ø§Ù… Ù†Ø´Ø¯. Ù„Ø·ÙØ§Ù‹ Ø¯ÙˆØ¨Ø§Ø±Ù‡ ØªÙ„Ø§Ø´ Ú©Ù†ÛŒØ¯.",
        "Download Picons": "Ø¯Ø§Ù†Ù„ÙˆØ¯ Ù¾ÛŒÚ©ÙˆÙ†â€ŒÙ‡Ø§",
        "Version: %s": "Ù†Ø³Ø®Ù‡: %s",
        "EXIT: Close": "EXIT: Ø¨Ø³ØªÙ†",
    },
    "ar": {
        "Update": "ØªØ­Ø¯ÙŠØ«",
        "Current version: %s": "Ø§Ù„Ø¥ØµØ¯Ø§Ø± Ø§Ù„Ù…Ø«Ø¨Øª: %s",
        "Latest version: %s": "Ø£Ø­Ø¯Ø« Ø¥ØµØ¯Ø§Ø±: %s",
        "Checking for the latest version...": "Ø¬Ø§Ø±Ù Ø§Ù„ØªØ­Ù‚Ù‚ Ù…Ù† Ø£Ø­Ø¯Ø« Ø¥ØµØ¯Ø§Ø±...",
        "Downloading update: %d%%": "Ø¬Ø§Ø±Ù ØªÙ†Ø²ÙŠÙ„ Ø§Ù„ØªØ­Ø¯ÙŠØ«: %d%%",
        "Installing update...": "Ø¬Ø§Ø±Ù ØªØ«Ø¨ÙŠØª Ø§Ù„ØªØ­Ø¯ÙŠØ«...",
        "No new version is available.": "Ù„Ø§ ÙŠÙˆØ¬Ø¯ Ø¥ØµØ¯Ø§Ø± Ø¬Ø¯ÙŠØ¯ Ù„Ù„ØªØ«Ø¨ÙŠØª.",
        "The update package was not found in the latest release.": "Ù„Ù… ÙŠØªÙ… Ø§Ù„Ø¹Ø«ÙˆØ± Ø¹Ù„Ù‰ Ø­Ø²Ù…Ø© Ø§Ù„ØªØ­Ø¯ÙŠØ« ÙÙŠ Ø£Ø­Ø¯Ø« Ø¥ØµØ¯Ø§Ø±.",
        "The update could not be completed.": "ØªØ¹Ø°Ø± Ø¥ÙƒÙ…Ø§Ù„ Ø§Ù„ØªØ­Ø¯ÙŠØ«.",
        "The update check timed out. Please try again.": "Ø§Ù†ØªÙ‡Øª Ù…Ù‡Ù„Ø© Ø§Ù„ØªØ­Ù‚Ù‚ Ù…Ù† Ø§Ù„ØªØ­Ø¯ÙŠØ«. ÙŠØ±Ø¬Ù‰ Ø§Ù„Ù…Ø­Ø§ÙˆÙ„Ø© Ù…Ø±Ø© Ø£Ø®Ø±Ù‰.",
        "Update installed successfully. Please restart Enigma2.": "ØªÙ… ØªØ«Ø¨ÙŠØª Ø§Ù„ØªØ­Ø¯ÙŠØ« Ø¨Ù†Ø¬Ø§Ø­. ÙŠØ±Ø¬Ù‰ Ø¥Ø¹Ø§Ø¯Ø© ØªØ´ØºÙŠÙ„ Enigma2.",
        "Settings": "Ø§Ù„Ø¥Ø¹Ø¯Ø§Ø¯Ø§Øª",
        "Download Picons": "ØªÙ†Ø²ÙŠÙ„ Ø§Ù„Ø¨ÙŠÙƒÙˆÙ†Ø§Øª",
        "Language": "Ø§Ù„Ù„ØºØ©",
        "About": "Ø­ÙˆÙ„",
        "Latest Updates": "Ø¢Ø®Ø± Ø£Ø®Ø¨Ø§Ø± Ø§Ù„ØªØ­Ø¯ÙŠØ«Ø§Øª",
        "Loading latest updates...": "Ø¬Ø§Ø±Ù ØªØ­Ù…ÙŠÙ„ Ø¢Ø®Ø± Ø£Ø®Ø¨Ø§Ø± Ø§Ù„ØªØ­Ø¯ÙŠØ«Ø§Øª...",
        "Latest updates loaded.": "ØªÙ… ØªØ­Ù…ÙŠÙ„ Ø¢Ø®Ø± Ø£Ø®Ø¨Ø§Ø± Ø§Ù„ØªØ­Ø¯ÙŠØ«Ø§Øª.",
        "Updates cannot be checked right now.": "Ù„Ø§ ÙŠÙ…ÙƒÙ† Ø§Ù„ØªØ­Ù‚Ù‚ Ù…Ù† Ø§Ù„ØªØ­Ø¯ÙŠØ«Ø§Øª Ø­Ø§Ù„ÙŠØ§Ù‹.",
        "GREEN": "Ø£Ø®Ø¶Ø±",
        "OK: Select     EXIT: Close": "OK: Ø§Ø®ØªÙŠØ§Ø±     EXIT: Ø¥ØºÙ„Ø§Ù‚",
        "Choose language": "Ø§Ø®ØªØ± Ø§Ù„Ù„ØºØ©",
        "OK: Select     EXIT: Back": "OK: Ø§Ø®ØªÙŠØ§Ø±     EXIT: Ø±Ø¬ÙˆØ¹",
        "Choose the destination for downloaded picons": "Ø§Ø®ØªØ± Ù…Ø³Ø§Ø± Ø­ÙØ¸ Ø§Ù„Ø¨ÙŠÙƒÙˆÙ†Ø§Øª Ø§Ù„ØªÙŠ ØªÙ… ØªÙ†Ø²ÙŠÙ„Ù‡Ø§",
        "Custom path": "Ù…Ø³Ø§Ø± Ù…Ø®ØµØµ",
        "OK: Select     BLUE: Edit custom path     ": "OK: Ø§Ø®ØªÙŠØ§Ø±     BLUE: ØªØ¹Ø¯ÙŠÙ„ Ø§Ù„Ù…Ø³Ø§Ø±     ",
        ": Save": ": Ø­ÙØ¸",
        "Enter picon destination path": "Ø£Ø¯Ø®Ù„ Ù…Ø³Ø§Ø± Ø­ÙØ¸ Ø§Ù„Ø¨ÙŠÙƒÙˆÙ†Ø§Øª",
        "The path must start with /": "ÙŠØ¬Ø¨ Ø£Ù† ÙŠØ¨Ø¯Ø£ Ø§Ù„Ù…Ø³Ø§Ø± Ø¨Ù€ /",
        "Picon destination saved:\n%s": "ØªÙ… Ø­ÙØ¸ Ù…Ø³Ø§Ø± Ø§Ù„Ø¨ÙŠÙƒÙˆÙ†Ø§Øª:\n%s",
        "Internet": "Ø§Ù„Ø¥Ù†ØªØ±Ù†Øª",
        "Checking...": "Ø¬Ø§Ø±Ù Ø§Ù„ØªØ­Ù‚Ù‚...",
        "Destination: %s": "Ø§Ù„Ù…Ø³Ø§Ø±: %s",
        "Checking download servers...": "Ø¬Ø§Ø±Ù Ø§Ù„ØªØ­Ù‚Ù‚ Ù…Ù† Ø®ÙˆØ§Ø¯Ù… Ø§Ù„ØªÙ†Ø²ÙŠÙ„...",
        "OK: Select/Unselect     ": "OK: Ø§Ø®ØªÙŠØ§Ø±/Ø¥Ù„ØºØ§Ø¡     ",
        ": Download": ": Download",
        "EXIT: Back": "EXIT: Ø±Ø¬ÙˆØ¹",
        "Online": "Ù…ØªØµÙ„",
        "Backup server": "Ø®Ø§Ø¯Ù… Ø§Ø­ØªÙŠØ§Ø·ÙŠ",
        "Offline": "ØºÙŠØ± Ù…ØªØµÙ„",
        "Connected to the main server": "Ù…ØªØµÙ„ Ø¨Ø§Ù„Ø®Ø§Ø¯Ù… Ø§Ù„Ø±Ø¦ÙŠØ³ÙŠ",
        "Main server is unavailable; backup server is ready": "Ø§Ù„Ø®Ø§Ø¯Ù… Ø§Ù„Ø±Ø¦ÙŠØ³ÙŠ ØºÙŠØ± Ù…ØªØ§Ø­Ø› Ø§Ù„Ø®Ø§Ø¯Ù… Ø§Ù„Ø§Ø­ØªÙŠØ§Ø·ÙŠ Ø¬Ø§Ù‡Ø².",
        "Neither download server is available": "Ù„Ø§ ÙŠØªÙˆÙØ± Ø£ÙŠ Ø®Ø§Ø¯Ù… ØªÙ†Ø²ÙŠÙ„",
        "Downloading is unavailable because no download server is reachable.": "Ù„Ø§ ÙŠÙ…ÙƒÙ† Ø§Ù„ØªÙ†Ø²ÙŠÙ„ Ù„Ø£Ù† Ø®ÙˆØ§Ø¯Ù… Ø§Ù„ØªÙ†Ø²ÙŠÙ„ ØºÙŠØ± Ù…ØªØ§Ø­Ø©.",
        "Selected: %s": "ØªÙ… Ø§Ù„Ø§Ø®ØªÙŠØ§Ø±: %s",
        "The download catalog is incomplete. Please reopen this screen.": "Ù‚Ø§Ø¦Ù…Ø© Ø§Ù„ØªÙ†Ø²ÙŠÙ„ ØºÙŠØ± Ù…ÙƒØªÙ…Ù„Ø©. Ø£ØºÙ„Ù‚ Ù‡Ø°Ù‡ Ø§Ù„Ø´Ø§Ø´Ø© ÙˆØ§ÙØªØ­Ù‡Ø§ Ù…Ø¬Ø¯Ø¯Ø§Ù‹.",
        "Select at least one satellite first.": "Ø§Ø®ØªØ± Ù‚Ù…Ø±Ø§Ù‹ ØµÙ†Ø§Ø¹ÙŠØ§Ù‹ ÙˆØ§Ø­Ø¯Ø§Ù‹ Ø¹Ù„Ù‰ Ø§Ù„Ø£Ù‚Ù„ Ø£ÙˆÙ„Ø§Ù‹.",
        "A tar.gz extraction tool is not available on this receiver.": "Ø£Ø¯Ø§Ø© Ø§Ø³ØªØ®Ø±Ø§Ø¬ tar.gz ØºÙŠØ± Ù…ØªÙˆÙØ±Ø© Ø¹Ù„Ù‰ Ù‡Ø°Ø§ Ø§Ù„Ø¬Ù‡Ø§Ø².",
        "Downloading selected picons...": "Ø¬Ø§Ø±Ù ØªÙ†Ø²ÙŠÙ„ Ø§Ù„Ø¨ÙŠÙƒÙˆÙ†Ø§Øª Ø§Ù„Ù…Ø­Ø¯Ø¯Ø©...",
        "Downloading: %d%% (%d/%d)": "Ø¬Ø§Ø±Ù Ø§Ù„ØªÙ†Ø²ÙŠÙ„: %d%% (%d/%d)",
        "Download completed: %d PNG files": "Ø§ÙƒØªÙ…Ù„ Ø§Ù„ØªÙ†Ø²ÙŠÙ„: %d Ù…Ù„Ù PNG",
        "Download finished.\n%d files were copied to:\n%s": "Ø§ÙƒØªÙ…Ù„ Ø§Ù„ØªÙ†Ø²ÙŠÙ„.\nØªÙ… Ù†Ø³Ø® %d Ù…Ù„Ù Ø¥Ù„Ù‰:\n%s",
        "Download failed": "ÙØ´Ù„ Ø§Ù„ØªÙ†Ø²ÙŠÙ„",
        "The picons could not be downloaded or verified. Please try again.": "ØªØ¹Ø°Ø± ØªÙ†Ø²ÙŠÙ„ Ø§Ù„Ø£ÙŠÙ‚ÙˆÙ†Ø§Øª Ø£Ùˆ Ø§Ù„ØªØ­Ù‚Ù‚ Ù…Ù†Ù‡Ø§. ÙŠØ±Ø¬Ù‰ Ø§Ù„Ù…Ø­Ø§ÙˆÙ„Ø© Ù…Ø±Ø© Ø£Ø®Ø±Ù‰.",
        "Download Picons": "ØªÙ†Ø²ÙŠÙ„ Ø§Ù„Ø£ÙŠÙ‚ÙˆÙ†Ø§Øª",
        "Version: %s": "Ø§Ù„Ø¥ØµØ¯Ø§Ø±: %s",
        "EXIT: Close": "EXIT: Ø¥ØºÙ„Ø§Ù‚",
    },
}


def tr(message):
    language = config.plugins.onlinepicons.language.value
    return TRANSLATIONS.get(language, {}).get(message, message)


# title, archive stem. Every entry has a matching tar.gz archive in index.json.
SATELLITES = [
    ("220x132-15Â°W (Telstar 12)", "15w"),
    ("220x132-8Â°W (Eutelsat 8W)", "8w"),
    ("220x132-7Â°W (Nilesat 201/301/7W)", "7w"),
    ("220x132-5Â°W (Eutelsat 5 West B)", "5w"),
    ("220x132-4Â°W (Dror 1)", "4w"),
    ("220x132-0.8Â°W (Thor 5/6/7/Intelsat 10-02)", "0.8w"),
    ("220x132-1.9Â°E (BulgariaSat 1)", "1.9e"),
    ("220x132-3Â°E (Eutelsat 3B)", "3e"),
    ("220x132-4.8Â°E (Astra 4A/SES 5)", "4.8e"),
    ("220x132-7Â°E (Eutelsat 7B/7C)", "7e"),
    ("220x132-9Â°E (Eutelsat 9B)", "9e"),
    ("220x132-10.0Â°E (Eutelsat 10B)", "10e"),  
    ("220x132-13.0Â°E (Hotbird 13F/13G)", "13e"),
    ("220x132-16.0Â°E (Eutelsat 16A)", "16e"),
    ("220x132-19.2Â°E (Astra 1N/1P)", "19.2e"),
    ("220x132-21.5Â°E (Eutelsat 21B)", "21.5e"),
    ("220x132-23.5Â°E (Astra 3C)", "23.5e"),
    ("220x132-26.0Â°E (Badr 7/8-Es'hail 2)", "26e"),
    ("220x132-30.5Â°E (ArabSat 5A/6A)", "30.5e"),
    ("220x132-33.0Â°E (Eutelsat 33F)", "33e"),
    ("220x132-39.0Â°E (Hellas Sat 3/4)", "39e"),
    ("220x132-40.0Â°E (Express AM7)", "40e"),
    ("220x132-42.0Â°E (Turksat 3A/4A/5B/6A)", "42e"),
    ("220x132-45.0Â°E (Azerspace 2/Intelsat 38)", "45e"),
    ("220x132-46.0Â°E (Azerspace 1)", "46e"),
    ("220x132-52.0Â°E (TÃ¼rkmenÃ„lem/MonacoSat)", "52e"),
    ("220x132-52.5Â°E (Al Yah 1)", "52.5e"),
    ("220x132-53.0Â°E (Express AM6)", "53e"),
    ("220x132-56.0Â°E (Express AT2)", "56e"),
    ("220x132-57.0Â°E (NSS 12)", "57e"),
    ("220x132-62.0Â°E (Intelsat 39)", "62e"),
    ("220x132-68.5Â°E (Intelsat 20/36)", "68.5e"),
    ("220x132-70.5Â°E (Eutelsat 70B)", "70.5e"),
    ("220x132-75.0Â°E (ABS 2/2A)", "75e"),
    ("220x132-78.5Â°E (Thaicom 6/8)", "78.5e"),
    ("220x132-80.0Â°E (Express 80)", "80e"),
    ("220x132-97.5Â°E (G-Sat 9)", "97.5e"),
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
    <screen name="OnlinePiconsMain" position="center,center" size="900,650"
            title="Online Picons">
        <widget name="title" position="45,30" size="810,55"
                font="Regular;38" halign="center" />
        <widget name="menu" position="65,115" size="715,390"
                scrollbarMode="showNever" />
        <widget name="hint" position="45,565" size="810,38"
                font="Regular;22" halign="center" foregroundColor="#aaaaaa" />
    </screen>
    """

    def __init__(self, session):
        try:
            ensure_assets()
        except Exception:
            pass
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
            self._menu_entry(tr("Latest Updates"), "rss.png"),
            self._menu_entry(tr("About"), "about.png"),
        ])
        _set_text(self["hint"], tr("OK: Select     EXIT: Close"))

    def _menu_entry(self, text, icon):
        icon_path = asset_path(icon) if icon == "rss.png" else os.path.join(
            PLUGIN_PATH, icon
        )
        return [
            _menu_text(text),
            MultiContentEntryPixmapAlphaTest(
                pos=(8, 8),
                size=(48, 48),
                png=LoadPixmap(
                    cached=True,
                    path=icon_path,
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
        elif index == 4:
            self.session.open(LatestUpdatesScreen)
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

    LANGUAGES = [("en", "English"), ("fa", "ÙØ§Ø±Ø³ÛŒ"), ("ar", "Ø§Ù„Ø¹Ø±Ø¨ÙŠØ©")]

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
        _set_text(self["heading"], tr("Choose language"))
        _set_text(self["hint"], tr("OK: Select     EXIT: Back"))
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
        <widget name="greenKey" position="710,648" size="60,30"
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
        _set_text(self["custom"], "  %s" % self.paths[2])

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
        <widget name="greenKey" position="682,648" size="60,30"
                font="Regular;22" halign="center" foregroundColor="#00ff00" />
        <widget name="downloadKey" position="580,648" size="160,30"
                font="Regular;22" halign="left" />
        <widget name="exitKey" position="815,648" size="180,30"
                font="Regular;22" halign="left" />
    </screen>
    """

    def __init__(self, session):
        try:
            ensure_assets()
        except Exception:
            pass
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
        self.onShown.append(self._screen_shown)
        self.refresh_list()
        self._run_background("catalog", self._check_download_servers)

    def _screen_shown(self):
        self._resize_connection_label()
        colors = {
            "primary": "green",
            "fallback": "yellow",
            "offline": "red",
        }
        self._set_connection_dot(colors.get(self.connectivity, "checking"))

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
            _set_text(self["status"], 
                tr("Connected to the main server")
            )
        elif state == "fallback":
            self._set_connection_text(tr("Backup server"))
            self._set_connection_dot("yellow")
            _set_text(self["status"], 
                tr("Main server is unavailable; backup server is ready")
            )
        else:
            self._set_connection_text(tr("Offline"))
            self._set_connection_dot("red")
            _set_text(self["status"], tr("Neither download server is available"))

    def _set_connection_text(self, text):
        _set_text(self["connection"], text)
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
        path = asset_path("dot-%s.png" % color)
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
                        path=asset_path("check.png"),
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
            _set_text(self["status"], tr("Selected: %s") % title)
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
        _set_text(self["status"], tr("Downloading selected picons..."))
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
        _set_text(self["status"], 
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
            _set_text(self["status"], 
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
            _set_text(self["status"], tr("Download failed"))
            self.session.open(
                MessageBox,
                tr("The picons could not be downloaded or verified. Please try again."),
                MessageBox.TYPE_ERROR,
                timeout=8,
            )


class LatestUpdatesScreen(Screen):
    skin = """
    <screen name="LatestUpdatesScreen" position="center,center" size="900,620"
            title="Latest Updates">
        <widget name="heading" position="40,25" size="820,50"
                font="Regular;34" halign="center" />
        <widget name="updates" position="70,100" size="760,390"
                scrollbarMode="showOnDemand" />
        <widget name="status" position="55,510" size="790,42"
                font="Regular;23" halign="center" />
        <widget name="hint" position="55,565" size="790,32"
                font="Regular;21" halign="center" foregroundColor="#aaaaaa" />
    </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.setTitle(tr("Latest Updates"))
        self["heading"] = Label(tr("Latest Updates"))
        self["updates"] = MenuList(
            [], enableWrapAround=True, content=eListboxPythonMultiContent
        )
        self["updates"].l.setFont(0, gFont("Regular", 30))
        self["updates"].l.setItemHeight(40)
        self["status"] = Label(tr("Loading latest updates..."))
        self["hint"] = Label(tr("EXIT: Back"))
        self["actions"] = ActionMap(
            ["OkCancelActions"], {"ok": self.close, "cancel": self.close}, -1
        )

        self.closed = False
        self.background_result = None
        self._timer_connections = []
        self.result_timer = eTimer()
        self._connect_timer(self.result_timer, self._poll_background)
        self.onShown.append(self._start_on_shown)
        self.onClose.append(self._cleanup)

    def _start_on_shown(self):
        try:
            self.onShown.remove(self._start_on_shown)
        except Exception:
            pass
        self._run_background(self._load_latest_updates)

    def _connect_timer(self, timer, callback):
        try:
            connection = timer.timeout.connect(callback)
            self._timer_connections.append(connection)
            return
        except Exception:
            pass
        timer.callback.append(callback)

    def _cleanup(self):
        self.closed = True
        try:
            self.result_timer.stop()
        except Exception:
            pass

    def _run_background(self, function):
        self.background_result = None
        self.result_timer.start(100, False)

        def worker():
            try:
                self.background_result = (True, function())
            except Exception as error:
                self.background_result = (False, str(error))

        thread = threading.Thread(target=worker)
        thread.daemon = True
        thread.start()

    def _poll_background(self):
        if self.closed:
            return
        result = self.background_result
        if result is None:
            return
        self.result_timer.stop()
        self.background_result = None
        success, payload = result
        if not success:
            message = tr("Updates cannot be checked right now.")
            _set_text(self["status"], message)
            self.session.open(MessageBox, message, MessageBox.TYPE_ERROR, timeout=5)
            return

        source_name, lines = payload
        rows = []
        for line in lines:
            rows.append([
                _menu_text(line),
                MultiContentEntryText(
                    pos=(12, 0), size=(730, 40), font=0,
                    flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                    text=_menu_text(line),
                ),
            ])
        self["updates"].setList(rows)
        _set_text(self["status"], tr("Latest updates loaded."))

    def _load_latest_updates(self):
        errors = []
        for source_name, base_url in PICONS_SOURCES:
            try:
                raw = _read_text(
                    _join_url(base_url, LATEST_UPDATES_FILENAME),
                    timeout=8,
                    max_bytes=32 * 1024,
                )
                lines = []
                for raw_line in raw.splitlines():
                    line = raw_line.strip()
                    if line:
                        lines.append(line)
                if not lines:
                    raise RuntimeError("Update news file is empty")
                return source_name, lines[:10]
            except Exception as error:
                errors.append("%s: %s" % (source_name, error))
        raise RuntimeError("; ".join(errors))


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
        self.background_result = None
        self.pending_progress = None
        self.pending_installing = False

        # Keep signal connection objects alive. Newer DreamOS images use
        # eTimer.timeout.connect(); discarding the returned object disconnects
        # the callback and leaves this screen at 0% forever.
        self._timer_connections = []
        self.result_timer = eTimer()
        self.check_timeout_timer = eTimer()
        self._connect_timer(self.result_timer, self._poll_background)
        self._connect_timer(self.check_timeout_timer, self._check_timed_out)

        # Start only after the screen is visible; this is more reliable than a
        # separate one-shot start timer across DreamOS/Enigma2 variants.
        self.onShown.append(self._start_on_shown)
        self.onClose.append(self._cleanup)

    def _start_on_shown(self):
        try:
            self.onShown.remove(self._start_on_shown)
        except Exception:
            pass
        self.start_update()

    def _connect_timer(self, timer, callback):
        try:
            connection = timer.timeout.connect(callback)
            self._timer_connections.append(connection)
            return
        except Exception:
            pass
        timer.callback.append(callback)

    def _cleanup(self):
        self.closed = True
        self.check_pending = False
        for timer in (self.result_timer, self.check_timeout_timer):
            try:
                timer.stop()
            except Exception:
                pass

    def start_update(self):
        if self.started or self.closed:
            return
        self.started = True
        self.check_pending = True
        self.check_timeout_timer.start(15000, True)
        self._run_background("check", self._check_latest)

    def _check_timed_out(self):
        if self.closed or not self.check_pending:
            return
        self.check_pending = False
        try:
            self.result_timer.stop()
        except Exception:
            pass
        self["progress"].setValue(0)
        _set_text(self["percent"], "--")
        message = tr("The update check timed out. Please try again.")
        _set_text(self["status"], message)
        self.session.open(MessageBox, message, MessageBox.TYPE_ERROR, timeout=8)

    def _run_background(self, kind, function, *args):
        self.background_result = None
        self.result_timer.start(100, False)

        def worker():
            try:
                result = function(*args)
                success = True
            except Exception as error:
                result = str(error)
                success = False
            # A single tuple assignment is safe here; the eTimer reads it from
            # the Enigma2 main thread and performs every UI update there.
            self.background_result = (kind, success, result)

        thread = threading.Thread(target=worker)
        thread.daemon = True
        thread.start()

    def _poll_background(self):
        if self.closed:
            return

        if self.pending_progress is not None:
            percent = self.pending_progress
            self.pending_progress = None
            self._show_progress(percent)

        if self.pending_installing:
            self.pending_installing = False
            self._show_installing()

        completed = self.background_result
        if completed is None:
            return

        self.result_timer.stop()
        self.background_result = None
        kind, success, result = completed
        self._background_finished(kind, success, result)

    def _check_latest(self):
        # Prefer the normal GitHub releases page. It redirects to the latest tag
        # and is often reachable even when api.github.com is blocked or slow.
        latest = None
        tag = None
        release_data = None
        errors = []

        try:
            response = _request(LATEST_RELEASE_PAGE, timeout=4)
            try:
                final_url = response.geturl()
            finally:
                response.close()
            match = re.search(r"/releases/tag/([^/?#]+)", final_url or "")
            if not match:
                raise RuntimeError("GitHub latest-release redirect has no tag")
            tag = match.group(1)
            latest = tag.lstrip("vV")
        except Exception as error:
            errors.append("release page: %s" % error)

        # Fall back to the GitHub API so assets and their sizes can still be
        # read when the API is available.
        if not latest:
            try:
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
            except Exception as error:
                release_data = None
                errors.append("release API: %s" % error)

        # Last fallback: read the version from the small source file on main.
        # The download URL is then built from the conventional v<version> tag.
        if not latest:
            try:
                version_source = _read_text(
                    LATEST_VERSION_FILE,
                    timeout=4,
                    max_bytes=16 * 1024,
                )
                match = re.search(
                    r'^PLUGIN_VERSION\s*=\s*["\x27]([^"\x27]+)["\x27]',
                    version_source,
                    re.M,
                )
                if not match:
                    raise RuntimeError("PLUGIN_VERSION was not found")
                latest = match.group(1)
                tag = "v" + latest
            except Exception as error:
                errors.append("version file: %s" % error)

        if not latest or not tag:
            raise RuntimeError(
                "Unable to determine the latest version (%s)"
                % "; ".join(errors)
            )

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

        if isinstance(release_data, dict):
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

        # The release-page and version-file methods do not return asset JSON.
        # Build the deterministic URL used by this repository's releases.
        if selected_asset is None:
            selected_asset = {
                "name": expected,
                "browser_download_url": (
                    "https://github.com/%s/releases/download/%s/%s"
                    % (REPOSITORY, tag, expected)
                ),
                "size": 0,
            }

        return latest, installer, extension, selected_asset

    def _background_finished(self, kind, success, result):
        if self.closed:
            return

        if kind == "check":
            if not self.check_pending:
                return
            self.check_pending = False
            try:
                self.check_timeout_timer.stop()
            except Exception:
                pass

        if not success:
            self["progress"].setValue(0)
            _set_text(self["percent"], "--")
            message = "%s\n%s" % (
                tr("The update could not be completed."),
                result,
            )
            _set_text(self["status"], message)
            self.session.open(
                MessageBox,
                message,
                MessageBox.TYPE_ERROR,
                timeout=10,
            )
            return

        if kind == "check":
            latest = result[0]
            _set_text(self["latest"], tr("Latest version: %s") % latest)
            if _version_tuple(latest) <= _version_tuple(PLUGIN_VERSION):
                self["progress"].setValue(100)
                _set_text(self["percent"], "100%")
                _set_text(self["status"], tr("No new version is available."))
                return
            if result[3] is None:
                message = tr("The update package was not found in the latest release.")
                _set_text(self["status"], message)
                self.session.open(
                    MessageBox,
                    message,
                    MessageBox.TYPE_ERROR,
                    timeout=8,
                )
                return
            _set_text(self["status"], tr("Downloading update: %d%%") % 0)
            self._run_background("install", self._download_and_install, result)
            return

        self["progress"].setValue(100)
        _set_text(self["percent"], "100%")
        message = tr("Update installed successfully. Please restart Enigma2.")
        _set_text(self["status"], message)
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
                        self.pending_progress = min(99, int(downloaded * 100 / total))
            finally:
                package.close()
        finally:
            response.close()

        self.pending_installing = True
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
        _set_text(self["percent"], "%d%%" % percent)
        _set_text(self["status"], tr("Downloading update: %d%%") % percent)

    def _show_installing(self):
        if self.closed:
            return
        self["progress"].setValue(100)
        _set_text(self["percent"], "100%")
        _set_text(self["status"], tr("Installing update..."))


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
