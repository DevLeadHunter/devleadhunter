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
- **Noms, villes et adresses changés** : le dépôt est public, aucun vrai site n'est associé à ses défauts. Les vrais résultats restent sur le poste de Léo (`devleadhunter-module-site-care-mockup/tools/data/`, ignoré par git).
- **Inventé** : les envois (« Écrits », « Bilan ouvert », « A répondu », « En suivi »), les trois clients de « Suivis », et les blocs « Radar » et « Depuis le dernier contrôle » de la veille. Rien n'a été envoyé à personne.

## À trancher

- **Les prix** : 190 € et 390 € reprennent ceux de dibodev.fr, comme le suivi à 100 € par mois ; 90 € (https, e-mails du domaine, fiche pour Google) et 60 € (petites retouches) sont des propositions de Claude.
- **Le message** : avec le lien du bilan ou sans lien. Un mail qui parle de sécurité et porte un lien peut ressembler à un hameçonnage ; un mail sans lien ne permet pas de suivre les visites. À mesurer en A et B.
- **L'adresse d'envoi** : à part de `leo@mail.dibodev.fr` et de `contact@dibodev.fr` (avis de Claude du 10/11).
- **Les douze points** : lesquels garder. Trois sont peu vendables seuls (numéro cliquable, année, numéro de la fiche Google) et servent surtout au suivi.
- **Les sites qui ne répondent plus** (4 sur 150) : les passer au module Sites web.
- **Le seuil du test à la main** reste le juge avant de coder : au moins 2 réponses intéressées ou 1 mission signée sur 20 à 25 messages, décision début décembre.

## Comment la rejouer

- La maquette en captures vit dans un dossier local, à côté du cœur : `C:\Users\leogu\Desktop\Projects\devleadhunter-module-site-care-mockup` (layer Nuxt `web/` sur données figées, dépôt git local jamais publié). Les données sont dans `web/app/fixtures/`. Depuis le 11/11 au soir, `devleadhunter-module-site-care` est le vrai module (voir « Le module codé »).
- Le worktree `dlh-mockup-site-care` et sa branche `mockup/site-care-module` ont été retirés le 11/11 : pour rejouer ces captures, il faudrait pointer le `product-modules.json` d'un worktree sur ce dossier.
- Outils, dans `devleadhunter-module-site-care-mockup/tools/` : `check_sites.py` (le contrôle), `build_fixture.py` (les douze points et les noms changés), `shoot.py` (les captures : l'API de prod n'est lue qu'une fois, ses réponses sont rejouées ensuite ; tout ce qui n'est pas une lecture est répondu sur place), `build_gallery.py` (cette page).
- Le module n'est pas listé par l'API comme activé : les captures l'ajoutent à la réponse de `GET /product-modules`.

## Retours de Léo sur la première version (11/11/2026) et version 2

Ses mots : « j'aurais plutôt vu une maquette Claude Code et pas simplement des screens ». Puis, point par point :

1. **« Mes prospects » et « Contrôles » font doublon** : une seule page. Et dans un module, « Mes prospects » ne montre que les prospects de ce module ; la liste et la recherche ne partagent pas leurs données d'un module à l'autre à l'écran (même si, en dessous, un prospect écarté par un module peut servir à un autre).
2. **Les pastilles de couleur du bilan** : « on ne comprend pas ce que ça veut dire, trop brouillon, pas assez propre, pas assez lisible, pas assez aéré ».
3. **L'email d'abord**, comme dans le module Sites web ; le téléphone passe après.
4. **La page générée pour le prospect** : « pas vraiment utile, pas vraiment belle, pas compréhensible. En l'état, je ne l'enverrai jamais. » À améliorer pour peut-être l'envoyer, ou à garder pour lui.
5. **Les métiers** : pas trois pastilles figées ; pouvoir en cocher autant qu'on veut, ou aucun, et en ajouter un autre, comme dans le module Sites web.
6. **« Laisser de côté les réseaux et les franchises »** : toujours actif, plus affiché.

**Version 2 = maquette cliquable** sur un canevas de design : https://claude.ai/artifact/Y6Dsa2yaw7x3qS7oyQ1VWX (ouvrable depuis l'iPad, partagé par lien par Léo le 11/11 ; sources dans `maquette-v2/`). Sept écrans reliés entre eux :

