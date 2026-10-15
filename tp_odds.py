# -*- coding: utf-8 -*-
"""Haalt live NL-odds op uit de eigen tubeemate-feed en bindt de beste odd aan een pick."""
import re, time, requests
from tp_config import TUBE_URL, TUBE_HEADERS, FEEDS, BOOKMAKERS
from tp_api import team_match

S = requests.Session()
_CACHE = {}   # bm -> [events]

# Jeugdteams (U15 t/m U23) mogen in Nederland niet aangeboden worden. Sommige feeds
# (Altenar: StarCasino, OneCasino) bevatten ze toch, dus die events slaan we altijd over.
_YOUTH = re.compile(r"\b(?:u|o|under|onder)[\s-]?(?:1[5-9]|2[0-3])\b", re.I)

def is_youth(name):
    return bool(_YOUTH.search(name or ""))

def load_all():
    """Haal per bookmaker alle prematch-events op (1x2, over_under_2.5, btts)."""
    _CACHE.clear()
    for bm in FEEDS:
        url = (f"{TUBE_URL}?action=prematch&sport=football"
               f"&markets=1x2,over_under_2.5,btts&bookmaker={bm}&ts={int(time.time())}")
        try:
            r = S.get(url, headers=TUBE_HEADERS, timeout=40)
            d = r.json() if r.status_code == 200 else {}
        except Exception:
            d = {}
        events = d.get("events", []) if isinstance(d, dict) else []
        _CACHE[bm] = [ev for ev in events
                      if not (is_youth(ev.get("home")) or is_youth(ev.get("away")))]
    return sum(len(v) for v in _CACHE.values())

def _outcome(ev, market, pick):
    mk = (ev.get("markets") or {}).get(market)
    if not mk: return None
    for o in mk.get("outcomes", []):
        name = (o.get("name") or "").strip()
        odd = o.get("odd") or o.get("odds") or o.get("price")
        try: odd = float(odd)
        except: continue
        if odd < 1.01 or odd > 100: continue
        low = name.lower()
        if pick == "btts_yes" and low in ("yes", "ja"): return odd
        if pick == "over25" and low.startswith("over"): return odd
        if pick == "under25" and low.startswith("under"): return odd
        if pick == "home" and team_match(name, ev.get("home", "")): return odd
        if pick == "away" and team_match(name, ev.get("away", "")): return odd
    return None

# odds_key -> tubeemate-markt
_MARKET = {"btts_yes": "btts", "over25": "over_under_2.5", "under25": "over_under_2.5",
           "home": "1x2", "away": "1x2"}

def odds_for(home, away, odds_key):
    """Return beste odd (+ bookmaker/link/all) voor deze pick, o.b.v. odds_key."""
    market = _MARKET.get(odds_key)
    if not market: return None
    pick = odds_key
    rows = []
    for bm, events in _CACHE.items():
        for ev in events:
            if team_match(ev.get("home", ""), home) and team_match(ev.get("away", ""), away):
                odd = _outcome(ev, market, pick)
                if odd:
                    # eigen affiliatelink heeft voorrang op de kale feed-url
                    link = BOOKMAKERS.get(bm, {}).get("link") or ev.get("affiliate_url", "")
                    rows.append((BOOKMAKERS.get(bm, {}).get("name", bm), odd, link, bm))
                break
    if not rows: return None
    rows.sort(key=lambda x: -x[1])
    best_name, best_odd, best_link, best_key = rows[0]
    return {"best": best_odd, "bookmaker": best_name, "link": best_link,
            "key": best_key, "all": rows}


def _all_outcomes(ev, market, home, away):
    """{key: odd} voor alle uitkomsten van één markt bij één bookmaker."""
    mk = (ev.get("markets") or {}).get(market)
    if not mk: return {}
    out = {}
    for o in mk.get("outcomes", []):
        name = (o.get("name") or "").strip(); low = name.lower()
        odd = o.get("odd") or o.get("odds") or o.get("price")
        try: odd = float(odd)
        except Exception: continue
        if odd < 1.01 or odd > 100: continue
        if market == "btts":
            if low in ("yes", "ja"): out["btts_yes"] = odd
            elif low in ("no", "nee"): out["btts_no"] = odd
        elif market == "over_under_2.5":
            if low.startswith("over"): out["over25"] = odd
            elif low.startswith("under"): out["under25"] = odd
        elif market == "1x2":
            if low in ("draw", "x", "gelijk", "gelijkspel"): out["draw"] = odd
            elif team_match(name, ev.get("home", "")): out["home"] = odd
            elif team_match(name, ev.get("away", "")): out["away"] = odd
    return out


_SETS = {"1x2": ("home", "draw", "away"), "btts": ("btts_yes", "btts_no"),
         "over_under_2.5": ("over25", "under25")}


def market_fair(home, away):
    """Eerlijke kansen volgens de markt: per bookmaker de marge eruit (1/odd genormaliseerd),
    daarna het gemiddelde over alle bookmakers met een complete markt. {key: kans} + aantal books."""
    acc = {}; n = {}
    for bm, events in _CACHE.items():
        for ev in events:
            if team_match(ev.get("home", ""), home) and team_match(ev.get("away", ""), away):
                for market, keys in _SETS.items():
                    o = _all_outcomes(ev, market, home, away)
                    if not all(k in o for k in keys):
                        continue
                    inv = {k: 1 / o[k] for k in keys}; s = sum(inv.values())
                    if not (1.0 <= s <= 1.25):            # onzin-marge (verkeerde koppeling) overslaan
                        continue
                    for k in keys:
                        acc[k] = acc.get(k, 0) + inv[k] / s; n[k] = n.get(k, 0) + 1
                break
    return {k: acc[k] / n[k] for k in acc}, (min(n.values()) if n else 0)
