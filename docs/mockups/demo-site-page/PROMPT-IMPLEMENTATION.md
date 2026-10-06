# Prompt d'implémentation : la page d'un site démo devient « l'atelier »

> À coller tel quel à un modèle de code. Repo : `C:\Users\leogu\Desktop\Projects\devleadhunter` (monorepo : `web/` = dashboard Nuxt 4, `api/` = FastAPI, `demo-host/` = hébergeur des sites). Tout le nécessaire est dans le dépôt.

---

Tu travailles dans le dépôt DevLeadHunter, dossier `web/` (Nuxt 4, Vue 3, TypeScript strict, Tailwind v4, Pinia, Nuxt UI). Ta mission : **remplacer la page d'un site démo** (`web/app/pages/dashboard/demo-sites/[id].vue`) par la version « atelier » dont la maquette a été validée par Léo le 06/10/2026.

## 1. Ce que tu dois produire

La maquette a été **construite dans le vrai logiciel**, sur la branche `mockup/demo-site-page` (dernier commit « feat: draft the atelier layout of the demo site page »). Commence par la lire : `git fetch origin && git show origin/mockup/demo-site-page --stat`, puis `git diff main...origin/mockup/demo-site-page`. Les captures validées sont dans `docs/mockups/demo-site-page/site-demo-atelier-captures.html` (dossier `captures-atelier/`) : ouvre-les, c'est le rendu attendu, au pixel près sur iPad en portrait (820 × 1180). La note `docs/mockups/demo-site-page/NOTE.md` liste la correspondance entre l'ancienne page et la nouvelle : **rien de l'existant ne doit disparaître**.

**Pars de la branche de maquette** (`git checkout -b feat/demo-site-atelier origin/mockup/demo-site-page`, puis `git merge main` pour être à jour) et finis le travail : la branche est une maquette fonctionnelle, pas un code fini. Ce qui doit être fait :

### 1.1 Comportement attendu de la page (voir les captures)

- **Barre du haut** : flèche retour, nom du site, pastille d'état (« En ligne » / « Hors ligne »), ligne de faits « Expire dans 8 j · Vidéo prête · Client pas encore invité », bouton rond « copier le lien », bouton « Ouvrir » (ouvre la démo avec `?internal=1`, comme aujourd'hui). Dès qu'il y a une modification non publiée : « Annuler » + « Publier » remplacent ces deux boutons.
- **Sélecteur Téléphone / Ordinateur** sous la barre, centré.
- **L'aperçu** : le site publié dans un **vrai écran** (téléphone 390 × 844 ou ordinateur 1440 × 900) réduit à l'échelle pour tenir dans la zone, centré, qui **défile à l'intérieur**. Il se redessine en direct avec les modifications non publiées (template, couleurs, ordre des photos, cartes de prestations) par le `postMessage` `dlh:preview` déjà compris par le demo-host en mode `_edit=1` (voir `DemoSitesTemplatePicker` pour le protocole ; le composant `DemoSitesAtelierPreview` de la branche le fait déjà).
- **Barre d'outils en bas** : Template, Couleurs, Photos, Prestations (seulement si la template a des cartes de services : `isServiceCardsEditorVisible`), Vidéo, Plus. Un point ambre sur l'outil qui porte une modification non publiée.
- **Volet** : toucher un outil ouvre un volet en bas (poignée, titre, sous-titre, bouton fermer) qui prend **au plus 44 % de la hauteur** ; l'aperçu se réduit au-dessus, il n'est **jamais caché**. Toucher le même outil referme le volet.
  - Template : les templates en cartes qui défilent de côté (vignette `/templates/{id}.jpg`, nom, « Actuelle » sur celle du site), l'actuelle en premier, les masquées exclues sauf l'actuelle (`filterSelectableTemplates`).
  - Couleurs : `DemoSitesColorEditor` dans sa nouvelle forme : « Couleur des boutons » en **deux cartes** (« Celle du logo » / « Celle de la template », avec la couleur et le code hex), puis « Toutes les couleurs » (action, fond, secondaire) avec des champs de 40 px. **Plus de pastille « boutons »**.
  - Photos : `DemoSitesImageSlots` avec `is-heading-hidden` (le volet porte déjà le titre), état vide `UiEmptyState` quand le prospect n'a pas de photo.
  - Prestations : `DemoSitesServiceCardsEditor`, inchangé.
  - Vidéo : la carte « Vidéo de prospection » telle qu'elle existe aujourd'hui (états générée / en cours / en attente du PC / échec, boutons copier / régénérer / supprimer, lien vers les réglages) + un encart « Comment elle part » (email : `{vignette_video}` et `{lien_video}` ; SMS : `{lien_video}` ; mesure de la lecture).
- **Plus** n'ouvre pas un volet : il **remplace l'aperçu par une vraie page** qui défile, cartes pleine largeur l'une sous l'autre : Lien de la démo (champ + copier, phrase « Elle est retirée dans N jours, le JJ/MM/AAAA » ou « Le compte à rebours démarre au premier email envoyé »), Espace d'administration du client (statut, « Ouvrir l'éditeur », « Inviter le client » / « Vérifier s'il a rejoint »), Informations du prospect (email, téléphone, créé le, template, description, lien « Modifier ces informations » vers `/dashboard/demo-sites/{id}/edit`), Code du site (exporter le zip), Supprimer le site (carte à liseré rouge, confirmation modale comme aujourd'hui).
- **Publier** = l'actuel `savePendingChanges` (template, couleurs, source de couleur, ordre des photos, cartes) ; « Annuler » = `resetPendingChanges`. Le libellé est « Publier » / « Publication… ».
- Thème sombre et clair, tous les deux (tokens `--app-*`, voir `web/app/assets/css/main.css`).

