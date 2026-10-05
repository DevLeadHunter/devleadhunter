# Maquettes

Les maquettes HTML du produit, gardées dans le dépôt pour qu'aucune ne se perde dans un fil de discussion. Chacune s'ouvre par un double-clic dans un navigateur : aucun serveur, aucune installation.

## En attente de décision

### Présence humaine sur la démo (`human-presence/`)

Ticket Asana « [IA Code] Présence humaine sur la démo ». Trois briques pour franchir le mur clic → contact de la vague 3 (environ 95 visites humaines, un seul message laissé).

| Fichier | Ce qu'il montre | État |
|---|---|---|
| `human-presence/banner-card.html` | La carte « Qui est derrière ce site » dans le bandeau démo : variantes C, A, B ; pastille, bureau, mobile ; site clair ou sombre | **Codée et en ligne le 03/10** (variante C, bouton « Me répondre », prix et date de retrait) |
| `human-presence/banner-receptionist.html` | La réceptionniste Léa dans le bandeau : onglet dans la carte (position 1) ou panneau séparé (position 2) | En attente |
| `human-presence/email-frank.html` | L'email franc en HTML : référence, variante (a) texte + signature, variante (b) avec une carte « Votre site, déjà en ligne » ; signature réelle ou allégée | En attente |
| `human-presence/email-frank-finalistes.html` (+ `email-vignette-exemple.jpg`, `email-capture-exemple.jpg`) | **Tranchée le 04/10 et codée** : proposition 1 sans titre ni image, réglage « Habillage » par modèle |
| `human-presence/email-frank-declinaisons.html` | Cinq déclinaisons du mail franc dans le gabarit de dibodev.fr, compatibles avec les modèles actuels (habillage, encadré du site, récapitulatif, photo du commerce, en-tête personnel) ; ordinateur et téléphone | En attente |
| `human-presence/email-frank-dibodev.html` | Variante (b) refaite le 03/10 au soir : le mail franc dans la mise en page de l'accusé de réception de dibodev.fr (carte blanche, bouton violet, trois étapes, signature) | En attente |
| `human-presence/NOTE.md` | Le pourquoi, les huit choix à trancher, l'avis donné sur chacun, l'effort et le plan d'implémentation | À jour |

### Trouver des prospects (`prospect-search/`)

| Fichier | Ce qu'il montre | État |
|---|---|---|
| `prospect-search/recherche-v5-captures.html` (+ `captures-v5/`) | **Douze vraies captures du logiciel** : la page « Nouvelle recherche » en quatre étapes, le volet « Recherche en cours » gardé d'une page à l'autre, la notification d'un nouveau lead, l'onglet « À valider » de Mes prospects, la fiche d'un lead, le thème sombre et le téléphone | **Retenue le 05/10** et intégrée au pixel près ; en attente de mise en ligne |
| `prospect-search/vivier-v4.html` | **Les leads en direct, version reprise** (maquette qui vit) : page des leads avec critères vérifiés en pastilles, barre de répartition, tri en lot ; page « Nouvelle recherche » en cinq questions avec résumé et coût ; barre de suivi large et basse sur les autres pages ; trois noms de menu à comparer | **Refusée le 04/10** ; décisions prises ensuite (voir la note) : la suite se construit dans le logiciel |
| `prospect-search/vivier-v3.html` | Première version du vivier en direct | Direction retenue le 04/10, remplacée par la v4 |
| `prospect-search/recherche-v2.html` | Première proposition : la phrase, le parcours, le fil | **Refusée le 04/10** (« aucune ne me plaît ») |
| `prospect-search/NOTE.md` | Ce qui est demandé, ce que montre le vivier, d'où vient chaque élément (dibodev.fr, PrePeers B2B, web), ce que cela change, les points à trancher | À jour |

### Nouvelle template électricien (`electrician-template/`)

| Fichier | Ce qu'il montre | État |
|---|---|---|
| `electrician-template/electricien-v5.html` (+ dossier `electricien-v5-photos/`) | Cinquième version : fond blanc, bleu nuit et touches ambre, haut de page en deux colonnes sans texte sur la photo ; trois états, dont un vrai prospect avec ses propres photos ; réglage « sections du CMS » | En attente (05/10) |
| `electrician-template/electricien-v4.html` | Quatrième version : texte sur une grande photo, cartes de couleurs | **Refusée le 05/10** |
| `electrician-template/electricien-halo.html` (+ quatre captures pleine page) | Troisième version : sobre, portée par les photos, calée sur les champs réels du contenu | « Pas mal » mais loin de l'effet attendu (05/10) |
| `electrician-template/electricien-clarte.html` (+ deux captures pleine page) | Deuxième version, dans l'esprit de dibodev.fr | « Beaucoup mieux » mais encore loin des meilleures templates (05/10) |
| `electrician-template/electricien-lueur.html` | Première version : page sombre qui s'allume, interrupteur, disjoncteurs | **Refusée le 05/10** |
| `electrician-template/NOTE.md` | Le pourquoi, la correspondance avec les sections du CMS, ce qui est inventé, les points à trancher | À jour |

### Ailleurs

- **Espace client de la réceptionniste** : la refonte du 01/10 (tableau de bord clair, quatre chiffres sur 30 jours, graphique) a été envoyée en captures, retour attendu avant de styliser les écrans secondaires. Maquettes publiées : v6 https://claude.ai/artifact/MPU1yQjGhRAUpDPFj6wizR et v7 https://claude.ai/artifact/6XhTx9kxyx7r7t1xiuhqPX.
- **Module Apple Wallet** : `design/wallet/` sur la branche `feat/apple-wallet-module` (page d'inscription client, chevalet, surface commerçant).

## Tranchées et codées

| Fichier | Ce qu'il montre | Devenu |
|---|---|---|
| `campaign-results-tab.html` | L'onglet « Résultats » d'une campagne (maquette v4) | Codé et en prod le 03/10 |
