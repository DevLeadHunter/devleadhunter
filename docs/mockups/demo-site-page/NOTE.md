# Page d'un site démo : l'atelier

## Pourquoi

Léo (06/10/2026) : la page d'un site démo (`/dashboard/demo-sites/{id}`) et celle d'une réceptionniste sont « des vieilles pages… brouillonnes, trop de contenu dans tous les sens, pas agréables à utiliser » comparées aux autres pages. Il veut une vraie nouvelle version, d'abord pour le module Sites web, puis les autres modules. Son écran principal est **l'iPad en portrait**.

## Ce qui a été proposé

1. **v1, refusée le 06/10** (`captures-v1/`) : l'existant rangé en onglets (Aperçu, Apparence, Photos, Vidéo, Client) sur un en-tête façon campagne. « Pas vraiment d'efforts, ça ressemble beaucoup à ce que j'ai déjà… la page Apparence est vraiment moche, pas utilisable. »
2. **Trois directions discutées**, Léo a choisi **A, l'atelier** : le site en plein écran, une barre d'outils en bas, des volets qui montent, le site change en direct. (B « la chaîne de contrôle » : étapes à cocher puis « Site vérifié » / « Site suivant » ; C « le dossier » : une page qui défile.)
3. **L'atelier** (`site-demo-atelier-captures.html`, `captures-atelier/`), construit dans le logiciel sur la branche `mockup/demo-site-page` (worktree `dlh-mockup-site-page`), capturé sur les vraies données de TP Motorsport. Premiers retours de Léo, corrigés le soir même : le volet ne doit jamais cacher le site (il prend au plus 44 %, le site se réduit au-dessus) ; l'aperçu ordinateur doit garder un vrai format d'écran (1440 × 900 réduit à l'échelle, pas une pleine largeur) ; le choix « logo / template » en petites pastilles était moche (devenu deux cartes avec la couleur dedans). Puis : « Plus » devient une vraie page sans aperçu, et la pastille « boutons » disparaît.
4. **Retenue le 06/10** : « c'est très bien ». Implémentation confiée à un autre modèle : voir `PROMPT-IMPLEMENTATION.md`.

## Ce que la maquette contient (rien de l'existant n'est perdu)

| Avant | Dans l'atelier |
|---|---|
| Résumé (statut, template, ville, email, tél, expiration, création) | Barre du haut (nom, état, « Expire dans 8 j · Vidéo prête · Client… ») + Plus › Informations |
| Lien de la démo + copier | Bouton lien en haut + Plus › Lien de la démo |
| Description | Plus › Informations (texte) |
| Exporter le code, Supprimer | Plus › Après la vente |
| Vidéo de prospection | Outil Vidéo (même carte, relais PC compris) |
| Storyblok CMS (inviter, vérifier, ouvrir) | Plus › Espace d'administration du client |
| Quatre chiffres (Statut URL, Jours, CMS, Slug) | La ligne sous le nom ; le slug n'est plus montré comme un chiffre |
| Aperçu & template (aperçu + carrousel) | Le site en plein écran + outil Template |
| Couleurs, photos, cartes de services (colonne de 360 px) | Outils Couleurs, Photos, Prestations dans le volet, le site visible au-dessus |
| Sauvegarder / Annuler en haut | « Publier » en haut dès qu'il y a une modification, point ambre sur l'outil, « Annuler » dans le volet |

## Code touché sur la branche (à reprendre si retenu)

- `web/app/pages/dashboard/demo-sites/[id].vue` : nouveau template (barre, aperçu, volet, barre d'outils), script : `atelierTools`, `activeTool`, `previewDevice`, `visibleTools`, `toolPendingChanges`, `selectableTemplates`, `siteFactsLine`, `expiryLabel`, `toggleTool`.
- `web/app/components/demo-sites/AtelierPreview.vue` (nouveau) : le site dans un vrai écran (390 × 844 ou 1440 × 900) réduit à l'échelle, centré, qui défile dedans, redessiné par `postMessage` (`dlh:preview`) comme le `TemplatePicker`.
- `web/app/components/demo-sites/ColorEditor.vue` : choix de la couleur des boutons en deux cartes (logo / template), champs plus grands. Partagé avec le tunnel de création : à vérifier là-bas si retenu.
- `web/app/components/demo-sites/ImageSlots.vue` : prop `isHeadingHidden` (le volet a déjà son titre).
- `web/app/components/demo-sites/TemplatePicker.vue` : prop `previewOnly` (reste de la v1, inutilisée par l'atelier).
- `web/app/types/DemoSiteDetailPage.ts`, `web/app/types/ImageSlots.ts`, `web/app/types/TemplatePicker.ts`.

## À trancher

- Deux hauteurs de volet (réglage / plein) tirées au doigt, ou une seule.
- Les photos en grille de grandes vignettes glissables plutôt qu'une liste à flèches : **maquette faite le 07/10** (`captures-atelier/ipad-03b-photos-grille-*.jpg`, composant `DemoSitesImageGrid` sur la branche, moteur `useDragToReorder` en axe `grid`). **Tranché le 07/10** : grille sur écran tactile (iPad, téléphone), liste actuelle à la souris (ordinateur). Prompt pour l'autre modèle : `PROMPT-PHOTOS-GRILLE.md`.
- Masquer la barre d'onglets du bas (app installée) sur cette page.
- Le même atelier pour la page d'une réceptionniste : **maquette faite et retenue le 07/10** (`docs/mockups/receptionist-page/`), avec une règle en plus : un outil sans besoin d'aperçu est une page dédiée, pas un volet.

## Comment rejouer les captures

Pile locale jetable (voir la mémoire `local-dev-environment`), base seedée avec le vrai site TP Motorsport (`scratchpad/api-local/seed3.py` de la session du 06/10), serveurs `api-relay-8022`, `demo-host-relay-3001`, `web-mockup-5173` (worktree), puis `scratchpad/shoot_atelier.py` (Playwright du venv API).

## État au 07/10/2026 : en ligne

L'atelier, la grille de photos au doigt et l'appui long (200 ms) sont sur `main` et en production (fast-forward `6798b7a8` → `40a8f6f0`, livrés par l'autre session). Relecture faite le 07/10 : un défaut corrigé (`b3098e94`), « Modifier ces informations » ouvrait l'atelier au lieu de la page d'édition parce que `[id].vue` était la page parente de `[id]/edit.vue` ; la page vit maintenant dans `[id]/index.vue`. Vérifié en local : page d'édition rendue, grille sur écran tactile (10 tuiles), liste à la souris. Pas encore vérifié : l'appui long et le défilement automatique dans Safari sur un vrai iPad.
