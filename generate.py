# -*- coding: utf-8 -*-
"""Wedtips-agent v2 (15-10-2026): kansmodel + marktconsensus -> alleen tips met kans én waarde.

  python3 generate.py --dry                 # tonen wat er geselecteerd wordt (geen CMS, geen trackrecord)
  python3 generate.py --date 2026-10-17      # specifieke dag
  python3 generate.py --days 4               # vandaag + 3 dagen
  python3 generate.py --publish              # items direct LIVE
Werkwijze: tp_model (verwachte doelpunten uit de stand, Poisson/Dixon-Coles) + tp_odds.market_fair
(eerlijke kans van alle NL-bookmakers) -> tp_select (drempels, 1 tip per wedstrijd, caps per dag).
Gepubliceerde tips blijven staan tot de aftrap (alleen de odd wordt ververst) en komen in het
trackrecord (tp_results, state/results.json -> public/stats.json). De vorige H2H-versie: generate_h2h_oud.py.
"""
import re, sys, argparse
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import tp_api as api
import tp_stats as stats
import tp_build as build
import tp_odds as odds
import tp_webflow as WF
import tp_results as R
import tp_select as SEL
from tp_model import League
from tp_config import LEAGUES, WEBFLOW_TOKEN

NL = ZoneInfo("Europe/Amsterdam")
_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})$")


def target_days(date_arg, days):
    base = datetime.strptime(date_arg, "%Y-%m-%d").date() if date_arg else datetime.now(NL).date()
    return {(base + timedelta(days=i)).isoformat() for i in range(days)}


def _pct(x):
    return f"{round(100 * x)}%"


