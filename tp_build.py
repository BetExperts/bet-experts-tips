# -*- coding: utf-8 -*-
"""Selectie van tips uit de H2H-stats + opbouw van de Webflow-velddata."""
import re, unicodedata
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from tp_config import (MARKT, MARKT_FIELD, ZEKERHEID, STATUS, LEAGUES, MIN_H2H, MIN_STREAK,
                       BOOKMAKER_REF, H2H_STRONG, H2H_MODERATE, FORM_SUPPORT, FORM_FEATURE,
                       FORM_FLOOR_1X2, N_FORM)

NL = ZoneInfo("Europe/Amsterdam")

def slugify(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s.lower())).strip("-")

def _local(iso):
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(NL)

def _best_1x2(pct_v, streak_v, n_v, desc_v, pct_o, streak_o, n_o, desc_o):
    """Kies voor een 1X2-pick de sterkste onderbouwing:
    - venue: winst in dezelfde thuis/uit-opstelling (min 3 duels)
    - algemeen: winst in ALLE onderlinge duels, thuis én uit (min MIN_H2H)
    Retourneert (h2h_n, h2h_pct, h2h_streak, desc, min_n). Bij twijfel het hoogste
    percentage; gelijk → langste streak. Voldoet geen van beide aan zijn drempel,
    dan de algemene (faalt daarna netjes op min_n)."""
    cands = []
    if n_o >= MIN_H2H: cands.append((n_o, pct_o, streak_o, desc_o, MIN_H2H))
    if n_v >= 3:       cands.append((n_v, pct_v, streak_v, desc_v, 3))
    if not cands:
        return (n_o, pct_o, streak_o, desc_o, MIN_H2H)
    cands.sort(key=lambda c: (c[1], c[2]), reverse=True)   # hoogste pct, dan streak
    return cands[0]

def _specs(st, form):
    n, sn = st["n"], st["same_n"]
    hb = _best_1x2(st["home_w_pct"], st["home_w_streak"], sn,
                   f'{st["home"]} won {st["home_w"]} van {sn} thuisduels',
                   st["h_win_pct"], st["h_win_streak"], n,
                   f'{st["home"]} won {st["h_wins"]} van {n} onderlinge duels')
    ab = _best_1x2(st["away_w_pct"], st["away_w_streak"], sn,
                   f'{st["away"]} won {st["away_w"]} van {sn} uitduels',
                   st["a_win_pct"], st["a_win_streak"], n,
                   f'{st["away"]} won {st["a_wins"]} van {n} onderlinge duels')
    return [
        ("BTTS", "Beide teams scoren", "btts_yes", n, st["btts_pct"], st["btts_streak"],
         form["btts"] if form else 0, f'{st["btts"]} van {n} H2H BTTS', MIN_H2H),
        ("Over 2.5", "Meer dan 2.5 doelpunten", "over25", n, st["o25_pct"], st["o25_streak"],
         form["over25"] if form else 0, f'{st["o25"]} van {n} H2H over 2.5', MIN_H2H),
        ("Under 2.5", "Minder dan 2.5 doelpunten", "under25", n, st["under_pct"], st["under_streak"],
         form["under25"] if form else 0, f'{st["under"]} van {n} H2H onder 2.5', MIN_H2H),
        ("1X2", f'{st["home"]} wint', "home", hb[0], hb[1], hb[2],
         form["home_win"] if form else 0, hb[3], hb[4]),
        ("1X2", f'{st["away"]} wint', "away", ab[0], ab[1], ab[2],
         form["away_win"] if form else 0, ab[3], ab[4]),
    ]

def has_prospect(st):
    """Is er minstens één markt met genoeg H2H (matig+) om überhaupt te kwalificeren?
    Zo niet, hoeven we de vorm niet op te halen."""
    for _, _, _, h2h_n, h2h_pct, _, _, _, min_n in _specs(st, None):
        if h2h_n >= min_n and h2h_pct >= H2H_MODERATE:
            return True
    return False

