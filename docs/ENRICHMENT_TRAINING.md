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
| n° 351 fermé, enrichi comme ouvert | Personne ne relisait le registre à l'enrichissement | Registre suisse lu à l'enrichissement : en liquidation ou radiée depuis moins de 3 ans → « Ne plus contacter » avec la raison |
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
