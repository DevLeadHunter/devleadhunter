# Prompt complémentaire : les photos en grille sur iPad, en liste sur ordinateur

> À coller tel quel à un modèle de code, après (ou pendant) l'implémentation de `PROMPT-IMPLEMENTATION.md`. Même dépôt, mêmes règles.

---

Tu travailles dans le dépôt DevLeadHunter, dossier `web/` (Nuxt 4, Vue 3, TypeScript strict, Tailwind v4). La page d'un site démo (`web/app/pages/dashboard/demo-sites/[id].vue`) est devenue « l'atelier » (voir `docs/mockups/demo-site-page/PROMPT-IMPLEMENTATION.md` et les captures dans `captures-atelier/`). Léo a tranché une variante pour l'outil **Photos** du volet :

- **Sur un écran tactile (iPad, téléphone)** : les photos s'affichent en **grille de grandes vignettes** que l'on glisse au doigt pour les réordonner.
- **Sur un ordinateur (souris)** : on garde **la liste actuelle** (`DemoSitesImageSlots`, lignes avec flèches), sans la changer.

La maquette validée de la grille : `docs/mockups/demo-site-page/captures-atelier/ipad-03b-photos-grille-light.jpg` (et `-dark.jpg`). Le composant de maquette existe sur la branche `mockup/demo-site-page` (commit « feat: draft a photo grid in the atelier photos sheet ») : `web/app/components/demo-sites/ImageGrid.vue`. Pars de lui et finis-le, ne le réécris pas de zéro.

## 1. Ce que fait la grille (voir la capture)

- Trois vignettes par rangée sur iPad (deux sur téléphone), format 4 : 3, l'image remplit la tuile.
- Le même ordre et les mêmes rôles que la liste : la première photo est « Principale » (tuile cerclée d'ambre, badge ambre), la deuxième « À propos », les suivantes « Galerie 1, 2, 3… ».
- Sur chaque tuile : un badge avec le rôle en haut à gauche ; en haut à droite « voir en grand » (la visionneuse `UiImageLightbox` existante) et « retirer du site » ; en bas à droite le bouton « Principale » (sauf sur la principale), qui met la photo en tête ; en bas à gauche une poignée de glissement, décorative : **toute la tuile se glisse**.
- **Glisser au doigt** réordonne : c'est le moteur `useDragToReorder` du dépôt en axe `grid` (il existe déjà, `web/app/composables/useDragToReorder.ts`, voir `DragToReorderAxis`). La maquette le branche déjà ; vérifie qu'il fonctionne au doigt (tuile en `touch-none`, image `draggable="false"`, les boutons de la tuile arrêtent le `pointerdown` pour ne pas lancer un glissement) et que l'ordre émis arrive bien au parent (`update:order`) : l'aperçu du site au-dessus se redessine en direct, « Publier » enregistre.
- Sous la grille, « Non utilisées (n) » : les photos du prospect pas encore placées, en petites tuiles assombries avec un « + » ; un appui les ajoute en fin de galerie.
- Sans photo : le même état vide que la liste.
- Le sous-titre du volet dit « Glissez une photo pour la déplacer. La première est l’en-tête, la deuxième « à propos », le reste la galerie. » pour la grille, et la phrase actuelle pour la liste.

## 2. Comment choisir entre grille et liste

Ce n'est **pas la largeur de l'écran** qui décide, c'est **le pointeur** : tactile → grille, souris → liste. Le dépôt utilise déjà les variantes Tailwind `pointer-coarse:` / `pointer-fine:` (voir `web/app/components/ui/PageHeader.vue`). Mais ici il faut **un seul des deux composants dans le DOM** (chacun a son moteur de glissement et sa visionneuse) : écris un petit composable `useCoarsePointer()` (`web/app/composables/`, `matchMedia('(pointer: coarse)')`, réactif, qui suit les changements, retourne `Ref<boolean>`, typé, avec JSDoc, et vrai côté client seulement), et dans le volet Photos rends `DemoSitesImageGrid` quand il est vrai, `DemoSitesImageSlots` sinon. Les deux composants ont exactement les mêmes props et le même événement (`ImageSlotsProps`, `ImageSlotsEmits`) : rien à adapter côté page.

Conséquences à vérifier : l'app Windows (Tauri, souris) montre la liste ; un iPad, même avec un clavier, montre la grille ; un téléphone montre la grille à deux colonnes.

## 3. Finitions attendues sur la grille

- Cibles tactiles d'au moins 40 px (les boutons de la maquette font 32 px : agrandis-les, ou garde 32 px visuels avec une zone de touche plus grande).
- Les boutons de la tuile ont un `aria-label` ; la grille a `aria-label="Photos placées sur le site"` ; la visionneuse s'ouvre et se ferme au clavier comme dans la liste.
- Animation de réordonnancement : la `TransitionGroup` avec `move-class` comme dans la liste, et `motion-reduce` respecté.
- Thème sombre et clair : badge « Principale » en ambre avec texte sombre (`#1b1508`, comme le bouton de recherche de la barre d'onglets), autres badges sur `--app-surface` ; les boutons sur `--app-overlay` en blanc.
- Nommage explicite (`isCoarsePointer`, pas `isMobile`). Types dans `web/app/types/` (réutilise `ImageSlots.ts` ; si tu crées un type pour le composable, `web/app/types/Composables.ts` comme les autres).

## 4. Ce que tu ne fais pas

- Pas de changement de `DemoSitesImageSlots` (la liste) ni de `useDragToReorder`, sauf un vrai bug de l'axe `grid` au doigt, que tu décris alors dans le compte rendu.
- Pas de choix par largeur d'écran, pas de réglage utilisateur « liste / grille ».
- Pas de grille ailleurs que dans le volet Photos de l'atelier (le tunnel de création de site garde ce qu'il a).

## 5. Règles et vérification

Les règles du dépôt sont celles de `docs/mockups/demo-site-page/PROMPT-IMPLEMENTATION.md`, section 2 (standards TypeScript strict, JSDoc, pas de commentaire en ligne, tokens `--app-*`, `npm --prefix web run lint` vert, hook jamais contourné, pas de PR, pas touche à `api/`). Vérifie à l'écran, dans les deux thèmes : à 820 × 1180 avec émulation tactile (Playwright `has_touch: true`, ou un vrai iPad) la grille s'affiche et un glissement réordonne en direct ; à 1440 px à la souris la liste s'affiche, inchangée ; à 390 px la grille a deux colonnes. Donne des captures dans le compte rendu, dis ce qui n'a pas pu être vérifié (un vrai glissement au doigt sur iPad, si tu n'as que Playwright).
