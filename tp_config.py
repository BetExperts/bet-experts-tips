# -*- coding: utf-8 -*-
"""Config voor de H2H-tips-agent (BTTS / Over-Under 2.5 / thuis-uitwinst)."""
import os

# --- Webflow ---
WEBFLOW_TOKEN    = os.environ.get("WEBFLOW_TOKEN", "").strip()
WF_API           = "https://api.webflow.com/v2"
TIPS_COLLECTION  = "6aab04ace124b6e1d758d57f"

# Markt = optieveld met slug 'markt-2' (Webflow hernoemde na herbouw)
MARKT_FIELD = "markt-2"
MARKT = {
    "BTTS":               "53feacdaa55da29b5656a9e4e185b4dd",
    "Over 2.5":           "c8c0d590f7a8ccff3f4460c48868ba86",
    "Under 2.5":          "71e68aa9856394ec15cdece58b2c40ff",
    "1X2":                "4bf48ee09d0eb9fd2990da882dbe1cba",
    "Dubbele kans":       "976e400ed47d49f0071532facf973636",
    "Thuisteam over 1.5": "bb9c6784493d13440cad0052b1339e5c",
    "Uitteam over 1.5":   "9b3abb0566b338e955a7d3545e88a479",
    "Betbuilder":         "a11fc22bcc36723f5a74b24c1a1c246a",
}
ZEKERHEID = {"Laag": "1493ba914f646ef3c0bef44284b91621",
             "Middel": "d7710104c72d56042c38ba550bd54c46",
             "Hoog": "dfdb2584aab9c4c6cb99ed2f031db7fa"}
STATUS = {"In afwachting": "d79fd2517846c28916899a024cf3d88e",
          "Gewonnen": "a9cafc90d97eb9056124af35f33e5446",
          "Verloren": "1c31fbbb2ca1e856b9aae028cc05f1f7",
          "Push": "d6a27c6436130f710bb921a711d2227e"}

# --- Bet-Experts API-proxy ---
API = "https://www.bet-experts.nl/api"

# Competities (slug -> weergavenaam). Alle competities; kwaliteit komt uit de
# H2H-eis (geen tip zonder H2H) i.p.v. uit een competitie-beperking.
LEAGUES = {
 "eredivisie":"Eredivisie","eerste-divisie":"Eerste Divisie","knvb-beker":"KNVB Beker",
 "johan-cruijff-schaal":"Johan Cruijff Schaal","premier-league":"Premier League","championship":"Championship",
 "league-one":"League One","league-two":"League Two","fa-cup":"FA Cup","efl-cup":"EFL Cup",
 "carabao-cup":"Carabao Cup","community-shield":"Community Shield","scottish-premiership":"Scottish Premiership",
 "mls":"MLS","la-liga":"La Liga","la-liga-2":"La Liga 2","segunda-division":"Segunda Division",
 "copa-del-rey":"Copa del Rey","serie-a":"Serie A","serie-b":"Serie B","coppa-italia":"Coppa Italia",
 "bundesliga":"Bundesliga","2-bundesliga":"2. Bundesliga","dfb-pokal":"DFB-Pokal","ligue-1":"Ligue 1",
 "ligue-2":"Ligue 2","coupe-de-france":"Coupe de France","primeira-liga":"Primeira Liga",
 "jupiler-pro-league":"Jupiler Pro League","belgian-cup":"Belgian Cup",
 "super-lig":"Super Lig","1-lig":"1. Lig","turkish-cup":"Turkiye Kupasi","eliteserien":"Eliteserien",
 "allsvenskan":"Allsvenskan","superliga":"Superliga","ekstraklasa":"Ekstraklasa","czech-liga":"Czech Liga",
 "nb-i":"NB I","ukrainian-premier-league":"Ukrainian Premier League","slovak-super-liga":"Slovak Super Liga",
 "bulgarian-first-league":"Bulgarian First League","super-league":"Super League",
 "swiss-super-league":"Swiss Super League","austrian-bundesliga":"Austrian Bundesliga",
 "greek-super-league":"Greek Super League","brasileirao":"Brasileirao",
 "saudi-pro-league":"Saudi Pro League","champions-league":"Champions League","europa-league":"Europa League",
 "conference-league":"Conference League","nations-league":"Nations League",
 "wc-qualification-europe":"WK Kwalificatie Europa",
}

