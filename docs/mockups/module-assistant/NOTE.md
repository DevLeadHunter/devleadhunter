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

## Codé le 16/11/2026, conversation avec Claude le 17/11/2026

- Cœur : composant `UiModuleAssistantChat`, bouton central par module (`tabBarMainAction`) et moteur de conversation `services/module_assistant_engine.py`.
- Missions : `/dashboard/missions/assistant`. Entretien de sites : `/dashboard/site-care/assistant`.
- Claude (clé `ANTHROPIC_API_KEY`, modèle `ASSISTANT_MODEL`, Haiku 5.5 par défaut) tient la conversation et appelle les outils de chaque module ; chaque chiffre, carte et graphique vient de la base. Le fil est gardé d'une question à l'autre et quand on change de page.
- Mesuré le 17/11 sur 23 questions : Haiku 5.5 environ 0,0005 $ et 3 secondes par question, Opus 5.5 environ 0,02 $ et 5 secondes, pour des réponses aussi justes.
- Groq n'est pas utilisé par le chat : son quota gratuit (8 000 jetons par minute) ne tient pas une conversation.

## Dans la maquette mais pas encore codé

- Écrire et envoyer une réponse depuis le chat (la planche « Brouillon ») : l'assistant lit, il n'agit pas ; la carte renvoie vers la page où l'on répond.
- Le nom des départements dans le graphique (« Paris (75) ») : le code affiche « Département 75 ».
- La recherche de sites par département (les sites n'ont que leur ville).
- Le lien « Voir les 12 missions » sous les cartes : six cartes au plus sont montrées, sans lien vers la liste.
- La conversation n'est pas gardée après un rechargement complet de la page.
