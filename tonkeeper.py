

import time
import logging
from urllib.parse import quote

import aiohttp

import config

logger = logging.getLogger(__name__)

TONCENTER_API = "https://toncenter.com/api/v2"

_API_KEY = getattr(config, "TONCENTER_API_KEY", "")
_HEADERS = {"X-API-Key": _API_KEY} if _API_KEY else {}


_addr_cache = {"addr": "", "ts": 0}


async def resolve_ton_dns(domain: str) -> str:


    if not domain.endswith(".ton"):
        return domain
    now = time.time()
    if _addr_cache["addr"] and now - _addr_cache["ts"] < 86400:
        return _addr_cache["addr"]
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{TONCENTER_API}/dns/resolve?name={domain}", headers=_HEADERS,
                             timeout=aiohttp.ClientTimeout(total=10)) as r:
                data = await r.json()
                wallet = data.get("result", {}).get("wallet", {}).get("value", "")
                if wallet:
                    _addr_cache["addr"] = wallet
                    _addr_cache["ts"] = now
                    return wallet
    except Exception as e:
        logger.warning(f"TON DNS resolve failed: {e}")
    return domain


def generate_link(address: str, amount_ton: float, comment: str, expires_at: int = 0) -> str:


    nanotons = int(round(amount_ton * 1e9))
    url = (f"https://app.tonkeeper.com/transfer/{address}"
           f"?amount={nanotons}&text={quote(comment, safe='')}")
    if expires_at > 0:
        url += f"&exp={int(expires_at)}"
    return url


async def check_payment(address: str, comment: str, expected_nano: int, since_ts: int) -> bool:


    try:
        async with aiohttp.ClientSession() as s:
            params = {"address": address, "limit": 30, "archival": "false"}
            async with s.get(f"{TONCENTER_API}/getTransactions", params=params, headers=_HEADERS,
                             timeout=aiohttp.ClientTimeout(total=10)) as r:
                data = await r.json()
                for tx in data.get("result", []):
                    if tx.get("utime", 0) < since_ts:
                        continue
                    in_msg = tx.get("in_msg", {})
                    msg_text = (in_msg.get("message", "") or "").strip()
                    value = int(in_msg.get("value", 0) or 0)
                    if msg_text == comment.strip() and value >= int(expected_nano * 0.95):
                        return True
    except Exception as e:
        logger.warning(f"Tonkeeper check failed: {e}")
    return False
