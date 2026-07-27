
import config
from emoji_ids import CARD, MENU, UNLOCK


def e(pair) -> str:

    emoji, eid = pair
    if config.USE_PREMIUM_EMOJI:
        return f'<tg-emoji emoji-id="{eid}">{emoji}</tg-emoji>'
    return emoji


def pe(pair) -> str:


    emoji, eid = pair
    return f'<tg-emoji emoji-id="{eid}">{emoji}</tg-emoji>'


def listing_card(l: dict) -> str:
    status = "Premium" if l["premium"] else "без Premium"
    return (
        f"{e(CARD['title'])} <b>НОВЫЙ ЛИСТИНГ</b>\n\n"
        f"{e(CARD['gift'])} Гифт: <b>{l['gift']}</b>\n"
        f"{e(CARD['price'])} Цена: <b>{l['price_stars']} ⭐️ / {l['price_ton']} TON</b>\n"
        f"{e(CARD['model'])} Модель: {l['model']}\n"
        f"{e(CARD['seller'])} Продавец: @{l['seller_user']} (<code>{l['seller_id']}</code>)\n"
        f"{e(CARD['level'])} Level: {l['level']}\n"
        f"{e(CARD['dm'])} Сообщения: {l['dm']}\n"
        f"{e(CARD['status'])} Статус: {status}\n"
        f"{e(CARD['slug'])} {l['slug']}\n"
        f"{e(CARD['time'])} {l['ts']}\n\n"
        f"<i>Created by @cutkeep</i>"
    )


_HR = "━━━━━━━━━━━━━"


def live_card(l: dict) -> str:

    unlock = l.get("unlock_in_min") is not None
    drop = l["kind"] == "floor_drop"
    head = ("🔓 <b>НОВЫЙ РАЗЛОК</b>" if unlock
            else "🔽 <b>ПАДЕНИЕ ФЛОРА</b>" if drop
            else "🆕 <b>НОВЫЙ ЛИСТИНГ</b>")
    name = l.get("item_slug") or l["gift"]
    lines = [head, _HR, f"🎁 <b>{name}</b>", ""]
    if l.get("unlock_in_min") is not None:
        m = l["unlock_in_min"]
        left = f"~{m} мин" if m >= 1 else "менее 1 мин"
        lines.append(f"⏳ До разлока: <b>{left}</b>")
    ton = f" · <b>{l['price_ton']}</b> TON" if l.get("price_ton") else ""
    lines.append(f"🪙 Флор: <b>{l['price_stars']} ⭐</b>{ton}")
    if drop and l.get("old_floor"):
        old = l["old_floor"]
        pct = round((old - l["price_stars"]) / old * 100) if old else 0
        lines.append(f"📊 Было <s>{old} ⭐</s> → стало <b>{l['price_stars']} ⭐</b>  (−{pct}%)")
    if l.get("supply"):
        lines.append(f"📦 Саплай: <b>{l['supply']:,}</b> · в ресейле: <b>{l['resale']}</b>")
    if l.get("seller_user"):
        lines.append(f"👤 Владелец: <b>@{l['seller_user']}</b>")
    lines.append(f"📶 Источник: <b>{l.get('source') or 'Telegram Маркет'}</b>")
    lines.append(f"🕓 {l['ts']}")
    lines.append(_HR)
    return "\n".join(lines)


def unlock_card(l: dict) -> str:

    import html as _html
    name = _html.escape(str(l.get("item_slug") or l["gift"]))
    m = l.get("unlock_in_min")
    left = ("—" if m is None else (f"~{m} мин" if m >= 1 else "менее 1 мин"))
    lines = [
        f"{pe(UNLOCK['lock'])} <b>НОВЫЙ РАЗЛОК</b>",
        _HR,
        f"{pe(UNLOCK['gift'])} <b>{name}</b>",
        f"{pe(UNLOCK['hourglass'])} До разлока: <b>{left}</b>",
        f"{pe(UNLOCK['coin'])} Флор: <b>{l.get('price_stars') or 0} {pe(UNLOCK['star'])}</b>",
        f"{pe(UNLOCK['signal'])} Источник: <b>{l.get('source') or 'peek.tg'}</b>",
        f"{pe(UNLOCK['clock'])} {l['ts']}",
        _HR,
    ]
    return "\n".join(lines)


def peek_card(c: dict) -> str:

    sub = c.get("gift_name") or ""
    if c.get("model_name"):
        sub += (" · " if sub else "") + c["model_name"]
    lines = [
        "🛡 <b>PEEK.TG · НОВАЯ КОЛЛЕКЦИЯ</b>", _HR,
        f"🎁 <b>{c.get('name') or 'Коллекция'}</b>",
    ]
    if sub:
        lines.append(f"📝 {sub}")
    if c.get("items_count"):
        lines.append(f"📦 Предметов: <b>{c['items_count']:,}</b>")
    lines.append(f"📶 Источник: <b>peek.tg</b>")
    lines.append(_HR)
    lines.append("⚡ <b>Gift Tracker</b> · мониторинг коллекций")
    return "\n".join(lines)


