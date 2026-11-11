# Module « Entretien de sites » : maquette des pages

## Pourquoi

Léo (11/11/2026) : « ça sera un module dans une repo séparé dans l'orga, comme on a fait pour les modules Apple Wallet et assistant IA. Tu peux me faire une maquette des pages pour ce module ? Les pages seront différentes du module site web et des autres modules, même s'il y aura des pages qui seront les mêmes, mais pas avec les mêmes données. »

L'idée de départ (10/11) : parcourir des sites, repérer de l'extérieur ce qui n'est pas à jour ou à risque, écrire au propriétaire avec un bilan gratuit, et décrocher de petites corrections comme la mission Villar-Documet. Détail : skill `/devleadhunter`, section « Module « Sites existants à remettre à jour » ».

## Ce que Léo a tranché avant la maquette (11/11)

- Nom du module : **Entretien de sites**. La page des bilans s'appelle **Contrôles**.
- Le prospect : les deux versions du message sont dessinées, avec le lien d'un bilan à son nom et sans lien (les faits dans le mail), pour les comparer en campagne.
- Ce que le module vend : la **correction à prix fixe** et le **suivi mensuel** (100 ou 150 €). Rien d'autre pour l'instant ; « je ne suis pas fermé à d'autres demandes ».
- Données de la maquette : de vrais contrôles sur 150 sites français de la base.

## Ce que montre la maquette (`entretien-de-sites-captures.html`, `captures/`)

Construite dans le vrai logiciel (voir « Comment la rejouer »), captures iPad portrait 820 × 1180, thème clair et sombre, ordinateur, téléphone.

- **Le module dans le sélecteur** : « Entretien de sites », avec son menu. Pages partagées : Tableau de bord, Mes prospects, Carte de prospection, Campagnes, Suivi des emails, Suivi des SMS, Ventes. Pages propres : Veille, Contrôles, Suivis. Bouton du haut : « Contrôler des sites ».
- **Contrôles** : quatre chiffres, onglets À écrire / Écrits / Rien d'urgent / À revoir / Tous, filtres par point et par métier, tableau à trois colonnes (entreprise, bilan, état). Le bilan tient en douze pastilles, quatre familles : sécurité (connexion sécurisée, version de PHP, logiciel du site, signes de piratage), e-mails (adresse de contact, SPF, DMARC), coordonnées (numéro de la fiche Google, numéro cliquable, année affichée), visibilité (affichage sur téléphone, lisible par Google et les IA).
- **L'atelier d'un contrôle** : le même atelier que la page d'un site démo ou d'une réceptionniste. Le bilan du prospect en plein écran dans un téléphone ou un écran d'ordinateur ; cinq outils en bas. « Points » (volet : couper un point le retire du bilan en direct) et « Offre » (volet : corrections à prix fixe, suivi mensuel à 100 ou 150 €) ; « Message » (page : avec le lien du bilan ou sans lien), « Activité » (page), « Plus » (page : lien du bilan, fiche du site, recontrôler, après la vente, ne plus contacter, supprimer).
- **Le bilan vu par le prospect** : page publique à son nom, toujours en clair. Les points à corriger d'abord, chacun avec « Vérifiez-le vous-même » ; puis ce qui va bien, ce qui n'est pas visible de l'extérieur, le prix, le suivi, qui écrit, comment dire non, et « Transférer à la personne qui gère le site ».
- **Contrôler des sites** : quatre sources (les entreprises écartées par les recherches, une nouvelle recherche, une liste d'adresses, les sites d'un même créateur), pays, métiers, nombre, réseaux et franchises laissés de côté, ce qui est lu.
- **Veille** : ce qui vient de changer et les échéances (PHP 8.2 le 31 décembre 2026, certificats qui expirent), une raison d'écrire par ligne.
- **Suivis** : les clients en suivi mensuel, leur dernier contrôle, le rapport du mois.
- **Réglages** : prix des corrections, quand écrire, points contrôlés, adresse d'envoi du module.

## D'où viennent les données

