

from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (Message, CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, LabeledPrice, PreCheckoutQuery,
                           ChatJoinRequest)

import logging
import time

import config
import db
import render
import keyboards
from sources import live_feed

router = Router()


class St(StatesGroup):
    sale = State()
    pct = State()
    fee = State()
    recv = State()
    bcast = State()
    give = State()
    revoke = State()
    user_lookup = State()
    give_custom = State()
    bulk_give = State()


async def cfg_pct() -> int:
    v = await db.get_kv("worker_pct")
    return int(v) if v is not None else config.WORKER_PCT


async def cfg_fee() -> int:
    v = await db.get_kv("payout_fee")
    return int(v) if v is not None else config.PAYOUT_FEE_STARS


async def cfg_recv() -> str:
    v = await db.get_kv("receiver_username")
    return (v or config.RECEIVER_USERNAME).lstrip("@")

try:
    from aiocryptopay import AioCryptoPay, Networks
    _cp = AioCryptoPay(token=config.CRYPTOBOT_TOKEN, network=Networks.MAIN_NET) if config.CRYPTOBOT_TOKEN else None
except Exception:
    _cp = None


def _parse_ref(text: str):
    parts = (text or "").split(maxsplit=1)
    if len(parts) == 2 and parts[1].startswith("ref_"):
        try:
            return int(parts[1][4:])
        except ValueError:
            return None
    return None


@router.message(CommandStart())
async def cmd_start(m: Message, state: FSMContext):
    await state.clear()
    if await db.is_banned(m.from_user.id):
        await m.answer("⛔ Доступ к боту заблокирован.")
        return
    ref_by = _parse_ref(m.text)
    await db.add_user(m.from_user.id, m.from_user.username, ref_by)
    await m.answer(
        render.welcome(m.from_user.first_name or "друг"),
        parse_mode="HTML",
        reply_markup=keyboards.main_menu(config.is_creator(m.from_user.id)),
    )


@router.callback_query(F.data == "home")
async def cb_home(c: CallbackQuery, state: FSMContext = None):
    if state:
        await state.clear()
    try:
        await c.message.edit_text(
            render.welcome(c.from_user.first_name or "друг"),
            parse_mode="HTML",
            reply_markup=keyboards.main_menu(config.is_creator(c.from_user.id)),
        )
    except Exception:
        await c.message.answer(
            render.welcome(c.from_user.first_name or "друг"),
            parse_mode="HTML",
            reply_markup=keyboards.main_menu(config.is_creator(c.from_user.id)),
        )
    await c.answer()


@router.callback_query(F.data == "check_sub")
async def cb_check_sub(c: CallbackQuery, state: FSMContext = None):


    await cb_home(c, state)


@router.chat_join_request()
async def on_join_request(req: ChatJoinRequest):


    await db.mark_gate_request(req.from_user.id, req.chat.id)
    log = logging.getLogger("subgate")
    log.info("gate join-request from uid=%s in chat=%s → засчитано", req.from_user.id, req.chat.id)


@router.callback_query(F.data == "profile")
async def cb_profile(c: CallbackQuery):
    sub = await db.get_subscription(c.from_user.id)
    claims = await db.claim_count(c.from_user.id)
    await c.message.edit_text(
        render.profile_text(c.from_user.id, c.from_user.username, sub, claims),
        parse_mode="HTML",
        reply_markup=keyboards.back_home(),
    )
    await c.answer()


@router.callback_query(F.data == "subscriptions")
async def cb_subs(c: CallbackQuery):
    await c.message.edit_text(
        render.tariffs_text(), parse_mode="HTML", reply_markup=keyboards.tariffs())
    await c.answer()


@router.callback_query(F.data.startswith("buy:"))
async def cb_buy(c: CallbackQuery):

    code = c.data.split(":", 1)[1]
    tariff = config.TARIFFS.get(code)
    if not tariff:
        await c.answer("Неизвестный тариф", show_alert=True)
        return
    label, hours, ton, stars = tariff
    rows = []
    if _cp:
        rows.append([InlineKeyboardButton(text="🤖 CryptoBot", callback_data=f"cbpay:{code}")])
    if config.TONKEEPER_WALLET:
        rows.append([InlineKeyboardButton(text="💎 Tonkeeper", callback_data=f"tkpay:{code}")])
    if not rows:
        await c.answer("Оплата временно недоступна.", show_alert=True)
        return
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="subscriptions")])
    await c.message.edit_text(
        f"💎 <b>Тариф «{label}»</b>\n\n"
        f"Сумма: <b>{ton} TON</b>\n\n"
        "Выбери способ оплаты:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await c.answer()


@router.callback_query(F.data.startswith("cbpay:"))
async def cb_pay_crypto(c: CallbackQuery):
    code = c.data.split(":", 1)[1]
    tariff = config.TARIFFS.get(code)
    if not tariff:
        await c.answer("Неизвестный тариф", show_alert=True)
        return
    if not _cp:
        await c.answer("Оплата временно недоступна (нет CRYPTOBOT_TOKEN).", show_alert=True)
        return
    label, hours, ton, stars = tariff
    try:
        inv = await _cp.create_invoice(
            asset="TON", amount=ton,
            description=f"Gift Tracker — подписка «{label}»",
            payload=f"{c.from_user.id}:{code}")
    except Exception as e:
        await c.answer(f"Не удалось создать счёт: {e}", show_alert=True)
        return
    pid = await db.create_payment(c.from_user.id, str(inv.invoice_id), hours, code)
    await c.message.answer(
        f"💳 <b>Оплата тарифа «{label}»</b>\n\n"
        f"Сумма: <b>{ton} TON</b>\n"
        "Оплати по кнопке, затем нажми «Проверить оплату» — доступ откроется автоматически.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить", url=inv.bot_invoice_url)],
            [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=f"chk:{pid}")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="subscriptions")],
        ]))
    await c.answer()


