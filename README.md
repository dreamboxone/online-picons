# Online Picons for DreamOS

Online Picons is an Enigma2 plugin for downloading 220x132 PNG picons from
[`dreamboxone/online-picons`](https://github.com/dreamboxone/online-picons).

پلاگین Online Picons برای دانلود و نصب پیکون‌های 220x132 روی گیرنده‌های
Enigma2 با سیستم‌عامل DreamOS ساخته شده است.

## Features

- DreamOS `.deb` package
- HDD, USB, or custom destination
- Google/GitHub connectivity indicator
- Multi-selection of satellite packages
- RAR extraction through `unrar`, `7z`, `7za`, `bsdtar`, or a RAR-capable
  `tar`
- Persian five-second messages when an archive is unavailable or the receiver
  is offline
- About page with `@routekernel`, version, and Gregorian/Persian build year

## Archive naming

Place RAR archives in the repository root. Use the orbital position without a
decimal point, followed by `e` or `w`, for example:

- `52e.rar`
- `192e.rar`
- `08w.rar`
- `1005e.rar`

One of the supported RAR extraction tools must be installed on the receiver.

## Build

```sh
python3 build_deb.py
```

The package is written to `dist/`.

## نصب آنلاین

دستور زیر را در ترمینال گیرنده اجرا کنید:

```sh
wget -qO- https://raw.githubusercontent.com/dreamboxone/online-picons/main/install.sh | sh
```

یا فایل DEB را مستقیماً دانلود و نصب کنید:

```sh
wget -O /tmp/enigma2-plugin-extensions-online-picons.deb https://raw.githubusercontent.com/dreamboxone/online-picons/main/releases/enigma2-plugin-extensions-online-picons_1.0.0_all.deb && dpkg -i /tmp/enigma2-plugin-extensions-online-picons.deb
```

پس از نصب، Enigma2 را یک‌بار Restart کنید.

## نصب لوکال از پوشه `/tmp`

فایل زیر را با FTP یا FileZilla به پوشه `/tmp` گیرنده انتقال دهید:

`enigma2-plugin-extensions-online-picons_1.0.0_all.deb`

سپس اجرا کنید:

```sh
dpkg -i /tmp/enigma2-plugin-extensions-online-picons_1.0.0_all.deb
```

در صورت نمایش خطای وابستگی:

```sh
apt-get -f install
```

سپس Enigma2 را Restart کنید.

## Notes

The plugin looks for `.rar` archives only. Picon archives are downloaded only
when selected and are not embedded in the plugin package.
