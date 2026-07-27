

import json
import os
import re

from aiogram.client.session.middlewares.base import BaseRequestMiddleware
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

_MAP_PATH = os.path.join(os.path.dirname(__file__), "_emoji_map.json")

try:
    with open(_MAP_PATH, encoding="utf-8") as f:
        _RAW = json.load(f)
except Exception:
    _RAW = {}

VARIANTS: dict[str, str] = {}
for _emoji, _eid in _RAW.items():
    _base = _emoji.replace("️", "")
    for _v in (_emoji, _base, _base + "️"):
        if _v:
            VARIANTS.setdefault(_v, _eid)

_KEYS = sorted(VARIANTS, key=len, reverse=True)
_RE = re.compile("|".join(re.escape(k) for k in _KEYS)) if _KEYS else None
_RE_LEAD = re.compile("^(" + "|".join(re.escape(k) for k in _KEYS) + ")\\s*") if _KEYS else None
_TG_SPAN = re.compile(r"<tg-emoji\b[^>]*>.*?</tg-emoji>", re.DOTALL)


def _repl(m: "re.Match") -> str:
    s = m.group(0)
    eid = VARIANTS.get(s)
    return f'<tg-emoji emoji-id="{eid}">{s}</tg-emoji>' if eid else s


def premiumize(text: str) -> str:


    if not text or not _RE:
        return text
    if "<tg-emoji" not in text:
        return _RE.sub(_repl, text)
    out, last = [], 0
    for m in _TG_SPAN.finditer(text):
        out.append(_RE.sub(_repl, text[last:m.start()]))
        out.append(m.group(0))
        last = m.end()
    out.append(_RE.sub(_repl, text[last:]))
    return "".join(out)


def _premium_button(btn: InlineKeyboardButton):


    if not _RE_LEAD or getattr(btn, "icon_custom_emoji_id", None) or not btn.text:
        return None
    m = _RE_LEAD.match(btn.text)
    if not m:
        return None
    eid = VARIANTS.get(m.group(1))
    rest = btn.text[m.end():].strip()
    if not eid or not rest:
        return None
    return btn.model_copy(update={"icon_custom_emoji_id": eid, "text": rest})


def premiumize_markup(markup):

    if not isinstance(markup, InlineKeyboardMarkup):
        return None
    changed = False
    rows = []
    for row in markup.inline_keyboard:
        new_row = []
        for btn in row:
            pb = _premium_button(btn)
            if pb is not None:
                changed = True
                new_row.append(pb)
            else:
                new_row.append(btn)
        rows.append(new_row)
    return InlineKeyboardMarkup(inline_keyboard=rows) if changed else None


class PremiumEmojiMiddleware(BaseRequestMiddleware):


    async def __call__(self, make_request, bot, method):
        if type(method).__name__ in ("AnswerCallbackQuery", "AnswerInlineQuery"):
            return await make_request(bot, method)
        updates = {}
        pm = str(getattr(method, "parse_mode", "") or "").lower()
        if "markdown" not in pm:
            for field in ("text", "caption"):
                val = getattr(method, field, None)
                if isinstance(val, str) and val:
                    new = premiumize(val)
                    if new != val:
                        updates[field] = new
        mk = getattr(method, "reply_markup", None)
        new_mk = premiumize_markup(mk) if mk is not None else None
        if new_mk is not None:
            updates["reply_markup"] = new_mk
        if not updates:
            return await make_request(bot, method)
        new_method = method.model_copy(update=updates)
        try:
            return await make_request(bot, new_method)
        except TelegramBadRequest as e:
            if "emoji" in str(e).lower():
                return await make_request(bot, method)
            raise
