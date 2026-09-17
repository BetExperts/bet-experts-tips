# -*- coding: utf-8 -*-
"""HTML-templates (1200x630) voor de dagelijkse promo-afbeeldingen.
Zelfde huisstijl als de Instagram-verhalen: Poppins + Plus Jakarta Sans,
kleuren #0A1017 / #169A47 / #6CC08B, en het echte betexperts-logo."""
import os, base64

BASE = "https://www.bet-experts.nl"
_DIR = os.path.dirname(os.path.abspath(__file__))

def _logo_uri():
    p = os.path.join(_DIR, "assets", "betexperts_logo.png")
    with open(p, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()
LOGO = _logo_uri()

MARKETS = {
    "btts": {
        "label": "BTTS TIPS",
        "title": ["Beide teams", "scoren"],
        "sub": "Per wedstrijd het BTTS-percentage van de laatste vijf duels en de hoogste odd van alle vergunde bookmakers.",
        "url": f"{BASE}/wedtips/btts-tips-voorspellingen",
    },
    "over25": {
        "label": "OVER 2.5 TIPS",
        "title": ["Meer dan 2.5", "doelpunten"],
        "sub": "De duels met het hoogste verwachte doelpuntengemiddelde, met de hoogste odd per wedstrijd.",
        "url": f"{BASE}/wedtips/over-2-5-goals-tips-voorspellingen",
    },
    "1x2": {
        "label": "1X2 TIPS",
        "title": ["Winst, gelijk", "of verlies"],
        "sub": "Per wedstrijd de verwachte uitslag op basis van vorm, onderlinge duels en het belang van het duel.",
        "url": f"{BASE}/wedtips/1x2-tips-voorspellingen",
    },
}
GENERAL = {
    "label": "WEDTIPS PER MARKT",
    "title": "Wedtips vandaag",
    "sub": "Per markt de onderbouwing en de hoogste odd van alle vergunde bookmakers.",
    "url": f"{BASE}/wedtips",
    "cards": [("BTTS", "beide teams scoren"), ("Over 2.5", "drie of meer doelpunten"), ("1X2", "de einduitslag")],
}

_CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{width:1200px;height:630px;overflow:hidden;position:relative;
  font-family:'Plus Jakarta Sans',system-ui,sans-serif;background:#0A1017;color:#F2F6F4;
  -webkit-font-smoothing:antialiased}
.glow1{position:absolute;inset:0;background:radial-gradient(70% 55% at 14% -6%, rgba(22,154,71,.26), transparent 60%)}
.glow2{position:absolute;inset:0;background:radial-gradient(60% 45% at 92% 104%, rgba(22,154,71,.14), transparent 60%)}
.topbar{position:absolute;left:0;top:0;width:100%;height:8px;background:linear-gradient(90deg,#169A47,rgba(22,154,71,0) 55%)}
.wrap{position:relative;width:100%;height:100%;padding:52px 64px}
.head{display:flex;align-items:center;justify-content:space-between}
.logo{height:44px;width:auto;display:block}
.pill{border:1px solid rgba(255,255,255,.18);color:#A9B7C2;border-radius:999px;
  padding:9px 22px;font-family:'Poppins',sans-serif;font-size:15px;font-weight:600;letter-spacing:.16em}
.site{font-family:'Poppins',sans-serif;color:#6CC08B;font-weight:600;font-size:21px}
.eyebrow{display:flex;align-items:center;gap:14px;margin:66px 0 16px}
.eyebrow .bar{width:4px;height:20px;background:#2FD46E;flex:none}
.eyebrow .txt{color:#6CC08B;font-weight:700;font-size:19px;letter-spacing:.14em;text-transform:uppercase}
h1{font-family:'Poppins',sans-serif;font-size:76px;line-height:1;font-weight:700;
  letter-spacing:-.035em;color:#F2F6F4}
.sub{color:#A9B7C2;font-size:24px;line-height:1.5;margin-top:24px;max-width:560px}
/* markt-kaart rechts */
.card{position:absolute;right:64px;top:150px;width:372px;
  background:linear-gradient(160deg,#14202B,#0C1620);border:1px solid rgba(47,212,110,.30);
  border-radius:24px;padding:28px 30px;box-shadow:0 24px 50px rgba(0,0,0,.4)}
.card .c-lbl{color:#6C7A86;font-size:15px;font-weight:700;letter-spacing:.14em;text-transform:uppercase}
.card .c-match{font-family:'Poppins',sans-serif;color:#F2F6F4;font-size:32px;font-weight:600;line-height:1.15;margin-top:12px}
.card .c-reason{color:#A9B7C2;font-size:20px;margin-top:12px}
.card .c-div{height:1px;background:rgba(255,255,255,.10);margin:22px 0}
.card .c-odd-row{display:flex;align-items:baseline;justify-content:space-between}
.card .c-odd-lbl{color:#6C7A86;font-size:19px}
.card .c-odd{font-family:'Poppins',sans-serif;color:#2FD46E;font-size:48px;font-weight:700;letter-spacing:-.02em}
/* general onderkaarten */
.cards{position:absolute;left:64px;right:64px;bottom:54px;display:flex;gap:22px}
.mcard{flex:1;background:linear-gradient(160deg,#14202B,#0C1620);border:1px solid rgba(255,255,255,.10);
  border-left:5px solid #169A47;border-radius:20px;padding:22px 26px}
.mcard .m-t{font-family:'Poppins',sans-serif;color:#F2F6F4;font-size:30px;font-weight:700;letter-spacing:-.01em}
.mcard .m-s{color:#6C7A86;font-size:18px;margin-top:6px}
.foot{position:absolute;right:64px;bottom:42px;font-family:'Poppins',sans-serif;color:#6CC08B;font-weight:600;font-size:21px}
"""

def _shorten(match):
    parts = [p.strip() for p in match.replace(" v ", " - ").split(" - ")]
    def s(n):
        for junk in (" FC", "FC ", " United", " City", " Football Club"):
            n = n.replace(junk, "")
        return n.strip()
    parts = [s(p) for p in parts]
    return " – ".join(parts[:2]) if len(parts) >= 2 else match

def _logo():
    return f'<img class="logo" src="{LOGO}" alt="betexperts">'

def _frame(inner):
    return f'<style>{_CSS}</style><div class="glow1"></div><div class="glow2"></div><div class="topbar"></div><div class="wrap">{inner}</div>'

def market_html(kind, match, reason, odd):
    m = MARKETS[kind]; t = m["title"]
    return _frame(f"""
      <div class="head">{_logo()}<span class="pill">VANDAAG</span></div>
      <div class="eyebrow"><span class="bar"></span><span class="txt">{m['label']}</span></div>
      <h1>{t[0]}<br>{t[1]}</h1>
      <div class="sub">{m['sub']}</div>
      <div class="card">
        <div class="c-lbl">Beste tip vandaag</div>
        <div class="c-match">{_shorten(match)}</div>
        <div class="c-reason">{reason}</div>
        <div class="c-div"></div>
        <div class="c-odd-row"><span class="c-odd-lbl">Beste odd</span><span class="c-odd">{odd}</span></div>
      </div>
      <div class="foot">bet-experts.nl</div>""")

def general_html():
    g = GENERAL
    cards = "".join(f'<div class="mcard"><div class="m-t">{t}</div><div class="m-s">{s}</div></div>'
                    for t, s in g["cards"])
    return _frame(f"""
      <div class="head">{_logo()}<span class="site">bet-experts.nl</span></div>
      <div class="eyebrow"><span class="bar"></span><span class="txt">{g['label']}</span></div>
      <h1>{g['title']}</h1>
      <div class="sub">{g['sub']}</div>
      <div class="cards">{cards}</div>""")
