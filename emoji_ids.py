

CARD = {
    "title":   ("🎉", "6041731551845159060"),
    "gift":    ("🎁", "6032644646587338669"),
    "price":   ("🪙", "5904462880941545555"),
    "model":   ("📝", "5197269100878907942"),
    "seller":  ("👤", "5870994129244131212"),
    "level":   ("📈", "5429651785352501917"),
    "dm":      ("📢", "5260268501515377807"),
    "status":  ("⭐️", "5406812184359507637"),
    "slug":    ("▶️", "5875506366050734240"),
    "time":    ("🕓", "5775896410780079073"),
}

MENU = {
    "profile":   ("👤", "5879770735999717115"),
    "id":        ("🆔", "5936017305585586269"),
    "diamond":   ("💎", "5357571247599275026"),
    "green":     ("🟢", "5427042188993252300"),
    "lock":      ("🔒", "5879895758202735862"),
    "calendar":  ("📅", "5274055917766202507"),
    "clock":     ("⏰", "5778605968208170641"),
    "chart":     ("📊", "5244837092042750681"),
    "party":     ("🎉", "5388846361930124309"),
    "bolt":      ("⚡️", "5877332341331857066"),
    "money":     ("💰", "5406976471153545018"),
    "card":      ("💳", "5927169041595634481"),
    "star":      ("⭐️", "5406812184359507637"),
    "home":      ("🏠", "5967822972931542886"),
    "gift_home": ("🎁", "5963213811597970978"),
}


UNLOCK = {
    "lock":      ("🔓", "5253647062104287098"),
    "gift":      ("🎁", "6032937473162614352"),
    "hourglass": ("⏳", "5451732530048802485"),
    "coin":      ("🪙", "6039802097916974085"),
    "star":      ("⭐", "5893494861612455015"),
    "signal":    ("📶", "5874986954180791957"),
    "clock":     ("🕓", "5776213190387961618"),
}


def e(pair):

    emoji, eid = pair
    return f'<tg-emoji emoji-id="{eid}">{emoji}</tg-emoji>'


def render_card(*, gift, price_stars, price_ton, model, seller_user, seller_id,
                level, dm, premium, slug, ts):

    status = "Premium" if premium else "без Premium"
    return (
        f"{e(CARD['title'])} <b>НОВЫЙ ЛИСТИНГ</b>\n\n"
        f"{e(CARD['gift'])} Гифт: <b>{gift}</b>\n"
        f"{e(CARD['price'])} Цена: <b>{price_stars} ⭐️ / {price_ton} TON</b>\n"
        f"{e(CARD['model'])} Модель: {model}\n"
        f"{e(CARD['seller'])} Продавец: @{seller_user} (<code>{seller_id}</code>)\n"
        f"{e(CARD['level'])} Level: {level}\n"
        f"{e(CARD['dm'])} Сообщения: {dm}\n"
        f"{e(CARD['status'])} Статус: {status}\n"
        f"{e(CARD['slug'])} {slug}\n"
        f"{e(CARD['time'])} {ts}\n"
    )