### 1.2 Ce qui reste à faire par rapport à la branche de maquette

1. **Plein écran propre.** La maquette force la hauteur avec des marges négatives (`.atelier { height: calc(100% + …); margin: … }`) qui dépendent du padding de `web/app/layouts/dashboard.vue`. Fais-le proprement : soit une option de page (`definePageMeta`) que le layout lit pour retirer son padding et ne pas faire défiler `<main>` sur cette page, soit un layout dédié. Pas de valeurs magiques copiées du layout.
2. **Barre d'onglets du bas de l'app installée** (`UiMobileTabBar`, visible en mode `standalone` sur écran tactile) : sur cette page elle ferait doublon sous la barre d'outils. La masquer sur cette page, par la même option de page.
3. **Volet à deux hauteurs** : réglage (44 %) et plein (le site réduit au minimum, par exemple 20 %), que l'on change en tirant la poignée ou en touchant la poignée. Si c'est trop long, garder une hauteur mais le dire dans le compte rendu.
4. **Réutiliser, ne pas dupliquer** : `DemoSitesTemplatePicker` a reçu une prop `previewOnly` sur la branche, qui ne sert plus à l'atelier : retire-la si elle est inutile. `DemoSitesColorEditor` est aussi utilisé par le tunnel de création de site (`web/app/pages/dashboard/demo-sites/create.vue` et ses composants) : vérifie qu'il y reste correct avec sa nouvelle forme, à l'écran, dans les deux thèmes.
5. **Nettoyer les restes de l'ancienne page** : `web/app/types/DemoSiteDetailPage.ts` ne doit contenir que les types utilisés ; aucun `asideRef`, aucune carte de statistiques, aucun onglet.
6. **Accessibilité** : la barre d'outils a `aria-pressed`, le volet se ferme à Échap, le focus revient sur l'outil ; `aria-label` sur les boutons sans texte (copier, fermer).
7. **Téléphone** (390 px de large) : la page doit rester utilisable (barre d'outils à six boutons, « Ouvrir » sans texte) ; vérifie-le.

## 2. Règles du dépôt à respecter

- Standards : `web/STANDARDS_CODE_ET_ARCHITECTURE.md`. En résumé : pas de `any` ; chaque `ref`, `computed`, paramètre et retour typés explicitement ; `type` plutôt que `interface` ; types des props dans `web/app/types/<Composant>.ts` et `defineProps({...})` à l'exécution avec `PropType` ; ordre d'un SFC : `<template>` puis `<script lang="ts" setup>` puis `<style scoped>` ; JSDoc au-dessus de chaque fonction ; **aucun commentaire en ligne** dans le code neuf ; classes Tailwind avec les tokens `--app-*`, jamais de couleur en dur ; pas de tiret cadratin dans les textes.
- Nommage explicite, lisible sans ouvrir le fichier (`isVideoWaitingForDesktop`, pas `isReady`).
- Les textes de l'interface sont en français, simples, sans jargon (« Publier », « Celle du logo », « Le site se redessine en direct »).
- Contrôles obligatoires avant de livrer, tous verts : `npm --prefix web run lint` (prettier, eslint, et le vrai contrôle de types `node web/scripts/typecheck.mjs`). Le hook de pre-commit les relance : ne jamais le contourner (`--no-verify` interdit).
- PostHog : rien à ajouter, le tableau de bord n'est pas suivi.
- Ne touche pas à `api/` : tout existe côté serveur. Ne touche pas au `demo-host/`.
- Commits : conventional commits en anglais, en minuscules, une ligne (`feat: turn the demo site page into the atelier`), fin de message `Co-Authored-By:` si ton outil l'exige. Pousser sur une branche `feat/demo-site-atelier`, **pas de pull request** (une PR touchant `api/` déclencherait un déploiement ; ici tu ne touches pas `api/`, mais la règle de la maison est « pas de PR »). Léo fusionnera.

## 3. Comment vérifier

1. Pile locale : voir le README (section Développement) ; en bref, l'API locale sur `:8000` ou une API jetable, `npm --prefix web run dev -- --port 5173`, `npm --prefix demo-host run dev -- --port 3001` avec `NUXT_PUBLIC_API_BASE` pointant sur l'API locale. Un site démo avec de vraies photos et une vidéo prête est indispensable pour juger : prends un site existant de la base locale ou crée-le depuis le tunnel.
2. Ouvre `/dashboard/demo-sites/{id}` à **820 × 1180** (iPad portrait) : chaque outil, les deux formats d'aperçu, les deux thèmes, puis à 390 px et à 1440 px. Compare aux captures de `docs/mockups/demo-site-page/captures-atelier/`.
3. Modifie une couleur et l'ordre des photos : le site de l'aperçu change **sans rechargement** ; « Publier » enregistre et l'aperçu recharge le site publié.
4. « Plus » : chaque bouton fait ce qu'il faisait sur l'ancienne page (copier, ouvrir l'éditeur, inviter, exporter, supprimer avec confirmation).
5. Dans le compte rendu final, donne : les fichiers touchés, ce qui a été vérifié à l'écran (avec captures), ce qui ne l'a pas été, et les choix faits sur les points ouverts (volet à deux hauteurs, barre d'onglets, grille de photos non faite).

## 4. Ce que tu ne fais pas

- Pas de refonte des composants d'édition eux-mêmes (`ImageSlots`, `ServiceCardsEditor`, carte vidéo) au-delà de ce qui est décrit : ils sont réutilisés tels quels.
- Pas de grille de photos à la place de la liste (idée notée, pas tranchée).
- Pas de changement de la page `/dashboard/demo-sites/{id}/edit` ni de la liste des sites.
- Pas de nouveau mécanisme d'aperçu : le `postMessage` `dlh:preview` et le mode `_edit=1` du demo-host existent déjà.
