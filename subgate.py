

import time
import logging

from aiogram import BaseMiddleware
from aiogram.types import (Message, CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup)

import config
import db

log = logging.getLogger("subgate")

_OK_STATUSES = {"member", "administrator", "creator", "owner"}

_cache: dict[int, tuple[bool, float]] = {}
_POS_TTL = 180
_NEG_TTL = 15


def gate_keyboard() -> InlineKeyboardMarkup:
    chans = config.required_channels()
    rows = []
    for ch, link in chans:
        name = ch if ch.startswith("@") else "Подписаться"
        rows.append([InlineKeyboardButton(text=f"📢 {name}", url=link)])
    rows.append([InlineKeyboardButton(text="✅ Я подписался", callback_data="check_sub")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def gate_text() -> str:
    return (
        "🔒 <b>Нужна подписка на канал</b>\n\n"
        "Чтобы пользоваться ботом, подпишись на наш канал — там апдейты, "
        "фишки и важные анонсы.\n\n"
        "⚡️ После подписки нажми «Я подписался» — доступ откроется сразу."
    )


async def is_subscribed(bot, uid: int, force: bool = False) -> bool:
    chans = config.required_channels()
    if not chans:
        return True
    now = time.time()
    if not force:
        cached = _cache.get(uid)
        if cached and now - cached[1] < (_POS_TTL if cached[0] else _NEG_TTL):
            return cached[0]
    ok = True
    for ch, _link in chans:

        cid = int(ch) if str(ch).lstrip("-").isdigit() else None
        if cid is not None and await db.has_gate_request(uid, cid):
            continue
        try:
            member = await bot.get_chat_member(ch, uid)
            if str(getattr(member, "status", "")).split(".")[-1].lower() not in _OK_STATUSES:
                ok = False
                break
        except Exception as e:

            log.warning("get_chat_member(%s, %s) failed: %s — пропускаю канал (fail-open). "
                        "Добавь бота админом!", ch, uid, e)
            continue
    _cache[uid] = (ok, now)
    return ok


async def _show_gate(event):
    if isinstance(event, CallbackQuery):
        try:
            await event.message.edit_text(gate_text(), parse_mode="HTML",
                                          reply_markup=gate_keyboard())
        except Exception:
            await event.message.answer(gate_text(), parse_mode="HTML",
                                       reply_markup=gate_keyboard())
        await event.answer("Сначала подпишись на канал", show_alert=True)
    elif isinstance(event, Message):
        await event.answer(gate_text(), parse_mode="HTML", reply_markup=gate_keyboard())


class SubGateMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = getattr(event, "from_user", None)
        if user is None or not config.required_channels() or config.is_creator(user.id):
            return await handler(event, data)
        force = isinstance(event, CallbackQuery) and event.data == "check_sub"
        bot = data.get("bot") or getattr(event, "bot", None)
        if await is_subscribed(bot, user.id, force=force):
            return await handler(event, data)
        await _show_gate(event)
        return None
