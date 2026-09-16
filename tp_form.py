# -*- coding: utf-8 -*-
"""Vorm-signaal: recente-wedstrijd-percentages per team (BTTS, over 2.5, winst)."""
import tp_api as api
from tp_config import N_FORM

FIN = ("FT", "AET", "PEN")
_CACHE = {}   # team-id -> rates dict

def _finished(f):
    st = (f.get("fixture", {}).get("status", {}) or {}).get("short")
    g = f.get("goals", {}) or {}
    return st in FIN and g.get("home") is not None and g.get("away") is not None

def rates(tid, n=N_FORM):
    """Percentages over de laatste n afgeronde wedstrijden van dit team."""
    if tid in _CACHE:
        return _CACHE[tid]
    fixtures = [f for f in api.team_form(tid) if _finished(f)]
    fixtures.sort(key=lambda f: f["fixture"]["date"], reverse=True)
    recent = fixtures[:n]
    tot = len(recent)
    btts = over = win = loss = scored = 0
    form = ""
    for f in recent:
        g = f["goals"]; t = f["teams"]
        home = str(t["home"]["id"]) == str(tid)
        my, opp = (g["home"], g["away"]) if home else (g["away"], g["home"])
        if g["home"] > 0 and g["away"] > 0: btts += 1
        if g["home"] + g["away"] > 2.5: over += 1
        if my > opp: win += 1
        elif my < opp: loss += 1
        if my > 0: scored += 1
    def pct(x): return round(100 * x / tot) if tot else 0
    for f in list(reversed(recent))[-5:]:   # laatste 5 chronologisch voor de vormstring
        g = f["goals"]; t = f["teams"]
        home = str(t["home"]["id"]) == str(tid)
        my, opp = (g["home"], g["away"]) if home else (g["away"], g["home"])
        form += "W" if my > opp else ("L" if my < opp else "G")
    r = {"n": tot, "btts": pct(btts), "over25": pct(over), "under25": pct(tot - over),
         "win": pct(win), "loss": pct(loss), "scored": pct(scored), "form": form}
    _CACHE[tid] = r
    return r

def signal(hid, aid):
    """Gecombineerde vorm-percentages voor de wedstrijd (thuis vs uit)."""
    h, a = rates(hid), rates(aid)
    def avg(x, y): return round((x + y) / 2)
    return {
        "btts": avg(h["btts"], a["btts"]),
        "over25": avg(h["over25"], a["over25"]),
        "under25": avg(h["under25"], a["under25"]),
        "home_win": avg(h["win"], a["loss"]),   # thuis wint vaak + uit verliest vaak
        "away_win": avg(a["win"], h["loss"]),
        "form_home": h["form"], "form_away": a["form"],
        "h": h, "a": a,
    }
