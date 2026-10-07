# Entraînement de l'enrichissement

Carnet des manches qui rendent l'enrichissement de l'app meilleur que l'enrichissement fait à la main
avec Claude Code. Commencé le 7 octobre 2026, sur les leads de la vague 4, avec la méthode du carnet
`docs/PROSPECT_SEARCH_TRAINING.md`.

**Le but, fixé par Léo (7 octobre) : que l'app fasse mieux que Claude à la main, pas « presque aussi
bien ».** Chaque enrichissement réel est une manche, et la manche continue de compter après.

## La méthode

Une manche = un petit lot de leads réels de la campagne. Ce qui est enrichi sert : rien n'est fait pour
rien.

1. Enrichissement à la main d'abord, sans regarder l'app : fiche Google (galerie, note, avis,
   horaires, « À propos »), page Facebook, Instagram, annuaires, registre officiel (France :
   recherche-entreprises ; Suisse : Zefix et ses publications FOSC ; Québec : registre des entreprises).
2. Enrichissement de l'app sur le même lot (`api/enrich_cli.py --prospect …`, le scraping du poste puis
   l'enregistrement par l'API, comme l'app Windows).
3. Comparaison champ par champ : photos utilisables pour un site, note et avis, horaires, description,
   services, logo, réseaux, décisionnaire, entreprise ouverte ou fermée. Une donnée fausse compte plus
   qu'une donnée manquante.
4. Chaque écart reçoit sa cause, puis une correction et un test qui la rejoue ; on relance l'app sur le
   même lot pour mesurer l'« après ».

Note d'un lead : nombre de champs où l'app a au moins ce que la main a trouvé, sans rien de faux.

## Manche 1 — 5 leads, un par chemin du moteur (7 octobre, après-midi)

| Lead | Cas | Ce que le moteur doit faire |
|---|---|---|
| n° 265 | paysagiste suisse, fiche Google seule | lire la fiche, le registre |
| n° 351 | paysagiste suisse, page Facebook seule, site mort | lire la page Facebook |
| n° 310 | électricien français, ni fiche ni page (trouvé par le registre RGE) | trouver la fiche par nom et ville |
| n° 321 | garage québécois, fiche Google et page Facebook | fusionner les deux |
| n° 280 | garage français de la campagne SMS, fiche Google seule | lire la fiche |

### À la main

13 minutes pour les 5. Ce que la main a trouvé que l'app n'avait pas :

- **n° 351 est fermé** : radié du registre suisse le 14 juillet 2025 « par suite de cessation
  d'activité » ; sa page Facebook ne bouge plus depuis 2020. Accepté par la recherche avant que le
  moteur lise le registre. Les 44 autres leads suisses de la campagne ont été repassés au registre :
  aucun autre n'est fermé.
- **n° 265 a 32 photos sur Google, pas 10** : sans compte, le visualiseur ouvert par l'image principale
  s'arrête à 10 ; la galerie de la section « Photos » (onglet « Tout ») les montre toutes.
- **Décisionnaires** : le registre suisse donne le patron du n° 265 (associé gérant, publication FOSC) ;
  le registre français donne le gérant du n° 310.
- **Descriptions et services** écrits par l'entreprise ailleurs que sur Google : annuaire suisse et but
  au registre (n° 265), page du réseau de garages « Certifié Auto Service » (n° 321 : 17 services et les
  horaires), présentation de la page Facebook (n° 321).
- **Logos et réseaux** : Instagram (n° 265, n° 280) avec photo de profil et publications.
- **Pièges** : n° 310 a trois fiches Google (l'ancienne fiche familiale à la même adresse, dont la seule
  photo est une vue Street View de la maison ; un homonyme dans une autre ville ; la bonne, sans photo) ;
  n° 280 a un homonyme radié au registre dans le même département.

### Par l'app (avant correction)

2 min 21 s pour les 5.

