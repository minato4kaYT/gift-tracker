
import time
import aiosqlite
import config

_db: aiosqlite.Connection | None = None


async def init():
    global _db
    _db = await aiosqlite.connect(config.DB_PATH)
    _db.row_factory = aiosqlite.Row
    await _db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users(
            user_id   INTEGER PRIMARY KEY,
            username  TEXT,
            created_at INTEGER,
            ref_by    INTEGER
        );
        CREATE TABLE IF NOT EXISTS subs(
            user_id    INTEGER PRIMARY KEY,
            expires_at INTEGER,        -- unix ts
            kind       TEXT            -- 'trial' | 'paid'
        );
        CREATE TABLE IF NOT EXISTS trials(
            user_id INTEGER PRIMARY KEY  -- one trial ever
        );
        CREATE TABLE IF NOT EXISTS claims(
            slug    TEXT PRIMARY KEY,
            user_id INTEGER,
            ts      INTEGER
        );
        CREATE TABLE IF NOT EXISTS seen(
            slug TEXT PRIMARY KEY
        );
        CREATE TABLE IF NOT EXISTS referrals(
            ref_by  INTEGER,
            user_id INTEGER PRIMARY KEY
        );
        CREATE TABLE IF NOT EXISTS kv(
            k TEXT PRIMARY KEY,
            v TEXT
        );
        CREATE TABLE IF NOT EXISTS banned(
            user_id INTEGER PRIMARY KEY,
            reason  TEXT,
            ts      INTEGER
        );
        -- закрытый переходник по заявке: кто подал chat_join_request (= прошёл гейт)
        CREATE TABLE IF NOT EXISTS gate_requests(
            user_id INTEGER,
            chat_id INTEGER,
            ts      INTEGER,
            PRIMARY KEY(user_id, chat_id)
        );
        CREATE TABLE IF NOT EXISTS payments(
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER,
            invoice_id TEXT,
            hours      INTEGER,
            tariff     TEXT,
            status     TEXT DEFAULT 'active',   -- active | paid
            created_at INTEGER
        );
        -- рабочие: те, кто занимает лоты и сдаёт гифты на выплату
        CREATE TABLE IF NOT EXISTS workers(
            user_id    INTEGER PRIMARY KEY,
            username   TEXT,
            joined_at  INTEGER,
            earned_ton REAL DEFAULT 0,    -- суммарно выплачено
            payouts    INTEGER DEFAULT 0  -- кол-во закрытых выплат
        );
        -- заявки на выплату: лот → передача гифта → приход → продажа → выплата
        CREATE TABLE IF NOT EXISTS payout_requests(
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            worker_id   INTEGER,
            username    TEXT,
            slug        TEXT,
            gift_title  TEXT,
            floor_stars INTEGER DEFAULT 0,
            floor_ton   REAL DEFAULT 0,
            status      TEXT DEFAULT 'awaiting',  -- awaiting|received|sold|paid|rejected
            arrival_id  INTEGER DEFAULT 0,        -- id из gifts.db gift_arrivals
            sale_ton    REAL DEFAULT 0,
            payout_ton  REAL DEFAULT 0,
            pct         INTEGER DEFAULT 50,
            fee_stars   INTEGER DEFAULT 0,        -- комиссия рабочего (30⭐), 0 = не оплачена
            fee_charge_id TEXT,                   -- telegram_payment_charge_id (для рефанда)
            note        TEXT,
            created_at  INTEGER,
            received_at INTEGER DEFAULT 0,
            sold_at     INTEGER DEFAULT 0,
            paid_at     INTEGER DEFAULT 0
        );
        """
    )
    cur = await _db.execute("PRAGMA table_info(claims)")
    ccols = {r[1] for r in await cur.fetchall()}
    for col, ddl in (("title", "TEXT"), ("floor_stars", "INTEGER DEFAULT 0"),
                     ("floor_ton", "REAL DEFAULT 0"), ("item_slug", "TEXT"),
                     ("card_text", "TEXT")):
        if col not in ccols:
            await _db.execute(f"ALTER TABLE claims ADD COLUMN {col} {ddl}")
    cur = await _db.execute("PRAGMA table_info(subs)")
    scols = {r[1] for r in await cur.fetchall()}
    if "expired_done" not in scols:
        await _db.execute("ALTER TABLE subs ADD COLUMN expired_done INTEGER DEFAULT 0")
    cur = await _db.execute("PRAGMA table_info(workers)")
    wcols = {r[1] for r in await cur.fetchall()}
    if "status" not in wcols:
        await _db.execute("ALTER TABLE workers ADD COLUMN status TEXT DEFAULT 'approved'")
    await _db.commit()


async def create_payment(user_id: int, invoice_id: str, hours: int, tariff: str) -> int:
    cur = await _db.execute(
        "INSERT INTO payments(user_id, invoice_id, hours, tariff, created_at) VALUES(?,?,?,?,?)",
        (user_id, invoice_id, hours, tariff, int(time.time())))
    await _db.commit()
    return cur.lastrowid


async def set_payment_invoice(pid: int, invoice_id: str):
    await _db.execute("UPDATE payments SET invoice_id=? WHERE id=?", (invoice_id, pid))
    await _db.commit()


async def get_payment(pid: int):
    cur = await _db.execute("SELECT * FROM payments WHERE id=?", (pid,))
    r = await cur.fetchone()
    return dict(r) if r else None


async def mark_payment_paid(pid: int) -> bool:

    cur = await _db.execute("UPDATE payments SET status='paid' WHERE id=? AND status!='paid'", (pid,))
    await _db.commit()
    return cur.rowcount > 0


async def get_kv(k: str, default=None):
    cur = await _db.execute("SELECT v FROM kv WHERE k=?", (k,))
    r = await cur.fetchone()
    return r["v"] if r else default


async def set_kv(k: str, v):
    await _db.execute(
        "INSERT INTO kv(k, v) VALUES(?, ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v",
        (k, str(v)),
    )
    await _db.commit()


async def add_user(user_id: int, username: str | None, ref_by: int | None):
    cur = await _db.execute("SELECT 1 FROM users WHERE user_id=?", (user_id,))
    if await cur.fetchone():
        await _db.execute("UPDATE users SET username=? WHERE user_id=?", (username, user_id))
    else:
        await _db.execute(
            "INSERT INTO users(user_id, username, created_at, ref_by) VALUES(?,?,?,?)",
            (user_id, username, int(time.time()), ref_by),
        )
        if ref_by and ref_by != user_id:
            await _db.execute(
                "INSERT OR IGNORE INTO referrals(ref_by, user_id) VALUES(?,?)",
                (ref_by, user_id),
            )
    await _db.commit()


async def mark_gate_request(user_id: int, chat_id: int):

    await _db.execute(
        "INSERT OR IGNORE INTO gate_requests(user_id, chat_id, ts) VALUES(?,?,?)",
        (user_id, chat_id, int(time.time())))
    await _db.commit()


async def has_gate_request(user_id: int, chat_id: int) -> bool:
    cur = await _db.execute(
        "SELECT 1 FROM gate_requests WHERE user_id=? AND chat_id=?", (user_id, chat_id))
    return await cur.fetchone() is not None


async def has_used_trial(user_id: int) -> bool:
    cur = await _db.execute("SELECT 1 FROM trials WHERE user_id=?", (user_id,))
    return await cur.fetchone() is not None


async def grant_subscription(user_id: int, hours: int, kind: str):
    now = int(time.time())
    cur = await _db.execute("SELECT expires_at FROM subs WHERE user_id=?", (user_id,))
    row = await cur.fetchone()
    base = max(now, row["expires_at"]) if row and row["expires_at"] > now else now
    expires = base + hours * 3600
    await _db.execute(
        "INSERT INTO subs(user_id, expires_at, kind, expired_done) VALUES(?,?,?,0) "
        "ON CONFLICT(user_id) DO UPDATE SET expires_at=excluded.expires_at, "
        "kind=excluded.kind, expired_done=0",
        (user_id, expires, kind),
    )
    if kind == "trial":
        await _db.execute("INSERT OR IGNORE INTO trials(user_id) VALUES(?)", (user_id,))
    await _db.commit()
    return expires


async def revoke_subscription(user_id: int) -> bool:

    cur = await _db.execute("DELETE FROM subs WHERE user_id=?", (user_id,))
    await _db.commit()
    return cur.rowcount > 0


async def user_id_by_username(username: str) -> int | None:

    username = (username or "").lstrip("@").strip()
    if not username:
        return None
    for table in ("users", "workers"):
        cur = await _db.execute(
            f"SELECT user_id FROM {table} "
            f"WHERE username IS NOT NULL AND lower(username)=lower(?) "
            f"ORDER BY user_id LIMIT 1",
            (username,))
        row = await cur.fetchone()
        if row:
            return row["user_id"]
    return None


async def get_username(user_id: int) -> str | None:
    for table in ("users", "workers"):
        cur = await _db.execute(
            f"SELECT username FROM {table} WHERE user_id=? AND username IS NOT NULL LIMIT 1",
            (user_id,))
        row = await cur.fetchone()
        if row and row["username"]:
            return row["username"]
    return None


async def revoke_worker(user_id: int) -> bool:

    cur = await _db.execute("SELECT status FROM workers WHERE user_id=?", (user_id,))
    row = await cur.fetchone()
    if not row:
        return False
    await _db.execute("UPDATE workers SET status='rejected' WHERE user_id=?", (user_id,))
    await _db.commit()
    return True


async def search_users(part: str, limit: int = 12):

    part = (part or "").lstrip("@").strip()
    if not part:
        return []
    cur = await _db.execute(
        "SELECT user_id, username FROM users "
        "WHERE username IS NOT NULL AND lower(username) LIKE lower(?) "
        "ORDER BY username LIMIT ?",
        (f"%{part}%", limit))
    return [(r["user_id"], r["username"]) for r in await cur.fetchall()]


async def list_users(offset: int = 0, limit: int = 8):

    cur = await _db.execute(
        "SELECT user_id, username FROM users ORDER BY created_at DESC, user_id DESC "
        "LIMIT ? OFFSET ?", (limit, offset))
    return [(r["user_id"], r["username"]) for r in await cur.fetchall()]


async def count_users() -> int:
    cur = await _db.execute("SELECT COUNT(*) c FROM users")
    return (await cur.fetchone())["c"]


async def user_payments(user_id: int, limit: int = 10):
    cur = await _db.execute(
        "SELECT hours, tariff, status, created_at FROM payments "
        "WHERE user_id=? ORDER BY id DESC LIMIT ?", (user_id, limit))
    return [dict(r) for r in await cur.fetchall()]


async def ban_user(user_id: int, reason: str = "") -> None:
    await _db.execute(
        "INSERT INTO banned(user_id, reason, ts) VALUES(?,?,?) "
        "ON CONFLICT(user_id) DO UPDATE SET reason=excluded.reason, ts=excluded.ts",
        (user_id, reason, int(time.time())))
    await _db.execute("DELETE FROM subs WHERE user_id=?", (user_id,))
    await _db.commit()


async def unban_user(user_id: int) -> bool:
    cur = await _db.execute("DELETE FROM banned WHERE user_id=?", (user_id,))
    await _db.commit()
    return cur.rowcount > 0


async def is_banned(user_id: int) -> bool:
    cur = await _db.execute("SELECT 1 FROM banned WHERE user_id=?", (user_id,))
    return await cur.fetchone() is not None


async def expired_subs() -> list[int]:

    now = int(time.time())
    cur = await _db.execute(
        "SELECT user_id FROM subs WHERE expires_at<=? AND COALESCE(expired_done,0)=0", (now,))
    return [r[0] for r in await cur.fetchall()]


async def mark_sub_expired_done(user_id: int):
    await _db.execute("UPDATE subs SET expired_done=1 WHERE user_id=?", (user_id,))
    await _db.commit()


async def get_subscription(user_id: int):
    cur = await _db.execute("SELECT expires_at, kind FROM subs WHERE user_id=?", (user_id,))
    row = await cur.fetchone()
    if not row:
        return None
    if row["expires_at"] <= int(time.time()):
        return None
    return {"expires_at": row["expires_at"], "kind": row["kind"]}


async def claim_count(user_id: int) -> int:
    cur = await _db.execute("SELECT COUNT(*) c FROM claims WHERE user_id=?", (user_id,))
    return (await cur.fetchone())["c"]


async def try_claim(slug: str, user_id: int, title: str = None,
                    floor_stars: int = 0, floor_ton: float = 0, item_slug: str = None,
                    card_text: str = None):


    try:
        await _db.execute(
            "INSERT INTO claims(slug, user_id, ts, title, floor_stars, floor_ton, item_slug, card_text) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (slug, user_id, int(time.time()), title, floor_stars, floor_ton, item_slug, card_text),
        )
        await _db.commit()
        return True, user_id
    except aiosqlite.IntegrityError:
        cur = await _db.execute("SELECT user_id FROM claims WHERE slug=?", (slug,))
        row = await cur.fetchone()
        return False, (row["user_id"] if row else None)


async def release_claim(slug: str, user_id: int, is_admin: bool = False):


    cur = await _db.execute("SELECT user_id, card_text FROM claims WHERE slug=?", (slug,))
    row = await cur.fetchone()
    if not row:
        return False, None
    if row["user_id"] != user_id and not is_admin:
        return False, None
    await _db.execute("DELETE FROM claims WHERE slug=?", (slug,))
    await _db.commit()
    return True, row["card_text"]


async def get_claim(slug: str):
    cur = await _db.execute("SELECT * FROM claims WHERE slug=?", (slug,))
    r = await cur.fetchone()
    return dict(r) if r else None


async def user_claims(user_id: int, limit: int = 50):
    cur = await _db.execute(
        "SELECT * FROM claims WHERE user_id=? ORDER BY ts DESC LIMIT ?", (user_id, limit))
    return [dict(r) for r in await cur.fetchall()]


async def mark_seen(slug: str) -> bool:

    try:
        await _db.execute("INSERT INTO seen(slug) VALUES(?)", (slug,))
        await _db.commit()
        return True
    except aiosqlite.IntegrityError:
        return False


async def referral_stats(user_id: int):
    cur = await _db.execute("SELECT COUNT(*) c FROM referrals WHERE ref_by=?", (user_id,))
    return (await cur.fetchone())["c"]


async def ensure_worker(user_id: int, username: str | None):
    cur = await _db.execute("SELECT 1 FROM workers WHERE user_id=?", (user_id,))
    if await cur.fetchone():
        if username:
            await _db.execute("UPDATE workers SET username=? WHERE user_id=?", (username, user_id))
    else:
        await _db.execute(
            "INSERT INTO workers(user_id, username, joined_at) VALUES(?,?,?)",
            (user_id, username, int(time.time())))
    await _db.commit()


async def get_worker(user_id: int):
    cur = await _db.execute("SELECT * FROM workers WHERE user_id=?", (user_id,))
    r = await cur.fetchone()
    return dict(r) if r else None


async def worker_status(user_id: int) -> str | None:

    w = await get_worker(user_id)
    return w["status"] if w else None


async def apply_worker(user_id: int, username: str | None) -> str:

    w = await get_worker(user_id)
    if not w:
        await _db.execute(
            "INSERT INTO workers(user_id, username, joined_at, status) VALUES(?,?,?, 'pending')",
            (user_id, username, int(time.time())))
    elif w["status"] == "rejected":
        await _db.execute("UPDATE workers SET status='pending', username=? WHERE user_id=?",
                          (username, user_id))
    elif username:
        await _db.execute("UPDATE workers SET username=? WHERE user_id=?", (username, user_id))
    await _db.commit()
    return (await get_worker(user_id))["status"]


async def set_worker_status(user_id: int, status: str):
    await _db.execute("UPDATE workers SET status=? WHERE user_id=?", (status, user_id))
    await _db.commit()


async def all_user_ids() -> list[int]:
    cur = await _db.execute("SELECT user_id FROM users")
    return [r[0] for r in await cur.fetchall()]


async def workers_top(limit: int = 30):
    cur = await _db.execute(
        "SELECT * FROM workers ORDER BY earned_ton DESC, payouts DESC LIMIT ?", (limit,))
    return [dict(r) for r in await cur.fetchall()]


async def create_payout(worker_id, username, slug, gift_title, floor_stars, floor_ton, pct) -> int:
    cur = await _db.execute(
        "INSERT INTO payout_requests(worker_id,username,slug,gift_title,floor_stars,floor_ton,pct,created_at) "
        "VALUES(?,?,?,?,?,?,?,?)",
        (worker_id, username, slug, gift_title, floor_stars, floor_ton, pct, int(time.time())))
    await _db.commit()
    return cur.lastrowid


async def mark_fee_paid(req_id: int, fee_stars: int, charge_id: str):
    await _db.execute(
        "UPDATE payout_requests SET fee_stars=?, fee_charge_id=? WHERE id=?",
        (fee_stars, charge_id, req_id))
    await _db.commit()


async def get_payout(req_id: int):
    cur = await _db.execute("SELECT * FROM payout_requests WHERE id=?", (req_id,))
    r = await cur.fetchone()
    return dict(r) if r else None


async def worker_payouts(worker_id: int, limit: int = 50):
    cur = await _db.execute(
        "SELECT * FROM payout_requests WHERE worker_id=? ORDER BY id DESC LIMIT ?", (worker_id, limit))
    return [dict(r) for r in await cur.fetchall()]


async def oldest_awaiting(worker_id: int):

    cur = await _db.execute(
        "SELECT * FROM payout_requests WHERE worker_id=? AND status='awaiting' "
        "AND fee_stars>0 ORDER BY id ASC LIMIT 1", (worker_id,))
    r = await cur.fetchone()
    return dict(r) if r else None


async def awaiting_requests(worker_id: int):


    cur = await _db.execute(
        "SELECT * FROM payout_requests WHERE worker_id=? AND status='awaiting' "
        "AND fee_stars>0 ORDER BY id ASC", (worker_id,))
    return [dict(r) for r in await cur.fetchall()]


async def mark_received(req_id: int, arrival_id: int):
    await _db.execute(
        "UPDATE payout_requests SET status='received', arrival_id=?, received_at=? "
        "WHERE id=? AND status='awaiting'",
        (arrival_id, int(time.time()), req_id))
    await _db.commit()


async def mark_sold(req_id: int, sale_ton: float):
    p = await get_payout(req_id)
    if not p:
        return None
    payout = round(sale_ton * (p["pct"] / 100), 2)
    await _db.execute(
        "UPDATE payout_requests SET status='sold', sale_ton=?, payout_ton=?, sold_at=? WHERE id=?",
        (sale_ton, payout, int(time.time()), req_id))
    await _db.commit()
    return payout


async def mark_paid(req_id: int) -> bool:

    cur = await _db.execute(
        "UPDATE payout_requests SET status='paid', paid_at=? WHERE id=? AND status='sold'",
        (int(time.time()), req_id))
    await _db.commit()
    if cur.rowcount <= 0:
        return False
    p = await get_payout(req_id)
    await _db.execute(
        "UPDATE workers SET earned_ton=earned_ton+?, payouts=payouts+1 WHERE user_id=?",
        (p["payout_ton"], p["worker_id"]))
    await _db.commit()
    return True


async def reject_payout(req_id: int, note: str = "") -> bool:
    cur = await _db.execute(
        "UPDATE payout_requests SET status='rejected', note=? WHERE id=? AND status NOT IN ('paid','rejected')",
        (note, req_id))
    await _db.commit()
    return cur.rowcount > 0


async def payouts_by_status(statuses: tuple, limit: int = 50):
    qs = ",".join("?" * len(statuses))
    cur = await _db.execute(
        f"SELECT * FROM payout_requests WHERE status IN ({qs}) ORDER BY id DESC LIMIT ?",
        (*statuses, limit))
    return [dict(r) for r in await cur.fetchall()]


async def creator_stats() -> dict:
    async def one(q, *a):
        return (await (await _db.execute(q, a)).fetchone())[0] or 0
    return {
        "workers": await one("SELECT COUNT(*) FROM workers"),
        "awaiting": await one("SELECT COUNT(*) FROM payout_requests WHERE status='awaiting' AND fee_stars>0"),
        "received": await one("SELECT COUNT(*) FROM payout_requests WHERE status='received'"),
        "sold": await one("SELECT COUNT(*) FROM payout_requests WHERE status='sold'"),
        "paid": await one("SELECT COUNT(*) FROM payout_requests WHERE status='paid'"),
        "sales_ton": round(await one("SELECT COALESCE(SUM(sale_ton),0) FROM payout_requests WHERE status IN ('sold','paid')"), 2),
        "payouts_ton": round(await one("SELECT COALESCE(SUM(payout_ton),0) FROM payout_requests WHERE status='paid'"), 2),
        "fee_stars": await one("SELECT COALESCE(SUM(fee_stars),0) FROM payout_requests"),
        "claims": await one("SELECT COUNT(*) FROM claims"),
    }
