# -*- coding: utf-8 -*-
"""Tipselectie op basis van kans x waarde (15-10-2026). Minder tips, betere tips.

Een tip komt er alleen als:
  - onze kans (model gemengd met de marktconsensus) hoog genoeg is (P_MIN per markt), én
  - de beste NL-odd waarde biedt: kans x odd - 1 >= EDGE_MIN (en niet onrealistisch hoog: EDGE_MAX),
  - de odd tussen ODD_MIN en ODD_MAX ligt en minstens NBOOKS_MIN bookmakers de markt aanbieden,
  - beide ploegen genoeg wedstrijden in de stand hebben (of een prior uit vorig seizoen).
Per wedstrijd hooguit één tip (de beste), per dag hooguit CAP_MARKT per markt en CAP_DAG in totaal.
"""
from tp_model import probs, blend

P_MIN = {"btts_yes": 0.55, "over25": 0.55, "under25": 0.55, "home": 0.50, "away": 0.50}
EDGE_MIN, EDGE_MAX = 0.03, 0.15
MAX_VERSCHIL = 0.15   # model en markt mogen niet verder uiteenlopen (dan mist het model iets: blessures, rotatie)
ODD_MIN, ODD_MAX = 1.45, 3.00
NBOOKS_MIN = 3
MIN_GESPEELD = 3
CAP_MARKT, CAP_DAG = 3, 8

# BTTS-minimum per dag (17-10-2026, gebruiker): de BTTS-hub mag niet leeg blijven. Zijn er op een dag minder dan
# BTTS_MIN_DAG BTTS-tips, dan vullen we aan met de BTTS-kansen met de hoogste kans waarvan de beste NL-odd rond
# de eerlijke prijs ligt (edge >= BTTS_BASIS_EDGE_MIN). Zulke tips heten 'basis: kans': geen waarde-claim in de tekst.
BTTS_MIN_DAG = 2
BTTS_BASIS_P_MIN = 0.58
BTTS_BASIS_EDGE_MIN = -0.04

# alleen nationale competities met een eigen stand (beker/Europees/interlands: sterktes niet vergelijkbaar)
GEEN_MODEL = {"knvb-beker", "johan-cruijff-schaal", "fa-cup", "efl-cup", "carabao-cup", "community-shield",
              "copa-del-rey", "coppa-italia", "dfb-pokal", "coupe-de-france", "belgian-cup", "turkish-cup",
              "champions-league", "europa-league", "conference-league", "nations-league",
              "wc-qualification-europe"}

MARKTEN = (("btts_yes", "BTTS", "Beide teams scoren"),
           ("over25", "Over 2.5", "Meer dan 2.5 doelpunten"),
           ("under25", "Under 2.5", "Minder dan 2.5 doelpunten"),
           ("home", "1X2", None), ("away", "1X2", None))


def zekerheid(p):
    return "Hoog" if p >= 0.65 else "Middel" if p >= 0.55 else "Laag"


def beste_tip(home, away, lam, fair, nbooks, odds_for):
    """De beste tip voor één wedstrijd, of None. odds_for(home, away, key) -> {'best', ...}."""
    if nbooks < NBOOKS_MIN:
        return None
    mp = probs(*lam)
    opties = []
    for key, markt, tekst in MARKTEN:
        if key not in fair:
            continue
        if abs(mp[key] - fair[key]) > MAX_VERSCHIL:
            continue
        p = blend(mp[key], fair[key])
        if p < P_MIN[key]:
            continue
        od = odds_for(home, away, key)
        if not od or not (ODD_MIN <= od["best"] <= ODD_MAX):
            continue
        edge = p * od["best"] - 1
        if not (EDGE_MIN <= edge <= EDGE_MAX):
            continue
        tip = tekst or (f"{home} wint" if key == "home" else f"{away} wint")
        opties.append({"markt": markt, "tip": tip, "odds_key": key, "p": p, "p_model": mp[key],
                       "p_markt": fair[key], "edge": edge, "od": od, "score": edge * p,
                       "zekerheid": zekerheid(p), "lam": lam})
    return max(opties, key=lambda o: o["score"]) if opties else None


def btts_basis(home, away, lam, fair, nbooks, odds_for):
    """BTTS-aanvulling voor één wedstrijd: hoge kans, odd rond de eerlijke prijs. None als hij niet voldoet."""
    if nbooks < NBOOKS_MIN or "btts_yes" not in fair:
        return None
    mp, f = probs(*lam)["btts_yes"], fair["btts_yes"]
    if abs(mp - f) > MAX_VERSCHIL:
        return None
    p = blend(mp, f)
    if p < BTTS_BASIS_P_MIN:
        return None
    od = odds_for(home, away, "btts_yes")
    if not od or not (ODD_MIN <= od["best"] <= ODD_MAX):
        return None
    edge = p * od["best"] - 1
    if not (BTTS_BASIS_EDGE_MIN <= edge <= EDGE_MAX):
        return None
    return {"markt": "BTTS", "tip": "Beide teams scoren", "odds_key": "btts_yes", "p": p, "p_model": mp,
            "p_markt": f, "edge": edge, "od": od, "score": edge * p, "zekerheid": zekerheid(p), "lam": lam,
            "basis": "kans"}


def aanvullen_btts(basis, gekozen, bestaand_per_dag=None, bezet=()):
    """Vul per dag aan tot BTTS_MIN_DAG BTTS-tips (hoogste kans eerst; nooit een tweede tip bij dezelfde wedstrijd)."""
    bestaand_per_dag = bestaand_per_dag or {}
    telling = {}
    for d, markten in bestaand_per_dag.items():
        telling[d] = markten.count("BTTS")
    for c in gekozen:
        if c["markt"] == "BTTS":
            telling[c["dag"]] = telling.get(c["dag"], 0) + 1
    bezet = set(bezet) | {c["fid"] for c in gekozen}
    extra = []
    for c in sorted(basis, key=lambda c: (-c["t"]["p"], -c["t"]["edge"])):
        if c["fid"] in bezet or telling.get(c["dag"], 0) >= BTTS_MIN_DAG:
            continue
        telling[c["dag"]] = telling.get(c["dag"], 0) + 1
        bezet.add(c["fid"]); extra.append(c)
    return extra


def kies(kandidaten, bestaand_per_dag=None):
    """Caps per dag en markt toepassen (beste score eerst). bestaand_per_dag: {dag: [markt, ...]} van
    tips die al gepubliceerd zijn en blijven staan (die tellen mee in de caps)."""
    bestaand_per_dag = bestaand_per_dag or {}
    gekozen, per_dag = [], {}
    for c in sorted(kandidaten, key=lambda c: -c["t"]["score"]):
        d = c["dag"]
        lst = per_dag.setdefault(d, list(bestaand_per_dag.get(d, [])))
        if len(lst) >= CAP_DAG or lst.count(c["markt"]) >= CAP_MARKT:
            continue
        lst.append(c["markt"]); gekozen.append(c)
    return gekozen
