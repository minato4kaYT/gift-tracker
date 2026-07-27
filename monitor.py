
import asyncio
import logging

from aiogram import Bot

import config
import db
import render
import keyboards
from sources.demo_feed import make_listing

log = logging.getLogger("monitor")


async def run_sub_expiry(bot: Bot):


    if not config.FORUM_CHAT:
        log.info("sub expiry: FORUM_CHAT не задан — кик из супергруппы пропускаем, DM шлём")
    await asyncio.sleep(6)
    while True:
        try:
            for uid in await db.expired_subs():
                if config.FORUM_CHAT:
                    try:
                        await bot.ban_chat_member(config.FORUM_CHAT, uid)
                        await bot.unban_chat_member(config.FORUM_CHAT, uid)
                    except Exception:
                        pass
                try:
                    await bot.send_message(uid, render.sub_expired_text(),
                                           parse_mode="HTML", reply_markup=keyboards.renew_sub())
                except Exception:
                    pass
                await db.mark_sub_expired_done(uid)
                log.info("подписка истекла: уведомлён uid=%s", uid)
                await asyncio.sleep(0.3)
        except Exception as ex:
            log.error("sub expiry loop: %s", ex)
        await asyncio.sleep(config.SUB_EXPIRY_POLL)


def _dest_chat() -> int:

    return config.FORUM_CHAT or config.LOG_CHAT_ID


async def _post_signal(bot: Bot, text: str, supply: int, reply_markup=None):

    chat = _dest_chat()
    kwargs = dict(parse_mode="HTML", reply_markup=reply_markup, disable_web_page_preview=True)
    if config.FORUM_CHAT:
        tid = config.topic_for_supply(supply)
        if tid:
            kwargs["message_thread_id"] = tid
    await bot.send_message(chat, text, **kwargs)


async def run_live_feed(bot: Bot):


    from sources import live_feed

    if not config.LIVE_FEED_ENABLED:
        log.info("live feed disabled")
        return
    if not _dest_chat():
        log.warning("ни FORUM_CHAT, ни LOG_CHAT_ID не заданы — фид некуда постить")
        return

    last = await db.get_kv("last_signal_id")
    if last is None:
        last = await live_feed.max_signal_id()
        await db.set_kv("last_signal_id", last)
    last = int(last)
    log.info("live feed запущен с signal_id=%s → форум %s (БД %s)",
             last, _dest_chat(), config.GIFTS_DB)

    await asyncio.sleep(2)
    while True:
        try:
            for it in await live_feed.fetch_new(last, config.FEED_BATCH):
                try:
                    await _post_signal(
                        bot, render.live_card(it), it.get("supply") or 0,
                        reply_markup=keyboards.listing_card(it["slug"], item_slug=it.get("item_slug")))
                except Exception as ex:
                    log.error("post failed: %s", ex)
                last = it["signal_id"]
                await db.set_kv("last_signal_id", last)
                await asyncio.sleep(0.5)
        except Exception as ex:
            log.error("live feed loop: %s", ex)
        await asyncio.sleep(config.FEED_INTERVAL)


async def run_peek_source(bot: Bot):


    from sources import live_feed
    import json, time

    if not config.PEEK_SOURCE_ENABLED or not _dest_chat():
        log.info("peek source disabled")
        return

    raw_ts = await db.get_kv("peek_drop_ts")
    drop_ts = int(raw_ts) if raw_ts else int(time.time())
    if not raw_ts:
        await db.set_kv("peek_drop_ts", str(drop_ts))
    raw_seen = await db.get_kv("peek_mover_seen")
    mover_seen = set(json.loads(raw_seen)) if raw_seen else set()
    log.info("peek live-фид запущен (drop_ts=%s, movers_known=%d)", drop_ts, len(mover_seen))

    await asyncio.sleep(8)
    while True:
        posted = 0
        try:
            if config.PEEK_DROPS_ENABLED:
                for g in await live_feed.peek_drops(drop_ts, 20):
                    if posted >= config.PEEK_MAX_PER_POLL:
                        break
                    try:
                        await _post_signal(
                            bot, render.peek_drop_card(g), g.get("total") or 0,
                            reply_markup=keyboards.listing_card(g["name"]))
                        posted += 1
                        await asyncio.sleep(0.6)
                    except Exception as ex:
                        log.error("peek drop post failed: %s", ex)
                    drop_ts = max(drop_ts, g.get("first_available") or drop_ts)
                await db.set_kv("peek_drop_ts", str(drop_ts))

            if config.PEEK_MOVERS_ENABLED:
                for g in await live_feed.peek_movers(config.PEEK_MOVER_MIN_CHANGE, 20):
                    if posted >= config.PEEK_MAX_PER_POLL:
                        break
                    ch = g.get("change") or 0
                    bucket = f"{g['name']}:{'+' if ch >= 0 else '-'}{int(abs(ch) // 5) * 5}"
                    if bucket in mover_seen:
                        continue
                    mover_seen.add(bucket)
                    try:
                        await _post_signal(bot, render.peek_mover_card(g), g.get("total") or 0)
                        posted += 1
                        await asyncio.sleep(0.6)
                    except Exception as ex:
                        log.error("peek mover post failed: %s", ex)
                await db.set_kv("peek_mover_seen", json.dumps(list(mover_seen)[-3000:]))

            if posted:
                log.info("peek: опубликовано сигналов %d", posted)
        except Exception as ex:
            log.error("peek source loop: %s", ex)
        await asyncio.sleep(config.PEEK_POLL)


async def run_unlock_source(bot: Bot):


    from sources import live_feed

    if not config.UNLOCK_SOURCE_ENABLED or not _dest_chat():
        log.info("unlock source disabled")
        return
    last = int(await db.get_kv("last_unlock_id") or 0)
    if last == 0:
        last = await live_feed.max_unlock_id()
        await db.set_kv("last_unlock_id", str(last))
    log.info("unlock source запущен с last_unlock_id=%s", last)

    await asyncio.sleep(10)
    while True:
        try:
            for it in await live_feed.unlock_signals(last, config.FEED_BATCH):
                try:
                    await _post_signal(
                        bot, render.unlock_card(it), it.get("supply") or 0,
                        reply_markup=keyboards.listing_card(
                            it["slug"], seller_user=it.get("seller_user") or None,
                            item_slug=it.get("item_slug")))
                except Exception as ex:
                    log.error("unlock post failed: %s", ex)
                last = it["signal_id"]
                await db.set_kv("last_unlock_id", str(last))
                await asyncio.sleep(0.5)
        except Exception as ex:
            log.error("unlock source loop: %s", ex)
        await asyncio.sleep(config.UNLOCK_POLL)


async def run_demo_feed(bot: Bot):

    if not config.DEMO_FEED_ENABLED:
        log.info("demo feed disabled")
        return
    if not config.LOG_CHAT_ID:
        log.warning("LOG_CHAT_ID not set — demo feed has nowhere to post")
        return

    await asyncio.sleep(3)
    while True:
        listing = make_listing()
        if await db.mark_seen(listing["slug"]):
            try:
                await bot.send_message(
                    config.LOG_CHAT_ID,
                    render.listing_card(listing),
                    parse_mode="HTML",
                    reply_markup=keyboards.listing_card(
                        listing["slug"], listing["seller_user"]),
                    disable_web_page_preview=True,
                )
            except Exception as ex:
                log.error("post failed: %s", ex)
        await asyncio.sleep(config.DEMO_FEED_INTERVAL)
