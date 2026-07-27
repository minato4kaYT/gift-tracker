

import asyncio
import datetime
import logging

import aiohttp

import config

log = logging.getLogger("swap")

_NANO = 10 ** 9
_MAINNET_ID = -239
_SIMULATE_URL = "https://api.ston.fi/v1/swap/simulate"


def _now_local() -> datetime.datetime:
    return datetime.datetime.utcnow() + datetime.timedelta(hours=config.SWAP_TZ_OFFSET)


def _seconds_until_run() -> float:
    now = _now_local()
    target = now.replace(hour=config.SWAP_HOUR, minute=config.SWAP_MINUTE,
                         second=0, microsecond=0)
    if target <= now:
        target += datetime.timedelta(days=1)
    return (target - now).total_seconds()


def _norm(addr: str) -> str:
    return (addr or "").strip().lower()


async def _simulate(offer_nano: int) -> dict | None:

    from stonfi import PTON_V1_ADDRESS
    params = {
        "offer_address": str(PTON_V1_ADDRESS),
        "ask_address": config.SWAP_ASK_JETTON,
        "units": str(offer_nano),
        "slippage_tolerance": str(config.SWAP_SLIPPAGE),
    }
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(_SIMULATE_URL, params=params,
                              timeout=aiohttp.ClientTimeout(total=20)) as r:
                if r.status != 200:
                    log.warning("simulate http %s: %s", r.status, (await r.text())[:200])
                    return None
                return await r.json()
    except Exception as e:
        log.warning("simulate failed: %s", e)
        return None


async def do_swap(bot=None) -> str:

    if not config.SWAP_ENABLED:
        return "disabled"
    if not config.TONKEEPER_MNEMONIC:
        msg = "⛔ Автосвап не настроен: пустой TONKEEPER_MNEMONIC"
        log.warning(msg)
        return msg

    from pytoniq import LiteBalancer
    from pytoniq.contract.wallets import WalletV5R1
    from stonfi import RouterV1

    prov = LiteBalancer.from_mainnet_config(1)
    await prov.start_up()
    try:
        mnemo = config.TONKEEPER_MNEMONIC.split()
        wallet = await WalletV5R1.from_mnemonic(prov, mnemo, network_global_id=_MAINNET_ID)
        addr = wallet.address.to_str(is_user_friendly=True, is_bounceable=False)
        if _norm(addr) != _norm(config.TONKEEPER_WALLET):
            msg = (f"⛔ Сид-фраза даёт адрес {addr}, а не TONKEEPER_WALLET "
                   f"({config.TONKEEPER_WALLET}). Проверь TONKEEPER_MNEMONIC/версию (нужен W5).")
            log.error(msg)
            return msg

        balance = int(wallet.balance or 0)
        reserve = int(config.SWAP_GAS_RESERVE_TON * _NANO)
        offer = balance - reserve
        if balance < int(config.SWAP_MIN_TON * _NANO) or offer <= 0:
            msg = f"ℹ️ Свапать нечего: баланс {balance/_NANO:.4f} TON (минимум {config.SWAP_MIN_TON})"
            log.info(msg)
            return msg

        sim = await _simulate(offer)
        if not sim or not sim.get("min_ask_units"):
            msg = "⛔ Не удалось получить котировку STON.fi — свап пропущен"
            log.warning(msg)
            return msg
        min_ask = int(sim["min_ask_units"])
        ask = int(sim.get("ask_units", 0))
        impact = float(sim.get("price_impact", 0) or 0)
        if impact > config.SWAP_MAX_IMPACT:
            msg = (f"⛔ Слишком большой price impact {impact:.2%} > "
                   f"{config.SWAP_MAX_IMPACT:.0%} — свап пропущен")
            log.warning(msg)
            return msg

        router = RouterV1()
        tx = await router.build_swap_ton_to_jetton_tx_params(
            user_wallet_address=wallet.address,
            ask_jetton_address=config.SWAP_ASK_JETTON,
            offer_amount=offer,
            min_ask_amount=min_ask,
            provider=prov,
        )
        await wallet.transfer(destination=tx["to"], amount=tx["amount"], body=tx["payload"])

        msg = (f"✅ Автосвап: {offer/_NANO:.4f} TON → ~{ask/1e6:.4f} USDT "
               f"(min {min_ask/1e6:.4f}, impact {impact:.2%})\n"
               f"USDT осел на кошельке {config.TONKEEPER_WALLET}")
        log.info(msg)
        return msg
    except Exception as e:
        msg = f"⛔ Ошибка автосвапа: {e}"
        log.exception(msg)
        return msg
    finally:
        try:
            await prov.close_all()
        except Exception:
            pass


async def _notify_owners(bot, text: str):
    if not bot:
        return
    for oid in set(config.CREATOR_IDS) | set(config.ADMIN_IDS):
        try:
            await bot.send_message(oid, text)
        except Exception:
            pass


async def run_auto_swap(bot):

    if not config.SWAP_ENABLED:
        log.info("auto-swap disabled")
        return
    log.info("auto-swap loop started (at %02d:%02d UTC+%d)",
             config.SWAP_HOUR, config.SWAP_MINUTE, config.SWAP_TZ_OFFSET)
    while True:
        try:
            await asyncio.sleep(_seconds_until_run())
            result = await do_swap(bot)
            if not result.startswith("ℹ️") and result != "disabled":
                await _notify_owners(bot, result)
            await asyncio.sleep(70)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.exception("swap loop error: %s", e)
            await asyncio.sleep(300)
