# Recherche de prospects : audit complet et plan « une seule recherche »

Audit du 4 octobre 2026. Code lu sur `main` (`f87692da`). Chiffres de production lus le même jour, en
lecture seule. Les tests Bright Data et les fichiers publics cités ont été exécutés pendant l'audit.
Ce document complète `docs/MULTI_COUNTRY_AUDIT.md` § 1, qui traite la justesse par pays des scrapers
actuels ; ici on traite la puissance de la recherche elle-même.

But fixé par Léo : une seule recherche (plus de choix de source), aussi bonne que ce que fait
Claude Code à la main pendant les campagnes, puis meilleure. L'IA peut en faire partie.

## État au 4 octobre 2026 : la recherche unique est livrée

Les sections 1 à 7 décrivent l'ancienne recherche (par sources), telle qu'elle était le jour de
l'audit. Elle a été retirée le même jour et remplacée par la cible de la section 8.

**Ce qui existe**

- Une seule recherche, par objectif : métiers, pays, villes facultatives, nombre par métier, canal
  (email, SMS, ou les deux), « sans site web », note Google minimale. Écran `Trouver des prospects`,
  routes `/api/v1/prospect-searches`, code dans `api/services/prospect_search/`.
- Elle tourne sur le serveur et reprend après un déploiement. Trouver : registres RGE (France) et
  RBQ (Québec), résultats locaux de Google par Bright Data, pages Facebook connues de Google.
  Vérifier : une recherche « "nom" ville » lue par des règles, puis par l'IA quand les règles ne
  tranchent pas (site caché, fermé, homonyme, réseau, autre métier).
- Email avec son niveau de preuve : A publié par le professionnel (sa page Facebook, un registre),
  B donné par un tiers qui parle de lui (annuaire), C sans preuve franche (attend une décision).
  Le domaine d'un email est contrôlé à chaque fois : s'il sert un site au nom de l'entreprise,
  l'entreprise a un site.
