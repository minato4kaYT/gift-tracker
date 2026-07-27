
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

import config
import db
import handlers
import monitor
import swap
from premium_emoji import PremiumEmojiMiddleware
from subgate import SubGateMiddleware

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("run")


async def main():
    if not config.BOT_TOKEN:
        raise SystemExit("BOT_TOKEN not set — copy .env.example to .env and fill it.")
    await db.init()

    bot = Bot(config.BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    bot.session.middleware(PremiumEmojiMiddleware())
    dp = Dispatcher()
    if config.required_channels():
        dp.message.outer_middleware(SubGateMiddleware())
        dp.callback_query.outer_middleware(SubGateMiddleware())
    dp.include_router(handlers.router)

    if config.LIVE_FEED_ENABLED:
        feed_task = asyncio.create_task(monitor.run_live_feed(bot))
    else:
        feed_task = asyncio.create_task(monitor.run_demo_feed(bot))
    peek_task = asyncio.create_task(monitor.run_peek_source(bot))
    unlock_task = asyncio.create_task(monitor.run_unlock_source(bot))
    exp_task = asyncio.create_task(monitor.run_sub_expiry(bot))
    swap_task = asyncio.create_task(swap.run_auto_swap(bot))

    me = await bot.get_me()
    log.info("bot @%s started (premium_emoji=ON, live_feed=%s, demo_feed=%s)",
             me.username, config.LIVE_FEED_ENABLED, config.DEMO_FEED_ENABLED)
    try:
        await dp.start_polling(bot)
    finally:
        feed_task.cancel()
        peek_task.cancel()
        unlock_task.cancel()
        exp_task.cancel()
        swap_task.cancel()


if __name__ == "__main__":
    asyncio.run(main())