@router.callback_query(F.data.startswith("chk:"))
async def cb_check(c: CallbackQuery, bot: Bot):
    pid = int(c.data.split(":", 1)[1])
    p = await db.get_payment(pid)
    if not p or p["user_id"] != c.from_user.id:
        await c.answer("Платёж не найден", show_alert=True)
        return
    if p["status"] == "paid":
        await c.answer("Уже активировано", show_alert=True)
        return
    if not _cp:
        await c.answer("Оплата недоступна", show_alert=True)
        return
    invs = await _cp.get_invoices(invoice_ids=int(p["invoice_id"]))
    inv = invs[0] if isinstance(invs, list) else invs
    if inv and inv.status == "paid":
        if await db.mark_payment_paid(pid):
            await db.grant_subscription(c.from_user.id, p["hours"], "paid")
        invite = await _invite_link(bot)
        kb = keyboards.access_button(invite) if invite else keyboards.back_home()
        await c.message.edit_text(
            "✅ <b>Подписка активирована!</b>\n\nДоступ к листингам открыт.",
            reply_markup=kb)
        await c.answer("Готово")
    else:
        await c.answer("Оплата ещё не поступила. Если оплатил — подожди минуту и проверь снова.",
                       show_alert=True)


@router.callback_query(F.data.startswith("tkpay:"))
async def cb_pay_tonkeeper(c: CallbackQuery):
    code = c.data.split(":", 1)[1]
    tariff = config.TARIFFS.get(code)
    if not tariff:
        await c.answer("Неизвестный тариф", show_alert=True)
        return
    if not config.TONKEEPER_WALLET:
        await c.answer("Оплата через Tonkeeper недоступна.", show_alert=True)
        return
    import tonkeeper
    label, hours, ton, stars = tariff
    now = int(time.time())

    pid = await db.create_payment(c.from_user.id, "", hours, code)
    uname = (c.from_user.username or "").lstrip("@")
    comment = f"payed{pid}" + (f"-{uname}" if uname else "")
    await db.set_payment_invoice(pid, comment)
    address = await tonkeeper.resolve_ton_dns(config.TONKEEPER_WALLET)
    expires_at = now + config.TONKEEPER_EXPIRY
    link = tonkeeper.generate_link(address, ton, comment, expires_at)
    mins = config.TONKEEPER_EXPIRY // 60
    await c.message.edit_text(
        f"💎 <b>Оплата через Tonkeeper</b>\n\n"
        f"Тариф: «{label}»\n"
        f"Сумма: <b>{ton} TON</b>\n\n"
        "Переведи точную сумму на кошелёк, <b>обязательно</b> указав комментарий.\n\n"
        f"Кошелёк:\n<code>{config.TONKEEPER_WALLET}</code>\n\n"
        f"Комментарий (memo):\n<code>{comment}</code>\n\n"
        f"⏳ Счёт активен {mins} мин. После оплаты нажми «Проверить оплату».",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💎 Оплатить в Tonkeeper", url=link)],
            [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=f"tkchk:{pid}")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="subscriptions")],
        ]))
    await c.answer()


