
from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo)
from aiogram.utils.keyboard import InlineKeyboardBuilder
import config


def main_menu(is_creator: bool = False) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🎁 Открыть Mini App", web_app=WebAppInfo(url=config.WEBAPP_URL))
    kb.button(text="👤 Мой профиль", callback_data="profile")
    kb.button(text="💎 Подписка", callback_data="subscriptions")
    kb.button(text="🎉 Рефералка", callback_data="referral")
    kb.button(text="⚡️ Попробовать бесплатно", callback_data="trial")
    kb.adjust(1, 2, 1, 1)
    return kb.as_markup()


def worker_panel(claims: list, payouts: list) -> InlineKeyboardMarkup:

    busy = {p["slug"] for p in payouts if p["status"] in ("awaiting", "received", "sold")}
    kb = InlineKeyboardBuilder()
    shown = 0
    for c in claims:
        if c["slug"] in busy or shown >= 10:
            continue
        title = c.get("title") or c["slug"]
        kb.button(text=f"📥 Сдать: {title[:24]}", callback_data=f"wpay:{c['slug']}")
        shown += 1
    kb.button(text="🔄 Обновить", callback_data="worker")
    kb.button(text="◀️ В меню", callback_data="home")
    kb.adjust(1)
    return kb.as_markup()


def pay_fee(req_id: int, fee_stars: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=f"⭐ Оплатить {fee_stars} ⭐", pay=True)
    kb.button(text="◀️ Отмена", callback_data="worker")
    kb.adjust(1)
    return kb.as_markup()


def creator_panel(s: dict) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=f"📥 Получено · {s['received']}", callback_data="cr:received")
    kb.button(text=f"💰 К выплате · {s['sold']}", callback_data="cr:sold")
    kb.button(text=f"⏰ Ждут гифт · {s['awaiting']}", callback_data="cr:awaiting")
    kb.button(text=f"✅ Выплачено · {s['paid']}", callback_data="cr:paid")
    kb.button(text="👥 Рабочие", callback_data="cr:workers")
    kb.button(text="🛠 Админка", callback_data="adm")
    kb.button(text="🔄 Обновить", callback_data="creator")
    kb.button(text="◀️ В меню", callback_data="home")
    kb.adjust(2, 2, 2, 2)
    return kb.as_markup()


def request_actions(p: dict) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    st = p["status"]
    if st in ("awaiting", "received"):
        if st == "awaiting":
            kb.button(text="📥 Отметить «получен»", callback_data=f"crrecv:{p['id']}")
        kb.button(text="💰 Продано — ввести сумму", callback_data=f"crsold:{p['id']}")
        kb.button(text="❌ Отклонить", callback_data=f"crrej:{p['id']}")
    elif st == "sold":
        kb.button(text=f"💵 Выплачено ({p['payout_ton']} TON)", callback_data=f"crpaid:{p['id']}")
        kb.button(text="✏️ Изменить сумму", callback_data=f"crsold:{p['id']}")
    if p.get("username"):
        kb.button(text="👤 Написать рабочему", url=f"https://t.me/{p['username']}")
    kb.button(text="◀️ Назад", callback_data="creator")
    kb.adjust(1)
    return kb.as_markup()


def request_list(items: list, back: str = "creator") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for p in items[:12]:
        title = (p.get("gift_title") or p["slug"] or "лот")[:20]
        kb.button(text=f"#{p['id']} {title}", callback_data=f"crp:{p['id']}")
    kb.button(text="◀️ Назад", callback_data=back)
    kb.adjust(1)
    return kb.as_markup()


def admin_panel() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📢 Рассылка", callback_data="adm:bcast")
    kb.button(text="👤 Управление юзером", callback_data="adm:user")
    kb.button(text="👥 Список юзеров", callback_data="adm:list")
    kb.button(text="🎁 Выдать подписку", callback_data="adm:give")
    kb.button(text="🚫 Снять подписку", callback_data="adm:revoke")
    kb.button(text="📋 Массовая выдача", callback_data="adm:bulk")
    kb.button(text="◀️ В меню", callback_data="home")

    kb.adjust(2, 2, 2, 1)
    return kb.as_markup()


def user_card(uid: int, has_sub: bool, worker_st: str | None,
              banned: bool = False) -> InlineKeyboardMarkup:

    kb = InlineKeyboardBuilder()
    kb.button(text=("➕ Продлить/выдать" if has_sub else "🎁 Выдать подписку"),
              callback_data=f"um:givemenu:{uid}")
    if has_sub:
        kb.button(text="🚫 Снять подписку", callback_data=f"um:subrevoke:{uid}")
    kb.button(text="🗒 История", callback_data=f"um:history:{uid}")
    if banned:
        kb.button(text="🔓 Разбанить", callback_data=f"um:unban:{uid}")
    else:
        kb.button(text="⛔ Забанить", callback_data=f"um:ban:{uid}")
    kb.button(text="🔄 Обновить", callback_data=f"um:card:{uid}")
    kb.button(text="🔎 Другой юзер", callback_data="adm:user")
    kb.button(text="◀️ В админку", callback_data="adm")
    kb.adjust(1, 1, 1, 2, 1, 2)
    return kb.as_markup()


