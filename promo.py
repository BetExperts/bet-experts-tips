# -*- coding: utf-8 -*-
"""Dagelijkse promo-agent: rendert een template-afbeelding + post een teaser naar
Telegram met knop naar de juiste hub. Wisselt af tussen algemeen en per markt.

  python3 promo.py --dry     # kies + render naar promo_preview.png, niets posten
  python3 promo.py --test    # post naar TELEGRAM_TEST_CHAT
  python3 promo.py           # post naar het kanaal
"""
import os, sys, json, argparse, random
from datetime import datetime
from zoneinfo import ZoneInfo

import tp_webflow as WF
import promo_templates as T
from tp_config import MARKT

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHANNEL   = os.environ.get("TELEGRAM_CHANNEL") or "@BetExpertsGroup"
TELEGRAM_TEST_CHAT = os.environ.get("TELEGRAM_TEST_CHAT", "").strip()

NL = ZoneInfo("Europe/Amsterdam")
BASE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(BASE, "state", "promo.json")
IMG = os.path.join(BASE, "promo_preview.png")
MARKT_NAAM = {v: k for k, v in MARKT.items()}
ORDER = ["general", "over25", "btts", "1x2"]   # afwisseling
MARKT_KEY = {"BTTS": "btts", "Over 2.5": "over25", "1X2": "1x2"}

DISC = "\n\n<i>Wat kost gokken jou? Stop op tijd. 18+ | Speel bewust.</i>"

def load_state():
    try: return json.load(open(STATE, encoding="utf-8"))
    except Exception: return {"i": -1}

def save_state(s):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    json.dump(s, open(STATE, "w", encoding="utf-8"))

def _short_reason(fd):
    return (fd.get("onderbouwing") or "").split(" · ")[0]

def pick_featured(items, today, market_key):
    """Beste uitgelichte tip van vandaag voor deze markt (korte naam eerst, dan hoge odd)."""
    cand = []
    for it in items:
        fd = it["fieldData"]
        if not fd.get("uitgelicht"): continue
        if (fd.get("tipdatum") or "")[:10] != today: continue
        if MARKT_KEY.get(MARKT_NAAM.get(fd.get("markt-2"))) != market_key: continue
        try: odd = float(fd.get("beste-odd") or 0)
        except: odd = 0
        cand.append((len(T._shorten(fd.get("wedstrijd", ""))), -odd, fd))
    cand.sort(key=lambda x: (x[0], x[1]))
    return cand[0][2] if cand else None

def render(html_inner):
    from playwright.sync_api import sync_playwright
    doc = ('<!doctype html><html><head><meta charset="utf-8">'
           '<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@600;700;800'
           '&family=Plus+Jakarta+Sans:wght@400;600;700&display=swap" rel="stylesheet"></head>'
           f'<body>{html_inner}</body></html>')
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1200, "height": 630}, device_scale_factor=2)
        pg.set_content(doc, wait_until="networkidle")
        pg.wait_for_timeout(500)
        pg.screenshot(path=IMG, clip={"x": 0, "y": 0, "width": 1200, "height": 630})
        b.close()
    return IMG

def caption(kind, fd, has_any):
    if kind == "general" and not has_any:
        return ("📅 <b>Wedtips</b> — vandaag staat er weinig op het programma. "
                "Bekijk vast de beste onderbouwde tips voor de <b>komende dagen</b>: BTTS, "
                "Over/Under 2.5 en 1X2, met de hoogste odd." + DISC)
    if kind == "general":
        return ("📊 <b>De wedtips van vandaag staan klaar!</b>\n"
                "Per markt de sterkste, 100% op data onderbouwde tips — BTTS, Over/Under 2.5 en 1X2, "
                "elk met de hoogste odd van alle vergunde bookmakers. Stel je lijstje samen 👇" + DISC)
    match = T._shorten(fd.get("wedstrijd", "")); reason = _short_reason(fd); odd = fd.get("beste-odd")
    intro = {"btts": "⚽ <b>BTTS-tip van de dag</b>", "over25": "🥅 <b>Doelpunten-tip van de dag</b>",
             "1x2": "🎯 <b>1X2-tip van de dag</b>"}[kind]
    tail = {"btts": "Bekijk alle BTTS-tips van vandaag", "over25": "Bekijk alle Over/Under 2.5-tips van vandaag",
            "1x2": "Bekijk alle 1X2-tips van vandaag"}[kind]
    return f"{intro}\n<b>{match}</b> — {reason} @ <b>{odd}</b>.\n{tail} 👇{DISC}"

def send(img, cap, url, test=False):
    import requests
    chat = TELEGRAM_TEST_CHAT if test else TELEGRAM_CHANNEL
    if not TELEGRAM_BOT_TOKEN or (test and not TELEGRAM_TEST_CHAT):
        print("  · Telegram overgeslagen (token/chat ontbreekt)."); return False
    api = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    data = {"chat_id": chat, "caption": cap, "parse_mode": "HTML",
            "reply_markup": json.dumps({"inline_keyboard": [[{"text": "Bekijk de tips →", "url": url}]]})}
    with open(img, "rb") as f:
        r = requests.post(api, data=data, files={"photo": f}, timeout=30)
    r.raise_for_status(); return True

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true"); ap.add_argument("--test", action="store_true")
    ap.add_argument("--kind", choices=ORDER, help="forceer een type")
    a = ap.parse_args()

    today = datetime.now(NL).date().isoformat()
    items = WF.list_items()
    has_any = any((it["fieldData"].get("tipdatum") or "")[:10] == today for it in items)

    st = load_state()
    kind = a.kind or ORDER[(st.get("i", -1) + 1) % len(ORDER)]

    fd = None
    if kind != "general":
        fd = pick_featured(items, today, kind)
        if not fd:                    # geen uitgelichte tip in deze markt → algemeen
            print(f"  · geen uitgelichte {kind}-tip vandaag → algemene template")
            kind = "general"
    if not has_any:
        kind = "general"

    if kind == "general":
        html = T.general_html(); url = T.GENERAL["url"]
    else:
        html = T.market_html(kind, fd["fieldData"]["wedstrijd"], _short_reason(fd["fieldData"]), fd["fieldData"]["beste-odd"])
        url = T.MARKETS[kind]["url"]
    cap = caption(kind, fd["fieldData"] if fd else None, has_any)

    print(f"Type: {kind} | {'tip: '+fd['fieldData']['wedstrijd'] if fd else 'algemeen'}")
    render(html)
    print(f"Afbeelding: {IMG}")
    if a.dry:
        print("caption:\n" + cap); return
    if send(IMG, cap, url, test=a.test):
        print(f"✔ Gepost{' (TEST)' if a.test else ''}.")
    if not a.kind:                    # alleen bij automatische afwisseling de teller opschuiven
        st["i"] = (st.get("i", -1) + 1) % len(ORDER); st["last"] = today; save_state(st)

if __name__ == "__main__":
    main()