@router.callback_query(F.data.startswith("tkchk:"))
async def cb_check_tonkeeper(c: CallbackQuery, bot: Bot):
    pid = int(c.data.split(":", 1)[1])
    p = await db.get_payment(pid)
    if not p or p["user_id"] != c.from_user.id:
        await c.answer("Платёж не найден", show_alert=True)
        return
    if p["status"] == "paid":
        await c.answer("Уже активировано", show_alert=True)
        return
    tariff = config.TARIFFS.get(p["tariff"])
    if not tariff:
        await c.answer("Тариф не найден", show_alert=True)
        return
    import tonkeeper
    ton = tariff[2]
    comment = p["invoice_id"]
    address = await tonkeeper.resolve_ton_dns(config.TONKEEPER_WALLET)
    expected_nano = int(round(ton * 1e9))
    paid = await tonkeeper.check_payment(address, comment, expected_nano, int(p["created_at"]))
    if paid:
        if await db.mark_payment_paid(pid):
            await db.grant_subscription(c.from_user.id, p["hours"], "paid")
        invite = await _invite_link(bot)
        kb = keyboards.access_button(invite) if invite else keyboards.back_home()
        await c.message.edit_text(
            "✅ <b>Подписка активирована!</b>\n\nДоступ к листингам открыт.",
            parse_mode="HTML", reply_markup=kb)
        await c.answer("Готово")
    else:
        await c.answer("Оплата ещё не поступила. Если перевёл — подожди минуту "
                       "(транзакция должна попасть в блокчейн) и проверь снова.",
                       show_alert=True)


@router.callback_query(F.data == "referral")
async def cb_ref(c: CallbackQuery):
    me = await c.bot.get_me()
    link = f"https://t.me/{me.username}?start=ref_{c.from_user.id}"
    invited = await db.referral_stats(c.from_user.id)
    await c.message.edit_text(
        render.referral_text(link, invited),
        parse_mode="HTML",
        reply_markup=keyboards.back_home(),
        disable_web_page_preview=True,
    )
    await c.answer()


@router.callback_query(F.data == "trial")
async def cb_trial(c: CallbackQuery):
    if await db.has_used_trial(c.from_user.id):
        await c.answer("Триал уже был использован.", show_alert=True)
        return
    await c.message.edit_text(
        render.RULES, parse_mode="HTML", reply_markup=keyboards.trial_rules())
    await c.answer()


@router.callback_query(F.data == "decline_trial")
async def cb_decline(c: CallbackQuery):
    await cb_home(c)


@router.callback_query(F.data == "accept_trial")
async def cb_accept(c: CallbackQuery):
    import datetime
    if await db.has_used_trial(c.from_user.id):
        await c.answer("Триал уже был использован.", show_alert=True)
        return
    expires = await db.grant_subscription(c.from_user.id, config.TRIAL_HOURS, "trial")
    exp = datetime.datetime.utcfromtimestamp(expires).strftime("%d.%m.%Y %H:%M UTC")
    invite = await _invite_link(c.bot)
    text = (
        "✅ <b>Пробный доступ активирован!</b>\n\n"
        f"Доступ действует до {exp}.\n"
        "Нажми кнопку ниже, чтобы перейти к листингам."
    )
    if invite:
        await c.message.edit_text(text, parse_mode="HTML",
                                  reply_markup=keyboards.access_button(invite))
    else:
        await c.message.edit_text(
            text + "\n\n⚠️ (демо: LOG_CHAT_ID не задан — ссылка недоступна)",
            parse_mode="HTML", reply_markup=keyboards.back_home())
    await c.answer()


async def _invite_link(bot: Bot):
    if config.INVITE_URL:
        return config.INVITE_URL
    if not config.FORUM_CHAT:
        return None
    try:
        link = await bot.create_chat_invite_link(
            config.FORUM_CHAT, member_limit=1, name="trial")
        return link.invite_link
    except Exception:
        return None


@router.callback_query(F.data.startswith("listing_claim:"))
async def cb_claim(c: CallbackQuery):
    claim_key = c.data.split(":", 1)[1]
    sub = await db.get_subscription(c.from_user.id)
    if not sub and c.from_user.id not in config.ADMIN_IDS:
        await c.answer("⛔ Нужна активная подписка/триал, чтобы занимать лоты.",
                       show_alert=True)
        return

    original_card = c.message.html_text or c.message.text or ""
    base, _, tail = claim_key.rpartition("-")
    is_instance = bool(base) and tail.isdigit()
    if not is_instance:
        base = claim_key
    item_slug = claim_key if is_instance else None
    title, fstars, fton = None, 0, 0
    try:
        col = await live_feed.collection_by_slug(base)
        if col:
            title = col.get("title")
            fstars = col.get("floor_stars") or 0
            fton = col.get("floor_ton") or 0
        else:
            pg = await live_feed.peek_gift_by_name(base)
            if pg:
                title = base
                fton = pg.get("price_ton") or 0
    except Exception:
        pass
    title = title or base
    ok, owner = await db.try_claim(claim_key, c.from_user.id, title, fstars, fton, item_slug,
                                   card_text=original_card)
    if not ok:
        await c.answer("Ты уже занял этот лот." if owner == c.from_user.id else "Уже в работе.",
                       show_alert=True)
        return

    uname = c.from_user.username
    tag = f"@{uname}" if uname else (c.from_user.full_name or f"id{c.from_user.id}")
    owner_user = None
    try:
        owner_user = await live_feed.unlock_owner(item_slug) if item_slug else None
    except Exception:
        pass


    try:
        await c.bot.send_message(
            c.from_user.id, original_card, parse_mode="HTML",
            reply_markup=keyboards.claimed_dm_kb(owner_user, item_slug),
            disable_web_page_preview=True)
    except Exception:
        await db.release_claim(claim_key, c.from_user.id)
        await c.answer("Сначала открой бота в личке.", show_alert=True)
        return

    try:
        await c.message.edit_text(
            render.taken_card(tag), parse_mode="HTML",
            reply_markup=keyboards.listing_taken(claim_key, c.from_user.id),
            disable_web_page_preview=True)
    except Exception as ex:
        logging.warning("claim edit failed: %s", ex)
    await c.answer("Взято")