- Chaque candidat a une place et une raison : gardé, mis de côté (joignable par l'autre canal), à
  confirmer, page Facebook à lire, écarté. Les gardés et les mis de côté deviennent des prospects
  (source « Recherche »).
- Mémoire : un prospect existant, un « ne plus contacter », une adresse déjà écrite, un candidat
  écarté depuis moins de 120 jours et une ville déjà balayée ne coûtent plus aucune requête.
- Pages Facebook : lues par le Chrome du poste, jamais par le serveur. L'application Windows le fait
  seule quand la recherche est ouverte ; `python prospect_search_cli.py` le fait depuis un terminal.
- Noms des fiches Google nettoyés (slogan, parenthèses, pictogrammes retirés).
- Email cherché aussi par le numéro de téléphone : un résultat qui montre le numéro du candidat parle
  de lui, quel que soit le nom affiché.
- Une fiche qui déclare un site que la vérification ne retrouve pas attend dans « À confirmer ».

**Mesuré sur les premiers passages (base locale, vraies requêtes)**

| Objectif | Requêtes | Gardés | Mis de côté |
|---|---|---|---|
| 3 plombiers, France (registre RGE) | 10 | 5 | 0 |
| 3 électriciens, Québec (registre RBQ) | 17 | 3 | 0 |
| 3 garages, France | 75 | 4 | 2 |
| 2 couvreurs, France | 75 | 2 | 6 |
| 3 paysagistes, Suisse | 160 | 4 | 12 |

Une requête coûte environ 0,0015 $. Un métier couvert par un registre revient à moins d'un centime
par prospect ; un métier sans registre, à 3 à 6 centimes.

**Premières recherches réelles (production, 4 octobre)**

| Objectif | Requêtes | Gardés | Mis de côté | À confirmer |
|---|---|---|---|---|
| 3 paysagistes à Monthey (Suisse), email et portable | 124 | 0 | 5 | 9 |
| 3 paysagistes et 3 électriciens en France, email et portable | 114 | 6 | 14 | 2 |

Les 6 gardés (Limoges, Castres) ont un email prouvé et un portable ; quatre ont été recontrôlés à la
main, aucun n'a de site. Durée : 5 à 7 minutes par recherche, lecture des pages Facebook comprise.

**Comparatif avec la méthode manuelle (paysagistes, Monthey, même objectif)**

| | Méthode manuelle (Claude Code + Bright Data) | Recherche de l'app |
|---|---|---|
| Requêtes | 16 | 124 |
| Fiches lues | 11 (annuaire) | 79 (Google « Lieux », 4 pages) |
| Prospects complets (email et portable) | 0 | 0 |
| Prospects avec portable, sans site | 0 gardé | 5 créés (4 recontrôlés à la main : justes) |
| Raison et preuve de chaque rejet | à la main, non gardées | enregistrées, 40 rejets |

- Ce que l'app a mieux fait : sept fois plus de fiches, les mêmes contrôles sur chacune, un email
  trouvé là où l'annuaire le cachait, aucune requête perdue sur les réponses vides (elle réessaie),
  et tout est gardé en mémoire pour la recherche suivante.
- Ce que la main avait mieux fait : un email donné par un annuaire sous un autre nom que la fiche
  Google. Corrigé le jour même : recherche par numéro de téléphone, et titre long cherché sans
  guillemets (le cas est rejoué en test).
- Ce que l'app ne fait toujours pas : trouver un artisan qui n'a ni fiche Google ni page Facebook
  (annonces dans des groupes), ouvrir le bouton « Site Web » d'une fiche quand Google ne montre pas le
  site ailleurs (ces fiches attendent dans « À confirmer »).

Depuis le 6 octobre (manche 1 de l'entraînement, `docs/PROSPECT_SEARCH_TRAINING.md`) : la fiche
search.ch de chaque candidat suisse est lue par son numéro (astérisque « pas de publicité » = écarté,
email et site de l'annuaire pris en compte), une ville que Google n'a pas servie est reprise au lieu
d'être comptée comme parcourue, et la Suisse compte 69 villes au lieu de 20.

**Ce qui reste (lots de la section 10)**

- Lot 2, en partie : le bouton « Vérifier » sur un prospect importé, ajouté à la main ou déjà en
  base.
- Lot 5, en partie : l'envoi direct des gardés vers une campagne (ils arrivent dans « Mes
  prospects »).
- Lot 6 : pastille « fiche complète » et enrichissement en file.
- Lot 7 : dirigeant hors France (le nom lu pendant la vérification est gardé comme preuve, pas
  encore reporté sur le prospect), score de potentiel, tableau de rendement.
- Lecture Facebook par un service payant : écartée (trop chère).

## 1. En bref

- **La recherche de l'app ne sert pas.** 20 passages de source enregistrés depuis l'origine, tous
  des essais « Électricien Lyon » des 27 et 28 août. Depuis, rien : les prospects en base viennent
  de Claude Code (par l'API) ou de l'ajout manuel.
- **Cause n° 1 : elle tourne sur le serveur, où Chrome ne démarre pas.** Google Maps et la chasse aux
  emails y sont donc morts. Seule la source Facebook marche (elle cherche par Bright Data côté
  serveur, puis lit les pages sur le PC).
- **Cause n° 2 : même réparée, elle ne fait qu'un tiers du travail.** Elle trouve, mais elle ne
  vérifie pas (site caché, fermé, homonyme, déjà contacté), elle ne vise pas un objectif, elle ne
  garde aucune preuve et elle ne dit pas ce qui manque à une fiche.
- **Trois découvertes de l'audit changent le plan :**
  1. Les résultats locaux de Google (« Lieux ») se lisent depuis le serveur par Bright Data : 20
     fiches par page avec nom, note, nombre d'avis, téléphone, statut et bouton « Site Web » présent
     ou non. Testé en Suisse et au Québec. Plus besoin de Chrome pour trouver.
  2. Deux fichiers publics gratuits donnent l'email : la liste RGE de l'ADEME (France, bâtiment) et
     les licences RBQ (Québec, bâtiment).
  3. Prendre « le premier email trouvé dans une page Google » est dangereux : sur un test réel,
     les adresses de quatre concurrents sortent avant celle du prospect.
- **Plan :** une recherche par objectif en six étapes (trouver, fusionner, vérifier, email,
  dirigeant, fiche complète), côté serveur sauf la lecture Facebook et les photos. L'IA juge des
  pages déjà lues, elle n'est jamais la source d'une donnée.

## 2. Les faits mesurés en production (04/10/2026)

| Mesure | Valeur |
|---|---|
| Passages de source enregistrés depuis l'origine | 20, tous « Électricien Lyon », 27 et 28 août |
| Dont Facebook | 17 (tours de la boucle compris), tous réussis |
| Dont recherche classique | 1 recherche, 3 sources essayées : Google en erreur (« Failed to start Chrome via nodriver »), Pages Jaunes vide, auto vide |
| Recherches en septembre et octobre | 0 |
| Recherches gardées en mémoire au moment de l'audit | 0 (effacées à chaque déploiement) |
| Prospects en base | 118 : 55 « facebook », 48 « manual », 15 « google » (étiquette de source ; presque tous créés à la main ou par Claude via l'API) |
| Par pays | France 70, Suisse 26, Belgique 22 |
| Avec email / téléphone | 110 / 111 |
| Avec fiche Google / page Facebook | 56 / 90 |
| Enrichissements lancés | 94 : 61 réussis (65 %), 23 vides, 10 « Facebook vide » |
| Recherches de dirigeant | 224 : 80 noms trouvés (36 %), dont 26 validés seuls et 54 « à confirmer » |

## 3. Comment marche la recherche aujourd'hui

1. Le formulaire (`SearchProspectsDrawer.vue`) envoie un métier, une ville, un pays, un nombre, une
   source et « sans site ».
2. `POST /scraping-jobs` crée un job **en mémoire** sur l'API (`scraping_job_service.py:37`).
3. `scraper_service.scrape_all` essaie les sources **l'une après l'autre** dans l'ordre
   `google → pagesjaunes → brightdata → osm` (`scraper_service.py:33`) et s'arrête dès qu'il a le
   compte. Hors France, Pages Jaunes et son relais Bright Data sortent de la chaîne.
4. Chaque source cherche, filtre « a un site vivant », puis cherche un email pour chaque prospect.
5. Chaque prospect trouvé est enregistré tout de suite, après un test de doublon nom + ville.
6. La source Facebook est à part : elle ne sort que des pages candidates, puis l'app desktop lit
   chaque page sur le PC et ne garde que celles qui ont un email (4 tours au plus).

## 4. Constats

### A. Où ça tourne

- **A1. La recherche tourne toujours sur le serveur.** `prospectSearch.ts` appelle l'API du VPS
  (`launchJob`), y compris depuis l'app Windows. Le programme local du PC (`scraper_sidecar.py`) n'a
  aucune route de recherche : il ne sait faire que les suggestions, l'enrichissement, Storyblok et
  la vidéo.
- **A2. Sur le serveur, tout ce qui passe par Chrome est mort** : Google Maps (`google_scraper`),
  Pages Jaunes en mode navigateur, et `email_scraper` (qui ouvre Google dans Chrome). Il reste OSM,
  Pages Jaunes par Bright Data (France) et la découverte Facebook.
- **A3. L'historique est perdu à chaque déploiement** (dictionnaire `_jobs`). Une recherche en
  cours meurt avec le déploiement.
- **A4. Déplacer la recherche sur le PC ne suffirait pas** : ouvrir chaque fiche Maps dans Chrome est
  lent, casse à chaque changement de Google (plusieurs fois par an), demande le PC allumé et une
  mise à jour de l'app à chaque correctif.

### B. Trouver

- **B1. Une recherche = un métier et une ville.** Pas d'objectif (« 5 paysagistes par pays »), pas
  de changement de ville, pas de liste de métiers. La boucle « jusqu'au compte » n'existe que pour
  Facebook, sur la même ville.
- **B2. Les sources se relaient, elles ne s'additionnent pas.** Dès qu'une source rend quelque
  chose, les autres ne tournent pas (`scraper_service.py`, `if is_specific and added > 0: break`).
  Une entreprise vue par deux sources n'est jamais fusionnée, alors que Pages Jaunes a le téléphone,
  Google la note et Facebook l'email.
- **B3. Les métiers sont câblés pour 5 ou 6 mots.** OSM connaît restaurant, plombier, electricien,
  coiffeur, boulangerie, garage (`osm_scraper.py:94`). Tout autre métier (paysagiste, barbier, food
  truck, couvreur) devient une recherche **par nom** (`name~"paysagiste"`). Et l'accent casse la
  table : le bouton rapide envoie « Électricien », la table attend « electricien ». Même défaut
  pour Pages Jaunes (`pagesjaunes_scraper.py:86`, `brightdata_scraper.py:43`), d'où le « Pages
  Jaunes vide » du 28 août.
- **B4. Google Maps : une seule requête, 8 défilements, puis chaque fiche ouverte une par une**
  (`google_scraper.py:856-883`), avec jusqu'à 6 pages Google par prospect pour l'email. Lent, et
  Google Maps ne rend qu'environ 120 fiches par requête : sans découpage par ville, on ne voit
  qu'une partie du marché.
- **B5. OSM est presque vide pour ces métiers.** France entière : 1 140 électriciens, 1 337
  plombiers, 896 jardiniers ; 7,7 % ont un email (taginfo, 04/10). Bon pour les horaires à
  l'enrichissement, pas pour trouver.
- **B6. Hors France il ne reste rien côté serveur** : Google Maps mort, Pages Jaunes exclu, OSM
  presque vide. Seul Facebook répond.
- **B7. Facebook : bon principe, exécution bricolée.** Le nom vient du titre du résultat Google, la
  ville n'est pas vérifiée, les candidats sont créés comme prospects puis supprimés, 4 tours au
  plus (`prospectSearch.ts:86`).

### C. Vérifier (l'étape qui n'existe pas)

- **C1. « Sans site » = ce que la source affiche.** Aucune recherche « "nom" ville » pour
  contrôler. À la main, cette étape écarte environ un candidat sur deux (site caché, site généré
  par un annuaire, homonyme, société radiée).
- **C2. Pour Facebook, « sans site » = le champ site de la page est vide** (`prospectSearch.ts:361`).
  Un artisan qui a un vrai site sans l'avoir mis sur sa page passe.
- **C3. « Fermé définitivement » n'est lu nulle part.** En vague 3, deux fiches fermées ont été vues
  à la main.
- **C4. Note et nombre d'avis : aucun seuil.** Ils ne sont lus que par Google Maps (mort). Dans la
  liste des prospects, `google_rating` est vide pour les 118.
- **C5. Aucun filtre « indépendant ».** La liste « ceci n'est pas un vrai site » a été bien étendue
  le 03/10 (annuaires et plateformes CH, BE, LU, CA), mais il manque les mini-sites de réseau
  écartés à la main (top-garage.fr, eurorepar.fr, boschcarservice, myhairbyfiducial.fr,
  digitalone.site, linktr.ee…). Une liste ne sera jamais complète : classer une adresse inconnue
  est un bon travail pour une IA.
- **C6. Doublons : nom + ville exacts seulement** (`prospect_service.py:331`). Rien sur le téléphone,
  la fiche Google, l'email ; la page Facebook n'est comparée que pour la source Facebook.
  « Garage Dupont » et « Dupont Garage SARL » font deux prospects. Aucun contrôle « déjà contacté »,
  « ne plus contacter » ni « supprimé le mois dernier » : risque d'écrire à quelqu'un qui a dit non.
- **C7. La garde anti-homonyme existe à l'enrichissement** (`place_identity_mismatch`), pas à la
  recherche.

### D. Email

- **D1. Trois chercheurs d'email différents.** `email_scraper` (Chrome, avec le tri anti-mairie
  `EmailCandidateScorer`), `brightdata_scraper._serp_email` (serveur, **prend le premier email de
  la page**, sans le tri : `brightdata_scraper.py:442` et `:509`), et la lecture de la page Facebook
  (PC). Le seul qui marche sur le serveur est le moins sûr.
- **D2. Test réel du 04/10.** Requête « "Toupet Entretien Paysager" Trois-Rivières "@gmail.com" » :
  les extraits contiennent les adresses de quatre autres entreprises (paysagementlalonde,
  Elliotthautepression, solutionhaiepilote, plantule) et aucune adresse sûre du prospect. Avec la
  règle « meilleur candidat même à score faible » (choix de Léo du 25/08 : mieux vaut un faux
  positif qu'il verra qu'un prospect perdu), le site de Toupet partirait chez un concurrent sans
  que personne l'ait vu. Le choix reste bon ; il lui manque le niveau de preuve et l'arrêt avant
  l'envoi.
- **D3. Aucune vérification d'adresse avant l'envoi** (syntaxe seulement). Le rebond se voit après.
- **D4. Aucune preuve gardée.** On ne sait pas d'où vient un email (la page du pro, un annuaire, un
  extrait Google). `confidence` (1 à 4) compte les champs remplis, pas la fiabilité de la source.
- **D5. L'email est exigé partout**, alors que le SMS est un canal depuis septembre : un artisan
  avec un portable et sans email est jeté par la source Facebook.

### E. Dirigeant

- **E1. France seulement** (`enrichment_service.py:398`) : 36 % de noms trouvés, 12 % validés seuls.
- **E2. Hors France, rien, alors que la donnée existe** : l'annuaire suisse affiche la personne
  (test : « Cheseaux Paysagiste » → « Cheseaux Stéphane »), le registre suisse porte le nom dans la
  raison individuelle (test : « Graine de Vie paysage - Rossier », CHE-275.432.850), le fichier RBQ a
  un champ « nom de l'intervenant », et un extrait Google suffit parfois (test : « Dany Gauthier -
  Propriétaire chez Capitaine Pelouse »).

### F. Fiche complète

- **F1. Rien ne dit ce qui manque à un prospect** (email prouvé, note, dirigeant, photos, logo).
  C'est la cause directe des allers-retours.
- **F2. L'enrichissement est une étape à part, manuelle, sur le PC**, qui réussit 2 fois sur 3.
- **F3. « Relancer l'enrichissement » écrase les photos et textes triés à la main** (garde-fou
  jamais codé, déjà noté au playbook).

