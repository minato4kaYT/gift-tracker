

import hashlib
import hmac
import json
import sqlite3
import sys
import time
from pathlib import Path
from urllib.parse import parse_qsl

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

import config

API = "/api/gifttracker"
app = FastAPI(title="Gift Tracker MiniApp")
STATIC = Path(__file__).resolve().parent / "static"


def _check_init(init_data: str):

    if not init_data or not config.BOT_TOKEN:
        return None
    try:
        pairs = dict(parse_qsl(init_data, keep_blank_values=True))
        got = pairs.pop("hash", "")
        check = "\n".join(f"{k}={pairs[k]}" for k in sorted(pairs))
        secret = hmac.new(b"WebAppData", config.BOT_TOKEN.encode(), hashlib.sha256).digest()
        calc = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(calc, got):
            return None
        return json.loads(pairs.get("user", "{}"))
    except Exception:
        return None


def _kv(k: str, default):

    try:
        con = sqlite3.connect(f"file:{config.DB_PATH}?mode=ro", uri=True, timeout=3)
        cur = con.execute("SELECT v FROM kv WHERE k=?", (k,))
        r = cur.fetchone()
        con.close()
        return r[0] if r else default
    except Exception:
        return default


@app.get(API + "/state")
async def state(request: Request):

    init = request.headers.get("X-Init-Data", "")
    user = _check_init(init)
    uid = user.get("id") if user else 0
    return {
        "ok": True,
        "now": int(time.time()),
        "brand": "Gift Tracker",
        "is_admin": uid in config.ADMIN_IDS,
        "pct": int(_kv("worker_pct", config.WORKER_PCT)),
        "fee": int(_kv("payout_fee", config.PAYOUT_FEE_STARS)),
        "creator": {
            "username": config.CREATOR_USERNAME,
            "status": config.CREATOR_STATUS,
        },
        "bot": "GiftTrackerHubBot",
    }


app.mount("/", StaticFiles(directory=str(STATIC), html=True), name="static")