@router.callback_query(F.data.startswith("listing_release:"))
async def cb_release(c: CallbackQuery):


    try:
        _, claim_key, owner_raw = c.data.split(":", 2)
        owner_id = int(owner_raw)
    except ValueError:
        await c.answer("Битая кнопка.", show_alert=True)
        return
    is_admin = c.from_user.id in config.ADMIN_IDS
    if c.from_user.id != owner_id and not is_admin:
        await c.answer("Отменить может только тот, кто занял.", show_alert=True)
        return
    released, card_text = await db.release_claim(claim_key, c.from_user.id, is_admin)
    if not released:
        await c.answer("Лот уже свободен или занят не тобой.", show_alert=True)
        return

    base, _, tail = claim_key.rpartition("-")
    item_slug = claim_key if (bool(base) and tail.isdigit()) else None
    seller_user = None
    try:
        seller_user = await live_feed.unlock_owner(item_slug) if item_slug else None
    except Exception:
        pass
    restored = card_text or f"{render.pe(render.MENU['lock'])} Лот снова свободен"
    try:
        await c.message.edit_text(
            restored, parse_mode="HTML",
            reply_markup=keyboards.listing_card(claim_key, seller_user=seller_user,
                                                item_slug=item_slug),
            disable_web_page_preview=True)
    except Exception as ex:
        logging.warning("release edit failed: %s", ex)
    await c.answer("Отменено")


@router.callback_query(F.data == "noop")
async def cb_noop(c: CallbackQuery):
    await c.answer()


@router.message(Command("demo"))
async def cmd_demo(m: Message):

    if m.from_user.id not in config.ADMIN_IDS:
        return
    from sources.demo_feed import make_listing
    listing = make_listing()
    await db.mark_seen(listing["slug"])
    target = config.LOG_CHAT_ID or m.chat.id
    await m.bot.send_message(
        target, render.listing_card(listing), parse_mode="HTML",
        reply_markup=keyboards.listing_card(listing["slug"], listing["seller_user"]),
        disable_web_page_preview=True,
    )
    await m.answer("✅ Демо-листинг отправлен.")


@router.message(Command("swap"))
async def cmd_swap(m: Message, bot: Bot):

    if not config.is_creator(m.from_user.id):
        return
    import swap
    await m.answer("⏳ Запускаю своп TON → USDT…")
    result = await swap.do_swap(bot)
    await m.answer(result)


@router.callback_query(F.data == "adm")
async def cb_adm(c: CallbackQuery, state: FSMContext):
    if c.from_user.id not in config.ADMIN_IDS:
        await c.answer("Только админ.", show_alert=True)
        return
    await state.clear()
    await c.message.edit_text(await _admin_text(), parse_mode="HTML",
                              reply_markup=keyboards.admin_panel())
    await c.answer()


@router.message(Command("admin"))
async def cmd_admin(m: Message):
    if m.from_user.id not in config.ADMIN_IDS:
        return
    await m.answer(await _admin_text(), parse_mode="HTML", reply_markup=keyboards.admin_panel())


async def _admin_text() -> str:
    total = await db.count_users()
    return (
        f"🛠 <b>Админ-панель Gift Tracker</b>\n\n"
        f"👥 Пользователей: <b>{total}</b>\n\n"
        f"Управление подписками, пользователями и рассылкой — кнопки ниже."
    )


@router.callback_query(F.data == "adm:bcast")
async def cb_adm_bcast(c: CallbackQuery, state: FSMContext):
    if c.from_user.id not in config.ADMIN_IDS:
        return
    await state.set_state(St.bcast)
    await c.message.answer("📢 Пришли текст рассылки (HTML). Отправлю всем пользователям бота.")
    await c.answer()