| Lead | Résultat |
|---|---|
| n° 265 | 10 photos (les mêmes qu'à la main), note, horaires ; ni description, ni logo, ni décisionnaire |
| n° 351 | enrichi comme s'il était ouvert ; galerie avec le logo et la couverture floue (320 px) ; description « Nom, Ville. 91 followers. … » coupée au milieu d'une phrase |
| n° 310 | échec : « la fiche trouvée (« Résultats ») ne correspond pas au nom » ; gérant non trouvé |
| n° 321 | galerie = 4 fois le logo + une bannière noire vide + 1 vraie photo ; description = un post de 2017 sur un déménagement ; lundi absent des horaires (jour férié) |
| n° 280 | **vide** : ni note, ni avis, ni horaires, alors que la fiche a 5,0 sur 20 avis |

### Écarts et causes

| Écart | Cause | Correction |
|---|---|---|
| n° 280 vide | L'image principale de la fiche est une vue Street View : le clic pour ouvrir la galerie entre dans Street View, qui garde l'adresse de la fiche ; ouverte par son lien « cid », la fiche ne passait jamais par le rechargement (réservé aux adresses « /maps/place/ ») | Jamais de clic sur une image principale Street View ; rechargement de la fiche par son adresse ou son lien, dès que le titre n'est plus celui de la fiche |
| 10 photos sur 32 (n° 265) | Le visualiseur de l'image principale est plafonné sans compte | Galerie ouverte par la section « Photos » : onglet « Tout » (section à faire défiler jusqu'à elle ; à ne pas confondre avec le « Tout » du filtre des avis), sinon « N photos » ; puis l'onglet « Photos du propriétaire » en tête |
| Logos, couverture floue, bannière vide dans la galerie (n° 321, 351) | Aucun tri des images au-delà des doublons ; les photos Facebook stockées en données intégrées échappaient même au dédoublonnage | Tri de chaque image : plus grand côté < 400 px, contraste quasi nul, ou une couleur unie sur 60 % de l'image en moins de 170 couleurs (logo, affiche ; mesuré : logos 66-88 %, photos 5-13 %), ou ressemblance avec le logo |
| Post de 2017 en description (n° 321), « 91 followers » en tête (n° 351) | La description Facebook prenait le texte le plus long, post compris ; l'en-tête de l'aperçu (nom, ville, abonnés, visites) n'était pas retiré | La présentation de la page passe avant tout ; complétée par un texte plus long qui commence pareil, sinon coupée après sa dernière phrase entière ; en-tête retiré |
| n° 351 fermé, enrichi comme ouvert | Personne ne relisait le registre à l'enrichissement | Registre suisse lu à l'enrichissement : en liquidation ou radiée depuis moins de 3 ans, l'entreprise passe dans « Écartés » avec la raison (d'abord « Ne plus contacter », remplacé le jour même par l'onglet « Écartés » de Mes prospects) |
| Aucun décisionnaire suisse | Le décisionnaire ne lisait que les registres français | Personnes lues dans les publications FOSC (titulaire, président, administrateur unique, associé gérant, gérant ; formats d'avant et d'après 2020 ; départs « n'est plus ») ; utilisé seul quand une seule personne tient le rôle et que le prénom est sûr, sinon proposé à confirmer |
| Gérant du n° 310 non retenu | À la même adresse, une autre entreprise du même nom de famille (même métier, toujours active) faisait jeu égal | Le numéro SIRET que la recherche avait lu (registre RGE) désigne l'entreprise : aucune autre entreprise du registre ne peut plus la concurrencer |

### Résultat

Après correction (commits `14af96a4`, `41409df7`, `dbeecd6b`, `18e3ef69`, `30de0e11`), même lot :

| Lead | Avant | Après |
|---|---|---|
| n° 265 | 3 champs sur 8 | 4 sur 8 : **29 photos au lieu de 10 (mieux qu'à la main)**, décisionnaire du registre |
| n° 351 | 1 sur 4 | 4 sur 4 : « Ne plus contacter — entreprise radiée », 4 vraies photos, présentation propre |
| n° 310 | 1 sur 3 | 2 sur 3 : gérant trouvé par le SIRET ; la fiche Google reste ratée |
| n° 321 | 3 sur 7 | 5 sur 7 : 1 vraie photo et le logo à sa place, présentation de la page |
| n° 280 | 1 sur 6 | 4 sur 6 : 5,0 sur 20 avis, 3 avis, horaires ; photo selon la mise en page servie |
| **Total** | **9 sur 28 (32 %)** | **19 sur 28 (68 %)** |

- Temps : 4 min 52 s pour les 5 (59 s par lead, contre 28 s avant : galerie complète et tri des
  images), contre 13 minutes à la main.
- Google sert la fiche sous deux mises en page, à peu près une fois sur deux chacune : avec les
  onglets de photos (toute la galerie), ou une simple section « Photos » plafonnée à 10. Recharger ne
  choisit pas la mise en page (mesuré).
- Reste à faire (manches suivantes) : descriptions et services écrits ailleurs (registre, annuaires,
  pages de réseau), Instagram (logo, présentation, photos), choix de la bonne fiche parmi plusieurs
  résultats (n° 310), horaires d'un jour férié (n° 321), décisionnaire québécois, vitesse.

## Manche 2 — 10 leads, trois pays (7 octobre, soir)

| Lead | Cas | Ce que le moteur doit faire |
|---|---|---|
| n° 319 | électricien suisse, fiche Google récente (logo seul, pas d'avis) | lire la fiche, prendre le logo |
| n° 336 | garage suisse, fiche Google et page Facebook | fusionner les deux, trouver le titulaire |
| n° 346 | paysagiste suisse, page Facebook seule | lire la page, ne pas prendre la fiche Google d'un autre |
| n° 268 | paysagiste français, fiche Google et page Facebook | toute la galerie, le gérant |
| n° 362 | garage français, fiche Google et page Facebook | idem |
| n° 309 | électricien français trouvé par le registre RGE, ni fiche ni page | ne pas prendre la fiche d'un autre, le gérant |
| n° 295 | électricien québécois trouvé par le registre RBQ, ni fiche ni page | idem |
| n° 281 | paysagiste québécois, fiche Google et page Facebook | fusionner, services |
| n° 286 | garage québécois, fiche Google et page Facebook | fusionner, le patron |
| n° 355 | garage français de la campagne SMS, fiche Google seule | lire la fiche, le président |

### À la main

28 minutes pour les 10 (2,8 min par lead). Ce que la main a trouvé :

- **Services écrits par l'entreprise** sur 6 leads : présentations Facebook en liste (« Achat • Vente •
  Reprise • Mécanique », « AIR CLIMATISÉ, FREIN, SILENCIEUX… », liste à émojis), phrase de liste dans la
  présentation (« Dallage, pavage, taille des arbres, mur de pierre… »).
- **Décisionnaires** : registre français (gérant, président, entreprise individuelle), registre suisse
  (raison individuelle dont le nom contient le titulaire), présentation de la page (« X, paysagiste de
  formation »), nom de l'entreprise repris par les clients dans leurs avis (« je vais voir … »),
  répondant d'une licence au Québec (répertoire professionnel).
- **Pièges** : 3 leads sans fiche Google dont la recherche par nom renvoie un AUTRE artisan (n° 346, 309,
  295) ; photos d'autres garages dans le panneau de la fiche ; images de banque et flyers sur les pages
  Facebook ; présentation Facebook coupée en plein mot par son auteur (n° 268).

### Par l'app (avant correction)

9 min pour les 10 (54 s par lead). 40 champs sur 59 (68 %).

- Mieux que la main : photos de 4 leads (26 vraies photos de chantier au lieu de 5 pour n° 346, 33 au lieu
  de 5 pour n° 362, 22 au lieu de 9 pour n° 281, 12 vraies photos d'atelier pour n° 286 où la main n'en
  avait vu aucune), logo de n° 362, Instagram de n° 281, licence RBQ de n° 295 ; aucune fiche d'un autre
  artisan prise pour n° 346, 309, 295.
- Moins bien : aucun service sur aucun lead ; décisionnaire seulement pour 2 leads sur 7 ; 10 photos au
  lieu de 20 pour n° 268 ; pas de logo pour n° 319.
- Faux : photo de la façade (n° 336) et d'un élagueur (n° 268) prises pour le logo ; présentation
  « I.H Paysagiste. 112 followers. … » (n° 346) ; présentation coupée « … d'exploitation de forê » (n° 268) ;
  présentation de n° 286 réduite à « GARAGE DE MÉCANIQUE AUTOMOBILE . » ; flyers, bannières et images de
  banque dans la galerie (n° 281, 286, 336).

### Écarts et causes

| Écart | Cause | Correction |
|---|---|---|
| Aucun service | Aucune source ne remplissait la liste des services | Lecture des listes écrites par l'entreprise (puces, émojis, phrase de liste à virgules), sans les lignes qui vendent (devis, téléphone, réseaux, garantie) ni le nom de l'entreprise ; une liste de villes n'est pas une liste de services |
| Présentations Facebook coupées ou salies | La présentation complète de la page (« best_description ») n'était pas lue ; le nom à points « I.H » bloquait le nettoyage de l'en-tête ; un texte complet sans point final était coupé à sa première phrase | Présentation complète lue en premier, jamais coupée sauf si son auteur l'a laissée tronquée (alors fin à la dernière phrase entière, ou rien) ; en-tête nettoyé même avec un nom à points |
| Photo prise pour le logo (n° 336, 268) | La photo de profil Facebook devenait le logo sans contrôle | Une image sans aplat (moins de 30 %) et à plus de 160 couleurs est une photo, jamais un logo (mesuré : façade et élagueur 13-16 % en 181-275 couleurs, vrais logos 34-77 % ou 144 couleurs) |
| Pas de logo (n° 319) | Le logo de la fiche Google était jeté avec les graphismes | Sans logo, la première image graphique carrée de la galerie devient le logo |
| 10 photos au lieu de 33 (n° 268) | Google sert la mise en page « simple » (galerie plafonnée à 10) une fois sur deux ; recharger ne change rien | Effacer les cookies retire la mise en page (mesuré : catégories, simple, catégories) : jusqu'à 3 nouveaux tirages quand la fiche annonce plus de 10 photos |
| Décisionnaires suisses et québécois absents | Hors de France, seul le registre suisse était lu | Hors de France, les sources neutres tournent aussi (réponses du patron, texte de la page lu par l'IA, nom de l'entreprise repris par les clients) : proposition à confirmer, jamais automatique |
| Président de « A.S auto garage » absent | La recherche du registre français veut tous les mots dans la raison sociale ; les initiales à points disparaissaient de la comparaison | Deuxième recherche sans les mots du métier ; initiales jointes ; sans les mots du métier, le nom doit coller presque exactement (un « Martin » seul ne prend pas l'homonyme du coin) |

### Résultat

Après correction (commits `cf1662ea`, `dc3cb4d2`, `9adf55a0`), même lot :

| Lead | Avant | Après |
|---|---|---|
| n° 319 | 2 sur 3 | 3 sur 3 : le logo de la fiche Google |
| n° 336 | 5 sur 8 | 7 sur 8 : 3 services, présentation, façade dans la galerie ; titulaire de la raison individuelle toujours absent |
| n° 346 | 4 sur 7 | 7 sur 7 : présentation complète, 6 services, titulaire proposé à confirmer (lu dans la présentation) |
| n° 268 | 4 sur 8 | 5 sur 8 : 32 photos au lieu de 10 ; plus de présentation coupée ni de photo en logo |
| n° 362 | 7 sur 8 | 8 sur 8 : 4 services, président par le registre |
| n° 309 | 2 sur 2 | 2 sur 2 : la fiche d'Elex.services refusée, gérant par le registre |
| n° 295 | 1 sur 2 | 1 sur 2 : la fiche de l'autre M.D. Électrique refusée ; répondant RBQ toujours absent |
| n° 281 | 7 sur 8 | 8 sur 8 : 7 services |
| n° 286 | 5 sur 8 | 8 sur 8 : présentation entière, 7 services, patron proposé à confirmer (nom de l'entreprise + avis) |
| n° 355 | 3 sur 5 | 5 sur 5 : président par le registre, 1 photo |
| **Total** | **40 sur 59 (68 %)** | **54 sur 59 (92 %)** |

- Temps : environ 10 minutes pour les 10 (1 min par lead : nouveaux tirages de la mise en page), contre
  28 minutes à la main.
- L'app trouve en plus ce que la main n'avait pas : 26 photos de chantier au lieu de 5 (n° 346), 33 au
  lieu de 5 (n° 362), le logo de n° 362, l'Instagram de n° 281, la licence RBQ de n° 295.
- Pas encore mieux que la main sur tout : il manque 5 champs (titulaire suisse sans publication, gérant
  d'une entreprise individuelle au nom du patron, présentation et services lus dans les annuaires,
  répondant RBQ), et des flyers, bannières et images de banque restent dans 3 galeries.
- Une relance ne vide pas un logo déjà enregistré (un logo mis à la main ne doit jamais disparaître) : les
  2 photos prises pour logo à la 1re passe ont été retirées à la main.
- Reste à faire (manche 3) : écarter flyers, publicités, captures d'écran et images de banque des
  galeries (étiquetage visuel des photos, déjà en place pour la restauration) ; décisionnaire d'une
  entreprise individuelle au nom du patron (adresse mail, registre), d'une raison individuelle suisse
  sans publication, d'un entrepreneur québécois (répondant de la licence RBQ) ; descriptions et
  services des annuaires.