- **Mes prospects** (la seule liste, « Contrôles » disparaît) : les prospects du module, quatre chiffres, recherche, filtre par métier, onglets À écrire / Écrits / Sans email / Rien à signaler / À revoir. Chaque ligne dit en une phrase ce qu'on a vu sur le site (« PHP 7.4, plus corrigé depuis 2022 »), sans pastille. Un clic sur le nom ouvre la fiche : à corriger, à surveiller, le reste, ce qu'on peut proposer, le message, « Envoyer par email ».
- **Nouvelle recherche** : la recherche du module, en quatre étapes comme la vraie (Cible, Zone, Critères, Lancer). Métiers à cocher librement, aucun = tous, champ « Autre métier ». « Par email » choisi d'office ; les entreprises sans email vont dans « Sans email ». Les réseaux et franchises sont écartés sans le dire.
- **Page pour le prospect (facultative)** : refaite comme une lettre. Un titre en clair, ce que j'ai vu, ce que ça change pour vous, vérifiez-le vous-même en deux gestes, le prix, le reste du site en phrases, qui je suis. Le message part sans lien ; un interrupteur dans la fiche ajoute le lien. Trois exemples (PHP plus corrigé, site piraté, pas de cadenas).
- **Veille**, **Suivis**, **Réglages**, **Menu du module** : repris en plus aéré, sans pastilles, avec des mots simples (« cadenas de sécurité » pour https, « moteur du site » pour PHP).

Ce que la version 2 ne montre pas : les pages partagées (Tableau de bord, Carte, Campagnes, Suivi des emails et des SMS, Ventes), marquées « page partagée » dans le menu. Les lignes viennent des mêmes contrôles réels ; les onglets « Rien à signaler » et « À revoir » n'affichent que les premières lignes.

**Deuxième retour de Léo (11/11, sur la version 2)** : « ça commence à être pas mal ». Sa demande : que la page pour le prospect reprenne la direction artistique de dibodev.fr. Fait le jour même, dans `PageProspect.dc.html` :

- police Rubik, fond blanc et bandes gris clair `#f6f6f3`, texte `#141414` ;
- violet `#6f5fe0` pour les sur-titres, le mot fort du titre et le bouton ; lavande `#e6e1ff` pour les ronds d'icône et le bloc final ;
- cartes à filet fin et coins de 12 px ; la carte du prix a le filet violet, l'ombre violette et l'étiquette « Prix fixe », comme la carte mise en avant des tarifs du site ;
- sections : le constat, les conséquences, la preuve (01, 02), le prix, le reste du site, qui vous écrit (portrait de Léo), bloc final « Vous voulez que je m'en occupe ? » avec « Me répondre » et « Ce n'est pas moi qui gère le site ».

Le portrait est celui du site (`dibodev.fr-frontend/public/images/about/leo-guillaume-portrait-400.webp`), déposé dans le canevas ; dans la source, son adresse `/_blob/…` ne vaut que là-bas. Les valeurs viennent de `app/assets/css/main.css` et des sections `DibodevPricingSection`, `DibodevFounderSection`, `DibodevContactCtaSection` du dépôt du site.

Vérification à l'écran : Léo a ouvert le lien en partage, Claude a donc pu regarder la page pour le prospect du haut en bas (rendu conforme). Les six autres écrans n'ont été contrôlés que par leur logique, exécutée hors canevas (aucune erreur) ; Léo les a vus lui-même.

**Troisième retour de Léo (11/11)**. Sa phrase sur la colonne « Ce qu'on a vu sur son site » était un reproche, pas un compliment (Claude l'avait mal lue) : on n'y comprenait pas au premier coup d'œil s'il s'agit d'une mise à jour en retard, d'une version à risque, de PHP ou d'un autre logiciel, d'un souci de sécurité ou d'un piratage. Et la carte « Ce que j'ai vu » de la page pour le prospect ne le convainquait pas : « peut-être la mettre en jaune, en orange, un peu en mode warning », dans la direction artistique de dibodev.fr, et ne plus laisser l'icône prendre la gauche de la carte en écrasant le texte.

Fait le jour même :

