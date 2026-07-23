# Plan de migration du stockage vers Cloudflare R2

> **Statut** : ✅ **IMPLÉMENTÉ** (phases 1 → 6 + 8). Vérifié en local contre les vrais buckets R2.
> Reste à valider en production : une génération vidéo complète de bout en bout et
> l'affichage de la vignette dans un vrai email (cf. §7).
> **Objectif** : sortir tout le stockage de fichiers (vidéos de prospection, vignettes, clip webcam
> presenter, pièces jointes support) du **disque du VPS** et du **FTP**, vers **Cloudflare R2**.
> **Même fonctionnement en local et en production** (aucun backend conditionnel).

---

## 0. Pourquoi (contexte)

Trois problèmes du stockage actuel sur disque VPS :

1. 🚨 **Le déploiement efface les fichiers.** `.github/workflows/deploy-api.yml` fait
   `sudo rm -rf "$TARGET_DIR/api"` puis re-upload les sources. Or `demo_video_dir` vaut
   `uploads/demo-videos` (**relatif**, donc `…/html/api/uploads/…`) → **chaque déploiement de l'API
   supprime toutes les vidéos générées et les clips presenter**. Comme `has_ready_video()` teste la
   présence du fichier sur disque, la DB dit « ready » mais la route renvoie 404, la page `/v/{slug}`
   redirige vers la démo, et la file email saute les templates `{vignette_video}`.
2. **Saturation disque + zéro redondance** : un seul disque, pas de backup.
3. **Bande passante** : le VPS sert les vidéos en concurrence avec l'API.

### Pourquoi R2 (et pas Supabase / O2switch)

| | Supabase Free | O2switch (FTPS) | **Cloudflare R2 Free** |
|---|---|---|---|
| Stockage | 1 Go ❌ | « illimité » (fair use) | **10 Go** ✅ |
| Egress | ~5 Go/mois ❌ | fair use → risque throttle | **gratuit, illimité** ✅ |
| Taille max fichier | 50 Mo ❌ | — | ~5 To |
| Durabilité | OK | **aucune redondance** ❌ | redondance objet ✅ |
| Protocole | client Supabase | FTPS (non atomique, fragile) | **S3 / boto3** ✅ |
| Risque CGU | — | **réel** (mutualisé ≠ CDN média) | nul |

**Besoin réel estimé** : 20 prospects/j × 5 j = 100 vidéos/semaine, TTL 14 j → ~**200 vidéos
simultanées** × ~12 Mo ≈ **2,5 Go en régime permanent** → tient dans les 10 Go gratuits avec 4× de marge.
Supabase Free (1 Go) était insuffisant ; R2 est gratuit à ce volume.

---

## 1. État des lieux du code (avant migration)

| Élément | Où | Aujourd'hui |
|---|---|---|
| Vidéos générées + vignettes | `services/demo_video_service.py` | disque : `{demo_video_dir}/{slug}.mp4` et `.jpg` |
| Clip webcam presenter | `services/presenter_video_service.py` | disque : `{presenter_video_dir}/…`, chemin en base (`presenter_video.file_path`) |
| Pièces jointes support | `services/support_storage_service.py` | **double backend `"local" \| "ftp"`** (FTPS en prod, disque en dev) |
| Génération | `demo_video_service.py` | Playwright (capture site) + ffmpeg (montage) — lourd, 1 rendu à la fois |
| Service d'URL | `demo_video_service.py` | `video_page_url`, `public_video_file_url`, `public_thumbnail_url` |
| Routes publiques | `api/v1/routes/demo_sites.py` | `GET /public/{slug}/video.mp4` + `/video-thumbnail.jpg` → `FileResponse` (Range-aware) |
| Page lecteur | `demo-host/app/pages/v/[slug].vue` | `videoSrc`/`posterSrc` pointent l'API |
| Cleanup TTL | `services/demo_site_cleanup_service.py` | supprime les démos expirées + `delete_files_for_slug()` |
| Sync DB prod→local | `web/src-tauri/src/db_sync.rs` + `DevLeadHunterDevToolbar.vue` | **commande Tauri Rust** `sync_dev_database_from_prod`, credentials dans `.env.sync` |