def _decide(h2h_n, h2h_pct, h2h_streak, form_pct, min_n, form_floor=0):
    """H2H = basis. Sterke H2H kwalificeert; matige H2H alleen mét sterke vorm.
    (Streak is geen harde eis — telt mee in de ranking/uitgelicht.)
    form_floor: minimale vorm ook bij sterke H2H (voor 1X2 win-tips)."""
    if h2h_n < min_n or form_pct < form_floor:
        return (False, False, None, None)
    strong = h2h_pct >= H2H_STRONG
    moderate = (H2H_MODERATE <= h2h_pct < H2H_STRONG) and form_pct >= FORM_SUPPORT
    if not (strong or moderate):
        return (False, False, None, None)
    feature = strong and form_pct >= FORM_FEATURE
    zek = "Hoog" if feature else "Middel"
    basis = "h2h" if strong else "h2h+vorm"
    return (True, feature, zek, basis)

def select(st, form):
    """Return lijst van tip-dicts. H2H is leidend, vorm bevestigt."""
    out = []
    for markt, tip, key, h2h_n, h2h_pct, h2h_streak, form_pct, h2h_desc, min_n in _specs(st, form):
        floor = FORM_FLOOR_1X2 if key in ("home", "away") else 0
        qual, feature, zek, basis = _decide(h2h_n, h2h_pct, h2h_streak, form_pct, min_n, floor)
        if not qual:
            continue
        ond = f'{h2h_desc} · vorm {form_pct}%'
        out.append({"markt": markt, "tip": tip, "onderbouwing": ond, "odds_key": key,
                    "h2h_pct": h2h_pct, "h2h_streak": h2h_streak, "form_pct": form_pct,
                    "zekerheid": zek, "feature": feature, "basis": basis})
    return out

_BASIS_TXT = {"h2h": "sterke onderlinge reeks", "h2h+vorm": "onderlinge reeks bevestigd door de vorm"}

def _berekening(st, t):
    basis = _BASIS_TXT.get(t.get("basis"), "statistiek")
    lines = [f'<p><strong>{t["tip"]}</strong> — {t["onderbouwing"]} (op basis van {basis}).</p>']
    lines.append("<ul>"
        f'<li>H2H BTTS: {st["btts"]}/{st["n"]} ({st["btts_pct"]}%), streak {st["btts_streak"]}</li>'
        f'<li>H2H Over 2.5: {st["o25"]}/{st["n"]} ({st["o25_pct"]}%), streak {st["o25_streak"]}</li>'
        f'<li>Thuis-oriëntatie ({st["home"]} thuis): BTTS {st["same_btts"]}/{st["same_n"]}, '
        f'thuiswinst {st["home_w"]}/{st["same_n"]}</li>'
        f'<li>Onderlinge winst (alle duels): {st["home"]} {st["h_wins"]}/{st["n"]}, '
        f'{st["away"]} {st["a_wins"]}/{st["n"]}</li>'
        f'<li>Vorm voor deze tip (laatste {N_FORM} duels): {t["form_pct"]}%</li>'
        + (f'<li>Vorm {st["home"]}: {st.get("form_home","")}</li>' if st.get("form_home") else "")
        + (f'<li>Vorm {st["away"]}: {st.get("form_away","")}</li>' if st.get("form_away") else "")
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
        "uitgelicht": bool(t.get("feature")),
        "beste-tip": bool(t.get("feature")),
        "fixture-id": str(st["fixture_id"]),
        "home-team-id": str(st["hid"]), "away-team-id": str(st["aid"]),
        "thuisclub": st["home"], "uitclub": st["away"],
        "competitie": comp, "league-slug": league_slug,
        "datum-tijd-wedstrijd": dt.isoformat(),
        "tijd-wedstrijd": f"{dt:%H:%M}",
        # 12:00 lokaal (niet middernacht): Webflow bewaart datums in UTC; op middernacht
        # zou dat 22:00/23:00 de dag ervoor worden en een dag verschuiven. Noon blijft
        # in beide tijdzones op dezelfde kalenderdag.
        "tipdatum": dt.replace(hour=12, minute=0, second=0, microsecond=0).isoformat(),
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