- **Colonne « Ce qu'on a vu sur son site »** : chaque ligne commence par une étiquette qui nomme le type de souci, avec son icône : Site piraté (rouge plein), Sécurité, Version à risque, Mise à jour en retard, E-mails, Sur téléphone, Coordonnées, Site daté, Dans Google. Rouge = à corriger, ambre = à surveiller, vert = rien à signaler. À côté, la technologie quand elle compte (« PHP 7.4 », « WordPress 6.5 »). Dessous, le fait en une phrase, puis « Aussi : … » qui nomme les autres soucis du site, à la place de « et 3 autres points ». Un troisième filtre, « Tous les soucis », trie la liste par type. La fiche reprend les mêmes étiquettes.
- **Carte du constat** : fond ambre `#fdf1dc`, filet et libellé `#b45309` (la teinte ambre de la palette de dibodev.fr, `app/core/constants/accentPalettes.ts`). L'icône et le libellé « Point à corriger » tiennent sur une ligne en haut ; le fait en gras, puis l'explication, sur toute la largeur. Même règle pour les cartes voisines : « Ce que ça change pour vous » et « Vérifiez-le vous-même » n'ont plus d'icône à gauche (une carte, des lignes séparées par un filet, « Étape 1 », « Étape 2 »).
- Hauteurs des planches : « Mes prospects » 2150, page pour le prospect 3960 (elle dépassait sa planche).

Vérification : rendu local de chaque planche modifiée (`render_board.js` puis capture Playwright avec `shoot_preview.py`, rangés dans `devleadhunter-module-site-care-mockup/tools/`), en clair et en sombre ; puis dans le vrai canevas : liste, onglet « Sans email », fiche ouverte, page pour le prospect.

Le layer Nuxt local de la maquette (`devleadhunter-module-site-care-mockup`) et les 24 captures correspondent à la première version, refusée.

## Le module codé (11/11/2026)

Léo, sur la version 2 corrigée : « Nickel, vas-y, code le nouveau module dans un repo séparé de l'orga, comme les modules Apple Wallet et assistant IA. » Fait le jour même.

- **Dépôt** : `DevLeadHunter/devleadhunter-module-site-care` (public), version `v1.0.0`, épinglée dans `product-modules.json` (cœur `86c23eb5`). Clé `site-care`, installé et **coupé par défaut** : il s'allume dans Paramètres → Administration → Modules.
- **Ce qui est livré** : les écrans de la version 2 (Mes prospects et la fiche, Nouvelle recherche, Veille, Suivis, Réglages, page pour le prospect sur l'hôte des démos, `/bilan/<adresse>`), le contrôle d'un site (douze points), l'envoi du message par le chemin d'envoi du cœur, la veille (recontrôle tous les sept jours) et le suivi mensuel avec son rapport. Le détail est dans le README du module et son `docs/API.md`.
- **Écarts avec la maquette, décidés en codant** :
  - la recherche puise dans les entreprises que les recherches du cœur ont écartées parce qu'elles ont un site (la recherche du cœur ne sait pas garder « seulement avec site ») ; les métiers proposés sont donc ceux de la base, avec leur nombre, et il n'y a ni champ « Autre métier » ni carte « Validation » ;
  - email seulement : « Par email, sinon par SMS » est affiché « Bientôt » ; pas de campagne, chaque message part depuis la fiche ;
  - un sixième onglet « Tous », dont la veille a besoin ;
  - la fiche a une carte « Son email » (chercher l'adresse sur le site, ou la taper) et des actions en bas (recontrôler, suivi mensuel, retirer) ;
  - les réglages ont une carte « Qui écrit » (nom, métier, phrase de présentation, site, photo) ; l'adresse d'envoi reste celle du compte ;
  - un site trop lent à répondre est rangé « à revoir », jamais annoncé comme disparu ; un piratage n'est retenu que sur des liens sortants vers des sites de jeux d'argent.
- **Pas fait** : une recherche qui trouve de nouvelles entreprises avec site, le SMS, les campagnes du module, une adresse d'envoi à part, le tri des pages partagées (carte, campagnes) par module.
- **Voir le module en local** sans aucun vrai site : `tools/local/` du dépôt du module (base jetable, entreprises inventées en `.test`, captures).
- Les domaines inventés des maquettes sont en `.fr` : à passer en `.example`, comme dans le dépôt du module.

## État au 11/11/2026

Module codé, relu et déployé en production le 11/11 au soir, coupé par défaut. Rien n'a été envoyé à personne. Le seuil du test à la main (début décembre) reste le juge de la suite.