**Bonne nouvelle** : le code est bien abstrait (helpers de chemins/URLs centralisés) → la bascule est
**localisée**, pas une refonte.

---

## 2. Configuration

### 2.1 Buckets (déjà créés par Léo)

- `devleadhunter-dev`
- `devleadhunter-prod`

### 2.2 Variables d'environnement

Déjà présentes dans `api/.env`, `api/.env.example` et les secrets GitHub :

```env
R2_ACCOUNT_ID=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_ENDPOINT=            # https://<account_id>.r2.cloudflarestorage.com  (ÉCRITURE only)
R2_BUCKET_DEV=devleadhunter-dev
R2_BUCKET_PROD=devleadhunter-prod
```

**⚠️ À AJOUTER (bloquant)** — l'endpoint S3 sert à écrire, **pas** à faire lire la vidéo par le prospect :

```env
R2_PUBLIC_BASE_URL_DEV=https://pub-xxxxx.r2.dev     # URL r2.dev du bucket dev (trafic local, rate limit sans importance)
R2_PUBLIC_BASE_URL_PROD=https://files.dibodev.fr    # domaine perso sur le bucket prod
```

**Résolution selon l'environnement** (dans `core/config.py`, propriétés calculées) :
- `ENV=development` → `r2_bucket = R2_BUCKET_DEV`, `r2_public_base_url = R2_PUBLIC_BASE_URL_DEV`
- `ENV=production` → `r2_bucket = R2_BUCKET_PROD`, `r2_public_base_url = R2_PUBLIC_BASE_URL_PROD`
- Les **deux** buckets restent lisibles car la **sync dev lit le bucket prod**.

### 2.3 Domaine public `files.dibodev.fr` (sans migrer toute la zone)

R2 exige que la zone soit chez Cloudflare, mais on ne délègue **que le sous-domaine** :

1. Cloudflare → **Add a site** → saisir **`files.dibodev.fr`** (zone de sous-domaine, **pas** `dibodev.fr`).
2. Cloudflare fournit **2 nameservers**.
3. Chez le DNS actuel de `dibodev.fr` : ajouter des enregistrements **`NS`** sur l'hôte `files` → ces 2 nameservers.
4. Zone active → R2 → bucket **prod** → Settings → **Custom domain** → `files.dibodev.fr` (certificat auto).

→ La zone `dibodev.fr` (site + apps) **ne bouge pas**. ⚠️ Vérifier à l'étape 1 que le plan Cloudflare
accepte la zone de sous-domaine.

### 2.4 Lifecycle rule (filet de sécurité)

Créer côté Cloudflare une règle de **suppression automatique après 14 jours** sur `videos/websites/`
et `images/websites/`. Même si le cleanup applicatif échoue, R2 purge tout seul.
**Ne pas l'appliquer** à `videos/presenter/` (le clip doit être permanent) ni à `images/support/`.

---

## 3. Arborescence du bucket

Pensée **évolutive** : le module « sites web » est le premier de trois (cf. `/devleadhunter` :
wallet Apple, missions freelance à venir).

```
devleadhunter-{dev|prod}/
├── videos/
│   ├── websites/{slug}.mp4              ← vidéo de prospection générée
│   └── presenter/{user_id}.mp4          ← clip webcam source (permanent, par user)
└── images/
    ├── websites/{slug}.jpg              ← vignette email ({vignette_video})
    └── support/{yyyy}/{mm}/{uuid}.{ext} ← pièces jointes tickets support
```

**⚠️ Clé = `{slug}`, PAS `{prospect_id}`** : un prospect peut avoir **plusieurs demo sites**
(`behavior_service._slugs_for_prospect()` itère déjà sur une liste). Le `slug` est l'identifiant
unique et déjà public dans les URLs.

Futur module → `videos/wallet/…`, `images/wallet/…`.

---

## 4. Phases d'implémentation

### Phase 1 — Socle R2

