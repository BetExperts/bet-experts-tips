# -*- coding: utf-8 -*-
"""Selectie van tips uit de H2H-stats + opbouw van de Webflow-velddata."""
import re, unicodedata
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from tp_config import (MARKT, MARKT_FIELD, ZEKERHEID, STATUS, LEAGUES, MIN_H2H, MIN_STREAK, BOOKMAKER_REF)

NL = ZoneInfo("Europe/Amsterdam")

def slugify(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s.lower())).strip("-")

def _local(iso):
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(NL)

def _zekerheid(pct, streak):
    if pct >= 85 and streak >= 4: return "Hoog"
    if pct >= 77: return "Middel"
    return "Laag"

# markt -> (voorwaarde(stat,thr) -> bool, tip_text_fn, onderbouwing_fn, pct_key, streak_key)
def _candidates(st, thr):
    out = []
    n, sn = st["n"], st["same_n"]
    def add(markt, ok, tip, ond, pct, streak, odds_key):
        if ok: out.append((markt, tip, ond, pct, streak, odds_key))
    add("BTTS", n >= MIN_H2H and st["btts_pct"] >= thr and st["btts_streak"] >= MIN_STREAK,
        "Beide teams scoren", f'{st["btts"]} van {n} onderlinge duels BTTS',
        st["btts_pct"], st["btts_streak"], "btts_yes")
    add("Over 2.5", n >= MIN_H2H and st["o25_pct"] >= thr and st["o25_streak"] >= MIN_STREAK,
        "Meer dan 2.5 doelpunten", f'{st["o25"]} van {n} duels over 2.5',
        st["o25_pct"], st["o25_streak"], "over25")
    add("Under 2.5", n >= MIN_H2H and st["under_pct"] >= thr and st["under_streak"] >= MIN_STREAK,
        "Minder dan 2.5 doelpunten", f'{st["under"]} van {n} duels onder 2.5',
        st["under_pct"], st["under_streak"], "under25")
    # 1X2 (thuis- of uitwinst; markt heet 1X2, de tip zegt welke kant)
    add("1X2", sn >= 3 and st["home_w_pct"] >= thr and st["home_w_streak"] >= MIN_STREAK,
        f'{st["home"]} wint', f'{st["home"]} won {st["home_w"]} van {sn} thuisduels tegen {st["away"]}',
        st["home_w_pct"], st["home_w_streak"], "home")
    add("1X2", sn >= 3 and st["away_w_pct"] >= thr and st["away_w_streak"] >= MIN_STREAK,
        f'{st["away"]} wint', f'{st["away"]} won {st["away_w"]} van {sn} uitduels bij {st["home"]}',
        st["away_w_pct"], st["away_w_streak"], "away")
    return out

def select(st, thr):
    """Return lijst van tip-dicts voor deze wedstrijd (kan meerdere markten zijn)."""
    tips = []
    for markt, tip, ond, pct, streak, odds_key in _candidates(st, thr):
        tips.append({"markt": markt, "tip": tip, "onderbouwing": ond, "odds_key": odds_key,
                     "pct": pct, "streak": streak, "zekerheid": _zekerheid(pct, streak)})
    return tips

def _berekening(st, t):
    dt = _local(st["date"])
    lines = [f'<p><strong>{t["tip"]}</strong> — {t["onderbouwing"]} '
             f'(reeks van {t["streak"]} op rij).</p>']
    lines.append("<ul>"
        f'<li>BTTS in H2H: {st["btts"]}/{st["n"]} ({st["btts_pct"]}%), streak {st["btts_streak"]}</li>'
        f'<li>Over 2.5 in H2H: {st["o25"]}/{st["n"]} ({st["o25_pct"]}%), streak {st["o25_streak"]}</li>'
        f'<li>Thuis-oriëntatie ({st["home"]} thuis): BTTS {st["same_btts"]}/{st["same_n"]}, '
        f'thuiswinst {st["home_w"]}/{st["same_n"]}</li>'
        + (f'<li>Vorm {st["home"]}: {st["form_home"]}</li>' if st.get("form_home") else "")
        + (f'<li>Vorm {st["away"]}: {st["form_away"]}</li>' if st.get("form_away") else "")
        + "</ul>")
    return "".join(lines)

def _odds_richtext(odds):
    if not odds: return ""
    items = "".join(f"<li>{r[0]}: {r[1]:.2f}</li>" for r in odds["all"])
    return f"<p>Beste odd <strong>{odds['best']:.2f}</strong> bij {odds['bookmaker']}.</p><ul>{items}</ul>"

def build_fielddata(st, t, league_slug, odds=None, now=None):
    now = now or datetime.now(NL)
    dt = _local(st["date"])
    comp = LEAGUES.get(league_slug, league_slug)
    tip_text = t["tip"]
    name = f'{st["home"]} - {st["away"]}: {tip_text}'
    slug = slugify(f'{t["markt"]}-{st["home"]}-{st["away"]}-{dt:%Y-%m-%d}')

    # thuis-oriëntatie afhankelijk van de pick
    if t.get("odds_key") == "home":
        orient = f'{st["home_w"]}/{st["same_n"]} thuiswinst'
    elif t.get("odds_key") == "away":
        orient = f'{st["away_w"]}/{st["same_n"]} uitwinst'
    else:
        orient = f'{st["same_btts"]}/{st["same_n"]} BTTS thuis'

    fd = {
        "name": name, "slug": slug,
        "wedstrijd": f'{st["home"]} - {st["away"]}',
        "tip": tip_text,
        "onderbouwing": t["onderbouwing"],
        "berekening": _berekening(st, t),
        MARKT_FIELD: MARKT[t["markt"]],
        "zekerheid": ZEKERHEID[t["zekerheid"]],
        "status": STATUS["In afwachting"],
        "fixture-id": str(st["fixture_id"]),
        "home-team-id": str(st["hid"]), "away-team-id": str(st["aid"]),
        "thuisclub": st["home"], "uitclub": st["away"],
        "competitie": comp, "league-slug": league_slug,
        "datum-tijd-wedstrijd": dt.isoformat(),
        "tijd-wedstrijd": f"{dt:%H:%M}",
        "tipdatum": dt.replace(hour=0, minute=0, second=0, microsecond=0).isoformat(),
        "publicatiedatum": now.astimezone(timezone.utc).isoformat(),
        "h2h-aantal-duels": st["n"],
        "h2h-laatste-5": t["onderbouwing"],
        "btts-percentage": st["btts_pct"], "btts-streak": st["btts_streak"],
        "over-2-5-percentage": st["o25_pct"], "over-2-5-streak": st["o25_streak"],
        "thuis-orientatie": orient,
        "vorm-thuisclub": st.get("form_home", ""), "vorm-uitclub": st.get("form_away", ""),
    }
    if odds:
        fd["beste-odd"] = f'{odds["best"]:.2f}'
        fd["beste-odd-bookmaker"] = odds["bookmaker"]     # tekst (gemak; ref is de bron)
        fd["odds-bijgewerkt"] = now.astimezone(timezone.utc).isoformat()
        ref = BOOKMAKER_REF.get(odds.get("key"))
        if ref:
            fd["bookmaker"] = ref     # reference -> Bookmakers (logo + affiliatelink)
    return fd, slug, name