@router.message(St.bcast, F.text)
async def st_bcast(m: Message, state: FSMContext, bot: Bot):
    if m.from_user.id not in config.ADMIN_IDS:
        await state.clear(); return

    await state.update_data(bcast_text=m.html_text)
    try:
        await bot.send_message(m.chat.id, m.html_text, parse_mode="HTML")
    except Exception as ex:
        await m.answer(f"⚠️ Не удалось отрисовать предпросмотр: {ex}\n"
                       f"Проверь HTML-разметку и пришли текст рассылки заново.")
        return
    await m.answer(
        "📌 <b>Предпросмотр.</b> Так рассылку увидят пользователи.\n\nОтправить?",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Отправить", callback_data="adm:bcast_send"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="adm:bcast_cancel"),
        ]]),
    )


@router.callback_query(F.data == "adm:bcast_send")
async def cb_bcast_send(c: CallbackQuery, state: FSMContext, bot: Bot):
    if c.from_user.id not in config.ADMIN_IDS:
        await c.answer("Нет доступа", show_alert=True); return
    data = await state.get_data()
    text = data.get("bcast_text")
    await state.clear()
    if not text:
        await c.answer("Текст рассылки не найден, начни заново.", show_alert=True)
        return
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    ids = await db.all_user_ids()
    sent = 0
    for uid in ids:
        try:
            await bot.send_message(uid, text, parse_mode="HTML")
            sent += 1
        except Exception:
            pass
    await c.message.answer(f"📢 Рассылка отправлена: {sent}/{len(ids)}",
                           reply_markup=keyboards.admin_panel())
    await c.answer()


@router.callback_query(F.data == "adm:bcast_cancel")
async def cb_bcast_cancel(c: CallbackQuery, state: FSMContext):
    if c.from_user.id not in config.ADMIN_IDS:
        await c.answer("Нет доступа", show_alert=True); return
    await state.clear()
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await c.message.answer("❌ Рассылка отменена.", reply_markup=keyboards.admin_panel())
    await c.answer()


async def _resolve_uid(token: str) -> int | None:

    token = (token or "").strip()
    if not token:
        return None
    if token.lstrip("-").isdigit():
        return int(token)
    return await db.user_id_by_username(token)


@router.callback_query(F.data == "adm:give")
async def cb_adm_give(c: CallbackQuery, state: FSMContext):
    if c.from_user.id not in config.ADMIN_IDS:
        return
    await state.set_state(St.give)
    await c.message.answer(
        "🎁 Введи <code>ID/@username часы</code> — кому и на сколько выдать подписку.\n\n"
        "Примеры:\n"
        "• <code>6059673725 720</code> — 30 дней\n"
        "• <code>@un1quexd 24</code> — 1 день\n\n"
        "Можно переслать/реплайнуть сообщение юзера — тогда просто пришли часы числом.",
        parse_mode="HTML")
    await c.answer()


@router.message(St.give, F.text)
async def st_give(m: Message, state: FSMContext, bot: Bot):
    import datetime
    if m.from_user.id not in config.ADMIN_IDS:
        await state.clear(); return
    parts = m.text.split()
    try:
        if m.reply_to_message and m.reply_to_message.from_user and len(parts) == 1:
            uid = m.reply_to_message.from_user.id
            hours = int(parts[0])
        else:
            uid = await _resolve_uid(parts[0])
            hours = int(parts[1])
        assert hours > 0
    except (ValueError, IndexError, AssertionError):
        await m.answer("⚠️ Формат: <code>ID/@username часы</code> "
                       "(например <code>@un1quexd 720</code>)", parse_mode="HTML")
        return
    if uid is None:
        await m.answer(f"⚠️ Юзер <code>{parts[0]}</code> не найден в базе "
                       "(он должен был хоть раз запустить бота). Попробуй по ID.",
                       parse_mode="HTML")
        return
    await state.clear()
    expires = await db.grant_subscription(uid, hours, "paid")
    exp = datetime.datetime.utcfromtimestamp(expires).strftime("%d.%m.%Y %H:%M UTC")
    invite = await _invite_link(bot)
    notified = False
    try:
        kb = keyboards.access_button(invite) if invite else keyboards.back_home()
        await bot.send_message(
            uid,
            f"🎁 <b>Тебе выдана подписка Gift Tracker!</b>\n\n"
            f"Действует до {exp}.\nДоступ к листингам открыт.",
            parse_mode="HTML", reply_markup=kb)
        notified = True
    except Exception:
        pass
    await m.answer(
        f"✅ Подписка выдана <code>{uid}</code> на {hours}ч (до {exp}).\n"
        + ("📧 Юзер уведомлён + инвайт отправлен." if notified
           else "⚠️ Не смог написать юзеру (не запускал бота) — доступ выдан, "
                "инвайт скинь вручную."),
        parse_mode="HTML", reply_markup=keyboards.admin_panel())


