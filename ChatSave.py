# meta developer: @unkxe
# meta description: Экспорт истории чата в HTML-сайт с фото и видео, отправка в архив-топик
__version__ = (2, 0, 0)

import html as _html
import os
import re
import time
import zipfile

from .. import loader, utils

PALETTE = "#e17076 #7bc862 #e5ca77 #65aadd #a695e7 #ee7aae #faa774 #6ec9cb".split()

ACTIONS = {
    "MessageActionChatCreate": "💬 Чат создан",
    "MessageActionChannelCreate": "📣 Канал создан",
    "MessageActionChatEditTitle": "✏️ Название изменено",
    "MessageActionChatEditPhoto": "🖼 Фото изменено",
    "MessageActionChatDeletePhoto": "🖼 Фото удалено",
    "MessageActionChatAddUser": "➕ Участник добавлен",
    "MessageActionChatJoinedByLink": "🔗 Присоединился по ссылке",
    "MessageActionChatDeleteUser": "➖ Участник покинул чат",
    "MessageActionPinMessage": "📌 Сообщение закреплено",
    "MessageActionHistoryClear": "🧹 История очищена",
}

URL_RE = re.compile(r"(https?://[^\s<>\"']+)")

MAX_ZIP_BYTES = int(1.9 * 1024**3)
SITE_ROOT = os.path.expanduser("~/chatsave")