def berekening(st, t, lg, hid, aid):
    lh, la = t["lam"]; od = t["od"]
    mp = __import__("tp_model").probs(lh, la)
    def team(tid, naam):
        v = lg.cur.get(tid) or {}
        if not v.get("p"):
            return f"<li>{naam}: nog geen competitiewedstrijden dit seizoen</li>"
        return (f'<li>{naam} dit seizoen: {v["gf"] / v["p"]:.1f} doelpunten voor en {v["ga"] / v["p"]:.1f} tegen '
                f'per wedstrijd ({v["p"]} duels; thuis {v["hgf"]}-{v["hga"]}, uit {v["agf"]}-{v["aga"]})</li>')
    return (f'<p><strong>{t["tip"]}</strong>: onze kans is <strong>{_pct(t["p"])}</strong>. '
            f'De bookmakers rekenen gemiddeld met {_pct(t["p_markt"])} (marge eruit gehaald). '
            f'Bij een odd van {od["best"]:.2f} ({od["bookmaker"]}) hoort een kans van {_pct(1 / od["best"])}, '
            f'dus deze odd biedt waarde: verwacht rendement +{round(100 * t["edge"])}%.</p>'
            "<ul>"
            f'<li>Verwachte doelpunten: {st["home"]} {lh:.2f}, {st["away"]} {la:.2f}</li>'
            f'<li>Kansen volgens ons model: {st["home"]} wint {_pct(mp["home"])}, gelijk {_pct(mp["draw"])}, '
            f'{st["away"]} wint {_pct(mp["away"])}, beide teams scoren {_pct(mp["btts_yes"])}, '
            f'meer dan 2.5 doelpunten {_pct(mp["over25"])}</li>'
            + team(hid, st["home"]) + team(aid, st["away"]) +
            "</ul>"
            "<p>Onze kans is een mix van ons eigen model (aanval en verdediging van beide ploegen, thuisvoordeel "
            "van de competitie) en de gemiddelde kans volgens alle in Nederland vergunde bookmakers.</p>")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date"); ap.add_argument("--days", type=int, default=1)
    ap.add_argument("--dry", action="store_true"); ap.add_argument("--publish", action="store_true")
    ap.add_argument("--league")
    a = ap.parse_args()

    days = target_days(a.date, a.days)
    live = a.publish
    now = datetime.now(timezone.utc)
    leagues = {a.league: LEAGUES.get(a.league, a.league)} if a.league else LEAGUES
    leagues = {k: v for k, v in leagues.items() if k not in SEL.GEEN_MODEL}
    print(f"== Wedtips v2 voor {sorted(days)} | modus: {'LIVE' if live else ('DRY' if a.dry else 'CONCEPT')} ==")

    fixtures, seen = [], set()
    for slug in leagues:
        for fx in api.fixtures(slug):
            d = fx.get("fixture", {}).get("date", "")
            if d[:10] in days and d > now.isoformat():
                fid = fx["fixture"]["id"]
                if fid not in seen:
                    seen.add(fid); fixtures.append((slug, fx))
    print(f"Wedstrijden in venster: {len(fixtures)}")
    if not fixtures:
        print("Geen wedstrijden. Klaar."); return
    tot = odds.load_all(); print(f"Odds geladen: {tot} events over {len(odds._CACHE)} bookmakers")

    state, res = WF.load_state(), R.load()
    # gepubliceerde v2-tips (in het trackrecord) blijven staan tot de aftrap
    behouden = {s: e for s, e in res.items() if e["status"] == "open" and e["aftrap"] > now.isoformat()
                and s in state and e["aftrap"][:10] in days}
    fid_behouden = {str(e["fid"]) for e in behouden.values()}
    bestaand_per_dag = {}
    for e in behouden.values():
        bestaand_per_dag.setdefault(e["aftrap"][:10], []).append(e["markt"])

    lgs, kand, zonder = {}, [], 0
    for slug, fx in fixtures:
        lg = lgs.get(slug) or lgs.setdefault(slug, League(slug))
        th, ta = fx["teams"]["home"], fx["teams"]["away"]
        lam = lg.lambdas(th["id"], ta["id"]) if lg.ok else None
        if not lam:
            zonder += 1; continue
        for tid in (th["id"], ta["id"]):
            if lg.played.get(tid, 0) < SEL.MIN_GESPEELD and not lg.prior.get(tid):
                lam = None
        if not lam:
            zonder += 1; continue
        fair, nb = odds.market_fair(th["name"], ta["name"])
        t = SEL.beste_tip(th["name"], ta["name"], lam, fair, nb, odds.odds_for)
        if not t:
            continue
        dag = fx["fixture"]["date"][:10]
        kand.append({"slug": slug, "fx": fx, "fid": str(fx["fixture"]["id"]), "dag": dag, "markt": t["markt"],
                     "t": t, "lg": lg})
    print(f"Zonder bruikbare data (geen stand/te weinig duels): {zonder} · kandidaten met waarde: {len(kand)}")

    # odds van behouden tips verversen (zelfde wedstrijd: geen tweede tip)
    kand = [c for c in kand if c["fid"] not in fid_behouden]
    gekozen = SEL.kies(kand, bestaand_per_dag)
    # tip van de dag: per dag de hoogste kans + waarde (kans >= 55%), tenzij er al een behouden tip van de dag is
    tvd_dagen = {e["aftrap"][:10] for e in behouden.values() if e.get("tip_van_de_dag")}
    for dag in sorted({c["dag"] for c in gekozen}):
        if dag in tvd_dagen:
            continue
        top = max((c for c in gekozen if c["dag"] == dag and c["t"]["p"] >= 0.55),
                  key=lambda c: c["t"]["p"] + c["t"]["edge"], default=None)
        if top:
            top["t"]["feature"] = True
    print(f"Geselecteerd: {len(gekozen)} nieuw + {len(behouden)} al gepubliceerd")

    made = updated = removed = failed = 0
    for c in sorted(gekozen, key=lambda c: (c["dag"], -c["t"]["score"])):
        t, fx, lg = c["t"], c["fx"], c["lg"]
        star = " ★ tip van de dag" if t.get("feature") else ""
        line = (f'{t["markt"]:9s} kans {_pct(t["p"])} (model {_pct(t["p_model"])}, markt {_pct(t["p_markt"])}) '
                f'@ {t["od"]["best"]:.2f} {t["od"]["bookmaker"]} edge +{round(100 * t["edge"])}%{star} | '
                f'{fx["teams"]["home"]["name"]} - {fx["teams"]["away"]["name"]}: {t["tip"]}')
        if a.dry:
            print(f"  ○ {line}"); continue
        try:
            st = stats.analyse(fx, want_form=False)
            hid, aid = fx["teams"]["home"]["id"], fx["teams"]["away"]["id"]
            st["form_home"], st["form_away"] = lg.vorm.get(hid, ""), lg.vorm.get(aid, "")
            lh, la = t["lam"]
            bt = {**t, "onderbouwing": f'Onze kans {_pct(t["p"])} · bookmakers {_pct(t["p_markt"])} · '
                                        f'verwacht {lh:.1f}-{la:.1f} doelpunten',
                  "berekening": berekening(st, t, lg, hid, aid)}
            fd, tslug, name = build.build_fielddata(st, bt, c["slug"], odds=t["od"])
            if tslug in state:
                WF.update_item(state[tslug], fd, live=live); updated += 1
            else:
                state[tslug] = WF.create_item(fd, live=live); WF.save_state(state); made += 1
            if live:
                R.record(res, tslug, {"fid": c["fid"], "markt": t["markt"], "t": bt, "od": t["od"],
                                      "wedstrijd": f'{st["home"]} - {st["away"]}',
                                      "competitie": LEAGUES.get(c["slug"], c["slug"]),
                                      "aftrap": fx["fixture"]["date"]})
            print(f"  ✔ {line}")
        except Exception as e:
            failed += 1
            print(f"  ⚠️  OVERGESLAGEN | {line}\n       {e}")

    if not a.dry:
        # behouden tips: alleen de odd verversen (CMS + trackrecord)
        for s, e in behouden.items():
            od = odds.odds_for(*e["wedstrijd"].split(" - ", 1), e["pick"]) if " - " in e["wedstrijd"] else None
            if od:
                try:
                    WF.update_item(state[s], {"beste-odd": f'{od["best"]:.2f}', "beste-odd-bookmaker": od["bookmaker"],
                                              "odds-bijgewerkt": now.isoformat()}, live=live)
                    e["odd_laatst"] = od["best"]; e["bijgewerkt"] = now.isoformat(timespec="seconds")
                except Exception as ex:
                    print(f"  · odd verversen mislukt ({s}): {ex}")
        # oude (H2H-)tips in dit venster die niet in het trackrecord staan en niet gekozen zijn: weg
        sel_slugs = set(state)  # na create bevat state ook de nieuwe
        nieuw = {build.slugify(f'{c["t"]["markt"]}-{c["fx"]["teams"]["home"]["name"]}-{c["fx"]["teams"]["away"]["name"]}-'
                               f'{build._local(c["fx"]["fixture"]["date"]):%Y-%m-%d}') for c in gekozen}
        for tslug, iid in list(state.items()):
            m = _DATE_RE.search(tslug)
            if m and m.group(1) in days and tslug not in res and tslug not in nieuw:
                WF.delete_item(iid); state.pop(tslug, None); removed += 1
                print(f"  🗑  vervalt (oude methode / geen waarde meer): {tslug}")
        WF.save_state(state)
        R.save(res); R.write_stats(res)

    print(f"\nKLAAR — nieuw: {made}, bijgewerkt: {updated}, verwijderd: {removed}, overgeslagen: {failed}")


if __name__ == "__main__":
    if "--dry" not in sys.argv and not WEBFLOW_TOKEN:
        print("FOUT: WEBFLOW_TOKEN ontbreekt (of gebruik --dry)."); sys.exit(1)
    main()
