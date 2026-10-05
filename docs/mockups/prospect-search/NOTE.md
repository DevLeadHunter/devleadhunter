# Trouver des prospects : du formulaire de recherche au vivier de leads

## Où on en est

| Maquette | Date | État |
|---|---|---|
| `recherche-v2.html` : trois directions (la phrase, le parcours, le fil) | 4 octobre 2026 | **Refusée** : « aucune ne me plaît » |
| `vivier-v3.html` : le vivier de leads en direct | 4 octobre 2026 | Direction retenue (« ça me plaît bien »), remplacée par la v4 |
| `vivier-v4.html` : les leads en direct, version reprise, avec la page « Nouvelle recherche » | 4 octobre 2026 | **Refusée** : hors de ce qui existe dans le logiciel |
| `recherche-v5-captures.html` : douze vraies captures du logiciel, dans `captures-v5/` | 5 octobre 2026 | **Retenue** : intégrée au pixel près, en attente de mise en ligne |

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

## Retour sur la v4 et décisions prises (4 octobre, soir)

Retour : l'icône du menu ne plaît pas ; le suivi posé en bas du menu occupe une place déjà prise par
les crédits et le compte ; la barre de progression n'est pas bonne ; seule la table tient à peu près ;
la page « Nouvelle recherche » ne va ni pour le visuel, ni pour l'usage, ni pour l'accord avec le
logiciel. Demande : beaucoup plus professionnel, plus fonctionnel, plus adapté à DevLeadHunter.

Cause : les maquettes inventaient une coquille au lieu de partir des vraies pages. Dans le logiciel,
la recherche s'ouvre déjà depuis Mes prospects, la Carte de prospection, le tunnel d'automatisation
et l'accueil ; « Mes prospects » est déjà le vivier (cartes de chiffres, filtres, onglets, tableau) ;
les volets restent ouverts d'une page à l'autre.

Quatre décisions, prises sur question :

| Sujet | Décision |
|---|---|
| Où vivent les leads à valider | Dans « Mes prospects », onglet « À valider » devant « Pas contacté » et « Contacté » |
| Lancer une recherche | Une page dédiée, sur le modèle du tunnel d'automatisation (étapes en haut, barre « Continuer » en bas) |
| Suivre depuis une autre page | Un volet « Recherche en cours » qui reste ouvert, et, fermé, un compteur dans le menu plus une notification par lead avec Accepter et Refuser |
| Validation | Un réglage par recherche : « Je valide » ou « Automatique » |

La suite ne passe plus par une maquette HTML : elle est construite dans le logiciel, avec ses
composants, sur la branche de travail, et montrée par de vraies captures avant toute mise en ligne.

## Version 5 : intégrée (5 octobre)

Demande : intégrer la recherche telle que la montrent les captures de `recherche-v5-captures.html`, au
pixel près. Les douze vues ont été refaites sur une base locale qui reprend leurs données, aux mêmes
tailles (1440 × 900, téléphone 390 × 844), en clair et en sombre, puis comparées pixel par pixel :
boîtes, bordures, icônes et positions tombent juste, seul le lissage du texte diffère (Windows contre
Linux).

Deux écarts avec les captures, voulus :

- Le journal ne dit plus « gardé » en mode « Je valide » : « complet, à valider » pour un lead complet,
  « un seul moyen de contact, à valider » pour un lead qui n'a qu'un contact.
- La page Campagnes porte le filtre « Tous canaux, Email, SMS », arrivé entre-temps.

« Annuler » après un refus rend au lead la place qu'il avait, avec son explication : un lead resté
« À vérifier » parce que Google n'a pas répondu revenait « Complet ». La place est gardée au refus
(colonnes `status_before_refusal` et `detail_before_refusal`) ; un refus antérieur à ces colonnes est
jugé de nouveau, comme avant.

Essayé à l'écran : refuser puis annuler (tableau, volet), accepter (tableau, fiche, volet, notification),
la fiche qui passe au lead suivant, le volet gardé d'une page à l'autre, le compteur du menu, le
lancement qui ouvre « À valider » et le volet. La mise en ligne lance seule les deux migrations de la base.

## Après la v5 : plusieurs recherches, sans note Google (5 octobre)

Retour : le bandeau « Une recherche tourne déjà » est raté ; il faut pouvoir lancer plusieurs
recherches, en file ou en même temps ; le filtre de note Google ne sert pas à grand-chose.

| Point | Ce qui est fait |
|---|---|
| Plusieurs recherches | Une **file d'attente** : une recherche lancée pendant qu'une autre tourne attend son tour et démarre toute seule à la fin de la précédente, dans l'ordre d'arrivée ; cinq au plus attendent |
| Pourquoi une file plutôt qu'en même temps | Une recherche saute les villes que les recherches finies ont déjà parcourues : en file, la suivante profite de la précédente ; en même temps, les deux paieraient les mêmes pages et proposeraient les mêmes entreprises |
| Bandeau en haut du tunnel | Retiré. L'étape « Lancer » dit quand la recherche démarre (« tout de suite », « après 3 recherches ») et le bouton devient « Ajouter à la file » |
| Suivre la file | Le volet « Recherche en cours » liste la file, avec « Retirer » ; le bandeau de Mes prospects dit ce qui suit |
| Note Google | Le filtre disparaît du tunnel et du récapitulatif ; l'étoile reste sur chaque lead, comme simple information |
| Responsive | Mes prospects ne défile plus de côté entre 768 et 1 280 pixels : l'en-tête invisible de la dernière colonne élargissait la page |
