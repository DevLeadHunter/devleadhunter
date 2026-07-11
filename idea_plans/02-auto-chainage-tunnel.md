# Plan — Auto-chaînage du tunnel : de « pipeline outillé » à « machine autonome »

> **Date** : 2026-07-11
> **Objet** : proposer une architecture concrète pour enchaîner automatiquement **recherche → enrichissement → génération de site → démarchage (→ relance → vente)** sans clic entre chaque étape, tout en gardant la main quand on le veut.
> **Prérequis lucide** : automatiser une chaîne fragile amplifie ses défauts. Ce plan suppose qu'on pose **en parallèle** un minimum de filet (voir `01-audit-logiciel.md` §5). On automatise une chaîne **fiable**, pas une chaîne bancale.

---

## ✅ État d'implémentation — Phase 1 livrée (2026-07-11, branche `feat/acquisition-sequences`)

Le **MVP « semi-auto sur un lot »** (§9 Phase 1) est construit de bout en bout, back + front, lint/types verts.

**Back (`api/`)**
- **Modèles** : `AcquisitionRun` + `AcquisitionRunItem` (`models/acquisition_run*.py`), enums `enums/acquisition.py` (statut run / mode / step). État 100 % en base → reprise après crash. Champs recherche (`search_*`, `only_without_website`) déjà prévus pour la Phase 2, nullables.
- **Migration** : `migrations/add_acquisition_tables.py` (idempotente, `checkfirst`), enregistrée dans `run_migrations.py` + `init_db()` + `models/__init__.py`.
- **Orchestrateur** : `services/acquisition_orchestrator.py` — worker asyncio `run_acquisition_loop()` (tick 30 s, budget d'avancées/tick), **stateless**, greffé au boot de `main.py` comme `run_queue_worker`. Machine à états par item `found → enriched → generated → (pause review) → campaigning`, réutilise `enrichment_service` / `demo_site_service` / `campaign_service` + `CampaignQueueService`. Retries bornés, garde-fous **crédits** (plancher + budget `max_credits` via delta consommé) et **cap emails/jour** (au lancement de la campagne, débordement `skipped` avec raison visible — pas de troncature silencieuse). Respecte la réservation org.
- **Service métier** : `services/acquisition_service.py` (créer depuis prospects visibles, pause/reprise/annuler, **valider la review**, rejeter un site, stats dérivées : compteurs par step + `won` via Orders + emails via EmailLog).
- **API** : `routes/acquisition_sequences.py` (`POST /acquisition-sequences`, list, detail, `pause`/`resume`/`cancel`/`approve`, `items/{id}/reject`, delete), scopée user, enregistrée dans le routeur v1.

**Front (`web/`)**
- `types/AcquisitionSequence.ts`, `services/acquisitionSequencesService.ts`, store Pinia `stores/acquisitionSequences.ts` (avec polling live via `hasActive`).
- **Drawer** `UiCreateSequenceDrawer` (sélection de prospects filtrable, mode, étapes auto, template de site, modèles A/B, garde-fous) — poussé sur la pile de drawers (règle de Léo : formulaire = drawer), câblé dans `DrawerStackHost`.
- **Page** `dashboard/sequences` — liste + **vue pipeline** (colonnes File/Enrichis/Sites générés/En campagne/Écartés), **bandeau de validation** « X sites à valider → Valider et démarcher », rejet au cas par cas, KPIs (sites/emails/**vendus**), pause/reprise/annuler. Entrée de nav « Séquences » (groupe Automatisation).

**Reste (non fait) — Phases 2-4** : chaîner la recherche T1 (partir d'un métier+ville), full-auto planifié/scoring, reflet live du `won` en `step` d'item, éditeur de relances dans le drawer, les 2 « quick wins » §5 (fulfilment au `mark-paid`, migration `lifespan`). Vérif E2E réelle à faire par Léo (nécessite pile MySQL+API + compte connecté + prospects).

---

## 1. Vision & principes

Aujourd'hui chaque étape est un **déclenchement manuel** (choix historique assumé : garder la main). Le but : que Léo puisse dire « **prospecte 30 plombiers à Lyon, génère leurs sites, et lance la campagne** » — et que la machine le fasse seule, en le tenant informé et en s'arrêtant aux points où **son jugement** a de la valeur.

**Principes non négociables :**
1. **Semi-auto par défaut, full-auto en option.** On ne remplace pas le jugement humain, on le déplace vers les rares points qui comptent (valider un site avant de démarcher, valider une campagne avant l'envoi). Full-auto est un mode assumé, pas le défaut.
2. **Garder la main = pouvoir stopper/reprendre/annuler à tout moment**, voir où en est chaque prospect, corriger avant l'étape suivante.
3. **Idempotent & reprenable.** Un run qui plante à l'étape 3 reprend à l'étape 3, pas à zéro. Chaque prospect avance indépendamment.
4. **Budget-aware.** Chaque étape consomme des crédits / du quota d'envoi / du temps Chrome. Le moteur respecte des **plafonds** (crédits max, X mails/jour, N sites/run) et s'arrête proprement.
5. **Observable.** Un run raconte son histoire (timeline par prospect, raisons de skip, erreurs) — indispensable pour un pipeline fait de maillons fragiles.
6. **Réutilise l'existant.** Tous les services unitaires existent déjà (`scraping_job_service`, `enrichment_service`, `demo_site_service`, `campaign_queue_service`, `order_service`). L'auto-chaînage est une **couche d'orchestration au-dessus**, pas une réécriture.

---

## 2. État actuel — les 5 points de clic manuels *(cartographie vérifiée dans le code)*

| # | Transition | Aujourd'hui | Déclencheur exact (fichier / endpoint) |
|---|-----------|-------------|-----------------------------------------|
| 1 | Lancer une recherche | **Manuel** | `search-prospects.vue` → `POST /scraping-jobs` → `scraping_job_service.start_job()` |
| 2 | Prospect trouvé → enrichir | **Manuel** | `ProspectEnrichment.vue` / bouton « Enrichir » → `POST /prospects/{id}/enrichment/run` ou `/enrichment/bulk-run` (max 50, **synchrone**) |
| 3 | Enrichi → générer le site | **Manuel** | wizard `create.vue` / « Générer les sites » → `POST /demo-sites` ou `/demo-sites/bulk` (max 25, **synchrone**) |
| 4 | Site prêt → campagne | **Manuel** | `POST /campaigns` (créer) + `/campaigns/{id}/prospects` (ajouter) + `/campaigns/{id}/launch` (lancer) |
| 5 | Campagne → relance / vente | **Semi-auto** | Relances = **auto** (worker, temporel) ; vente = webhook Stripe **auto** au paiement |

**Déjà automatisé — les 4 seuls « seams » (les briques sur lesquelles bâtir) :**
1. **Génération → enrichissement** : `demo_site_service.create_demo_site(prospect_id)` appelle `enrichment_service.ensure_enriched()` avant de provisionner. Générer un site enrichit d'abord si besoin.
2. **Paiement (webhook Stripe) → mise en prod** : `payments.py` → `asyncio.create_task(order_service.fulfill_order_async)` → Vercel + `mark_delivered` + invite CMS. **Le seul enchaînement auto de bout en bout.**
3. **J1 envoyé → relances** : `campaign_queue_service._schedule_follow_ups()` planifie toutes les étapes (temporel), le worker les envoie à échéance.
4. **Worker → file** : `email_queue_worker` consomme la table `email_queue` en continu.

> 🎯 **Le trou n°1, nommé précisément** : `prospect_service.create_prospect()` **ne déclenche RIEN** après sauvegarde (add/commit/return). Aucun prospect nouvellement trouvé/sauvé ne notifie de service en aval. **C'est le crochet à créer** pour amorcer `scrape → enrich → generate`. De même, les jobs de scraping vivent **en mémoire** (`self._jobs`, perdus au redémarrage) — un vrai orchestrateur exige un état **persisté en base** (voir §3).

---

## 3. Le concept central : une « Séquence d'acquisition »

On introduit un objet de premier ordre : **`AcquisitionRun`** (ou « Séquence ») — une recette qui décrit *quoi prospecter et jusqu'où aller automatiquement*.

**Exemple de séquence :**
> « **Plombiers à Lyon**, 30 max, source Pages Jaunes, sans site web → enrichir → générer avec la template *artisan-edito* → **s'arrêter pour validation** → puis campagne A/B *(modèle X / Y)* avec relance J+5 et J+10. Plafond : 200 crédits, 20 mails/jour. »

C'est une **configuration** que l'orchestrateur exécute étape par étape, prospect par prospect, en respectant les points d'arrêt et les plafonds.

### Modèle de données proposé
```
AcquisitionRun
  id, user_id, organization_id
  name
  status            # draft | running | paused | awaiting_review | completed | cancelled | failed
  # --- config de recherche ---
  search_category, search_city, search_source, max_results, only_without_website
  # --- config des étapes (jusqu'où aller + mode) ---
  auto_enrich       # bool
  auto_generate     # bool + template_id
  auto_campaign     # bool + template_id_a / template_id_b / follow_ups
  mode              # semi_auto (points de validation) | full_auto
  # --- garde-fous ---
  max_credits, daily_email_cap
  # --- suivi ---
  created_at, updated_at, stats(json)

AcquisitionRunItem   # un prospect dans la séquence
  id, run_id, prospect_id
  step              # found | enriching | enriched | generating | generated | review | campaigning | contacted | won | skipped | failed
  step_reason       # ex. "pas d'email", "site déjà bon", "réservé par un autre membre"
  updated_at
```

Cette structure donne **gratuitement** : reprise sur incident (chaque item a son `step`), observabilité (timeline par prospect), garde-fous (compteurs), et l'org-awareness (un run appartient à un user/org, réutilise la visibilité prospects existante).

---

## 4. L'orchestrateur : machine à états par prospect

Le cœur est un **service `acquisition_orchestrator`** qui, pour chaque `AcquisitionRunItem`, fait avancer l'état selon la config, en appelant les services unitaires existants. C'est une **machine à états** simple :

```
found → (auto_enrich ?) → enriched → (auto_generate ?) → generated
      → (mode semi_auto ? PAUSE "review") → (auto_campaign ?) → campaigning → contacted
```

Chaque transition = **une fonction qui (a) vérifie les préconditions/garde-fous, (b) appelle le service existant, (c) écrit le nouvel état + la raison**. Détail des transitions avec garde-fous :

### T1 · Recherche → items
- Lance un `scraping_job` avec la config du run. **Chaque prospect sauvé crée un `AcquisitionRunItem` en état `found`** (hook après `create_prospect` dans `scraping_job_service`).
- Garde-fou : respecte `max_results` et le plafond de crédits.

### T2 · found → enriched (si `auto_enrich`)
- Appelle `enrichment_service` (réutilise le bulk existant). 
- Garde-fou : timeout par prospect ; si l'enrichissement rend vide (sélecteurs cassés), l'item passe `enriched` quand même mais **flag qualité** (le site sera pauvre) — et on **log/alerte** (relie au point fragile de l'audit).

### T3 · enriched → generated (si `auto_generate`)
- Appelle `demo_site_service.create` (ou bulk) avec le `template_id` du run. Le contenu enrichi est déjà injecté.
- Garde-fou : **ne génère que si l'enrichissement a produit un minimum** (nom + au moins téléphone OU services), sinon `skipped` (raison « données insuffisantes »). Évite de générer 30 sites vides.
- Garde-fou : respecte le plafond de sites/run.

### T4 · generated → PAUSE `review` (mode semi_auto)
- **Le point de validation humaine le plus rentable.** Le run passe `awaiting_review` : Léo voit les sites générés, en corrige/rejette, puis « Valider et démarcher ». En full_auto, on saute ce point.
- Garde-fou : ne démarche jamais un prospect dont le site n'est pas `active` (réutilise le garde-fou existant `_template_uses_demo_link`).

### T5 · generated/validé → campaigning (si `auto_campaign`)
- Crée (ou réutilise) une campagne avec les modèles A/B du run, **y ajoute les prospects du run**, la lance. La file throttlée 1 mail/20 min + les relances **existent déjà** — on s'y branche.
- Garde-fous : `daily_email_cap` global, exclusion des désinscrits (déjà en place), exclusion des prospects **réservés par un autre membre** (org), skip si pas d'email.

### T6 · relance & vente (déjà auto)
- Relances = worker existant (temps). Vente = webhook Stripe → fulfilment (déjà auto). L'item passe `won` quand une `Order` liée passe `paid`. **Rien à réécrire**, juste refléter l'état dans le run.

---

## 5. Infra d'exécution en arrière-plan — ce qui existe déjà (vérifié)

Bonne nouvelle : **le socle existe**. L'API démarre déjà des workers de fond au boot (`main.py`, `@app.on_event("startup")`), en **tâches asyncio** :

| Worker existant | Type | Cadence | Rôle |
|---|---|---|---|
| `run_queue_worker()` | asyncio task, `while True` | tick **60 s**, ≤10 envois | Dispatch de la file cold-email (`email_queue_worker.py`) |
| `run_demo_site_cleanup_loop()` | asyncio task, `while True` | **3600 s** | Expiration/suppression des démos + spaces |
| Jobs de scraping | `asyncio.create_task` par requête | à la demande | **État en mémoire** (perdu au redémarrage) |
| Fulfilment vente | `asyncio.create_task` sur webhook | à l'événement | Vercel + livraison |

**Pas de scheduler/cron applicatif** (ni APScheduler, ni Celery/RQ ; les GitHub Actions n'ont pas de `cron:`). L'API utilise encore l'ancien `@app.on_event("startup")` (pas `lifespan`).

**Donc, concrètement :**
- **On greffe l'orchestrateur exactement comme `run_queue_worker`** : une nouvelle tâche asyncio de boot, `run_acquisition_loop()`, tick toutes les ~30-60 s. Elle lit en base les `AcquisitionRunItem` « prêts à avancer », exécute **une** transition par item, écrit le nouvel état. C'est le même patron que le worker d'emails, déjà éprouvé.
- **Le principe clé : l'état vit en base, pas en mémoire.** Le worker est *stateless* — il lit les items prêts et les avance d'un cran. Un crash/redémarrage ne perd rien et reprend naturellement (contrairement aux jobs de scraping actuels, en mémoire). C'est ce qui rend la machine autonome ET robuste.
- **Amélioration d'infra recommandée en Phase 0** : migrer les `@app.on_event("startup")` vers un **`lifespan`** FastAPI (ajout propre d'un worker supplémentaire, arrêt gracieux) — petit refactor, gros confort.

### Deux « quick wins » d'auto-chaînage repérés dans le code (avant même l'orchestrateur)
- **Unifier le paiement manuel** : `POST /orders/{id}/mark-paid` marque payé mais **ne lance PAS** `fulfill_order` (seul le webhook Stripe le fait). → faire déclencher le fulfilment au `mark-paid` comme au webhook. Supprime un clic « Déployer » et une asymétrie source de confusion.
- **Le seul input humain incompressible de la mise en prod** = `order.domain` (Vercel n'achète pas le domaine, le DNS est externe). L'auto-chaînage peut aller jusqu'à « prêt à déployer, en attente du domaine » — la saisie du domaine reste le point d'arrêt naturel de fin de tunnel.

---

## 6. Modes & points de validation

| Mode | Enrichir | Générer | **Valider les sites** | Démarcher | Pour qui |
|------|:---:|:---:|:---:|:---:|---|
| **Manuel** (actuel) | clic | clic | — | clic | contrôle total |
| **Semi-auto** (défaut proposé) | auto | auto | **PAUSE humaine** | auto après validation | le bon compromis |
| **Full-auto** | auto | auto | auto | auto | volume, confiance établie |

Le **point de validation « review »** est le cœur du semi-auto : c'est là que le jugement humain a le plus de valeur (un site raté qu'on envoie = un prospect grillé + une image de marque). On peut même affiner : validation **par lot** (« ces 25 sites sont bons, go ») plutôt que par prospect.

---

## 7. UI de pilotage — une page « Séquences » (ou « Automatisation »)

- **Créer une séquence** : un formulaire/wizard (métier, ville, source, max, template, mode, plafonds, modèles A/B). Réutilise les composants existants (autocomplete ville, sélecteurs de modèles A/B déjà dans le drawer campagne).
- **Suivre une séquence** : une vue « pipeline » — colonnes par étape (Trouvés / Enrichis / Sites générés / En validation / En campagne / Vendus), chaque prospect une carte qui progresse. Barre de progression, crédits consommés, mails du jour, bouton **Pause / Reprendre / Annuler**.
- **Point de validation** : quand le run est `awaiting_review`, un bandeau « 25 sites à valider » → grille d'aperçus (le `DemoSitePreviewFrame` existe déjà) → « Valider et démarcher » / rejeter au cas par cas.
- Cette page **matérialise le tunnel** — elle rejoint l'idée « vue Pipeline comme home » évoquée dans la vision produit.

---

## 8. Garde-fous transverses (à câbler dès le MVP)

- **Crédits** : le run s'arrête net quand `max_credits` est atteint (raison explicite), ne démarre pas une étape qu'il ne peut pas payer.
- **Anti-spam / délivrabilité** : `daily_email_cap` global (tous runs confondus), throttle 1/20 min conservé, jamais deux fois le même prospect, exclusion désinscrits + réservés-par-un-autre.
- **Qualité** : ne pas générer sur données insuffisantes ; ne pas démarcher sans site `active` ; flag qualité quand l'enrichissement est pauvre.
- **RGPD** : hérite du cadrage global (cf. audit) — l'automatisation ne doit pas contourner le consentement.
- **Réversibilité** : Pause/Annuler à tout moment ; un run annulé laisse les prospects/sites déjà créés en place (rien de destructif).
- **Org** : un run respecte la visibilité et la réservation des prospects de l'organisation.

---

## 9. Plan par phases

**Phase 0 — Prérequis (dérisquage, cf. audit)** : confirmer/poser le runner de fond, brancher monitoring, quelques tests sur les maillons. *Ne pas automatiser une chaîne aveugle.*

**Phase 1 — MVP « semi-auto sur un lot »** *(le plus gros ROI)* :
- Modèle `AcquisitionRun` + `AcquisitionRunItem` + migration.
- Orchestrateur : transitions T2→T3→T4(pause)→T5 sur des prospects **déjà trouvés** (on part d'une sélection existante, on ne recâble pas la recherche tout de suite).
- Un endpoint « créer une séquence à partir de ces prospects » + le tick worker.
- UI minimale : lancer, suivre (pipeline), valider le lot, stopper.
→ Résultat : « je sélectionne 25 prospects, la machine enrichit + génère + s'arrête pour validation + démarche ». **80 % de la valeur.**

**Phase 2 — Chaîner la recherche (T1)** : la séquence part d'un métier+ville, lance le scraping, crée les items automatiquement. La machine devient autonome de bout en bout.

**Phase 3 — Full-auto + affinages** : mode sans validation, planification (« tous les lundis, 20 plombiers d'une nouvelle ville »), scoring qui priorise l'ordre de démarchage, relances pilotées par comportement intégrées au run.

**Phase 4 — Autonomie complète** : la machine tourne en fond, remplit le pipeline, et Léo n'intervient que pour valider/vendre. C'est la « machine autonome » cible.

---

## 10. Pourquoi ça transforme l'outil

Aujourd'hui DevLeadHunter **outille** chaque étape ; demain il **exécute** la chaîne. La différence : le temps de Léo passe de « cliquer entre chaque page pour 25 prospects » à « définir une intention + valider les sites ». C'est le passage de l'**outil** à l'**agent** — et c'est le seul chantier qui change la nature du produit plutôt que d'ajouter une fonctionnalité de plus.

**Ordre recommandé** : Phase 0 (filet minimal) → Phase 1 (semi-auto sur lot, énorme ROI) → mesurer → Phase 2/3. Ne pas viser le full-auto d'emblée : le semi-auto sur lot capture l'essentiel de la valeur avec le moins de risque.
