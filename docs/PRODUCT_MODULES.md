# Modules produit — architecture

> Source de vérité de la séparation entre le cœur DevLeadHunter (module **Sites web**) et les modules produit
> optionnels, chacun dans son dépôt de l'organisation GitHub `DevLeadHunter`.

| Module | Clé (stockée en base) | Dépôt | Par défaut |
| --- | --- | --- | --- |
| Sites web (le cœur) | `websites` | `DevLeadHunter/devleadhunter` | toujours actif |
| Réceptionniste IA | `ai-assistant` | `DevLeadHunter/devleadhunter-module-receptionist` | activé |
| Cartes Apple Wallet | `apple-wallet` | `DevLeadHunter/devleadhunter-module-apple-wallet` | désactivé |
| Entretien de sites | `site-care` | `DevLeadHunter/devleadhunter-module-site-care` | désactivé |

La clé `ai-assistant` est historique (déjà écrite dans `prospects.contacted_by_module`, `presenter_videos.module`) :
elle ne change pas.

## Installé ≠ activé

- **Installé** : le dépôt du module est récupéré au déploiement, à la version épinglée dans
  [`product-modules.json`](../product-modules.json). L'API installe le paquet Python `api/` du module, `web/` et
  `demo-host/` étendent ses layers Nuxt.
