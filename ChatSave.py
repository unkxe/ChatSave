# meta developer: @unkxe
# meta description: Экспорт истории чата в HTML-сайт с фото и видео, отправка в архив-топик
__version__ = (2, 2, 0)

import asyncio
import base64 as _b64
import html as _html
import mimetypes as _mt
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
<html lang="ru" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root{--bg0:#0a0f16;--bg1:#0e1621;--bg2:#17212b;--card:rgba(23,33,43,.72);--line:rgba(255,255,255,.08);--fg:#e7ebf0;--dim:#8fa5b9;--accent:#5eb5f7;--accent2:#a695e7;--bubble:#182533;--bubble-out:linear-gradient(135deg,#2b5278,#34689b);--shadow:0 10px 30px rgba(0,0,0,.45)}
html[data-theme="light"]{--bg0:#eef2f7;--bg1:#f7f9fc;--bg2:#ffffff;--card:rgba(255,255,255,.8);--line:rgba(0,0,0,.08);--fg:#1c2733;--dim:#6b7f93;--accent:#2f80ed;--accent2:#7b61ff;--bubble:#ffffff;--bubble-out:linear-gradient(135deg,#d7e9ff,#c3ddff);--shadow:0 10px 30px rgba(40,60,90,.12)}
*{margin:0;padding:0;box-sizing:border-box}
html{scroll-behavior:smooth}
body{background:radial-gradient(1200px 600px at 15% -10%,rgba(94,181,247,.16),transparent 60%),radial-gradient(1000px 500px at 100% 0,rgba(166,149,231,.14),transparent 55%),var(--bg1);color:var(--fg);font:15px/1.5 -apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;min-height:100vh;transition:background .4s,color .4s;-webkit-font-smoothing:antialiased}
.wrap{max-width:880px;margin:0 auto;padding:22px 14px 90px}
.head{position:sticky;top:10px;z-index:20;display:flex;align-items:center;gap:14px;background:var(--card);backdrop-filter:blur(16px) saturate(140%);-webkit-backdrop-filter:blur(16px) saturate(140%);border:1px solid var(--line);border-radius:18px;padding:14px 18px;margin-bottom:22px;box-shadow:var(--shadow);animation:drop .5s cubic-bezier(.2,.8,.2,1) both}
.ava{width:50px;height:50px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:19px;color:#fff;flex:none;box-shadow:0 6px 18px rgba(0,0,0,.35);position:relative;overflow:hidden}
.ava::after{content:"";position:absolute;inset:0;border-radius:50%;box-shadow:inset 0 0 0 2px rgba(255,255,255,.15)}
.t1{font-size:18px;font-weight:700;letter-spacing:.2px}
.t2{font-size:12.5px;color:var(--dim);margin-top:3px}
.spacer{flex:1}
.tool{display:flex;gap:8px}
.ib{width:40px;height:40px;border-radius:12px;border:1px solid var(--line);background:var(--bg2);color:var(--fg);cursor:pointer;font-size:17px;display:flex;align-items:center;justify-content:center;transition:transform .18s,background .18s,border-color .18s}
.ib:hover{transform:translateY(-2px);border-color:var(--accent)}
.ib:active{transform:scale(.94)}
.day{text-align:center;margin:26px 0 12px;animation:fade .5s both}
.day span{background:var(--card);backdrop-filter:blur(10px);border:1px solid var(--line);font-size:12px;color:var(--fg);padding:6px 16px;border-radius:16px;font-weight:600;letter-spacing:.3px}
.svc{text-align:center;margin:12px 0;animation:fade .5s both}
.svc span{background:rgba(0,0,0,.18);border:1px solid var(--line);font-size:12.5px;color:var(--dim);padding:5px 15px;border-radius:14px}
.m{display:flex;margin:6px 0;align-items:flex-end;gap:8px;animation:rise .42s cubic-bezier(.2,.8,.2,1) both}
.m.out{justify-content:flex-end}
.b{position:relative;max-width:74%;background:var(--bubble);border:1px solid var(--line);border-radius:16px;padding:9px 13px 7px;font-size:14.5px;box-shadow:0 3px 12px rgba(0,0,0,.18);overflow-wrap:break-word;transition:transform .18s,box-shadow .18s}
.b:hover{transform:translateY(-1px);box-shadow:0 8px 22px rgba(0,0,0,.28)}
.m.out .b{background:var(--bubble-out);border-color:rgba(255,255,255,.12)}
.g1 .b{border-bottom-left-radius:6px}
.m.out.g1 .b{border-bottom-left-radius:16px;border-bottom-right-radius:6px}
.nm{display:block;font-size:13.5px;font-weight:700;margin-bottom:3px}
.note{font-size:12px;color:var(--dim);margin:2px 0 4px;font-style:italic}
.tx{white-space:pre-wrap}
.tx a{color:var(--accent);text-decoration:none;border-bottom:1px solid transparent;transition:border-color .2s}
.tx a:hover{border-bottom-color:var(--accent)}
.tm{float:right;margin:7px -3px -4px 12px;font-size:11px;color:var(--dim)}
.ext{color:var(--accent);font-size:13px;display:inline-block;padding:3px 0}
.pm{display:block;max-width:330px;max-height:430px;border-radius:12px;margin:3px 0;cursor:zoom-in;transition:transform .25s,filter .25s;will-change:transform}
.pm:hover{transform:scale(1.02);filter:brightness(1.06)}
.vd{display:block;width:330px;max-width:100%;border-radius:12px;margin:3px 0;background:#000}
.vn{width:230px;height:230px;border-radius:50%;object-fit:cover;margin:4px auto;display:block;border:2px solid var(--line)}
.mfail{display:inline-block;font-size:13px;color:#e17076;margin:3px 0}
.burn{display:inline-flex;align-items:center;gap:5px;font-size:11.5px;font-weight:600;color:#ff9e57;background:rgba(255,140,60,.13);border:1px solid rgba(255,140,60,.35);padding:2px 9px;border-radius:10px;margin:3px 0}
.mfile{display:flex;align-items:center;gap:10px;background:rgba(0,0,0,.15);border:1px solid var(--line);border-radius:12px;padding:10px 12px;margin:4px 0;max-width:330px;text-decoration:none;color:var(--fg);transition:transform .18s,border-color .18s}
.mfile:hover{transform:translateY(-2px);border-color:var(--accent)}
.mfile .ic{font-size:22px}
.mfile .fn{font-size:13px;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.footer{text-align:center;color:var(--dim);font-size:12px;margin-top:38px;padding-top:18px;border-top:1px solid var(--line)}
#lb{position:fixed;inset:0;background:rgba(4,8,12,.92);backdrop-filter:blur(8px);display:none;align-items:center;justify-content:center;z-index:100;opacity:0;transition:opacity .3s}
#lb.on{display:flex;opacity:1}
#lb img,#lb video{max-width:94vw;max-height:90vh;border-radius:12px;box-shadow:0 20px 60px rgba(0,0,0,.6);animation:zoom .35s cubic-bezier(.2,.9,.2,1) both}
#lb .x{position:absolute;top:18px;right:22px;font-size:30px;color:#fff;cursor:pointer;width:48px;height:48px;border-radius:50%;display:flex;align-items:center;justify-content:center;background:rgba(255,255,255,.08);transition:background .2s,transform .2s}
#lb .x:hover{background:rgba(255,255,255,.2);transform:rotate(90deg)}
@keyframes rise{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
@keyframes fade{from{opacity:0}to{opacity:1}}
@keyframes drop{from{opacity:0;transform:translateY(-16px)}to{opacity:1;transform:none}}
@keyframes zoom{from{opacity:0;transform:scale(.9)}to{opacity:1;transform:none}}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
@media (max-width:600px){.b{max-width:84%}.pm,.vd{max-width:100%}.wrap{padding:14px 10px 80px}}
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
<div class="spacer"></div>
<div class="tool"><button class="ib" id="theme" title="Тема">🌙</button></div>
</div>
__MESSAGES__
<div class="footer">🗂 ChatSave · __COUNT__ · выгружено __DATE__</div>
</div>
<div id="lb"><span class="x">✕</span><div id="lbc"></div></div>
<script>
(function(){
  var root=document.documentElement,tb=document.getElementById('theme');
  var saved=null;try{saved=localStorage.getItem('cs_theme')}catch(e){}
  if(saved)root.dataset.theme=saved;
  function sync(){tb.textContent=root.dataset.theme==='dark'?'🌙':'☀️'}
  sync();
  tb.addEventListener('click',function(){
    root.dataset.theme=root.dataset.theme==='dark'?'light':'dark';
    try{localStorage.setItem('cs_theme',root.dataset.theme)}catch(e){}
    sync();
  });
  var lb=document.getElementById('lb'),lbc=document.getElementById('lbc');
  function close(){lb.classList.remove('on');lbc.innerHTML=''}
  lb.addEventListener('click',function(e){if(e.target===lb||e.target.classList.contains('x'))close()});
  document.addEventListener('keydown',function(e){if(e.key==='Escape')close()});
  document.querySelectorAll('img.pm').forEach(function(img){
    img.addEventListener('click',function(){
      lbc.innerHTML='<img src="'+img.getAttribute('src')+'">';
      lb.classList.add('on');
    });
  });
  var io=new IntersectionObserver(function(es){
    es.forEach(function(en){if(en.isIntersecting){en.target.style.animationPlayState='running';io.unobserve(en.target)}});
  },{threshold:.05});
  document.querySelectorAll('.m,.day,.svc').forEach(function(el){el.style.animationPlayState='paused';io.observe(el)});
})();
</script>
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
            loader.ConfigValue("embed_media", True, lambda: "Встраивать фото/видео прямо в HTML (base64, один автономный файл)"),
            loader.ConfigValue("embed_max_mb", 200, lambda: "Лимит размера одного медиа для встраивания, МБ"),
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
        n_photo = n_video = n_burn = 0
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
                    fpath = os.path.join(media_dir, fname)
                    current = fname
                    ttl = self._ttl(m)
                    try:
                        got = await self._download_media(m, fpath)
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
                            entry = {"kind": kind, "file": fname}
                            if ttl:
                                entry["ttl"] = ttl
                                n_burn += 1
                            if th:
                                entry["thumb"] = os.path.basename(th)
                            self._maybe_embed(entry, fpath, th)
                            media_map[m.id] = entry
                            if kind == "photo":
                                n_photo += 1
                            else:
                                n_video += 1
                        else:
                            if ttl:
                                media_map[m.id] = {
                                    "kind": kind,
                                    "ttl": ttl,
                                    "error": "сгорающее медиа уже недоступно",
                                }
                            else:
                                media_map[m.id] = {"kind": kind, "error": "не скачалось"}
                    except Exception as e:
                        media_map[m.id] = {"kind": kind, "ttl": ttl or None, "error": str(e)[:80]}
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
            + (f"\n📷 Фото: {n_photo} · 🎬 Видео: {n_video}" + (f" · 🔥 Сгорающих: {n_burn}" if n_burn else "") if do_media else "\n📷 Медиа отключено (.cs nomedia)")
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
                title, len(msgs), n_photo, n_video, n_burn, bytes_total, site_dir, link, time.time() - started
            ))
        else:
            await utils.answer(
                message,
                cap + (f"\n🔗 {link}" if link else ""),
            )

    async def _download_media(self, m, fpath, tries=3):
        last = None
        for attempt in range(max(1, tries)):
            try:
                got = await self._client.download_media(m, file=fpath)
                if got and os.path.isfile(got) and os.path.getsize(got) > 0:
                    return got
            except Exception as e:
                last = e
            if attempt + 1 < tries:
                await asyncio.sleep(1.0 + attempt)
        if last and not os.path.isfile(fpath):
            raise last
        return None

    def _maybe_embed(self, entry, fpath, thumb):
        if not self._opt_bool("embed_media", True):
            return
        limit = int(self._opt_num("embed_max_mb", 200)) * 1024 * 1024
        try:
            if not os.path.isfile(fpath) or os.path.getsize(fpath) > limit:
                return
            mime = _mt.guess_type(fpath)[0] or "application/octet-stream"
            with open(fpath, "rb") as fh:
                data = _b64.b64encode(fh.read()).decode("ascii")
            entry["embed"] = "data:{};base64,{}".format(mime, data)
            entry["mime"] = mime
            if thumb and os.path.isfile(thumb):
                tmime = _mt.guess_type(thumb)[0] or "image/jpeg"
                with open(thumb, "rb") as fh:
                    tdata = _b64.b64encode(fh.read()).decode("ascii")
                entry["embed_thumb"] = "data:{};base64,{}".format(tmime, tdata)
            os.remove(fpath)
            if thumb and os.path.isfile(thumb):
                os.remove(thumb)
            entry["embedded"] = True
        except Exception:
            entry.pop("embed", None)
            entry.pop("embed_thumb", None)

    def _opt_bool(self, name, default):
        try:
            return bool(self.config[name])
        except Exception:
            return default

    def _opt_num(self, name, default):
        try:
            return float(self.config[name])
        except Exception:
            return default

    def _ttl(self, m):
        try:
            media = getattr(m, "media", None)
            ttl = getattr(media, "ttl_seconds", None)
            if ttl:
                return int(ttl)
            ttl = getattr(m, "ttl_period", None)
            if ttl:
                return int(ttl)
        except Exception:
            pass
        return 0

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

    def _done(self, title, count, n_photo, n_video, n_burn, size, site_dir, link, elapsed):
        k = self.inline.screen()
        k.add("<b>✅ Экспорт завершён</b>")
        k.add("<hr>")
        k.add(f"<b>Чат:</b> {_esc(title)}")
        k.add(f"<b>Сообщений:</b> {count}")
        k.add(f"<b>Фото:</b> {n_photo} · <b>Видео:</b> {n_video}")
        if n_burn:
            k.add(f"<b>🔥 Сгорающих:</b> {n_burn}")
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
        burn = ""
        if item.get("ttl"):
            burn = f'<div class="burn">🔥 Сгорающее · {item["ttl"]} c</div>'
        if item.get("error"):
            label = self._media(m) or "Медиа"
            return burn + f'<span class="mfail">{_esc(label)} · {_esc(item["error"])}</span>'
        kind = item["kind"]
        if item.get("embed"):
            src = item["embed"]
        else:
            src = _esc(f"media/{item['file']}")
        if kind == "photo":
            return burn + (
                f'<img class="pm" src="{src}" loading="lazy" alt="фото"'
                f' onerror="this.outerHTML=\'<span class=mfail>📷 Фото не открылось</span>\'">'
            )
        cls = "vd"
        if kind == "video_note":
            cls = "vd vn"
        if kind == "gif":
            return burn + f'<video class="{cls}" src="{src}" autoplay loop muted playsinline preload="metadata"></video>'
        poster = ""
        pthumb = item.get("embed_thumb") or (
            f"media/{item['thumb']}" if item.get("thumb") else None
        )
        if pthumb:
            poster = f' poster="{pthumb if item.get("embed_thumb") else _esc(pthumb)}"'
        return burn + f'<video class="{cls}" src="{src}" controls preload="none"{poster}></video>'

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