# --- Odds-feed (jouw eigen NL-bookmakers via tubeemate; Referer verplicht) ---
TUBE_URL = "https://tubeemate.com/odds/odds.php"
TUBE_HEADERS = {"Referer": "https://www.bet-experts.nl/",
                "Origin": "https://www.bet-experts.nl",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
# bookmaker-key -> weergavenaam + affiliatelink (fallback als event geen affiliate_url geeft)
BOOKMAKERS = {
 "circus":{"name":"Circus","link":"https://note.circus.nl/redirect.aspx?pid=12467&bid=10131"},
 "tonybet":{"name":"Tonybet","link":"https://dro.netavix.com/redirect.aspx?pid=175115&bid=2034&lpid=1688"},
 "unibet":{"name":"Unibet","link":"https://b1.trickyrock.com/redirect.aspx?pid=86118747&bid=39312"},
 "onecasino":{"name":"OneCasino","link":"https://record.oneaffiliates.net/_8XG55gD0z_7PWnjzjqRrQ2Nd7ZgqdRLk/1"},
 "bet365":{"name":"Bet365","link":"https://www.bet365.nl/hub/nl-nl/open-account?affiliate=365_02599619"},
 "leovegas":{"name":"LeoVegas","link":"https://casino.leovegas.nl/redirect.aspx?pid=3768358&lpid=506&bid=13309"},
 "betmgm":{"name":"BetMGM","link":"https://casino.betmgm.nl/redirect.aspx?pid=3781431&lpid=3329&bid=20762"},
 "888sports":{"name":"888Sports","link":"https://media.888.nl/tracking.php?tracking_code&aid=119973&mid=9674&sid=460575&pid=3736"},
 "comeon":{"name":"ComeOn!","link":"https://media.comeon.nl/tracking.php?tracking_code&aid=119973&mid=9234&sid=458851&pid=3459"},
 "bingoal":{"name":"Bingoal","link":"https://tinyurl.com/bingoal-betexperts-sport"},
 "711sports":{"name":"711","link":"https://media1.711affiliates.nl/redirect.aspx?pid=2395&bid=1505"},
 "toto":{"name":"TOTO","link":"https://partner.toto.nl/C.ashx?btag=a_375b_445c_&affid=184&siteid=375&adid=445&c="},
 "jacks":{"name":"Jacks.nl","link":"https://media.friendsofjacks.eu/redirect.aspx?pid=2527&bid=2224"},
 "vbet":{"name":"Vbet","link":"https://www.vbet.nl/nl/affiliates/?btag=2343788_l356243"},
 "starcasino":{"name":"StarCasino","link":"https://media1.affiliates.starcasino.nl/redirect.aspx?pid=2170&bid=1478"},
}
FEEDS = list(BOOKMAKERS.keys())

# tubeemate-bookmaker-key -> item-id in de Bookmakers-collectie (voor het reference-veld)
BOOKMAKER_REF = {
 "circus":"64ff0fbd5a8f205b05d54670","tonybet":"682b116bb82996896cb52d5d",
 "unibet":"64ff0fbd5a8f205b05d54687","onecasino":"67974cf05b546fe28ef78cdc",
 "bet365":"651bd6728c40de720bd8072a","leovegas":"6526a08a94d8631739581743",
 "betmgm":"66bb685ec057aa8c4337ceea","888sports":"6909dcf78e3c22a32d06e2ad",
 "comeon":"66a24463b6de25483eec85e9","bingoal":"68dd287867de5cd59d44dc39",
 "711sports":"66a8a87062108480763b7309","toto":"669ab9f5aceb8b717cea24c3",
 "jacks":"64ff0fbd5a8f205b05d5465c","vbet":"67c9acaf7db0b29e5b03370d",
 "starcasino":"6a7afdaa4a7453c17d31cab5",
}

# --- Selectie-drempels ---
MIN_H2H = 4          # minimaal aantal onderlinge duels
MIN_STREAK = 2       # minimale lopende streak
MIN_ODD = 1.40       # tip alleen als de beste odd hier boven ligt (geen waarde bij lagere odds)

# H2H = basis (er moet H2H zijn). Sterke H2H kwalificeert; matige H2H alleen als
# de vorm het bevestigt. GEEN puur-op-vorm tips.
H2H_STRONG   = 80    # sterke H2H (8/10+) → kwalificeert
H2H_MODERATE = 60    # matige H2H (6/10+) → alleen mét sterke vorm
FORM_SUPPORT = 75    # vorm die een matige H2H mag bevestigen
FORM_FEATURE = 70    # sterke H2H + vorm hierboven → uitgelicht
N_FORM = 8           # recente wedstrijden per team voor de vorm-percentages

# Volume/beheer
CAP_PER_MARKET_PER_DAY = 6   # max tips per markt per dag (beste eerst)
REQUIRE_ODDS = True          # geen tip zonder odd (voorkomt obscure duels)
RETENTION_DAYS = 30          # tips ouder dan dit worden opgeruimd (hitrate-venster blijft)
def threshold(n_fixtures):
    """Drukke dag = strengere drempel."""
    if n_fixtures >= 200: return 80
    if n_fixtures >= 100: return 75
    return 70
