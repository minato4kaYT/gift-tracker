

import asyncio
import re

from telethon import TelegramClient, functions
from telethon.tl.types import ChatAdminRights

API_ID = 21536167
API_HASH = "1c8446933e892bb00a9d78fe24c46b38"
SESSION = "/root/FIRMA_PROJECT/_un1quexd"
BOT_NAME = "Gift Tracker"
CANDIDATES = [
    "GiftTrackerHubBot", "NftGiftTrackerBot", "GiftResaleTrackerBot",
    "GiftFloorTrackerBot", "GiftSignalsHubBot", "GiftDropTrackerBot",
    "GiftMarketTrackerBot", "GiftTrackerXBot", "GiftTracker2025Bot",
]


async def wait_reply(c, bf, after_id):
    for _ in range(15):
        await asyncio.sleep(1)
        msgs = await c.get_messages(bf, limit=1)
        if msgs and msgs[0].id > after_id and not msgs[0].out:
            return msgs[0]
    return None


async def make_bot(c):
    bf = await c.get_entity("BotFather")
    last = (await c.get_messages(bf, limit=1))[0].id
    await c.send_message(bf, "/newbot")
    m = await wait_reply(c, bf, last); last = m.id if m else last
    await c.send_message(bf, BOT_NAME)
    m = await wait_reply(c, bf, last); last = m.id if m else last
    for uname in CANDIDATES:
        await c.send_message(bf, uname)
        m = await wait_reply(c, bf, last); last = m.id if m else last
        txt = m.message if m else ""
        print(f"[{uname}] -> {txt[:80].replace(chr(10),' ')}")
        mt = re.search(r"(\d{8,10}:[A-Za-z0-9_-]{30,})", txt or "")
        if mt:
            return uname, mt.group(1)
        if "too many" in (txt or "").lower():
            print("RATE-LIMIT BotFather"); break
    return None, None


async def make_channel(c, bot_username):
    res = await c(functions.channels.CreateChannelRequest(
        title="Gift Tracker — Listings", about="NFT gift resale signals", broadcast=True, megagroup=False))
    ch = res.chats[0]
    rights = ChatAdminRights(post_messages=True, edit_messages=True, delete_messages=True,
                             invite_users=True, manage_call=False, other=True)
    await c(functions.channels.EditAdminRequest(
        channel=ch, user_id=bot_username, admin_rights=rights, rank="bot"))
    log_id = int(f"-100{ch.id}")
    return log_id, ch.id


async def main():
    c = TelegramClient(SESSION, API_ID, API_HASH)
    await c.connect()
    if not await c.is_user_authorized():
        print("СЕССИЯ НЕ АВТОРИЗОВАНА"); return
    me = await c.get_me(); print("session:", me.id, me.first_name)

    uname, token = await make_bot(c)
    if not token:
        print("BOT_TOKEN не получен"); await c.disconnect(); return
    print(f"\nBOT=@{uname}\nBOT_TOKEN={token}")

    log_id, raw = await make_channel(c, uname)
    print(f"LOG_CHAT_ID={log_id}  (channel raw id {raw}, бот @{uname} админ)")
    await c.disconnect()
    print("\n=== ДЛЯ .env ===")
    print(f"BOT_TOKEN={token}")
    print(f"LOG_CHAT_ID={log_id}")


asyncio.run(main())
