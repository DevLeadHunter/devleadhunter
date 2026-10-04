# Trouver des prospects : du formulaire de recherche au vivier de leads

## Où on en est

| Maquette | Date | État |
|---|---|---|
| `recherche-v2.html` : trois directions (la phrase, le parcours, le fil) | 4 octobre 2026 | **Refusée** : « aucune ne me plaît » |
| `vivier-v3.html` : le vivier de leads en direct | 4 octobre 2026 | En attente de décision |

## Ce qui est demandé

Retour sur la première maquette : la recherche n'est pas un formulaire suivi d'un tableau. Ce qui est
voulu, c'est « un très beau système de gestion de vivier de leads, avec acceptation et refus en temps
réel, où l'on peut faire autre chose dans une autre page en attendant, voir l'avancée et interagir en
temps réel ». Références données : le tableau de bord de dibodev.fr, le vivier de PrePeers B2B, le
skill ui-ux-pro-max et le web.

## Ce que montre `vivier-v3.html`

La maquette vit : des leads arrivent toutes les trois secondes, on accepte, on refuse, on annule, on
change de page. Données de la vraie recherche n° 2 de production, emails et téléphones masqués.

**La page Vivier**

- Une seule feuille, sans cartes imbriquées : titre, bandeau de recherche, cinq chiffres, onglets,
  tableau.
- Bandeau de recherche : point qui pulse, étape en cours, barre fine, « Arrêter ».
- Cinq chiffres : à valider, acceptés, de côté, écartés, fiches vérifiées.
- Onglets à compteur : À valider, Acceptés, De côté, Écartés.
- Tableau : monogramme, nom, métier et ville ; email avec sa preuve ; qualité (Complet, À vérifier,
  Portable seul). Le bord gauche dit la qualité d'un regard : vert, ambre, gris.
- Deux boutons ronds au bout de la ligne : refuser, accepter.
- Les leads qui arrivent pendant qu'on trie s'accumulent derrière « 2 nouveaux leads · Afficher » :
  la liste ne saute pas sous le curseur.
- Une ligne ouvre un volet qui pousse la page, avec les preuves. Accepter, Refuser ou De côté, puis
  le lead suivant s'affiche tout seul.
- Clavier : A accepter, R refuser, S de côté, flèches pour passer d'un lead à l'autre, Z annuler.
- Toute décision s'annule pendant cinq secondes (« Annuler »), et un lead écarté se reprend depuis
  l'onglet Écartés.
- Bascule « Je valide / Automatique » : en automatique, les leads complets sont acceptés seuls.

**Depuis une autre page**

- Le menu de gauche porte une entrée « Vivier » avec le nombre de leads à valider.
- En bas du menu, une carte « Recherche en cours » : acceptés, à valider, barre d'avancement.
- En bas à droite, une carte repliable montre le prochain lead avec Accepter et Refuser : on trie sans
  quitter la page où l'on travaille.

## D'où vient chaque élément

| Élément | Source |
|---|---|
| Feuille unique, barre d'outils, tableau dense, volet qui pousse la page | Tableau de bord de dibodev.fr (`indexing.vue`) |
| Bandeau d'avancement, carte de suivi en bas du menu, compteur sur l'entrée du menu | Tableau de bord de dibodev.fr |
| Bandeau de cinq chiffres, onglets à compteur, monogramme, bord gauche coloré, volet gardé d'une page à l'autre, bascule manuel / automatique | Vivier de PrePeers B2B (`lola.vue`) |
| Accepter, refuser, reporter au clavier avec passage au suivant | Tri de Linear et de Superhuman |
| Pastille « n nouveaux » | Pratique courante des listes en direct |
| Annulation par toast | Modèle de Gmail |
| Carte flottante repliable sur les autres pages | Panneau d'envoi de Google Drive |

PrePeers B2B n'a ni refus, ni temps réel, ni annulation : ces parties sont nouvelles. Les couleurs
restent celles de DevLeadHunter (noir et blanc, ambre en annotation), pas le violet ni l'orange des
références.

## Ce que cela change dans le fonctionnement

Aujourd'hui l'app crée seule un prospect pour chaque lead qui tient l'objectif. Dans le vivier, l'app
propose et l'utilisateur accepte ; un prospect n'est créé qu'à l'acceptation. Le mode « Automatique »
garde le comportement actuel pour les leads complets.

## À trancher

1. Le concept du vivier tel que montré.
2. Par défaut : « Je valide » ou « Automatique ».
3. Le lancement d'une recherche (bouton « Nouvelle recherche ») n'est pas encore dessiné.