- **La base** (lue en prod le 11/11, en lecture seule) : les 27 recherches de prospects ont écarté 2 036 entreprises parce qu'elles ont un site en ligne (1 153 en France, 771 en Suisse, 112 au Québec ; 886 paysagistes, 582 électriciens, 568 garages). Aucune n'est devenue un prospect : elles n'ont jamais été contactées.
- **Les contrôles** : 150 sites français tirés au hasard, lus le 11/11/2026. Une seule lecture de la page d'accueil et les réglages publics du nom de domaine (MX, SPF, DMARC), comme un visiteur ; rien d'envoyé, aucun dossier caché, aucune connexion essayée.
- **Résultats réels** : 146 pages lues, 4 sites qui ne répondent plus ; 14 sites de réseaux ou d'annuaires retirés, il en reste 136, dont 121 lisibles ; **32 méritent un message** (25 avec un point à corriger) ; 1 site piraté (liens cachés vers des casinos, vérifié à la main) ; 8 sur un PHP sans correctifs (7.1, 7.4, 8.1) et 7 sur PHP 8.2 ; 2 sans https valable ; 3 certificats qui expirent sous 20 jours ; 12 WordPress en retard ; 12 domaines qui envoient des mails sans SPF ; 60 sans DMARC ; 4 pages pas adaptées au téléphone ; 12 où le numéro de la fiche Google n'est pas celui de la page d'accueil ; 16 signés par une agence en pied de page. La version de PHP n'est affichée que par 32 sites sur 121.
- **Noms, villes et adresses changés** : le dépôt est public, aucun vrai site n'est associé à ses défauts. Les vrais résultats restent sur le poste de Léo (`devleadhunter-module-site-care/tools/data/`, ignoré par git).
- **Inventé** : les envois (« Écrits », « Bilan ouvert », « A répondu », « En suivi »), les trois clients de « Suivis », et les blocs « Radar » et « Depuis le dernier contrôle » de la veille. Rien n'a été envoyé à personne.

## À trancher

- **Les prix** : 190 € et 390 € reprennent ceux de dibodev.fr, comme le suivi à 100 € par mois ; 90 € (https, e-mails du domaine, fiche pour Google) et 60 € (petites retouches) sont des propositions de Claude.
- **Le message** : avec le lien du bilan ou sans lien. Un mail qui parle de sécurité et porte un lien peut ressembler à un hameçonnage ; un mail sans lien ne permet pas de suivre les visites. À mesurer en A et B.
- **L'adresse d'envoi** : à part de `leo@mail.dibodev.fr` et de `contact@dibodev.fr` (avis de Claude du 10/11).
- **Les douze points** : lesquels garder. Trois sont peu vendables seuls (numéro cliquable, année, numéro de la fiche Google) et servent surtout au suivi.
- **Les sites qui ne répondent plus** (4 sur 150) : les passer au module Sites web.
- **Le seuil du test à la main** reste le juge avant de coder : au moins 2 réponses intéressées ou 1 mission signée sur 20 à 25 messages, décision début décembre.

## Comment la rejouer

- Le module vit dans un dossier local, à côté du cœur : `C:\Users\leogu\Desktop\Projects\devleadhunter-module-site-care` (layer Nuxt `web/`, dépôt git local, pas encore de dépôt GitHub). Les données sont dans `web/app/fixtures/`.
- Le cœur est le worktree `C:\Users\leogu\Desktop\Projects\dlh-mockup-site-care` (branche `mockup/site-care-module`, sur `origin/main` du 10/11) : seule modification, `product-modules.json` inscrit le module `site-care`. À ne pas fusionner : le dépôt GitHub du module n'existe pas.
- Serveur : configuration `web-mockup-site-care` du `.claude/launch.json` (port 3000, `DLH_PRODUCT_MODULES_DIR` pointe sur le dossier des clones).
- Outils, dans `devleadhunter-module-site-care/tools/` : `check_sites.py` (le contrôle), `build_fixture.py` (les douze points et les noms changés), `shoot.py` (les captures : l'API de prod n'est lue qu'une fois, ses réponses sont rejouées ensuite ; tout ce qui n'est pas une lecture est répondu sur place), `build_gallery.py` (cette page).
- Le module n'est pas listé par l'API comme activé : les captures l'ajoutent à la réponse de `GET /product-modules`.

