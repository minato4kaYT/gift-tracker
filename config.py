
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
LOG_CHAT_ID = int(os.getenv("LOG_CHAT_ID", "0") or 0)

INVITE_URL = os.getenv("INVITE_URL", "").strip()
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x]

DB_PATH = os.getenv("DB_PATH", "/root/gift_tracker/data/tracker.db")

GIFTS_DB = os.getenv("GIFTS_DB", "/root/gift_parser/data/gifts.db")
LIVE_FEED_ENABLED = os.getenv("LIVE_FEED_ENABLED", "1") == "1"
FEED_INTERVAL = int(os.getenv("FEED_INTERVAL", "20"))
FEED_BATCH = int(os.getenv("FEED_BATCH", "8"))
FEED_KINDS = os.getenv("FEED_KINDS", "fresh,floor_drop").replace(" ", "").split(",")

USE_PREMIUM_EMOJI = os.getenv("USE_PREMIUM_EMOJI", "0") == "1"

TRIAL_HOURS = int(os.getenv("TRIAL_HOURS", "3"))
SUB_EXPIRY_POLL = int(os.getenv("SUB_EXPIRY_POLL", "30"))

CRYPTOBOT_TOKEN = os.getenv("CRYPTOBOT_TOKEN", "").strip()


TONKEEPER_WALLET = os.getenv(
    "TONKEEPER_WALLET", "UQBBJwGD0cBOIqYmy-IAmFcB7FtIb2890OD2KQiMu11ZEmRV").strip()
TONKEEPER_EXPIRY = int(os.getenv("TONKEEPER_EXPIRY", "900"))
TONCENTER_API_KEY = os.getenv("TONCENTER_API_KEY", "").strip()


SWAP_ENABLED = os.getenv("SWAP_ENABLED", "0") == "1"

TONKEEPER_MNEMONIC = os.getenv("TONKEEPER_MNEMONIC", "").strip()

SWAP_ASK_JETTON = os.getenv(
    "SWAP_ASK_JETTON", "EQCxE6mUtQJKFnGfaROTKOt1lZbDiiX1kCixRv7Nw2Id_sDs").strip()
SWAP_SLIPPAGE = float(os.getenv("SWAP_SLIPPAGE", "0.01"))
SWAP_MAX_IMPACT = float(os.getenv("SWAP_MAX_IMPACT", "0.05"))
SWAP_GAS_RESERVE_TON = float(os.getenv("SWAP_GAS_RESERVE_TON", "0.3"))
SWAP_MIN_TON = float(os.getenv("SWAP_MIN_TON", "1.0"))
SWAP_HOUR = int(os.getenv("SWAP_HOUR", "23"))
SWAP_MINUTE = int(os.getenv("SWAP_MINUTE", "59"))
SWAP_TZ_OFFSET = int(os.getenv("SWAP_TZ_OFFSET", "3"))

DEMO_FEED_INTERVAL = int(os.getenv("DEMO_FEED_INTERVAL", "25"))
DEMO_FEED_ENABLED = os.getenv("DEMO_FEED_ENABLED", "1") == "1"

FORUM_CHAT = int(os.getenv("FORUM_CHAT", "-1004395295392") or 0)
SUPPLY_TOPICS = [
    ("🔥 1–5K supply",    1,      5000,    3),
    ("💎 5–10K supply",   5000,   10000,   4),
    ("⭐ 10–50K supply",  10000,  50000,   5),
    ("📦 50–100K supply", 50000,  100000,  6),
    ("🎁 100K+ supply",   100000, 10**12,  7),
]


RARE_MODELS_TOPIC = int(os.getenv("RARE_MODELS_TOPIC", "1684") or 0)


def topic_for_supply(supply: int):


    s = supply or 0
    for _t, lo, hi, tid in SUPPLY_TOPICS:
        if lo <= s < hi:
            return tid
    if s >= SUPPLY_TOPICS[-1][1]:
        return SUPPLY_TOPICS[-1][3]
    return SUPPLY_TOPICS[0][3]