### G. Mesure

- **G1. Aucun rendement connu** : candidats vus, écartés et pourquoi, coût par prospect gardé,
  apport de chaque source.
- **G2. Aucun lien avec les résultats de campagne** (quel profil clique, répond, achète).

## 5. Ce que fait Claude Code à la main

Méthode du playbook (`operations-playbook.md`, étapes 1 et 8), validée sur les vagues 1 à 3.

| Étape | Outil | Rendement observé |
|---|---|---|
| Lister des candidats par métier et ville | Bright Data : recherche Google + lecture de pages (Pages Jaunes, `site:facebook.com`, extraits local.ch) | 30 à 40 candidats pour 18 gardés (vague 1) |
| Contrôler « pas de site » par « "nom" ville » | Bright Data, recherche Google | environ 50 % d'écartés |
| Contrôler ouvert, note, avis | Fiche Google dans un vrai navigateur, ou panneau Google dans la recherche | 2 fermés détectés en vague 3 |
| Trouver l'email | Page Facebook lue dans un navigateur ; annuaires qui l'affichent | 11 emails sur 18 venaient de la page Facebook |
| Écarter les déjà-contactés | Croisement avec la base et les emails envoyés | à la main |
| Dirigeant | API Recherche d'entreprises, plusieurs variantes, adresse comparée | jamais de prénom inventé |
| Équilibrer métiers, pays, villes | Jugement | à la main |
| Photos, logo, tri visuel | Navigateur + agents vision | 40 à 60 % des photos Facebook jetées |