- **Activé** : interrupteur du super admin, page **Paramètres → Administration → Modules**
  (`/dashboard/admin/modules`), stocké dans la table `product_modules` (`module_key`, `is_enabled`).
  Module coupé : ses routes API répondent 404, ses tâches de fond s'arrêtent (≤ 30 s), il disparaît du sélecteur de
  module, et la file d'envoi saute tout message qui utilise une de ses variables (raison « Module « X » désactivé »).
  Les webhooks Stripe du module restent traités (la facturation suit Stripe quoi qu'il arrive).

Le cœur ne doit **jamais** importer un module : il le découvre et l'appelle par le contrat. Un module qui plante au
chargement est écarté (raison visible sur la page Modules) et le cœur tourne sans lui.

## API — le contrat

- `api/core/product_modules/contract.py` : `ProductModule` (clé, libellé, routers, tâches de fond, migrations, seed,
  bibliothèque d'emails, webhooks Stripe, balises des pages démo, slugs, stockage, sidecar desktop…).
- `api/core/product_modules/campaign_offer.py` : `CampaignOffer`, ce qu'un module vend par les campagnes
  (variables email/SMS, gardes, valeurs, modèles SMS).
- `api/core/product_modules/registry.py` : découverte par entry point `devleadhunter.product_modules`.
- `api/services/product_module_service.py` : interrupteurs ; `api/services/campaign_offers.py` : les offres vues par
  le moteur de campagnes ; `api/services/product_module_loop_supervisor.py` : tâches de fond.

Un module déclare, dans le `pyproject.toml` de son dossier `api/` :

```toml
[project.entry-points."devleadhunter.product_modules"]
ai-assistant = "devleadhunter_receptionist.module:ReceptionistModule"
```

Son code importe le cœur par ses noms habituels (`from models.prospect_db import ProspectDB`, `from core.database
import Base`…) : il tourne toujours avec la racine `api/` du cœur dans le `sys.path`.

### Routes HTTP du cœur liées aux modules

- `GET /api/v1/product-modules` (tout utilisateur connecté) →
  `[{ "key": "ai-assistant", "label": "Réceptionniste IA", "has_email_templates": true, "has_sms_templates": true }]`
  : les modules installés **et** activés (le module Sites web n'y figure pas, il est toujours là).
  `has_email_templates` : l'offre du module apporte des variables qu'un modèle d'email peut utiliser ;
  `has_sms_templates` : elle ajoute au moins un modèle à la bibliothèque de SMS. Un module qui écrit ses messages
  lui-même (Entretien de sites, Missions) renvoie `false` aux deux.
- `GET /api/v1/admin/product-modules` (super admin) → `[{ key, label, description, is_installed, is_enabled,
  is_switchable, load_error, updated_at }]` : Sites web en premier (non commutable), puis les modules installés,
  puis les interrupteurs d'un module non installé.
- `PATCH /api/v1/admin/product-modules/{key}` (super admin), corps `{ "is_enabled": true }` → la ligne mise à jour ;
  400 pour `websites`, 404 pour un module non installé.

### Contrats qui changent pour le dashboard

- Lancement / reprise / remplissage d'une campagne (`CampaignEnqueueOutcome`, réponse de `launch` et `resume`) : les
  champs `skipped_no_assistant` et `skipped_no_loyalty_card_demo` disparaissent, remplacés par
  `skipped_without_offer: [{ module_key, module_label, prospects: [{ id, name }] }]`. Le message texte reste
  construit par l'API.
- `GET/PATCH /api/v1/auth/me` et `/users` : plus de `assistant_monthly_price_cents` ni
  `assistant_annual_free_months`. Le prix de la réceptionniste se lit et s'écrit sur
  `GET/PUT /api/v1/ai-assistants/pricing` → `{ monthly_price_cents, annual_free_months }`.
- Modèles SMS (`GET /sms/templates`) : `module` vaut la clé du module vendu (`websites`, `ai-assistant`,
  `apple-wallet`).
- Modèles d'email (`GET /email-templates` et chaque réponse qui renvoie un modèle) : `module` vaut la clé du module
  que le modèle vend, lue dans ses variables comme une campagne la lit (`{lien_assistant}` → `ai-assistant`, aucune
  variable de module → `websites`). Rien n'est stocké : changer le texte d'un modèle peut le changer de module.
- Les routes de la réceptionniste gardent leurs chemins (`/ai-assistants/…`, `/public/{slug}/…`, `/client/{token}/…`).

## Web et demo-host — layers Nuxt

`web/nuxt.config.ts` et `demo-host/nuxt.config.ts` étendent `productModuleLayers('web' | 'demo-host')`
([`product-modules.mjs`](../product-modules.mjs)) : `github:<dépôt>/<app>#<tag>` en prod, le clone local quand
`DLH_PRODUCT_MODULES_DIR` pointe sur le dossier des clones.

Dans un layer, `~/` désigne l'application hôte (le cœur) : les imports vers le cœur restent en `~/…`, les imports
entre fichiers du module passent en **relatif**. Chaque layer déclare ses propres dossiers de composants (mêmes
préfixes que le cœur : `ui/` donne `Ui…`, le reste sans préfixe) et un plugin qui inscrit le module dans les registres
du cœur. Jamais de fichier de layer au même chemin qu'un fichier du cœur : l'un masque l'autre.

`DLH_PRODUCT_MODULES_DISABLED=1` construit une application sans aucun layer, le cœur seul : c'est la preuve que le
cœur ne dépend d'aucun fichier de module.

### Ce que le dashboard montre du module ouvert

Un module ne déclare que son menu (`navGroups`, `home`, `primaryCta`, `settingsLinks`) ; le cœur en déduit le reste
(`web/app/utils/moduleNavigation.ts`, `web/app/composables/useModuleNavigation.ts`, `useSettingsNav.ts`).

- **Menu de gauche** : le menu du module, sans le lien vers `/dashboard`, qui est le tableau de bord des Sites web.
  Avec un autre module ouvert, `/dashboard` mène à l'accueil de ce module (middleware `websites-dashboard`). Un
  module qui a son propre tableau de bord le met dans son menu, à sa propre adresse.
- **« Paramètres »** : les pages communes (envoi, santé email, compte, aide, administration) se voient partout. Une
  page du cœur qui porte `requiredModuleFeature` (`web/app/constants/settingsNav.ts`) ne se voit que dans les modules qui s'en
  servent : « Modèles d'email » (`has_email_templates`), « Relance SMS » (`has_sms_templates` ; hors Sites web elle
  s'appelle « Expéditeur SMS » et ne garde que le nom d'expéditeur), « Vidéo de prospection » (le module a une prise
  dans `PresenterVideoAdapterRegistry`). Une page inscrite par un module (`SettingsNavRegistry.register`) ne se voit
  que dans ce module. La page ouverte garde toujours son lien, quel que soit le module.
- **Pages filtrées** : « Modèles d'email » liste les modèles du module ouvert, « Vidéo de prospection » sa prise.
  Ouvertes par leur adresse dans un module qui ne s'en sert pas, elles montrent tout.
- **« Suivi des emails » et « Suivi des SMS »** : la liste, les chiffres et les réponses à traiter sont ceux du
  module ouvert (`?module_key=` sur `/emails/logs`, `/emails/stats`, `/emails/replies/pending`, `/sms/messages`,
  `/sms/stats`, `/sms/replies/pending`). Chaque envoi est rangé sous un module à sa création
  (`email_logs.module_key`, `sms_messages.module_key`), sans que le module ait à le dire : le cœur note quel module
  travaille à chaque entrée dans son code (`ModuleAtWork` : ses routes, ses boucles, ses événements Stripe, les
  balises de ses démos). Un email de campagne prend le module de sa campagne, une réponse celui de l'email
  d'origine, un email écrit à la main celui du module ouvert dans le dashboard. Un SMS prend le module de son
  modèle ; écrit à la main, celui dont il porte les liens (`owns_sms_message`), sinon celui du module ouvert. Le
  reste va aux Sites web. Un message laissé sur un site démo n'apparaît dans les réponses à traiter que dans les
  Sites web.
- **Création de campagne** (volet « Nouvelle campagne ») : les modèles d'email et de SMS proposés sont ceux du
  module ouvert ; un module sans modèles à lui les voit tous. Le tunnel d'automatisation, qui crée des sites démo, ne
  propose que les modèles des Sites web.
- **Palette Ctrl+K** : les pages listées sont celles du module ouvert (son menu, son bouton principal, ses réglages,
  puis les pages de « Paramètres » qu'il voit). Une action ou une recherche liée à une page (« Créer un site »,
  « Nouvelle campagne », recherche de prospects ou de campagnes) n'apparaît que si le module a cette page.
- **Barre du bas** (application installée) : au centre le `primaryCta` du module (aucun bouton sans `primaryCta`) ;
  autour, les pages du module (les liens de son menu sous `home`), puis « Notifications », puis les pages communes
  de prospection que son menu contient (Campagnes, Suivi des emails, Suivi des SMS, Mes prospects). Quatre onglets
  sur téléphone, six sur iPad, avec les compteurs du menu. Seule la barre des Sites web est écrite à la main
  (`web/app/constants/mobileTabBar.ts`).

## Déploiement

- **API (VPS)** : `api/scripts/product_module_requirements.py` écrit les lignes `pip`
  (`<paquet> @ git+https://github.com/<dépôt>@<tag>#subdirectory=api`) ; le VPS les installe après
  `api/requirements.txt`, avec `--force-reinstall --no-deps` (pip compare les versions, pas les tags). Les
  dépendances qu'un module déclare ne sont donc pas installées en prod : chacune doit aussi figurer dans
  `api/requirements.txt` du cœur (ex. `h2` pour les notifications APNs du Wallet). Les migrations du module passent
  avec celles du cœur (`schema_migrations`, par nom), après le `create_all` qui crée déjà ses tables.
- Côté npm, même règle : le `package.json` de l'application déclare ce que ses layers importent (`@dicebear/*` pour
  les démos de la réceptionniste, `qrcode` pour le Wallet) ; un layer `github:` n'installe pas ses dépendances.
- **Dashboard (OVH) et démos (Vercel)** : `nuxt prepare` et le build récupèrent les layers par giget, avec
  `GIGET_AUTH` (même jeton que pour les templates). `demo-host/vercel.json` redéploie aussi quand
  `product-modules.*` change.
- **Application PC** : le workflow installe les modules avant PyInstaller ; `build_scraper_sidecar.py` embarque les
  paquets de modules installés (leurs routes de sidecar, comme la vidéo de la réceptionniste).
- Les workflows manuels de la réceptionniste (`gen-demo-assistant`, `prod-receptionist-for-business`,
  `dump-receptionist-targets`) restent dans le cœur, avec les secrets du VPS ; ils importent le paquet du module.

## Module privé

Un module dont le dépôt est privé porte `"private": true` dans `product-modules.json`, comme `missions`.
GitHub ne donne pas ce dépôt anonymement, donc :

- `product_module_requirements.py` et `productModuleLayers()` le laissent de côté (avec un avertissement), sauf clone
  local dans `DLH_PRODUCT_MODULES_DIR` : le cœur se construit et se teste sans lui, sur n'importe quelle machine.
- Les workflows le récupèrent avec **sa clé de déploiement en lecture seule** : secret `MISSIONS_MODULE_DEPLOY_KEY`
  du cœur, clé publique dans les *Deploy keys* du dépôt du module. `deploy-api.yml` en fait une roue (`pip wheel`)
  envoyée au VPS avec `api/`, si bien que le serveur ne détient aucune clé ; `deploy-web.yml` et
  `desktop-release.yml` le clonent dans `web/.private-modules/`, où ses imports se résolvent sur `web/node_modules`.
- Sans le secret, les déploiements passent **sans le module** (avertissement dans le journal du workflow).
- Prérequis de l'organisation GitHub : *Settings → Member privileges → Deploy keys → Enabled*.
- Un autre module privé suit le même schéma : un secret `<MODULE>_MODULE_DEPLOY_KEY` et les mêmes étapes dans les
  trois workflows.

## Publier une version d'un module

1. Taguer `main` du dépôt du module (`vX.Y.Z`) et pousser le tag.
2. Passer `ref` à `vX.Y.Z` dans `product-modules.json` du cœur : le push sur `main` redéploie l'API, le dashboard,
   les démos et l'application PC (hors créneau d'envoi 8 h-14 h, comme tout déploiement de l'API).

## Développer un module en local

```bash
# Le clone à côté du cœur, puis, dans le venv de api/ du cœur :
git clone git@github.com:DevLeadHunter/devleadhunter-module-receptionist.git ../devleadhunter-module-receptionist
pip install -e ../devleadhunter-module-receptionist/api
```

```bash
# web/ et demo-host/ étendent les clones locaux : chemin ABSOLU du dossier qui contient les clones
# (résolu depuis web/ ou demo-host/, un chemin relatif tomberait à côté).
export DLH_PRODUCT_MODULES_DIR=/chemin/vers/Projects
```

Un layer cloné n'a pas de `node_modules` : `vue`, `@dicebear/*`… se résolvent par une jonction
`<module>/web/node_modules` vers `web/node_modules` du cœur (idem pour `demo-host/`), ignorée par git. Sous Windows,
`mklink /J`, et la retirer avec `cmd /c rmdir`, jamais `rm -rf` (qui viderait le dossier du cœur).

Les tests d'un module tournent depuis `api/` du cœur, sur ses fixtures :
`python -m pytest ../../devleadhunter-module-receptionist/api/tests`.
