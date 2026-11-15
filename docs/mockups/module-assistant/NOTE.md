# Assistant des modules (page de chat)

Maquette de la page « Assistant » des modules Missions et Entretien de sites, ouverte par le bouton orange au centre de la barre du bas.

- Canevas de design : https://claude.ai/artifact/8qtVr3pvwG4h1Xk3Q1Jmky
- Sources : `Main.dc.html` (le composant, avec ses réglages `module`, `start`, `wide`, `dark`), les dix planches `*.dc.html` qui l'appellent, `canvas.json`.

## Ce que Léo a demandé (15/11/2026)

Un chat « un peu comme celui de PostHog » : du texte, des cartes (les mêmes que la liste du module), des graphiques, une recherche dans les données du module, et des suggestions de messages à toucher.

## Ce qui a été tranché

- Versions 1 et 2 refusées : trop chargées, « on ne sait pas quoi faire ». Une seule chose par écran.
- Version 3 refusée : gros logo au milieu, pas assez d'écrans. Retiré, tuiles d'icône colorées, onze planches.
- Les suggestions sont des boutons séparés sous le mot « Suggestions », pas une carte ; texte en 14 px normal, aéré ; une icône « Entrée » à droite pour montrer que le toucher envoie.
- Icône du bouton central : une bulle de message (l'étoile a été refusée).
- Validée le 16/11/2026 : « tu peux implémenter ça dans le code ».

## Codé le 16/11/2026

- Cœur : composant `UiModuleAssistantChat` et bouton central par module (`tabBarMainAction`).
- Missions : `/dashboard/missions/assistant`. Entretien de sites : `/dashboard/site-care/assistant`.
- Le modèle de langage traduit seulement la question en requête ; chaque chiffre et chaque phrase viennent de la base.

## Dans la maquette mais pas encore codé

- Écrire et envoyer une réponse depuis le chat (la planche « Brouillon ») : pour l'instant la carte renvoie vers la page où l'on répond.
- Le nom des départements dans le graphique (« Paris (75) ») : le code affiche « Département 75 ».
- La recherche de sites par département (les sites n'ont que leur ville).
- Le lien « Voir les 12 missions » sous les cartes.