def peek_drop_card(g: dict) -> str:

    lines = [
        f"{pe(MENU['green'])} <b>PEEK.TG · ПОДАРОК ДОСТУПЕН</b>", _HR,
        f"{pe(CARD['gift'])} <b>{g.get('name') or 'Gift'}</b>",
    ]
    if g.get("price_ton"):
        floor = g.get("floor_nofee") or g["price_ton"]
        lines.append(f"{pe(CARD['price'])} Флор: <b>{g['price_ton']}</b> TON  (без ком.: {floor})")
    if g.get("change") is not None:
        ch = g["change"]
        lines.append(f"{pe(CARD['level'])} За 24ч: <b>{ch:+.2f}%</b>")
    if g.get("total"):
        lines.append(f"📦 Саплай: <b>{g['total']:,}</b> · выпущено: <b>{g.get('issued') or 0:,}</b>")
    lines.append(f"{pe(CARD['dm'])} Источник: <b>peek.tg</b> · live")
    lines.append(_HR)
    return "\n".join(lines)


def peek_mover_card(g: dict) -> str:

    ch = g.get("change") or 0
    up = ch >= 0
    head = (f"{pe(MENU['party'])} <b>PEEK.TG · РОСТ ФЛОРА</b>" if up
            else f"{pe(MENU['diamond'])} <b>PEEK.TG · СЛИВ ФЛОРА</b>")
    lines = [head, _HR, f"{pe(CARD['gift'])} <b>{g.get('name') or 'Gift'}</b>", ""]
    if g.get("price_ton"):
        lines.append(f"{pe(CARD['price'])} Флор: <b>{g['price_ton']}</b> TON")
    lines.append(f"{pe(CARD['level'])} Изменение 24ч: <b>{ch:+.2f}%</b>")
    if g.get("total"):
        lines.append(f"📦 Саплай: <b>{g['total']:,}</b> · выпущено: <b>{g.get('issued') or 0:,}</b>")
    if g.get("available"):
        lines.append(f"{pe(MENU['green'])} Сейчас доступен к покупке")
    lines.append(_HR)
    lines.append(f"{pe(MENU['bolt'])} <b>Gift Tracker</b> · сигнал по флору")
    return "\n".join(lines)


def taken_card(worker_tag: str) -> str:

    return f"{pe(MENU['lock'])} <b>Данный лог занят</b>\n\nВзято: {worker_tag}"


def claimed_dm(gift_title: str, slug: str, item_slug: str | None = None,
               owner_user: str | None = None) -> str:

    lines = [
        f"{pe(MENU['green'])} <b>Ты занял лот!</b>", _HR,
        f"{pe(CARD['gift'])} Лот: <b>{gift_title or slug}</b>",
    ]
    if item_slug:
        lines.append(f"{pe(CARD['slug'])} Инстанс: <code>{item_slug}</code>")
    if owner_user:
        lines.append(f"{pe(CARD['seller'])} Владелец: <b>@{owner_user}</b>")
    lines.append(_HR)
    lines.append(
        f"{pe(MENU['bolt'])} Лот закреплён за тобой. Открой «Панель рабочего», "
        f"забери NFT-подарок и сдай его на выплату.")
    return "\n".join(lines)


def welcome(name: str) -> str:
    return (
        f"{e(MENU['home'])} <b>Добро пожаловать, {name}!</b>\n\n"
        f"{e(MENU['gift_home'])} Этот бот трекает ресейл NFT-подарков и присылает "
        f"горячие лоты первым подписчикам.\n\n"
        f"{e(MENU['bolt'])} Жми кнопки ниже:"
    )


def tariffs_text() -> str:
    lines = [f"{pe(MENU['diamond'])} <b>Тарифы</b>\n"]
    for _, (label, _h, ton, stars) in config.TARIFFS.items():
        lines.append(f"{pe(MENU['clock'])} {label} — {ton} {pe(MENU['money'])} TON / {stars} {pe(MENU['star'])}")
    lines.append(f"\n{pe(MENU['card'])} Выбери длительность:")
    return "\n".join(lines)