Ce que je fais et que l'app ne fait pas : viser un objectif, changer de ville seul, croiser
plusieurs sources pour une même entreprise, contrôler chaque candidat sur Google, garder la raison
d'un rejet, refuser un email sans preuve. Ce que je fais mal : je repars de zéro à chaque session,
je ne balaie pas une zone en entier, je ne mesure ni le coût ni le rendement, et il faut me lancer.

## 6. Ce qui se fait ailleurs

Recherche web du 04/10 (sources en § 13). [V] = lu sur la page officielle, [T] = source tierce.

- **Tous les outils sérieux filtrent « sans site » et « fermé ».** Apify (`website: withoutWebsite`,
  `skipClosedPlaces`, à partir de 1,5 $ les 1 000 fiches) [V], Outscraper (3 $ les 1 000) [T],
  Scrap.io (49 €/mois) [V].
- **Ils dépassent la limite des 120 résultats en découpant la carte** (sous-zones, codes postaux,
  zoom) puis en dédoublonnant.
- **Ils tirent presque tous l'email du site web.** Mesure Lobstr sur 214 361 fiches : 42,7 % ont un
  email, 14 % seulement pour un métier français sans site [V]. Sur notre cible (sans site), l'email
  est donc le vrai goulot : aucun outil du marché ne le résout pour nous.
