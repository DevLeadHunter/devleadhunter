# Entraînement de la recherche de prospects

Carnet des manches qui rendent la recherche de l'app meilleure que la recherche faite à la main avec
Claude Code. Commencé le 6 octobre 2026, pendant le sourcing de la vague 4.

## La méthode

Une manche = un objectif réel de la vague 4 (métiers, pays, nombre, canal). Les prospects trouvés
servent à la campagne : rien n'est cherché pour rien.

1. Recherche à la main d'abord (Bright Data, annuaires, navigateur), sans regarder l'app.
2. Recherche de l'app sur le même objectif, en mode « Je valide » : rien ne devient prospect avant le
   contrôle.
3. Vérité terrain : chaque business trouvé par l'un ou l'autre est contrôlé à fond (site, ouvert,
   email qui est bien le sien, portable, mention « pas de publicité », déjà contacté).
4. Note de la manche : bons prospects trouvés, gardés à tort, ratés, requêtes, temps.
5. Chaque écart reçoit sa cause, puis une correction du moteur et un test qui la rejoue.

Les deux méthodes ne cherchent pas forcément dans les mêmes villes : un raté de l'app dans une ville
qu'elle n'a pas parcourue est un écart de zones, pas de vérification.

## Manche 1 — Suisse, 5 garages + 5 électriciens, email (6 octobre)

Recherche de l'app n° 3 (moteur du 5 octobre), lancée en même temps que la recherche à la main.

### À la main

Méthode : pages de l'annuaire search.ch par ville et par métier, recherches Google
`site:local.ch <métier> <canton> "gmail.com"` (les extraits de local.ch montrent l'email, les numéros
et leur astérisque), contrôle « "nom" ville », fiche vCard de search.ch pour l'email, le site et les
portables.

- Environ 9 minutes, environ 90 requêtes Bright Data (une sur trois sans réponse ce soir-là) et 14
  lectures directes de search.ch.
- 8 businesses retenus, 6 bons après contrôle : un déjà contacté en vague 3 (oublié de croiser avec la
  base) et un qui porte l'astérisque « ne souhaite pas de publicité » (vu après coup dans l'annuaire).
- Bons : Garage du Valais (Saxon), Garage Touring AC (Romont), Satuev Automobiles (Moudon), Dias
  automobiles (Fribourg), Garage du Canada (Vétroz), Atelier E (Martigny, site « bientôt en ligne »).

### Par l'app

- Villes tirées : Vevey et Neuchâtel pour les garages ; Vevey, Neuchâtel, Montreux, Yverdon, Sierre,
  Aigle pour les électriciens.
- Garages : 5 gardés dans les deux premières villes, en moins de 6 minutes.
- Électriciens : presque tous ont un site dans les grandes villes (Vevey : 0 fiche sans site déclaré
  sur 20 ; Neuchâtel : 1 sur 49). Gardés : un électricien dont le site est suspendu (Auvernier), un
  dont le domaine n'existe plus (Sierre), et un commerce « Multimedia & Electro » de Sierre au métier
  douteux.

### Écarts et causes

| Écart | Cause | Correction |
|---|---|---|
| 2 des 5 garages gardés (Vevey, Neuchâtel) refusent la publicité dans l'annuaire suisse ; 1 des 8 trouvés à la main aussi | L'astérisque de search.ch n'était lu par personne. La loi suisse interdit la publicité à ces abonnés (LCD art. 3 al. 1 let. u) | Fiche search.ch lue par le numéro de chaque candidat suisse : astérisque = écarté (« Refuse la publicité »), et mémorisé comme un site ou une fermeture |
| Montreux et Yverdon comptées comme parcourues sans aucune fiche lue (40 électriciens) | Google n'a pas répondu à leur première page (Bright Data surchargé) ; le moteur prenait l'absence de réponse pour une ville vide | Une ville sans réponse est retentée en fin de tour, puis laissée pour une reprise, jamais comptée comme parcourue |
| Les électriciens des grandes villes ont presque tous un site | Les 20 villes suisses du moteur sont les plus grandes de Romandie | 49 petites villes ajoutées (Saxon, Fully, Moudon, Romont, Echallens…), tirées avec les grandes |
| Des emails et des sites connus de l'annuaire restaient invisibles | La fiche vCard de search.ch donne l'email, le site et les portables d'un abonné | Lue avec l'astérisque : son email devient une preuve « annuaire » (B), son site est contrôlé comme les autres |

Deux écarts de plus sont apparus en rejouant la manche dans le moteur corrigé :

