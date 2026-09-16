# -*- coding: utf-8 -*-
"""Selectie van tips uit de H2H-stats + opbouw van de Webflow-velddata."""
import re, unicodedata
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from tp_config import (MARKT, MARKT_FIELD, ZEKERHEID, STATUS, LEAGUES, MIN_H2H, MIN_STREAK,
                       BOOKMAKER_REF, H2H_STRONG, FORM_CONFIRM, FORM_STRONG, FORM_FEATURE, N_FORM)

NL = ZoneInfo("Europe/Amsterdam")

def slugify(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s.lower())).strip("-")

def _local(iso):
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(NL)

def _decide(h2h_n, h2h_pct, h2h_streak, form_pct, thr, min_n=MIN_H2H):
    """Beslis of een markt kwalificeert op basis van H2H + vorm.
    Return (qualify, feature, zekerheid, basis) of (False,...)."""
    strong = h2h_n >= min_n and h2h_pct >= H2H_STRONG and h2h_streak >= MIN_STREAK
    combined = h2h_n >= min_n and h2h_pct >= thr and form_pct >= FORM_CONFIRM
    form_only = h2h_n < min_n and form_pct >= FORM_STRONG
    qualify = strong or combined or form_only
    if not qualify:
        return (False, False, None, None)
    feature = strong and form_pct >= FORM_FEATURE
    if feature:                 zek = "Hoog"
    elif strong or combined:    zek = "Middel"
    else:                       zek = "Laag"
    basis = "h2h" if strong else ("combi" if combined else "vorm")
    return (True, feature, zek, basis)

def _candidates(st, form, thr):
    n, sn = st["n"], st["same_n"]
    specs = [
        ("BTTS", "Beide teams scoren", "btts_yes", n, st["btts_pct"], st["btts_streak"],
         form["btts"], f'{st["btts"]} van {n} H2H BTTS', MIN_H2H),
        ("Over 2.5", "Meer dan 2.5 doelpunten", "over25", n, st["o25_pct"], st["o25_streak"],
         form["over25"], f'{st["o25"]} van {n} H2H over 2.5', MIN_H2H),
        ("Under 2.5", "Minder dan 2.5 doelpunten", "under25", n, st["under_pct"], st["under_streak"],
         form["under25"], f'{st["under"]} van {n} H2H onder 2.5', MIN_H2H),
        ("1X2", f'{st["home"]} wint', "home", sn, st["home_w_pct"], st["home_w_streak"],
         form["home_win"], f'{st["home"]} won {st["home_w"]} van {sn} thuisduels', 3),
        ("1X2", f'{st["away"]} wint', "away", sn, st["away_w_pct"], st["away_w_streak"],
         form["away_win"], f'{st["away"]} won {st["away_w"]} van {sn} uitduels', 3),
    ]
    out = []
    for markt, tip, key, h2h_n, h2h_pct, h2h_streak, form_pct, h2h_desc, min_n in specs:
        qual, feature, zek, basis = _decide(h2h_n, h2h_pct, h2h_streak, form_pct, thr, min_n)
        if not qual:
            continue
        if basis == "vorm":
            ond = f'Vorm: {form_pct}% in de laatste {N_FORM} duels'
        else:
            ond = f'{h2h_desc} · vorm {form_pct}%'
        out.append({"markt": markt, "tip": tip, "onderbouwing": ond, "odds_key": key,
                    "h2h_pct": h2h_pct, "h2h_streak": h2h_streak, "form_pct": form_pct,
                    "zekerheid": zek, "feature": feature, "basis": basis})
    return out

def select(st, form, thr):
    """Return lijst van tip-dicts (H2H + vorm gecombineerd)."""
    return _candidates(st, form, thr)

_BASIS_TXT = {"h2h": "sterke onderlinge reeks", "combi": "onderlinge reeks + vorm",
              "vorm": "recente vorm"}

def _berekening(st, t):
    basis = _BASIS_TXT.get(t.get("basis"), "statistiek")
    lines = [f'<p><strong>{t["tip"]}</strong> — {t["onderbouwing"]} (op basis van {basis}).</p>']
    lines.append("<ul>"
        f'<li>H2H BTTS: {st["btts"]}/{st["n"]} ({st["btts_pct"]}%), streak {st["btts_streak"]}</li>'
        f'<li>H2H Over 2.5: {st["o25"]}/{st["n"]} ({st["o25_pct"]}%), streak {st["o25_streak"]}</li>'
        f'<li>Thuis-oriëntatie ({st["home"]} thuis): BTTS {st["same_btts"]}/{st["same_n"]}, '
        f'thuiswinst {st["home_w"]}/{st["same_n"]}</li>'
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
