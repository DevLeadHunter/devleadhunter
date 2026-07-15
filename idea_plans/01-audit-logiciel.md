# Audit DevLeadHunter — tour complet du logiciel & du tunnel

> **Date** : 2026-07-11
> **Périmètre** : le monorepo (`api/` FastAPI + MySQL, `web/` Nuxt 4 + Tauri, `demo-host/` Nuxt), les repos templates (Nuxt layers) et le contrat de contenu partagé.
> **Méthode** : lecture du code réel (deux passes d'audit ciblées + connaissance de la session en cours). Chaque constat est ancré dans un fichier ; les points marqués *à vérifier* dépendent de l'état du serveur, pas seulement du code.
> **Ton** : volontairement critique et actionnable. Le but est un audit utile, pas flatteur.
>
> **📋 Journal des corrections** (document vivant — on coche à mesure qu'on dépile) :
> - **2026-07-11** — ✅ #1 Secrets de déploiement injectés (7 vars) + ✅ #2 token BrightData révoqué & fichiers purgés (commit `3b8db54`). PageSpeed vérifié fonctionnel.
> - **2026-07-11** — ✅ #3 `updateProfile` branché sur `PATCH /auth/me` (persiste réellement) + ✅ #8 unsubscribe signé (token HMAC, XSS échappée) + ✅ #9 health check réel (probe DB, 503 si KO). Vérifiés en live.
> - **2026-07-11** — ✅ #6 fulfilment robuste (loop de reprise + cap + `fulfillment_attempts`/`last_error`) + ✅ #4 migrations jouées au déploiement (`run_migrations.py` avant les seeders). Migration idempotente jouée en local, reprise testée E2E. Déploiement prod OK (migrations « adoptent » le schéma existant sans casse). **Effet de bord découvert** : les seeders de démo (10 faux users + transactions) tournaient à chaque deploy → ✅ **gatés hors production** (`settings.is_production`).
> - **2026-07-11** — ✅ **Résilience scraping (Étape 1)** : fallbacks sélecteur/regex/JSON-LD (Google + Pages Jaunes, 10 tests), failover inter-sources, capture réactive typée + page admin de monitoring. Correction du constat erroné sur `SCRAPER_BROWSER_HEADLESS` (headless=false volontaire, scraping sur IP résidentielle de l'utilisateur, pas un VPS).
> - **2026-07-11** — ✅ **Fiabilisation enrichissement (Étape 2)** : source complémentaire **OpenStreetMap** (horaires ~60 % + social + email/site), fallback **JSON-LD** (description/note/avis), `social_links` branché, échec non silencieux (diagnostic « enrichment » → monitoring). Vérifié en live.
> - **2026-07-11** — ✅ **Storyblok éprouvé & fiabilisé (Étape 3)** : cycle complet testé en live (2 bugs prod corrigés — provisioning du template par défaut + re-fetch CDN 301), re-sync des composants (upsert PUT + endpoints admin), provisioning parallélisé (~4 s). Rendu social visible sur les 5 templates au passage.
> - **2026-07-11** — ✅ **Mailjet supprimé** (mort — Léo = Resend) : service + settings retirés, custom-domain reroutée vers Resend, et la vérif DNS custom-domain passe du **placeholder factice Mailjet** à de **vrais lookups SPF/DKIM** (`dns_service`, dnspython, testé en live). ✅ **Page campagnes** : grille 3 col → **2 col sous `2xl`** (le drawer « Nouvelle campagne » n'écrase plus les cartes) + texte redondant retiré du drawer.
> - **2026-07-13** — ✅ **Funnel A/B email→démo→vente bouclé (Resend→PostHog)** : vérifié via le MCP PostHog que la source data-warehouse Resend est bien connectée & saine (« DevLeadHunter — Resend (prod) », synchro ~6 h, `resend.emails`/`domains`/`audiences` requêtables). **Trou trouvé & corrigé** : le statut passant `SENT` en base synchronement, le webhook `email.sent` arrivait au même rang → l'event **`email_sent` n'était jamais capté**. Émis désormais **à la source** (`email_sending_service`, les 2 chemins) avec `distinct_id = slug de la démo` (= identité des events démo) → parcours complet `email_sent → delivered → opened → clicked → $pageview (démo) → demo_engaged` résolu sur **une seule personne** (funnel + session replay reliés, découpable par variante A/B). Helper partagé `services/demo_identity.py` (source unique du `distinct_id`) réutilisé par l'envoi et le webhook ; `get_events_for_slug` filtré sur `DEMO_EVENTS` (les events email mirrorés ne polluent plus la timeline in-app, qui source l'email depuis `EmailLog`). Branche `feat/posthog-email-sent-capture`, commit `e1efd48` (compile + smoke + `test_lead_scoring` + lint web verts ; 1er `email_sent` réel visible au prochain envoi).

---

## 1. Résumé exécutif

DevLeadHunter est **remarquable pour un outil bâti seul** : la promesse « trouver → enrichir → générer un vrai site → démarcher → vendre → livrer » est **réellement câblée bout-en-bout dans le code** (ce n'est pas du vaporware — les vrais appels Stripe, Vercel, Storyblok, PostHog sont là), avec un **front d'une qualité produit rare** et une **documentation abondante**.

Le contraste central, qui structure tout cet audit :

> **Discipline front exemplaire** (TypeScript ultra-strict *réellement* tenu — 0 `any` dans `web/app`, lint imposé au commit) **vs back non gouverné** (aucun lint/type/test Python enforced) **et opérations non durcies** (0 test, monitoring factice, secrets fragiles au déploiement, maillons jamais éprouvés en prod).

Autrement dit : **la surface fonctionnelle est large et saine, mais le filet opérationnel est mince.** C'est le profil classique d'un produit riche construit vite et seul. Ce qui reste n'est pas de la reconstruction — c'est du **durcissement** : tests, CI, secrets, observabilité, et la validation live des maillons critiques.

**Verdict global : excellent prototype avancé / outil perso ; pas encore un logiciel durci pour l'échelle ou le multi-utilisateur.**

| Dimension | Verdict |
|---|---|
| Tests | 🔴 Manquant (critique) |
| Robustesse scraping | 🟠 Partiel / fragile |
| Erreurs & observabilité | 🟠 Fragile |
| Sécurité & RGPD | 🔴 Risqué (plusieurs points) |
| Données & migrations | 🟠 Partiel |
| Qualité du code | 🟢 Front solide / 🟠 Back fragile |
| Complétude fonctionnelle | 🟠 Partiel (beaucoup à valider en live) |
| CI/CD & déploiement | 🟠 Partiel / fragile |
| DX & doc | 🟢 Solide (quelques inexactitudes) |
| Frontend / UX | 🟢 Solide (résidus) |

---

## 2. 🚨 À regarder EN PREMIER — les trouvailles concrètes et sévères

Ce ne sont pas des généralités : ce sont des lignes de code précises à traiter en priorité.

1. ✅ **RÉSOLU (2026-07-11)** — **Secrets omis au déploiement de l'API — potentiellement catastrophique.** `.github/workflows/deploy-api.yml` **régénère intégralement `api/.env` à chaque déploiement** via un heredoc, en **omettant** plusieurs secrets présents dans `.env.example` : `ENCRYPTION_KEY`, `RESEND_API_KEY`, `RESEND_WEBHOOK_SECRET`, `BRIGHTDATA_API_TOKEN`, `PAGESPEED_API_KEY`… Conséquences si c'est bien l'état du serveur :
   - **`ENCRYPTION_KEY` absent** → `encryption_service.py` **génère une clé aléatoire à chaque démarrage** (le code le dit : *« This key will be lost when the server restarts! »*). Toute donnée chiffrée (**comptes email, tokens OAuth Gmail**) devient **indéchiffrable après chaque deploy**. → tes comptes d'envoi se « cassent » silencieusement.
   - **`RESEND_API_KEY` absent** → le fournisseur d'email **principal** est HS en prod.
   > **Correctif (commit `3b8db54`)** : le heredoc injecte désormais `ENCRYPTION_KEY`, `RESEND_API_KEY`, `RESEND_WEBHOOK_SECRET`, `BRIGHTDATA_API_TOKEN`, `BRIGHTDATA_ZONE`, `PAGESPEED_API_KEY`, `STORYBLOK_WEBHOOK_SECRET`. Les secrets GitHub Actions correspondants ont été ajoutés (dont une `ENCRYPTION_KEY` Fernet fixe). Un `${{ secrets.X }}` non défini se résout en chaîne vide → aucune régression. **PageSpeed vérifié fonctionnel** (PSI HTTP 200 avec la clé). ⚠️ **Reste à faire au 1er deploy** : re-saisir les comptes email d'envoi (l'ancien chiffré, produit avec les clés aléatoires perdues, est irrécupérable).

2. ✅ **RÉSOLU (2026-07-11)** — **Token BrightData en dur, committé dans git** : `api/test_bedee_comparison.py:22` → `os.environ.setdefault("BRIGHTDATA_API_TOKEN", "8daca9ae-…")`. Le fichier est suivi par git → **le secret est dans l'historique**. → **révoquer le token chez BrightData + purger le fichier** (et l'artefact `response.json` de debug committé à la racine).
   > **Correctif (commit `3b8db54`)** : token **révoqué + régénéré** chez BrightData, `test_bedee_comparison.py` et `response.json` **supprimés**. Le token demeure dans l'**historique** git (commit `77a44b5`) mais est **inoffensif car révoqué** → pas de réécriture d'historique (opération destructive évitée).

3. ✅ **RÉSOLU (2026-07-11)** — **La modification de profil ne persiste pas** : `web/app/stores/user.ts` → `updateProfile` est un **mock** (`await new Promise(setTimeout 800ms)` + localStorage, l'appel API est **commenté** avec `// TODO`). L'utilisateur croit enregistrer son nom/email, **rien n'est sauvé côté serveur**.
   > **Correctif** : endpoint self-service `PATCH /auth/me` (vérif d'unicité email), `authService.updateProfile` + store branchés dessus. Persistance **vérifiée en live** (PATCH → `GET /me` renvoie la nouvelle valeur). ⚠️ Un changement d'**email** invalide le token courant (l'email est le `sub` du JWT) → re-login requis après.

4. ✅ **RÉSOLU (2026-07-11)** — **Endpoint de désinscription non protégé** (`api/api/v1/routes/unsubscribe.py`) :
   - **Aucun token/signature** : `GET /unsubscribe?email=…` → **n'importe qui peut désinscrire n'importe lequel de tes prospects** en devinant l'URL (unsubscribe-bombing).
   - **XSS réfléchie** : l'`email` est injecté **brut** dans le HTML (f-string, l. ~102) sans échappement.
   > **Correctif** : lien signé par **token HMAC-SHA256 par email** (`generate_token`/`verify_token`, clé = `SECRET_KEY`) — un token invalide/absent → **400 + page « lien invalide »** (aucune action) ; email **échappé** (`html.escape`). Vérifié en live (sans token → 400, token valide → OK, `<script>` → `&lt;script&gt;`). Note : les liens des emails **déjà envoyés** (sans token) afficheront la page « lien invalide ».

5. ✅ **RÉSOLU (2026-07-11)** — **Health check factice** : `api/api/v1/routes/health.py` renvoie en dur `{"database":"healthy","scrapers":"healthy"}` **sans jamais tester** la DB ni les scrapers → **inutilisable pour du monitoring/uptime** (ne détectera jamais une panne).
   > **Correctif** : probe réel `SELECT 1` sur la DB → **HTTP 503** si elle tombe (détectable par un moniteur uptime) ; le faux `scrapers: healthy` retiré (jobs à la demande, pas un service persistant). Vérifié en live.

6. ✅ **RÉSOLU (2026-07-11)** — **Fulfilment post-paiement en fire-and-forget** : `payments.py` → `asyncio.create_task(fulfill_order_async(...))` **sans retry ni dead-letter**. Si Vercel/Storyblok échoue **après** l'encaissement, l'`Order` reste `paid` **non livré**, récupération manuelle requise. Un client qui a payé et n'est pas livré, c'est le pire scénario commercial.
   > **Correctif** : **loop de reprise en fond** (`order_fulfillment_recovery_service`, greffé comme le worker email/cleanup) qui rejoue toutes les 10 min les commandes `paid`/`deploying` non livrées — **plafonné** (`MAX_FULFILMENT_ATTEMPTS=8`, fenêtre 14 j) et **traçable** (colonnes `fulfillment_attempts` + `fulfillment_last_error` sur `orders`). Le `POST /orders/{id}/deploy` manuel **réarme** le budget. Reprise testée E2E (détection → tentative → cap → terminal ignoré).

7. ✅ **RÉSOLU (2026-07-11)** — **Migrations non jouées au déploiement** : `deploy-api.yml` lance `init_db.py` (= `create_all` + seeders), qui **ne fait jamais d'`ALTER`**. Toute **nouvelle colonne** sur une table existante n'est **pas appliquée** au deploy → il faut SSH + `run_migrations.py` à la main (documenté mais non automatisé) → **dérive de schéma silencieuse → 500 en prod**.
   > **Correctif** : nouvelle étape `run_migrations.py` **avant** les seeders dans `deploy-api.yml`. Runner **idempotent** (table `schema_migrations` + chaque migration gardée par `INFORMATION_SCHEMA`/`checkfirst`) — j'ai vérifié que **les 19 migrations existantes sont sûres à re-jouer** (le 1er deploy « adopte » proprement le schéma prod appliqué à la main). Les seeders (idempotents) restent inchangés. Runner joué en local (19 skip + 1 appliquée).

---

## 3. Le tunnel, étape par étape

### Étape 1 — Trouver (scraping)
**Bien** : multi-sources (Pages Jaunes, Google, OSM, BrightData) via `nodriver` (Chrome piloté), jobs **asynchrones avec stream live**, déduplication, filtre « sans site web », email récupéré systématiquement. Timeouts partout (pas de hang). Dégradation gracieuse (une extraction partielle rend ce qu'elle a pu). Chaînes de fallback de requêtes. UX de la page « Trouver des prospects » claire.
**À améliorer / risqué** :
- ✅ **RÉSOLU (2026-07-11) — Sélecteurs fragiles** : le scraping DOM casse dès que Google/Pages Jaunes changent leur markup — et **aucun test de non-régression** ne l'attrape. Les classes Google (`div.F7nice`, `.d4r55`, `.wiI7pd`…) sont obfusquées et tournent souvent.
  > **Correctif** : (1) **chaînes de fallback** par champ (sélecteur actuel → alternatives sémantiques `aria`/`data-*` → regex) + **JSON-LD** (schema.org `LocalBusiness`, ancre la plus durable) sur Google + Pages Jaunes (`resilient_extract.py`, 10 tests unitaires) ; (2) **failover automatique entre sources** (`scraper_service` : si une source est bloquée/vide, bascule Google→Pages Jaunes→BrightData→OSM) ; (3) **capture réactive** (statut typé bloqué/vide/timeout + HTML capturé au blocage) et **page admin de monitoring** (`/dashboard/admin/monitoring`) pour voir la santé par source sans sonde proactive.
- **Aucun retry/backoff** dans les scrapers (pas de `tenacity`) : un échec transitoire = échec. *(partiellement atténué par le failover inter-sources ci-dessus ; un retry/backoff intra-source reste à ajouter.)*
- ~~**Footgun de config** : `SCRAPER_BROWSER_HEADLESS=false`~~ ❌ **CONSTAT ERRONÉ (retiré)** : `false` est **volontaire et correct**. Un Chrome headless a une empreinte détectable → bien plus challengé par Cloudflare. Et le scraping **ne tourne pas sur un VPS** mais sur **la machine de l'utilisateur (IP résidentielle)** via le sidecar de l'app desktop — une IP datacenter serait bloquée d'office. Aucun changement requis.
- **Jobs de scraping en mémoire** (`self._jobs`) : perdus au redémarrage de l'API. *(inchangé ; les diagnostics par source, eux, sont désormais persistés en base.)*

### Étape 2 — Enrichir (le point le plus rentable à fiabiliser) — ✅ **FIABILISÉ (2026-07-11)**
**Bien** : séparé du scraping de recherche, à la demande ou en masse (`bulk-run`), injecté automatiquement dans le contenu du site à la génération (`ensure_enriched()` avant provisioning).
**À améliorer / risqué** (état vérifié dans `enrichment_scraper.py`) :
- `rating` + `opening_hours` : **OK**.
- ✅ `description` : ~~**fragile** — retombe sur le méta générique Google~~ → **JSON-LD** (schema.org) en fallback + `description` OSM en complément.
- ✅ `reviews_count` / `reviews` : ~~**fragiles**~~ → `reviews_count` a un fallback **JSON-LD** (`aggregateRating.reviewCount`) ; `reviews` reste best-effort DOM (Google n'expose pas d'avis en JSON-LD sur Maps).
- ✅ `social_links` : ~~**jamais extrait**~~ → **branché** (liens sociaux du panneau Google + `contact:facebook`/`contact:instagram` d'OSM). `services` : **volontairement laissé manuel** — aucune source fiable (ni Google DOM ni OSM ne donnent une liste propre), et les défauts éditoriaux par métier des templates sont meilleurs qu'une extraction faible.
- ✅ Casse **silencieuse** : ~~un `EnrichmentData()` vide passait inaperçu~~ → chaque enrichissement **enregistre un diagnostic** (`source="enrichment"`, statut ok/vide/bloqué/erreur + HTML capturé au blocage) → visible sur la **page admin de monitoring**.
- ✅ **Source complémentaire ajoutée : OpenStreetMap** (Nominatim `extratags`, gratuit, sans blocage, IP-agnostique). Couverture mesurée sur artisans FR : **~60 % ont `opening_hours`** (le point faible de Google), + email/website/phone/social. Fusionné en comblement de trous (Google prioritaire pour photos/avis/note ; OSM pour horaires/social/description). Enrichissement dégradé fonctionne même sans Chrome (OSM seul). **Vérifié en live** (« The Hair Academy », Lyon : vrais horaires + FB/IG + email + site).
- ✅ **Rendu des `social_links` sur les sites** : ~~pas encore de section réseaux sociaux~~ → **branché de bout en bout** — champ `social` ajouté au contrat partagé `SiteContent` (`@devleadhunter/website-content` **v1.3.0**), mappé par l'API (`map_prospect_and_enrichment` + schéma Storyblok + bridges), et **rendu dans le footer des 5 templates** (artisan-edito v1.2.0, plumber-signature v1.2.0, plumber-atelier v1.3.0, plumber-cuivre v1.2.0, electrician-lumen v1.2.0 — chacun à sa propre DA, liens vérifiés en SSR). Bridge demo-host + les 5 pins bumpés (typecheck vert).
- → **la qualité du site démo = ton taux de vente.**

### Étape 3 — Générer le site — ✅ **ÉPROUVÉ & FIABILISÉ (2026-07-11)**
**Bien** : registre propre (un module Python/template), 4 templates en layers séparés, contrat `SiteContent` unique, copie éditoriale **désormais éditable par le client** et pré-remplie, **mock mode** sans token, injection auto de l'enrichissement. Génération unitaire ou en masse.
**À améliorer / risqué** :
- ✅ **Storyblok éprouvé en réel** : ~~jamais testé en prod~~ → **cycle complet validé en live** avec un vrai token (provision → composants → publish → CDN fetch → aplatissement `from_storyblok_site_content` → re-sync), sur un space de test créé puis supprimé. **2 bugs prod trouvés & corrigés** : (a) `artisan_edito` (template **par défaut**) ne ré-exportait pas `to_storyblok_site_content` → **provisioning impossible** ; (b) le re-fetch CDN prenait un **301 non suivi** (`follow_redirects=False`) → en région EU **les éditions client ne se synchronisaient jamais** dans `content_json` → fix `follow_redirects=True`.
- ✅ **Re-sync des spaces existants** : ~~l'API ne met pas à jour les composants existants~~ → `_ensure_template_components` fait désormais un **upsert** (PUT sur les composants existants, POST sinon) → propage les nouveaux champs (`social`) et libellés FR. Méthode publique `storyblok_service.resync_components(space_id)` + endpoints admin `POST /admin/storyblok/resync/{space_id}` et `/resync-all`.
- ✅ **Génération accélérée** : ~~~5-6 appels séquentiels (timeout 60 s)~~ → les composants sont **upsertés en parallèle** (concurrence bornée) et les 3 étapes indépendantes de `provision_space` (preview URL, composants, webhook) tournent **en `asyncio.gather`** → **provision mesurée à ~4 s** en live (vs séquentiel + `sleep 0.15` × 12).

### Étape 4 — Démo
**Bien** : `demo.dibodev.fr/{slug}`, TTL 14 j + nettoyage auto (worker de fond), vérification d'URL, **tracking PostHog** riche (pageviews, clics tel/email/CTA, scroll, temps, session replay), étiqueté `demo_slug` + variante A/B.
**À améliorer / risqué** :
- **RGPD** : session replay **nominatif** sans bandeau de consentement (choix assumé « en test »). À cadrer **avant** tout volume/revente — risque juridique réel.
- ✅ **RÉSOLU (2026-07-13)** — ~~Dépend de la **connexion Resend→PostHog** (config) pour boucler le funnel A/B email→démo→vente.~~ Source warehouse Resend connectée & saine (vérifiée via MCP) **+** events email captés à la source sous l'identité `demo_slug` → funnel `email→démo→vente` requêtable nativement (cf. §journal 2026-07-13).

### Étape 5 — Cold email
**Bien** : A/B, file **throttlée 1 mail/20 min** via un **worker asyncio persistant** (tick 60 s, ≤10/tick, isolé par erreur — ne meurt jamais), relances multiples **automatiques** (temporelles), garde-fou « lien démo vide », **désinscription RGPD** (footer + triple filtre + headers RFC 8058), relance perso selon comportement, sélection A/B dès la création.
**À améliorer / risqué** :
- **Délivrabilité partiellement gérée** : la **vérif SPF/DKIM** d'un compte custom-domain est désormais **réelle** (`dns_service`, lookups dnspython — cf. §journal). Reste ouvert : **warm-up de domaine, DMARC, cap quotidien global**. Un mauvais départ **brûle le domaine `dibodev.fr`** — c'est le vrai risque du cold email.
- **Limites de tracking Resend** connues (réponses/suppressions non traçables) → angles morts du funnel.
- ✅ **RÉSOLU (2026-07-11) — `mailjet_service` placeholder/mort** : supprimé (Léo utilise Resend). Les comptes custom-domain envoient via Resend ; la vérif DNS ne renvoie plus les fausses instructions Mailjet.

### Étape 6 — Vendre + mettre en prod
**Bien** : section Ventes (`Order` multi-produit), lien Stripe **distinct des crédits**, email avec preview, **webhook Stripe → fulfilment auto**, remboursements gérés, **vérification avant `DELIVERED`** (domaine répond + CMS réel), mise en prod par domaine (Vercel host→slug — vrais appels API v10), handover Storyblok auto à la vente.
**À améliorer / risqué** :
- **Jamais déclenché par un vrai paiement** : tout le fulfilment est du code réel **non éprouvé en prod**. **La première vente = le vrai test d'intégration.**
- **Asymétrie** : le `mark-paid` **manuel** ne lance PAS le fulfilment (seul le webhook le fait) → il faut re-cliquer « Déployer ». *(atténué : la loop de reprise rattrape désormais une commande `paid` non livrée — cf. §2.6.)*
- **DNS du domaine = étape manuelle externe** (Vercel n'achète pas le domaine) — rupture dans « à vie sans dev ».
- ~~Fulfilment **fire-and-forget**~~ ✅ **RÉSOLU** (loop de reprise + cap + tracking — cf. §2.6).

---

## 4. Dimensions transverses

### Tests — 🔴 MANQUANT (risque #1)
**Couverture réelle ≈ 0 %.** Aucune suite `pytest` réelle (les 2 fichiers `test_*` sont des scripts smoke à `print()`), aucun `conftest.py`/`pytest.ini`, **`pytest` est dans `requirements.txt` mais jamais utilisé** (l'intention existait). Côté front : 0 test, aucun script `test`. Aucun job de test en CI. → **Le seul filet est le typage front (vue-tsc) + le lint pre-commit.** Toute régression back n'est visible qu'à l'exécution — sur un pipeline fait de maillons fragiles (scraping, webhooks, paiement, CMS), c'est le trou le plus dangereux.

### Robustesse & gestion d'erreurs — 🟠 Fragile
**163 `except Exception`** + **90 `# noqa: BLE001`** dans `api/` : la plupart dégradent gracieusement (bien), mais **masquent les causes** et **rien n'est monitoré**. **23 `print()`** en prod, y compris sur des chemins **financiers** (`payments.py`, `stripe_payment_service.py`, `accounting_service.py`). Le webhook Stripe renvoie `str(e)` dans un 500 (fuite d'info). **Bien** : handler global 500 propre avec CORS ; worker email résilient (anti-runaway).

### Observabilité — 🟠 Fragile
**Aucun Sentry / APM / logging structuré** (recherche `sentry|opentelemetry|structlog|prometheus` = vide) — **le principal trou d'observabilité encore ouvert**. ~~Health check factice~~ ✅ **résolu** (§2.5, probe DB + 503) ; une **capture réactive par source** existe désormais (diagnostics scraping/enrichment → page admin de monitoring). Root logger à `WARNING` (les `INFO` masqués), pas d'ID de corrélation. → sans Sentry, **on ne voit toujours pas** un webhook 4xx ou une erreur applicative en temps réel.

### Sécurité & RGPD — 🔴 Risqué
- **Auth** : bcrypt (bon), JWT HS256, expiry 30 min, **pas de refresh token** ni de révocation → re-login fréquent (et le front stocke le token en localStorage).
- **Rate limiting incohérent** : appliqué **seulement sur l'auth** ; `core/rate_limiter.py` définit un dict `RATE_LIMITS` **jamais utilisé (code mort)** ; **3 instances `Limiter`** distinctes ; **stockage in-memory** (reset au restart, ne tient pas multi-worker). Endpoints publics (unsubscribe) non spécifiquement limités.
- ~~**Unsubscribe sans token + XSS réfléchie**~~ ✅ **RÉSOLU** (cf. §2.4 — token HMAC + `html.escape`).
- **Webhooks fail-open** : Resend (svix) et Storyblok **acceptent tout si le secret n'est pas configuré** (`return True`). Pour Storyblok c'est défendable (payload jamais cru, re-fetch source) ; **pour Resend, reste à durcir** (⏳ demi-item ouvert). Stripe **OK** (signature exigée).
- ~~**Secret BrightData committé**~~ ✅ **RÉSOLU** (cf. §2.2 — révoqué + purgé).
- **CORS** : `allow_credentials=True` avec origines `localhost` autorisées **en prod** (risque faible mais négligé).
- **RGPD** : désinscription conforme, mais session replay nominatif sans consentement (cf. étape 4).

### Modèle de données & migrations — 🟠 Partiel
Runner **idempotent** (table `schema_migrations` + garde `INFORMATION_SCHEMA` avant `ALTER`), scoping `user_id`/`organization_id` cohérent (multi-user sans fuite, testé cette session). ~~**migrations non jouées en CI**~~ → ✅ **jouées au déploiement** (§2.7). **Mais** : forward-only (aucun rollback), **Alembic est installé mais inutilisé** (migrations réécrites à la main), hybride `create_all` + migrations incrémentales qui peut **diverger** sans détection, quelques **incohérences mortes** (enum `YELP` gardé alors que le scraper est retiré, endpoint `GET /prospects/search` deprecated mais présent). ~~un **seeder qui injecte de fausses transactions crédit** en base d'init~~ → ✅ **gaté hors production** (`settings.is_production`).

### Qualité du code — 🟢 Front / 🟠 Back
- **Front** : **TS ultra-strict réellement tenu** — 0 `any`, 0 `as any`, 0 `@ts-ignore` dans `web/app`, lint (prettier+eslint+vue-tsc) imposé au commit, arbo nette. **Rare et excellent.** Résidus : **65 `console.*`** laissés.
- **Back** : **aucun outil de lint/type Python** (pas de mypy/ruff/black, pas de `pyproject.toml`), typage partiel (~65 % des fonctions de `services/` annotées), **services obèses** (`accounting_service` 1079 l, `storyblok_service` 717, `demo_site_service` 591, `campaign_queue_service` 549, `order_service` 535), et `@app.on_event` déprécié (vs `lifespan`).

### Complétude fonctionnelle — 🟠 Partiel
**Réellement câblé** : tout le tunnel (code réel, pas stub) + Vercel (vrais appels) + Stripe (checkout/webhook/refund) + scoring PostHog. ~~**À valider en live** : cycle Storyblok publish→webhook, sélecteurs enrichment~~ → **désormais éprouvés en live** (cf. Étapes 2-3). Reste à valider en réel : **déploiement Vercel de vente** (achat domaine/DNS **hors scope**, manuels) et **webhooks Stripe jamais déclenchés en prod**. ~~**Stubs réels** : `updateProfile`, `mailjet_service`~~ → **résolus** (updateProfile branché §2.3 ; mailjet supprimé). **Vision non construite (normal)** : Apple Wallet, Missions freelance, facturation multi-user.

### CI/CD & déploiement — 🟠 Fragile
4 workflows (deploy-api VPS OVH, deploy-web VPS, deploy-demo-host Vercel, desktop-release Tauri). **Fragilités** : **zéro job de test/lint en CI** (les workflows **déploient seulement** ; seul filet = pre-commit local, contournable via `--no-verify`), deploy-api fait `rm -rf` + ré-upload (**fenêtre de coupure, pas de health check post-restart, pas de rollback, migrations non jouées, secrets omis**), **desktop-release = Windows only** (README/skill affirment Windows+macOS — inexact), demo-host déployé avec contournements Vercel documentés.

### DX & doc — 🟢 Solide
Doc abondante et à jour (`README`, `LOCAL_DEV`, `STANDARDS…`, `TEMPLATES_ARCHITECTURE`, `.env.example` commenté, skill `/devleadhunter` excellent), onboarding one-command (`npm run dev` lance les 3). **Inexactitudes à corriger** : README `playwright install chromium` (le projet utilise `nodriver`, pas Playwright), desktop « Windows + macOS » (Windows seulement), le skill liste un scraper `yelp_` retiré.

### Frontend / UX — 🟢 Solide
Refonte « Atelier » de qualité (tokens light/dark, IBM Plex, lucide, drawers persistants, palette Ctrl+K), `demo-host/` minimal et net. **Points faibles** : ~~modif de profil non fonctionnelle~~ ✅ (résolu §2.3), 65 `console.*` résiduels, et **la vérification visuelle des écrans récents n'a pas pu se faire** (pas de tests Playwright + l'outil de navigation « Claude in Chrome » était déconnecté — c'est une capacité de l'assistant, **pas** un artefact du repo ; ma note antérieure « extension non testée » ne désigne donc aucun code d'ici). Un passage runtime/Playwright reste à faire.

---

## 5. Top risques priorisés

| # | Risque | Impact | Effort | Pourquoi maintenant |
|---|--------|--------|--------|---------------------|
| ~~1~~ ✅ | ~~**Secrets de déploiement omis** (ENCRYPTION_KEY/RESEND)~~ **RÉSOLU** | Critique | Faible | Corrigé (commit `3b8db54`) — 7 vars injectées + secrets Actions ajoutés |
| ~~2~~ ✅ | ~~**Token BrightData committé**~~ **RÉSOLU** | Élevé | Faible | Corrigé (commit `3b8db54`) — token révoqué + fichiers purgés |
| 3 | **Zéro test + zéro gate CI** | Élevé | Moyen | Aucune détection de régression, surtout en montant en charge/multi-user |
| ~~4~~ ✅ | ~~**Migrations non automatisées**~~ **RÉSOLU** | Élevé | Faible | `run_migrations.py` joué au déploiement (idempotent) |
| 5 | **Maillons jamais éprouvés en prod** (1re vente, Stripe, Storyblok, Vercel) | Élevé | Faible | Une vente test de bout en bout dérisque d'un coup |
| ~~6~~ ✅ | ~~**Fulfilment fire-and-forget**~~ **RÉSOLU** | Élevé | Moyen | Loop de reprise + cap + tracking ; redéploiement manuel réarme |
| ~~7~~ ✅ | ~~**Enrichissement fragile**~~ **RÉSOLU** (fallbacks JSON-LD + source OSM + social branché & rendu) | Élevé | Moyen | `services` laissé manuel volontairement (défauts templates meilleurs) |
| 8 | 🟡 **Unsubscribe** ✅ (token+XSS corrigés) / **webhooks Resend fail-open** ⏳ | Moyen-élevé | Faible | Unsubscribe sécurisé ; reste à exiger le secret Resend |
| 9 | 🟡 **Health check** ✅ (probe DB réel) / **pas de Sentry** ⏳ | Moyen | Faible | Pannes DB détectables ; observabilité applicative encore absente |
| 10 | **RGPD tracking nominatif** | Moyen (juridique) | Faible | À cadrer avant volume |
| ~~11~~ ✅ | ~~**updateProfile mocké**~~ **RÉSOLU** | Moyen | Faible | Branché sur `PATCH /auth/me` — persiste réellement |
| 12 | **Délivrabilité cold email** non gérée | Moyen | Moyen | Un mauvais départ brûle le domaine |

---

## 6. Recommandations priorisées

**Immédiat (heures)**
- ~~**Vérifier `api/.env` sur le VPS** (secrets #1) + **révoquer le token BrightData** (#2) + purger `test_bedee_comparison.py`/`response.json`.~~ ✅ **FAIT (2026-07-11, commit `3b8db54`)** — secrets injectés au déploiement, token révoqué, fichiers purgés, PageSpeed vérifié. Reste : re-saisir les comptes email au 1er deploy.
- **Brancher un Sentry** (gratuit) api + demo-host — voir enfin quand ça casse. *(reste à faire — le seul demi-item d'observabilité encore ouvert)*
- ~~**Vrai health check** (ping DB)~~ ✅ **FAIT** (§2.5, probe DB + 503).

**Quick wins (jours)**
- **Faire une vente test de bout en bout** (toi en cobaye : Stripe test → domaine → publication CMS → webhook → site à jour) : valide d'un coup #5, #6 et le cycle Storyblok. *(le cycle Storyblok, lui, est déjà validé en live — cf. Étape 3.)*
- ~~**Corriger `updateProfile`** (#11)~~ ✅ **FAIT**.
- ~~**Protéger l'unsubscribe** (token signé + échapper le HTML — #8)~~ ✅ **FAIT**. Reste : **exiger le secret Resend** (fermer le fail-open).
- **Cadrer le RGPD** (bandeau/consentement démos, ou couper le replay nominatif).
- Configurer les clés d'env restantes. ~~**Resend→PostHog**~~ ✅ **FAIT (2026-07-13)** — source warehouse connectée + `email_sent` capté à la source (funnel bouclé, cf. §journal).

**Court terme (semaines)**
- ~~**Jouer les migrations en CI** (ou au boot) (#4)~~ ✅ **FAIT** (au déploiement).
- **Poser un socle de tests** sur les points où une régression coûte cher (bridges Storyblok, webhook Stripe/fulfilment, garde-fous d'envoi, parsing import, scoring) + **les faire tourner en CI** (avec le lint front déjà là). *(amorcé : `api/tests/` + 11 tests sur `resilient_extract` ; reste à élargir + brancher en CI.)*
- ~~**Fiabiliser l'enrichissement** ... `services`/`social_links` (#7)~~ ✅ **FAIT** (fallbacks JSON-LD + OSM + social branché & rendu ; `services` laissé manuel volontairement).
- ~~**Fulfilment robuste** : retry + dead-letter + reprise (#6)~~ ✅ **FAIT** (loop de reprise + cap + tracking).
- **Délivrabilité** : ~~vérif SPF/DKIM~~ ✅ (réelle désormais) ; reste **cap quotidien global**, **warm-up**, **DMARC**.
- ~~**Re-sync des schémas Storyblok** pour les spaces existants~~ ✅ **FAIT** (upsert PUT + endpoints admin).
- **Lint/type Python** (ruff + mypy) en CI pour amener le back au niveau du front ; découper les god services au fil de l'eau.

**Structurant**
- **Auto-chaînage du tunnel** (cf. `02-auto-chainage-tunnel.md`) : ce qui fait passer l'outil de « pipeline outillé » à « machine autonome » — **mais seulement après** un minimum de filet (tests + monitoring + secrets sains). Automatiser une chaîne fragile amplifie ses défauts.

---

## 7. Ce qui est franchement réussi (à préserver)

Pour l'équilibre — ce sont de vraies fondations, pas des acquis à défaire : l'**architecture templates** (un repo/layer par métier, contrat unique, dispatch par composant), le **contrat `SiteContent`** + ses deux bridges miroirs, la **refonte UI Atelier** et le **socle de drawers persistants**, le **CMS Storyblok réellement bouclé** (webhook publish→content_json), le **mock mode** Storyblok, le **worker d'envoi résilient**, la **vérification de signature Stripe**, les **organisations** avec réservation, et surtout la **discipline de qualité front** (TS strict réellement tenu). Le travail restant est du **durcissement**, pas de la reconstruction — et c'est une bonne nouvelle.
