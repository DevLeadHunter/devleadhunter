# Europe (Suisse / Belgique) — état du support et dette restante

> Audit complet réalisé le 2026-09-21 (au lancement de la vague 3 FR/CH/BE), suivi du premier
> lot de correctifs. Ce document liste ce qui est FAIT et ce qui RESTE, par gravité.
> Contexte : le logiciel a été construit 100 % France ; `prospects.country` (ISO alpha-2,
> défaut `FR`) est désormais le pivot de tout comportement dépendant du pays.

## ✅ Fait (2026-09-21)

- **`prospects.country`** : colonne + migration (`add_prospect_country`, backfill par préfixe
  `+41`/`+32`), schémas API, fiche prospect (affichage + édition), drawer d'ajout, table
  (drapeau), catalogue partagé `web/app/utils/prospectCountries.ts`.
- **Tunnel de recherche** : `ScrapingJobCreate.country` → job → `scrape_all(country=…)` →
  chaque scraper (`BaseScraper.scrape` a le kwarg). Sélecteur Pays dans le drawer de recherche,
  transmis aussi aux rounds de la boucle Facebook. Chaque prospect sauvé est estampillé du pays
  du job (chokepoint `on_prospect`).
- **Routage des sources** : hors France, Pages Jaunes et l'unlocker Bright Data (qui lit
  pagesjaunes.fr) sortent de la chaîne de failover et refusent un appel direct.
- **Géo réelle** : OSM/Nominatim `countrycodes` suit le pays (avant : `fr` en dur → une
  recherche « Sion » géocodait une commune française) ; requête Google Maps suffixée du pays
  (« plombier à Mons Belgique ») ; SERP Bright Data `gl=`/`cc=` suit le pays (avant : `gl=fr`
  enterrait les pages suisses).
- **Garde SMS** : `sms_service.send_to_prospect` refuse tout prospect non-FR. Raison : un 079
  suisse saisi sans indicatif se normalise en `+337…` **valide** → SMS payant vers un inconnu
  français ; et la mention STOP 36180 est un code court français.
- **Garde décisionnaire** : la cascade SIRENE/Pappers ne tourne plus pour un prospect non-FR
  (elle ne pouvait produire qu'un homonyme français « Registre officiel » + son SIREN écrit sur
  le prospect).
- **Copie templates** : trust électricien neutralisé (NF C 15-100 / garantie décennale /
  Consuel → formulations vraies partout), « Devis 0 € » → « Devis gratuit » (4 templates).

## 🔴 Reste — bloquant à la PREMIÈRE VENTE CH/BE (à faire avant de finaliser une vente hors France)

1. **`order_service._split_postal_address`** ne reconnaît que les CP à 5 chiffres → `zip_code`
   vide → la finalisation exige un code postal introuvable. CH/BE = 4 chiffres.
2. **`UiTaxIdLookupInput` / `taxIdUtils.ts`** : un IDE suisse (CHE-xxx.xxx.xxx) réduit à
   9 chiffres peut passer le Luhn et déclencher un lookup SIRENE qui écrase le formulaire avec
   une société française tierce (`FinalizeSaleDrawer.applyRegistryPrefill`). Un n° BCE belge
   (10 chiffres) est bloqué « incomplet ». → Par pays : champ libre hors FR, pas de lookup.
3. **`FinalizeSaleDrawer`** : `country_code: 'FR'` en dur, autocomplete BAN, « Montant (€) ».
   → sélecteur de pays (préréglé sur `prospect.country`) + saisie libre hors FR.
4. **Qonto** : `locale FR`, `EUR`, mention `S293B` (franchise TVA française) en dur. Pour la
   Belgique (B2B intracommunautaire) la mention correcte est l'autoliquidation (art. 196 dir.
   TVA) ; pour la Suisse (export hors UE) la TVA n'est pas applicable — et un client suisse
   attend du CHF. À trancher au premier acheteur : facturer en EUR (simple, légal) et adapter la
   mention, ou gérer le CHF.
5. **Domaine** : `suggestion_service` ne propose que du `.fr` ; proposer `.ch`/`.be` selon le
   pays (l'achat OVH lui-même semble générique, à vérifier au premier cas).

## 🟠 Reste — dégrade la qualité CH/BE (non bloquant pour la vague email)

- **Extraction ville/CP** : partout `\d{5}` (google/osm/pagesjaunes `extract_city`,
  `facebook_enrichment_scraper._parse_city_postal` + regex « France » littéral). CH/BE = 4
  chiffres → `place_city`/`place_postal_code` vides → garde-fou homonyme de fiche inactif.
- **Parseur téléphone FB** (`_FR_PHONE_RE`) : ignore `+41`/`+32` → prospect FB CH/BE sans tel.
- **`email_scraper`** : `gl=fr` en dur + stratégie « nom + téléphone » réservée aux numéros FR.
- **Scoring email** : blocklist d'annuaires FR uniquement — ajouter local.ch, search.ch,
  moneyhouse.ch, zefix.ch, goldenpages.be, kbopub… + « commune de » (équivalents mairie).
- **Autocomplete ville/adresse** (`geo.api.gouv.fr` / BAN) : aucune suggestion CH/BE (saisie
  libre possible — pénible, pas bloquant).
- **Mentions légales décisionnaire** : tester `/impressum` (CH) et « éditeur responsable » (BE)
  — c'est la stratégie qui pourrait remplacer SIRENE hors France.
- **Page Couverture** : `geo.api.gouv.fr` → prospects CH/BE jamais géocodés, absents de la
  carte (silencieux).
- **`useProspectionScript`** : « développeur web à Rennes » dans le script vidéo — argument de
  proximité à revoir pour un prospect hors France.
- **Copie plombier partagée** : « garantie décennale », « chèque » (quasi disparu en Belgique)
  — à neutraliser avant une vague plombiers CH/BE.
- **Jours fériés SMS** : liste française (le canal SMS est de toute façon fermé hors FR).

## 🟢 Non-problèmes vérifiés

- Lighthouse/PSI : sans locale, valide partout. Fuseau CH/BE = CET (fenêtres OK).
- Lead scoring : purement comportemental, aucun biais géo.
- `resilient_extract._PHONE_RE` (JSON-LD) : déjà international.

## Décisions associées (vague 3)

- Canada écarté (CASL). USA = email only (TCPA interdit le cold SMS) et chaîne 100 % FR à
  traduire d'abord. Suisse : rester en 1-to-1 ultra-personnalisé (la « publicité de masse »
  y est opt-in). Prix : mention « ≈470 CHF » dans le modèle email suisse.