@router.callback_query(F.data == "adm:revoke")
async def cb_adm_revoke(c: CallbackQuery, state: FSMContext):
    if c.from_user.id not in config.ADMIN_IDS:
        return
    await state.set_state(St.revoke)
    await c.message.answer(
        "🚫 Пришли <code>ID</code> или <code>@username</code> юзера, у кого снять подписку "
        "(или реплай на его сообщение).\n\n"
        "Подписка удалится, юзер будет кикнут из канала.",
        parse_mode="HTML")
    await c.answer()


@router.message(St.revoke, F.text)
async def st_revoke(m: Message, state: FSMContext, bot: Bot):
    if m.from_user.id not in config.ADMIN_IDS:
        await state.clear(); return
    if m.reply_to_message and m.reply_to_message.from_user:
        uid = m.reply_to_message.from_user.id
    else:
        token = m.text.split()[0] if m.text.split() else ""
        uid = await _resolve_uid(token)
        if uid is None:
            await m.answer(f"⚠️ Юзер <code>{token}</code> не найден. "
                           "Пришли ID/@username или реплай на сообщение юзера.",
                           parse_mode="HTML")
            return
    await state.clear()
    removed = await db.revoke_subscription(uid)
    kicked = False
    if config.FORUM_CHAT:
        try:
            await bot.ban_chat_member(config.FORUM_CHAT, uid)
            await bot.unban_chat_member(config.FORUM_CHAT, uid)
            kicked = True
        except Exception:
            pass
    try:
        await bot.send_message(
            uid, "🚫 Твоя подписка Gift Tracker снята администратором.",
            reply_markup=keyboards.renew_sub())
    except Exception:
        pass
    await m.answer(
        (f"✅ Подписка снята у <code>{uid}</code>." if removed
         else f"ℹ️ У <code>{uid}</code> активной подписки не было.")
        + ("\n🚪 Кикнут из супергруппы." if kicked else "\n⚠️ Из супергруппы не кикнут (нет прав/FORUM_CHAT)."),
        parse_mode="HTML", reply_markup=keyboards.admin_panel())


async def _user_card_text(uid: int) -> str:
    import datetime
    uname = await db.get_username(uid)
    sub = await db.get_subscription(uid)
    wst = await db.worker_status(uid)
    if sub:
        exp = datetime.datetime.utcfromtimestamp(sub["expires_at"]).strftime("%d.%m.%Y %H:%M UTC")
        sub_line = f"✅ активна ({sub['kind']}) до {exp}"
    else:
        sub_line = "— нет"
    wmap = {"approved": "✅ рабочий", "pending": "⏳ заявка на рассмотрении",
            "rejected": "❌ отклонён/снят"}
    handle = f"@{uname}" if uname else "—"
    claims = await db.claim_count(uid)
    banned = await db.is_banned(uid)
    pays = len(await db.user_payments(uid, limit=50))
    return (f"👤 <b>Управление юзером</b>\n\n"
            f"ID: <code>{uid}</code>\n"
            f"Username: {handle}\n"
            + ("🚫 <b>ЗАБАНЕН</b>\n" if banned else "")
            + f"Подписка: {sub_line}\n"
            f"Статус рабочего: {wmap.get(wst, '— не рабочий')}\n"
            f"Занятых лотов: {claims} · платежей: {pays}")


