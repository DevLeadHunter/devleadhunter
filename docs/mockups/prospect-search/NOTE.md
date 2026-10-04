# Trouver des prospects : du formulaire de recherche au vivier de leads

## Où on en est

| Maquette | Date | État |
|---|---|---|
| `recherche-v2.html` : trois directions (la phrase, le parcours, le fil) | 4 octobre 2026 | **Refusée** : « aucune ne me plaît » |
| `vivier-v3.html` : le vivier de leads en direct | 4 octobre 2026 | Direction retenue (« ça me plaît bien »), remplacée par la v4 |
| `vivier-v4.html` : les leads en direct, version reprise, avec la page « Nouvelle recherche » | 4 octobre 2026 | En attente de décision |

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

## Version 4 : ce qui change après le retour sur la v3

Retour reçu : la direction plaît, mais il manque la page « Nouvelle recherche » ; des flèches écrites
en texte ; la carte de suivi sur les autres pages est trop étroite et trop haute ; le nom « Vivier »
et son icône peuvent être mieux ; inutile d'afficher les raccourcis clavier.

| Point | Dans `vivier-v4.html` |
|---|---|
| Page « Nouvelle recherche » | Cinq questions sur une colonne (métiers, combien, où, comment les joindre, critères), une ligne « Reprendre » pour relancer une recherche passée, et une barre fixe en bas : résumé en une phrase, coût et durée recalculés à chaque choix, bouton « Lancer la recherche » |
| Flèches en texte | Remplacées par des icônes |
| Suivi sur les autres pages | Une barre large et basse en bas de la page : état de la recherche, lead à valider, ses critères, Refuser, Accepter ; elle se replie en pastille |
| Nom et icône | Trois propositions à comparer dans le menu : « Leads », « Radar », « Chasse » |
| Raccourcis clavier | Ils marchent toujours, ils ne sont plus affichés |
| Critères vérifiés | Quatre pastilles par ligne (email, portable, pas de site, note) : vert vérifié, ambre à vérifier, gris absent ; le volet les détaille avec leur preuve |
| Répartition | Quatre chiffres et une barre de répartition, à la place du bandeau de cinq cases |
| Tri en lot | Bouton « Accepter les n complets », filtres par métier |

Sources ajoutées pour la page « Nouvelle recherche » : Exa Websets et Parallel (résumé et coût avant
de lancer), Clay et Apollo (relancer une recherche, exclure les prospects connus). Erreur évitée :
la colonne de dizaines de filtres.

Avis donné sur le nom : « Leads », avec l'icône radar. Le mot dit ce que contient la page, et il se
distingue de « Mes prospects », qui reçoit les leads acceptés.

## À trancher (v4)

1. Le nom du menu : Leads, Radar ou Chasse.
2. Le mode par défaut : « Je valide » ou « Automatique ».
3. Un essai sur cinq leads avant la vraie recherche (vu chez Parallel et Clay) : utile ou non.
