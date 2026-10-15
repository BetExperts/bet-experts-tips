# -*- coding: utf-8 -*-
"""Trackrecord van de wedtips (15-10-2026).

Elke gepubliceerde tip komt in state/results.json (blijft bewaard, ook als het CMS-item na een paar dagen
wordt opgeruimd). Inzet in de statistiek = 1 eenheid tegen de odd op het moment van publiceren
(odd_publicatie); de laatste odd voor de aftrap bewaren we apart (closing line value).
Telt eerlijk: elke gepubliceerde tip telt mee, gewonnen én verloren; alleen afgelaste wedstrijden niet.

public/stats.json (via raw.githubusercontent.com) voedt het trackrecord-blok op de tip-hubs.
"""
import json, os
from datetime import datetime, timedelta, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(BASE, "state", "results.json")
STATS = os.path.join(BASE, "public", "stats.json")
MARKTEN = ("BTTS", "Over 2.5", "Under 2.5", "1X2")


def load():
    try:
        return json.load(open(RESULTS, encoding="utf-8"))
    except Exception:
        return {}


def save(r):
    os.makedirs(os.path.dirname(RESULTS), exist_ok=True)
    json.dump(r, open(RESULTS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def record(res, slug, c, now=None):
    """Nieuwe tip vastleggen of (tot de aftrap) de laatste odd bijwerken."""
    now = (now or datetime.now(timezone.utc)).isoformat(timespec="seconds")
    t, od = c["t"], c["od"] or {}
    e = res.get(slug)
    if e is None:
        res[slug] = e = {
            "fid": c["fid"], "markt": c["markt"], "pick": t["odds_key"], "tip": t["tip"],
            "wedstrijd": c["wedstrijd"], "competitie": c["competitie"], "aftrap": c["aftrap"],
            "odd_publicatie": od.get("best"), "bookmaker": od.get("bookmaker"),
            "kans": round(t["p"], 4), "kans_markt": round(t["p_markt"], 4), "edge": round(t["edge"], 4),
            "tip_van_de_dag": bool(t.get("feature")), "gepubliceerd": now, "status": "open"}
    if e["status"] == "open":
        e["odd_laatst"] = od.get("best"); e["bijgewerkt"] = now
    return e


def uitkomst(pick, gh, ga):
    if pick == "btts_yes": return gh > 0 and ga > 0
    if pick == "over25": return gh + ga >= 3
    if pick == "under25": return gh + ga <= 2
    if pick == "home": return gh > ga
    if pick == "away": return ga > gh
    return None


def _agg(rows):
    n = len(rows); w = sum(1 for r in rows if r["status"] == "gewonnen")
    winst = sum((r["odd_publicatie"] - 1) if r["status"] == "gewonnen" else -1 for r in rows)
    return {"tips": n, "gewonnen": w, "verloren": n - w,
            "raak": round(100 * w / n) if n else None,
            "winst_eenheden": round(winst, 2), "rendement": round(100 * winst / n, 1) if n else None,
            "gem_odd": round(sum(r["odd_publicatie"] for r in rows) / n, 2) if n else None}


def write_stats(res, now=None):
    now = now or datetime.now(timezone.utc)
    klaar = [r for r in res.values() if r["status"] in ("gewonnen", "verloren") and r.get("odd_publicatie")]
    klaar.sort(key=lambda r: r["aftrap"], reverse=True)
    grens = (now - timedelta(days=30)).isoformat()
    recent = [r for r in klaar if r["aftrap"] >= grens]
    out = {
        "bijgewerkt": now.isoformat(timespec="seconds"),
        "sinds": min((r["gepubliceerd"] for r in res.values()), default=None),
        "totaal": _agg(klaar), "dertig_dagen": _agg(recent),
        "per_markt": {m: {"totaal": _agg([r for r in klaar if r["markt"] == m]),
                          "dertig_dagen": _agg([r for r in recent if r["markt"] == m])} for m in MARKTEN},
        "tip_van_de_dag": _agg([r for r in klaar if r.get("tip_van_de_dag")]),
        "open": sum(1 for r in res.values() if r["status"] == "open"),
        "laatste": [{"datum": r["aftrap"][:10], "wedstrijd": r["wedstrijd"], "markt": r["markt"], "tip": r["tip"],
                     "odd": r["odd_publicatie"], "uitslag": r.get("eindstand"), "status": r["status"]}
                    for r in klaar[:20]],
    }
    os.makedirs(os.path.dirname(STATS), exist_ok=True)
    json.dump(out, open(STATS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return out