async def _render_card(msg, uid: int, edit: bool = True):
    has_sub = bool(await db.get_subscription(uid))
    wst = await db.worker_status(uid)
    banned = await db.is_banned(uid)
    txt = await _user_card_text(uid)
    kb = keyboards.user_card(uid, has_sub, wst, banned)
    try:
        await (msg.edit_text if edit else msg.answer)(txt, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await msg.answer(txt, parse_mode="HTML", reply_markup=kb)


async def _do_grant(bot: Bot, uid: int, hours: int):
    import datetime
    expires = await db.grant_subscription(uid, hours, "paid")
    exp = datetime.datetime.utcfromtimestamp(expires).strftime("%d.%m.%Y %H:%M UTC")
    invite = await _invite_link(bot)
    notified = False
    try:
        kb = keyboards.access_button(invite) if invite else keyboards.back_home()
        await bot.send_message(
            uid,
            f"🎁 <b>Тебе выдана подписка Gift Tracker!</b>\n\n"
            f"Действует до {exp}.\nДоступ к листингам открыт.",
            parse_mode="HTML", reply_markup=kb)
        notified = True
    except Exception:
        pass
    return exp, notified


@router.callback_query(F.data == "adm:user")
async def cb_adm_user(c: CallbackQuery, state: FSMContext):
    if c.from_user.id not in config.ADMIN_IDS:
        return
    await state.set_state(St.user_lookup)
    await c.message.answer(
        "👤 Пришли <code>ID</code> или <code>@username</code> юзера "
        "(или реплай на его сообщение) — открою карточку управления.",
        parse_mode="HTML")
    await c.answer()


@router.message(St.user_lookup, F.text)
async def st_user_lookup(m: Message, state: FSMContext):
    if m.from_user.id not in config.ADMIN_IDS:
        await state.clear(); return
    if m.reply_to_message and m.reply_to_message.from_user:
        uid = m.reply_to_message.from_user.id
    else:
        token = m.text.split()[0] if m.text.split() else ""
        uid = await _resolve_uid(token)
        if uid is None:

            matches = await db.search_users(token)
            if matches:
                await state.clear()
                await m.answer(
                    f"🔎 Найдено по «{token}» — выбери юзера:",
                    reply_markup=keyboards.search_results(matches))
                return
            await m.answer(f"⚠️ Юзер <code>{token}</code> не найден. "
                           "Пришли ID/@username, часть ника или реплай на сообщение.",
                           parse_mode="HTML")
            return
    await state.clear()
    await _render_card(m, uid, edit=False)


@router.callback_query(F.data.startswith("adm:list"))
async def cb_adm_list(c: CallbackQuery, state: FSMContext):
    if c.from_user.id not in config.ADMIN_IDS:
        return
    await state.clear()
    per = 8
    parts = c.data.split(":")
    page = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
    total = await db.count_users()
    rows = await db.list_users(page * per, per)
    pages = max(1, (total + per - 1) // per)
    txt = (f"👥 <b>Список юзеров</b> · всего {total}\n"
           f"Страница {page + 1}/{pages} — жми на юзера для управления.")
    kb = keyboards.users_list(rows, page, total, per)
    try:
        await c.message.edit_text(txt, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await c.message.answer(txt, parse_mode="HTML", reply_markup=kb)
    await c.answer()


@router.callback_query(F.data.startswith("um:card:"))
async def cb_um_card(c: CallbackQuery):
    if c.from_user.id not in config.ADMIN_IDS:
        return
    await _render_card(c.message, int(c.data.split(":")[2]))
    await c.answer()


@router.callback_query(F.data.startswith("um:givemenu:"))
async def cb_um_givemenu(c: CallbackQuery):
    if c.from_user.id not in config.ADMIN_IDS:
        return
    uid = int(c.data.split(":")[2])
    await c.message.edit_text(
        f"🎁 На сколько выдать подписку юзеру <code>{uid}</code>?",
        parse_mode="HTML", reply_markup=keyboards.give_menu(uid))
    await c.answer()


@router.callback_query(F.data.startswith("um:givecustom:"))
async def cb_um_givecustom(c: CallbackQuery, state: FSMContext):
    if c.from_user.id not in config.ADMIN_IDS:
        return
    uid = int(c.data.split(":")[2])
    await state.set_state(St.give_custom)
    await state.update_data(uid=uid)
    await c.message.answer(
        f"✏️ Введи число часов для юзера <code>{uid}</code> (например <code>720</code>):",
        parse_mode="HTML")
    await c.answer()


@router.message(St.give_custom, F.text)
async def st_give_custom(m: Message, state: FSMContext, bot: Bot):
    if m.from_user.id not in config.ADMIN_IDS:
        await state.clear(); return
    data = await state.get_data()
    uid = data.get("uid")
    try:
        hours = int(m.text.strip()); assert hours > 0
    except (ValueError, AssertionError):
        await m.answer("⚠️ Введи положительное число часов."); return
    await state.clear()
    exp, notified = await _do_grant(bot, uid, hours)
    await m.answer(
        f"✅ Подписка выдана <code>{uid}</code> на {hours}ч (до {exp})."
        + ("" if notified else "\n⚠️ Юзер не уведомлён (не запускал бота)."),
        parse_mode="HTML")
    await _render_card(m, uid, edit=False)


@router.callback_query(F.data.startswith("um:give:"))
async def cb_um_give(c: CallbackQuery, bot: Bot):
    if c.from_user.id not in config.ADMIN_IDS:
        return
    _, _, uid, hours = c.data.split(":")
    uid, hours = int(uid), int(hours)
    exp, notified = await _do_grant(bot, uid, hours)
    await c.answer(f"✅ Выдано на {hours}ч (до {exp})"
                   + ("" if notified else " · юзер не уведомлён"), show_alert=True)
    await _render_card(c.message, uid)


@router.callback_query(F.data.startswith("um:subrevoke:"))
async def cb_um_subrevoke(c: CallbackQuery, bot: Bot):
    if c.from_user.id not in config.ADMIN_IDS:
        return
    uid = int(c.data.split(":")[2])
    removed = await db.revoke_subscription(uid)
    kicked = False
    if config.FORUM_CHAT:
        try:
            await bot.ban_chat_member(config.FORUM_CHAT, uid)
            await bot.unban_chat_member(config.FORUM_CHAT, uid)
            kicked = True
        except Exception:
            pass
    try:
        await bot.send_message(
            uid, "🚫 Твоя подписка Gift Tracker снята администратором.",
            reply_markup=keyboards.renew_sub())
    except Exception:
        pass
    await c.answer(("✅ Подписка снята" if removed else "ℹ️ Подписки не было")
                   + (" · кикнут" if kicked else ""), show_alert=True)
    await _render_card(c.message, uid)


async def _history_text(uid: int) -> str:
    import datetime
    pays = await db.user_payments(uid, 10)
    lines = [f"🗒 <b>История</b> — <code>{uid}</code>\n", "<b>Платежи (подписки):</b>"]
    if pays:
        for p in pays:
            d = (datetime.datetime.utcfromtimestamp(p["created_at"]).strftime("%d.%m.%y")
                 if p.get("created_at") else "—")
            lines.append(f"• {d} · {p['hours']}ч · {p['tariff']} · {p['status']}")
    else:
        lines.append("— нет")
    return "\n".join(lines)


@router.callback_query(F.data.startswith("um:history:"))
async def cb_um_history(c: CallbackQuery):
    if c.from_user.id not in config.ADMIN_IDS:
        return
    uid = int(c.data.split(":")[2])
    try:
        await c.message.edit_text(await _history_text(uid), parse_mode="HTML",
                                  reply_markup=keyboards.card_back(uid))
    except Exception:
        await c.message.answer(await _history_text(uid), parse_mode="HTML",
                               reply_markup=keyboards.card_back(uid))
    await c.answer()


@router.callback_query(F.data.startswith("um:ban:"))
async def cb_um_ban(c: CallbackQuery, bot: Bot):
    if c.from_user.id not in config.ADMIN_IDS:
        return
    uid = int(c.data.split(":")[2])
    await db.ban_user(uid, f"admin:{c.from_user.id}")
    kicked = False
    if config.FORUM_CHAT:
        try:
            await bot.ban_chat_member(config.FORUM_CHAT, uid)
            kicked = True
        except Exception:
            pass
    try:
        await bot.send_message(uid, "⛔ Доступ к боту заблокирован администратором.")
    except Exception:
        pass
    await c.answer("⛔ Забанен" + (" · выкинут из группы" if kicked else ""), show_alert=True)
    await _render_card(c.message, uid)


@router.callback_query(F.data.startswith("um:unban:"))
async def cb_um_unban(c: CallbackQuery, bot: Bot):
    if c.from_user.id not in config.ADMIN_IDS:
        return
    uid = int(c.data.split(":")[2])
    ok = await db.unban_user(uid)
    if config.FORUM_CHAT:
        try:
            await bot.unban_chat_member(config.FORUM_CHAT, uid)
        except Exception:
            pass
    await c.answer("🔓 Разбанен" if ok else "ℹ️ Не был забанен", show_alert=True)
    await _render_card(c.message, uid)


@router.callback_query(F.data == "adm:bulk")
async def cb_adm_bulk(c: CallbackQuery, state: FSMContext):
    if c.from_user.id not in config.ADMIN_IDS:
        return
    await state.set_state(St.bulk_give)
    await c.message.answer(
        "📋 <b>Массовая выдача подписки</b>\n\n"
        "Первым числом — <b>часы</b>, дальше ID/@username через пробел или с новой строки.\n\n"
        "Пример:\n<code>720 6059673725 @un1quexd 94381037</code>",
        parse_mode="HTML")
    await c.answer()


@router.message(St.bulk_give, F.text)
async def st_bulk_give(m: Message, state: FSMContext, bot: Bot):
    if m.from_user.id not in config.ADMIN_IDS:
        await state.clear(); return
    toks = m.text.split()
    try:
        hours = int(toks[0]); assert hours > 0
    except (IndexError, ValueError, AssertionError):
        await m.answer("⚠️ Первым — число часов. Пример: <code>720 6059673725 @un1quexd</code>",
                       parse_mode="HTML")
        return
    targets = toks[1:]
    if not targets:
        await m.answer("⚠️ Добавь хотя бы один ID/@username после часов.")
        return
    await state.clear()
    ok, fail = [], []
    for t in targets:
        uid = await _resolve_uid(t)
        if uid is None:
            fail.append(t); continue
        await db.grant_subscription(uid, hours, "paid")
        try:
            await bot.send_message(uid, f"🎁 Тебе выдана подписка Gift Tracker на {hours}ч.")
        except Exception:
            pass
        ok.append(t)
    report = f"✅ Выдано <b>{len(ok)}</b> на {hours}ч."
    if fail:
        report += f"\n⚠️ Не найдены ({len(fail)}): {', '.join(fail)}"
    await m.answer(report, parse_mode="HTML", reply_markup=keyboards.admin_panel())
