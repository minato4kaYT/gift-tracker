

from __future__ import annotations
import asyncio
import datetime


async def poll_native_market(api_id: int, api_hash: str, session: str,
                             gift_type_ids: list[int], interval: int = 8):

    from telethon import TelegramClient
    from telethon.sessions import StringSession
    from telethon.tl.functions.payments import GetResaleStarGiftsRequest

    client = TelegramClient(StringSession(session), api_id, api_hash)
    await client.connect()
    seen: set[str] = set()

    while True:
        for gift_id in gift_type_ids:
            try:
                res = await client(GetResaleStarGiftsRequest(
                    gift_id=gift_id, attributes_hash=0, offset="", limit=20,
                ))
            except Exception as ex:
                await asyncio.sleep(interval * 3)
                continue

            for g in getattr(res, "gifts", []):
                slug = getattr(g, "slug", None)
                if not slug or slug in seen:
                    continue
                seen.add(slug)
                stars, ton = _extract_price(g)
                yield {
                    "gift": getattr(g, "title", "Gift"),
                    "model": _attr(g, "model"),
                    "price_stars": stars,
                    "price_ton": ton,
                    "seller_user": _seller_username(res, g),
                    "seller_id": _seller_id(g),
                    "level": 1,
                    "dm": "бесплатно",
                    "premium": True,
                    "slug": slug,
                    "ts": datetime.datetime.utcnow().strftime("%d.%m.%Y %H:%M:%S"),
                }
        await asyncio.sleep(interval)


def _extract_price(g):
    amounts = getattr(g, "resell_amount", None) or []
    stars = ton = None
    for a in amounts:
        cn = type(a).__name__.lower()
        if "stars" in cn:
            stars = getattr(a, "amount", None)
        elif "ton" in cn:
            ton = round(getattr(a, "amount", 0) / 1e9, 2)
    return stars, ton


def _attr(g, kind):
    for a in getattr(g, "attributes", []) or []:
        if type(a).__name__.lower().endswith(kind):
            return getattr(a, "name", "—")
    return "—"


def _seller_username(res, g):
    return getattr(g, "owner_name", None) or "seller"


def _seller_id(g):
    return getattr(g, "owner_id", 0)