- **Le modèle « cascade » (Clay)** : une source à la fois, arrêt à la première donnée vérifiée,
  chaque champ gardé avec sa source et sa date.
- **L'agent IA par ligne (Claygent)** : consignes publiées par Clay [V] : donner tout le contexte de
  la ligne, nommer les sources à consulter, imposer un format de réponse avec l'adresse de la
  preuve, autoriser « non trouvé », contrôler 5 ou 6 lignes à la main. Bon pour juger, mauvais pour
  trouver un fait.
- **Fusion entre sources** : téléphone au format international d'abord, puis nom nettoyé + code
  postal ; la zone de doute part en revue humaine.
- **Vérification d'email** : Reoon 11,90 $ les 10 000, 20 par jour gratuits [V]. Orange et Yahoo
  répondent mal : « inconnu » ne veut pas dire « invalide ».
- **Mobile ou fixe** : le préfixe suffit en France, Suisse et Belgique ; au Québec il faut un
  contrôle payant (0,0025 € par numéro) [V].
- **API officielle Google Places** : `websiteUri`, `businessStatus`, note ; gratuite à notre volume,
  mais ses conditions interdisent de stocker les données (seul l'identifiant se garde) [V]. Non
  retenue comme source.
- **IA avec recherche web intégrée** : l'outil de Mistral coûte 0,03 $ l'appel [V] ; les systèmes
  « compound » de Groq sont annoncés arrêtés le 21/09/2026 [V, à revérifier]. Faire la recherche
  nous-mêmes par Bright Data (1,5 $ les 1 000 requêtes [V]) puis donner les pages à l'IA coûte
  environ vingt fois moins.

## 7. Tests faits pendant l'audit

| Test | Résultat |
|---|---|
| Google « Lieux » (`udm=local`) « paysagiste Sion », pays `ch`, par Bright Data depuis un centre de données | 20 fiches lisibles : nom, note, nombre d'avis, catégorie, ville, téléphone, ouvert ou fermé, bouton « Site Web » présent ou non, identifiant Google de la fiche. **3 sur 20 sans site.** |
| Même chose « paysagiste Trois-Rivières », pays `ca`, page 2 (`start=20`) | 20 autres fiches, pagination fonctionnelle. **5 sur 20 sans site.** |
| Recherche « "Tendance Nature" paysagiste Sion » | Seulement des annuaires : pas de site caché, confirmé en 1 requête |
| Recherche « "Graine de Vie paysage" Valais » | Registre suisse : nom du titulaire (Rossier) et numéro IDE |
| Page annuaire search.ch d'un paysagiste sans site | Nom de la personne, portable, horaires ; pas d'email. Astérisque « ne souhaite pas de publicité » visible sur certaines fiches |
| local.ch par Bright Data | Bloqué (protection anti-robot Anubis) |
| `site:facebook.com "Toupet Entretien Paysager"` | Page Facebook trouvée, avec le nombre de mentions « J'aime » dans l'extrait (signe d'activité) |
| Recherche email par domaines grand public | Faux positifs dangereux (voir D2) |
| Fichier RGE de l'ADEME (API ouverte, sans clé) | 158 797 lignes, 59 515 entreprises. **13 758 entreprises sans site déclaré avec une adresse gmail, orange, wanadoo…** Dans le Rhône : 647 entreprises avec email et sans site déclaré |
| Fichier des licences RBQ (données ouvertes, mis à jour chaque jour) | 54 431 licences actives, 87 % avec courriel. **Électriciens : 4 278, dont 4 049 avec courriel et 1 966 en messagerie grand public. Plombiers : 2 302, 2 108 et 1 069.** |
| OSM (taginfo) | Voir B5 |

Une requête sur six lancées en lot a échoué sans raison (« non-JSON response ») : il faut une
reprise automatique.

## 8. La cible : une seule recherche

### 8.1 Ce que Léo saisit

Un **objectif**, pas une source :

- un ou plusieurs métiers (catalogue de métiers : libellé, synonymes par pays, template liée) ;
- un pays, avec des zones à inclure ou à exclure (« hors Bretagne ») ;
- un nombre par métier ;
- le canal visé : email, SMS ou les deux (décide si l'email ou le portable est obligatoire) ;
- les critères : sans site, site en panne accepté ou non, note minimale, indépendant ;
- un plafond de dépense.

L'app choisit les villes elle-même (communes de la zone par ordre de population) et change de ville
jusqu'au compte.

### 8.2 Les six étapes

1. **Trouver des candidats** (serveur, sans Chrome).
   - Google « Lieux » par Bright Data, page par page, ville par ville, avec les synonymes du
     métier. Source principale, tous pays.
   - Fichiers publics qui portent l'email : RGE (France, bâtiment), RBQ (Québec, bâtiment). On part
     des lignes « email grand public et pas de site déclaré ».
   - `site:facebook.com "métier" "ville"` (existant) pour les commerces sans fiche Google (food
     trucks).
   - Annuaire du pays en lecture fiche par fiche quand il apporte un champ (Pages Jaunes en France).
2. **Fusionner.** Une fiche candidat par entreprise. Clé : téléphone au format international, sinon
   identifiant Google de la fiche, sinon adresse de la page Facebook, sinon nom nettoyé + code
   postal. Chaque champ garde sa source et sa date. Le candidat est comparé aux prospects existants
   (toutes les clés), aux emails déjà envoyés, à « ne plus contacter » et aux candidats déjà
   écartés.
3. **Vérifier.** Une recherche Google « "nom" ville » par candidat. Les dix résultats passent par
   des règles (domaines connus) puis par l'IA pour le reste. Verdicts, chacun avec l'adresse qui le
   prouve : site propre ou non, site vivant ou mort (service existant), fermé, homonyme, chaîne ou
   réseau, page Facebook, Instagram, numéro de registre.
4. **Email, en cascade, arrêt au premier email prouvé.**
   1. donné par une source officielle ou par le pro (RGE, RBQ, fiche d'annuaire) ;
   2. bloc « À propos » de sa page Facebook (lecture par le PC, ou service payant à tester) ;
   3. extrait Google de **sa** page Facebook ou Instagram ;
   4. annuaires qui affichent l'email ;
   5. recherche large, puis l'IA répond à une seule question : « cette adresse appartient-elle à ce
      commerce, et où est-ce écrit ? ».

   Ensuite contrôle technique (syntaxe, domaine qui reçoit du courrier, vérificateur). Niveau de
   preuve gardé : **A** publié par le pro ou un registre officiel, **B** annuaire tiers, **C**
   trouvé par recherche, sans preuve franche. A et B entrent en campagne. C n'est pas jeté (choix
   de Léo du 25/08) : il est montré avec l'extrait où il a été trouvé et attend un clic.
5. **Dirigeant.** France : cascade actuelle. Suisse : nom de la raison individuelle ou personne de
   l'annuaire. Québec : « nom de l'intervenant » RBQ. Partout : extrait Google « propriétaire »
   jugé par l'IA. Toujours « à confirmer » sans source officielle ; jamais de prénom inventé.
6. **Fiche complète.** Une pastille par prospect dit ce qui manque. Les photos, avis et horaires
   partent seuls en file sur le PC quand l'app desktop est ouverte. Le tri fait à la main n'est
   plus écrasé.

À la fin, un écran de revue : gardés, écartés avec la raison, à confirmer. Un clic corrige un
verdict et l'app s'en souvient.

### 8.3 Ce qu'on reprend de chaque source actuelle

| Source actuelle | Ce qu'on garde | Ce qui part |
|---|---|---|
| Google Maps (Chrome) | Le lecteur de fiche (`_extract_current_place`), `extract_city` par pays, la lecture note + avis : pour l'enrichissement sur PC et l'ajout manuel | La découverte par Chrome |
| Pages Jaunes | Le lecteur de fiche par HTTP, la détection de blocage, le lien social de la fiche | Le choix « source Pages Jaunes » |
| Bright Data | `BrightDataClient` devient le moteur de toute la recherche ; la requête « "nom" "téléphone" », la plus précise | Le premier-email-trouvé |
| OSM | `osm_enrichment` (horaires, réseaux) à l'enrichissement | La découverte OSM |
| Auto | L'idée de fusion par nom nettoyé | Le reste |
| Facebook | Nettoyage des adresses de page et des titres, pages exclues gardées en base, boucle jusqu'au compte, requête « gmail.com » | Les prospects créés puis supprimés |
| Email | `EmailCandidateScorer` (anti-mairie, annuaires par pays), appliqué partout ; « garder le meilleur même à score faible » reste | L'envoi d'un email de niveau C que Léo n'a pas vu |
| Dirigeant | La cascade et le niveau « à confirmer », modèle pour tous les verdicts | Rien |
| Site vivant ou mort | `website_liveness_service` dans l'étape Vérifier | Rien |
| Diagnostics | Les incidents par source et la capture de page bloquée | Rien |

### 8.4 Où l'IA sert, et où elle ne sert pas

Modèle : Groq `gpt-oss-120b` en réponse structurée (déjà en place dans `llm_service`), Mistral en
secours.

Elle sert à :
- classer les résultats de la recherche de vérification (site propre, annuaire, réseau, homonyme) ;
- dire si un email appartient au commerce, avec la preuve ;
- lire un nom de dirigeant dans un extrait ;
- dire si une catégorie Google floue correspond au métier (« Service d'entretien de pelouse » pour
  un paysagiste) ;
- proposer les synonymes d'un métier par pays ;
- écrire la raison d'un rejet en mots simples.

Elle ne sert pas à : inventer un email ou un nom, répondre de mémoire sur une petite entreprise,
dédoublonner (du code suffit), vérifier une adresse, décider seule d'un envoi. Règles : toujours une
page déjà lue en entrée, toujours l'adresse de la preuve en sortie, « non trouvé » autorisé.

### 8.5 Serveur ou PC

Étapes 1 à 5 : sur le serveur, en tâche de fond enregistrée en base, qui reprend après un
déploiement. La recherche marche donc depuis le web et le téléphone. Restent sur le PC : la lecture
des pages Facebook (tant qu'un service payant n'est pas retenu) et les photos, avis et horaires.

### 8.6 La mémoire

Deux tables : les recherches (objectif, état, compteurs, coût) et les candidats (fiche, sources,
verdicts, raison du rejet). C'est ce qui manque le plus à Claude Code : un candidat écarté n'est
jamais re-testé, une zone balayée est connue, un rejet corrigé par Léo sert aux recherches
suivantes.

### 8.7 Coût (ordre de grandeur, à mesurer au premier lot)

Environ 12 à 15 requêtes Bright Data par prospect gardé (listes, vérification, email), soit environ
0,02 $ ; l'IA ajoute des centimes par semaine. 100 prospects gardés : autour de 2 $. Lecture
Facebook par un service payant, si retenue : environ 10 $ les 1 000 pages.

## 9. En quoi elle peut devenir meilleure que Claude Code

1. Elle se souvient de tout ce qu'elle a vu et écarté.
2. Elle balaie une zone en entier, toutes les pages, au lieu de s'arrêter au compte.
3. Elle fait les mêmes contrôles à chaque fois et garde la preuve.
4. Elle filtre un fichier public de 50 000 lignes en une seconde.
5. Elle tourne la nuit, sans session ouverte, et reprend après une coupure.
6. Elle apprend des campagnes : un score de potentiel recalé sur les clics et les réponses.
7. Elle connaît son coût par prospect.

Limites honnêtes : le jugement fin (une photo représentative, le ton d'une page) restera moins bon,
d'où la file « à confirmer ». Facebook reste le point dur. Et tant qu'elle n'a pas été comparée à
une liste vérifiée à la main, on ne lui fait pas confiance (voir idée 23).

## 10. Plan en lots

| Lot | Contenu | Taille |
|---|---|---|
| 0 | Sécurité immédiate : le tri anti-faux-positif dans `brightdata_scraper`, accents dans les tables de métiers | petit |
| 1 | Socle : tables des recherches et des candidats, tâche de fond qui reprend, clés d'identité, doublons élargis (téléphone, Facebook, fiche Google, email, déjà contacté, ne plus contacter) | moyen |
| 2 | Vérification d'un candidat : recherche « "nom" ville », règles + IA, fermé, homonyme, réseau, preuve. Utilisable aussi sur l'import, l'ajout manuel et les prospects existants | moyen |
| 3 | Découverte : Google « Lieux » par Bright Data (lecteur, pagination, villes, synonymes) + fichiers RGE et RBQ | moyen |
| 4 | Email prouvé : cascade, niveaux A, B, C, contrôle technique, file de lecture Facebook sur PC, essai d'un service de lecture côté serveur | gros |
| 5 | Écran « recherche par objectif » : formulaire, progression, revue des gardés, écartés et à confirmer, envoi vers une campagne ; retrait du choix de source | gros |
| 6 | Fiche complète : pastille, enrichissement en file, garde-fou sur le tri manuel | moyen |
| 7 | Dirigeant hors France, score de potentiel, tableau de rendement et de coût | moyen |

Ordre conseillé : 0, 1, 2, 3 d'abord. Ce sont eux qui suppriment les allers-retours et qui rendent
la Suisse et le Québec cherchables, donc utiles à la vague 4.

Avant de faire confiance au moteur : le rejouer sur les prospects des vagues 1 à 3, déjà vérifiés à
la main, et compter les écarts.

## 11. Idées en vrac

1. Partir des fichiers qui portent l'email (RGE, RBQ, fichier de contacts de la BCE belge à mesurer)
   au lieu de chercher l'email à la fin.
2. Une adresse gmail, orange, bluewin ou videotron est un indice « pas de site ». Un domaine
   personnel dans l'email : tester le domaine (site caché, ou site en panne = angle existant).
3. Indice d'activité : nombre de mentions « J'aime », dernier message Facebook, avis récents ;
   écarter les pages mortes.
4. Critère « entreprise récente » (date de création dans l'API Recherche d'entreprises).
5. Lire l'astérisque « pas de publicité » de l'annuaire suisse et ne pas envoyer de SMS à ces
   numéros (règle suisse à vérifier).
6. Recherche « en miroir » : partir d'un prospect qui a répondu et chercher ses semblables.
7. Seuils par métier appris des vagues (artisans 45 % de clics, food et barbiers 14 %).
8. Zone d'exclusion permanente (Bretagne) enregistrée dans le compte.
9. Équilibrage automatique : même nombre par métier et par pays (exigence de la vague 4).
10. Tirage au sort du canal email ou SMS parmi ceux qui ont les deux (vague 4).
11. Arrêt sur budget : N prospects ou X requêtes.
12. Recherche programmée : « 20 nouveaux paysagistes suisses chaque lundi ».
13. Carte de couverture nourrie par les zones déjà balayées et leur rendement.
14. Le même moteur sur un prospect collé à la main ou importé (bouton « Vérifier »).
15. Nouveau contrôle la veille de l'envoi : fermé, ou a maintenant un site.
16. Repérer « a déjà un prestataire web » (mini-site d'annuaire) : autre angle ou rejet.
17. Option « site en panne » : produire exprès ces prospects.
18. Logo depuis la photo de profil Facebook, côté serveur (méthode validée sur 51 pages).
19. Garder 30 jours les extraits qui prouvent un verdict.
20. Bouton « pourquoi écarté » et bouton « récupérer » sur chaque candidat.
21. Coût affiché par recherche et par prospect gardé.
22. Catalogue de métiers en base : synonymes par pays, catégories Google acceptées, codes RGE et
    RBQ, template liée.
23. Jeu d'essai permanent : les prospects vérifiés à la main servent d'examen au moteur à chaque
    changement.
24. Mode « réceptionniste » : mêmes étapes, critère « sans site » retiré.
25. Apify (filtre « sans site » natif) comme solution de secours si Google « Lieux » change.
26. Accepter « portable sans email » quand le canal de l'objectif est le SMS.
27. Un seul client HTTP avec reprise automatique et compteur de requêtes.

## 12. Limites à connaître

- **Annuaire suisse (search.ch, local.ch)** : l'extraction en masse est interdite par leurs
  conditions, et la clé gratuite de leur API est réservée à l'usage non commercial avec une
  pénalité prévue au contrat. On ne prend pas cette clé. Google « Lieux » sert à trouver ;
  l'annuaire se consulte fiche par fiche, comme le ferait une personne.
- **Belgique** : la recherche publique du registre (BCE) interdit la réutilisation ; son fichier
  ouvert interdit le démarchage des entreprises en nom propre. Consultation fiche par fiche
  seulement.
- **Google Places (API officielle)** : stockage interdit, donc non retenue.
- **Facebook** : la lecture sans connexion reste fragile et plafonnée ; l'API officielle n'est pas
  ouverte à la prospection.
- **Fichiers RGE et RBQ** : bâtiment seulement. Rien pour paysagiste, garage, barbier, food truck.
  « Pas de site déclaré » ne prouve pas l'absence de site : l'étape Vérifier reste nécessaire.

## 13. Sources

Outils et prix : apify.com/compass/crawler-google-places · scrap.io/pricing ·
lobstr.io/blog/google-maps-email-extractor · clay.com/guides/how-to-use-claygent-for-prospect-research ·
exa.ai/pricing · reoon.com/email-verifier · hlr-lookups.com/en/pricing · brightdata.com/pricing/serp ·
brightdata.com/pricing/web-unlocker · serper.dev · apify.com/apify/facebook-pages-scraper

Google : developers.google.com/maps/billing-and-pricing/pricing ·
developers.google.com/maps/documentation/places/web-service/policies

IA : console.groq.com/docs/deprecations · console.groq.com/docs/browser-search ·
mistral.ai/pricing/api · docs.mistral.ai/agents/connectors/websearch

Données publiques : data.ademe.fr/datasets/liste-des-entreprises-rge-2 ·
donneesquebec.ca/recherche/dataset/licencesactives · recherche-entreprises.api.gouv.fr/docs ·
zefix.admin.ch/ZefixPublicREST/v3/api-docs · search.ch/tel/api/terms ·
kbopub.economie.fgov.be · taginfo.openstreetmap.org/keys/craft
