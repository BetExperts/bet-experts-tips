# -*- coding: utf-8 -*-
"""Webflow Data API v2 — create/update/publish van Tips-items + state."""
import os, json, requests
from tp_config import WEBFLOW_TOKEN, WF_API, TIPS_COLLECTION

BASE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(BASE, "state", "tips.json")

def _h():
    return {"Authorization": f"Bearer {WEBFLOW_TOKEN}", "Content-Type": "application/json",
            "accept": "application/json"}

def load_state():
    try: return json.load(open(STATE, encoding="utf-8"))
    except Exception: return {}

def save_state(s):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    json.dump(s, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

def list_items(limit=100):
    """Alle Tips-items (paginerend)."""
    out = []; offset = 0
    while True:
        url = f"{WF_API}/collections/{TIPS_COLLECTION}/items?limit={limit}&offset={offset}"
        r = requests.get(url, headers=_h(), timeout=30); r.raise_for_status()
        d = r.json(); items = d.get("items", [])
        out.extend(items)
        if len(items) < limit: break
        offset += limit
    return out

def _check(r):
    """raise_for_status, maar mét de Webflow-fouttekst (anders zie je alleen '400')."""
    if r.status_code >= 400:
        raise requests.exceptions.HTTPError(
            f"{r.status_code} {r.reason} voor {r.request.method} {r.url} — {r.text[:400]}",
            response=r)

def create_item(fd, live=False):
    ep = "items/live" if live else "items"
    url = f"{WF_API}/collections/{TIPS_COLLECTION}/{ep}"
    body = {"isArchived": False, "isDraft": not live, "fieldData": fd}
    r = requests.post(url, headers=_h(), json=body, timeout=30)
    _check(r)
    j = r.json()
    want = fd.get("slug"); got = (j.get("fieldData") or {}).get("slug")
    if want and got and got != want:
        # Webflow weigert een dubbele slug niet met een 400 maar plakt er een
        # suffix achter -> stille duplicaten. Detecteer dat, verwijder het net
        # aangemaakte duplicaat en meld het (generate slaat de tip over; het
        # bestaande item blijft en wordt op een volgende run bijgewerkt).
        delete_item(j.get("id"))
        raise requests.exceptions.HTTPError(
            f"duplicaat vermeden: slug '{want}' bestond al (Webflow gaf '{got}')")
    return j.get("id")

def delete_item(item_id):
    url = f"{WF_API}/collections/{TIPS_COLLECTION}/items/{item_id}"
    r = requests.delete(url, headers=_h(), timeout=30)
    # 404 = al weg; niet fataal
    if r.status_code not in (200, 204, 404):
        r.raise_for_status()
    return True

def update_item(item_id, fd, live=False):
    ep = f"items/{item_id}/live" if live else f"items/{item_id}"
    url = f"{WF_API}/collections/{TIPS_COLLECTION}/{ep}"
    body = {"fieldData": fd}
    if live: body.update({"isArchived": False, "isDraft": False})
    r = requests.patch(url, headers=_h(), json=body, timeout=30)
    _check(r)
    return item_id