| Écart | Cause | Correction |
|---|---|---|
| Un garage de Romont écarté pour un « site » qui était sa page de vendeur autoscout24 | Le bouton « Site Web » de sa fiche Google pointe vers autoscout24, inconnu de la liste des annuaires et places de marché | autoscout24, motoscout24 et 25 annuaires ou comparateurs suisses rencontrés pendant la manche ajoutés à la liste |
| L'email de l'annuaire d'un électricien de Martigny ignoré | La fiche search.ch porte « Atelier E SA - Prénom Nom », trop loin du nom de la fiche Google | Une fiche d'entreprise trouvée par le numéro du candidat est crue ; seule la fiche d'un particulier qui partage le numéro doit nommer le business |
| Un électricien de Sierre gardé avec un email sur un domaine mort | Les serveurs DNS du domaine répondent tous en échec ; le contrôle prenait ça pour une lenteur | Un domaine dont tous les serveurs échouent, vérifié par des résolveurs publics qui répondent pour gmail.com, ne reçoit pas de courrier |

### Résultat de la manche

Vérité terrain des 15 businesses retenus par l'une ou l'autre méthode (aucun en commun : les villes
diffèrent) :

| | Retenus | Bons | Faux |
|---|---|---|---|
| App, moteur du 5 octobre | 10 | 5 | 4 refusent la publicité, 1 email sur un domaine mort |
| À la main | 8 | 6 | 1 déjà contacté, 1 refuse la publicité (et a un site) |
| Moteur corrigé, mêmes businesses rejoués | 10 gardés | 10 | 0 (les 5 faux de l'app et le faux à la main rejoué écartés pour la bonne raison) |

Le rejeu (17 businesses, 32 requêtes, 14 appels du juge) classe chaque business comme le contrôle à la
main. Un garage de Vevey dont l'email vient de sa page Facebook attend la lecture de la page : la
recherche réelle l'avait gardé avec cet email. Le prospect déjà contacté n'est pas rejoué : la mémoire
des prospects l'écarte avant toute vérification.

Coût de la recherche de l'app : 25 minutes, 313 requêtes (environ 0,47 $), 104 appels du juge, 7
villes dont 2 sans réponse de Google. 114 des 145 écartés avaient un site : les grandes villes coûtent
cher pour les électriciens.

## Manche 2 — Suisse, garages + électriciens, email (6 octobre)

Recherche de l'app n° 4 sur les six villes de mes trouvailles de la manche 1 (Saxon, Romont, Moudon,
Fribourg, Vétroz, Martigny), 8 par métier. Les corrections de la manche 1 ont été déployées pendant
qu'elle tournait : les garages ont été vérifiés avant celle de la fiche search.ch ouverte
directement, les électriciens après.

### Par l'app

- Garages : objectif atteint autour de Saxon (10 gardés) avant Romont, Moudon, Fribourg et Vétroz. La
  comparaison avec la main ne vaut donc que pour Saxon et Martigny.
- Électriciens : 4 gardés sur 8 ; l'astérisque de l'annuaire en a écarté une quinzaine.
- 368 requêtes, 88 appels du juge. La recherche s'est arrêtée en attendant la lecture de trois pages
  Facebook par le PC ; l'API a répondu par une erreur 500 à la dernière (corrigé, voir plus bas).

### Vérité terrain des 15 gardés et du candidat à confirmer

| | Nombre | Détail |
|---|---|---|
| Bons | 3 | Garage des Bains (Saillon), SwedenSpeed (Saxon), Jantes Alu (Saxon, site mort) : prospects 261 à 263 |
| Refusent la publicité | 7 | 4 garages vérifiés avant le déploiement du correctif de la fiche ouverte directement, 2 dont l'astérisque est sur un second numéro, 1 garage au nom de son patron trouvé seulement par le nom |
| En liquidation au registre du commerce | 3 | dont le candidat à confirmer |
| Adresse en France | 1 | Romont existe aussi dans les Vosges |
| Site en ligne | 1 | page « bientôt en ligne » servie avec le code 503, prise pour un site mort |
| Page Facebook d'une association | 1 | ni téléphone ni adresse, email d'une association professionnelle |

### Écarts et causes

| Écart | Cause | Correction |
|---|---|---|
| 2 astérisques manqués sur une fiche pourtant lue | L'astérisque d'un second numéro (le portable du patron) est écrit après le lien, pas dedans | Les deux écritures sont lues |
| Un garage au nom de son patron, absent de l'annuaire sous son numéro, refuse la publicité sur la fiche du garage | La fiche n'était cherchée que par le numéro | Numéro absent : l'annuaire est cherché par le nom dans la ville ; une fiche d'entreprise qui nomme le business, ou son patron sur sa ligne supplémentaire, transmet son astérisque |
| 3 sociétés en liquidation gardées ou à confirmer | Le registre du commerce l'écrit dans le titre (« … Sàrl en liquidation ») ; rien ne le lisait | Un titre de registre qui nomme le business « en liquidation » (ou radié) l'écarte comme fermé, avec la source |
| Un électricien des Vosges gardé dans une recherche suisse | Google renvoie aussi le Romont français ; l'adresse finissait par « France » | Une adresse qui finit par un autre pays est écartée (« Dans un autre pays ») avant toute requête payante |
| Une page Facebook d'association gardée comme électricien | Une page trouvée par la recherche Facebook, sans téléphone, gardée sur son seul email | Une page Facebook sans téléphone va dans « À confirmer », jamais dans les gardés |
| Un électricien de Martigny gardé avec un « site mort » | Son site « bientôt en ligne » répond avec le code 503 | Un 503 qui sert la page du site compte comme un site en ligne ; une page d'hébergeur (« site suspendu ») reste un site mort |
| Erreur 500 quand le PC rend la dernière page Facebook attendue | La recherche redémarre, et l'API renvoyait le candidat après avoir rendu sa connexion à la base | Le candidat est relu avant de rendre la connexion ; un test rejoue l'erreur |
| Un garage cherché sous le nom de sa fiche Google, alors que l'annuaire et son site portent un autre nom | Le site n'est cherché que sous le nom de la fiche Google | Pas corrigé : l'astérisque l'écartait de toute façon |

