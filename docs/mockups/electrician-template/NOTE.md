# Nouvelle template électricien

## Pourquoi

Aucune vente après trois vagues. Les trois prospects intéressés avaient un site paysagiste ou garage ; les sept
électriciens qui ont visité leur démo n'ont pas donné suite. Hypothèse à tester en vague 4 : un site plus beau et plus
fini, pour le même métier, obtient-il plus de réponses ?

## Les maquettes

| Fichier | Ce qu'il montre | État |
|---|---|---|
| `electricien-v5.html` (+ dossier `electricien-v5-photos/`) | Cinquième version : fond blanc, bleu nuit et touches ambre ; haut de page en deux colonnes sans texte sur la photo ; trois états de données, dont un vrai prospect avec ses propres photos | En attente du retour du 05/10 |
| `electricien-v4.html` | Quatrième version : texte posé sur une grande photo, quatre cartes de couleurs sous la photo | **Refusée le 05/10** : pas de texte sur une image, pas de cartes multicolores, pas pensée pour les photos des prospects |
| `electricien-halo.html` (+ quatre captures `electricien-halo-*.jpg`) | Troisième version : sobre, portée par les photos, calée sur les champs réels du contenu | « Pas mal » le 05/10, mais loin de l'effet attendu : barre de menu flottante et pastille à point jugées « design IA », texte du haut de page mal agencé sur ordinateur. La découpe de la photo et le rendu téléphone ont plu |
| `electricien-clarte.html` (+ deux captures) | Deuxième version : sobre, dans l'esprit de dibodev.fr | « Beaucoup mieux » le 05/10, mais encore loin des templates garage et paysagiste, et pas alignée sur les données |
| `electricien-lueur.html` | Première version : page sombre qui « s'allume », interrupteur, disjoncteurs cliquables | **Refusée le 05/10** : trop d'appels à l'action, trop proche de la template actuelle, pas assez pro |

Toutes s'ouvrent par un double-clic.

## Cinquième version : les trois états

La barre en bas de page change les données affichées :

1. **Cz63 Électricité (Orléat)**, vrai prospect de la vague 3. Aucune photo à lui, une note Google (5,0 sur 35 avis).
   Les photos sont donc celles de la template.
2. **Feeling Good Electricité (Tournai)**, vrai prospect de la vague 3. Ses propres photos (une photo d'en-tête, une
   photo « à propos », cinq photos de chantier, prises au téléphone), pas de note Google, une adresse. C'est l'état qui
   prouve que la page tient avec ce qu'un prospect nous donne vraiment.
3. **Fiche bien remplie** : Cz63 avec trois avis, une adresse, des horaires et un lien Facebook inventés.

État des cinq électriciens en ligne au 05/10 : un seul a une note Google, aucun n'a de texte d'avis, deux ont leurs
propres photos, deux ont une adresse, un n'a pas de logo.

## Ce qui a été pensé pour les photos des prospects

- Aucun texte posé sur une photo : la lisibilité ne dépend jamais de l'image reçue.
- Cadres de taille modérée et de proportions fixes, plutôt verticaux : une photo de téléphone, verticale et moyenne,
  y rend bien. Plus de grande photo pleine largeur.
- Réalisations en bande de vignettes verticales toutes identiques, à faire défiler : n'importe quel nombre de photos,
  n'importe quel format, sans trou dans la grille.
- Les six photos de prestations sont celles de la template (aucun prospect n'en fournit) : c'est là qu'on maîtrise la
  qualité.
- Boutons bleu nuit, la couleur d'accent ne porte jamais de texte : elle peut venir du logo du prospect, même jaune.

## Ce qui s'affiche selon la fiche

| Donnée absente | Ce que fait la page |
|---|---|
| Pas de note Google | Le coin découpé de la photo d'en-tête montre la ville et « Secteur d'intervention » ; le deuxième repère devient « Devis gratuit » (c'est déjà ce que l'API renvoie) ; la ligne « Avis Google » disparaît de « À propos » |
| Pas de texte d'avis | La section « Avis clients » ne s'affiche pas |
| Pas d'adresse | La colonne contact montre le secteur ; la carte est centrée sur la ville |
| Pas d'horaires, pas de réseaux | Les lignes correspondantes ne s'affichent pas |
| Pas de photo | Les photos par défaut de la template |

À prévoir au moment de coder : une photo d'en-tête trop petite doit être ignorée (un des cinq électriciens a une image
de 320 pixels de large en photo principale), et un en-tête sans logo.

## Ce qui vient de la fiche et ce qui est nouveau

Viennent de la fiche réelle : nom, logo, téléphone, e-mail, ville, secteur, adresse, note, texte de présentation, les
six services et leurs descriptions, les cinq questions et leurs réponses, les quatre repères, les trois points forts,
les photos de Feeling Good.

Sont nouveaux, à écrire comme textes par défaut de la template : le titre principal, les titres de section, la
description des services, les quatre étapes, le texte de la bannière et la description du contact. L'accroche reprend
celle d'aujourd'hui, sans le tiret long.

Les photos par défaut viennent d'une banque d'images libre (Unsplash). Certaines montrent encore du matériel
américain : jeu définitif à choisir avant de coder.

## Correspondance avec le contenu éditable

| Bloc de la page | Section du CMS | Champs |
|---|---|---|
| Haut de page | En-tête | Badge, titre, accroche, photo principale, deuxième photo, trois points forts, textes des deux boutons |
| Bandeau de quatre repères | Repères de confiance | Quatre repères (valeur et libellé) |
| Prestations | Services | Titre, description, six services (titre, description, photo) |
| À propos | À propos | Titre, texte, photo |
| Déroulé | Méthode | Titre, étapes (titre, description) |
| Réalisations | Photos | Titre, galerie |
| Avis clients | Avis clients | Titre, avis (auteur, note, texte) |
| Questions fréquentes | Questions fréquentes | Titre, questions et réponses |
| Bannière | Contact | Titre et texte de la bannière, photo |
| Contact, carte, pied de page | Contact et informations | Titre, description, téléphone, e-mail, ville, secteur, horaires, réseaux, logo |

Non éditables, lus sur la fiche Google : la note, le nombre d'avis, l'adresse et la position sur la carte.

Rien ne demande de nouveau champ dans le contrat de contenu. Trois réglages par template suffisent, déjà utilisés
ailleurs : une deuxième photo d'en-tête (comme la deuxième photo « à propos » du garage ; à défaut, la première photo
de la galerie), une photo de bannière, et les champs titre principal, description des services, description du contact
(comme le paysagiste).

## À trancher

1. La direction de la cinquième version convient-elle ?
2. Le jeu de photos par défaut : une quinzaine de photos européennes à choisir.
3. La couleur d'accent : ambre pour tous, ou tirée du logo de chaque prospect.