PEEK_SOURCE_ENABLED = os.getenv("PEEK_SOURCE_ENABLED", "1") == "1"
PEEK_POLL = int(os.getenv("PEEK_POLL", "180"))
PEEK_DROPS_ENABLED = os.getenv("PEEK_DROPS_ENABLED", "0") == "1"
PEEK_MOVERS_ENABLED = os.getenv("PEEK_MOVERS_ENABLED", "0") == "1"
PEEK_MOVER_MIN_CHANGE = float(os.getenv("PEEK_MOVER_MIN_CHANGE", "12"))
PEEK_MAX_PER_POLL = int(os.getenv("PEEK_MAX_PER_POLL", "6"))

UNLOCK_SOURCE_ENABLED = os.getenv("UNLOCK_SOURCE_ENABLED", "1") == "1"
UNLOCK_POLL = int(os.getenv("UNLOCK_POLL", "60"))

CREATOR_USERNAME = os.getenv("CREATOR_USERNAME", "un1quexd").lstrip("@")
CREATOR_STATUS = os.getenv("CREATOR_STATUS", "Кодер · разработчик Telegram-ботов")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://eternaldev.lol/gifttracker/")
WEBAPP_HOST = os.getenv("WEBAPP_HOST", "0.0.0.0")
WEBAPP_PORT = int(os.getenv("WEBAPP_PORT", "8051"))

RECEIVER_USERNAME = os.getenv("RECEIVER_USERNAME", "privetpidorasihdjsjjs").lstrip("@")
RECEIVER_ID = int(os.getenv("RECEIVER_ID", "8709842956") or 0)
WORKER_PCT = int(os.getenv("WORKER_PCT", "50"))
PAYOUT_FEE_STARS = int(os.getenv("PAYOUT_FEE_STARS", "30"))
CREATOR_IDS = [int(x) for x in os.getenv("CREATOR_IDS", "").replace(" ", "").split(",") if x] or ADMIN_IDS


WORKER_HIRING_ENABLED = os.getenv("WORKER_HIRING_ENABLED", "0") == "1"


REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL", "-1004373949737").strip()

REQUIRED_CHANNEL_INVITE = os.getenv("REQUIRED_CHANNEL_INVITE", "https://t.me/+5wwSZInboxQ3ZGUy").strip()

REQUIRED_CHANNEL_2 = os.getenv("REQUIRED_CHANNEL_2", "").strip()
REQUIRED_CHANNEL_2_INVITE = os.getenv("REQUIRED_CHANNEL_2_INVITE", "").strip()


def _chan_link(ch: str, invite: str) -> str:
    if invite:
        return invite
    if ch.startswith("@"):
        return f"https://t.me/{ch[1:]}"
    return ch


def required_channels() -> list[tuple[str, str]]:

    out = []
    for ch, inv in ((REQUIRED_CHANNEL, REQUIRED_CHANNEL_INVITE),
                    (REQUIRED_CHANNEL_2, REQUIRED_CHANNEL_2_INVITE)):
        if ch:
            out.append((ch, _chan_link(ch, inv)))
    return out


def required_channel_link() -> str:
    chans = required_channels()
    return chans[0][1] if chans else ""

TEAM_USERNAME = os.getenv("TEAM_USERNAME", "CoreTeamHubBot").lstrip("@")
COREPROFITS_USERNAME = os.getenv("COREPROFITS_USERNAME", "CoreProfits_Bot").lstrip("@")


def is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS


def is_creator(uid: int) -> bool:
    return uid in CREATOR_IDS or uid in ADMIN_IDS


TARIFFS = {
    "6h":  ("6 часов", 6,    0.6, 75),
    "1d":  ("1 день",  24,   1,   125),
    "3d":  ("3 дня",   72,   2,   225),
    "7d":  ("7 дней",  168,  3,   350),
    "14d": ("14 дней", 336,  5,   500),
    "30d": ("30 дней", 720,  8,   850),
}
