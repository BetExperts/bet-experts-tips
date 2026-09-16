# -*- coding: utf-8 -*-
"""API-proxy calls + fuzzy team-matching (voor odds-koppeling)."""
import time, unicodedata, re
import requests
from tp_config import API

S = requests.Session()

def _get(url, headers=None):
    for _ in range(5):
        try:
            r = S.get(url, headers=headers, timeout=40)
            if r.status_code == 429: time.sleep(3); continue
            if r.status_code >= 500: time.sleep(2); continue
            if r.status_code >= 400: return None
            return r.json()
        except Exception:
            time.sleep(2)
    return None

def fixtures(slug):
    d = _get(f"{API}/fixtures/{slug}")
    if not d: return []
    resp = d.get("response") or {}
    up = resp.get("upcoming") or []
    return up

def h2h(hid, aid):
    d = _get(f"{API}/h2h/{hid}-{aid}")
    if not d: return []
    hl = d.get("response", d) if isinstance(d, dict) else d
    return hl if isinstance(hl, list) else []

def team_form(tid):
    d = _get(f"{API}/team-form/{tid}")
    if not d: return []
    hl = d.get("response", d) if isinstance(d, dict) else d
    return hl if isinstance(hl, list) else []

# --- fuzzy team-naam matching (api-sports namen <-> tubeemate namen) ---
def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", s.lower())

def team_match(a, b):
    if not a or not b: return False
    na, nb = norm(a), norm(b)
    if na == nb: return True
    if len(na) > 3 and len(nb) > 3 and (na in nb or nb in na): return True
    wa, wb = norm(a.split(" ")[0]), norm(b.split(" ")[0])
    if len(wa) >= 3 and wa == wb: return True
    la, lb = norm(a.split(" ")[-1]), norm(b.split(" ")[-1])
    return len(la) >= 4 and la == lb
