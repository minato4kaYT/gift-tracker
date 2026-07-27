

import datetime

import aiosqlite

import config

_RO = lambda: aiosqlite.connect(f"file:{config.GIFTS_DB}?mode=ro", uri=True)

_Q = (
    "SELECT s.id, s.gift_id, s.title, s.kind, s.floor_stars, s.floor_ton, s.old_floor, "
    "s.slug, s.sample_slug, s.created_at, c.floor_ton AS coll_ton, c.resale_count, c.supply, c.image_url "
    "FROM signals s LEFT JOIN collections c ON c.gift_id = s.gift_id "
    "WHERE s.id > ? ORDER BY s.id ASC LIMIT ?"
)


def _shape(r: dict) -> dict:
    ton = r.get("floor_ton") or r.get("coll_ton") or 0
    ts = datetime.datetime.utcfromtimestamp(r["created_at"]).strftime("%d.%m.%Y %H:%M:%S")
    return {
        "signal_id": r["id"],
        "kind": r["kind"],
        "gift": r["title"] or f"Gift #{r['gift_id']}",
        "price_stars": r["floor_stars"],
        "price_ton": ton,
        "old_floor": r["old_floor"],
        "resale": r.get("resale_count") or 0,
        "supply": r.get("supply") or 0,
        "slug": r["slug"] or "",
        "item_slug": r.get("sample_slug") or "",
        "ts": ts,
    }


async def fetch_new(last_id: int, limit: int = 8) -> list[dict]:

    async with _RO() as g:
        g.row_factory = aiosqlite.Row
        cur = await g.execute(_Q, (last_id, limit * 3))
        rows = [dict(r) for r in await cur.fetchall()]
    out = [_shape(r) for r in rows if r["kind"] in config.FEED_KINDS]
    return out[:limit]


async def max_signal_id() -> int:
    async with _RO() as g:
        cur = await g.execute("SELECT COALESCE(MAX(id), 0) FROM signals")
        return (await cur.fetchone())[0]


async def collection_by_slug(slug: str):
    if not slug:
        return None
    async with _RO() as g:
        g.row_factory = aiosqlite.Row
        cur = await g.execute("SELECT * FROM collections WHERE slug=? LIMIT 1", (slug,))
        r = await cur.fetchone()
        return dict(r) if r else None


async def feed_floors(limit: int = 80) -> list[dict]:

    async with _RO() as g:
        g.row_factory = aiosqlite.Row
        cur = await g.execute(
            "SELECT gift_id,title,floor_stars,floor_ton,resale_count,slug,image_url,supply,"
            "COALESCE(locked_until,0) AS locked_until "
            "FROM collections WHERE resale_count>0 ORDER BY floor_stars LIMIT ?", (limit,))
        return [dict(r) for r in await cur.fetchall()]


async def peek_collections(limit: int = 80) -> list[dict]:
    async with _RO() as g:
        g.row_factory = aiosqlite.Row
        try:
            cur = await g.execute(
                "SELECT * FROM peek_collections ORDER BY items_count DESC LIMIT ?", (limit,))
            return [dict(r) for r in await cur.fetchall()]
        except Exception:
            return []


async def peek_drops(after_ts: int, limit: int = 20) -> list[dict]:


    async with _RO() as g:
        g.row_factory = aiosqlite.Row
        try:
            cur = await g.execute(
                "SELECT * FROM peek_gifts WHERE available=1 AND first_available>? "
                "ORDER BY first_available ASC LIMIT ?", (after_ts, limit))
            return [dict(r) for r in await cur.fetchall()]
        except Exception:
            return []


async def peek_gift_by_name(name: str):

    if not name:
        return None
    async with _RO() as g:
        g.row_factory = aiosqlite.Row
        try:
            cur = await g.execute("SELECT * FROM peek_gifts WHERE name=? LIMIT 1", (name,))
            r = await cur.fetchone()
            return dict(r) if r else None
        except Exception:
            return None


async def unlock_signals(after_id: int, limit: int = 8) -> list[dict]:


    import datetime
    async with _RO() as g:
        g.row_factory = aiosqlite.Row
        try:
            cur = await g.execute(
                "SELECT u.id, u.name, u.gift_number, u.unlock_at, u.market, "
                "u.owner_username, p.price_ton, p.total "
                "FROM unlock_soon u LEFT JOIN peek_gifts p ON p.name = u.name "
                "WHERE u.id > ? ORDER BY u.id ASC LIMIT ?", (after_id, limit))
            rows = [dict(r) for r in await cur.fetchall()]
        except Exception:
            return []
    import time
    now = int(time.time())
    out = []
    for r in rows:
        ton = r.get("price_ton") or 0
        ua = r["unlock_at"]
        ts = datetime.datetime.utcfromtimestamp(ua).strftime("%d.%m.%Y %H:%M:%S")
        out.append({
            "signal_id": r["id"],
            "kind": "fresh",
            "gift": r["name"],
            "price_stars": 0,
            "price_ton": ton,
            "old_floor": 0,
            "resale": 0,
            "supply": r.get("total") or 0,
            "slug": r["name"],
            "item_slug": f"{r['name']}-{r['gift_number']}",
            "seller_user": r.get("owner_username") or "",
            "unlock_at": ua,
            "unlock_in_min": max(0, round((ua - now) / 60)),
            "ts": ts,
            "source": "peek.tg",
        })
    return out


async def unlock_owner(item_slug: str):

    if not item_slug or "-" not in item_slug:
        return None
    base, _, tail = item_slug.rpartition("-")
    if not tail.isdigit():
        return None
    async with _RO() as g:
        g.row_factory = aiosqlite.Row
        try:
            cur = await g.execute(
                "SELECT owner_username FROM unlock_soon WHERE name=? AND gift_number=? LIMIT 1",
                (base, int(tail)))
            r = await cur.fetchone()
            return (dict(r).get("owner_username") if r else None)
        except Exception:
            return None


async def max_unlock_id() -> int:
    async with _RO() as g:
        try:
            cur = await g.execute("SELECT COALESCE(MAX(id),0) FROM unlock_soon")
            return (await cur.fetchone())[0]
        except Exception:
            return 0


async def peek_movers(min_change: float, limit: int = 20) -> list[dict]:

    async with _RO() as g:
        g.row_factory = aiosqlite.Row
        try:
            cur = await g.execute(
                "SELECT * FROM peek_gifts WHERE change IS NOT NULL AND ABS(change)>=? "
                "ORDER BY ABS(change) DESC LIMIT ?", (min_change, limit))
            return [dict(r) for r in await cur.fetchall()]
        except Exception:
            return []


async def arrivals_after(last_id: int, limit: int = 50) -> list[dict]:
    async with _RO() as g:
        g.row_factory = aiosqlite.Row
        try:
            cur = await g.execute(
                "SELECT * FROM gift_arrivals WHERE id>? ORDER BY id ASC LIMIT ?", (last_id, limit))
            return [dict(r) for r in await cur.fetchall()]
        except Exception:
            return []


async def max_arrival_id() -> int:
    async with _RO() as g:
        try:
            cur = await g.execute("SELECT COALESCE(MAX(id),0) FROM gift_arrivals")
            return (await cur.fetchone())[0]
        except Exception:
            return 0
