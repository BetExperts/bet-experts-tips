# -*- coding: utf-8 -*-
"""Sluit afgelopen tips af: haalt de eindstand uit de API (fixture-id) en zet
automatisch de status op Gewonnen/Verloren.

  python3 settle.py --dry     # tonen wat er afgesloten zou worden
  python3 settle.py           # eindstand + status bijwerken
"""
import sys, argparse
from datetime import datetime, timezone
import tp_api as api
import tp_webflow as WF
from tp_config import API, STATUS, MARKT, MARKT_FIELD, WEBFLOW_TOKEN

FIN = ("FT", "AET", "PEN")
INAFWACHTING = STATUS["In afwachting"]
MARKT_NAAM = {v: k for k, v in MARKT.items()}

def result_of(markt, gh, ga, fd):
    tot = gh + ga
    if markt == "BTTS":       return gh > 0 and ga > 0
    if markt == "Over 2.5":   return tot >= 3
    if markt == "Under 2.5":  return tot <= 2
    if markt == "Thuisteam over 1.5": return gh >= 2
    if markt == "Uitteam over 1.5":   return ga >= 2
    if markt == "1X2":
        tip = (fd.get("tip") or "")
        if tip.startswith(fd.get("thuisclub", "\0")): return gh > ga
        if tip.startswith(fd.get("uitclub", "\0")):   return ga > gh
        return None
    return None   # Dubbele kans / Betbuilder e.d. handmatig

def match_result(fid):
    d = api._get(f"{API}/match/{fid}")
    if not d: return None
    resp = d.get("response", d)
    fx = resp[0] if isinstance(resp, list) and resp else resp
    if not isinstance(fx, dict): return None
    st = (fx.get("fixture", {}).get("status", {}) or {}).get("short")
    g = fx.get("goals", {}) or {}
    if st not in FIN or g.get("home") is None or g.get("away") is None:
        return None
    return g["home"], g["away"]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    if not a.dry and not WEBFLOW_TOKEN:
        print("FOUT: WEBFLOW_TOKEN ontbreekt."); sys.exit(1)

    items = WF.list_items()
    now = datetime.now(timezone.utc)
    open_tips = [it for it in items if it["fieldData"].get("status") == INAFWACHTING]
    print(f"Open tips (In afwachting): {len(open_tips)}")
    done = 0
    for it in open_tips:
        fd = it["fieldData"]
        fid = fd.get("fixture-id")
        markt = MARKT_NAAM.get(fd.get(MARKT_FIELD))
        if not fid or not markt:
            continue
        res = match_result(fid)
        if not res:
            continue   # nog niet gespeeld / geen uitslag
        gh, ga = res
        won = result_of(markt, gh, ga, fd)
        if won is None:
            continue
        eindstand = f"{gh}-{ga}"
        status = STATUS["Gewonnen"] if won else STATUS["Verloren"]
        toel = f'{fd.get("tip","")} — {"gewonnen" if won else "verloren"} (eindstand {eindstand}).'
        upd = {"eindstand": eindstand, "status": status, "resultaat-toelichting": toel}
        label = f'{fd.get("wedstrijd")} | {markt} → {"WIN" if won else "VERLIES"} ({eindstand})'
        if a.dry:
            print(f"  ○ {label}")
        else:
            live = not it.get("isDraft", False)
            WF.update_item(it["id"], upd, live=live)
            print(f"  ✔ {label}")
        done += 1
    print(f"\nKLAAR — {done} tip(s) afgesloten.")

if __name__ == "__main__":
    main()
