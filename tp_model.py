# -*- coding: utf-8 -*-
"""Kansmodel voor de wedtips (15-10-2026): verwachte doelpunten -> kansen per markt.

Waarom: een backtest (138 wedstrijden, 3 weken) liet zien dat H2H-percentages bij BTTS en over/under
niets voorspelden (tips scoorden gelijk aan of onder de basisfrequentie). Wat wél werkt in de literatuur
en praktijk: aanvals- en verdedigingssterkte per team (doelpunten voor/tegen, thuis/uit), en de markt zelf.

1. Sterktes uit de stand van dit seizoen (doelpunten voor/tegen per wedstrijd), aangevuld met vorig seizoen
   als 'prior' (krimp naar die prior bij weinig gespeelde wedstrijden; promovendi starten zwakker).
2. Verwachte doelpunten:  lambda_thuis = gem. thuisgoals competitie x aanval_thuis x verdediging_uit
                           lambda_uit   = gem. uitgoals competitie  x aanval_uit   x verdediging_thuis
3. Poisson met Dixon-Coles-correctie (lage uitslagen 0-0/1-0/0-1/1-1 realistischer) -> kansen
   op 1/X/2, BTTS, over/under 2.5.
4. Mengen met de 'eerlijke' kans van de markt (gemiddelde van alle NL-bookmakers, marge eruit gehaald):
   de markt is de beste enkele voorspeller; het model bepaalt waar de markt afwijkt.
"""
import math
import tp_api as api
from tp_config import API

PRIOR_GAMES = 8        # pseudo-wedstrijden voor de prior (krimp bij weinig data)
PROMOTED_ATT = 0.85    # promovendus: aanval 15% zwakker dan gemiddeld
PROMOTED_DEF = 1.15    # ... en 15% meer tegengoals
RHO = -0.08            # Dixon-Coles-parameter
MAXG = 10
W_MODEL = 0.35         # gewicht model t.o.v. marktconsensus

_STAND = {}


def _standings(slug, season=None):
    key = (slug, season)
    if key not in _STAND:
        d = api._get(f"{API}/standings/{slug}" + (f"/{season}" if season else "")) or {}
        r = d.get("response") or []
        lg = (r[0] if isinstance(r, list) and r else r) or {}
        lg = lg.get("league", lg) if isinstance(lg, dict) else {}
        tabel = []
        for groep in lg.get("standings") or []:
            tabel += groep
        _STAND[key] = (lg.get("season"), tabel)
    return _STAND[key]


def _rates(row):
    a = row.get("all") or {}; h = row.get("home") or {}; w = row.get("away") or {}
    return {"p": a.get("played") or 0, "gf": (a.get("goals") or {}).get("for") or 0,
            "ga": (a.get("goals") or {}).get("against") or 0,
            "hp": h.get("played") or 0, "hgf": (h.get("goals") or {}).get("for") or 0,
            "hga": (h.get("goals") or {}).get("against") or 0,
            "ap": w.get("played") or 0, "agf": (w.get("goals") or {}).get("for") or 0,
            "aga": (w.get("goals") or {}).get("against") or 0}


class League:
    """Sterktes voor één competitie (huidig seizoen + vorig seizoen als prior)."""

    def __init__(self, slug):
        self.slug = slug
        season, tabel = _standings(slug)
        self.ok = bool(tabel)
        if not self.ok:
            return
        cur = {r["team"]["id"]: _rates(r) for r in tabel}
        prev = {}
        if season:
            _, pt = _standings(slug, int(season) - 1)
            prev = {r["team"]["id"]: _rates(r) for r in pt}
        # competitiegemiddelden: dit én vorig seizoen samen (één seizoensbegin is te grillig: na 8 speelrondes
        # scoorden uitploegen in de Eredivisie 2026/27 méér dan thuisploegen — toeval, geen structureel voordeel)
        def tot(dct, k): return sum(v[k] for v in dct.values())
        hp = tot(cur, "hp") + tot(prev, "hp"); ap = tot(cur, "ap") + tot(prev, "ap")
        hg = tot(cur, "hgf") + tot(prev, "hgf"); ag = tot(cur, "agf") + tot(prev, "agf")
        self.lh = hg / hp if hp else 1.5
        self.la = ag / ap if ap else 1.2
        self.lg = (self.lh + self.la) / 2                 # gemiddeld per team per wedstrijd
        self.cur = cur
        self.vorm = {r["team"]["id"]: (r.get("form") or "").replace("D", "G") for r in tabel}
        self.played = {t: v["p"] for t, v in cur.items()}
        self.prior = {t: bool(prev.get(t) and prev[t]["p"] >= 10) for t in cur}
        self.att, self.dfn = {}, {}
        for t, v in cur.items():
            pv = prev.get(t)
            if pv and pv["p"] >= 10:
                pa = (pv["gf"] / pv["p"]) / self.lg
                pd = (pv["ga"] / pv["p"]) / self.lg
            else:                                          # promovendus / nieuw in deze competitie
                pa, pd = PROMOTED_ATT, PROMOTED_DEF
            k = PRIOR_GAMES
            self.att[t] = ((v["gf"] / self.lg) + k * pa) / (v["p"] + k)
            self.dfn[t] = ((v["ga"] / self.lg) + k * pd) / (v["p"] + k)

    def lambdas(self, hid, aid):
        if not self.ok or hid not in self.att or aid not in self.att:
            return None
        return (self.lh * self.att[hid] * self.dfn[aid], self.la * self.att[aid] * self.dfn[hid])


def _pois(k, lam):
    return math.exp(-lam) * lam ** k / math.factorial(k)


def probs(lh, la, rho=RHO):
    """Kansen uit verwachte doelpunten (Poisson + Dixon-Coles)."""
    P = [[_pois(i, lh) * _pois(j, la) for j in range(MAXG + 1)] for i in range(MAXG + 1)]
    P[0][0] *= 1 - lh * la * rho
    P[0][1] *= 1 + lh * rho
    P[1][0] *= 1 + la * rho
    P[1][1] *= 1 - rho
    s = sum(map(sum, P))
    P = [[x / s for x in r] for r in P]
    home = sum(P[i][j] for i in range(MAXG + 1) for j in range(MAXG + 1) if i > j)
    away = sum(P[i][j] for i in range(MAXG + 1) for j in range(MAXG + 1) if j > i)
    draw = 1 - home - away
    btts = sum(P[i][j] for i in range(1, MAXG + 1) for j in range(1, MAXG + 1))
    under = sum(P[i][j] for i in range(MAXG + 1) for j in range(MAXG + 1) if i + j <= 2)
    return {"home": home, "draw": draw, "away": away, "btts_yes": btts, "btts_no": 1 - btts,
            "over25": 1 - under, "under25": under}


def blend(model_p, market_p, w=W_MODEL):
    if market_p is None:
        return None
    return w * model_p + (1 - w) * market_p
