# Démos vitrines et aperçu en direct depuis dibodev.fr

Posé le 2026-11-02. Les pages « Site internet pour <métier> : voyez le vôtre en 2 minutes » de dibodev.fr
encadrent une démo DevLeadHunter dans une iframe et la pilotent par `postMessage` : le visiteur voit son
nom, sa ville, son téléphone, son logo, ses photos, ses couleurs et ses prestations sur le **vrai** template,
sans qu'aucun site ne soit généré. Deux briques côté DevLeadHunter : des **démos vitrines permanentes**
(une par template) et le champ **`identity`** du message `dlh:preview`.

## 1. Démos vitrines (`DemoSite.is_showcase`)

Une démo vitrine est un `DemoSite` ordinaire (rendu par `demo-host` depuis `content_json`), avec :

| Champ | Valeur |
|---|---|
| `is_showcase` | `true` (colonne ajoutée par la migration `add_demo_site_is_showcase`) |
| `prospect_id` | `NULL` — aucune campagne, relance ni relance J+30 ne la voit (toutes sélectionnent par prospect) |
| `status` | `active`, `demo_url_live = true`, pas d'espace Storyblok (inutile avant une vente) |
| `expires_at` | `2099-12-31`, `demo_link_sent_at = NULL` |
| Retrait | **jamais** : `expire_due_sites` et la page « démo retirée » (`/public/{slug}/withdrawn`, `/revive`) l'ignorent, `start_demo_ttl` / `restart_demo_ttl` refusent de lancer un compte à rebours, la boucle des espaces Storyblok (`next_site_without_space`) la saute |
| Tableau de bord | étiquette « Vitrine · jamais retirée » sur la carte et la fiche ; exclue du compteur « Démos actives » de l'accueil |
| Pages publiques | `noindex` comme toute démo ; **pas de tracking PostHog** (`DemoSiteView` ne l'initialise pas pour une vitrine) ; le bandeau « Ce site vous plaît ? » reste affiché en plein écran (jamais dans une iframe) |

Catalogue (`api/services/showcase_demo_service.py`, `SHOWCASE_DEMO_SITES`) — entreprises **fictives**
(noms vérifiés sans homonyme sur annuaire-entreprises.data.gouv.fr le 2026-11-02), téléphones de la plage
non attribuée `02 99 00 00 0X`, villes de Rennes Métropole, contenu produit par le registre comme pour un
prospect sans enrichissement (photos par défaut du template) :

| Page dibodev.fr | Slug (contrat, ne jamais renommer) | Template | Entreprise fictive | Ville | Téléphone |
|---|---|---|---|---|---|
| plombier | `exemple-plombier-signature` | `plumber-signature` | Plomberie Kerhuel | Rennes | 02 99 00 00 01 |
| plombier | `exemple-plombier-atelier` | `plumber-atelier` | Atelier Plomberie Kervella | Cesson-Sévigné | 02 99 00 00 02 |
| plombier | `exemple-plombier-cuivre` | `plumber-cuivre` | Ty Plomb | Bruz | 02 99 00 00 03 |
| électricien | `exemple-electricien-eclat` | `electrician-eclat` | Élec Bréquigny | Rennes | 02 99 00 00 04 |
| électricien | `exemple-electricien-lumen` | `electrician-lumen` | Courant d'Ille | Saint-Grégoire | 02 99 00 00 05 |
| garage | `exemple-garage-pitlane` | `mechanic-pitlane` | Atelier Mécanique Kerlann | Chantepie | 02 99 00 00 06 |
| paysagiste | `exemple-paysagiste-verdure` | `landscaper-verdure` | Les Jardins de Kerbel | Betton | 02 99 00 00 07 |
| menuisier | `exemple-menuisier-edito` | `artisan-edito` (+ 6 cartes « prestations » menuisier en `section_overrides`) | Atelier Bois Guéhenno | Vern-sur-Seiche | 02 99 00 00 08 |
| restaurant | `exemple-restaurant` | `food` | Le Bouillon de la Vilaine | Rennes | 02 99 00 00 09 |
| coiffeur | `exemple-coiffeur` | `barber` | Salon Mezen | Pacé | 02 99 00 00 10 |
| dentiste | `exemple-dentiste` | `dental` | Cabinet dentaire du Thabor | Rennes | 02 99 00 00 11 |

URL publique : `https://demo.dibodev.fr/<slug>` ; en iframe pilotée : `https://demo.dibodev.fr/<slug>?_edit=1`.

### Créer ou rejouer

```bash
cd api && python scripts/create_showcase_demos.py            # crée les manquantes, garde les existantes
cd api && python scripts/create_showcase_demos.py --rebuild-content   # régénère aussi le contenu des existantes
```

Le script est **rejouable** : une démo existante garde son identifiant et son contenu (donc les couleurs
retouchées dans le tableau de bord), seuls ses drapeaux et ses champs d'identité sont remis au catalogue ;
un slug du catalogue tenu par la démo d'un vrai prospect fait échouer le script (`ShowcaseSlugTakenError`),
jamais de reprise silencieuse. En production : workflow manuel
`.github/workflows/create-showcase-demos.yml` (SSH vers le VPS, venv de prod), à lancer **après** le
déploiement de l'API qui porte le script (`gh workflow run create-showcase-demos.yml`).

Les démos appartiennent au compte `ADMIN_EMAIL` (`--owner-email` pour un autre) : les pages publiques
signent avec ses coordonnées et son prix de vente.

## 2. Le message `dlh:preview` (aperçu en direct, `?_edit=1`)

`demo-host` écoute `window.postMessage` quand la page est ouverte avec `?_edit=1`
(`app/composables/useDemoPreviewOverrides.ts`) et fusionne le message dans le contenu rendu
(`app/pages/[slug]/index.vue`, `app/utils/DemoPreviewIdentityUtils.ts`) : couleurs, photos, cartes,
template et identité changent **sans rechargement et sans persistance** (rien n'est lu en retour ni
enregistré ; l'origine n'est pas filtrée, un cadre malveillant ne peut que restyler sa propre iframe).
Chaque champ est facultatif et validé strictement : une valeur invalide est ignorée, jamais tronquée.

| Champ | Forme | Limites |
|---|---|---|
| `type` | `'dlh:preview'` | obligatoire |
| `templateId` | identifiant de template (`plumber-signature`…) | ≤ 64 caractères ; sur une vitrine, changer de style = changer de `src` (une démo par template) |
| `palette` | `{ primary, secondary, accent }` | couleurs `#rrggbb`, clés inconnues ignorées |
| `photos` | tableau d'URL `https://` ou `data:image/…` | ≤ 30 photos, ≤ 2 Mo chacune ; `[0]` → hero, `[1]` → à propos, `[2:]` → galerie |
| `services` | `[{ title, description, image }]` | ≤ 12 cartes, titre ≤ 120, description ≤ 400, image `https://` ou `data:image/` ou `""` |
| `identity` | `{ businessName, phone, city, area, logoUrl }` | `businessName` ≤ 120, `phone` ≤ 32, `city` ≤ 80, `area` ≤ 120 (une ligne chacun) ; `logoUrl` = `https://` ou `data:image/…` ≤ 2 Mo |

L'identité est appliquée aux champs `businessName`, `phone`, `city`, `area` (par défaut = `city`) et `logo`
du `SiteContent`, puis les valeurs publiées sont remplacées partout où les textes les répètent
(« Plomberie Kerhuel, c'est… », « dépannage rapide à Rennes ») : le site entier lit l'entreprise du visiteur.

```json
{
  "type": "dlh:preview",
  "identity": {
    "businessName": "Plomberie Le Gall",
    "phone": "02 99 12 34 56",
    "city": "Vitré",
    "area": "Vitré et alentours",
    "logoUrl": "data:image/png;base64,iVBORw0KGgo…"
  },
  "palette": { "primary": "#0F5257", "secondary": "#14181C", "accent": "#C8102E" },
  "photos": ["data:image/jpeg;base64,/9j/4AAQ…", "https://exemple.fr/chantier.jpg"],
  "services": [
    { "title": "Dépannage 7 j / 7", "description": "Fuite, chauffe-eau, canalisation bouchée.", "image": "" },
    { "title": "Salle de bains clé en main", "description": "Du plan à la pose.", "image": "" }
  ]
}
```

Côté encadrant : `iframe.contentWindow.postMessage(message, 'https://demo.dibodev.fr')`, à renvoyer après
chaque `load` de l'iframe (un rechargement repart du contenu publié) ; modèle = `web/app/components/atelier/DevicePreview.vue`.
Origines autorisées à encadrer (`frame-ancestors`, `demo-host/nuxt.config.ts`) : le tableau de bord,
Storyblok, `https://dibodev.fr`, `https://www.dibodev.fr`, `https://localhost:3000`, `http://localhost:3200`.