def profile_text(uid, username, sub, claims) -> str:
    import time, datetime
    if sub:
        kind = "🔒 Пробная (Trial)" if sub["kind"] == "trial" else "💎 Платная"
        exp = datetime.datetime.utcfromtimestamp(sub["expires_at"]).strftime("%d.%m.%Y %H:%M UTC")
        status = f"{e(MENU['green'])} Активна"
    else:
        kind, exp, status = "—", "—", "🔴 Неактивна"
    return (
        f"{e(MENU['profile'])} <b>Мой профиль</b>\n\n"
        f"{e(MENU['id'])} ID: <code>{uid}</code>\n"
        f"{e(MENU['profile'])} Username: @{username or '—'}\n\n"
        f"{e(MENU['diamond'])} Статус: {status}\n"
        f"{e(MENU['lock'])} Тип: {kind}\n"
        f"{e(MENU['calendar'])} Истекает: {e(MENU['clock'])} {exp}\n\n"
        f"{e(MENU['chart'])} Занято лотов: {claims}"
    )


def referral_text(link, invited) -> str:
    return (
        f"{e(MENU['party'])} <b>Реферальная программа</b>\n\n"
        f"⭐ Приглашай друзей — получай 1 ч подписки за каждого, кто активирует "
        f"триал или оплатит тариф.\n\n"
        f"{e(MENU['profile'])} Приглашено всего: {invited}\n\n"
        f"{e(MENU['bolt'])} Твоя ссылка:\n{link}"
    )


RULES = (
    "⚠️ <b>Правила использования</b>\n\n"
    "📝 1. Кнопка «Занять» — ТОЛЬКО для тех, кто реально забирает лот. "
    "Ложные клики = бан.\n"
    "📝 2. Передача инвайт-ссылки третьим лицам запрещена.\n"
    "📝 3. Подписка не возвращается (кроме тех. сбоя бота).\n"
    "📝 4. Обход доступа (мультиаккаунты/скрипты) = перманентный бан.\n\n"
    f"⏰ Trial: {config.TRIAL_HOURS} ч., выдаётся один раз.\n\n"
    "Нажимая «Принимаю», ты подтверждаешь, что прочитал правила."
)


_PSTATUS = {
    "awaiting": "⏰ Ждём гифт",
    "received": "📥 Гифт получен",
    "sold":     "💰 Продано, к выплате",
    "paid":     "✅ Выплачено",
    "rejected": "❌ Отклонено",
}


def worker_panel_text(w, claims, payouts) -> str:
    earned = (w or {}).get("earned_ton", 0) or 0
    cnt = (w or {}).get("payouts", 0) or 0
    active = [p for p in payouts if p["status"] in ("awaiting", "received", "sold")]
    lines = [
        f"💼 <b>Панель рабочего</b>\n",
        f"💎 Заработано всего: <b>{earned} TON</b>",
        f"✅ Закрытых выплат: <b>{cnt}</b>",
        f"📦 Занято лотов: <b>{len(claims)}</b>",
        f"🔥 Активных заявок: <b>{len(active)}</b>\n",
    ]
    if active:
        lines.append("<b>Активные заявки:</b>")
        for p in active[:8]:
            payout = f" → <b>{p['payout_ton']} TON</b>" if p["status"] == "sold" else ""
            lines.append(f"• #{p['id']} {p['gift_title'] or p['slug']} — {_PSTATUS.get(p['status'], p['status'])}{payout}")
        lines.append("")
    lines.append("📥 Чтобы сдать гифт на выплату — выбери занятый лот ниже.")
    return "\n".join(lines)


def payout_fee_text(fee_stars, gift_title) -> str:
    return (
        f"📥 <b>Сдать гифт на выплату</b>\n\n"
        f"🎁 Лот: <b>{gift_title}</b>\n\n"
        f"Чтобы оформить заявку, оплати разовую комиссию <b>{fee_stars} ⭐</b> "
        f"(из них 25 ⭐ уходит на передачу подарка на маркет).\n\n"
        f"После оплаты бот выдаст адрес для передачи подарка и начнёт "
        f"автоматически ждать его поступление."
    )


def payout_instructions_text(req_id, gift_title, receiver, pct) -> str:
    return (
        f"✅ <b>Заявка #{req_id} создана!</b>\n\n"
        f"🎁 Лот: <b>{gift_title}</b>\n\n"
        f"📤 <b>Передай NFT-подарок на аккаунт:</b>\n"
        f"➡️ @{receiver}\n\n"
        f"⚙️ Передавай <b>с того же аккаунта</b>, с которого работаешь в боте — "
        f"бот опознает приход автоматически по твоему ID.\n\n"
        f"💎 После продажи тебе моментально начислят <b>{pct}%</b> от суммы. "
        f"Статус смотри в «Панели рабочего»."
    )


def worker_received_text(req_id, gift_title) -> str:
    return (
        f"📥 <b>Гифт по заявке #{req_id} получен!</b>\n\n"
        f"🎁 {gift_title}\n\n"
        f"Подарок у создателя — ждём продажу. Как только продастся, "
        f"тебе придёт выплата."
    )