- `api/requirements.txt` : **+ `boto3`**.
- `api/core/config.py` : les 8 settings R2 + propriétés `r2_bucket` / `r2_public_base_url` résolues selon `ENV`.
- **Nouveau** `api/services/r2_storage_service.py` — calqué sur le pattern éprouvé de FitDex
  (`api/services/supabase_storage_service.py` dans le repo FitDex) :
  - client **boto3 singleton** (`_client`), `endpoint_url=R2_ENDPOINT`, `region_name="auto"`,
    signature v4 ;
  - `is_configured()` / `require_configured()` (guards, comme FitDex) ;
  - `upload_file(local_path, key, content_type=None)` / `upload_bytes(key, data, content_type)` ;
  - `download_to_path(key, local_path)` (nécessaire pour ffmpeg) ;
  - `delete(key)` / `delete_many(keys)` ;
  - `exists(key)` (`head_object`, gérer `404`) ;
  - `list_objects(prefix)` → `[{key, size, last_modified, etag}]` avec **pagination** (`list_objects_v2`
    + `ContinuationToken`) ;
  - `public_url(key)` → `f"{r2_public_base_url}/{key}"` ;
  - `copy_from_bucket(src_bucket, key)` → **CopyObject serveur-à-serveur** (pour la sync).
- **Helpers de clés** (un seul endroit qui connaît l'arborescence) :
  `website_video_key(slug)`, `website_thumbnail_key(slug)`, `presenter_key(user_id)`,
  `support_key(ext)` (avec `{yyyy}/{mm}/{uuid}`).
- Toutes les I/O boto3 sont **bloquantes** → les appeler via `asyncio.to_thread(...)` depuis du code
  async (comme FitDex le fait pour l'upload).

### Phase 2 — Vidéos de prospection

`api/services/demo_video_service.py` :
- La génération continue d'écrire en **temp local** (ffmpeg a besoin d'un vrai fichier), puis :
  **upload `.mp4` + `.jpg` sur R2** → **nettoyage du temp**.
- `has_ready_video(site)` : ne teste plus le disque. → statut DB `READY` (+ `exists()` R2 si on veut
  être strict, mais attention au coût d'un `head_object` par appel — préférer le statut DB).
- `video_file_path()` / `thumbnail_file_path()` → deviennent des **clés R2** (ou disparaissent).
- `public_video_file_url(slug)` / `public_thumbnail_url(slug)` → `r2.public_url(key)`.
- `delete_files_for_slug(slug)` → `r2.delete_many([video_key, thumb_key])`.

`api/api/v1/routes/demo_sites.py` :
- `GET /public/{slug}/video.mp4` et `/video-thumbnail.jpg` → **`RedirectResponse` 302 vers l'URL R2**.
  ⚠️ **Ne pas supprimer ces routes** : les emails **déjà envoyés** embarquent ces URLs (la vignette
  `{vignette_video}` pointe l'API). Le 302 garantit la compat.
- Exposer `video_url` + `thumbnail_url` dans `DemoSitePublicResponse` (schéma `schemas/demo_site.py`).

`demo-host/app/pages/v/[slug].vue` :
- `videoSrc` / `posterSrc` ← lus depuis le payload public (URLs R2) au lieu d'être construits sur `apiBase`.
- → **le VPS ne sert plus un seul octet de vidéo**.

`api/services/demo_site_cleanup_service.py` :
- La purge TTL supprime aussi les objets R2 (elle appelle déjà `delete_files_for_slug`).

**Range requests** : R2 les gère nativement (comme le faisait `FileResponse`) → le seek dans le
lecteur continue de fonctionner.

### Phase 3 — Clip webcam presenter

`api/services/presenter_video_service.py` :
- À l'upload : accepter toujours jusqu'à `PRESENTER_VIDEO_MAX_MB` (300) **dans la requête**, puis
  **normaliser avec ffmpeg** avant de stocker :
  - même résolution que le canvas de montage (**1280×720**), fps 30, `libx264` **CRF 20-21**,
    `aac 128k`, `+faststart` ;
  - bénéfices : source homogène → **génération plus rapide et plus fiable**, stockage réduit
    (~5-15 Mo au lieu de 300), et **aucune perte visible** puisque le montage downscale de toute
    façon en 720p (et 260×260 pour la pastille).
- Upload vers `videos/presenter/{user_id}.mp4`.
- Le modèle `models/presenter_video.py` stocke désormais la **clé R2** (plus un chemin disque)
  → **migration DB** dans `api/migrations/` (renommer/re-sémantiser `file_path`, idempotente comme
  les autres migrations).
- `demo_video_service` : **télécharger le clip en temp** (`download_to_path`) avant le montage,
  nettoyer après. Le code qui faisait `Path(presenter.file_path).is_file()` doit être adapté.

### Phase 4 — Support (suppression totale du FTP)

- `api/services/support_storage_service.py` : **réécrit sur R2**, backend **unique** (plus de
  `backend: "local" | "ftp"`, plus de `_save_locally`, plus de `ftplib`).
- Supprimer les settings `SUPPORT_FTP_*` (`core/config.py`) et `support_local_upload_dir`.
- Retirer les secrets `SUPPORT_FTP_*` du workflow de déploiement.
- **Aucune migration** des pièces jointes existantes : validé avec Léo (2 images de test, déjà
  cassées en prod).

### Phase 5 — Page admin « Stockage » (admin-only)

**API** (`api/api/v1/routes/admin_storage.py` ou dans un routeur admin existant) :
- `GET /admin/storage` → liste : `key`, `type` (vidéo/vignette/presenter/support), `size`,
  `created_at`, **`expires_in_days`**, `public_url`. Filtrable par préfixe. Croisée avec la DB pour
  afficher le **nom du prospect**.
- `DELETE /admin/storage/{key}` → suppression manuelle (confirmation côté UI).
- `POST /admin/storage/purge-expired` → purge manuelle des objets au-delà du TTL.
- `GET /admin/storage/health` → **incohérences** : objets R2 sans enregistrement DB (orphelins) et
  DB `READY` sans objet R2 (fichiers manquants). C'est ce qui donne la **certitude que la suppression
  à 14 j fonctionne**.

**Front** (`web/app/pages/dashboard/admin/storage.vue`) :
- Tableau + filtres par type/préfixe, **lecteur vidéo inline**, **copier le lien**, suppression
  confirmée (`UiConfirmModal`), **badge « expire dans X j »**, section « incohérences ».
- Admin-only (rôle `UserRole.ADMIN`, comme la page crédits).
- Disponible dans l'app desktop puisque c'est le même dashboard Nuxt sous Tauri.

### Phase 6 — Sync bucket prod → dev

- `POST /admin/storage/sync-from-prod` — **dev uniquement**, **garde stricte** : refuser si
  `settings.is_production`.
- Algorithme **incrémental** (jamais de wipe) :
  1. `list_objects` sur le bucket **prod** et sur le bucket **dev** ;
  2. diff par clé :
     - présent prod / absent dev → **`copy_from_bucket`** (CopyObject **serveur-à-serveur**, rien ne
       transite par l'API) ;
     - absent prod / présent dev → **supprimer en dev** ;
     - présent des deux côtés → comparer **ETag/taille**, ne rien faire si identique (cas normal :
       les vidéos sont immuables) ;
  3. retourner un rapport `{copied, deleted, unchanged}`.
- Coût : le listing est en Class B (10 M gratuites/mois) → négligeable.
- **Branchement UI** : le bouton existant `DevLeadHunterDevToolbar.vue` **enchaîne**
  `syncDevDatabaseFromProd()` (Tauri/Rust) **puis** un appel à cet endpoint, avec **un seul toast**
  récapitulatif (« DB synchronisée · 5 fichiers copiés, 1 supprimé »).
  ⚠️ Ne **pas** implémenter le S3 en Rust : boto3 côté Python, le bouton orchestre.
- Les credentials R2 étant déjà dans `api/.env`, **rien à ajouter dans `.env.sync`**.

### Phase 8 — Déploiement

- `.github/workflows/deploy-api.yml` : ajouter les `R2_*` (dont les 2 `R2_PUBLIC_BASE_URL_*`) au bloc
  qui génère le `.env`, **retirer les `SUPPORT_FTP_*`**.
- `api/.env.example` aligné.
- Créer la **lifecycle rule 14 j** côté Cloudflare (cf. §2.4).
- ✅ Effet de bord bienvenu : le `rm -rf` du déploiement ne peut plus rien détruire, les fichiers ne
  sont plus sur le VPS.

---

## 5. Décisions ÉCARTÉES (ne pas rouvrir sans raison)

### ❌ Phase 7 « Qualité » (1080p et/ou 60 fps) — abandonnée

- **60 fps impossible simplement** : le défilement du site est capturé par **Playwright
  `record_video`**, qui enregistre à **~25 fps** et **n'expose aucune option de fps**. Le filtre
  ffmpeg force déjà `fps=30` → des frames sont **déjà dupliquées**. Passer à 60 ne ferait que
  dupliquer davantage : fichier plus lourd, **zéro fluidité gagnée**. Du vrai 60 fps imposerait de
  remplacer toute la capture (CDP screencast / screenshots frame-par-frame) → gros chantier.
- **1080p inutile** : Léo a acté qu'on **ne passe pas Playwright en 1080p**. Or la capture du site
  occupe **~23 s sur 32 s** (le contenu principal). Monter le canvas en 1080p **upscalerait** cette
  portion (plus floue qu'aujourd'hui) pour un fichier ~2× plus lourd. Aucun gain réel.
- **Décision** : on **reste en 1280×720 / 30 fps / CRF 22**. Cohérent, ~12 Mo/vidéo, génération
  rapide, chargement rapide en 4G chez le prospect.
- *(Levier gratuit si on veut plus de fluidité perçue un jour : **ralentir le scroll**, pas monter le fps.)*

### ❌ Une 2ᵉ API déployée sur O2switch — abandonnée

L'idée initiale (API Python sur O2switch gérant upload/TTL/listing) dupliquerait auth, déploiement,
monitoring, et **couperait la source de vérité en deux** (métadonnées en base VPS *et* sur O2switch).
Tout existe déjà : métadonnées dans `demo_sites`, TTL dans `demo_site_cleanup_service`, endpoints
dans l'API FastAPI, UI dans le dashboard. **Le stockage doit rester un seau bête.**

### ❌ Supabase — abandonné

1 Go de stockage et ~5 Go d'egress sur le plan Free → insuffisant dès la montée en charge
(2,5 Go en régime permanent). Le plan Pro (25 $/mois) était la seule option ; R2 fait le job gratuitement.

---

## 6. Prérequis avant de coder

- [ ] Ajouter `R2_PUBLIC_BASE_URL_DEV` et `R2_PUBLIC_BASE_URL_PROD` (`.env`, `.env.example`, secrets GitHub)
- [ ] Déléguer `files.dibodev.fr` à Cloudflare (§2.3) et l'attacher au bucket **prod**
- [ ] Activer l'URL `r2.dev` du bucket **dev**
- [ ] (Optionnel mais recommandé) Créer la lifecycle rule 14 j

---

## 7. Checklist de vérification (après implémentation)

- [ ] Upload d'un clip presenter → objet présent dans `videos/presenter/`, **taille réduite** par la
      normalisation ffmpeg, lecture OK dans la page de config
- [ ] Génération d'une vidéo → `.mp4` + `.jpg` dans `videos/websites/` et `images/websites/`,
      **temp local nettoyé**, aucun fichier écrit dans `uploads/`
- [ ] Page `/v/{slug}` : la vidéo se lit depuis **R2** (vérifier l'URL dans l'onglet réseau), le
      **seek fonctionne** (réponses `206 Partial Content`)
- [ ] `{vignette_video}` dans un email de test → l'image charge depuis R2
- [ ] Anciennes URLs API `/public/{slug}/video.mp4` → **302** vers R2
- [ ] Pièce jointe support → objet dans `images/support/{yyyy}/{mm}/`, plus **aucun** appel FTP
- [ ] `grep -rniE "ftp" api/` → **plus aucune** occurrence fonctionnelle
- [ ] Purge TTL → objets supprimés de R2 ; `GET /admin/storage/health` ne remonte pas d'orphelin
- [ ] Sync prod → dev : 2ᵉ exécution consécutive = **0 copie, 0 suppression** (idempotence)
- [ ] Sync refusée si `ENV=production`
- [ ] Déploiement API → les vidéos **survivent** (le bug historique est corrigé)
- [ ] `npm --prefix web run lint` vert · `pytest` vert