### Retour sur la manche 1

- Garage du Valais (Saxon), compté bon à la main, a un nouveau site en ligne (l'annuaire donnait
  l'ancienne adresse, morte) : l'app l'a trouvé et l'a écarté à raison.
- Un des cinq prospects créés à la manche 1 porte l'astérisque sur un second numéro : marqué « Ne
  plus contacter ».

### Résultat de la manche

Rejeu de 22 candidats dans le moteur corrigé (80 requêtes, 10 appels du juge, 4 vérifications sans
réponse de Google) : chaque faux dont la cause était corrigée est écarté pour la bonne raison. Les
corrections suivantes (liquidation, recherche par le nom, second numéro, code 503) ont été vérifiées
sur les fiches et les sites réels des candidats concernés.

La manche rapporte 3 prospects pour 15 gardés : la précision de l'app passe avant la vitesse pour la
prochaine manche.

## Manche 3 — Suisse, 8 paysagistes, email (6 octobre au soir)

Recherche de l'app n° 5, villes choisies par le moteur (Jura, Jura bernois, Neuchâtel, Chablais,
Lavaux, Bienne), avec les corrections de la manche 2 en production.

### À la main

Listes search.ch « paysagiste » de Fully, Conthey, Savièse et Collombey-Muraz : 21 entreprises, dont
12 avec l'astérisque dans la liste. Des 9 autres, aucun prospect par email : sites en ligne, une
société en liquidation, pas d'email trouvé, et une fiche dont l'astérisque n'apparaît que sur la page
complète (un second numéro).

### Par l'app

- 7 gardés sur 8 demandés, en 40 minutes : 423 requêtes (environ 0,63 $), 78 appels du juge.
- 197 candidats : 81 refusent la publicité (41 %), 36 ont un site, 22 sont d'un autre métier.
- Vérité terrain des 7 gardés : 4 bons (La Ferrière, Porrentruy, Servion, Châtel-Saint-Denis, ce
  dernier avec un site mort) : prospects 264 à 267. 3 faux : le même paysagiste gardé deux fois
  (deux fiches Google, un seul numéro), l'email d'un magazine français dont la page Facebook avait
  parlé d'un homonyme, et l'email d'un homonyme belge.

### Écarts et causes

| Écart | Cause | Correction |
|---|---|---|
| Une fiche trouvée par le nom passait pour sans astérisque | La liste de search.ch ne montre pas l'astérisque d'un second numéro | La fiche trouvée par le nom est lue en entier (page et vCard), comme celle trouvée par le numéro |
| Un paysagiste écarté pour l'astérisque d'une autre entreprise | « André » était trouvé dans « Alexandre » : les mots du nom étaient cherchés comme des bouts de texte | Les mots distinctifs du nom se comparent mot à mot |
| Un même paysagiste gardé deux fois | Deux fiches Google ; le numéro et l'email n'apparaissent qu'à la vérification, après le contrôle des doublons | Un business déjà proposé par la recherche est reconnu à son numéro ou à son email, même sous une autre fiche |
| L'email d'un magazine gardé pour un paysagiste | Une publication qui nomme le business faisait de la page qui l'a publiée la page du business | Une publication ne compte que si l'adresse de la page porte le nom du business |
| L'email d'un homonyme belge gardé | Le résultat nomme le business mais montre un autre numéro (belge) | Un résultat qui nomme le business mais ne montre que d'autres numéros est celui d'un homonyme |
| Des comparateurs (horticole-comparatif, gartenbauvergleich…) et des pages de réseau (autofit) risquaient de passer pour des sites | Absents de la liste des tiers | Tout domaine « comparatif », « vergleich », « comparison » ou « comparazione » est un tiers ; autofit, landi et deux annuaires ajoutés |
| Le suivi de la recherche s'arrêtait pendant un déploiement ou une coupure de la base | La ligne de commande quittait à la première erreur de l'API | Elle réessaie pendant cinq minutes ; une lecture Facebook non transmise sera relue |

### Résultat de la manche

Les paysagistes suisses sont la case la plus difficile : 4 bons pour 197 candidats. L'astérisque en
écarte deux sur cinq, et la loi l'impose.
