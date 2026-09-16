# -*- coding: utf-8 -*-
"""H2H-tips-agent: fixtures -> H2H-trends -> Tips-CMS (met live NL-odds).

  python3 generate.py --dry                 # alleen tonen wat er geselecteerd wordt
  python3 generate.py --date 2026-09-19      # specifieke dag
  python3 generate.py --days 3               # vandaag + 2 dagen (weekend)
  python3 generate.py                        # vandaag, items als concept aanmaken
  python3 generate.py --publish              # items direct live zetten
Zonder --date: vandaag (Europe/Amsterdam)."""
import sys, argparse
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import tp_api as api
import tp_stats as stats
import tp_build as build
import tp_odds as odds
import tp_webflow as WF
from tp_config import LEAGUES, threshold, WEBFLOW_TOKEN

NL = ZoneInfo("Europe/Amsterdam")

def target_days(date_arg, days):
    if date_arg:
        base = datetime.strptime(date_arg, "%Y-%m-%d").date()
    else:
        base = datetime.now(NL).date()
    return {(base + timedelta(days=i)).isoformat() for i in range(days)}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date"); ap.add_argument("--days", type=int, default=1)
    ap.add_argument("--dry", action="store_true"); ap.add_argument("--publish", action="store_true")
    ap.add_argument("--no-odds", action="store_true"); ap.add_argument("--limit", type=int)
    ap.add_argument("--league")
    a = ap.parse_args()

    days = target_days(a.date, a.days)
    live = a.publish
    leagues = {a.league: LEAGUES.get(a.league, a.league)} if a.league else LEAGUES
    print(f"== Tips genereren voor {sorted(days)} | modus: {'LIVE' if live else ('DRY' if a.dry else 'CONCEPT')} ==")

    # 1) wedstrijden verzamelen (dedup op fixture-id; sommige comps hebben 2 slugs)
    seen_fix = set(); fixtures = []
    for slug in leagues:
        for fx in api.fixtures(slug):
            if fx.get("fixture", {}).get("date", "")[:10] in days:
                fid = fx["fixture"]["id"]
                if fid in seen_fix: continue
                seen_fix.add(fid); fixtures.append((slug, fx))
    print(f"Wedstrijden in venster: {len(fixtures)}")
    if not fixtures:
        print("Geen wedstrijden. Klaar."); return
    thr = threshold(len(fixtures))
    print(f"Selectiedrempel: {thr}%")

    # 2) odds-feeds laden (1x)
    if not a.dry and not a.no_odds:
        try:
            tot = odds.load_all()
            print(f"Odds geladen: {tot} events over {len(odds._CACHE)} bookmakers")
        except Exception as e:
            print(f"  · odds laden mislukt ({e}); ga door zonder odds.")

    state = WF.load_state()
    made = updated = 0
    for slug, fx in fixtures:
        st = stats.analyse(fx, want_form=False)
        tips = build.select(st, thr)
        if not tips:
            continue
        # vorm ophalen (alleen voor kansrijke wedstrijden)
        st["form_home"] = stats._form_string(api.team_form(st["hid"]), st["hid"])
        st["form_away"] = stats._form_string(api.team_form(st["aid"]), st["aid"])
        for t in tips:
            od = None
            if not a.dry and not a.no_odds:
                try: od = odds.odds_for(st["home"], st["away"], t["markt"])
                except Exception: od = None
            fd, tslug, name = build.build_fielddata(st, t, slug, odds=od)
            oddtxt = f' @ {od["best"]:.2f} ({od["bookmaker"]})' if od else ""
            if a.dry:
                print(f"  ○ {t['markt']:11s} {t['pct']}%/{t['streak']} | {name}{oddtxt}")
            else:
                if tslug in state:
                    WF.update_item(state[tslug], fd, live=live); updated += 1
                    print(f"  ✎ {t['markt']:11s} {name}{oddtxt}")
                else:
                    iid = WF.create_item(fd, live=live); state[tslug] = iid; WF.save_state(state)
                    made += 1
                    print(f"  ✔ {t['markt']:11s} {name}{oddtxt}")
            if a.limit and (made + updated) >= a.limit: break
        if a.limit and (made + updated) >= a.limit: break

    print(f"\nKLAAR — nieuw: {made}, bijgewerkt: {updated}")

if __name__ == "__main__":
    if "--dry" not in sys.argv and not WEBFLOW_TOKEN:
        print("FOUT: WEBFLOW_TOKEN ontbreekt (of gebruik --dry)."); sys.exit(1)
    main()
