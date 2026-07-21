# -*- coding: utf-8 -*-
from Screens.Screen import Screen
from Components.Label import Label
from Components.ProgressBar import ProgressBar
from Components.ActionMap import ActionMap
from Plugins.Plugin import PluginDescriptor
from enigma import eHttpDownloader
import os

class OnlinePiconsProgressScreen(Screen):
    skin = """
    <screen name="OnlinePiconsProgressScreen" position="center,center" size="700,220" title="Online Picons Downloader">
        <widget name="status" position="20,20" size="660,35" font="Regular;22" halign="center" valign="center" transparent="1" />
        <widget name="progress" position="50,75" size="600,25" borderWidth="1" borderColor="#ffffff" />
        <widget name="percentage" position="20,115" size="660,30" font="Regular;20" halign="center" valign="center" transparent="1" />
        <widget name="info" position="20,160" size="660,30" font="Regular;18" halign="center" valign="center" foregroundColor="#aaaaaa" transparent="1" />
    </screen>
    """

    def __init__(self, session, download_url, destination_path):
        Screen.__init__(self, session)
        self.session = session
        self.download_url = download_url
        self.destination_path = destination_path

        self["status"] = Label("در حال شروع دانلود...")
        self["percentage"] = Label("0%")
        self["info"] = Label("لطفاً شکیبا باشید...")
        self["progress"] = ProgressBar()
        self["progress"].setRange((0, 100))
        self["progress"].setValue(0)

        self["actions"] = ActionMap(["OkCancelActions"], {
            "cancel": self.cancelDownload,
            "ok": self.cancelDownload,
        }, -1)

        self.downloader = None
        self.onShown.append(self.startDownload)

    def startDownload(self):
        try:
            self.downloader = eHttpDownloader()
            self.downloader.progressChanged.get().append(self.onProgress)
            self.downloader.downloadFinished.get().append(self.onFinished)
            self.downloader.downloadFailed.get().append(self.onFailed)
            
            # Compatible string conversion for Py2 & Py3
            url = str(self.download_url) if isinstance(self.download_url, str) else self.download_url.encode('utf-8')
            dest = str(self.destination_path) if isinstance(self.destination_path, str) else self.destination_path.encode('utf-8')
            
            self.downloader.startSave(url, dest)
        except Exception as e:
            self["status"].setText("خطا در شروع دانلود: " + str(e))

    def onProgress(self, current_bytes, total_bytes):
        if total_bytes > 0:
            percent = int((float(current_bytes) / float(total_bytes)) * 100)
            self["progress"].setValue(percent)
            
            current_mb = current_bytes / (1024.0 * 1024.0)
            total_mb = total_bytes / (1024.0 * 1024.0)
            
            self["percentage"].setText("{0}%".format(percent))
            self["info"].setText("{0:.2f} MB / {1:.2f} MB".format(current_mb, total_mb))

    def onFinished(self):
        self["progress"].setValue(100)
        self["percentage"].setText("100%")
        self["status"].setText("دانلود با موفقیت انجام شد!")
        self["info"].setText("در حال استخراج فایل‌ها...")

    def onFailed(self, error_msg):
        self["status"].setText("دانلود ناموفق بود.")
        self["info"].setText("خطا: " + str(error_msg))

    def cancelDownload(self):
        if self.downloader:
            try:
                self.downloader.stop()
            except:
                pass
        self.close()
