# -*- coding: utf-8 -*-
"""Haalt live NL-odds op uit de eigen tubeemate-feed en bindt de beste odd aan een pick."""
import time, requests
from tp_config import TUBE_URL, TUBE_HEADERS, FEEDS, BOOKMAKERS
from tp_api import team_match

S = requests.Session()
_CACHE = {}   # bm -> [events]

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
        _CACHE[bm] = d.get("events", []) if isinstance(d, dict) else []
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

# pick -> (market, pick-key)
PICK = {
    "BTTS":       ("btts", "btts_yes"),
    "Over 2.5":   ("over_under_2.5", "over25"),
    "Under 2.5":  ("over_under_2.5", "under25"),
    "Thuiswinst": ("1x2", "home"),
    "Uitwinst":   ("1x2", "away"),
}

def odds_for(home, away, markt):
    """Return (beste_odd, bm_naam, link, [(bm_naam, odd, link)...]) voor deze pick."""
    if markt not in PICK: return None
    market, pick = PICK[markt]
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
