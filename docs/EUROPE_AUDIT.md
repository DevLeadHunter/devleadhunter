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

## ✅ Fait (2026-10-03, ticket Support Québec) — la vente hors France ne casse plus

Tout passe par le socle `api/services/country_profiles.py` (`CountryProfile` par pays) et la
route `GET /api/v1/countries` que le drawer consomme (libellé et obligation de l'identifiant
fiscal, motif et exemple de code postal, monnaie) — aucun fait pays dupliqué côté front.

1. **`order_service._split_postal_address(address, city, country)`** lit le motif du profil
   (FR 5 chiffres, CH/BE/LU 4, CA `A1A 1A1`, ville avant le code et province « (Québec) »
   retirée) ; `billing_details_for_order` prérègle le pays de facturation sur
   `prospect.country`.
2. **`FinalizeSaleDrawer`** : sélecteur « Pays de facturation » (préréglé), lookup SIRENE et
   autocomplete BAN seulement en France, champ libre ailleurs avec le libellé du pays (SIREN /
   SIRET, IDE (CHE), Numéro BCE, Numéro RCS, NEQ), contrôle de la forme du code postal,
   « Montant (€) » conservé (on encaisse en euros).
3. **Identifiant fiscal optionnel hors France** (`missing_billing_fields` + drawer) : Qonto
   documente le TIN comme optionnel à la création du client ; jamais de chaîne vide envoyée.
   ⚠️ Reste à vérifier en sandbox Qonto avec un client CH/CA sans TIN (voir § 9 du plan vague 4).
4. **Qonto** : EUR partout ; `vat_exemption_reason` par pays — `S293B` (art. 293 B) en France,
   `S283` (autoliquidation, art. 196 directive TVA / art. 283-2 CGI) pour un B2B de l'UE
   (BE/LU), `S259` (prestation de services exportée hors UE, art. 259-1 CGI) pour CH/CA, la
   mention en clair répétée dans `terms_and_conditions` hors France. Le CHF n'est pas géré
   (décision : facturer en euros, la banque du client convertit).
5. **Domaine** : `suggestion_service.suggest(…, country)` propose les TLD du profil
   (`.fr` / `.ch` / `.be` / `.lu` / `.ca`), prix OVH par TLD.
6. **Extraction ville/CP** : `GoogleScraper.extract_city`, `OSMScraper.extract_city`,
   `facebook_enrichment_scraper._parse_city_postal` et la garde `_place_mismatch` lisent le
   motif du profil (mots pays « Suisse / Belgique / Québec, QC, Canada » compris) ; Nominatim
   `countrycodes` suit le pays jusque dans l'enrichissement OSM.

## 🟠 Reste — dégrade la qualité CH/BE (non bloquant pour la vague email)

- **Parseur téléphone FB** (`_FR_PHONE_RE`) : ignore `+41`/`+32` → prospect FB CH/BE sans tel
  (le plan nord-américain est lu pour un prospect CA).
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

## Décisions associées (vague 3, révisées vague 4)

- USA = email only (TCPA interdit le cold SMS) et chaîne 100 % FR à traduire d'abord. Suisse :
  rester en 1-to-1 ultra-personnalisé (la « publicité de masse » y est opt-in).
- **Québec (CA) ouvert par email** à la vague 4 (plan `wave-4-plan.md` § 4) : téléphone NANP
  (« 514 555-0199 », jamais lu comme un numéro français), code postal `A1A 1A1`, recherche
  suffixée « Québec », pas de SMS (`sms_prospecting_open=False`), pied de mail CASL avec
  l'adresse postale `SENDER_POSTAL_ADDRESS`, lexique régional (devis → soumission, e-mail →
  courriel, portable → cellulaire) appliqué au rendu des messages et aux textes des sites.
- **Prix** : plus de modèle email par pays — `{prix}` et `{prix_assistant}` sont rendus dans la
  monnaie du prospect par `CountryProfile.format_price` (« 500 € », « ≈ 470 CHF », « ≈ 800 $ CA »).