def search_results(rows: list) -> InlineKeyboardMarkup:

    kb = InlineKeyboardBuilder()
    for uid, uname in rows:
        kb.button(text=f"@{uname} · {uid}", callback_data=f"um:card:{uid}")
    kb.button(text="🔎 Другой поиск", callback_data="adm:user")
    kb.button(text="◀️ В админку", callback_data="adm")
    kb.adjust(1)
    return kb.as_markup()


def card_back(uid: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="◀️ К карточке", callback_data=f"um:card:{uid}")
    return kb.as_markup()


def users_list(rows: list, page: int, total: int, per: int = 8) -> InlineKeyboardMarkup:

    kb = InlineKeyboardBuilder()
    for uid, uname in rows:
        label = f"@{uname}" if uname else f"ID {uid}"
        kb.button(text=f"{label} · {uid}", callback_data=f"um:card:{uid}")
    pages = max(1, (total + per - 1) // per)
    nav = 0
    if page > 0:
        kb.button(text="◀️", callback_data=f"adm:list:{page - 1}"); nav += 1
    if page < pages - 1:
        kb.button(text="▶️", callback_data=f"adm:list:{page + 1}"); nav += 1
    kb.button(text="🔎 Поиск", callback_data="adm:user")
    kb.button(text="◀️ В админку", callback_data="adm")
    sizes = [1] * len(rows)
    if nav:
        sizes.append(nav)
    sizes.append(2)
    kb.adjust(*sizes)
    return kb.as_markup()


def give_menu(uid: int) -> InlineKeyboardMarkup:

    kb = InlineKeyboardBuilder()
    for label, h in (("1 день", 24), ("3 дня", 72), ("7 дней", 168),
                     ("30 дней", 720), ("90 дней", 2160), ("365 дней", 8760)):
        kb.button(text=label, callback_data=f"um:give:{uid}:{h}")
    kb.button(text="✏️ Своё число часов", callback_data=f"um:givecustom:{uid}")
    kb.button(text="◀️ Назад", callback_data=f"um:card:{uid}")
    kb.adjust(2, 2, 2, 1, 1)
    return kb.as_markup()


def trial_rules() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Принимаю", callback_data="accept_trial")
    kb.button(text="🚫 Отказ", callback_data="decline_trial")
    kb.adjust(1)
    return kb.as_markup()


def tariffs() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for code, (label, _h, ton, stars) in config.TARIFFS.items():
        kb.button(text=f"💎 {label} — {ton} TON / {stars} ⭐", callback_data=f"buy:{code}")
    kb.button(text="◀️ Назад", callback_data="home")
    kb.adjust(1)
    return kb.as_markup()


def worker_apply(can_reapply: bool = False) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=("🔄 Подать повторно" if can_reapply else "✉️ Подать заявку"),
              callback_data="worker_apply")
    kb.button(text="◀️ В меню", callback_data="home")
    kb.adjust(1)
    return kb.as_markup()


def app_decision(uid: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Одобрить", callback_data=f"wapp_ok:{uid}")
    kb.button(text="❌ Отклонить", callback_data=f"wapp_no:{uid}")
    kb.adjust(2)
    return kb.as_markup()


def renew_sub() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="💎 Продлить подписку", callback_data="subscriptions")
    kb.button(text="🏠 В меню", callback_data="home")
    kb.adjust(1)
    return kb.as_markup()


def back_home() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🏠 В меню", callback_data="home")
    return kb.as_markup()


def access_button(invite_url: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔓 Перейти к доступу к листингу", url=invite_url)
    return kb.as_markup()


def listing_card(slug: str, seller_user: str | None = None,
                 item_slug: str | None = None) -> InlineKeyboardMarkup:
    claim_key = item_slug or slug
    rows = [[InlineKeyboardButton(text="🟢 Занять", callback_data=f"listing_claim:{claim_key}")]]
    bottom = []
    if item_slug:
        bottom.append(InlineKeyboardButton(text="🔗 Открыть лот", url=f"https://t.me/nft/{item_slug}"))
    if seller_user:
        bottom.append(InlineKeyboardButton(text="👤 Владелец", url=f"https://t.me/{seller_user}"))
    if bottom:
        rows.append(bottom)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def claimed_dm_kb(owner_user: str | None = None,
                  item_slug: str | None = None) -> InlineKeyboardMarkup:

    kb = InlineKeyboardBuilder()
    if owner_user:
        kb.button(text=f"✍️ Написать владельцу @{owner_user}", url=f"https://t.me/{owner_user}")
    if item_slug:
        kb.button(text="🔗 Открыть лот", url=f"https://t.me/nft/{item_slug}")
    kb.button(text="🏠 В меню", callback_data="home")
    kb.adjust(1)
    return kb.as_markup()


def listing_taken(claim_key: str, owner_id: int) -> InlineKeyboardMarkup:


    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="❌ Отменить",
                             callback_data=f"listing_release:{claim_key}:{owner_id}")]])
