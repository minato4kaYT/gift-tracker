/* Gift Tracker — Mini App (инфо о проекте + автор) */
const API = "/api/gifttracker";
const tg = window.Telegram?.WebApp;
let INIT = "";
try { tg?.ready(); tg?.expand(); tg?.setHeaderColor?.("#09090b"); tg?.setBackgroundColor?.("#09090b"); } catch (e) {}
INIT = tg?.initData || "";

const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);
let BOT = "GiftTrackerHubBot";
let CREATOR = "un1quexd";

async function load() {
  let s = null;
  try {
    const r = await fetch(API + "/state", { headers: { "X-Init-Data": INIT } });
    s = await r.json();
  } catch (e) { return; }
  if (!s || !s.ok) return;
  BOT = s.bot || BOT;
  const pct = s.pct || 50, fee = s.fee || 30;
  $$(".pct").forEach((el) => el.textContent = pct + "%");
  $$(".fee").forEach((el) => el.textContent = fee);
  const cr = s.creator || {};
  CREATOR = (cr.username || CREATOR).replace(/^@/, "");
  $("#crName").textContent = "@" + CREATOR;
  if (cr.status) $("#crStatus").textContent = cr.status;
  $("#crLink").href = "https://t.me/" + CREATOR;
}

// CTA → открыть бота
$("#ctaBot").onclick = () => {
  tg?.HapticFeedback?.impactOccurred?.("medium");
  const url = "https://t.me/" + BOT;
  if (tg?.openTelegramLink) tg.openTelegramLink(url); else window.open(url, "_blank");
};

load();