def worker_paid_text(req_id, payout_ton, gift_title) -> str:
    return (
        f"💵 <b>Выплата по заявке #{req_id}!</b>\n\n"
        f"🎁 {gift_title}\n"
        f"💎 Начислено: <b>{payout_ton} TON</b>\n\n"
        f"Спасибо за работу 🔥"
    )


def creator_panel_text(s, receiver, pct, fee) -> str:
    return (
        f"🛠 <b>Панель создателя</b>\n\n"
        f"👥 Рабочих: <b>{s['workers']}</b>\n"
        f"⏰ Ждут гифт: <b>{s['awaiting']}</b>\n"
        f"📥 Получено: <b>{s['received']}</b>\n"
        f"💰 Продано (к выплате): <b>{s['sold']}</b>\n"
        f"✅ Выплачено: <b>{s['paid']}</b>\n\n"
        f"📊 Оборот продаж: <b>{s['sales_ton']} TON</b>\n"
        f"💎 Выплачено рабочим: <b>{s['payouts_ton']} TON</b>\n"
        f"⭐ Собрано комиссий: <b>{s['fee_stars']} ⭐</b>\n\n"
        f"📤 Приём гифтов: @{receiver}\n"
        f"⚙️ Доля рабочего: <b>{pct}%</b> · комиссия: <b>{fee} ⭐</b>"
    )


def request_text(p, receiver) -> str:
    lines = [
        f"📄 <b>Заявка #{p['id']}</b> — {_PSTATUS.get(p['status'], p['status'])}\n",
        f"👤 Рабочий: @{p['username'] or '—'} (<code>{p['worker_id']}</code>)",
        f"🎁 Лот: <b>{p['gift_title'] or p['slug']}</b>",
    ]
    if p["floor_stars"]:
        lines.append(f"🪙 Флор на момент заявки: {p['floor_stars']} ⭐ / {p['floor_ton']} TON")
    lines.append(f"⭐ Комиссия: {p['fee_stars']} ⭐")
    if p["status"] in ("sold", "paid"):
        lines.append(f"💰 Продано за: <b>{p['sale_ton']} TON</b>")
        lines.append(f"💎 Доля рабочего ({p['pct']}%): <b>{p['payout_ton']} TON</b>")
    if p["status"] == "rejected" and p.get("note"):
        lines.append(f"📝 Причина: {p['note']}")
    return "\n".join(lines)


_TG = {
    "lock": ('🔒', 6037249452824072506),
    "gem":  ('💎', 5776023601941582822),
    "gift": ('🎁', 5773677501825945508),
    "bell": ('🔔', 6039486778597970865),
}
def _e(key: str) -> str:
    ch, eid = _TG[key]
    return f'<tg-emoji emoji-id="{eid}">{ch}</tg-emoji>'


def sub_expired_text() -> str:
    return (
        f"{_e('lock')} <b>Подписка истекла</b>\n\n"
        f"Ты был удалён из канала. Чтобы вернуться к листингам и сигналам — "
        f"продли подписку {_e('gem')}"
    )


def worker_apply_text() -> str:
    return (
        f"{_e('gift')} <b>Стать рабочим Gift Tracker</b>\n\n"
        "Рабочий занимает лоты из форума сигналов, сдаёт NFT-подарки на приём "
        "и получает свою долю с каждой продажи.\n\n"
        "Доступ к «Панели рабочего» открывается <b>после одобрения заявки</b> создателем.\n"
        "Это занимает немного времени — после одобрения тебе придёт уведомление.\n\n"
        f"{_e('bell')} Нажми «Подать заявку», чтобы отправить запрос."
    )


def worker_pending_text() -> str:
    return (
        f"{_e('bell')} <b>Заявка на рассмотрении</b>\n\n"
        "Твоя заявка отправлена создателю. Как только её одобрят — "
        "«Панель рабочего» откроется автоматически, и придёт уведомление.\n\n"
        "Спасибо за терпение!"
    )


def worker_rejected_text() -> str:
    return (
        f"{_e('lock')} <b>Заявка отклонена</b>\n\n"
        "К сожалению, твою заявку отклонили. Можешь подать её повторно — "
        "возможно, позже наберём ещё рабочих."
    )


def worker_approved_dm() -> str:
    return (
        f"{_e('gem')} <b>Заявка одобрена!</b>\n\n"
        "Доступ к «Панели рабочего» открыт. Заходи в меню → «Панель рабочего», "
        "занимай лоты и зарабатывай."
    )


def new_app_owner_text(uid: int, username: str | None) -> str:
    who = f"@{username}" if username else f"id <code>{uid}</code>"
    return (
        f"{_e('bell')} <b>Новая заявка в рабочие</b>\n\n"
        f"От: {who}\n"
        f"ID: <code>{uid}</code>\n\n"
        "Одобрить доступ к «Панели рабочего»?"
    )