## Retours de Léo sur la première version (11/11/2026) et version 2

Ses mots : « j'aurais plutôt vu une maquette Claude Code et pas simplement des screens ». Puis, point par point :

1. **« Mes prospects » et « Contrôles » font doublon** : une seule page. Et dans un module, « Mes prospects » ne montre que les prospects de ce module ; la liste et la recherche ne partagent pas leurs données d'un module à l'autre à l'écran (même si, en dessous, un prospect écarté par un module peut servir à un autre).
2. **Les pastilles de couleur du bilan** : « on ne comprend pas ce que ça veut dire, trop brouillon, pas assez propre, pas assez lisible, pas assez aéré ».
3. **L'email d'abord**, comme dans le module Sites web ; le téléphone passe après.
4. **La page générée pour le prospect** : « pas vraiment utile, pas vraiment belle, pas compréhensible. En l'état, je ne l'enverrai jamais. » À améliorer pour peut-être l'envoyer, ou à garder pour lui.
5. **Les métiers** : pas trois pastilles figées ; pouvoir en cocher autant qu'on veut, ou aucun, et en ajouter un autre, comme dans le module Sites web.
6. **« Laisser de côté les réseaux et les franchises »** : toujours actif, plus affiché.

**Version 2 = maquette cliquable** sur un canevas de design : https://claude.ai/artifact/Y6Dsa2yaw7x3qS7oyQ1VWX (privé, ouvrable depuis l'iPad ; sources dans `maquette-v2/`). Sept écrans reliés entre eux :

- **Mes prospects** (la seule liste, « Contrôles » disparaît) : les prospects du module, quatre chiffres, recherche, filtre par métier, onglets À écrire / Écrits / Sans email / Rien à signaler / À revoir. Chaque ligne dit en une phrase ce qu'on a vu sur le site (« PHP 7.4, plus corrigé depuis 2022 »), sans pastille. Un clic sur le nom ouvre la fiche : à corriger, à surveiller, le reste, ce qu'on peut proposer, le message, « Envoyer par email ».
- **Nouvelle recherche** : la recherche du module, en quatre étapes comme la vraie (Cible, Zone, Critères, Lancer). Métiers à cocher librement, aucun = tous, champ « Autre métier ». « Par email » choisi d'office ; les entreprises sans email vont dans « Sans email ». Les réseaux et franchises sont écartés sans le dire.
- **Page pour le prospect (facultative)** : refaite comme une lettre. Un titre en clair, ce que j'ai vu, ce que ça change pour vous, vérifiez-le vous-même en deux gestes, le prix, le reste du site en phrases, qui je suis. Le message part sans lien ; un interrupteur dans la fiche ajoute le lien. Trois exemples (PHP plus corrigé, site piraté, pas de cadenas).
- **Veille**, **Suivis**, **Réglages**, **Menu du module** : repris en plus aéré, sans pastilles, avec des mots simples (« cadenas de sécurité » pour https, « moteur du site » pour PHP).

Ce que la version 2 ne montre pas : les pages partagées (Tableau de bord, Carte, Campagnes, Suivi des emails et des SMS, Ventes), marquées « page partagée » dans le menu. Les lignes viennent des mêmes contrôles réels ; les onglets « Rien à signaler » et « À revoir » n'affichent que les premières lignes.

Non vérifié à l'écran par Claude : le canevas demande le compte de Léo. La logique de chaque écran a été exécutée hors canevas (aucune erreur).

Le layer Nuxt local (`devleadhunter-module-site-care`) et les 24 captures correspondent à la première version : à refaire sur la version retenue.

## État au 11/11/2026

Version 2 cliquable publiée, en attente du retour de Léo. Rien n'est codé côté API, rien n'est envoyé.
