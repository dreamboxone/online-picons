# Online Picons for DreamOS

پلاگین **Online Picons** برای دانلود و نصب پیکون‌های PNG با اندازه
`220x132` روی گیرنده‌های Enigma2 دارای سیستم‌عامل DreamOS ساخته شده است.

## امکانات

- دانلود پیکون ماهواره‌های مختلف از GitHub
- انتخاب هم‌زمان چند ماهواره
- نمایش `X` سبز کنار ماهواره انتخاب‌شده
- نمایش تیک سبز پس از دانلود و استخراج موفق
- انتخاب محل ذخیره پیکون‌ها روی HDD، USB یا مسیر دلخواه
- بررسی اتصال گیرنده به Google و GitHub با دستور Ping
- نمایش پیام فارسی در صورت نبودن فایل یا بروز خطا
- پشتیبانی از فایل‌های فشرده RAR

## وضعیت اتصال

در صفحه **Download Picons** وضعیت اتصال با یک دایره رنگی نمایش داده می‌شود:

- سبز: اتصال به Google و GitHub برقرار است.
- زرد: اینترنت برقرار است، اما GitHub در دسترس نیست.
- قرمز: اتصال اینترنت برقرار نیست.

## نصب آنلاین

با Telnet یا SSH وارد گیرنده شوید و دستور زیر را اجرا کنید:

```sh
wget -qO- https://raw.githubusercontent.com/dreamboxone/online-picons/main/install.sh | sh
```

همچنین می‌توانید فایل DEB را مستقیماً دانلود و نصب کنید:

```sh
wget -O /tmp/enigma2-plugin-extensions-online-picons.deb https://raw.githubusercontent.com/dreamboxone/online-picons/main/releases/enigma2-plugin-extensions-online-picons_1.0.12_all.deb && dpkg -i /tmp/enigma2-plugin-extensions-online-picons.deb
```

پس از نصب، Enigma2 را یک‌بار Restart کنید.

## نصب فایل DEB از پوشه `/tmp`

فایل زیر را با FTP یا FileZilla به پوشه `/tmp` گیرنده انتقال دهید:

`enigma2-plugin-extensions-online-picons_1.0.12_all.deb`

سپس با Telnet یا SSH دستور زیر را اجرا کنید:

```sh
dpkg -i /tmp/enigma2-plugin-extensions-online-picons_1.0.12_all.deb
```

پس از پایان نصب، Enigma2 را Restart کنید.

## نصب آنلاین فایل IPK

برای گیرنده‌های Enigma2 مبتنی بر `opkg`، با Telnet یا SSH دستورهای زیر را اجرا کنید:

```sh
wget -O /tmp/enigma2-plugin-extensions-online-picons.ipk https://github.com/dreamboxone/online-picons/releases/download/v1.0.12/enigma2-plugin-extensions-online-picons_1.0.12_all.ipk
opkg install /tmp/enigma2-plugin-extensions-online-picons.ipk
```

## نصب فایل IPK از پوشه `/tmp`

فایل زیر را با FTP یا FileZilla به پوشه `/tmp` گیرنده انتقال دهید:

`enigma2-plugin-extensions-online-picons_1.0.12_all.ipk`

سپس با Telnet یا SSH دستور زیر را اجرا کنید:

```sh
opkg install /tmp/enigma2-plugin-extensions-online-picons_1.0.12_all.ipk
```

اگر نسخه قبلی نصب است و نیاز به نصب مجدد دارید، از دستور زیر استفاده کنید:

```sh
opkg install --force-reinstall /tmp/enigma2-plugin-extensions-online-picons_1.0.12_all.ipk
```

پس از پایان نصب، Enigma2 را Restart کنید.

## روش استفاده

1. از منوی پلاگین‌ها وارد **Online Picons** شوید.
2. وارد **Settings** شوید و محل ذخیره پیکون‌ها را انتخاب کنید.
3. وارد **Download Picons** شوید و منتظر نمایش وضعیت اتصال بمانید.
4. روی نام ماهواره موردنظر دکمه OK را بزنید. کنار ماهواره انتخاب‌شده یک `X`
   سبز نمایش داده می‌شود.
5. برای انتخاب چند ماهواره، همین کار را روی ماهواره‌های دیگر تکرار کنید.
6. دکمه سبز کنترل را برای شروع دانلود بزنید.
7. پس از دانلود و استخراج موفق، کنار نام ماهواره تیک سبز نمایش داده می‌شود.

برای خارج‌کردن یک ماهواره از حالت انتخاب، دوباره روی نام آن دکمه OK را بزنید.

## درباره پلاگین

- نسخه: `1.0.12`
- YouTube: `@routekernel`
- GitHub: [dreamboxone/online-picons](https://github.com/dreamboxone/online-picons)
