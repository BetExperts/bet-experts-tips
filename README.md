# H2H-tips-agent (BTTS / Over-Under 2.5 / thuis-uitwinst)

Vult de Webflow **Tips**-collectie (`6aab04ace124b6e1d758d57f`) met dagelijkse tips,
op basis van H2H-trends uit de Bet-Experts API-proxy, met **live NL-odds** (beste odd
+ bookmaker-referentie) uit de eigen tubeemate-feed.

## Werking
1. `/api/fixtures/{league}` → wedstrijden in het venster (dedup op fixture-id).
2. Per wedstrijd `/api/h2h` + `/api/team-form` → BTTS%, Over/Under 2.5%, thuis-/uitwinst
   in H2H, streaks, thuis-oriëntatie en vorm.
3. Selectie per markt met een **dynamische drempel**: ≥70% (rustige dag), ≥75%
   (druk), ≥80% (zeer druk); min. 4 H2H + lopende streak.
4. Live odds uit `tubeemate.com/odds/odds.php` (per bookmaker, Referer-header verplicht):
   beste odd voor de pick over alle NL-books, met **bookmaker-referentie** naar de
   Bookmakers-CMS (logo + affiliatelink komen daaruit).
5. Tips-items aanmaken/updaten (idempotent via `state/tips.json`).

## Gebruik
```bash
python3 generate.py --dry                 # tonen wat geselecteerd wordt
python3 generate.py --date 2026-09-19      # specifieke dag
python3 generate.py --days 3               # vandaag + 2 dagen (weekend)
python3 generate.py                        # vandaag, items als CONCEPT
python3 generate.py --publish              # items direct LIVE
```
Env: `WEBFLOW_TOKEN`. Optioneel: `--league <slug>`, `--limit N`, `--no-odds`.

## Bestanden
`tp_config.py` (ids, competities, bookmakers, drempels) · `tp_api.py` (proxy + fuzzy
team-match) · `tp_stats.py` (H2H-trends) · `tp_odds.py` (tubeemate best-odd) ·
`tp_build.py` (selectie + velddata) · `tp_webflow.py` (create/update/publish) ·
`generate.py`.

## Let op
- Draait vanaf elk IP (API-proxy + tubeemate niet geo-geblokkeerd) → geschikt voor
  GitHub Actions of de Mac.
- Markt **Betbuilder** zit als optie in de CMS maar wordt (nog) niet automatisch gevuld.
- Teamlogo's: níet opgeslagen — af te leiden uit `home-team-id`/`away-team-id`
  via `https://media.api-sports.io/football/teams/{id}.png`.
