# -*- coding: utf-8 -*-
"""H2H-tips-agent: fixtures -> H2H-trends (+ vorm ter bevestiging) -> Tips-CMS met live NL-odds.

  python3 generate.py --dry                 # tonen wat er geselecteerd wordt
  python3 generate.py --date 2026-09-19      # specifieke dag
  python3 generate.py --days 4               # vandaag + 3 dagen
  python3 generate.py                        # vandaag, items als CONCEPT
  python3 generate.py --publish              # items direct LIVE
Zonder --date: vandaag (Europe/Amsterdam)."""
import re, sys, argparse
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from collections import defaultdict

import tp_api as api
import tp_stats as stats
import tp_form as form_mod
import tp_build as build
import tp_odds as odds
import tp_webflow as WF
from tp_config import LEAGUES, WEBFLOW_TOKEN, MIN_ODD, REQUIRE_ODDS, CAP_PER_MARKET_PER_DAY

NL = ZoneInfo("Europe/Amsterdam")
_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})$")

def target_days(date_arg, days):
    base = datetime.strptime(date_arg, "%Y-%m-%d").date() if date_arg else datetime.now(NL).date()
    return {(base + timedelta(days=i)).isoformat() for i in range(days)}

def _score(t):
    return (1000 if t.get("feature") else 0) + t["h2h_pct"] * 3 + t["form_pct"] + min(t["h2h_streak"], 6) * 5

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date"); ap.add_argument("--days", type=int, default=1)
    ap.add_argument("--dry", action="store_true"); ap.add_argument("--publish", action="store_true")
    ap.add_argument("--no-odds", action="store_true"); ap.add_argument("--league")
    a = ap.parse_args()

    days = target_days(a.date, a.days)
    live = a.publish
    use_odds = not a.dry and not a.no_odds
    leagues = {a.league: LEAGUES.get(a.league, a.league)} if a.league else LEAGUES
    print(f"== Tips voor {sorted(days)} | modus: {'LIVE' if live else ('DRY' if a.dry else 'CONCEPT')} ==")

    # 1) wedstrijden verzamelen (dedup op fixture-id)
    seen = set(); fixtures = []
    for slug in leagues:
        for fx in api.fixtures(slug):
            if fx.get("fixture", {}).get("date", "")[:10] in days:
                fid = fx["fixture"]["id"]
                if fid in seen: continue
                seen.add(fid); fixtures.append((slug, fx))
    print(f"Wedstrijden in venster: {len(fixtures)}")
    if not fixtures:
        print("Geen wedstrijden. Klaar."); return

    if use_odds:
        try:
            tot = odds.load_all(); print(f"Odds geladen: {tot} events over {len(odds._CACHE)} bookmakers")
        except Exception as e:
            print(f"  · odds laden mislukt ({e})")

    # 2) kandidaten verzamelen (H2H leidend, vorm bevestigt, odds verplicht)
    cands = []
    for slug, fx in fixtures:
        st = stats.analyse(fx, want_form=False)
        if not build.has_prospect(st):
            continue
        fm = form_mod.signal(st["hid"], st["aid"])
        st["form_home"] = fm["form_home"]; st["form_away"] = fm["form_away"]
        for t in build.select(st, fm):
            od = None
            if use_odds:
                try: od = odds.odds_for(st["home"], st["away"], t["odds_key"])
                except Exception: od = None
                if REQUIRE_ODDS and od is None:      # geen odds -> geen tip
                    continue
                if od and od["best"] < MIN_ODD:      # te lage odd -> geen waarde
                    continue
            fd, tslug, name = build.build_fielddata(st, t, slug, odds=od)
            cands.append({"slug": tslug, "fd": fd, "name": name, "markt": t["markt"],
                          "day": st["date"][:10], "score": _score(t), "od": od, "t": t})

    # 3) cap per (dag, markt): beste eerst
    groups = defaultdict(list)
    for c in cands:
        groups[(c["day"], c["markt"])].append(c)
    selected = []
    for lst in groups.values():
        lst.sort(key=lambda c: -c["score"])
        selected += lst[:CAP_PER_MARKET_PER_DAY]
    sel_slugs = {c["slug"] for c in selected}
    print(f"Kandidaten: {len(cands)}  →  geselecteerd (na cap {CAP_PER_MARKET_PER_DAY}/markt/dag): {len(selected)}")

    state = WF.load_state()
    made = updated = 0
    for c in sorted(selected, key=lambda c: (c["day"], c["markt"], -c["score"])):
        t = c["t"]; star = " ★" if t.get("feature") else ""
        oddtxt = f' @ {c["od"]["best"]:.2f} ({c["od"]["bookmaker"]})' if c["od"] else ""
        line = f'{c["markt"]:9s} H2H{t["h2h_pct"]}% vorm{t["form_pct"]}%{star} | {c["name"]}{oddtxt}'
        if a.dry:
            print(f"  ○ {line}"); continue
        if c["slug"] in state:
            WF.update_item(state[c["slug"]], c["fd"], live=live); updated += 1
        else:
            state[c["slug"]] = WF.create_item(c["fd"], live=live); WF.save_state(state); made += 1
        print(f"  ✔ {line}")

    # 4) opruimen: tips in dit venster die NIET meer geselecteerd zijn (odd weg, niet meer sterk genoeg)
    removed = 0
    if not a.dry:
        for tslug, iid in list(state.items()):
            m = _DATE_RE.search(tslug)
            if m and m.group(1) in days and tslug not in sel_slugs:
                WF.delete_item(iid); state.pop(tslug, None); removed += 1
                print(f"  🗑  vervalt: {tslug}")
        WF.save_state(state)

    print(f"\nKLAAR — nieuw: {made}, bijgewerkt: {updated}, verwijderd: {removed}")

if __name__ == "__main__":
    if "--dry" not in sys.argv and not WEBFLOW_TOKEN:
        print("FOUT: WEBFLOW_TOKEN ontbreekt (of gebruik --dry)."); sys.exit(1)
    main()