PAGE = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0e1621;color:#e7ebf0;font:15px/1.45 -apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:860px;margin:0 auto;padding:20px 12px 70px}
.head{display:flex;align-items:center;gap:13px;background:#17212b;border-radius:14px;padding:14px 18px;margin-bottom:18px;box-shadow:0 4px 18px rgba(0,0,0,.35)}
.ava{width:46px;height:46px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:18px;color:#fff;flex:none}
.t1{font-size:17px;font-weight:600}
.t2{font-size:13px;color:#708499;margin-top:3px}
.day{text-align:center;margin:20px 0 10px}
.day span{background:rgba(0,0,0,.25);font-size:12px;color:#c9d1d9;padding:5px 14px;border-radius:14px}
.svc{text-align:center;margin:10px 0}
.svc span{background:rgba(0,0,0,.2);font-size:12.5px;color:#9fb3c8;padding:4px 14px;border-radius:12px}
.m{display:flex;margin:3px 0;align-items:flex-end}
.m.out{justify-content:flex-end}
.b{max-width:72%;background:#182533;border-radius:14px;padding:7px 12px 6px;font-size:14.5px;box-shadow:0 1px 2px rgba(0,0,0,.25);overflow-wrap:break-word}
.m.out .b{background:#2b5278}
.g1 .b{border-bottom-left-radius:5px}
.m.out.g1 .b{border-bottom-left-radius:14px;border-bottom-right-radius:5px}
.nm{display:block;font-size:13.5px;font-weight:600;margin-bottom:2px}
.note{font-size:12px;color:#8fa5b9;margin:1px 0 3px}
.m.out .note{color:rgba(255,255,255,.6)}
.tx{white-space:pre-wrap}
.tx a{color:#5eb5f7}
.m.out .tx a{color:#d8e8ff}
.tm{float:right;margin:6px -3px -4px 12px;font-size:11.5px;color:#708499}
.m.out .tm{color:rgba(255,255,255,.6)}
.ext{color:#7cccff;font-size:13px}
.pm{display:block;max-width:320px;max-height:420px;border-radius:10px;margin:2px 0;cursor:pointer}
.vd{display:block;width:320px;max-width:100%;border-radius:10px;margin:2px 0}
.vn{width:200px;height:200px;border-radius:50%;object-fit:cover;margin:2px 0}
.mfail{display:inline-block;font-size:13px;color:#e17076;margin:2px 0}
.footer{text-align:center;color:#708499;font-size:12px;margin-top:30px}
</style>
</head>
<body>
<div class="wrap">
<div class="head">
<div class="ava" style="background:__C_AVA__">__INI__</div>
<div>
<div class="t1">__TITLE__</div>
<div class="t2">__INFO__</div>
</div>
</div>
__MESSAGES__
<div class="footer">🗂 ChatSave · __COUNT__ · выгружено __DATE__</div>
</div>
</body>
</html>
"""


def _esc(value):
    return _html.escape(str(value if value is not None else ""))


def _display_name(obj):
    if obj is None:
        return None
    fn = getattr(obj, "first_name", None)
    ln = getattr(obj, "last_name", None)
    name = " ".join(p for p in (fn, ln) if p) or getattr(obj, "title", None)
    return str(name).strip() or None


def _palette(name):
    return PALETTE[sum(map(ord, str(name))) % len(PALETTE)]


def _initials(name):
    parts = [p for p in str(name).split() if p]
    if not parts:
        return "?"
    return "".join(p[0] for p in parts[:2]).upper()


def _bar(percent):
    fill = max(0, min(10, round(percent / 10)))
    return "█" * fill + "░" * (10 - fill)


def _fmt_size(num):
    num = float(num)
    for unit in ("Б", "КиБ", "МиБ", "ГиБ"):
        if num < 1024 or unit == "ГиБ":
            return f"{num:.0f} {unit}" if unit in ("Б", "КиБ") else f"{num:.1f} {unit}"
        num /= 1024
    return f"{num:.1f} ТиБ"


@loader.tds
class ChatSave(loader.Module):
    """Сохраняет историю чата в HTML-сайт с фото и видео и отправляет архив в топик чата-архива"""

    strings = {"name": "ChatSave"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue("dest_chat", 3946198505, lambda: "ID чата-архива, куда падают выгрузки"),
            loader.ConfigValue("dest_topic", 6, lambda: "ID топика (темы) в чате-архиве"),
            loader.ConfigValue("default_limit", 0, lambda: "Сколько сообщений выгружать по умолчанию (0 — вся история)"),
        )

    async def client_ready(self, client, db):
        self._client = client
        self._cs_stop = False

    @loader.command()
    async def cs(self, message):
        """<cs [число] [nomedia]> — выгрузить чат в HTML-сайт; фото и видео скачиваются в архив"""
        tokens = (utils.get_args_raw(message) or "").strip().lower().split()
        limit = int(self.config["default_limit"] or 0)
        do_media = True
        for tok in tokens:
            if tok.isdigit():
                limit = max(1, int(tok))
            elif tok in ("nomedia", "nom", "бзмедиа"):
                do_media = False
            elif tok in ("all", "все", "всё"):
                limit = 0

        self._cs_stop = False

        base = message
        if message.is_reply:
            base = await message.get_reply_message()
        chat = await base.get_chat()
        if not chat:
            chat = await message.get_chat()
        chat_id = utils.get_chat_id(base)
        title = _display_name(chat) or f"Чат {chat_id}"

        total = 0
        try:
            many = await self._client.get_messages(chat, limit=0)
            total = getattr(many, "total", 0) or 0
        except Exception:
            total = 0

        form = await self._form(message, "Готовлю выгрузку…", 0, total)

        msgs = []
        seen = 0
        started = time.time()
        async for m in self._client.iter_messages(chat, limit=limit or None):
            if self._cs_stop:
                break
            msgs.append(m)
            seen += 1
            if form and seen % 50 == 0:
                await form.edit(rich_html=self._progress("Выгружаю сообщения…", seen, total, time.time() - started))

        stopped = self._cs_stop

        site_name = f"chat_{chat_id}_{time.strftime('%Y%m%d_%H%M%S')}"
        site_dir = os.path.join(SITE_ROOT, site_name)
        media_dir = os.path.join(site_dir, "media")
        media_map = {}
        n_photo = n_video = 0
        media_total = 0

        if do_media:
            media_msgs = [m for m in msgs if self._kind(m)]
            media_total = len(media_msgs)
            if media_msgs:
                os.makedirs(media_dir, exist_ok=True)
                done = 0
                last_edit = 0.0
                current = ""
                for m in media_msgs:
                    if self._cs_stop:
                        break
                    kind = self._kind(m)
                    fname = f"{kind}_{m.id}{self._ext(m)}"
                    current = fname
                    try:
                        got = await self._client.download_media(
                            m, file=os.path.join(media_dir, fname)
                        )
                        th = None
                        if got and kind != "photo":
                            try:
                                th = await self._client.download_media(
                                    m,
                                    file=os.path.join(media_dir, f"{kind}_{m.id}_th.jpg"),
                                    thumb=-1,
                                )
                            except Exception:
                                th = None
                        if got:
                            media_map[m.id] = {
                                "kind": kind,
                                "file": fname,
                                "thumb": os.path.basename(th) if th else None,
                            }
                            if kind == "photo":
                                n_photo += 1
                            else:
                                n_video += 1
                        else:
                            media_map[m.id] = {"kind": kind, "error": "не скачалось"}
                    except Exception as e:
                        media_map[m.id] = {"kind": kind, "error": str(e)[:80]}
                    done += 1
                    now = time.time()
                    if form and now - last_edit > 3:
                        last_edit = now
                        try:
                            await form.edit(rich_html=self._progress(
                                "Скачиваю медиа…", seen, total, now - started,
                                done, media_total, current,
                            ))
                        except Exception:
                            form = None

        html_data = await self._render(title, chat_id, reversed(msgs), len(msgs), media_map)
        os.makedirs(site_dir, exist_ok=True)
        index_path = os.path.join(site_dir, "index.html")
        with open(index_path, "wb") as f:
            f.write(html_data)

        stamp = time.strftime("%Y%m%d_%H%M%S")
        zip_path = os.path.join(SITE_ROOT, f"ChatSave_{chat_id}_{stamp}.zip")
        zip_err = None
        bytes_total = 0
        try:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_STORED, allowZip64=True) as zf:
                for root, dirs, files in os.walk(site_dir):
                    for f in sorted(files):
                        full = os.path.join(root, f)
                        rel = os.path.relpath(full, site_dir)
                        zf.write(full, arcname=f"{site_name}/{rel}")
            bytes_total = os.path.getsize(zip_path)
        except Exception as e:
            zip_path = None
            zip_err = str(e)[:120]

        dest = int(self.config["dest_chat"])
        topic = int(self.config["dest_topic"])

        cap = (
            f"🗂 ChatSave · {title}\n"
            f"🗓 Сообщений: {len(msgs)}"
            + (f"\n📷 Фото: {n_photo} · 🎬 Видео: {n_video}" if do_media else "\n📷 Медиа отключено (.cs nomedia)")
            + (f"\n💾 Размер архива: {_fmt_size(bytes_total)}" if zip_path else "")
            + ("\n⛔ Остановлено вручную (частичный файл)" if stopped else "")
        )

        link = None
        if zip_path and bytes_total <= MAX_ZIP_BYTES:
            sent = await self._client.send_file(
                dest, zip_path, caption=cap, reply_to=topic, force_document=True
            )
            short = str(dest).replace("-100", "", 1).lstrip("-")
            link = f"https://t.me/c/{short}/{topic}/{sent.id}"
        else:
            if zip_path:
                cap += "\n⚠️ Архив больше лимита Telegram — отправляю HTML, сайт лежит локально"
            else:
                cap += f"\n⚠️ Архив не собран: {zip_err} — отправляю HTML, сайт лежит локально"
            cap += f"\n📁 Локально: {site_dir}"
            try:
                sent = await self._client.send_file(
                    dest, index_path, caption=cap, reply_to=topic, force_document=True
                )
                short = str(dest).replace("-100", "", 1).lstrip("-")
                link = f"https://t.me/c/{short}/{topic}/{sent.id}"
            except Exception:
                link = None

        if form:
            await form.edit(rich_html=self._done(
                title, len(msgs), n_photo, n_video, bytes_total, site_dir, link, time.time() - started
            ))
        else:
            await utils.answer(
                message,
                cap + (f"\n🔗 {link}" if link else ""),
            )

    def _kind(self, m):
        try:
            if m.photo:
                return "photo"
            if m.video_note:
                return "video_note"
            if m.gif:
                return "gif"
            if m.video:
                return "video"
        except Exception:
            pass
        return None

    def _ext(self, m):
        try:
            if m.photo:
                return ".jpg"
            mime = getattr(m.document, "mime_type", "") or ""
            if "webm" in mime:
                return ".webm"
        except Exception:
            pass
        return ".mp4"

    async def _form(self, message, status, done, total):
        if not getattr(self, "inline", None):
            return None
        try:
            return await self.inline.form(
                "",
                message=message,
                rich_html=self._progress(status, done, total),
                force_me=True,
            )
        except Exception:
            return None

    def _progress(self, status, done, total, elapsed=0.0, m_done=0, m_total=0, m_current=""):
        k = self.inline.screen()
        k.add("<b>🗂 ChatSave — экспорт чата в HTML-сайт</b>")
        k.add("<hr>")
        k.add(f"<b>Статус:</b> {_esc(status)}")
        if elapsed:
            k.add(f"<b>Время:</b> {elapsed:.1f} c")
        if total and done:
            pct = min(100, round(done * 100 / total))
            k.add(f"<pre>{_bar(pct)}  {pct}%</pre>")
        k.add(f"<b>Обработано:</b> {done} из {total or '∞'}")
        if m_total:
            mpct = min(100, round(m_done * 100 / m_total))
            k.add(f"<b>Медиа:</b> {m_done}/{m_total} ({mpct}%)")
            if m_current:
                k.add(f"<code>{_esc(m_current)}</code>")
        k.add("<hr>")
        k.add(k.row(k.tap("⛔ Остановить", self._stop, style="danger", force_me=True)))
        return k

    def _done(self, title, count, n_photo, n_video, size, site_dir, link, elapsed):
        k = self.inline.screen()
        k.add("<b>✅ Экспорт завершён</b>")
        k.add("<hr>")
        k.add(f"<b>Чат:</b> {_esc(title)}")
        k.add(f"<b>Сообщений:</b> {count}")
        k.add(f"<b>Фото:</b> {n_photo} · <b>Видео:</b> {n_video}")
        if size:
            k.add(f"<b>Размер архива:</b> {_fmt_size(size)}")
        k.add(f"<b>Время:</b> {elapsed:.1f} c")
        k.add(f"<code>{_esc(site_dir)}</code>")
        k.add("<hr>")
        if link:
            k.add(f'<tg-button type="url" url="{link}">🗂 Открыть в архиве</tg-button>')
        k.add(k.row(k.tap("Скрыть", self._freeze, style="primary", force_me=True)))
        return k

    async def _stop(self, call):
        self._cs_stop = True
        await call.answer()

    async def _freeze(self, call):
        await call.answer()

    def _media(self, m):
        try:
            if m.sticker:
                emo = ""
                for attr in getattr(m.file, "attributes", []) or []:
                    if getattr(attr, "alt", None):
                        emo = " " + attr.alt
                return "🎭 Стикер" + emo
            if m.photo:
                return "📷 Фото"
            if m.voice:
                secs = getattr(m.voice, "seconds", 0)
                return f"🎤 Голосовое · {secs} c" if secs else "🎤 Голосовое"
            if m.video_note:
                return "📹 Видеосообщение"
            if m.gif:
                return "🎞 GIF"
            if m.video:
                return "🎬 Видео"
            if m.audio:
                fn = getattr(m.file, "name", None) or getattr(m.audio, "title", None) or "аудио"
                return f"🎧 {fn}"
            if m.contact:
                return f"👤 {_esc(getattr(m.contact, 'first_name', ''))} {_esc(getattr(m.contact, 'last_name', ''))}".strip()
            if m.geo:
                return "📍 Геолокация"
            if m.poll:
                poll = getattr(m.poll, "poll", None)
                return f"📊 {_esc(getattr(poll, 'question', 'Опрос'))}"
            if m.dice:
                return f"🎲 {_esc(getattr(m.dice, 'emoticon', '🎲'))}"
            if m.document:
                fn = getattr(m.file, "name", None) or "файл"
                return f"📎 {fn}"
        except Exception:
            pass
        return None

    def _media_html(self, m, item):
        if not item:
            return None
        if item.get("error"):
            label = self._media(m) or "Медиа"
            return f'<span class="mfail">{_esc(label)} · не скачалось: {_esc(item["error"])}</span>'
        kind = item["kind"]
        esc_rel = _esc(f"media/{item['file']}")
        if kind == "photo":
            return (
                f'<a href="{esc_rel}" target="_blank">'
                f'<img class="pm" src="{esc_rel}" loading="lazy" alt="фото"'
                f' onerror="this.outerHTML=\'<span class=mfail>📷 Фото не открылось</span>\'"></a>'
            )
        cls = "vd"
        if kind == "video_note":
            cls = "vd vn"
        if kind == "gif":
            return f'<video class="{cls}" src="{esc_rel}" autoplay loop muted playsinline preload="metadata"></video>'
        poster = ""
        if item.get("thumb"):
            poster = f' poster="{_esc("media/" + item["thumb"])}"'
        return f'<video class="{cls}" src="{esc_rel}" controls preload="none"{poster}></video>'

    async def _render(self, title, chat_id, raw, count, media_map=None):
        media_map = media_map or {}
        msgs = list(raw)
        msgs.reverse()

        names = {}
        rows = []
        last_day = None
        prev_sid = None
        prev_dt = None

        for m in msgs:
            date = m.date
            day = date.strftime("%d.%m.%Y")
            if day != last_day:
                rows.append(f'<div class="day"><span>{_esc(day)}</span></div>')
                last_day = day

            if m.action is not None:
                label = ACTIONS.get(type(m.action).__name__, "⚙️ Событие в чате")
                rows.append(f'<div class="svc"><span>{_esc(label)}</span></div>')
                prev_sid = None
                prev_dt = None
                continue

            sid = m.sender_id or 0
            if sid not in names:
                if not sid:
                    name = title
                else:
                    sender = m.sender
                    if sender is None:
                        try:
                            sender = await m.get_sender()
                        except Exception:
                            sender = None
                    name = _display_name(sender) or "Отправитель"
                names[sid] = name
            name = names[sid]

            item = media_map.get(m.id)
            media_html = self._media_html(m, item) if item else None
            if not media_html:
                media = self._media(m)
                media_html = f'<span class="ext">{_esc(media)}</span>' if media else ""
            text = URL_RE.sub(r'<a href="\1">\1</a>', _esc(m.message)) if m.message else ""
            if not text and not media_html:
                continue

            grouped = (
                prev_sid == sid
                and prev_dt is not None
                and (date - prev_dt).total_seconds() < 600
            )
            prev_sid = sid
            prev_dt = date

            stamp = date.strftime("%H:%M") + (" ✏️" if m.edit_date else "")

            inner = ""
            if m.fwd_from:
                who = m.fwd_from.from_name or ""
                inner += f'<div class="note">↪ Переслано{": " + _esc(who) if who else ""}</div>'
            if m.reply_to:
                inner += '<div class="note">↱ Ответ</div>'
            inner += media_html
            if text:
                inner += f'<div class="tx">{text}</div>'
            inner += f'<span class="tm">{_esc(stamp)}</span>'

            avatar = ""
            name_line = ""
            if not m.out and not grouped:
                color = _palette(name)
                avatar = f'<div class="ava" style="background:{color};width:37px;height:37px;font-size:13px">{_esc(_initials(name))}</div>'
                name_line = f'<span class="nm" style="color:{color}">{_esc(name)}</span>'

            cls = "m" + (" out" if m.out else "") + ("" if grouped else " g1")
            rows.append(f'<div class="{cls}">{avatar}<div class="b">{name_line}{inner}</div></div>')

        info = f"Экспорт: {time.strftime('%d.%m.%Y %H:%M')} · ID чата: {chat_id}"
        page = (
            PAGE.replace("__TITLE__", _esc(title))
            .replace("__C_AVA__", _palette(title))
            .replace("__INI__", _esc(_initials(title)))
            .replace("__INFO__", info)
            .replace("__MESSAGES__", "\n".join(rows))
            .replace("__COUNT__", str(count))
            .replace("__DATE__", time.strftime("%d.%m.%Y %H:%M"))
        )
        return page.encode("utf-8")
