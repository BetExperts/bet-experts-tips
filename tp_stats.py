# -*- coding: utf-8 -*-
"""Berekent H2H-trends per wedstrijd voor alle markten."""
import tp_api as api

FIN = ("FT", "AET", "PEN")

def _finished(h):
    st = (h.get("fixture", {}).get("status", {}) or {}).get("short")
    g = h.get("goals", {}) or {}
    return st in FIN and g.get("home") is not None and g.get("away") is not None

def _btts(h): g = h["goals"]; return g["home"] > 0 and g["away"] > 0
def _tot(h):  g = h["goals"]; return g["home"] + g["away"]

def _streak(lst, cond):
    s = 0
    for h in lst:
        if cond(h): s += 1
        else: break
    return s

def _form_string(fixtures, tid):
    done = [f for f in fixtures if _finished(f)]
    done.sort(key=lambda f: f["fixture"]["date"])
    out = ""
    for f in done[-5:]:
        t = f["teams"]; g = f["goals"]
        home = str(t["home"]["id"]) == str(tid)
        my, opp = (g["home"], g["away"]) if home else (g["away"], g["home"])
        out += "W" if my > opp else ("L" if my < opp else "G")
    return out

def analyse(fx, want_form=True):
    teams = fx["teams"]; fixture = fx["fixture"]; league = fx.get("league", {})
    hid, aid = teams["home"]["id"], teams["away"]["id"]
    hn, an = teams["home"]["name"], teams["away"]["name"]

    hl = [h for h in api.h2h(hid, aid) if _finished(h)]
    hl.sort(key=lambda h: h["fixture"]["date"], reverse=True)   # nieuwste eerst
    n = len(hl)
    btts = sum(1 for h in hl if _btts(h))
    o25 = sum(1 for h in hl if _tot(h) > 2.5)
    under = n - o25

    # zelfde oriëntatie: huidige thuisploeg ook thuis
    same = [h for h in hl if h["teams"]["home"]["id"] == hid]
    same_btts = sum(1 for h in same if _btts(h))
    home_w = sum(1 for h in same if h["goals"]["home"] > h["goals"]["away"])
    away_w = sum(1 for h in same if h["goals"]["home"] < h["goals"]["away"])
    draw = len(same) - home_w - away_w

    # algemene onderlinge dominantie: wie won het duel, ongeacht thuis/uit
    def _winner(h):
        gh, ga = h["goals"]["home"], h["goals"]["away"]
        if gh == ga: return None
        return h["teams"]["home"]["id"] if gh > ga else h["teams"]["away"]["id"]
    h_wins = sum(1 for h in hl if _winner(h) == hid)   # huidige thuisploeg won (thuis of uit)
    a_wins = sum(1 for h in hl if _winner(h) == aid)   # huidige uitploeg won (thuis of uit)

    def pct(x, tot): return round(100 * x / tot) if tot else 0

    form_h = form_a = ""
    if want_form:
        form_h = _form_string(api.team_form(hid), hid)
        form_a = _form_string(api.team_form(aid), aid)

    return {
        "fixture_id": fixture["id"], "home": hn, "away": an, "hid": hid, "aid": aid,
        "home_logo": teams["home"].get("logo"), "away_logo": teams["away"].get("logo"),
        "date": fixture["date"], "kickoff": fixture["date"],
        "n": n, "same_n": len(same),
        "btts": btts, "btts_pct": pct(btts, n), "btts_streak": _streak(hl, _btts),
        "o25": o25, "o25_pct": pct(o25, n), "o25_streak": _streak(hl, lambda h: _tot(h) > 2.5),
        "under": under, "under_pct": pct(under, n), "under_streak": _streak(hl, lambda h: _tot(h) <= 2.5),
        "same_btts": same_btts, "same_btts_streak": _streak(same, _btts),
        "home_w": home_w, "away_w": away_w, "draw": draw,
        "home_w_pct": pct(home_w, len(same)), "away_w_pct": pct(away_w, len(same)),
        "home_w_streak": _streak(same, lambda h: h["goals"]["home"] > h["goals"]["away"]),
        "away_w_streak": _streak(same, lambda h: h["goals"]["home"] < h["goals"]["away"]),
        # algemene onderlinge winst (thuis + uit samen)
        "h_wins": h_wins, "a_wins": a_wins,
        "h_win_pct": pct(h_wins, n), "a_win_pct": pct(a_wins, n),
        "h_win_streak": _streak(hl, lambda h: _winner(h) == hid),
        "a_win_streak": _streak(hl, lambda h: _winner(h) == aid),
        "form_home": form_h, "form_away": form_a,
    }
