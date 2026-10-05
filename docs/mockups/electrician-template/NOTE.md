# Nouvelle template électricien

## Pourquoi

Aucune vente après trois vagues. Les trois prospects intéressés avaient un site paysagiste ou garage ; les sept
électriciens qui ont visité leur démo n'ont pas donné suite. Hypothèse à tester en vague 4 : un site plus beau et plus
fini, pour le même métier, obtient-il plus de réponses ?

## Les maquettes

| Fichier | Ce qu'il montre | État |
|---|---|---|
| `electricien-halo.html` (+ quatre captures `electricien-halo-*.jpg`) | Troisième version : sobre, portée par les photos, calée sur les champs réels du contenu. Deux réglages en bas de page : données réelles du prospect ou fiche bien remplie, et affichage des sections du CMS | En attente du retour du 05/10 |
| `electricien-clarte.html` (+ deux captures) | Deuxième version : sobre, dans l'esprit de dibodev.fr | Jugée « beaucoup mieux » le 05/10, mais encore loin des templates garage et paysagiste, et pas alignée sur les données |
| `electricien-lueur.html` | Première version : page sombre qui « s'allume », interrupteur, disjoncteurs cliquables | **Refusée le 05/10** : trop d'appels à l'action, trop proche de la template actuelle, pas assez pro |

Les trois s'ouvrent par un double-clic. Le prospect est réel : Cz63 Électricité à Orléat, vague 3.

## Troisième version : ce qui vient de la fiche et ce qui est inventé

Tout ce qui s'affiche dans l'état « Données réelles de Cz63 » est le contenu que le prospect a aujourd'hui en base :
nom, logo, téléphone, e-mail, ville, secteur, note 5,0 sur 35 avis, texte de présentation, les six services et leurs
descriptions, les cinq questions et leurs réponses, les quatre repères de confiance, les trois points forts.

Sont nouveaux, à écrire comme textes par défaut de la template : le titre principal, les titres de section, la
description de la section services, les quatre étapes, le texte de la bannière et la description du contact.

Sont inventés pour l'état « Fiche bien remplie » : les trois avis, l'adresse, les horaires et le lien Facebook.

Les photos viennent toutes d'une banque d'images libre (Unsplash). Ce prospect n'a aucune photo à lui. Plusieurs
montrent du matériel américain (tableau, interrupteur) : à remplacer par des photos au standard européen avant de coder.

## Correspondance avec le contenu éditable

| Bloc de la page | Section du CMS | Champs |
|---|---|---|
| Haut de page | En-tête | Badge, titre, accroche, photo principale, deuxième photo, trois points forts, texte du bouton |
| Bandeau de quatre repères | Repères de confiance | Quatre repères (valeur et libellé) ; le repère « avis » reprend la vraie note |
| Prestations | Services | Titre, description, six services (titre, description, photo) |
| À propos | À propos | Titre, texte, photo |
| Déroulé | Méthode | Titre, étapes (titre, description) |
| Réalisations | Photos | Titre, galerie |
| Avis clients | Avis clients | Titre, avis (auteur, note, texte) |
| Bannière sombre | Contact | Titre et texte de la bannière, image de fond |
| Questions fréquentes | Questions fréquentes | Titre, questions et réponses |
| Contact, carte, pied de page | Contact et informations | Titre, description, téléphone, e-mail, ville, secteur, horaires, réseaux, logo |

Non éditables, lus sur la fiche Google : la note, le nombre d'avis, l'adresse et la position sur la carte.

Rien ne demande de nouveau champ dans le contrat de contenu. Trois réglages par template suffisent, déjà utilisés
ailleurs : une deuxième photo d'en-tête (comme la deuxième photo « à propos » du garage), une image de fond de bannière
et les champs titre principal, description des services, description du contact (comme le paysagiste).

## Ce qui a été retiré depuis la deuxième version, faute de donnée

- La section « Éclairage » : aucun champ ne la porte.
- Les « Trois réflexes en attendant » : texte figé, non éditable.
- La liste des communes : la fiche ne donne que la ville et « ses alentours ». Remplacée par la carte.
- Les légendes des réalisations : la galerie ne contient que des photos.

## Comportement quand la fiche est pauvre

- Pas de texte d'avis (cas de tous les électriciens actifs aujourd'hui) : la section montre seulement la note Google.
- Pas d'adresse ni d'horaires : la colonne contact montre téléphone, e-mail et secteur ; la carte est centrée sur la ville.
- Pas de photo : les photos par défaut de la template. D'où l'importance de bien les choisir.

## À trancher

1. La direction de la troisième version convient-elle ?
2. Le jeu de photos par défaut : une quinzaine de photos européennes à choisir.
3. La couleur d'action quand le prospect n'a pas de logo coloré.
