# Plan — L'Automatisation : le tunnel qui trouve → génère → vend

> **Date** : 2026-07-11 · **Révisé** : 2026-07-12 (cadrage co-construit avec Léo)
> **Objet** : un **tunnel guidé unique** qui enchaîne **cible → génération de sites → validation → démarchage**, en **semi-auto** (on marche les étapes, avec des points de validation) ou en **full-auto** (le même tunnel qui s'auto-avance à partir d'un métier + une ville). Ce tunnel **remplace** l'actuel « Créer un site ».
> **Prérequis lucide** : automatiser une chaîne fragile amplifie ses défauts. Le full-auto scrape tout seul — le maillon le plus fragile (cf. `01-audit-logiciel.md` §5). On pose donc des garde-fous honnêtes : s'arrêter et prévenir plutôt qu'inventer, flaguer les sites sous-remplis. On automatise une chaîne **fiable**, pas une chaîne bancale.

---

## 0. Décisions produit (verrouillées le 2026-07-12)

- **Un seul moteur.** Le tunnel **remplace entièrement** « Créer un site ». Générer **un seul** site = le tunnel avec **1 prospect** et l'envoi désactivé. Le bouton « Générer un site » du drawer prospect devient un raccourci qui pré-remplit le tunnel avec ce prospect.
- **Nom.** Le concept = **« Automatisation »**. Le **gros bouton du menu de navigation** devient **« Créer une automatisation »** (texte d'action, comme « Créer un site »). Renommable trivialement.
- **Deux modes, un tunnel.** *Semi-auto* : on marche les étapes avec les gates humaines. *Full-auto* : le **même tunnel qui s'auto-avance**, à partir d'un métier + une ville + un objectif en jours.
- **Un prospect = une seule automatisation.** Un prospect n'est lié qu'à une automatisation à la fois → un seul mail, un seul site. C'est le verrou anti-double-démarchage.
- **La cadence d'envoi vit dans les Paramètres**, pas dans le tunnel : une **politique d'envoi globale** (fenêtre horaire, jours, espacement, plafond/jour) qui gouverne **toute la file email**.
- **Socle backend déjà écrit** (branche `feat/acquisition-sequences`) : objet `AcquisitionRun` + items + orchestrateur stateless + gates + pause/reprise. **Conservé et adapté.** Ce qui se refait : le **front** (le board d'observation → remplacé par le **tunnel** + une **liste/détail d'automatisations**), plus le **template par prospect**, la **politique d'envoi** et l'**étape de scraping** du full-auto.

---

## 1. Principes

1. **Semi-auto par défaut, full-auto en option.** Le full-auto ne s'active que quand la qualité des sites est fiable. Au début, Léo valide à la main.
2. **Garder la main = valider, corriger en route, stopper/reprendre.** On déplace le jugement humain vers les rares points qui comptent (valider les sites avant d'envoyer).
3. **Idempotent & reprenable.** L'automatisation **retient son étape** : on peut fermer, revenir, elle rouvre là où elle en était. Chaque prospect avance indépendamment ; un crash reprend sans rien perdre (état 100 % en base).
4. **Un prospect = une automatisation.** Verrou dur.
5. **Observable.** Statuts d'automatisation + récap par prospect (site + vrai mail).
6. **Réutilise l'existant.** Services unitaires (`enrichment_service`, `demo_site_service`, `campaign_service`, `CampaignQueueService`, `scraping_job_service`), file email, orchestrateur de fond.

---

## 2. Le concept : une « Automatisation »

Un **lot nommé** (souvent « Plombiers – Rennes », « Électriciens – Iffendic ») qui va de la **cible** à la **vente**. Deux façons de le définir :

- **Par sélection** (surtout semi-auto) : on part de prospects existants qu'on coche.
- **Par requête** (surtout full-auto) : on part d'un **métier + une ville** (plusieurs possibles) et d'un **objectif en jours**.

C'est un objet de premier ordre, réutilisant l'objet `AcquisitionRun` déjà en base.

---

## 3. Le tunnel (le cœur)

| Étape | Semi-auto (on marche) | Full-auto (s'auto-avance) |
|---|---|---|
| **1 · Cible** | Filtrer/sélectionner des prospects (villes, métier, avec/sans site, avec/sans email, non-utilisés…) ; **lancer une recherche** si on manque de monde. | **Métier(s) + ville(s) + objectif en jours.** Pioche les prospects **non-utilisés** correspondants, puis **scrape le complément**. |
| **2 · Templates** | Un template pour tous **et/ou** un template **par prospect**. | Un template pour tous (bulk). |
| **3 · Génération** | Enrichit (les non-enrichis) **puis** crée les sites. Progression live, reprenable. | Idem, en fond. |
| **4 · Validation** | **Gate humaine** : récap site par site, corrections, « valider l'ensemble ». | **Auto-validée** — mais les sites douteux sont **flaggés « à vérifier »**. |
| **5 · Emails** | Modèles A/B + **preview du vrai mail**. | Modèles A/B **choisis d'avance**. |
| **6 · Envoi** | Alimente la file, cadencée par la **politique d'envoi**. | Idem, en fond. |

**Full-auto, concrètement** : on choisit métier(s) + ville(s) + objectif → suivant → template (une pour tous) → modèles d'email → **Lancer**. Ensuite la machine déroule seule (pioche/scrape → enrichit → génère → auto-valide → envoie) et l'écran devient une **vue de progression**. On ne peut pas automatiser plus que ça sans perdre la main sur la qualité.

**Semi-auto** : les mêmes étapes, mais on clique « suivant » soi-même et on s'arrête à la Validation.

---

## 4. La cible « en jours » (full-auto)

Plutôt qu'un nombre de prospects chiffré, le full-auto se règle en **nombre de jours de démarchage visés** — parce que la **politique d'envoi** fixe déjà le débit.

> Exemple : politique = **20 mails/jour**, lun–ven, 7h–18h. Objectif full-auto = **« 10 jours »** → ~**200 prospects** à réunir. La machine consomme d'abord les **non-utilisés** du métier+ville, puis **scrape le complément** jusqu'à la cible.

C'est un **objectif, pas une garantie** : si le scraping s'épuise avant, l'automatisation **coupe avant les 10 jours** et **prévient** (elle n'invente rien). La cible temporelle lie proprement l'automatisation à la cadence réelle d'envoi.

---

## 5. Paramètres → Envoi (politique d'envoi globale)

Nouvelle section de réglages, **globale par utilisateur**, qui gouverne **toute la file email** (le tunnel **et** les campagnes manuelles existantes) :

- **Plafond/jour** (défaut **20** — anti-spam).
- **Jours d'envoi** (défaut **lun→ven**).
- **Fenêtre horaire** (défaut **7h→18h**).
- **Espacement** entre deux mails (défaut **20 min**).

> ⚙️ **Vrai chantier backend** : le worker actuel (`email_queue_worker` / `CampaignQueueService`) espace les envois mais **ignore jours et heures**. Il faut lui apprendre la **fenêtre** + le **quota/jour**. Bénéfice transverse : ça fiabilise aussi les campagnes classiques.

---

## 6. La liste des Automatisations + le détail

**≠ la liste des campagnes email.** C'est **la liste des automatisations**, chacune avec un **statut** :

`brouillon` · `en cours` · **`à valider`** · `validée` · `en campagne` · `terminée` · `en pause` · `arrêtée` · `échec`
*(en full-auto, `à valider` est franchi automatiquement).*

- **Clic sur une automatisation → la liste de ses prospects.**
- **Clic sur un prospect → un récap** : le **site généré** (aperçu + lien Storyblok + indicateur « vendable ? »), **le vrai mail** qui sera/a été envoyé (rendu avec le lien démo réel), son **statut**.
- **Bouton « valider l'ensemble »** (= la gate de validation).
- **Notifications** : **in-app** (badge sur « Automatisations » + statut dans la liste) **+ email** (`leo@dibodev.fr`) quand une automatisation atteint une gate ou se termine — utile pour le full-auto qu'on laisse tourner.

---

## 7. Corriger en cours de route (le cœur du semi-auto)

À l'étape Validation, pour **chaque site** :

- **Aperçu** du site (iframe démo — le `DemoSitePreviewFrame` existe déjà).
- **« Ouvrir dans Storyblok »** pour le **contenu** (texte/médias) — on a déjà l'URL éditeur + identifiants du client sur le `DemoSite`. **Pas d'éditeur maison** : on ne réimplémente pas un CMS, le client éditera de toute façon dans Storyblok.
- **Changer de template & régénérer** — pour **1, plusieurs ou tous** les prospects (même space Storyblok, re-provisionné).
- **Ré-enrichir** (re-scanner Google/OSM).
- **Exclure** le prospect de l'automatisation.

**Score de « vendabilité »** par site (nb de champs enrichis remplis, photo héro, tel, avis…) → on **remonte en rouge** les sites à risque en haut de la liste, pour ne pas relire 40 sites à l'œil. Vaut aussi en full-auto (les douteux flaggés).

---

## 8. Garde-fous

- **1 prospect = 1 automatisation** (verrou dur ; un prospect « pris » n'est plus piochable).
- **Scrape fragile (full-auto)** : s'arrête et **prévient** si le scrape rend trop peu ; **flag « à vérifier »** les sites sous-remplis même en full-auto.
- **Anti-spam / délivrabilité** : la **politique d'envoi** (fenêtre + jours + quota/jour + espacement) ; exclusion des désinscrits + des prospects réservés par un autre membre d'org.
- **Crédits** : admin = illimité (rien affiché) ; user = borné par son **solde** (pas de génération à 0). **Plus de cap crédits dans le tunnel** — inutile.
- **RGPD** : hérité du cadrage global ; l'automatisation ne contourne pas le consentement.
- **Réversibilité** : pause / annuler à tout moment, **non destructif** (prospects, enrichissements et sites déjà créés restent).
- **Org** : respecte visibilité + réservation des prospects.

---

## 9. Modèle de données (évolution du socle existant)

**`AcquisitionRun`** (existe) — ajouts/évolutions :
- `mode` (`semi_auto` | `full_auto`) — existe.
- **Cible par requête** (full-auto) : `search_metiers` (liste), `search_villes` (liste), **`target_days`** (objectif en jours).
- Défauts d'étapes : `template_id` (template par défaut), `email_template_id_a/b` — existent.
- **Retirés** : `max_credits`, `daily_email_cap` → déplacés dans la **politique d'envoi**.
- Suivi : `status`, `review_approved_at`, `campaign_id`, `stats` — existent.

**`AcquisitionRunItem`** (existe) — ajout :
- **`template_id`** (template **par prospect**, hérite du défaut du run).
- `step`, `step_reason`, `demo_site_id`, `last_error`, `attempts` — existent.
- (Score de vendabilité : calculé à la lecture, ou stocké si on veut trier côté SQL.)

**`SendPolicy`** (nouveau, 1 par user) : `daily_cap`, `days_of_week`, `window_start_hour`, `window_end_hour`, `spacing_minutes`.

---

## 10. L'orchestrateur (évolution)

Même worker asyncio stateless (`run_acquisition_loop`, greffé au boot comme `run_queue_worker`), machine à états par item. Ajouts :

- **T0 — Cible full-auto** *(nouveau)* : consomme les prospects **non-utilisés** du/des métier(s)+ville(s), puis **lance le scraping** pour compléter jusqu'à `target_days × daily_cap`. Crée un item par prospect. S'arrête + notifie si le scrape s'épuise.
- **T1 — Enrichir → T2 — Générer** : réutilisent `enrichment_service` / `demo_site_service`, mais **avec le `template_id` de l'item** (per-prospect).
- **Gate Validation** : semi-auto = `awaiting_review` (l'humain valide) ; full-auto = auto-validée, flags de vendabilité posés.
- **T3 — Envoi** : crée/lance la campagne A/B et **alimente la file**, désormais **cadencée par la `SendPolicy`** (fenêtre + quota/jour).
- **Relance & vente** : inchangées (worker de relance + webhook Stripe) ; l'automatisation reflète l'état (`won` dérivé des Orders).

---

## 11. Ce qui existe déjà vs. ce qui change

**Déjà en place (branche `feat/acquisition-sequences`)** : `AcquisitionRun`/`AcquisitionRunItem` + migration, orchestrateur + service + routes CRUD (create/list/detail/pause/resume/cancel/approve/reject), gates.

**À faire / à refaire** :
1. **Front — le tunnel** (remplace « Créer un site ») : les 6 étapes, semi & full-auto.
2. **Front — liste/détail d'automatisations** (remplace le board) : statuts, récap par prospect (site + vrai mail), « valider l'ensemble », corrections en route.
3. **Paramètres → Envoi** + apprentissage de la fenêtre/quota au worker email.
4. **Template par prospect** (`AcquisitionRunItem.template_id`) + actions « changer template & régénérer / ré-enrichir / exclure ».
5. **Full-auto T0** : cible métier+ville+jours, consommation des non-utilisés + scraping de complément + garde-fous.
6. **Score de vendabilité** + flags.
7. **Notifications** in-app + email.
8. **Retrait** de « Créer un site » et du nommage « Séquences ».

---

## 12. Plan par phases

**Phase 0 — Fondations** : `SendPolicy` (Paramètres → Envoi) + apprentissage fenêtre/quota au worker ; verrou « 1 prospect = 1 automatisation » ; `template_id` par item.

**Phase 1 — Le tunnel semi-auto** *(remplace « Créer un site », gros ROI)* : les 6 étapes avec gates, la liste/détail d'automatisations, la Validation (récap par site + corrections Storyblok/in-app + score de vendabilité), la preview email, l'envoi cadencé. → « je sélectionne mes prospects, la machine enrichit + génère + je valide + ça démarche ».

**Phase 2 — Full-auto** : cible métier+ville+jours, T0 (consommation des non-utilisés + scraping de complément), auto-avance + auto-validation avec flags, garde-fous scrape. → « métier + ville + 10 jours → la machine fait tout ».

**Phase 3 — Affinages** : notifications email, planification récurrente (« chaque lundi, une nouvelle ville »), scoring de priorisation, score de vendabilité affiné.

---

## 13. Pourquoi ça transforme l'outil

Aujourd'hui DevLeadHunter **outille** chaque étape ; demain il **exécute** la chaîne. Le temps de Léo passe de « cliquer entre chaque page pour 40 prospects » à « définir une intention + valider les sites » — et, en full-auto, à « définir un métier, une ville, un nombre de jours ». C'est le passage de l'**outil** à l'**agent**, et le tunnel unique (qui remplace « Créer un site ») en fait la **colonne vertébrale** du produit plutôt qu'une fonctionnalité de plus.
