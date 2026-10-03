# Passe multi-pays : tout ce qui suppose encore la France (Québec, Suisse, Belgique, Luxembourg)

> Audit réalisé le 2026-10-03 sur le worktree `dlh-w4-audit` (branche `docs/multi-country-audit`,
> partie de `main` au commit `3dcc87ee`). Prérequis de la vague 4 (France × Suisse × Québec).
> Même méthode que `docs/EUROPE_AUDIT.md` du 21/09 : inventaire fichier par fichier, ligne exacte,
> correctif, gravité. Décision produit (03/10) : « le logiciel entier, et tous les modules, doivent
> fonctionner pour des prospects québécois, suisses, belges, puis d'autres francophones ; les
> anglophones plus tard ».
>
> **Socle** : `api/services/country_profiles.py` (`CountryProfile`, `CountryProfiles`) et
> `api/enums/country.py`. Le profil sait aujourd'hui : `label`, `enabled`, `currency`, `eur_rate`,
> `price_format` (+ `format_price`), `timezone`, `dial_code`, `postal_code_pattern`,
> `sms_prospecting_open`, `sms_opt_out`, `email_footer_needs_postal_address`, `tax_id_label`,
> `tax_id_required`, `domain_tlds`, `lexicon`. Pour chaque point ci-dessous, la colonne
> « correctif » dit quel fait du profil lire, ou quel fait manque encore (synthèse au § B).
>
> **Gravité** : `bloquant vente` (empêche ou fausse une vente, un envoi payant, un message au
> prospect) · `dégrade` (le résultat est faux ou pauvre, la vente reste possible) · `cosmétique` ·
> `non-problème` (vérifié, rien à faire) · `en cours` (traité par un ticket parallèle, cité pour
> mémoire). Les lignes sont celles de `rg -n` au commit `3dcc87ee` ; les chemins sont relatifs
> au dépôt.
>
> **Comptage brut** (hors `api/tests/`) : `\d{5}` 12 fichiers · `Europe/Paris` 9 · `geo.api.gouv`
> 5 · `api-adresse` 2 · `+33` 14 · `36180` 6 · `SIREN|SIRET` 14 · `.fr` en dur dans le domaine
> 6 · `fr-FR` 31 (presque tous = affichage pour l'utilisateur) · `€` 52 (prix, exemples, aide).

## État au 2026-10-03 (soir) : ce qui est livré depuis cet audit

Les tickets du § A sont fusionnés sur `main` et déployés : fenêtre d'envoi au fuseau du prospect
(`5906b7c6`), licence RBQ et 10 templates republiés (`b78ecaeb`), Québec ouvert + dette de vente
Europe (`e4d71846`), SMS de prospection vers la Suisse + modèles francs (`4af58720`). Les lignes
du corps de ce document décrivent l'état du commit `3dcc87ee` ; voici ce qu'elles deviennent.

**Corrigé** : `country` dans l'export/import JSON des prospects ; `extract_city` et les codes postaux
lus au format du pays (scrapers, découpage d'adresse à la vente, ville avant le code au Québec) ;
`TaxIdLookupInput` et `PostalCodeAutocompleteInput` ne mutilent plus une saisie hors France ;
`FinalizeSaleDrawer` (pays du prospect, libellé fiscal par pays, facultatif hors France, licence RBQ
pour un prospect CA) ; mention TVA Qonto par pays (S293B, S283, S259 : codes présents dans l'API
Qonto) ; domaines par pays et RDAP sans faux « disponible » ; pays transmis jusqu'à `build_content_json`
et lexique régional dans les emails, les SMS et les sites ; `{prix}` dans la monnaie du prospect
(arrondi à l'unité sous 200) ; pied de mail CASL (« Envoyé par {entreprise} ({nom}), {adresse} », lu
sur le profil de l'utilisateur qui envoie : champ « Adresse postale » de « Mon profil »,
`users.postal_address` ; tant qu'il est vide, tout email commercial vers un prospect québécois est
retenu, avec la raison affichée sur la ligne de la campagne) ; téléphone nord-américain (lecture,
affichage, jamais un mobile SMS) ; garde pays sur
tous les envois SMS, `send_manual` compris, lue sur le profil déclaré ; mention de désinscription posée
par smsmode (`body.stop`) au lieu de « STOP au 36180 » ; « ≈ » écrit « env. » en SMS ; numéro de
l'expéditeur en format international pour un prospect hors de France ; fenêtre légale et fériés SMS
par pays ; coût SMS par pays ; `plumber_atelier` sans « 0 € / 10 ans » ; recherche d'emails au pays du
prospect (`gl` du pays et `hl=fr` sur toutes les recherches Google, téléphone cherché sous sa forme nationale,
pays transmis par les scrapers Maps, OSM et auto, par le sidecar d'enrichissement et par `enrich_cli`) ;
annuaires, plateformes, messageries grand public et domaines publics CH, BE, LU et CA reconnus (scoring email,
sous-domaines compris, `x.qc.ca` découpé après `qc.ca`, site d'annuaire jamais compté comme vrai site,
mini-sites d'annuaire, « Domain zu verkaufen ») ; numéros CH, BE et LU lus sur Facebook dans la forme du pays
(un « 079 » suisse n'est plus lu comme un mobile français), affichés dans leurs blocs nationaux ;
pied légal et pages `/legal` et `/privacy` sur tous les sites générés, démo comme site vendu, calculés par l'API pour le
pays de l'entreprise (§ 4.3).

**Encore ouvert** : carte de couverture sans le Québec ; Réceptionniste
IA hors France (§ 7 : fuseau du client, +1, expéditeur, pied légal) ; décisionnaire hors France ;
probe Qonto en sandbox (client CH ou CA sans numéro fiscal, doublon éventuel de mention) ; achat
d'un `.com` (ou d'un `.ca` au nom du client) par l'automatisation de domaine ; boucles SMS automatiques limitées à la France tant que le premier SMS suisse
n'est pas vérifié (`SmsProspectingRules.AUTOMATIC_SMS_COUNTRIES`).

## A. En cours ailleurs (ne pas refaire, juste s'y brancher)

| Ticket | Ce qu'il couvre | Ce que cet audit lui transmet |
|---|---|---|
| Dette Europe bloquante à la vente + Support Québec (`1218704239762835`, `1219123795694887`) | pays `CA` ouvert, catalogue front + drapeau, téléphone NANP, CP `A1A 1A1` et adresse « Ville (Québec) » dans `_split_postal_address`, `{prix}` par pays, lexique régional, pied de mail CASL, endpoint `/countries`, `UiTaxIdLookupInput`, `FinalizeSaleDrawer` | les trois pièges du § C, le bloc légal des sites (§ 4.3), le Qonto `locale`/`vat_exemption_reason` (§ 6.2) |
| Fenêtre d'envoi au fuseau du prospect (`1219123794179571`) | `_schedule_slots`, relances, `SendPolicy` | le fuseau du module Réceptionniste est un chantier séparé (73 appels, § 7.2) |
| SMS de prospection vers la Suisse (`1219123040905231`) | garde CH, normalisation par pays, désinscription par pays, segments, fenêtre et fériés par pays, coût par pays | `send_manual` sans garde (§ 5, bloquant), le « ≈ » hors GSM-7 (§ C) |
| Licence RBQ (`1219124186850310`) | champ prospect, registre public, affichage dans les 10 templates, audit des mots France-only dans les layers | le contrat `site_content` n'a aucun champ légal (§ 4.3) : la licence a besoin d'un bloc `legal` |
| Modèles email/SMS francs (`1219122474057965`) | refonte des modèles 30-33 et SMS | « devis », « email » dans les modèles SMS (§ 5.9) |
| Manuel : numéro court smsmode + adresse postale (`1219123795667029`) | | l'adresse postale est une donnée de l'utilisateur, pas du pays (§ 5.2) |

## B. Faits manquants au profil (synthèse, pour une seule extension de `CountryProfile`)

| Fait proposé | Sert à | Domaine |
|---|---|---|
| `search_suffix` | suffixe des requêtes Maps/Facebook/email (`""` FR, « Suisse », « QC, Canada ») : le `label` « Canada (Québec) » est mauvais dans une requête | 1 |
| `country_names` | mots à retirer en fin d'adresse (« Suisse », « Schweiz », « Switzerland », « Canada ») | 1, 3 |
| `city_before_postal` | ordre « Ville, QC H2X 3K8 » au Canada, « 1204 Genève » ailleurs | 1, 3, 6 |
| `language` | `hl=`, `setlang=`, préposition « à », salutation, jours de la semaine ; indispensable aux anglophones | 1, 4, 7 |
| `directory_domains` + `public_domain_patterns` | blocklists d'annuaires et d'administrations par pays | 1 |
| `registry_name`, `registry_search_url`, `legal_mention_paths`, `activity_code_system` | décisionnaire par registre local, `/impressum` | 1 |
| `trunk_prefix`, `mobile_prefixes` (vide = « inconnu », CA) | normalisation et détection mobile par pays (données déjà dans `_SERVED_MOBILE_RANGES`) | 5, 7 |
| `sms_window`, `holidays_country`, `holidays_subdiv` | fenêtre légale et fériés par pays (CH par canton, CA `QC`) | 5 |
| `sms_segment_price_eur` | coût estimé par pays (FR 0,061 ; CA 0,022 selon smsmode ; CH à vérifier) | 5, 8 |
| `sms_sender_mode` (alphanumérique / numérique) | CA refuse un expéditeur « Dibodev » ; BE le remplace par un code court | 5, 7 |
| `invoice_locale`, `vat_exemption_reason`, `invoice_currency`, `vat_number_required`, `tax_id_pattern`, `registrant_must_be_local` | Qonto : `locale`, code TVA, devise du client ; n° TVA du client obligatoire pour l'autoliquidation (BE/LU) ; validation de l'identifiant fiscal par pays ; `.ca` réservé à un titulaire canadien | 6 |
| `postal_area_prefix_len`, `mailbox_provider_domains` | garde-fou homonyme par zone (FR 2, CA 3) ; familles de boîtes mail par pays (bluewin.ch, skynet.be, videotron.ca…) pour la page Santé email | 3, 8 |
| Côté commande (pas pays) : `orders.billing_region` | province québécoise (champ `state` Stripe, adresse Qonto `province_code`) | 6 |
| fait : `site_legal` (`SiteLegalFacts` : `locale`, titres et liens du pied, `legal_id_label`, `vat_number_label`, `is_publication_director_required`, `is_host_disclosure_required`, `privacy_regime`, autorité de contrôle) ; restent `trade_permit_label`, `contact_label`, `payment_methods_phrase` | pied de page et page légale des sites générés (§ 4.3) ; restent « Nous joindre », moyens de paiement, autorisation d'établissement | 4 |
| `map_region_label`, `map_regions_file` | carte : « Régions administratives », fichier geojson du pays | 2 |
| Côté utilisateur (pas pays) : `users.postal_address`, `users.city`, `ai_assistants.timezone` | pied CASL, script vidéo, fuseau de l'artisan | 5, 4, 7 |

## C. Trois pièges transverses à transmettre aux tickets en cours

1. **`CountryProfiles.get()` retombe sur la France pour un code fermé ou inconnu** (`api/services/country_profiles.py:197-201`). `CA` est déclaré mais `enabled=False` ; un prospect peut déjà porter `country="CA"` (création sans liste blanche : `api/services/prospect_service.py:297` ; mise à jour sans contrôle : `:452`). Toute décision « SMS ouvert ? », « pied CASL ? », « prix ? » doit lire `CountryProfiles.declared(code)` et traiter `None` ou `enabled=False` comme fermé. Remplacer la garde `!= "FR"` par `get(...).sms_prospecting_open` ouvrirait le SMS au Québec. Et une recherche de prospects `CA` devient aujourd'hui une recherche France sans message (`api/enums/country.py:27`, `api/services/scraping_job_service.py:51`).
2. **Le « ≈ » de « ≈ 470 CHF » n'est pas dans l'alphabet GSM-7** : `api/services/sms/gsm_segments.py:27-37` ne le translittère pas, le SMS passe en Unicode (70 caractères par segment) et les modèles à `{prix}` (`api/services/sms/templates.py:173`, `:182`) seront refusés comme trop longs. Prévoir « env. 470 CHF » pour le SMS, ou une entrée `"≈": "env."` dans la table.
3. **Le lexique mot à mot casse l'accord** : « devis » → « soumission » donne « Le soumission est-il gratuit ? » (`api/services/templates/site_content.py:55`, `landscaper_verdure.py:208` « Demander un soumission gratuit »). Le lexique CA a besoin d'expressions, plus longues d'abord : « le devis est-il gratuit » → « la soumission est-elle gratuite », « un devis gratuit » → « une soumission gratuite », « du/au devis » → « de la/à la soumission ». Entrées manquantes : « week-end » → « fin de semaine », « SMS » → « texto », « à emporter » → « pour emporter ».

## D. Ce que `EUROPE_AUDIT.md` classait « à faire » et qui est fait depuis

- Copie plombier partagée (« décennale », « chèque ») : neutralisée dans l'API (commit `aa575238`, `api/services/templates/site_content.py:64-68`, `plumber_cuivre.py:154`, `:170`). Reste : `api/services/templates/plumber_atelier.py:142-143` (« 0 € », « 10 ans, Travaux garantis ») et le dump `demo-host/app/utils/previewLayers.json` (voir § 4).
- Tout le reste de la liste rouge et orange du 21/09 est encore là, relocalisé ci-dessous avec les lignes actuelles.

---

## 1. Recherche de prospects

Chemin du pays vérifié : `SearchProspectsDrawer.vue:405` → `ScrapingJobCreate.country` (`api/models/scraping_job.py:29`) → `scraping_job_service.py:51` (`normalize_country`) → `scrape_all(country=…)` (`:255`) → `scraper_service.py:183` retire Pages Jaunes et l'unlocker hors FR → `scraper.scrape(country=…)` (`:127`). Google Maps : `google_scraper.py:793` `build_query(category, city, country)` ; SERP Bright Data : `brightdata_client.py:124` `gl=` / `:141` `cc=` ; OSM : `osm_scraper.py:160` `countrycodes=`. Là où le pays n'arrive pas : `email_scraper`, `osm_enrichment`, `enrichment_scraper`, `acquisition_service`.

| fichier:ligne | ce qui suppose la France | correctif proposé (fait du profil) | gravité |
|---|---|---|---|
| `api/enums/country.py:27` | `normalize_country` renvoie `CountryProfiles.get(code).code` : un pays fermé (CA) ou inconnu devient `FR` en silence | refuser (422) à la création du job un code dont `CountryProfiles.declared(code)` n'est pas `enabled` | bloquant vente (CA) |
| `api/services/scraping_job_service.py:51` | `country=normalize_country(job_data.country)` : c'est ici que CA devient FR, Pages Jaunes comprise | même correctif | bloquant vente (CA) |
| `api/enums/country.py:40` + `api/scrappers/google_scraper.py:249` + `api/scrappers/facebook_search_scraper.py:325` | `country_label(country)` sert de suffixe de requête : « plombier à Laval Canada (Québec) » (« Québec » est aussi une ville, Google ignore les parenthèses) | fait manquant `search_suffix` : FR `""`, CH « Suisse », BE « Belgique », LU « Luxembourg », CA « QC, Canada » | dégrade (CA) ; non-problème CH/BE/LU |
| `api/scrappers/google_scraper.py:268` | `extract_city` : `\b(\d{5})\s+(.+)$`, puis repli `parts[-1]` (`:272`) = dernier segment de l'adresse : « Suisse », « Belgique », « Canada », « 1204 Genève », « QC H2X 3K8 ». La ville fausse part dans `{ville}` des emails et sur le site démo | `profile.postal_code_pattern` + retrait de `country_names` en fin d'adresse + `city_before_postal` | bloquant vente (hors FR, dès que le sourcing passe par l'app) |
| `api/scrappers/google_scraper.py:246` | préposition « à {city} » | `language` (anglophones seulement) | cosmétique |
| `api/scrappers/google_scraper.py:303` / `:896` | `build_business_query(name, city)` et `find_email(name, city, …)` sans le pays | passer `country`, `search_suffix` | dégrade |
| `api/scrappers/google_scraper.py:794` | `google.com/maps/search/{query}` sans `hl`/`gl` | aucun : domaine neutre, le pays est dans la requête | non-problème |
| `api/scrappers/osm_scraper.py:118` | Overpass `area["name"="{city}"]["admin_level"~"[8-9]"]` sans pays : homonymes Mons, Fribourg, Montréal (Aude) | filtrer d'abord une zone `["ISO3166-1"="{profile.code}"]` | dégrade |
| `api/scrappers/osm_scraper.py:160` | `countrycodes=country.lower()` | aucun (CA donnerait `ca`) | non-problème |
| `api/scrappers/osm_scraper.py:74` | `\d{5}` dans `extract_city` | code mort, jamais appelé | non-problème |
| `api/scrappers/osm_enrichment.py:204` | `"countrycodes": "fr"` **en dur** : aucun enrichissement OSM hors France, ou l'homonyme français | `profile.code.lower()` | dégrade |
| `api/scrappers/enrichment_scraper.py:567` / `:602` / `:694` | `enrich(…, city=…)`, `enrich_from_osm(name, city)`, recherche Maps « nom + ville » : jamais le pays | ajouter `country` (lu sur `prospect.country`) | dégrade |
| `api/scrappers/pagesjaunes_scraper.py:791` / `:102` | `if country != "FR": return []` protège le `\d{5}` | aucun | non-problème |
| `api/scrappers/brightdata_scraper.py:331` / `:340` / `:500` | `\d{5}` et `google(query)` sans pays, chaîne réservée FR (`:544`) | aucun | non-problème |
| `api/scrappers/brightdata_client.py:124` / `:141` | `gl=`/`cc=` suivent le pays mais `hl=fr`, `setlang=fr` en dur | `language` | cosmétique |
| `api/scrappers/email_scraper.py:127` / `:130` / `:192` | `google.com/search?q=…` sans `gl` : classement selon l'IP française ; requête `{name} {city} email` sans pays | `&gl={profile.code.lower()}`, `search_suffix` | dégrade |
| `api/scrappers/email_scraper.py:385` | `&gl=fr&hl=fr` **en dur** | `gl=profile.code.lower()` | dégrade |
| `api/scrappers/email_scraper.py:255` / `:375` | téléphone « +33 → 0 », paires de 2 chiffres : un « +41 79 … » n'est jamais cherché dans sa forme locale | format national par `dial_code` / `phonenumbers` (absent de `api/requirements.txt`) | dégrade |
| `api/scrappers/email_scraper.py:434` / `:475` | `find_email_smart` / `find_email` n'ont pas de paramètre pays | ajouter `country` | dégrade |
| `api/scrappers/email_candidate_scoring.py:67-129` | `BLOCKED_DOMAINS` = `frozenset` de chaînes, comparaison exacte sur le domaine (`:252`) ; annuaires FR seulement : pagesjaunes.fr, pages-jaunes.fr, annuaire.com, kompass.com, societe.com, verif.com, infogreffe.fr, 118000.fr, 118712.fr, mappy.com, hoodspot.fr, starofservice.com, travaux.com, houzz.fr, justacote.com, cylex.fr… | ajouter (liste globale, sans risque) : **CH** local.ch, search.ch, tel.search.ch, localsearch.ch, moneyhouse.ch, zefix.ch, zefix.admin.ch, help.ch, monetas.ch, renovero.ch, ofri.ch, houzz.ch, yelp.ch ; **BE** goldenpages.be, pagesdor.be, goudengids.be, kbopub.economie.fgov.be, infobel.be, companyweb.be, trendstop.levif.be, openthebox.be, 1307.be, houzz.be ; **LU** editus.lu, yellow.lu, lbr.lu ; **CA** pagesjaunes.ca, yellowpages.ca, 411.ca, canada411.ca, registreentreprises.gouv.qc.ca, soumissionrenovation.ca, reno-assistance.ca, homestars.com, houzz.ca, yelp.ca, opencorporates.com, bbb.org, canpages.ca (à vérifier). Un sous-domaine (`mail.local.ch`) n'est pas bloqué : passer à « domaine ou sous-domaine » | dégrade |
| `api/scrappers/email_candidate_scoring.py:140` | seul domaine d'État reconnu : `\.gouv\.fr$` | `public_domain_patterns` : `\.admin\.ch$`, cantons `.ch`, `\.fgov\.be$`, `\.belgium\.be$`, `\.public\.lu$`, `\.gc\.ca$`, `\.gouv\.qc\.ca$`, `(^|[.-])ville\.`, `cpas-`, `mrc-` | dégrade |
| `api/scrappers/email_candidate_scoring.py:132` / `:161` / `:178` | sous-chaînes « mairie », « prefecture », « gendarmerie » ; boîtes de rôle « devis » | ajouter « commune », « gemeinde », « municipalite » ; « soumission » (lexique) ; « kontakt » | cosmétique |
| `api/scrappers/email_candidate_scoring.py:34` | fournisseurs grand public FR seulement (orange.fr, free.fr…) | bluewin.ch, gmx.ch, sunrise.ch, skynet.be, telenet.be, proximus.be, voo.be, pt.lu, videotron.ca, sympatico.ca, bell.net, hotmail.ca | cosmétique |
| `api/scrappers/email_candidate_scoring.py:327` | `_registrable_label` prend `parts[-2]` : pour `x.qc.ca` c'est « qc » (bonus +100 à tort entre deux `.qc.ca`) | liste des suffixes publics (`tldextract`, absent) | dégrade (CA) |
| `api/scrappers/facebook_enrichment_scraper.py:552` / `:554` / `:593` | `_CITY_FRANCE_POSTAL_RE` exige le mot « France » + `\d{5}` ; `_POSTAL_CITY_RE` `\b(\d{5})\b` ; nettoyage ne retire que « France », « Frankreich » | regex construite avec `postal_code_pattern` et `country_names` | dégrade |
| `api/scrappers/facebook_enrichment_scraper.py:609` | `_FR_PHONE_RE` : rate +41, +352, +1 ; capte les mobiles belges 04xx et les réécrit en paires françaises | `phonenumbers.PhoneNumberMatcher(text, profile.code)` ou parseur par `dial_code` | dégrade |
| `api/scrappers/facebook_enrichment_scraper.py:903` / `api/scrappers/auto_scraper.py:124` | `enrich(business_name, facebook_url)`, `find_email_smart` sans pays | ajouter `country` | dégrade |
| `api/scrappers/resilient_extract.py:64` | exige ≥ 10 chiffres : rate fixes belges et numéros luxembourgeois (9 chiffres) | le repli brut de `google_scraper.py:430` compense | non-problème (JSON-LD seul : cosmétique) |
| `api/services/scraper_service.py:44` / `:85` / `:211` | `_FRANCE_ONLY_SOURCES` en dur ; `source=pagesjaunes` demandé avec CH tourne quand même (vide, logué « empty ») ; diagnostics sans pays | fait manquant `sources` ; retirer la source réservée ; enregistrer `country` | cosmétique |
| `api/services/validation_service.py:53` | plateformes et annuaires `.fr` : hors France un `treatwell.be` ou `pagesjaunes.ca` compte comme vrai site et le prospect est **exclu** | ajouter local.ch, search.ch, treatwell.ch/.be, goldenpages.be, editus.lu, pagesjaunes.ca, yellowpages.ca, skipthedishes.com, doordash.com, opentable.ca | dégrade |
| `api/services/validation_service.py:31` / `:303` | formes juridiques FR (sarl, sas, eurl) ; contrôle département 5 chiffres (hors FR, `:309` compare la ville) | ajouter gmbh, sprl, srl, asbl, inc, ltée, enr | cosmétique / non-problème |
| `api/services/website_liveness_service.py:45` / `:57` | seul mini-site d'annuaire connu : pagesjaunes.fr ; marqueurs « domaine à vendre » FR/EN | mini-sites localsearch (CH), pagesjaunes.ca ; « Domain zu verkaufen » | cosmétique |
| `api/services/acquisition_service.py:226` / `api/services/acquisition_orchestrator.py:179` | sélection des prospects par ville (sous-chaîne) sans pays : « Mons » prend FR et BE | filtrer sur `ProspectDB.country` ; fait manquant au run : `search_country` | dégrade |
| `api/services/sourcing_verticals.py:76` | « Agence immobilière » (QC : « courtier immobilier ») | termes par `lexicon` | cosmétique |
| `api/services/enrichment_service.py:392` | garde `(prospect.country or "FR") != "FR"` : coupe **toute** la cascade décisionnaire, y compris les 3 stratégies sans registre (avis, mentions légales, IA) qui ne sont jamais `primary` et ne peuvent produire qu'un nom « à confirmer » | garde **par stratégie** (attribut `countries`), champ `country` dans `ResolutionContext` (`api/services/decision_maker/types.py:96`) | dégrade |
| `api/services/decision_maker/strategies.py:33` / `:34` / `:207` / `:342` | recherche-entreprises.api.gouv.fr, api.pappers.fr, département = 2 premiers chiffres, `google(query)` donc `gl=fr` | protégés par la garde ; passer le pays si la garde devient par stratégie | non-problème |
| `api/services/decision_maker/strategies.py:470` / `:463` | chemins `/mentions-legales`, `/a-propos`, `/about` ; rôles « gérant », « directeur de publication » | fait manquant `legal_mention_paths` (CH `/impressum`, BE « éditeur responsable », QC `/nous-joindre`) ; « Inhaber », « Geschäftsführer » | dégrade |
| `api/services/decision_maker/resolver.py:35` / `activity.py:28` / `normalize.py:17` / `greeting.py:39` | `\b(\d{5})\b` ; codes NAF ; formes juridiques FR ; repli « Bonjour » | `postal_code_pattern` ; `activity_code_system` (NOGA, NACE-BEL, SCIAN) ; ajouter gmbh, ag, inc, ltée ; `language` | non-problème (FR) / cosmétique |
| `web/app/utils/prospectCountries.ts:18-23` + `web/app/types/index.ts:22` | catalogue fixe `FR/CH/BE/LU` recopié du back ; ouvrir CA = 3 fichiers | endpoint `/countries` qui expose `CountryProfiles.enabled()` | bloquant vente (CA), en cours |
| `web/app/components/ui/SearchProspectsDrawer.vue:92` | `UiCityAutocompleteInput` interroge geo.api.gouv.fr (`CityAutocompleteInput.vue:124`) quel que soit le pays | couper hors FR ou Photon/Nominatim avec `countrycodes` | dégrade |
| `web/app/components/ui/SearchProspectsDrawer.vue:372` | pays gardé en localStorage : après une recherche CH, une ville française peut partir en CH | remettre FR quand la ville change | cosmétique |
| `web/app/pages/dashboard/search-prospects.vue:44` / `:218` | « catégorie · ville » sans le pays | `ProspectCountries.suffix(job.country)` | cosmétique |
| `api/api/v1/routes/prospects.py:140` | route `/search` (dépréciée) : `scrape_all` sans pays | supprimer ou passer `country` | cosmétique |

**Décisionnaire par registre local, faisabilité :**

- Cascade actuelle (`resolver.py:43-54`, six stratégies en parallèle) : RegistreGouv (recherche-entreprises, `primary`), Pappers (clé requise, `primary`), WebRegistry (Google puis RegistreGouv, `primary`), OwnerResponse (signatures dans les réponses aux avis, 0,55-0,7), LegalMentions (`/mentions-legales`…, 0,75), LlmAggregate (0,6). `pick_best` (`:66`) : AUTO seulement si `primary` + localisation confirmée + confiance ≥ 0,7. Garde pays : une seule, globale, `enrichment_service.py:392`.
- **Zefix (CH)** : faisabilité moyenne, la meilleure. API REST `https://www.zefix.admin.ch/ZefixPublicREST/api/v1`, gratuite mais **compte obligatoire** (Basic auth, demande à zefix@bj.admin.ch). Recherche par nom + siège → IDE (CHE) + publications FOSC. Les personnes ne sont pas un champ structuré (texte FOSC, à vérifier). Une raison individuelle porte obligatoirement le nom du titulaire : bon signal. Limite : pas d'inscription obligatoire sous 100 000 CHF.
- **KBO/BCE (BE)** : moyenne à faible. Pas d'API gratuite ; `kbopub.economie.fgov.be` consultable sans compte (recherche par nom, fonctions listées sur la fiche) mais lecture HTML fragile ; open data CSV mensuel sur inscription, fonctions probablement absentes.
- **REQ (Québec)** : faible. Pas d'API ; données ouvertes mensuelles **sans les administrateurs** et sous CC BY-NC-SA (**pas d'usage commercial**). Reste la recherche web par nom ; si CAPTCHA, pas d'automatisation.
- Repli : la salutation neutre existe déjà (`greeting.py:39`). Hors France un prospect reçoit toujours « Bonjour », sauf prénom saisi à la main. Correct pour tous les pays visés, il ne manque que `language` pour les anglophones.

## 2. Carte de prospection (page Couverture)

| fichier:ligne | ce qui suppose la France | correctif proposé | gravité |
|---|---|---|---|
| `web/app/components/dashboard/CoverageMap.vue:149` | régions françaises chargées depuis `raw.githubusercontent.com/gregoiredavid/france-geojson/master/regions-version-simplifiee.geojson` (dépendance externe, non versionnée) | garder, ou rapatrier dans `web/public/` comme les régions étrangères | non-problème (FR) |
| `web/app/components/dashboard/CoverageMap.vue:158` / `:164-166` / `:184` / `:529` | `FRANCE_BOUNDS`, `MAP_MAX_BOUNDS` = [-13.0, 37.0] à [16.5, 55.5], `EUROPE_BOUNDS` ; cadrage initial = Europe si un prospect étranger existe, sinon France. Le Québec (longitudes -79 à -57) est **hors des limites de déplacement** : la carte ne peut pas y aller | cadrer par pays via `countryBounds()` (existe déjà `:674`) et `maxBounds` = union des boîtes des pays présents (ou le lever) ; faits manquants `map_regions_file`, `map_bbox` | bloquant (CA) pour la page, pas pour la vente |
| `web/app/components/dashboard/CoverageMap.vue:240` | `ProspectCountries.option(entry.country)` : un pays hors catalogue (CA) retombe sur l'option France : deuxième puce « France », prospects CA comptés nulle part | catalogue depuis `/countries` | dégrade (CA) |
| `web/app/components/dashboard/CoverageMap.vue:616` + `api/api/v1/routes/dashboard.py:337` | la zone « ville » ne transmet que le nom ; `coverage/prospects` filtre `city IN (...)` sans le pays : Laval (FR) et Laval (QC) mélangés | ajouter `country` à la zone et au filtre | dégrade |
| `web/app/composables/useFranceGeo.ts:17` | cache localStorage `dlh-cities-v5` : un `null` (ville CA ratée aujourd'hui) reste en cache pour toujours | passer à `dlh-cities-v6` avec le correctif CA | dégrade |
| `web/app/components/dashboard/CoverageMap.vue:190` | `REGION_LABELS = { FR: 'Régions', CH: 'Cantons', BE: 'Provinces', LU: 'Districts' }` : pas de CA | fait manquant `map_region_label` (CA : « Régions administratives ») | cosmétique |
| `web/app/components/dashboard/CoverageMap.vue:234` / `:790` | `selectedCountry = 'FR'` par défaut, puis premier pays de la liste | aucun | non-problème |
| `web/app/components/dashboard/CoverageMap.vue:243-260` | choroplèthe étrangère = point-in-polygon des villes géocodées dans `regions-ch-be-lu.geojson` (`foreignRegionAt`), clé = `properties.code` ISO 3166-2 ; FR = code INSEE région renvoyé par geo.api.gouv | marche tel quel pour CA si un geojson CA est servi avec `code` (ex. `CA-QC-06`), `name`, `country: "CA"` | non-problème |
| `web/app/components/dashboard/CoverageMap.vue:633` / `:643` / `:651` | `feature.properties?.nom ?? FRANCE_REGIONS[code]`, pré-remplissage de ville depuis `FRANCE_MAJOR_CITIES` | villes suggérées par pays (fait manquant `major_cities` ou table front par pays) | cosmétique |
| `web/app/utils/foreignRegions.ts:16` + `web/public/regions-ch-be-lu.geojson` | un seul fichier CH+BE+LU : 232 Ko, 40 features (26 CH, 11 BE, 3 LU), propriétés `code`/`name`/`country` ; noms belges en anglais (« West Flanders », « Liege », « Flemish Brabant ») | fichier par pays (`regions-ca.geojson`) ou un fichier étendu ; noms en français | cosmétique (noms) |
| `web/app/utils/franceTerritory.ts:9` / `:37` + `web/app/stores/coverage.ts:111` / `:122-124` | `FRANCE_REGIONS` (codes INSEE), `FRANCE_MAJOR_CITIES` : suggestions de villes = France seulement | table par pays | cosmétique |
| `web/app/composables/useFranceGeo.ts:125` / `:331` | `geo.api.gouv.fr/communes` : géocodage et reverse-géocodage FR | aucun pour FR ; le reverse (`reverseGeocodeCommune`) n'existe pas hors FR | non-problème / cosmétique |
| `web/app/composables/useFranceGeo.ts:146` / `:162-168` | Photon `photon.komoot.io` pour les villes hors France, requête `${city}, ${label}` (le `label` vient de `ProspectCountries` : pour CA aujourd'hui « Laval, **France** » puisque CA retombe sur l'option France), `lang: 'fr'`, **filtre côté client** sur `properties.countrycode === countryCode` | marche pour CA dès que CA est au catalogue avec le libellé « Canada » ; préférer `search_suffix` (« Laval, QC, Canada ») ; Photon est le bon choix (la politique d'usage de Nominatim interdit l'autocomplétion et limite à 1 req/s) | non-problème (CH/BE/LU) ; dégrade (CA) |
| `web/app/composables/useFranceGeo.ts:202` / `:275` / `:293` | branche `code === 'FR'` ; adresses de rue via `api-adresse.data.gouv.fr` (BAN) : hors FR, repli au centre-ville | Photon accepte aussi une adresse complète (à vérifier) | cosmétique |
| `web/app/services/franceGeoAutocompleteService.ts:45` / `:75` / `:79` | BAN `api-adresse` ; `/^\d{5}$/` ; `geo.api.gouv.fr/communes?codePostal=` | `postal_code_pattern` ; aucune suggestion hors FR (saisie libre) | dégrade (confort) |
| `web/app/components/ui/CitySelect.vue:64` / `CityAutocompleteInput.vue:124` / `web/app/types/UiCitySelect.ts:1` | autosuggest `geo.api.gouv.fr` partout (filtres, recherche, vente) | composant par pays (Photon `countrycode`) | dégrade (confort) |
| `api/schemas/dashboard.py:65` / `:83` | `country: str = "FR"` sur les agrégats de couverture, avec commentaire | aucun | non-problème |

**Canada : quel fichier, quelle taille** (estimations, rien n'a été téléchargé ; référence mesurée sur le fichier actuel : environ 17,5 octets par point une fois minifié, 123 Ko pour 7 033 points).
- Provinces : Natural Earth `ne_10m_admin_1_states_provinces` filtré `iso_a2 = CA` → **13 features** (10 provinces + 3 territoires), champ `iso_3166_2` déjà « CA-QC » ; simplifié ≈ 50 à 100 Ko pour les 13, 20 à 35 Ko pour le Québec seul. Domaine public.
- Québec : 17 régions administratives, Données Québec « Découpages administratifs » (MRNF, ex-MERN), licence CC-BY 4.0 (**attribution obligatoire**, `customAttribution` MapLibre) ; simplifié (mapshaper ~1 %, 4 décimales) ≈ 70 à 175 Ko. C'est le bon niveau pour une choroplèthe de prospection (Montréal, Laval, Montérégie, Capitale-Nationale…).
- Proposition : `web/public/regions-ca-qc.geojson` séparé, `code` = `CA-QC-<n° de région 01 à 17>`, `name` en français, `country: "CA"` (le comptage par préfixe `CA-` de `CoverageMap.vue:290` marche tel quel) ; `fetchForeignRegions` (`foreignRegions.ts:16`) charge une liste d'URL par pays présents ; `REGION_LABELS.CA = 'Régions administratives'` ; `maxBounds` depuis les boîtes des pays ; cache `dlh-cities-v6`. Boîtes approximatives (ouest, sud, est, nord) : FR [-5.6, 41.2, 9.9, 51.4], BE [2.5, 49.5, 6.4, 51.5], LU [5.7, 49.4, 6.6, 50.2], CH [5.9, 45.8, 10.5, 47.9], Québec [-79.8, 44.9, -57.1, 62.6].
- Non vérifié : l'origine et la licence de `regions-ch-be-lu.geojson` (le commit `251a233e` ne le dit pas ; noms anglais = Natural Earth ou geoBoundaries probable), la taille réelle du geojson FR distant (le commentaire `CoverageMap.vue:144` dit ≈ 220 Ko).

## 3. Enrichissement

| fichier:ligne | ce qui suppose la France | correctif proposé | gravité |
|---|---|---|---|
| `api/services/enrichment_service.py:46` / `:715` | `_POSTAL_CODE_RE = \b(\d{5})\b` pour le garde-fou homonyme de fiche : hors FR il est inactif (repli sur la ville) | `profile.postal_code_pattern` | dégrade |
| `api/services/enrichment_service.py:392` | garde décisionnaire (voir § 1) | garde par stratégie | dégrade |
| `api/services/address_service.py:27-29` | `remove_postal_code` : `\b\d{5}\b\s*` (« Pattern for French postal codes ») : « 1204 » et « H3B 1A1 » restent dans l'adresse affichée | `profile.postal_code_pattern` | cosmétique |
| `api/scrappers/facebook_enrichment_scraper.py:552` / `:554` / `:593` / `:609` | ville/CP et téléphone FB France-only (détail § 1) : un prospect FB CH/BE/LU/CA sort sans ville, sans CP, sans téléphone | voir § 1 | dégrade |
| `api/scrappers/google_scraper.py:268` | `extract_city` (voir § 1) : alimente `place_city`/`place_postal_code` | voir § 1 | bloquant vente |
| `api/services/decision_maker/resolver.py:35` | `\b(\d{5})\b` | `postal_code_pattern` quand une stratégie hors FR arrive | non-problème |
| `api/services/templates/site_content.py:471` | `_WEEKDAYS` = jours en français et anglais seulement : une ligne « Montag », « maandag », « Méindeg » est jetée et les horaires sortent vides (Suisse alémanique, Flandre, Luxembourg) | ajouter de/nl/lb, ou normaliser les jours au scraping (`opening_hours.py:48` connaît déjà `montag`/`maandag`) | dégrade |
| `api/services/ai_assistant/opening_hours.py:25` | `ZoneInfo("Europe/Paris")` pour lire « ouvert maintenant » (voir § 7) | `profile.timezone` / fuseau de l'assistant | bloquant (CA, module Réceptionniste) |
| `web/app/components/ui/ProspectPhones.vue:104` / `ProspectDrawer.vue:547` / `AddProspectDrawer.vue:142` | placeholder « 06 12 34 56 78 » | placeholder par `dial_code` (« 079 123 45 67 », « 514 555-0199 ») | cosmétique |
| `web/app/components/ui/ProspectPhones.vue:168-173` | clé d'identité = chiffres seuls : « 06… » et « +33… » fusionnent, mais « 079… » et « +41 79… » ne fusionnent pas | normaliser avec le pays du prospect | cosmétique |
| `web/app/components/ui/ProspectTable.vue:133` / `ProspectDrawer.vue:311` / `:1011` / `:1070` / `AddProspectDrawer.vue:282` / `:315` / `:413` | `'FR'` = défaut et « pas de drapeau pour la France » | aucun | non-problème |
| `api/requirements.txt` | ni `phonenumbers`, ni `holidays`, ni `tldextract` | décision à prendre (§ Questions) : `phonenumbers` règle FR/CH/BE/LU, mais classe un numéro canadien `FIXED_LINE_OR_MOBILE` | dégrade |
| `api/scrappers/facebook_enrichment_scraper.py:627-631` / `:566` | le numéro FB est remis en forme « 0X XX XX XX XX » et **perd l'indicatif** (un belge « 0470… » devient « 04 70 12 34 56 ») ; `_NON_CITY_WORDS` ne contient que « france » | stocker en E.164 ; `country_names` | dégrade |
| `api/services/enrichment_service.py:230-235` + `api/services/prospect_enrichment_service.py:65` (+ `scraper_sidecar.py:437`, `enrich_cli.py:143`) | `enrichment_scraper.enrich(...)` et `scrape_by_business_name(name, city)` (bouton « Pré-remplir depuis Google ») sans le pays | passer `prospect.country` | dégrade |
| `api/services/validation_service.py:303-304` | garde-fou homonyme : compare les 2 premiers chiffres du CP si 5 caractères ; hors FR il ne reste que la ville | fait manquant `postal_area_prefix_len` (FR 2, CA 3 pour « H3B ») | dégrade |
| `api/services/prospect_contact.py:20` (+ `prospect_phones.py:138`) | le « mobile FR » déduit d'un « 079… » range un prospect CH/LU **sans email** dans le canal `sms`, qui lui est fermé | lire `declared(country).sms_prospecting_open` | dégrade |
| `api/services/website_equipment_service.py:131` | `CONTACT_LINK_HINTS` sans « nous-joindre » ni « soumission » : le formulaire de contact d'un site québécois n'est pas détecté | ajouter ces mots (lexique) | dégrade |
| `web/app/components/ui/ProspectPhones.vue:44` + `ProspectTable.vue:143` | `tel:${number}` et affichage **bruts** : un « 079… » stocké sans indicatif, appelé depuis la France, compose un numéro français | `tel:` en E.164 construit avec `dial_code` | dégrade |
| `web/app/components/ui/ProspectDrawer.vue:568` / `:580` / `:1086` + `AddProspectDrawer.vue:65` / `:123` / `:133` / `:150` | adresse via la BAN et ville via geo.api.gouv : choisir une suggestion **remplace la ville par une commune française** ; le sélecteur Pays arrive après ces champs (`AddProspectDrawer.vue:148`) | BAN/geo.api.gouv seulement si `FR`, sinon Photon filtré par pays ; Pays en premier | dégrade |
| `api/scrappers/osm_enrichment.py:41-51` + `api/services/french_date_formatter.py:23-24` + `api/scrappers/resilient_extract.py:64` / `:163-164` + `api/models/prospect_enrichment.py:73` | jours en français (valables au Québec), `_PHONE_RE` accepte « (514) 555-1234 » et « +41… » (testé), CP/ville lus du JSON-LD, `place_postal_code` String(10) (« H3B 1A1 » tient) | aucun | non-problème |
| `api/services/trade_normalizer.py:20-52` + `api/services/photo_labeling_service.py:93` | métiers FR seulement (manquent « débosseleur », « nettoyeur ») ; consigne « commerce de restauration français » | quelques entrées QC ; « francophone » | cosmétique |

Au Québec le code postal est **après** la ville (« Montréal (Québec) H3B 1A1 ») : la logique « CP puis ville » de tous les parseurs ci-dessus est inversée, d'où le fait `city_before_postal`.

## 4. Sites générés

Constat principal : **le pays n'arrive jamais jusqu'au site**. `demo_site_service.py:253` et `:867` appellent `storyblok_service.build_content_json(…)` (`:118`) sans `country`, qui appelle `registry.build_site_content` (`:170-195`) puis le `build_site_content` du template et `map_prospect_and_enrichment` (`site_content.py:551`) : aucune de ces signatures n'a le pays, le dict retourné (`:644-671`) n'a pas de clé `country`, et la réponse publique `DemoSitePublicResponse` (`api/api/v1/routes/demo_sites.py:148`, `:164`) non plus. Rien ne peut donc être adapté : ni lexique, ni `lang`, ni pied de page. Les prix ne sont jamais formatés par le code (chaînes libres, « 32 € » du barbier retirés par `without_price`, `site_content.py:300`) : `format_price` n'a rien à faire ici. Les 10 layers vivent dans d'autres dépôts (`demo-host/nuxt.config.ts:10-19`) : leur pied de page, leur `lang`, leur carte et le format du téléphone affiché n'ont pas pu être vérifiés ; `previewLayers.json` est le seul dump disponible et il date du 2026-07-27.

| fichier:ligne | ce qui suppose la France | correctif proposé | gravité |
|---|---|---|---|
| `api/services/storyblok_service.py:118` + `api/services/demo_site_service.py:253` / `:867` + `api/services/templates/registry.py:170` + `site_content.py:551` | pas de pays dans la génération (prospect pourtant chargé `demo_site_service.py:174`, `:182`) | ajouter `country`, résoudre `CountryProfiles.declared(country)`, écrire `"country"` et `"locale"` dans le dict (`:644`) ; colonne `demo_sites.country` pour les démos sans prospect | dégrade (préalable à tout le reste) |
| `api/services/templates/site_content.py:873` | section contact = `contactHeading, businessName, phone, email, city, area, logo, openingHours, social` : **aucun champ légal** (ni SIRET, ni IDE, ni BCE, ni NEQ, ni licence RBQ), même pour un site vendu en France | bloc `legal` dans SiteContent (voir § 4.3) | bloquant vente (à la livraison, pas à la démo) |
| `api/services/templates/site_content.py:292` | `"Devis gratuit", "Sans engagement"` écrit par `apply_real_trust_stats` après les défauts : un lexique branché dans chaque template ne le verrait pas | brancher `localize_editorial(site, profile)` dans `registry.build_site_content` juste après `:186` | dégrade |
| `api/services/templates/site_content.py:55` / `:100` + `artisan_edito.py:69,83,102,128,133` + `plumber_cuivre.py:128,196,210,216` + `plumber_signature.py:483,488` + `electrician_lumen.py:651,653` + `landscaper_verdure.py:133,139,180,208,277` + `mechanic_pitlane.py:90,153,155,178` | « devis » (QC : « soumission ») avec accord en genre | lexique CA par **expressions** (§ C.3) | dégrade (CA) |
| `api/services/templates/site_content.py:51` / `food.py:155` | « week-end » (QC « fin de semaine »), « à emporter » (QC « pour emporter ») | entrées de lexique manquantes | cosmétique |
| `api/services/templates/site_content.py:64` + `food.py:147` + `barber.py:159` + `artisan_edito.py:115` + `plumber_cuivre.py:170` | « Carte, espèces et virement » : CH = TWINT courant ; QC = « argent comptant », « Interac » | fait manquant `payment_methods_phrase` | cosmétique |
| `api/services/templates/plumber_atelier.py:142` / `:143` | `{"value": "0 €", "label": "Devis sans engagement"}`, `{"value": "10 ans", "label": "Travaux garantis"}` (= décennale sous un autre nom ; faux en CH et au QC, 5 ans art. 2118 C.c.Q.) : oubliés par le correctif du 21/09, ce template n'appelle pas `apply_real_trust_stats` | « Gratuit » et « Travail garanti / Interventions assurées » comme plumber-cuivre ; corriger aussi le layer | dégrade |
| `api/services/templates/dental.py:81` / `:152` | « CHIRURGIEN-DENTISTE » (CH « médecin-dentiste », QC « dentiste »), « mutuelles » (CH « assurance complémentaire », QC « assurances dentaires ») | lexique CH (vide aujourd'hui) et CA | cosmétique |
| `api/services/templates/electrician_lumen.py:33` / `:351` / `:358` / `:487` | description catalogue « NF C 15-100, Consuel » ; décennale/Consuel dans `build_content` (code mort, `storyblok_service.py:171` n'appelle plus que `build_site_content`) | réécrire la description ; supprimer le code mort pour qu'il ne soit pas réactivé | cosmétique / non-problème |
| `api/services/templates/site_content.py:719` / `:801` / `:803` | aide de l'éditeur Storyblok : « Devis 0 € », « Email de contact », « Lyon et ses alentours » | « Devis gratuit » ; lexique sur `display_name` dans `registry.content_schemas` (`:212`) | cosmétique |
| `api/services/demo_site_service.py:198` | carte « nous trouver » sans `@lat,lng` dans l'URL Maps : le layer se centre sur sa ville par défaut (française) | géocoder avec le pays, ou masquer la carte sans coordonnées | dégrade |
| `api/services/service_card_suggestion_service.py:255` | prompt IA « commerce de restauration **français** » | « francophone ({profile.label}) » + consigne de lexique | cosmétique |
| `api/services/site_contact_email.py:121` | `to_e164_mobile(phone) or to_e164_fr(phone)` : un « 079… » saisi dans le formulaire contact de devleadhunter.fr est lu comme mobile français (boutons Appeler/WhatsApp vers un inconnu) | lire le pays du formulaire ou exiger `+41` | dégrade |
| `demo-host/app/components/DemoCtaBanner.vue:264` | `tel:` du numéro de l'expéditeur en forme nationale (« 06… ») : composé depuis CH/BE/LU/QC, mauvais numéro | stocker `users.contact_phone` en E.164 (normaliser à la sauvegarde, `auth.py:220`) | dégrade |
| `demo-host/app/utils/ContactLinkUtils.ts:27` | `google.com/maps/search/?api=1&query={place}` sans pays (« Mons », « Sion » ambigus) ; pas de `hl`/`gl` | ajouter `profile.label` à la requête | cosmétique |
| `demo-host/nuxt.config.ts:9` + `demo-host/app/components/DemoSiteView.vue` | demo-host ne pose jamais `htmlAttrs.lang` : jamais `fr-CA`/`fr-CH` (si les layers ne le font pas non plus, pas de `lang` du tout) | fait manquant `site_locale` + `useHead({ htmlAttrs: { lang } })` | cosmétique |
| `demo-host/app/pages/t/[templateId].vue:14` + `demo-host/app/utils/previewLayers.json:59` / `:80` / `:208` / `:321` / `:424` / `:529` / `:567` / `:1194` / `:6` | le catalogue public `/t/` (« asset commercial partageable ») montre le dump du 27/07, antérieur aux correctifs : « chèque », « Devis 0 € », « garantie décennale » ×3, « NF C 15-100 et attestation Consuel », « crédit d'impôt entretien de jardin », « Rennes » | régénérer le dump depuis l'API actuelle ; vérifier le layer verdure pour le crédit d'impôt | dégrade |
| `web/app/composables/useProspectionScript.ts:53` / `:54` | « je suis développeur web **à Rennes** » : ville du premier utilisateur en dur pour tous les utilisateurs, argument de proximité faux hors France ; le clip est enregistré **une fois par utilisateur** (`api/models/presenter_video.py:22`), donc un champ de profil ne changerait que le prompteur | tout de suite : « je suis développeur web » ; sinon `users.city` + `presenter_mentions_city` (FR) + colonne `market` sur `presenter_videos` | dégrade |
| `web/app/composables/useProspectionScript.ts:116` | « vous recevez un SMS » (QC « texto ») | lexique | cosmétique |
| `api/services/prospection_video_service.py`, `presenter_video_service.py`, `demo_video_service.py`, `video_montage.py:144` | aucun prix, aucun « € », « Bonjour {prénom} » valable partout | aucun | non-problème |
| `api/services/templates/barber.py:124-144` / `:217` | prix « 32 € », « 22 € »… en fin de description, retirés par `without_price` | aucun | non-problème |
| `api/services/templates/registry.py:69` | « à Le » → « au » marche aussi pour « au Locle », « aux Escoumins » | aucun | non-problème |

**4.3 Pied de page et mentions légales, par pays** (vérifié le 03/10 sur les textes consolidés ; ce n'est pas un avis d'avocat). Le tableau d'origine, écrit de mémoire, se trompait sur quatre points : l'article de la LCEN (l'ancien art. 6 III est devenu l'art. 1-1 avec la loi SREN du 21/05/2024), le répertoire des métiers (remplacé par le RNE le 01/01/2023), l'autorisation d'établissement luxembourgeoise (son numéro ou son code-barres doit figurer sur le site) et la licence RBQ (les membres de la CMEQ et de la CMMTQ en sont exemptés).

| Pays | Titre | Ce que la loi demande sur le site vitrine d'un artisan | Identifiant | Confidentialité |
|---|---|---|---|---|
| FR | « Mentions légales » | LCEN art. 1-1 : nom, prénoms, domicile et téléphone (personne physique) ou dénomination, siège, téléphone et capital (société), n° d'inscription au RCS ou au RNE (artisanat) ; directeur de la publication (art. 93-2 loi 82-652 : l'entrepreneur lui-même, ou le gérant) ; hébergeur avec nom, adresse et téléphone. LCEN art. 19 (art. 14 : les communications commerciales sont du commerce électronique) : adresse, e-mail, téléphone, n° TVA, autorité d'autorisation, profession réglementée. Sanction art. 1-2 : un an et 75 000 € | SIREN ou SIRET ; « RCS + ville du greffe » et « EI » (C. com. R123-237, R526-27) pour une entreprise au RCS ; « RM » obsolète | RGPD art. 13 ; durée CNIL : trois ans après le dernier contact (référentiel « gestion commerciale ») ; médiateur de la consommation sur le site si clientèle de particuliers (C. conso L616-1, R616-1) ; plus de lien vers la plateforme RLL, fermée le 20/07/2025 (règl. 2024/3228) |
| CH | « Impressum » (« Mentions légales » aussi en usage, aucune règle ; les sites affichent « Mentions légales ») | LCD art. 3 al. 1 let. s ch. 1 : identité et adresse de contact, e-mail compris (application à un site sans commande en ligne débattue ; par prudence oui, et un formulaire seul ne suffit pas) ; raison de commerce inscrite, complète (CO art. 954a) ; ni hébergeur ni directeur | IDE facultatif (LIDE art. 5 al. 3, OIDE art. 8 al. 5) | nLPD art. 19 (responsable, finalité, destinataires, États étrangers et garanties) ; LTC art. 45c (informer des cookies et de la façon de les refuser) ; PFPDT |
| BE | « Mentions légales » | CDE art. XII.6 (le SPF Économie l'applique aux sites vitrines) : nom, adresse, coordonnées dont l'e-mail, numéro d'entreprise, autorité d'autorisation, profession réglementée, n° TVA, codes de conduite. Société : CSA art. 2:20 (forme légale, siège, « RPM » suivi du tribunal). « Éditeur responsable » : imprimés seulement (nouveau Code pénal art. 671) | numéro d'entreprise (BCE), n° TVA | RGPD art. 13 ; APD |
| LU | « Mentions légales » | loi du 14/08/2000 art. 5(1) : nom, adresse, coordonnées dont l'e-mail, n° RCS, n° TVA, autorisation et autorité qui l'a délivrée ; loi du 02/09/2011 art. 28(1) et 34(1) : code-barres 2D ou numéro de l'autorisation d'établissement sur le site (amende de 25 à 250 €) | n° RCS (si commerçant), autorisation d'établissement | RGPD art. 13 ; CNPD |
| CA/QC | pas d'équivalent des mentions légales | licence RBQ dans toute publicité, site compris (Loi sur le bâtiment art. 57.1 ; exemptés : membres CMEQ et CMMTQ, tenus par les règles de leur corporation) ; site en français (Charte art. 52) | NEQ facultatif | LPRPSP (Loi 25) : art. 3.1 (titre et coordonnées du responsable, par défaut la personne ayant la plus haute autorité), art. 3.2 (politiques de gouvernance), art. 8 (fins, moyens, droits, retrait du consentement, communication hors Québec), art. 8.2 (politique publiée dès qu'on recueille par un moyen technologique ; la CAI y range les courriels reçus), art. 17 (évaluation avant de communiquer hors Québec) ; réponse sous 30 jours ; CAI |

Livré : un bloc `legal` calculé par l'API à chaque service du site (`api/services/site_legal/`), jamais stocké dans `content_json` (une publication Storyblok peut mettre à jour une ligne de contact, pas l'effacer), à partir du prospect, de l'identité de registre de confiance, de la vente et du profil pays (`CountryProfile.site_legal`) ; un lien discret en pied de chaque site et deux pages, `/legal` et `/privacy` (démo : `/{slug}/legal` et `/{slug}/privacy`), rendues par demo-host, sans toucher aux 10 layers ni au contrat `website-content`. Une démo nomme son éditeur (l'utilisateur DevLeadHunter, établi en France, avec l'adresse et le SIRET de « Mon profil ») et décrit la mesure PostHog ; un site vendu nomme l'entreprise et dit qu'il ne mesure rien.

Reste à collecter à la vente (aucune donnée en base aujourd'hui) : FR, le registre (« RCS de la ville du greffe » ou « RNE »), le capital d'une société, la mention « EI », le médiateur de la consommation ; BE, la forme légale et le tribunal d'une société ; LU, le numéro de l'autorisation d'établissement.

## 5. Emails et SMS

Variables email, toutes résolues dans `api/services/email_variables.py:333-357` (`salutation` 333, `prenom` 334, `nom` 335, `entreprise` 336, `ville` 337, `email` 338, `phone` 339, `metier` 340, `lien_demo` 341, `lien_assistant` 342, `prenom_receptionniste` 343, `lien_video` 344, `vignette_video` 345, `lien_video_assistant` 346, `vignette_video_assistant` 347-349, `ancien_site` 350, `prix` 351, `prix_assistant` 352-356, `date_expiration` 357). Dépendent du pays : `{prix}` et `{prix_assistant}` (devise) ; `{ville}` dépend de la qualité de l'extraction (§ 1). Point de branchement : `profile = CountryProfiles.declared(prospect.country)` en tête de `build_for_prospect` (`:323`), même chose `sms_variables.py:102` ; le plus simple est d'ajouter `country` à `PricingService.format_price` (`api/services/pricing_service.py:40-50`, qui force `DEFAULT_COUNTRY_CODE` à la ligne 50).

| fichier:ligne | ce qui suppose la France | correctif proposé | gravité |
|---|---|---|---|
| `api/services/sms_service.py:335-337` + `api/api/v1/routes/sms.py:532-552` + `web/app/components/ui/SendSmsDrawer.vue:380` | **`send_manual` n'a aucune garde pays** : `to_e164_fr(to_raw)` + `is_mobile_fr(to_raw)`. Le tiroir SMS pré-remplit `prospect.phone` : un « 079 123 45 67 » suisse devient `+33791234567` (mobile français valide), un « 621 123 456 » luxembourgeois devient `+33621123456`, et le SMS **part, payant, vers un inconnu**. La garde posée le 21/09 ne couvre que `send_to_prospect` (`:207-210`) | si `prospect_id` est fourni : charger le prospect, appliquer la même garde, normaliser avec `to_served_mobile(to_raw, country=prospect.country)` (déjà écrit, `phone_normalizer.py:104`) | **bloquant vente** |
| `api/services/country_profiles.py:197-201` | `get()` → FR pour CA (§ C.1) | `declared()` | en cours (piège) |
| `api/services/pricing_service.py:50` + `email_variables.py:351-356` + `sms_variables.py:119-123` + `assistant_pricing_service.py:78-80` | `{prix}`, `{prix_assistant}` toujours formatés FR | `profile.format_price` par `prospect.country` | en cours (Québec) |
| `api/services/sms/gsm_segments.py:27-37` + `sms/templates.py:173` / `:182` | « ≈ » hors GSM-7 (§ C.2) | « env. » ou format SMS dédié | en cours (piège) |
| `api/services/email_variables.py:190-191` | `{date_expiration}` calculée en UTC, pas au fuseau du prospect (un jour d'écart possible au Québec le soir) | convertir vers `profile.timezone` avant `day_month` | cosmétique |
| `api/services/email_variables.py:140` / `:333` | mois en français (« 12 octobre »), « Bonjour M./Mme » | aucun (valide dans les 5 pays) | non-problème |
| `api/services/unsubscribe_service.py:155-186` + `api/services/email_sending_service.py:257-268` | pied de mail = phrase + lien « Se désabonner » : **ni nom de l'expéditeur, ni adresse postale, ni contact**. CASL (Canada) exige nom + adresse postale + contact valables 60 jours ; `profile.email_footer_needs_postal_address` n'est lu **nulle part** | bloc identité ajouté quand le profil l'exige ; refuser l'envoi CA si l'adresse manque ; **fait manquant côté utilisateur** `users.postal_address` (`api/models/user.py` n'a que `company_name` :71 et `company_website_url` :74 ; `api/schemas/user.py` aucun champ postal) | en cours (Québec) |
| `api/services/unsubscribe_service.py:23-37` + `api/api/v1/routes/unsubscribe.py:102` / `:173` / `:203` + `email_sending_service.py:128-140` | jeton HMAC sans date limite (valable > 60 j CASL, > 30 j CAN-SPAM), GET + POST one-click, en-têtes RFC 8058, page `lang="fr"` | aucun | non-problème |
| `api/services/sms_service.py:55` / `:296-298` + `web/app/components/ui/SendSmsDrawer.vue:105` / `:142` / `:269` + `web/app/pages/dashboard/settings/sms.vue:229` + `web/app/pages/dashboard/campaigns/[id]/index.vue:982` + `web/app/components/ui/DrawerStackHost.vue:710` | « STOP au 36180 » en dur, idempotence testée sur « 36180 » ; `profile.sms_opt_out` (LINK pour CH, no-sms.eu) n'est lu **nulle part** (aucune occurrence de « no-sms » dans le dépôt) ; la regex de `DrawerStackHost` ne retirerait pas une mention en lien (doublon au renvoi) | mention par `sms_opt_out`, renvoyée par l'API au front | en cours (SMS Suisse) |
| `api/services/sms/send_window.py:17` / `:22-62` / `:66-74` / `:92-114` / `:126` / `:145` | `ZoneInfo("Europe/Paris")`, `now_in_paris`, horaires FR (lun-ven 8-20 h, sam 10-19 h), 11 fériés de métropole | `profile.timezone`, faits manquants `sms_window`, `holidays_country`, `holidays_subdiv` ; lib `holidays` absente de `api/requirements.txt` ; en Suisse les fériés dépendent du canton (déduire du CP ou prendre l'union) | en cours |
| `api/services/sms/pricing.py:25` + `api/core/config.py:396-400` | un seul tarif `smsmode_price_per_segment_eur` (défaut **0,061**, pas 0,045 : voir `api/migrations/rebackfill_sms_price_estimate.py:4-5`) | fait manquant `sms_segment_price_eur` ; passer le pays à `sms_service.py:516-518` | en cours |
| `api/services/sms/phone_normalizer.py:39-48` / `:61` / `:85-91` | tout 9 chiffres après retrait du 0 devient `+33…` (même sans 0 : « 621 123 456 » → `+33621123456`) ; mobile = `e164[3] in {6,7}` ; `to_e164_mobile` ne lit la forme nationale que pour FR. « 514 555-0199 » : 10 chiffres → `None` (refusé, pas lu comme 05 14…) ; « 079 123 45 67 » → `+33791234567` jugé mobile | `trunk_prefix` + `dial_code` + `mobile_prefixes` (données déjà dans `_SERVED_MOBILE_RANGES` `:95-101`) ou `phonenumbers` | en cours |
| `api/services/prospect_phones.py:28` / `:76` / `:138-139` | clé de doublon et « mobile en premier » via `to_e164_fr` ; `first_mobile_e164` sans le pays, utilisé par tous les chemins SMS (aussi `prospect_contact.py:20`, `demo_site_service.py:1533`, `routes/demo_sites.py:294`) | `to_served_mobile(phone, country=prospect.country)` ; CA = `None` = « inconnu », donc pas de SMS | en cours / cosmétique |
| `api/services/campaign_queue_service.py:703-705` / `:720` | `_enqueue_sms` juge un prospect non-FR joignable si son numéro ressemble à un mobile FR (079, 621…), **réserve** le prospect au module SMS (`record_contact`) puis échoue à l'envoi (`:834`) | filtrer à l'enfilement avec `declared(prospect.country).sms_prospecting_open`, avant la réservation | dégrade |
| `api/services/sms_automation_service.py:119-121` / `:376` + `api/services/sms_relance_service.py:168` / `:209` / `:305` | aucun motif « pays fermé » : la ligne est planifiée, affichée dans les prévisions, puis sautée « Échec d'envoi SMS » ; `revive_demo_site` remet la démo en ligne **avant** que la garde refuse | motif « Pays fermé au SMS », filtre `ProspectDB.country.in_(pays ouverts)` | dégrade |
| `api/services/campaign_queue_service.py:518-561` / `:779-783` / `:1482-1514` + `sms_automation_service.py:293-300` + `routes/sms.py:280-287` | créneaux, fenêtre et relances à l'heure de Paris | fuseau du prospect | en cours |
| `api/services/sms/mo.py:16-18` | mots STOP FR/EN seulement (pas « ARRET ») ; en mode lien aucun retour MO | mots par pays ; récupérer les désinscriptions par lien | en cours |
| `api/services/sms/smsmode_provider.py:127` + `sms_config_service.py:13-15` + `api/models/sms_config.py:37` | expéditeur alphanumérique « Dibodev » (règle A2P française), un seul par utilisateur | fait manquant `sms_sender_mode` ; expéditeur numérique pour CA plus tard | cosmétique (BE/LU/CA fermés) |
| `api/services/sms/templates.py:140` / `:143` / `:163-243` | « devis » ×2, « email » ×10 (QC « soumission », « courriel ») | lexique | en cours (modèles francs) |
| `api/seeders/email_template_seeder.py:144` / `:184` / `:196` / `:218-225` | `{prix}` ×3 ; « devis » ×3 ; aucun €, Rennes, SIRET, 36180 ni chèque dans les modèles | `{prix}` par pays, lexique | en cours |
| `web/app/components/ui/SendSmsDrawer.vue:29` / `:58` / `:61` + `web/app/pages/dashboard/settings/sms.vue:8-9` / `:86` + `web/app/components/ui/SmsConversation.vue:65` | « Mobile français (06/07) », « 06 12 34 56 78 », horaires légaux FR | textes par pays ouverts, `dial_code` | cosmétique |
| `web/app/utils/emailVariables.ts:133-141` + `web/app/utils/smsVariables.ts:21` | exemples « 500 € », « 79 € » | exemple par pays (« ≈ 470 CHF ») | cosmétique |
| `api/services/reply_capture_service.py:48` + `api/models/prospect.py:213` | réponses automatiques FR/EN ; exemple `+33123456789` | aucun | non-problème |

## 6. Vente et facturation

| fichier:ligne | ce qui suppose la France | correctif proposé | gravité |
|---|---|---|---|
| `api/services/order_service.py:53` / `:111` | `_FRENCH_ZIP_PATTERN = \b(\d{5})\b` dans `_split_postal_address` (`:96-118`) : « Rue du Rhône 12, 1204 Genève » et « 123, rue Sainte-Catherine Ouest, Montréal (Québec) H3B 1A1 » → aucun match → `zip_code=None` → `missing_billing_fields` exige « le code postal » (`:382`) et la finalisation bloque | `profile.postal_code_pattern` + `city_before_postal` ; pour CA couper sur « (Québec) » | bloquant vente, en cours |
| `api/services/order_service.py:117` / `:97` | `trailing_city` cherchée **après** le CP ; « le dernier groupe de 5 chiffres est le CP » : « 10500, boulevard Henri-Bourassa Est, Montréal (Québec) H1C 1G9 » donne CP « 10500 » et une rue vide | `city_before_postal` + retrait de « (Québec) » ; motif du profil (lettres) | bloquant vente |
| `api/services/order_service.py:327-330` / `:338` / `:404` / `:431` + `api/schemas/order.py:49` / `:66` + `api/services/payment_providers/base.py:34` | le pré-remplissage lit `prospect.address` et `prospect.city` mais **jamais `prospect.country`** ; `country_code = order.billing_country_code or "FR"` partout, défaut `"FR"` dans les schémas | `order.billing_country_code or prospect.country or DEFAULT_COUNTRY_CODE` ; champ obligatoire sans défaut dans les schémas | bloquant vente, en cours |
| `api/models/order.py:37-42` | aucune colonne province | `billing_region` (QC) pour `province_code` Qonto et `state` Stripe | dégrade |
| `api/services/order_service.py:384` | `required["tax_id"] = "le SIREN / SIRET"` dès que le fournisseur est Qonto | `profile.tax_id_label` + `tax_id_required` (CH/BE/LU/CA = facultatif tant que le probe sandbox n'a pas dit le contraire) | bloquant vente |
| `api/services/order_service.py:219` / `:295` / `:567` / `:1261` | commande créée en `currency="eur"` ; `format_amount` (`:121-123`) gère une autre devise | garder EUR encaissé ; afficher `profile.format_price` dans les emails/pages (`:732`) | non-problème (choix EUR) |
| `api/services/payment_providers/base.py:34` / `:36` | `BillingClient.country_code = "FR"`, `tax_id` « SIREN/SIRET » | défaut depuis le prospect | cosmétique |
| `api/services/payment_providers/qonto_provider.py:188` | client Qonto : `"currency": "EUR", "locale": "FR"` en dur. Doc Qonto (vérifiée le 03/10) : la facture **hérite de la devise du client** et refuse une devise différente ; CHF et CAD sont acceptés ; `locale` ∈ fr/en/it/de/es | faits manquants `invoice_currency` (EUR partout si l'on garde l'EUR), `invoice_locale` (FR pour tous les pays visés ; DE pour un Alémanique, EN plus tard) | dégrade |
| `api/services/payment_providers/qonto_provider.py:204` | `tax_identification_number` envoyé seulement s'il est saisi : doc Qonto : « optionnel à la création du client, mais la création de facture peut échouer si le champ manque ou est invalide **selon des règles par pays** ; mettre à jour le client puis réessayer » | le code fait déjà le PATCH-puis-retry (`:179-184`). Reste à savoir si CA/CH déclenchent le 422 : **probe sandbox** (§ 6.4) | à vérifier |
| `api/services/payment_providers/qonto_provider.py:38-39` / `:243-244` | `vat_rate "0"`, `vat_exemption_reason "S293B"` (franchise en base française) pour tout client | par pays du client : FR `S293B` ; BE/LU (B2B intra-UE, client assujetti) = autoliquidation art. 196 directive 2006/112/CE, mention « Autoliquidation », n° TVA intracom du client obligatoire ; CH/CA (prestation de services B2B hors UE) = TVA non applicable, art. 259-1 CGI. Codes Qonto listés sans explication (S293B, S259, S283, S262, S261, S263…) : **à confirmer dans l'interface Qonto** (S259 ≈ art. 259, S283 ≈ art. 283-2 ?) ; fait manquant `vat_exemption_reason` | bloquant vente (mention fausse sur une facture CH/BE/CA) |
| `api/services/payment_providers/qonto_provider.py:205-206` | `vat_number` transmis s'il existe, **jamais exigé** : l'autoliquidation BE/LU n'est légale qu'avec un n° TVA client valide (VIES) ; sans lui, le client est traité comme un particulier et `S293B` reste juste. La règle dépend donc du pays **et** du n° TVA, pas du pays seul | fait manquant `vat_number_required` ; contrôle VIES ; à confirmer avec le comptable : n° TVA intracommunautaire du vendeur et DES (art. 286 ter CGI) | bloquant vente (BE/LU) |
| `api/services/payment_providers/qonto_provider.py:34` | `_PAYMENT_METHODS = ["bank_transfer", "credit_card", "apple_pay"]` : le virement vers un IBAN FR convient à CH/BE/LU (SEPA), pas à un Canadien (SWIFT) ; cartes hors UE via le lien Qonto : à vérifier | retirer le virement pour CA | dégrade |
| `api/services/payment_providers/qonto_provider.py:228-233` | `status: "unpaid"` (finalisée) directement : un numéro consommé à chaque essai | aucun en prod ; le probe utilise `draft` | non-problème |
| `api/services/payment_providers/stripe_provider.py:37` / `:90-95` / `:107-113` / `:167-177` | `_BANK_TRANSFER_COUNTRY = "FR"` (« every target is French ») ; un client retrouvé par email est réutilisé **sans mise à jour** du pays ni de l'adresse ; `Customer.create` sans `preferred_locales`, `tax_id_data`, `tax_exempt` ; facture sans `footer` (mention TVA) ni `automatic_tax` | `stripe.Customer.modify` comme Qonto ; `preferred_locales=[invoice_locale]` ; BE/LU `tax_exempt="reverse"` + `tax_id_data` ; mention TVA dans `footer` ; pas de virement pour CA | dégrade |
| `api/services/payment_providers/stripe_provider.py:166` / `:187` + `api/services/stripe_payment_service.py:112` / `:116` / `:141` | devise `eur`, `payment_method_types=["card"]`, `automatic_tax` désactivé, pas de `locale` | un Canadien paie en EUR avec le change de sa banque : le dire ; rien côté taxes | non-problème (à dire au client) |
| `web/app/components/ui/FinalizeSaleDrawer.vue:310` / `:368` / `:388` | `country_code: 'FR'` en dur (3 fois) | sélecteur de pays préréglé sur `prospect.country` | bloquant vente, en cours |
| `web/app/components/ui/FinalizeSaleDrawer.vue:74` / `:327` / `:341` | label « SIREN / SIRET (facultatif) », commentaire « Qonto rejects an invoice whose client carries no TIN », `isTaxIdRequired` → « le SIREN / SIRET » manquant | `profile.tax_id_label`, `tax_id_required` ; champ libre hors FR | bloquant vente, en cours |
| `web/app/components/ui/FinalizeSaleDrawer.vue:84` | « Montant (€) » | `profile.currency` ou « Montant (€, encaissé en euros) » | cosmétique |
| `web/app/components/ui/FinalizeSaleDrawer.vue:141-144` / `:154` / `:440` / `:454-464` | code postal libre, `UiCityAutocompleteInput` placeholder « Rennes » (geo.api.gouv), pré-remplissage registre `recherche-entreprises.api.gouv.fr`, suggestions BAN | saisie libre hors FR, pas de lookup | bloquant vente, en cours |
| `web/app/components/ui/PostalCodeAutocompleteInput.vue:144` / `:7` + `FinalizeSaleDrawer.vue:143` / `:145` | `rawValue.replace(/\D/g, '').slice(0, 5)` : **« H3B 1A1 » devient « 311 »** et c'est ce qui part à Qonto ; `inputmode="numeric"` ; placeholder « 35000 » | hors FR : champ texte validé par `postal_code_pattern` | bloquant vente (CA) |
| `web/app/components/ui/TaxIdLookupInput.vue:129` / `:147` / `:7` | `normalizeTaxIdDigits(rawValue).slice(0, 14)` : **« CHE-123.456.789 » devient « 123456789 », « B123456 » devient « 123456 »**, et c'est envoyé à Qonto ; un IDE qui passe le Luhn déclenche la recherche SIRENE ; clavier numérique | garder le format national hors FR, pas de Luhn ni de lookup | bloquant vente (CH/LU) |
| `web/app/components/ui/FinalizeSaleDrawer.vue:159` / `:165` / `:328` | « N° de TVA (facultatif) », placeholder « FR32123456789 » ; `isTaxIdRequired = provider === 'qonto'` sans le pays | obligatoire pour BE/LU (autoliquidation), masqué pour CH/CA ; `tax_id_required` du profil | bloquant vente (BE/LU) |
| `web/app/utils/taxIdUtils.ts:1-2` / `:44` / `:60` + `web/app/services/companyRegistryLookupService.ts:9` / `:53` / `:104-123` + `web/app/components/ui/TaxIdLookupInput.vue:27` / `:98` / `:106` | 9 ou 14 chiffres, Luhn, lookup SIRENE : un IDE suisse réduit à 9 chiffres peut passer le Luhn et **écraser le formulaire avec une société française** ; un BCE (10 chiffres) est « incomplet » | formats par pays à valider : CHE-123.456.789 ; BE 0123.456.789 ; LU B123456 ; NEQ 10 chiffres (commence par 11/22/33/88, à vérifier) ; lookup réservé à FR | bloquant vente, en cours |
| `api/services/domain/suggestion_service.py:1` / `:65` / `:98` / `:116` | `f"{label}.fr"` seulement | `profile.domain_tlds` (`.ch`, `.be`, `.lu`, `.ca`) | bloquant vente (hors FR), en cours ? (à confirmer avec le ticket Europe) |
| `api/services/domain/availability.py:47-48` | `if response.status_code == 404: return True` : **rdap.org répond 404 pour `google.ch`, `google.be` et `google.lu`** (testé le 03/10 en lecture seule), donc l'outil les affiche « disponible » : faux positif sur tout le domaine `.ch`/`.be`/`.lu` ; `.ca` redirige bien vers `rdap.ca.fury.ca` (testé) | un 404 servi par rdap.org lui-même (sans redirection) doit donner `None` ; ou demander la disponibilité au panier OVH | dégrade (fort : un domaine pris proposé au client) |
| `api/services/domain/ovh_catalog.py:73` / `:78` + `api/core/config.py:295-298` | catalogue public OVH (filiale FR, prix HT) **testé** : `.ch` 9,99 €, `.be` 6,99 €, `.lu` 16,39 €, `.ca` 8,99 €, `.quebec` 24,99 € ; repli `.fr` seulement | aucun pour le prix ; `OrderDrawer.vue:227` (« ~6 € ») est faux pour `.lu` (≈ 19,67 € TTC) et `.quebec` (≈ 30 € TTC) | non-problème / cosmétique |
| `api/services/domain/ovh_provider.py:1` / `:35` / `:168-175` / `:180-182` + `api/core/config.py:313-316` | « buy a `.fr` » ; `OWNER_CONTACT`/`ADMIN`/`TECH` = `/me` du compte OVH du vendeur ; une configuration exigée par le TLD et non fournie est ignorée avec un avertissement (la commande échoue ensuite) ; endpoint `eu.api.ovh.com`. Un `.ca` exige la **présence canadienne** du titulaire (CIRA CPR) : un titulaire français ne peut pas l'être, il faudrait enregistrer au nom du client (contact owner distinct) ou proposer `.com` | décision produit (§ Questions) ; fait manquant `registrant_must_be_local` ; vérifier chez OVH si `.ca` passe par `ovh-eu` avec un titulaire étranger ou s'il faut `ovh-ca`, et les configurations exigées pour `.ch`/`.be`/`.lu`/`.ca` | bloquant vente (CA, si `.ca`) |
| `api/api/v1/routes/domains.py:56` / `:110` / `:134` + `api/services/llm_service.py:469-470` | `f"{cleaned}.fr"` par défaut ; la route ne passe pas `row.country` ; prompt IA « entreprise française, pas de .fr » | `profile.domain_tlds[0]` ; passer le pays au prompt | dégrade |
| `web/app/components/ui/OrderDrawer.vue:144` / `:227` / `:300` / `:525` + `web/app/pages/dashboard/orders/index.vue:164` | placeholder « sonentreprise.fr », « Achat réel (~6 €) », « Montant (€) », `${amount} €` | `domain_tlds[0]`, vrai prix OVH, lire `order.currency` | cosmétique |
| `web/app/services/domainsService.ts:3` / `:31` / `:40` / `:52` / `:80-81` | libellés « .fr », « AFNIC » | textes par `domain_tlds` | cosmétique |
| `api/services/pricing_service.py:50` | prix de vente stocké en EUR par utilisateur, formaté FR | `format_price` par pays pour l'affichage seulement | en cours |

**6.4 Probe Qonto sandbox (TIN pour un client CA puis CH, brouillon, suppression).**

- Contexte : un 422 « tin_number must have a value » a été vu en sandbox le 26/07 pour un client **français** ; la doc Qonto lue le 03/10 (`clients/create-a-client`) dit le TIN optionnel à la création du client mais prévient que la facture peut échouer « selon des règles par pays » ; `client-invoices/create-a-client-invoice` accepte `status: draft` et `delete-a-client-invoice` ne supprime que les brouillons (« les factures validées ou payées ne peuvent pas être supprimées »).
- Ce qui a été vérifié dans le worktree : `api/.env` déclare `QONTO_ENVIRONMENT=sandbox` et un `QONTO_STAGING_TOKEN` (non recopié ici), l'hôte résolu par `settings.qonto_api_base_url` est `https://thirdparty-sandbox.staging.qonto.co`. Mais l'authentification Qonto est **OAuth par utilisateur** (ou clé API `login:secret`), stockée **chiffrée dans la table `payment_accounts`** (`api/models/payment_account.py:59-65`). La base locale (`devleadhunter_db_mariadb`, démarrée puis remise à l'arrêt) a **0 ligne** dans `payment_accounts` ; `.env` n'a aucune clé API. Obtenir un token demanderait un login OAuth dans un navigateur, que je ne fais pas.
- **Résultat : le probe n'a pas tourné.** Le script est prêt et validé en `--dry-run` (annexe A) : il refuse tout hôte hors sandbox, crée un client `kind=company` `country_code=CA` (H3B 1A1, `province_code=QC`) puis `CH` (1204 Genève) **sans TIN**, tente une facture `status: draft` avec le payload exact du provider (`S293B`, EUR), supprime le brouillon puis le client, et imprime statut + corps d'erreur ; options `--with-tin` (NEQ 10 chiffres, IDE CHE) et `--native-currency` (CAD, CHF).
- Pour le lancer (2 minutes) : connecter Qonto sandbox depuis le dashboard local (OAuth) **ou** créer une clé API dans l'app sandbox, puis `cd api && PYTHONPATH=. QONTO_PROBE_ACCESS_TOKEN=… ./.venv/Scripts/python.exe <script>` (ou `QONTO_PROBE_API_LOGIN`/`QONTO_PROBE_API_SECRET`, et `QONTO_PROBE_IBAN` si `GET /organization` est hors scope). Consigner le résultat (422 ou 201 par pays) dans ce document, § 6.4.
- Ce que le résultat changera : 201 pour CA/CH sans TIN → `tax_id_required=False` confirmé pour ces pays, le formulaire peut laisser le champ facultatif ; 422 → demander NEQ / IDE avant la facture (le PATCH-puis-retry du provider s'en charge si le champ est renseigné).

## 7. Module Réceptionniste IA

Constat principal : le module n'utilise **jamais** `CountryProfiles` (aucune occurrence dans `api/services/ai_assistant`, `api/services/assistant_*.py`, `api/api/v1/routes/ai_assistant*.py`). Pour CH, BE et LU rien ne bloque : même heure que Paris, mobiles servis, SMS de service hors de la garde prospection. Pour le Québec, deux blocages : la liste fermée des mobiles d'alerte, et `Europe/Paris` en dur (73 appels à `OpeningHoursCalendar.business_now/business_timezone/to_business_time/localize/to_utc` dans 25 fichiers).

| fichier:ligne | ce qui suppose la France | correctif proposé | gravité |
|---|---|---|---|
| `api/services/sms/phone_normalizer.py:19` / `:95-101` / `:104-123` | `SERVED_MOBILE_PREFIXES = ("+33", "+32", "+352", "+41", "+49")`, `_SERVED_MOBILE_RANGES` en dur, `to_served_mobile` refuse `+1` | lire `dial_code` des pays déclarés ; `mobile_prefixes` (vide pour CA = tout numéro NANP valide, le bouton « SMS test » `ai_assistant_client_space.py:225` sert de vérification) ; `trunk_prefix` (`:89` : un national hors FR est refusé) | bloquant vente (CA) |
| `api/services/ai_assistant/assistant_service.py:148` / `:151-152` + `client_space_service.py:528-530` | numéro d'alerte validé par `to_served_mobile` ; 422 « un mobile de France (06 / 07), Belgique, Luxembourg, Suisse ou Allemagne est requis ». Conséquence CA : `alert_phone_e164` vide, `wants_sms` False (`alert_settings.py:77`), aucun SMS, et les relances J+3/J+14 (`start_reminders.py:32`) réclament un mobile impossible à saisir | même correctif ; message construit depuis les `label` | bloquant vente (CA) |
| `api/services/ai_assistant/assistant_service.py:207-212` | `business_country` = pays du prospect, FR par défaut | bon point d'appui ; utiliser `declared()` | non-problème |
| `api/services/ai_assistant/calendar_booking.py:191` / `:298` / `:335` | mobile du visiteur via `to_served_mobile` (pas de confirmation ni de rappel pour un visiteur CA, ni pour un CH/BE/LU en forme nationale) ; événement Google créé en `Europe/Paris` ; libellés à l'heure de Paris | `mobile_prefixes` ; fuseau de l'assistant | bloquant vente (CA) |
| `api/services/ai_assistant/opening_hours.py:22` / `:25` / `:70-71` | commentaire « Every targeted country keeps Paris time », `ZoneInfo("Europe/Paris")`, méthodes statiques sans l'assistant | colonne `ai_assistants.timezone` (défaut `declared(pays).timezone`), passée à `OpeningHoursCalendar`, exposée au widget et à l'espace client. Le fuseau doit être porté par l'**assistant**, pas seulement le pays (6 fuseaux au Canada ; Îles-de-la-Madeleine et Basse-Côte-Nord hors `America/Toronto`) | bloquant vente (CA) ; non-problème CH/BE/LU |
| `api/services/ai_assistant/request_alerts.py:89` / `:154` / `:174` + `alert_settings.py:19-20` | plage calme 22 h-8 h lue à l'heure de Paris : au Québec un SMS reçu entre 16 h et 2 h est retenu puis part à 2 h du matin ; rappel J+1 au patron idem | fuseau de l'assistant (les heures 22/8 sont bonnes) | bloquant vente (CA) |
| `api/services/ai_assistant/appointment_reminder.py:21-23` + `appointment_notices.py:213-216` + `calendar_slot_grid.py:76` + `appointment_slots.py:79` | rappel J-1 entre 9 h et 20 h Paris (3 h-14 h à Montréal), « la veille », créneaux 9 h-12 h « Paris » | fuseau de l'assistant | bloquant vente (CA) |
| `api/services/ai_assistant/daily_message_cap.py:61` + `unanswered_digest.py:30` + `report_service.py:50` / `:88-89` | remise à zéro à minuit Paris (18 h à Montréal), digest lundi 8 h Paris (2 h), rapport mensuel | fuseau de l'assistant | dégrade / cosmétique |
| `api/services/ai_assistant/knowledge_builder.py:287` + `business_card.py:83` + `request_service.py:136` + `request_email.py:106` + `client_space_payload.py:89` + `api/api/v1/routes/ai_assistant_widget.py:220` | l'IA dit « ouvert/fermé » avec l'heure de Paris ; `is_open_now` de la page publique ; `received_outside_hours` faux ; heures des e-mails et de l'espace client à l'heure de Paris | fuseau de l'assistant | dégrade (CA) |
| `api/services/sms_service.py:403` + `sms_config_service.py:13-15` + `smsmode_provider.py:127` | SMS de service avec expéditeur alphanumérique `config.sender` : refusé au Canada (numéro 10DLC requis) | fait manquant `sms_sender_mode` + un numéro long/sans frais pour CA | bloquant vente (CA) |
| `api/services/sms_service.py:207` | la garde prospection ne s'applique **pas** aux SMS de service (`send_service_message` `:362-409` via `message_delivery.py:58-96`, `request_alerts.py:340-362`, `appointment_notices.py:245-264`) : un artisan suisse reçoit ses alertes | aucun | non-problème |
| `api/services/ai_assistant/chat_contact_capture.py:160` | « 514 555-0199 » tapé dans le chat n'est pas capté (règle « +, 0, ou mobile luxembourgeois ») ; le formulaire, lui, l'accepte (`visitor_contact.py:23-24`, 9 à 11 chiffres) | `trunk_prefix` ; accepter 10 chiffres NANP pour CA | dégrade (CA) |
| `api/services/ai_assistant/photo_vision.py:100-102` | `PRICE_PATTERN` ne connaît que €, eur, chf : « 250 $ » passe le filtre et peut s'afficher au visiteur | ajouter `$` et `profile.currency` | dégrade (CA) |
| `api/services/assistant_pricing_service.py:20` / `:78-80` + `api/models/user.py:69` + `api/migrations/add_user_assistant_pricing.py:45` | défaut du code **79 €** (7900), colonne créée avec **2900** par la migration : deux défauts incohérents ; `format_price` toujours FR | trancher 29/79 ; `declared(pays).format_price` | non-problème (prix) / dégrade (format) |
| `api/services/assistant_subscription_service.py:124` / `:138` + `api/api/v1/routes/ai_assistant_widget.py:206` + `client_space_payload.py:310` | Checkout Stripe `"eur"` sans `automatic_tax`, `tax_id_collection` ni `locale` ; prix affiché formaté FR | garder EUR, afficher « 29 € (≈ 50 $ CA) » via `format_price` ; plus tard Adaptive Pricing | non-problème (à dire au client) |
| `api/services/ai_assistant/config_builder.py:25-30` | `_LANGUAGES_BY_COUNTRY` sans CA → repli `["fr", "en"]` | convient au Québec | non-problème |
| `api/services/ai_assistant/alert_sms.py:23` / `:30` + `request_email.py:67` + `trade_openings.py:48` + `knowledge_builder.py:177` | « demande de devis », « e-mail » | `lexicon` (ligne de vocabulaire dans `render_system_prompt`, fonction sur les libellés API) | cosmétique |
| `api/services/ai_assistant/chat_service.py:45-48` | `_FALLBACK_REPLY` français seulement | table par langue comme `CAPPED_REPLIES` | cosmétique |
| `api/services/ai_assistant/masculine_first_names.py:1` | 141 prénoms FR/BE/LU/CH ; sert au genre de la réceptionniste (un artisan qui la renomme « Réjean » obtient des accords féminins) | ajouter réjean, réal, ghislain, normand, yvon, william, jacob | cosmétique |
| `api/services/ai_assistant/client_space_example.py:98` / `:214` / `:231` + `demo_space_examples.py:94` / `:373` + `demo-host/app/utils/AssistantDemoScenarioUtils.ts:185` / `:35` / `:278` | exemples « 06 12 34 56 78 », `+33612345678`, « 79 €/mois », 25 numéros « 06 39 98 … », « 600 € », « 8 000 € » montrés au prospect | exemples par pays (CA : 514 555-01xx, numéros fictifs réservés) | dégrade (démo CA/CH) |
| `demo-host/app/utils/AssistantScheduleUtils.ts:4-5` | `BUSINESS_TIME_ZONE = 'Europe/Paris'` | l'API envoie `timezone` dans la config publique | bloquant vente (CA) |
| `demo-host/app/constants/AssistantWidgetLabels.ts:81` / `:268-269` / `:331` / `:460` + `ClientSpaceRequestUtils.ts:7` / `:14` + `ClientSpaceRequestTypes.ts:5` | « devis », « E-mail », `fr: 'fr-FR'` | surcharge `fr-CA` à partir d'un champ `country` envoyé par l'API | cosmétique |
| `demo-host/app/components/AssistantBusinessPage.vue:42-45` / `:107` / `:110` | pied de page = une phrase sur l'assistant : **aucune mention légale ni politique de confidentialité** sur `/ia/{slug}`, `/client/`, `/embed/`, widget ; conversations gardées 90 jours (`conversation_service.py:20`) sans le dire ; `toLocaleString('fr-FR')` | pied légal par pays (RGPD FR/BE/LU, Loi 25 QC : consentement, responsable, transfert hors Québec vers les fournisseurs d'IA ; nLPD CH) ; à valider par un juriste | dégrade (risque légal) |
| `demo-host/app/components/ClientSpaceSettings.vue:53` + `web/app/components/ai-assistants/AssistantSettingsForm.vue:98` | placeholder « 06 12 34 56 78 ou +352 621 123 456 » | `dial_code` | cosmétique |
| `demo-host/public/ai-assistant.js:240` | `aria-label 'Fermer'` | traduire | cosmétique |
| `api/services/ai_assistant/appointment_texts.py:339` | `PRODID:-//Dibodev//Receptionniste//FR` | invisible | non-problème |

Non vérifié : couverture et prix smsmode vers CA/CH/BE/LU ; `tzdata` absent de `requirements.txt` (sans effet sur Linux, tout passerait en UTC sur une image minimale) ; réglages Stripe côté tableau de bord (Adaptive Pricing, Stripe Tax) ; statut TVA du vendeur pour une vente B2B en CH/CA ; prix réel en prod (29 ou 79).

## 8. Tableau de bord et exports

| fichier:ligne | ce qui suppose la France | correctif proposé | gravité |
|---|---|---|---|
| `web/app/utils/prospectCountries.ts:18-23` + `web/app/types/index.ts:22` + `web/app/components/ui/UiCountryFlag.vue:11-30` | catalogue `FR/CH/BE/LU` en dur (drapeaux emoji dans le catalogue, SVG inline dans `UiCountryFlag` pour 4 pays : un `CA` n'aurait **aucun drapeau**) ; double source avec l'API | `/countries` (en cours) + SVG CA | bloquant (CA), en cours |
| `web/app/utils/prospectJson.ts:7` / `:50` / `:312` / `:80` | **l'export réellement branché sur le bouton « Exporter » est ce JSON, et ni l'export ni l'import ne portent `country`** : tout prospect importé devient `FR` (défaut `api/models/prospect.py:34`), et un « 079… » suisse importé serait ensuite lu comme un mobile français par l'envoi SMS ; modèle d'import 100 % français (« 04 72 00 00 00 », « 69003 ») | exporter et lire `country` (code vérifié contre le catalogue, refuser un pays fermé) | bloquant vente |
| `api/api/v1/routes/prospects.py:220` + `web/app/pages/dashboard/my-prospects/index.vue:129` / `:553` + `api/api/v1/routes/dashboard.py:51` + `web/app/components/ui/CampaignProspectsPickerDrawer.vue:236` / `:264` + `web/app/pages/dashboard/emails/index.vue:98` / `:102` + `api/api/v1/routes/exports.py:32` | **aucun filtre Pays nulle part** : liste des prospects (filtres site, ville via `UiCitySelect` geo.api.gouv, catégorie, température, email), stats de l'accueil, **sélection des destinataires d'une campagne** (une campagne n'a qu'un modèle : mélanger FR et CA casse le lexique et le prix), Suivi des e-mails, exports. Seule la carte de couverture découpe par pays | filtre `country` API + front, lu du catalogue ; `aggregate_email_log_counts` (`email_log_stats.py:97`) accepte déjà des filtres | dégrade |
| `api/services/export_service.py:30-41` / `:52` / `:89` / `:98` / `:26` / `:59` | export CSV (**non appelé par le front**) : colonnes `ID, Nom, Email, Téléphone, Adresse, Ville, Catégorie, Source, Site Web, Confiance, Date de création`, **pas de pays, pas de CP**, téléphone brut, séparateur `,` sans BOM, date UTC non dite | ajouter `Pays`, téléphone E.164 | dégrade |
| `api/services/email_health_service.py:40` + `web/app/pages/dashboard/email-health.vue:115` | `_PROVIDER_FAMILIES` centré France (commentaire `:38`) : bluewin.ch, skynet.be, telenet.be, pt.lu, videotron.ca, sympatico.ca, bell.net tombent dans « Autres », le détecteur de filtrage silencieux ne les voit pas ; texte « Orange, Free ou SFR » | fait manquant `mailbox_provider_domains` | dégrade |
| `api/services/prospect_service.py:181` / `:323` + `api/services/behavior_service.py:428` + `web/app/pages/dashboard/index.vue:115` + `web/app/components/ui/CampaignForecast.vue:612` / `:616` | badge STOP via `to_e164_fr` ; journal « Prospect créé · ville » et prospects chauds et prévision sans pays ni drapeau | `to_e164_mobile(raw, country)` ; `country` dans `HotLeadResponse` et `api/schemas/campaign.py:261` | cosmétique |
| `api/services/sms_service.py:123-124` / `:139` | détail du journal : « fenêtre légale (lun–ven 8h–20h, sam 10h–19h…) », « Prochain créneau » à l'heure de Paris | textes par `sms_window` et `timezone` | cosmétique |
| `api/schemas/dashboard.py:65` / `:83` | `country: str = "FR"` | aucun | non-problème |
| `api/services/activity_log_service.py` | aucun libellé France-only (ni 36180, ni SIRENE) | aucun | non-problème |
| `api/services/notification_service.py:1018` | symboles `{"eur": "€", "usd": "$", "gbp": "£"}` : pas de CHF ni CAD | lire `profile.price_format` | cosmétique |
| `api/core/config.py:396-400` + `web/app/components/ui/CampaignForecast.vue` + `web/app/pages/dashboard/sms/index.vue:56` + `web/app/components/ui/SmsLogDrawer.vue:85` | coût SMS estimé à un seul tarif (0,061) | `sms_segment_price_eur` par pays ; l'affichage en euros est juste (smsmode facture en EUR) | cosmétique |
| `fr-FR` (31 fichiers : `EmailHealthTrendChart.vue` ×6, `dashboard/index.vue` ×4, `credits.vue` ×4, `email-health.vue` ×3, `EmailHealthVolumeChart.vue` ×3, `campaigns/index.vue`, `buy-credits.vue`, `accounting.vue` ×2, `utils/date.ts`, `CampaignForecast.vue:445`, `SmsLogDrawer.vue`, `ProspectBehavior.vue`…) | formats de date/nombre pour l'utilisateur (français) : fuseau du navigateur via `parseApiDate` | aucun tant que l'utilisateur est francophone ; un jour `user.locale` | non-problème |
| `web/app/pages/dashboard/emails/` (Suivi des e-mails) | heure d'envoi affichée en heure locale de l'utilisateur : pour un Québécois 14 h Paris = 8 h chez lui | colonne « heure locale du prospect » lue de `profile.timezone` | cosmétique |
| `web/app/pages/dashboard/accounting.vue` (`€` ×13, `fr-FR` ×2) + `api/services/accounting_service.py` | comptabilité de l'utilisateur en EUR | aucun (il encaisse en EUR) | non-problème |

## 9. Tests témoins : un parcours par pays

**Ce qui existe** : `api/tests/test_country_profiles.py` (7 tests : repli FR, `enabled`, fuseaux réels, prix euro exact, prix converti arrondi, règles SMS), `api/tests/test_country_support.py` (`normalize_country`, `country_label`, chaîne de failover avec/sans Pages Jaunes, suffixe de requête Maps), `test_qonto_provider.py` (payload client FR, facture EUR, `S293B`), `test_order_invoice.py`, `test_sms_prospect_send.py` (garde non-FR), `test_email_variables.py`, `test_site_content_storyblok.py`, `test_facebook_enrichment*.py`, `test_domain_suggestion.py`, `test_assistant_abuse_guards.py:157-167` (mobile d'alerte étranger refusé). Fixture `db` = SQLite en mémoire (`conftest.py:30-40`). Aucun test ne traverse un pays de bout en bout.

**Squelette proposé** : `api/tests/test_country_journey.py`, paramétré `@pytest.mark.parametrize("country", ["FR", "CH", "BE", "CA"])` avec une fixture `journey_prospect(country)` (nom, adresse locale, téléphone national, ville, email) et les attendus par pays dans un dict (`expected_city`, `expected_zip`, `expected_e164`, `sms_open`, `tax_id_required`, `tld`, `price_label`) :

1. **Recherche** : `GoogleScraper.build_query(cat, city, country)` contient `search_suffix` ; `GoogleScraper.extract_city(address, country)` == `expected_city` ; `ScraperService._ordered_candidates(…, country)` exclut Pages Jaunes hors FR ; `brightdata_client` construit `gl=`/`cc=` du pays ; `email_scraper.find_email(…, country)` passe `gl`.
2. **Enrichissement** : `_parse_city_postal(text, country)` → (ville, CP) ; `_parse_phone(text, country)` == `expected_e164` ; décisionnaire : hors FR, seules les stratégies autorisées tournent, `greeting` neutre.
3. **Site** : `build_content_json(…, country)` renvoie `country`, `locale`, un bloc `legal`, aucun « € », « décennale », « NF C » ; pour CA aucun « devis » hors citations, « Nous joindre ».
4. **Email** : `EmailVariables.build_for_prospect(prospect)["prix"] == CountryProfiles.declared(country).format_price(50000)` ; le pied contient l'adresse postale si `email_footer_needs_postal_address` (CA) ; en-têtes RFC 8058 présents.
5. **SMS** : `send_to_prospect` : accepté FR/CH, refusé BE/CA avec le motif « pays fermé » ; `send_manual("079 123 45 67", prospect_id=CH)` ne part **jamais** en `+337…` ; mention STOP = code court FR, lien CH ; `estimate_price_cents(segments, country)` ; `compose` sans « ≈ » en GSM-7.
6. **Vente** : `_split_postal_address(address, city, country)` → `expected_zip` ; `missing_billing_fields` demande le TIN seulement si `tax_id_required` ; `QontoPaymentProvider._client_body` → `country_code`, `currency`, `locale`, et `create_invoice` → `vat_exemption_reason` du pays ; `suggestion_service.suggest(prospect)` finit par `tld`.
7. **Facture sandbox** : `@pytest.mark.sandbox`, sauté sans `QONTO_PROBE_ACCESS_TOKEN` ; client + brouillon + suppression (annexe A).

**Ce qui manque pour l'écrire** : les paramètres `country` sur `extract_city`, `_parse_*`, `build_content_json`, `_split_postal_address`, `send_manual`, `format_price` (tous absents aujourd'hui) ; `CountryProfiles.declared` utilisé partout à la place de `get` ; CA ouvert ou une fixture qui force `enabled=True` ; une décision sur `phonenumbers` (sinon les attendus téléphone restent ceux du normaliseur maison) ; un bloc `legal` et un `search_suffix` dans le profil ; une ligne `payment_accounts` sandbox pour l'étape 7.

## Vu en passant, hors sujet pays (à ne pas perdre)

- `web/app/components/dashboard/CoverageMap.vue:524` : chemin absolu `C:/Users/leogu/Desktop/Projects/devleadhunter/web/node_modules/...` dans un `typeof import(...)` : casse le typage dans tout autre worktree.
- `web/app/components/ui/FinalizeSaleDrawer.vue:371` : le montant est arrondi à l'euro (499,90 € devient 500 €).
- Plusieurs écrans font `new Date(...)` sur une date de l'API au lieu de `parseApiDate` (`ProspectBehavior.vue:198`, `search-prospects.vue:223`, `credits.vue:406/434/584`, `support/index.vue:183`, `settings/sms.vue:250`) : décalage possible de 1 à 2 h, à vérifier valeur par valeur.
- `api/services/templates/template_repos.py:18` : versions de layers (v1.2.2…) différentes de `demo-host/nuxt.config.ts` (v1.3.1…) : l'export du code d'un site figerait d'anciennes versions.
- `docs/EUROPE_AUDIT.md` classe encore la copie plombier partagée « à faire » alors qu'elle est neutralisée (§ D).

## Ordre de livraison proposé

1. **Avant toute recherche ou import hors France depuis l'app** : refuser un pays fermé à la création du job (`country.py:27`, `scraping_job_service.py:51`) ; règle `declared()` ; `country` dans l'export/import JSON (`prospectJson.ts:312`) ; `extract_city` par pays (`google_scraper.py:268`) ; `osm_enrichment.py:204` ; `email_scraper.py:385/127` ; garde pays sur `send_manual` (`sms_service.py:335`) et `_enqueue_sms`. Puis une vraie recherche suisse depuis l'app desktop (jamais validée en live).
2. **Avant la première vente CH/CA** (dette Europe + Québec, en cours) : `_split_postal_address` par profil (ville avant CP), `PostalCodeAutocompleteInput` et `TaxIdLookupInput` qui ne mutilent plus la saisie hors FR, `FinalizeSaleDrawer` (pays depuis le prospect, label TIN, TVA obligatoire BE/LU), Qonto `locale`/`vat_exemption_reason` par pays + `vat_number_required`, **probe sandbox**, RDAP sans faux positif, `domain_tlds`, décision `.ca`/`.com` et titulaire OVH.
3. **Avant un Réceptionniste québécois** : `ai_assistants.timezone` + `OpeningHoursCalendar` paramétré, `mobile_prefixes`/`trunk_prefix` (+1), expéditeur SMS numérique, pied légal des pages publiques, `AssistantScheduleUtils` lit le fuseau.
4. **Qualité du sourcing et des sites** : regex CP/téléphone par profil (FB, enrichment, address), blocklists CH/BE/LU/CA, `validation_service.py:53`, Overpass par pays, pays dans `build_content_json` + lexique par expressions + bloc `legal`, `plumber_atelier.py:142-143`, régénérer `previewLayers.json`, retirer « à Rennes » du script, filtre Pays + export CSV.
5. **Carte** : `regions-ca.geojson` (17 régions du Québec), cadrage par pays, `REGION_LABELS.CA`, noms belges en français.
6. **Plus tard** : `language` (anglophones : `hl`, salutation, widget, prompts), décisionnaire Zefix (compte à demander), `holidays`/`phonenumbers`.

## Questions ouvertes

Tranché le 03/10 :

- **Facturation CH/CA** : en euros. Les mails annoncent le prix local avec « ≈ » (« ≈ 470 CHF »), comme pour la Suisse.
- **Domaine d'un client québécois** : un `.com` s'achète comme un `.fr`, au nom de l'opérateur. Un `.ca` exige un titulaire présent au Canada (règle CIRA), il se prend donc au nom du client.
- **Adresse postale CASL** : dans « Mon profil » (`users.postal_address`), remplie en prod.
- **Pied légal des sites** : un bloc `legal` commun et, pour le Québec, une politique de confidentialité (Loi 25), ajoutés à la première vente hors de France.
- **Script vidéo** : « à Rennes » gardé pour tous les marchés.

Encore ouverts :

1. **Mention TVA** : faire confirmer par le comptable l'autoliquidation (BE/LU avec n° TVA client valide VIES ; sans n° TVA le client reste traité comme un particulier et `S293B` s'applique), la non-application (CH/CA), l'obligation pour le vendeur d'avoir un n° TVA intracommunautaire et de déposer une DES pour les ventes BE/LU. Les codes Qonto (`S293B`, `S283`, `S259`) sont dans les profils pays.
2. **Probe sandbox** : reconnecter Qonto sandbox en local (OAuth) ou créer une clé API sandbox pour lancer le script de l'annexe A.
3. **Prix du Réceptionniste** affiché à un Québécois qui paiera en euros (module réceptionniste).
4. Choix techniques, tranchés au moment du chantier : carte du Québec (17 régions administratives), décisionnaire hors France (les 3 stratégies sans registre avec une salutation neutre par défaut, compte Zefix pour la Suisse), bibliothèques `phonenumbers` et `holidays` ou normaliseur maison étendu par profil.

## Annexe A : probe Qonto sandbox (prêt, non lancé)

Script validé en `--dry-run` le 03/10 depuis `api/` (hôte résolu `thirdparty-sandbox.staging.qonto.co`). À lancer avec `cwd = api/` et `PYTHONPATH=.` ; identifiants attendus en variables d'environnement, jamais dans le dépôt.

```python
"""Probe Qonto SANDBOX : un client étranger (CA puis CH) sans TIN peut-il être facturé ?

cd api
PYTHONPATH=. QONTO_PROBE_ACCESS_TOKEN=<token OAuth sandbox> ./.venv/Scripts/python.exe qonto_sandbox_tin_probe.py
# ou : QONTO_PROBE_API_LOGIN=<slug-org> QONTO_PROBE_API_SECRET=<clé>
# options : --with-tin (NEQ / IDE), --native-currency (CAD / CHF), --dry-run (payloads seulement)
Garde-fous : refuse hors sandbox ; factures « draft » seulement ; supprime brouillon puis client.
"""

from __future__ import annotations

import argparse, asyncio, json, os, sys
from datetime import UTC, datetime, timedelta

import httpx

from core.config import settings

_CASES: dict[str, dict[str, str]] = {
    "CA": {"street_address": "123 rue Sainte-Catherine Ouest", "city": "Montréal", "zip_code": "H3B 1A1",
           "province_code": "QC", "tin_example": "1234567890", "native_currency": "CAD"},
    "CH": {"street_address": "Rue du Rhône 12", "city": "Genève", "zip_code": "1204",
           "tin_example": "CHE-123.456.789", "native_currency": "CHF"},
}


def _headers() -> dict[str, str]:
    token = os.environ.get("QONTO_PROBE_ACCESS_TOKEN", "").strip()
    login = os.environ.get("QONTO_PROBE_API_LOGIN", "").strip()
    secret = os.environ.get("QONTO_PROBE_API_SECRET", "").strip()
    if token:
        authorization = f"Bearer {token}"
    elif login and secret:
        authorization = f"{login}:{secret}"
    else:
        raise SystemExit("Exporter QONTO_PROBE_ACCESS_TOKEN ou QONTO_PROBE_API_LOGIN + QONTO_PROBE_API_SECRET.")
    return {"Authorization": authorization, "X-Qonto-Staging-Token": settings.qonto_staging_token}


def _assert_sandbox() -> None:
    if not settings.qonto_is_sandbox or "sandbox" not in settings.qonto_api_base_url or not settings.qonto_staging_token:
        raise SystemExit(f"Refus : environnement '{settings.qonto_environment}', hôte '{settings.qonto_api_base_url}'.")


def _client_body(country: str, *, currency: str, with_tin: bool, stamp: str) -> dict:
    case = _CASES[country]
    body: dict = {
        "kind": "company", "name": f"Probe multi-pays {country} {stamp}", "currency": currency, "locale": "FR",
        "email": f"probe-{country.lower()}-{stamp}@example.com",
        "billing_address": {"street_address": case["street_address"], "city": case["city"],
                            "zip_code": case["zip_code"], "country_code": country},
    }
    if "province_code" in case:
        body["billing_address"]["province_code"] = case["province_code"]
    if with_tin:
        body["tax_identification_number"] = case["tin_example"]
    return body


def _invoice_body(client_id: str, *, currency: str, iban: str) -> dict:
    today = datetime.now(UTC).date()
    return {
        "client_id": client_id, "issue_date": today.isoformat(),
        "due_date": (today + timedelta(days=30)).isoformat(), "currency": currency, "status": "draft",
        "payment_methods": {"iban": iban},
        "items": [{"title": "Probe site web (brouillon, à supprimer)", "description": "Probe multi-pays, jamais finalisé",
                   "quantity": "1", "unit": "unit", "unit_price": {"value": "500.00", "currency": currency},
                   "vat_rate": "0", "vat_exemption_reason": "S293B"}],
    }


async def _call(client: httpx.AsyncClient, method: str, path: str, **kwargs) -> tuple[int, dict | str]:
    response = await client.request(method, f"{settings.qonto_api_base_url}/v2{path}", headers=_headers(), timeout=30.0, **kwargs)
    try:
        return response.status_code, response.json()
    except ValueError:
        return response.status_code, response.text


async def _resolve_iban(client: httpx.AsyncClient) -> str:
    iban = os.environ.get("QONTO_PROBE_IBAN", "").strip()
    if iban:
        return iban
    status, body = await _call(client, "GET", "/organization")
    accounts = ((body.get("organization") or {}).get("bank_accounts") or []) if isinstance(body, dict) else []
    if status != 200 or not accounts or not accounts[0].get("iban"):
        raise SystemExit(f"IBAN introuvable (GET /organization -> {status}) : exporter QONTO_PROBE_IBAN.")
    return accounts[0]["iban"]


async def _run_case(client: httpx.AsyncClient, country: str, *, currency: str, with_tin: bool, iban: str, stamp: str) -> dict:
    report: dict = {"country": country, "currency": currency, "with_tin": with_tin}
    status, body = await _call(client, "POST", "/clients", json=_client_body(country, currency=currency, with_tin=with_tin, stamp=stamp))
    report["client_create"] = {"status": status, "body": body if status >= 400 else "ok"}
    if status not in (200, 201) or not isinstance(body, dict):
        return report
    client_id = body["client"]["id"]
    status, body = await _call(client, "POST", "/client_invoices", json=_invoice_body(client_id, currency=currency, iban=iban))
    report["draft_invoice_create"] = {"status": status, "body": body if status >= 400 else "ok"}
    if status in (200, 201) and isinstance(body, dict):
        invoice = body["client_invoice"]
        if invoice.get("status") != "draft":
            report["WARNING"] = "facture non brouillon : ne pas rejouer sans comprendre"
        status, _ = await _call(client, "DELETE", f"/client_invoices/{invoice['id']}")
        report["draft_invoice_delete"] = status
    status, _ = await _call(client, "DELETE", f"/clients/{client_id}")
    report["client_delete"] = status
    return report


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-tin", action="store_true")
    parser.add_argument("--native-currency", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    _assert_sandbox()
    stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    variants: list[tuple[str, str, bool]] = []
    for country in _CASES:
        variants.append((country, "EUR", False))
        if args.with_tin:
            variants.append((country, "EUR", True))
        if args.native_currency:
            variants.append((country, _CASES[country]["native_currency"], False))
    if args.dry_run:
        print(f"base_url={settings.qonto_api_base_url}")
        for country, currency, with_tin in variants:
            print(json.dumps(_client_body(country, currency=currency, with_tin=with_tin, stamp=stamp), ensure_ascii=False, indent=2))
            print(json.dumps(_invoice_body("<client_id>", currency=currency, iban="<iban sandbox>"), ensure_ascii=False, indent=2))
        return
    async with httpx.AsyncClient() as client:
        iban = await _resolve_iban(client)
        reports = [await _run_case(client, c, currency=cur, with_tin=tin, iban=iban, stamp=stamp) for c, cur, tin in variants]
    print(json.dumps(reports, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
```

Résultat attendu à consigner ici : pour chaque variante, `client_create.status` (201 attendu), `draft_invoice_create.status` (201 = le TIN n'est pas exigé pour ce pays ; 422 = corps d'erreur à copier), `draft_invoice_delete` (204), `client_delete` (204).
