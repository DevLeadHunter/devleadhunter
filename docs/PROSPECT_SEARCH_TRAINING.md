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

## Manche 4 — France, paysagistes + garages + électriciens, email (6 octobre au soir)

Recherche de l'app n° 6, villes choisies par le moteur (Dijon, Rouen, Blois et leurs environs), 8 par
métier : 25 gardés en 36 minutes, 385 requêtes, 54 appels du juge. Les électriciens viennent tous de
la liste des entreprises RGE.

### Vérité terrain des 25 gardés

| | Nombre | Détail |
|---|---|---|
| Bons | 9 | 3 paysagistes, 4 garages, 2 électriciens (dont un site mort) : prospects 268 à 276 |
| Site en ligne | 8 | dont 2 dont l'email était lu sur leur propre site, 1 dont le domaine de l'email épelle le nom, 1 dont le nom de fiche contient le domaine |
| Email d'un tiers | 3 | la boîte `dpo@` d'une plateforme d'artisans, l'adresse d'un réseau de garages, celle d'un groupe de distribution |
| Autre métier | 3 | un plombier et deux chauffagistes venus de la liste RGE |
| Autre métier non vérifiable | 1 | laissé à confirmer |

En plus, 4 businesses joignables par SMS seulement (prospects 277 à 280) complètent la campagne SMS
France.

### Écarts et causes

| Écart | Cause | Correction |
|---|---|---|
| L'email lu sur le site du business, et le site ignoré | Le site porte un autre nom que la fiche Google (« Passion Paysage 21 » pour « Plaisir Paysage ») | Un site qui n'est pas un annuaire, qui publie l'email et dont l'adresse reprend un mot de cet email, est le site du business |
| Un domaine d'email au nom du business, et son site ignoré | La page d'accueil ne nomme pas le business et la fiche n'a pas de téléphone | Un domaine qui épelle le nom du business, à une lettre près, suffit |
| Une fiche nommée « … Dijon-Paysagiste.fr » gardée sans site | Le nom de la fiche n'était pas lu | Un domaine écrit dans le nom est contrôlé comme son site |
| Emails de plateformes, de réseaux de garages, d'un groupe | Domaines absents des listes | Plateformes d'artisans, réseaux de garages, marques et groupe ajoutés ; boîtes `dpo@`, `rgpd@`, `privacy@`… jamais retenues |
| Un plombier et des chauffagistes proposés comme électriciens | La liste RGE des électriciens comptait la « Ventilation mécanique » | Seuls les « Radiateurs électriques » restent |

### Résultat de la manche

9 bons pour 25 gardés. Chaque faux a sa correction, en production le soir même.

## Manche 5 — Québec, paysagistes + garages + électriciens, email (6 octobre au soir)

Recherche de l'app n° 7, villes choisies par le moteur (Trois-Rivières, Joliette, Victoriaville,
Repentigny, Saint-Jérôme), 7 par métier : 25 gardés en une heure, 506 requêtes, 65 appels du juge
(le quota quotidien du juge était épuisé pendant une partie de la recherche). Les électriciens
viennent tous du fichier des licences de la RBQ.

### Vérité terrain des 25 gardés

| | Nombre | Détail |
|---|---|---|
| Bons | 16 | 5 paysagistes, 5 garages, 6 électriciens avec leur licence RBQ : prospects 281 à 296 |
| Site en ligne | 3 | dont un site « en construction » |
| Autre métier | 2 | un vendeur de portes de garage, une entreprise d'excavation |
| Email d'un tiers | 2 | le commentaire d'une entreprise de ménage sous une annonce d'emploi, l'adresse d'un réseau de santé |
| À confirmer | 2 | l'email de la page Facebook ne correspond pas sûrement au garage |

### Écarts et causes

| Écart | Cause | Correction |
|---|---|---|
| 76 garages sur 104 écartés comme « autre métier » | Sur les fiches québécoises sans catégorie, le numéro de téléphone ou la rue prenaient la place de la catégorie | Un téléphone ou une rue n'est jamais une catégorie ; le numéro est gardé |
| Un hôpital proposé comme électricien | Le fichier de la RBQ liste aussi les établissements qui ont une licence ; ses emails n'étaient pas filtrés | Les établissements publics (nom ou domaine d'email) sont écartés des registres |
| Un vendeur de portes de garage pris pour un garage | « garage » dans la catégorie suffisait | Les catégories de portes sont exclues |
| L'email d'un commentateur gardé | Le résumé d'une publication de groupe Facebook mélange les commentaires | Aucun email n'est pris sous une publication de groupe |
| Un annuaire (411habitation) pris pour le site d'un paysagiste | Absent de la liste des tiers | Ajouté |

### Résultat de la manche

16 bons pour 25 gardés. Au Québec, presque tous les paysagistes ont un site : les garages et les
électriciens de la RBQ rendent mieux.

## Manche 6 — France, paysagistes + garages + électriciens, email (6 octobre, nuit)

Recherche de l'app n° 8 (Pau, Gap, Limoges et alentours), 7 par métier, sans le juge (quota
quotidien épuisé) : 24 gardés en 51 minutes, 529 requêtes.

### Vérité terrain des 24 gardés

| | Nombre | Détail |
|---|---|---|
| Bons | 17 | 4 paysagistes, 6 garages, 7 électriciens (dont 4 sites morts) : prospects 297 à 313 |
| Email d'un tiers | 4 | un réseau social russe, une publication de groupe Facebook, un site romain dont le numéro a les mêmes chiffres, un appel d'offres public qui liste plusieurs entreprises |
| Site en ligne | 2 | dont un site injoignable ce soir-là mais indexé, d'un garage de dix salariés |
| Autre métier | 1 | un plombier venu de la liste RGE |

### Écarts et causes

| Écart | Cause | Correction |
|---|---|---|
| Un email lu sur un site italien gardé pour un garage français | Un fixe romain (indicatif 06) avait les mêmes dix chiffres que le portable français du garage | Une page d'un autre pays (domaine national) ne prouve rien par le numéro |
| Un email lu dans un appel d'offres | Un document liste plusieurs entreprises : un numéro et un email s'y côtoient par hasard | Aucun email n'est pris dans un document téléchargé |
| Un email pris sous une publication de groupe Facebook, par la recherche du numéro | La règle des groupes ne couvrait que la recherche par email | Elle couvre aussi la recherche par le numéro |

### Résultat de la manche

17 bons pour 24 gardés : la France email est presque complète (39 sur 40).

## Manches 7 et 8 — Suisse garages + électriciens, Québec garages + électriciens (nuit du 6 au 7 octobre)

| Recherche | Gardés | Bons | Faux |
|---|---|---|---|
| n° 9, Suisse, 8 par métier (90 minutes, 664 requêtes) | 11 | 5 (prospects 315 à 319) | 2 astérisques ratés, 2 sites, 2 vendeurs de voitures d'occasion |
| n° 10, Québec, 4 par métier (12 minutes, 99 requêtes) | 10 | 9 (prospects 320 à 328) | 1 site |

### Écarts et causes

| Écart | Cause | Correction |
|---|---|---|
| Un garage « … Sàrl » dont la fiche de l'annuaire porte l'astérisque passait pour non listé | search.ch exige tous les mots : la forme juridique (« Sàrl ») absente de la fiche la cachait | Le nom est cherché sans sa forme juridique (Sàrl, SA, GmbH, Inc…) |
| Un domaine d'email au nom du garage (« adnauto.ch » pour « ADN Autos Sàrl ») non relié | La forme juridique faussait la comparaison | La comparaison se fait sans forme juridique |
| Un électricien gardé alors que son numéro porte l'astérisque dans l'annuaire | Un annuaire qui ne répond pas (limite de requêtes, panne) était lu comme « pas listé » | Annuaire muet = « À confirmer » (astérisque non lu) ; une fiche sans vCard est lue quand même |

### Résultat

Le 7 octobre à 2 h 15 : France email 40/40, Québec 25/20, SMS France 15/15, Suisse 16/40.

## Manche 9 — Suisse, les trois métiers (nuit du 7 octobre)

| Recherche | Gardés | Bons | Faux |
|---|---|---|---|
| n° 11, Suisse, 8 par métier (3 h, 863 requêtes, 147 appels au juge) | 17 | 12 (prospects 329, 330, 332 à 341) | 2 emails d'une autre entreprise (la galerie d'un proche, un autre garage), 1 profil Facebook d'un particulier, 1 seconde fiche d'un astérisque, 1 carrosserie d'un groupe qui a son site |

Les fiches restées « à valider » dans les recherches 1 à 9 ont été reprises : 7 portaient l'astérisque, une entreprise était radiée, un garage était bon (son email était dans l'annuaire, Google n'avait pas répondu) : prospect 331.

### Écarts et causes

| Écart | Cause | Correction |
|---|---|---|
| Un paysagiste « F. … Sàrl » passait pour absent de l'annuaire alors que son patron y figure, à la même adresse, avec l'astérisque | Le numéro de l'entreprise n'est pas listé et le nom (« F. … ») ne trouve pas la fiche (« …, Prénom ») | L'annuaire est aussi lu à l'adresse de la fiche, sous le nom de famille ; seule la même adresse compte, pas un homonyme plus loin dans la rue |
| La moitié des paysagistes suisses coûtaient une recherche Google pour finir écartés par l'astérisque | L'annuaire n'était lu qu'après la recherche Google | L'annuaire (gratuit) est lu d'abord : une fiche à astérisque ne coûte plus de requête payante ni d'appel au juge |
| Un tiers des fiches coûtaient une recherche Google pour découvrir leur site | Le bouton « Site Web » de la fiche Google n'était pas suivi | Le bouton est suivi (une simple redirection de Google, gratuite) : un site en ligne écarte la fiche sans requête payante |
| Des fiches restaient « à valider : site déclaré mais pas retrouvé » | Leur bouton « Site Web » mène à leur page d'annuaire (yellow.local.ch), pas à un site | Un bouton qui mène à un annuaire ne compte plus comme un site ; vers une page Facebook, il donne la page |
| Une seconde fiche Google d'un paysagiste déjà écarté pour l'astérisque a été gardée (refusée à la main) | Sa fiche ne montrait pas de numéro : l'annuaire, désormais lu avant Google, était interrogé sans numéro, puis plus jamais une fois le numéro révélé par Google | Un numéro ou une adresse que Google révèle est cherché dans l'annuaire |
| La même entreprise pouvait revenir d'une ville à l'autre | La mémoire de la recherche (déjà proposé) se perdait à chaque nouvelle ville, et elle ne retenait pas ses propres rejets | La recherche garde, d'une ville à l'autre et après un redémarrage, ce qu'elle a proposé et ce qu'elle a écarté pour de bon |
| Un paysagiste gardé avec l'email d'une galerie d'art (refusé à la main) | La galerie d'un membre de la famille partage le fixe de la maison : la recherche par numéro prenait l'email de toute page montrant le numéro | Hors annuaire, une page ne donne son email que si son titre nomme l'entreprise |
| Un « électricien » gardé : le profil Facebook d'un particulier dont le nom de famille est celui de la ville, avec l'email d'une paroisse (refusé à la main) | La ville lue dans le nom de la page plaçait la page dans la ville ; un domaine d'Église n'était pas reconnu comme institution | Le nom de la page ne compte plus pour la ville, un profil personnel (« … et d'autres personnes que vous pouvez connaître ») est écarté, les domaines de paroisse, de diocèse et d'Église (« cath ») sont des institutions |
| Une entreprise trouvée par Facebook pouvait échapper à l'astérisque | Sans numéro au départ, l'annuaire n'était pas interrogé ; le numéro lu ensuite sur la page ne l'était jamais | Le numéro lu sur la page Facebook est cherché dans l'annuaire avant la décision |
| Un garage dont un annuaire miroir écrit « * Ne désire pas recevoir de publicité » | La mention n'était lue que sur local.ch et search.ch | La mention est lue sur tout résultat qui nomme l'entreprise |
| Un électricien accepté la veille porte l'astérisque sur zip.ch (prospect passé en « Ne plus contacter ») | search.ch ne liste plus son numéro ; zip.ch garde les fiches que l'annuaire a perdues, astérisque compris | Un numéro absent de search.ch est cherché sur zip.ch |
| Un garage gardé avec l'email d'un autre garage (refusé à la main) | « Garage du Moulin » passait pour « Garage du Soleil » : les mots génériques communs (« garage du ») suffisaient | Un texte ne nomme une entreprise que s'il porte au moins un mot propre à son nom |
| Une carrosserie gardée avec un email sur le domaine de son groupe, qui a un site en ligne (refusée à la main) | Le site du domaine ne la nommait pas : l'email était pris sans autre question | Un email sur le domaine d'un site en ligne qui ne nomme pas l'entreprise met la fiche « à confirmer » |
| Un garage dont le domaine ne montre que la page d'accueil de l'hébergeur passait pour avoir un site | La page « Bienvenue sur … » répond normalement | Cette page compte comme un site mort |
| Trois garages « à confirmer : l'annuaire n'a pas répondu » | Interrogé avant Google pour chaque fiche, search.ch limitait le débit du serveur | Les requêtes à l'annuaire sont espacées d'une seconde et redemandées après un refus |

### Résultat

Le 7 octobre à 9 h 30 : Suisse 28/40 (17 garages, 8 paysagistes, 3 électriciens), France email 40/40, Québec 25/20, SMS France 15/15. Les paysagistes (4 sur 8) et les électriciens (1 sur 8) ont atteint la limite de 12 villes par métier : la recherche est relancée pour 12 villes de plus. La recherche des garages est la plus rentable (9 en 5 villes) ; la moitié des paysagistes et des électriciens suisses refusent la publicité.

## Manche 10 — Suisse, paysagistes et électriciens (7 octobre, matin)

| Recherche | Contrôlés à la main | Bons | Refusés |
|---|---|---|---|
| n° 11 reprise, 12 villes de plus par métier (376 requêtes, 57 appels au juge) | 10 | 4 (prospects 342 à 345) | 6 : un email sur un faux domaine Gmail, un astérisque sur zip.ch, une centrale hydroélectrique, un site derrière une page anti-robots, un email sur le domaine d'une autre entreprise, un électricien français itinérant |
| n° 12, 5 par métier (1 h, 242 requêtes, 23 appels au juge) | 6 | 3 (prospects 346 à 348) | 3 : la page Facebook d'une association de commerces, un astérisque sur un portable, une agence d'emploi |
| n° 13, 3 par métier (46 minutes, 173 requêtes, 17 appels au juge) | 5 | 5 (prospects 349 à 353) | aucun |

« Contrôlés à la main » = les fiches gardées et les fiches « à confirmer » qui avaient un email. Le prospect 342 était « à confirmer » : son email figure sur la liste des entreprises de sa commune, il a été gardé à la main. Le prospect 344 est un homme à tout faire qui entretient des jardins : cas limite, gardé.

La règle de la manche 9 « email sur le domaine d'un site en ligne qui ne nomme pas l'entreprise » a joué : un électricien dont l'email est sur le domaine d'une autre entreprise est arrivé « à confirmer », pas gardé.

### Écarts et causes

| Écart | Cause | Correction |
|---|---|---|
| Un « électricien » à confirmer était une centrale hydroélectrique, avec l'email d'une pharmacie du même nom | La catégorie Google « centrale hydroélectrique » passait pour le métier | Centrales, sous-stations et postes électriques sont hors du métier (`0f787f0d`) |
| Un électricien gardé a un site, derrière une page anti-robots | La page d'accueil du domaine de son email, qui porte son nom, ne se lisait pas : le domaine était ignoré | Un domaine d'email qui épelle le nom de l'entreprise et qui répond est son site, même illisible (`ebcf66b2`) |
| Un paysagiste gardé : son portable porte l'astérisque sur zip.ch | search.ch trouvait l'entreprise par son nom, et zip.ch n'était lu que si search.ch ne trouvait rien | zip.ch est lu pour tout numéro que search.ch ne liste pas ; un extrait zip.ch étoilé dans les résultats Google compte aussi (`771a4e56`) |
| Le nom d'une page Facebook gardait son identifiant (« … (@…) ») jusque dans la fiche du prospect (corrigé à la main) | Le titre de la page n'était coupé qu'à « \| Facebook » | L'identifiant est retiré du nom (`911407e4`) |
| Un électricien à confirmer : son portable porte l'astérisque dans l'extrait Google de sa fiche d'annuaire | L'extrait arrivait derrière un lien de redirection Google, et l'astérisque n'était lu que sur les liens des annuaires | Un numéro étoilé précédé de « téléphone », « mobile », « portable », « natel » ou « fax » est lu sur tout résultat (`d7cca9c5`) |
| Un « électricien » gardé était la page Facebook d'une association de commerces de la région | Une page trouvée par la recherche Facebook était crue sur le métier cherché | Une page Facebook dont le nom ne dit pas le métier passe « à confirmer » (`94f22911`) |
| Un paysagiste à confirmer : son seul email est sur « gmail.ch » | gmail.ch n'est pas Gmail : le domaine a son propre serveur de courrier, il passe tous les contrôles | Pas corrigé : la fiche attendait déjà une confirmation, et pas de filtre agressif sur les emails |
| Un électricien français itinérant, à confirmer (page Facebook sans téléphone) | Sa page est sortie de la recherche Facebook de la ville | Pas corrigé : la fiche attendait déjà une confirmation |
| Trouvé en relisant le code : un fax étoilé dans un extrait arrivé par une redirection n'était pas lu | La liste des mots devant le numéro oubliait « fax », alors qu'un fax étoilé sur une page d'annuaire écarte déjà la fiche | « fax » ajouté à la liste (`280b2c4b`) |

Groq : la recherche n° 11 a épuisé le quota gratuit du jour (200 000 jetons sur gpt-oss-120b). Le juge passe désormais sur gpt-oss-20b, qui a son propre quota, quand celui du modèle principal est épuisé (`d4fbbbaa`).

### Résultat

Le 7 octobre à 10 h 55 : Suisse 40 au total (18 garages, 17 paysagistes, 5 électriciens). Les totaux par pays étaient atteints, pas le tableau par métier arrêté pour la campagne : voir la manche 11. Les électriciens suisses restent la case la plus dure : 1 bon sur 24 villes dans la n° 11, aucun sur 12 villes dans la n° 12, 2 sur 12 villes dans la n° 13 (Genève, Montreux) ; dans chaque ville, la plupart ont un site ou refusent la publicité.

## Manche 11 — Le tableau par métier (7 octobre, midi)

Le tableau de la campagne fixe un nombre par métier dans chaque case, pas seulement un total par pays :

| Campagne | Paysagistes | Garages | Électriciens |
|---|---|---|---|
| Suisse, email | 16 | 14 | 10 |
| France, email | 16 | 14 | 10 |
| Québec, email | 6 | 10 | 4 |
| France, SMS (sans email) | 6 | 6 | 3 |

Compté case par case, il manquait 17 prospects : 5 électriciens suisses, 6 paysagistes et 2 garages français par email, 1 paysagiste québécois, 3 garages français par SMS. Les surplus des autres cases restent en réserve.

Six sont venus de fiches déjà en attente, contrôlées à la main : 3 garages français mis de côté avec un portable sans email (case SMS), 1 paysagiste québécois au site mort (les 3 autres « à confirmer » de sa recherche avaient un site en ligne, que le bouton « Site Web » de la manche 9 repère désormais), et 1 électricien suisse mis de côté sans email alors que l'annuaire en donne un (voir plus bas). Le reste vient de trois recherches :

| Recherche | Gardés | Bons | Faux |
|---|---|---|---|
| n° 14, France, paysagistes + garages, 6 par métier (20 minutes, 233 requêtes, 26 appels au juge) | 13 | 6 retenus (prospects 358 à 363), 3 garages bons en réserve | 1 paysagiste radié au registre, 1 garage avec l'email du réseau AD, 2 paysagistes non vérifiables au registre (en réserve) |
| n° 15, Suisse, électriciens, 5 (25 villes en trois passages, 383 requêtes, 55 appels au juge) | 8 | 4 (prospects 365 à 367, 370), 1 en réserve non contrôlé | 1 entreprise française sans adresse, 1 électricien qui a un site (certificat cassé), 1 indépendant radié (repris par une autre entreprise) |
| n° 16, France, paysagistes, 2 (2 minutes, 23 requêtes, 3 appels au juge) | 3 | 2 (prospects 368, 369) | aucun (1 bon en réserve) |

### Écarts et causes

| Écart | Cause | Correction |
|---|---|---|
| Des garages, carrossiers ou vendeurs de voitures écartés comme « autre métier » | Le métier était lu au sens strict, alors que la template mécanique leur convient ; même chose pour le jardin (clôtures, arrosage) et l'électricité (domotique, éclairage) | Chaque métier couvre le thème de sa template ; les faux amis restent dehors (assurance auto, bornes de recharge publiques, jardins d'enfants) (`3989e9e4`) |
| Les électriciens suisses ne se trouvaient presque plus | Les 69 villes suisses du moteur étaient déjà parcourues pour ce métier | 78 villes romandes de plus (`bf40ef13`) |
| Des fiches « à confirmer » parce que Google n'a pas répondu, deux fois de suite | Bright Data reste muet plusieurs minutes par moments, et le second essai venait tout de suite après le premier | Un dernier essai, après une minute, en fin de métier (`e34d2ad6`) |
| Un garage gardé avec l'email du réseau AD (info@autodistribution.com) | Le domaine du réseau n'était pas dans la liste des réseaux | autodistribution.com et .fr ajoutés (`eb440a8b`) |
| Un électricien mis de côté « sans email » alors que l'annuaire donne son adresse sur un domaine accentué (info@…contrôles.ch) | La validation des emails refusait les lettres accentuées : l'adresse était jetée sans bruit | L'email est lu dans la forme que lisent les serveurs (`xn--…`) (`ae9f288f`), envoyé ainsi à Resend (`92a17321`), et la page d'accueil de l'hébergeur d'un domaine accentué compte comme un site mort (`47eb7f37`) |
| Une entreprise française gardée dans une recherche suisse (ville frontalière) | Sans adresse, rien ne la plaçait en France, alors que son numéro commence par +33 | Sans adresse, un numéro d'un autre pays place la fiche dans cet autre pays (`28677a39`) |
| Un électricien gardé alors qu'il a un site | Son certificat HTTPS est cassé : la page d'accueil du domaine de son email passait pour muette, et le domaine (« nom + fils ») ne ressemble pas assez au nom complet | La page d'accueil est relue en HTTP quand le HTTPS échoue (`1f41e9ca`) |
| Un électricien indépendant gardé alors qu'il est radié (repris par une autre entreprise en 2024), une société « en liquidation » à confirmer | Google ne montrait pas la page du registre qui le dit | Le registre fédéral (Zefix) est lu pour toute fiche suisse proposée : même nom et même siège « en liquidation », ou radiés depuis moins de trois ans, sans homonyme actif = fermée (`2fcf5b15`, `00b33355`) |

Piste écartée : les listes de membres des associations cantonales d'électriciens (EIT) ; presque tous les membres ont déjà un site.

### Résultat

Le 7 octobre à 13 h 20, toutes les cases du tableau sont pleines (17 prospects ajoutés, n° 354 à 370) :

| Campagne | Paysagistes | Garages | Électriciens |
|---|---|---|---|
| Suisse, email | 17/16 | 18/14 | 10/10 |
| France, email | 16/16 | 14/14 | 18/10 |
| Québec, email | 6/6 | 10/10 | 10/4 |
| France, SMS (sans email) | 7/6 | 6/6 | 5/3 |

Le dixième électricien suisse est arrivé au troisième passage de la n° 15 (36 villes déjà parcourues pour ce métier avant elle). Le dernier essai différé a joué une fois en production.

## Bilan de l'entraînement (7 octobre)

Précision de l'app = bons prospects parmi les fiches qu'elle a gardées (les « à confirmer » sont à part : c'est l'app qui demande un contrôle).

| Recherche | Pays | Gardés | Bons | Précision |
|---|---|---|---|---|
| n° 3 (manche 1) | Suisse | 10 | 5 | 50 % |
| n° 4 (manche 2) | Suisse | 15 | 3 | 20 % |
| n° 5 (manche 3) | Suisse | 7 | 4 | 57 % |
| n° 6 (manche 4) | France | 25 | 9 | 36 % |
| n° 7 (manche 5) | Québec | 25 | 16 | 64 % |
| n° 8 (manche 6) | France | 24 | 17 | 71 % |
| n° 9 (manche 7) | Suisse | 11 | 5 | 45 % |
| n° 10 (manche 8) | Québec | 10 | 9 | 90 % |
| n° 11 (manches 9 et 10) | Suisse | 22 | 15 | 68 % |
| n° 12 (manche 10) | Suisse | 4 | 3 | 75 % |
| n° 13 (manche 10) | Suisse | 5 | 5 | 100 % |
| n° 14 (manche 11) | France | 13 | 9 | 69 % |
| n° 15 (manche 11) | Suisse | 8 | 4 (+ 1 non contrôlé) | 50 % |
| n° 16 (manche 11) | France | 3 | 2 (+ 1 mini-site Solocal douteux) | 67 % |

- La Suisse passe de 20 à 57 % les premiers jours à 50-100 % sur les quatre dernières recherches (les électriciens, la case la plus rare, tirent vers le bas) ; la France de 36 à 67-71 %, le Québec de 64 à 90 %. À la main, la manche 1 donnait 75 % (6 bons sur 8) : l'app fait maintenant à peu près aussi bien, seule, et chaque faux des dernières recherches a reçu sa correction. Ce n'est pas l'arrivée : Léo veut que l'app fasse mieux qu'à la main (7 octobre), l'entraînement continue donc à chaque recherche.
- Le 7 octobre à midi, compté case par case, il manquait encore 17 prospects : un total par pays ne suffit pas, le tableau de la campagne fixe un nombre par métier.
- Les fiches « à confirmer » rapportent peu (1 bon sur 5 dans la reprise de la n° 11) : l'app a raison de les montrer à part.
- Coût : 35 requêtes par prospect dans la n° 13, environ 80 dans les n° 11 et 12 (électriciens, grandes villes), soit 0,05 à 0,12 $ par prospect (0,0015 $ la requête).
- Ce qui demande encore un humain : les fiches « à confirmer » (Google sans réponse, email sans preuve franche, page Facebook sans téléphone ou sans le métier dans son nom) et les cas limites (un homme à tout faire qui entretient des jardins).

## Les fermetures françaises (8 octobre, nuit)

- En remplaçant le garage fermé n° 302, un second garage fermé est apparu dans la réserve de la recherche
  n° 14 : la recherche française ne lisait pas l'état du registre. La Suisse le faisait déjà (Zefix).
- Corrigé : pour chaque candidat français proposé, le registre des entreprises est lu par le nom (tel quel,
  sans les mots du métier, puis sans les communes qu'il cite). Une société de ce nom, à son code postal ou
  dans sa ville, fermée depuis moins de trois ans, ferme le candidat ; une société ouverte à son nom, ou du
  même patron à son adresse ou dans le département (un artisan passé en société), le garde ouvert ; un
  nouveau venu à la même adresse est une autre affaire.
- Contrôle sur les 135 prospects français : un seul autre fermé (n° 151, écarté), et une fausse alerte
  corrigée pendant le contrôle (le même patron, une société du même nom dans la commune voisine).

## Manche 12 — France, garages, vague 5 (31 octobre, soir)

Recherche de l'app n° 17 (garages et paysagistes, 17 par métier, email et portable exigés, note ≥ 4,0, mode
« Je valide »), arrêtée à 666 requêtes après 7 villes de garages (Châtellerault, Montluçon, Dax, Cholet,
Mulhouse, Aurillac, Perpignan) : elle n'avait pas encore commencé les paysagistes.

### Ce qui a changé en route

- **Email et portable exigés ensemble = presque rien en France** : 5 garages avaient les deux, 29 un email
  sans portable, 14 un portable sans email. Décision pour la vague 5 : email obligatoire, portable en plus
  quand il existe. Les recherches suivantes (n° 18 paysagistes et électriciens, n° 19 Martinique, n° 20
  Suisse) partent avec le canal « email ».
- La recherche à la main n'a pas pu se faire comme d'habitude : la clé Bright Data du poste avait expiré,
  puis le Web Unlocker de Bright Data a répondu « Request setup error » (Google en 502) une partie de la
  soirée, y compris pour le serveur. La vérité terrain s'est faite avec le registre des entreprises
  (recherche-entreprises.api.gouv.fr), le domaine de chaque email et les preuves enregistrées par l'app.

### Vérité terrain (41 candidats avec email : 5 gardés, 29 mis de côté, 7 à confirmer)

- **17 validés** et devenus prospects : Aquitaine Négoce Auto, Garage Sani'Drive, Pneumagic, Carprog86
  (les 4 avec portable), GARAGE CS AUTO, Enault Sport, MJV Automobiles (email de la gérante, nom au
  registre), Garage des Marais, Garage Norville, Montluçon Automobiles, Dax Carrosserie, DAC Automobiles,
  FM Garage, Garage Sélection Auto Cholet, Garage Bel Air, Auto Expert (Illzach), Tourlan et Fils.
- **Réserve** (bons, gardés de côté) : Garage du Paradis, Garage Aurillac Électro Diesel, Garage
  Serv'Auto, GLD Automobiles, Léon Motors, Garage Martinez Philippe BC, SARL Verge.
- **13 refusés**, dont des erreurs de l'app :

| Candidat | Place donnée par l'app | Vérité | Écart |
|---|---|---|---|
| SARL Lucens Automobiles (Montluçon) | **gardé** | `lucensautomobiles.fr` répond « Accueil - Lucens Automobiles » : il a un site | aucun contrôle du domaine dans ses preuves : un candidat qui a email et portable est gardé sans que le domaine de son email soit lu |
| Welington Automobiles | à confirmer | l'email est sur `welington.fr`, son propre nom | un domaine qui porte le nom distinctif de l'entreprise et sert une page = un site, même si le titre ne la nomme pas |
| AG Automobiles | à confirmer | l'email est sur `ag-garage.fr` (page Bosch Car Service) | idem (initiales + métier dans le domaine) |
| Abj Auto | à confirmer | `abjautorepair.net@domainsbyproxy.com` est l'adresse d'un service qui cache le titulaire d'un domaine | une adresse de protection de domaine (Domains By Proxy et semblables) n'est jamais l'email de l'entreprise ; elle révèle son domaine (`abjautorepair.net`) : il a un site |
| Carrosserie CS Auto | mis de côté | même email et même société que GARAGE CS AUTO (deux fiches Google) | deux candidats avec le même email ou le même SIREN = une seule entreprise |
| Peugeot - Dax Auto, Peugeot - Garage Thierry Hoff, Renault / Dacia - Garage Tastet, Garage Lebreton (Aixam) | à confirmer ou mis de côté | agents et concessionnaires de marque | une marque automobile en tête du nom, ou la catégorie « Concessionnaire <marque> », = réseau : le patron ne décide pas seul de son site |
| AD Carrosserie et Garage Expert Atelier Panon | mis de côté | deux réseaux (AD, Garage Expert) | ajouter les réseaux de garages indépendants à la liste des enseignes (AD, Garage Expert, Bosch Car Service, Motrio, Eurorepar, Top Garage, Point S…) |
| Garage Dyma | mis de côté | email `brd.auto.performance@gmail.com`, au nom d'une autre affaire | un email dont la partie locale nomme une autre entreprise n'est pas une preuve |
| Garage Millésime Auto | à confirmer | email `garageautohouse@gmail.com`, idem | idem |
| GLD Automobiles | à confirmer (preuve « c ») | `gld-automobiles@orange.fr` : la partie locale est le nom de l'entreprise | un email dont la partie locale reprend le nom normalisé de l'entreprise vaut au moins une preuve « b » |

- Pièges du contrôle : le registre trouvé par le nom se trompe parfois d'entreprise (« Montluçon Vitrage
  Automobile », une boulangerie fermée en Ariège pour SARL Verge, une ancienne société pour Garage du
  Paradis) ; une absence au registre ne prouve rien.

### Note de la manche

- Gardés par l'app : 5, dont 1 faux (Lucens, il a un site) : 4 bons sur 5.
- Sur les 41 avec email, 24 bons (17 validés + 7 en réserve) et 13 refusés : 7 placés à tort par l'app
  (Lucens gardé, et mis de côté : 3 agents de marque, 1 réseau, 1 doublon, 1 email d'autrui), 4 « à
  confirmer » qu'elle aurait pu trancher seule (Welington, AG, Abj, Peugeot Dax) et 2 doutes justifiés
  (Millésime, Motorsport). Un bon email a aussi été classé « sans preuve » (GLD).
- Corrections à faire dans le moteur (session de code dédiée) : contrôle du domaine pour tout email appris,
  y compris quand le candidat a déjà email et portable ; domaine au nom de l'entreprise = site ; adresses de
  protection de domaine ; doublons par email et SIREN ; marques automobiles et réseaux de garages ; email
  au nom d'une autre affaire ; email au nom de l'entreprise = preuve « b ».

### Résultat

Moteur corrigé dans la nuit du 31 octobre au 1er novembre (`e8410245`, `3b4a6864`), puis le lot rejoué hors
ligne. Chaque candidat repart des preuves que
sa vérification a enregistrées : aucune recherche Google n'est refaite. Ce que le moteur corrigé fait sans
requête payante est refait pour de vrai : réseaux et marques, lecture des mots de l'email, adresses de
protection de domaine, page d'accueil et état de chaque domaine, courrier du domaine, registre des
entreprises, puis les doublons, dans l'ordre où la recherche avait placé les candidats. Critères de la
n° 17 : email et portable, note ≥ 4,0. Le « avant » des 13 refusés à la main est la place que l'app leur
avait donnée : l'ancien moteur, rejoué sur les mêmes preuves, redonne exactement la place enregistrée de
tous les autres.

| Candidat | Avant | Après | Règle qui joue |
|---|---|---|---|
| SARL Lucens Automobiles | gardé | écarté, a un site (`lucensautomobiles.fr`) | le domaine porte son nom (« lucens » + « automobiles ») : un domaine à son nom qui répond derrière un contrôle anti-robots est son site ; l'email d'un candidat déjà complet est relu avant de le garder |
| AG Automobiles | à confirmer | écarté, a un site (`ag-garage.fr`) | initiales + mot du métier dans le domaine |
| Welington Automobiles | à confirmer | rejeu hors ligne : mis de côté, email sans portable (gardé avec « email » seul), **à tort** ; depuis la correction du 1er novembre : écarté, a un site (`welingtonautomobiles.fr`) | `welington.fr`, le domaine de son email, est parqué : un site mort, pas son site. Son vrai site était dans les résultats de la n° 17, derrière la redirection de Google (`google.com/goto?url=…`) : l'adresse écrite sous le titre est maintenant lue (voir plus bas) |
| Abj Auto | à confirmer | écarté, ni email ni portable | `abjautorepair.net@domainsbyproxy.com` n'est jamais un email ; le domaine révélé, `abjautorepair.net`, a été lu : il n'existe plus |
| Carrosserie CS Auto | mis de côté | écarté, « même entreprise que GARAGE CS AUTO, une fiche mieux renseignée » | même email, et même SIREN lu au registre ; GARAGE CS AUTO (152 avis contre 26) reste proposé |
| Peugeot - Dax Auto | à confirmer | écarté avant toute recherche, « agent ou concessionnaire Peugeot » | marque en tête du nom |
| Peugeot - Garage Thierry Hoff, Renault / Dacia - Garage Tastet | mis de côté | écartés avant toute recherche, agent ou concessionnaire Peugeot, Renault | marque en tête du nom, catégorie « Concessionnaire Peugeot » |
| Garage Lebreton (Aixam) | mis de côté | écarté avant toute recherche, agent ou concessionnaire Aixam | catégorie de concessionnaire et marque dans le nom |
| AD Carrosserie et Garage Expert Atelier Panon | mis de côté | écarté avant toute recherche, réseau | réseaux de garages indépendants (AD, Bosch Car Service, Motrio, Eurorepar, Top Garage, Point S, First Stop, Profil Plus, Autoprimo…), lus dans le titre de la fiche, le nom de sa page Facebook, le site qu'elle déclare, le domaine de l'email ou une page du réseau qui nomme le garage dans sa ville |
| Garage Dyma | mis de côté | à confirmer : « Son email (brd.auto.performance@gmail.com) porte le nom d'une autre affaire » | email au nom d'une autre affaire = aucune preuve |
| Garage Millésime Auto, Motorsport | à confirmer, sans raison précise | à confirmer, avec la même raison explicite | idem (`garageautohouse@…`, `mdslmotorsport@…`) |
| GLD Automobiles | à confirmer (preuve « c ») | écarté avant toute recherche, réseau (son email vaut désormais « b ») | site déclaré sur le site d'un réseau (`motrio.fr/shop/GLD AUTOMOBILES/…`) ; email au nom de l'entreprise |
| Garage des Marais (validé, n° 380) | mis de côté | écarté, réseau | sa page Facebook s'appelle `Motrio.GarageDesMaraisMontlucon`, et le titre de sa fiche finit par « - Motrio » |
| Garage du Paradis | mis de côté | écarté avant toute recherche, réseau | la page Facebook que déclare sa fiche est « AD-Garage-du-Paradis » |
| SARL Verge | mis de côté | écarté avant toute recherche, réseau | site déclaré sur `boschcarservice.fr` |
| Garage Martinez Philippe BC | mis de côté | écarté, réseau, dès que la vérification montre sa page Autoprimo | une page du site d'un réseau (Autoprimo, AD, Motrio, une marque…) qui le nomme dans sa ville |
| DAC Automobiles (validé, n° 384) | mis de côté | à confirmer, « un site est déclaré sur sa fiche Google, mais il n'a pas été retrouvé » | sa page Facebook, trouvée par une recherche, ne tient plus lieu du site déclaré (`www.dacautomobiles-narrosse.fr`, en ligne) ; une page Google vide ne vaut plus vérification |
| GARAGE NORVILLE (validé, n° 381) | mis de côté, sans ville | mis de côté, « 38 Rue Denis Papin, 03100 Montluçon » | une adresse sans code postal prend celui de la société de son nom installée à cette rue, dans sa ville (registre) |

Le contrôle de la réserve, pendant l'enrichissement de la même nuit, a déplacé six des 24 « bons » : Garage
des Marais, Garage du Paradis, GLD, SARL Verge et Garage Martinez sont des garages de réseau, DAC a un site.
Le rejeu hors ligne écarte Garage des Marais et Garage du Paradis ; pour GLD, Verge, Martinez et DAC, la
preuve qui décide (le site déclaré par la fiche, la page Autoprimo, le bouton « Site Web » non suivi)
n'avait pas été enregistrée par la n° 17 : la règle est écrite et rejouée dans les tests, le rejeu hors
ligne les laisse mis de côté. MJV Automobiles (email de la gérante) reste mis de côté.

| Lot de 41 avec email | Gardés | Mis de côté | À confirmer | Écartés |
|---|---|---|---|---|
| Avant | 5, dont 1 faux | 29 | 7 | 0 |
| Après, rejeu hors ligne (email et portable) | 4 | 23 | 3 | 11 |
| Après, avec les preuves non enregistrées (GLD, Verge, Martinez, DAC, Welington) | 4 | 18 | 4 | 15 |
| Après, rejeu hors ligne (email seul, réglage de la vague 5) | 27 | 0 | 3 | 11 |

- Placés à tort : 7 → 0. « À confirmer » que l'app pouvait trancher : 4 → 0. Le rejeu hors ligne plaçait
  Welington à tort (mis de côté, alors qu'il a un site) : l'adresse de son site manquait aux preuves
  enregistrées. Avec la correction du 1er novembre, il est écarté. Restent à confirmer les trois emails au
  nom d'une autre affaire, avec cette raison écrite, et DAC.
- Les 23 proposés du rejeu hors ligne : les 18 bons qui restent, Welington (à tort, voir plus bas) et
  4 garages d'Aurillac que le contrôle n'avait pas classés (Garage Laur Sebastien, B&P Auto-services, Garage
  du Viaduc, Garage Ams).
- Coût : 105 fiches sur 296 de la n° 17 sont des réseaux ou des marques par leur nom, leur catégorie ou leur
  page Facebook. Elles sont maintenant écartées dès la lecture de la fiche Google, sans vérification ; 16
  d'entre elles avaient été proposées et 11 avaient coûté une recherche de contact complète.

Corrections de la vérité terrain (contrôle en direct pendant le rejeu) :

- **Welington Automobiles a un site**, `welingtonautomobiles.fr` (« Spécialiste vente voitures occasion
  Montluçon », en ligne). Le contrôle du site à l'enrichissement l'a trouvé le 1er novembre au matin
  (prospect n° 392, écarté depuis). `welington.fr`, le domaine de son email, n'est qu'un domaine parqué chez
  GoDaddy (seul son courrier fonctionne) : le refus à la main était juste, pour une autre raison. La n° 17
  avait pourtant vu ce site : le résultat Google qui lui a donné son email venait de
  `welingtonautomobiles.fr`, mais Google en cachait l'adresse derrière sa redirection
  (`google.com/goto?url=…`), et le moteur a lu une page de google.com. 33 preuves de la n° 17 (25 emails,
  8 patrons) viennent de résultats ainsi cachés. Leurs redirections, suivies le 1er novembre, mènent au site
  de l'entreprise pour cinq d'entre elles : Welington, Lucens et DAC, que la recherche n'avait pas vus, et
  deux garages déjà écartés pour un site trouvé ailleurs. Elles mènent aussi à des pages Facebook : celle
  de Garage Bel Air, et une page Motrio pour GLD. Corrigé le 1er novembre (`d20db841`) : l'adresse que
  Google écrit sous le titre (`https://welingtonautomobiles.fr › vehicules`) donne le site du résultat. Une
  page morte du domaine de l'email ne tient plus lieu du site que déclare la fiche Google : le candidat
  reste « à confirmer ».
- **Abj Auto n'a plus de site** : `abjautorepair.net` n'existe plus (aucun DNS, adresse libre selon le
  RDAP). Il reste écarté, mais faute d'email, pas pour un site.
- **Tourlan Et Fils (validé, prospect n° 389) est douteux** : il partage son email `ggetourlan@wanadoo.fr`
  avec AD Garage Expert TOURLAN, dont le site `garagetourlan.com` présente « 2 garages AD Expert » de la
  famille à Aurillac (pas celui de la rue Cugnot), et cet email vient de sa page `garagetourlan.myautoconseil.com`.
  À revoir avant l'envoi du 5/11. Le moteur ne peut pas le voir : la fiche AD est maintenant écartée avant sa
  vérification, son email n'est donc jamais lu.

Règles non écrites, par risque de faux positifs :

- Une page Facebook cachée derrière la redirection de Google reste non lue (Garage Bel Air, prospect
  n° 387). Sous le titre, seul le site est sûr (`facebook.com`) : la suite est un fil d'Ariane, pas
  l'adresse de la page (`welingtonautomobiles.fr › vehicules` pour `/414/vehicules/?marque=834`). La lire
  demanderait de suivre la redirection, une requête de plus par résultat.

- « Garage Expert » seul n'est pas un réseau : l'enseigne d'AD est « Garage AD Expert », et toutes les
  fiches AD de la manche portent « AD ». Le mot aurait écarté « Garage Expert 68 » (Mulhouse), sans doute
  indépendant.
- Une page d'accueil cachée derrière un contrôle anti-robots, sur un domaine qui ne porte pas le nom de
  l'entreprise, reste sans suite : la distinguer d'un serveur vide qui refuse l'accès demande une lecture de
  plus. Le cas de Lucens passe par le nom du domaine.
- Les marques au nom de mot courant (Mini, Smart, Alpine, DS, MG, Lotus) ne comptent que dans la catégorie
  Google « Concessionnaire <marque> ».
- Un réseau de carrosseries comme Five Star (l'email de GARAGE CS AUTO vient de sa liste d'adhérents)
  n'est reconnu que s'il est écrit dans le nom.
- Un nom qui commence par « AD » ne suffit pas : « AD » suivi de garage, carrosserie ou expert est un
  réseau, « AD » seul peut être les initiales du patron.

Décision du 1er novembre : un site Wix gratuit en ligne (Garage Aurillac Électro Diesel, `….wixsite.com/…`)
reste un mini-site, comme le range la règle du 3 août avec les mini-sites d'annuaire : le prospect est gardé.
Le site démo lui est proposé comme un vrai site à la place d'une page gratuite ; un message ne lui écrit jamais
qu'il n'a pas de site. Garage Aurillac Électro Diesel, refusé à la main dans la réserve, redevient un bon
prospect.

Suite du 1er novembre : Garage Aurillac Électro Diesel, validé (prospect n° 393), est sorti de la campagne dès
son enrichissement : sa fiche s'appelle « Garage Aurillac Electro Diesel - Bosch Car Service » (réseau). Et
Welington Automobiles, repris (n° 392), a bien un site en ligne, `welingtonautomobiles.fr` (« Spécialiste
vente voitures occasion Montluçon »), que le contrôle de site de l'enrichissement a trouvé : `welington.fr`,
le domaine de son email, n'est qu'un domaine parqué. Le refus d'origine était juste, pour une autre raison.

## Manche 13 — France, paysagistes et électriciens, vague 5 (1er novembre, nuit)

Recherche de l'app n° 18 (17 paysagistes et 17 électriciens, canal « email », note ≥ 4,0, sans les registres,
mode « Je valide »), terminée avec 18 gardés par métier après 1 256 requêtes. Elle a tourné presque entière
avec le moteur d'avant les corrections de la manche 12 (déployées vers minuit).

### Vérité terrain (48 candidats avec email : 36 gardés, 12 à confirmer)

Contrôles : registre des entreprises, Google « "nom" ville » et « "email" » par Bright Data (revenu dans la
nuit), sites déclarés ouverts à la main.

- **15 validés** (n° 394 à 408). Paysagistes : Medina Paysage, Oh Joli Jardin, T&A Paysage, Vulcan'Paysage,
  Jardin Authentique, LT Services, Un Temps au Jardin. Électriciens : Bost Électricité, Le Petit Élec,
  Alex'Élec, KR Électricité Générale, Ticheur Christophe, BM Élec, Les Solutions d'Olivier, LDBM Élec.
- **Réserve** : Pierre et Jardins (Metz, le registre trouvé par le nom est une autre société à Villeurbanne),
  Flash Élec 24 (email `flashelecidf@…`).
- **Précision des gardés : 7 bons sur 18 paysagistes (39 %), 8 sur 18 électriciens (44 %).**
- **31 refusés** :

| Cause | Cas | Règle à écrire |
|---|---|---|
| Email ou page d'un homonyme ailleurs en France | Élagage Pierrot (Reims) : l'email est celui de « Pierrot Élagage » à La Crau (83) ; Les Jardins d'Eden (Reims) : `lejardindeden.occitanie@…` ; greentouch (Reims) : page Facebook « Green Touch » à Saint-Martin-Longueau (60) ; Les jardins d'Odin (Reims) : au registre dans le 63, email `taverneodin@…` ; Stéphane Demerges (Clermont-Ferrand) : sa page dit Le Tronquay (14) ; Bernard Frères (Dordogne) : l'email est sur la fiche d'une « Société Bernard Électricité » à Besançon ; DAM'ÉLEC (Coulon) : page « DAM ELEC services » à Péronne (80) ; Rg Élec (Nancy) : `rg.elec.89@…`, registre dans le 30 ; JS Électricité (Nancy) : registre à La Réunion ; Ogelec (Périgueux) : `kisscool29@…`, registre dans le 30 | la page où l'email a été trouvé doit parler du même lieu (code postal, département, commune ou téléphone du candidat) ; un numéro de département dans la partie locale qui contredit celui du candidat, ou une région écrite en toutes lettres, met le candidat « à confirmer » |
| Adresse absente, ville cherchée prise par défaut | 5 des 6 paysagistes gardés à Reims étaient des entreprises d'ailleurs | un candidat sans adresse dans la zone cherchée reçoit sa vraie adresse (fiche, registre, page) avant d'être gardé |
| Email sans rapport avec l'entreprise | GL Énergie : `hhj@imaeil.com` (un journaliste d'un quotidien coréen) ; Laurier : `pjheng@naver.com` ; Un jardin un service : `1service@gmail.com` (une société de location de voitures) ; Aurélec : `lannexe@wanadoo.fr` (« L'annexe », une autre affaire) ; M.A.S Élec 30 : `bc.elec30@…` (« BC Élec ») | un email lu sur une page qui ne parle pas du candidat n'est pas une preuve, même « b » ; une page en langue étrangère sur un domaine sans rapport ne donne jamais d'email |
| Mauvais métier | La petite Maçonnerie (code 43.99C, maçonnerie) en paysagiste ; Solosecc Chauffagiste en électricien ; Gazelec Gardois (association sportive) ; Asser (réparation d'équipements, 33.14Z) | un nom qui porte un autre métier (maçonnerie, chauffagiste, plomberie…) ou un code d'activité d'un autre métier ou d'une association écarte le candidat |
| Site déclaré en ligne | Les Compagnons du Paysage, Les Jardins Périgordins, Au fil du Paysage (gardés), Nancy Élec, Green Concepts, S.T.E.C.O, Ets Bourreau, C-velec, MR Électricien, JCB Électricité (à confirmer) | couvert par la correction du 1er novembre (une vérification qui échoue ne vaut pas « pas de site ») ; à vérifier sur la manche suivante |
| Réseau | PPF (agence du réseau ppf.fr) | ajouter PPF aux réseaux |
| Fermé | Laurier Jean Pierre (cessé au registre) | déjà couvert |

### Suite

Il manque 10 paysagistes et 8 électriciens français : recherche n° 22 (14 par métier, mêmes réglages) lancée
avec le moteur corrigé, pour mesurer l'« après » sur une recherche neuve.

### Résultat

Moteur corrigé le 1er novembre (`ef9627cc`, `ed91e02e`) et en prod à 2 h 23, juste après la fin de la n° 19 : la
n° 20 a repris au redémarrage, les n° 21 et 22 partent avec ce moteur. Le lot a été rejoué hors ligne : chaque
candidat repart des preuves que sa vérification a enregistrées, sans nouvelle recherche Google. Le registre des entreprises, la liste
des communes, les pages d'accueil et le courrier des domaines sont relus pour de vrai. Les trois sites déclarés ont
été relus en direct (trois vérifications, deux cartes locales). Hors ligne, le nom d'une page Facebook trouvée par
une recherche est lu dans son adresse (« /p/La-Taverne-dOdin-… ») ; le moteur lit le titre que Google lui donne.
Critères de la n° 18 : email, note ≥ 4,0.

| Écart | Cas | Règle écrite | Après |
|---|---|---|---|
| Un autre numéro écrit à côté de l'email | DAM'ÉLEC, greentouch, Rg Élec, Aurelec (liste des entreprises de Beaumont), Flash Élec 24, Green Concepts | dans un résultat qui montre des numéros, l'email appartient au numéro écrit le plus près. Si ce n'est pas celui du candidat, l'email n'est pas pris, même quand le juge le lui donne ; s'il porte le nom de l'entreprise, il est gardé en preuve « c » avec la raison (règle affinée en manche 14 : l'autre numéro peut être celui de son responsable) | à confirmer (DAM'ÉLEC, greentouch, Rg Élec, Flash Élec 24) ou écarté faute de contact (Aurelec, Green Concepts) |
| Page dans une autre écriture | les candidats n° 4981 et 4998 (pages coréennes, dont l'une montre un numéro aux mêmes chiffres que le sien) | un résultat écrit surtout en coréen, cyrillique, arabe… ne donne jamais d'email | email écarté |
| Page qui ne situe pas l'entreprise | Élagage Pierrot (« Pierrot Elagage, La Crau, FR »), le paysagiste n° 4796 (fiche infobel « à Le Tronquay ») | l'email lu sur la page d'un tiers qui ne montre ni le numéro du candidat, ni sa commune, ni un code postal de son département vaut au plus « c » : « La page qui donne son email (…) ne dit pas où il est : à vérifier, ce peut être un homonyme. » | à confirmer |
| Lieu écrit dans l'email ou une page | Ogelec (`29`), Les Jardins d'Eden (`occitanie`), JS Électricité (page `…belux`), Asser (page `Asser84700`) ; Rg Élec (`89`) et Flash Élec 24 (`idf`) sont déjà écartés par le numéro | un numéro de département, un code postal, une région ou un pays voisin écrit avant le « @ », dans l'adresse de la page Facebook qui a donné l'email ou dans celle du candidat, et qui n'est pas son département, le laisse « à confirmer » avec le lieu lu | à confirmer |
| Page Facebook d'une autre affaire | Les jardins d'Odin (page « La Taverne d'Odin »), M.A.S Élec 30 (page « BC Elec ») | une page dont le nom met un autre mot à la place du métier (« taverne » pour « jardins ») n'est pas la sienne ; « Elec » est un mot du métier, pas un nom | page et email laissés de côté : mis de côté (portable) |
| Ville cherchée prise par défaut | Élagage Pierrot, Les Jardins d'Eden, Les jardins d'Odin, Rg Élec… | une fiche Google sans adresse ni commune prend celle du panneau Google, ou du registre : la seule société ouverte du département qui porte exactement son nom (« 51350 Cormontreuil » pour Les jardins d'Odin, « 24380 Sanilhac » pour Medina Paysage), commune et code postal seulement. Sans elle : « Sa fiche Google ne donne pas d'adresse : rien ne montre qu'il est à Reims, à vérifier. » | gardé avec sa vraie commune, ou à confirmer |
| Autre métier dans le nom | La petite Maçonnerie, Solosecc Chauffagiste | un nom qui dit un autre métier (maçonnerie, plomberie, chauffagiste, peinture…) et pas le métier cherché est écarté dès la fiche Google | écarté, sans vérification payante |
| Association | Gazelec S. Gardois | toutes les sociétés ouvertes du département qui portent les mots de son nom sont des associations au registre, et son nom ou sa page Facebook dit un club (« Sportif ») | écarté |
| Réseau | PPF Niort | `ppf.fr` et `preservationdupatrimoine.fr` ajoutés aux sites de réseaux : un email sur ce domaine fait un réseau | écarté |
| Site déclaré en ligne | Les Jardins Périgordins, Les Compagnons du Paysage, Au fil du Paysage | correction du 1er novembre : une page Facebook trouvée par une recherche ne vaut plus le site que déclare la fiche | relus en direct : le panneau donne `lesjardinsperigordins-24.fr`, les boutons « Site Web » mènent à `lescompagnonsdupaysage.fr` et `aufildupaysage17.fr` : écartés ; un bouton qu'on ne peut pas suivre les laisse « à confirmer » |

| Lot de 48 avec email | Gardés (dont bons) | Mis de côté | À confirmer | Écartés |
|---|---|---|---|---|
| Avant, la recherche | 36 (15, 42 %) | 0 | 12 | 0 |
| Avant, l'ancien moteur rejoué sur les mêmes preuves | 38 (15, 39 %) | 0 | 10 | 0 |
| Après, rejeu hors ligne (règles de la manche 14 comprises) | 14 (10, 71 %) | 2 | 23 | 9 |

- Gardés à tort après : 4. Nancy Élec et C-velec ont un site déclaré en ligne que le rejeu hors ligne ne voit
  pas : la recherche lit le bouton « Site Web » ou le panneau, comme pour les trois sites relus en direct (5 bons
  sur 6 électriciens gardés, 10 sur 12 en tout). Restent Un jardin un service et Bernard Frères (voir plus bas).
- Paysagistes gardés : 5 bons sur 6.
- Bons laissés « à confirmer » : 5 sur 15. Quatre sans adresse que ni le panneau ni le registre ne placent
  (Vulcan'Paysage, Bost Électricité, Alex'Élec, KR Électricité), un dont l'email porte `33` pour Niort (Oh Joli
  Jardin). C'est le prix de la règle du lieu : un contrôle à la main, pas un refus.
- Même rejeu sur la n° 17 (garages) : les validés restent gardés, sauf Garage des Marais (réseau, déjà su) et
  Tourlan et Fils (déjà douteux : l'email de sa fiche est écrit à côté d'un autre numéro).

Vérité terrain contrôlée en direct : l'email de Bernard Frères (`electricite.bernard@orange.fr`) ne ressort sur
Google qu'au nom de la Société Bernard Électricité de Besançon (25000). La page qui l'a donné (« Top 10 des
chauffagistes à Trélissac ») l'écrit pourtant juste après le numéro du candidat, et la société BERNARD FRÈRES de
Boulazac a pour enseigne « Entreprise Bernard Électricité ».

Règles non écrites :

- L'email d'un homonyme écrit sur un annuaire juste après le numéro du candidat (Bernard Frères) : seule une
  recherche de l'email lui-même le montre, une requête payante de plus par candidat.
- Un email coupé par la mise en page d'un magazine (« 1jardin 1service@gmail.com », lu `1service@gmail.com`,
  l'adresse d'une société de location de voitures) : Google ne connaît pas l'adresse entière, rien ne permet de la
  recoller sûrement.
- Le code d'activité du registre ne sert pas à écarter : Medina Paysage (validé) y est inscrit en 81.21Z
  (nettoyage), Les jardins d'Odin en 46.62Z. Seule la forme d'association compte.
- Un département écrit dans l'email ne vaut pas refus : ce peut être une année de naissance ou un département
  voisin ; le candidat reste « à confirmer ».

## Manche 14 — Martinique, les trois métiers, vague 5 (1er novembre, nuit)

Recherche de l'app n° 19 (7 par métier, canal « email », note ≥ 4,0, sans les registres, mode « Je valide »),
la première entière sur le moteur corrigé de la manche 12. 1 007 requêtes : garages 7 sur 7, paysagistes 6 sur
7, électriciens 6 sur 7. 60 fiches n'avaient qu'un portable : en Martinique, l'artisan se joint surtout par
téléphone.

### Vérité terrain (20 candidats avec email : 19 gardés, 1 à confirmer)

- **16 validés** (n° 409 à 424) : garages JN.Performance Motors, Garage Cratère, Garage Clio, Top Car
  Martinique ; paysagistes Green Corner Karayi'b, À Votre Service Martinique (site Strikingly gratuit = mini-site,
  comme un Wix), Chris Services, Elo Green Services, Green Garden, Bel Jaden Matinik ; électriciens Seveur
  Services, J.B Élec, Lamtra Services, Lisima Électricité, L.GELEC Entreprise, Tout Faire Habitat (site
  `toutfairehabitat.com` mort : 302 vers un HTTPS qui ne répond pas, 404 en HTTP).
- **Précision des gardés : 16 bons sur 19 (84 %)**, contre 39-44 % sur la recherche n° 18 avant les corrections.
- **4 refusés** :

| Candidat | Place donnée par l'app | Vérité | Règle à écrire |
|---|---|---|---|
| Garage Casimir Cadignan (Saint-Esprit) | gardé (site déclaré sur Google = sa page Facebook) | site en ligne `garageccadignan.fr` (« votre garagiste qualifié situé à Saint-Esprit ») ; ses pages « contact » et « mentions légales » sortent quand on cherche son email | quand l'email du candidat apparaît sur un domaine qui porte son nom (pages contact, mentions légales), ce domaine est son site, même si la fiche déclare une page Facebook |
| Garage Automobile VSP (Fort-de-France) | gardé | email `aixamautomobille@outlook.fr` : concessionnaire Aixam (voitures sans permis) | une marque dans la partie locale de l'email révèle un concessionnaire de marque, comme une marque en tête du nom |
| Flash Car (Ducos) | gardé | l'email est celui de « Garage Flash Auto Carrosserie » au Marin, une autre affaire dans une autre commune | couvert par la règle du lieu de la manche 13 ; à vérifier sur ce cas |
| entretien d'espace vert et nettoyage haute pression (Rivière-Pilote) | à confirmer | nom générique, ni téléphone ni avis | rien à changer : le doute était juste |

- Erreur de ma part, rattrapée : Tout Faire Habitat d'abord refusé pour son site, qui est mort ; repris.

### Résultat

Moteur corrigé le 1er novembre (`f2f4d321`), puis le lot rejoué hors ligne, chaque cas contrôlé en direct. Il a
fallu quatre recherches Google pour le garage de Saint-Esprit et une pour Flash Car.

| Écart | Règle écrite | Après |
|---|---|---|
| Garage de Saint-Esprit (n° 5484) : site `garageccadignan.fr` non vu | une page d'un domaine qui porte un mot distinctif du nom de l'entreprise, et qui montre son numéro ou son email, est son site, même quand la fiche déclare une page Facebook. La règle joue dans la vérification, la recherche par le numéro et la recherche de l'email. Lors de la n° 19, les résultats de la vérification étaient en partie cachés derrière la redirection de Google, lue depuis la manche 12 | écarté, a un site : la vérification rejouée en direct trouve `https://www.garageccadignan.fr/`, en ligne |
| Garage Automobile VSP : `aixamautomobille@…` | une marque automobile qui ouvre un mot de l'email (« aixamautomobile ») ou qui en est un mot entier (« garage.kia ») fait un concessionnaire, comme une marque en tête du nom. Ne comptent pas les marques au nom de mot courant (Mini) ou de prénom (Mercedes) | écarté : « Agent ou concessionnaire Aixam » |
| Flash Car (Ducos) : email de « Garage Flash Auto Carrosserie », au Marin | une page Facebook trouvée par une recherche n'est pas la sienne quand elle nomme une autre commune du département d'outre-mer, ou en métropole un code postal d'un autre département, sans montrer son numéro. La règle de la manche 13 ne comparait que les départements : toute la Martinique est en 972 | refusé en direct : la recherche Facebook titre « Garage Flash Auto Carrosserie \| Le Marin Martinique ». Le rejeu hors ligne le garde, ce titre n'étant pas enregistré |

| Lot de 20 avec email | Gardés (dont bons) | À confirmer | Écartés |
|---|---|---|---|
| Avant, la recherche | 19 (16, 84 %) | 1 | 0 |
| Après, rejeu hors ligne | 15 (14, 93 %) | 3 | 2 |
| Après, la page Facebook de Flash Car lue en direct | 14 (14, 100 %) | 3 | 3 |

- Bons laissés « à confirmer » : 2 sur 16. L'email d'Elo Green Services porte `971` (Guadeloupe) pour une
  entreprise inscrite à Fort-de-France : c'est le prix de la règle du lieu, une vérification à la main. Bèl Jaden
  Matinik n'a pas d'adresse sur sa fiche, et la page qui donne son email (une liste d'ateliers) ne la situe pas.
- Règle affinée en route. Un email écrit à côté d'un autre numéro que celui du candidat n'est plus jeté quand il
  porte le nom de l'entreprise : sur la page de Bèl Jaden, l'autre numéro est celui de son responsable. Il est
  gardé en preuve « c », « à confirmer » avec la raison, et reste jeté quand il ne porte pas ce nom (Aurelec). Sur
  la n° 18, le rejeu donne les mêmes gardés, 2 mis de côté et 23 à confirmer au lieu de 5 et 19 (manche 13).
- À vérifier à la main : une page « Top Garage Ducos » cite Flash Car à la même adresse (zone de la Petite
  Cocotte). Il pourrait être un garage du réseau Top Garage.

Règle non écrite : chercher l'email lui-même sur Google. Google ignore l'adresse exacte et renvoie des pages sans
rapport : le forum d'Orange pour une adresse `…@orange.fr`, des « Flash Auto » de toute la France. Une règle tirée
de ces résultats placerait des homonymes au hasard. Le site du garage de Saint-Esprit vient de la recherche par son
nom.

## Manche 15 — Suisse, les trois métiers (n° 20), et la suite France (n° 18 et 21), vague 5 (1er novembre, nuit)

Recherche de l'app n° 20 (17 par métier, canal « email », note ≥ 4,0, avec les registres, mode « Je valide »), la
première suisse sur le moteur corrigé. 729 requêtes, arrêtée sur la limite de 12 communes par métier (relancée) :
garages 7 gardés et 8 à confirmer, paysagistes 2 et 5, électriciens 2 et 0. Écartés : 155 « déjà écartés par une
recherche précédente » (sites et refus de publicité vus en octobre), 103 refus de publicité (astérisque des
annuaires), 57 mauvais métier, 39 sites, 22 hors de Suisse. En Suisse romande, presque tous les paysagistes et
électriciens ont un site ou refusent la publicité.

### Vérité terrain de la n° 20 (19 candidats avec email : 9 gardés, 10 à confirmer)

- **13 validés** (n° 425 à 435, 440, 441) : garages Cano François, YP Services, Garage 2S (site = page d'hébergeur
  « Bienvenue sur … »), Paratte Carrosserie (idem), Centre-auto, Garage R. Marques, Garage Gambin (site mort) ;
  paysagistes LML Jardin, Shuti Arcenciel Arrosage, Flo Jardinier (titulaire inscrit à Renens, domaine
  `flojardinier.com` vide), Francis Caron ; électriciens Rapin Telecom-Électricité, J.-C. Berger SA.
- Écartés ensuite : Francis Caron par l'app à la création (radié au registre, et un site en ligne), Cano François
  à l'enrichissement (radié d'office le 02.10.2026, voir `docs/ENRICHMENT_TRAINING.md`, manche 6).
- **Précision des gardés : 7 bons sur 9 (78 %)** : Willemin refusé, Cano François radié.
- À confirmer : 4 bons sur 10 (Centre-auto, Garage Gambin, Shuti Arcenciel Arrosage, Flo Jardinier).

| Candidat | Place donnée par l'app | Vérité | Règle à écrire |
|---|---|---|---|
| MML Automobiles (Chavornay) | à confirmer | email de Viviane Auto, autre affaire de la commune, avec son site | quand la page ou le domaine qui porte l'email nomme une autre entreprise (autre nom, autre adresse), ce n'est pas son email : écarté |
| Le Mechanic Moderne (Moutier) | à confirmer | email d'ACM Auto Centre Moutier SA, site en ligne | idem |
| Garage Bonito (Vétroz) | à confirmer | email pris sur la page autopro.ch d'Auto Caetano (autre adresse de Vétroz, site `auto-caetano.ch`) | idem |
| Garage Autotec (La Neuveville) | à confirmer, « site déclaré pas retrouvé » | site de fiche `autotec.stopgo.ch` : réseau Stop+Go | un sous-domaine du site d'un réseau fait un membre du réseau, comme AD, Motrio, Bosch |
| Garage St Christophe Willemin SA (Develier) | gardé | concession Toyota : catégorie « Concessionnaire automobile », domaines `willemin.ch` et `garage.toyota.ch` | la catégorie « concessionnaire » et un domaine de marque font une concession |
| Cédric Arn (Le Landeron) | à confirmer | email `cedriconair@…` que rien ne situe, 2 avis | rien à changer : le doute était juste |
| Francis Caron (Le Landeron) | à confirmer, preuve « c » | l'extrait qui porte l'email porte aussi le même portable que la fiche (preuve « a ») ; mais radié au registre, et un site trouvé par la ville du registre (Cornaux) | lire l'état du numéro Zefix dès la recherche, comme « société cessée » en France |

- Erreurs de ma part : Francis Caron et Flo Jardinier d'abord refusés. Flo Jardinier repris à juste titre ;
  Francis Caron repris à tort, l'app l'a écarté.

### Suite de la n° 18 (Arles, Perpignan, Chambéry, Mulhouse) et n° 21 (garages, Narbonne)

- La n° 18 s'arrête sur son budget (1 597 requêtes) à 13 paysagistes et 9 électriciens validés : relancée pour
  les électriciens surtout. La n° 22 (mêmes métiers) a été annulée, en double.
- **5 validés** : Aubane Paysage (n° 436), Jardins Grégory (n° 437), Les Jardins de Tistou (n° 438), Hibiscus
  Garden (n° 439), Daguier Multiservices (n° 442).
- **4 refusés** :

| Candidat | Place donnée par l'app | Vérité | Règle à écrire |
|---|---|---|---|
| Coupe Feuilles Jardinier Perpignan 66 | à confirmer | l'email vient de la page Facebook « Nicolas Le Jardinier 66 », un autre jardinier (site `nicolas-le-jardinier-66.fr`, 49 avis) ; la fiche est celle de Nicolas Levavasseur (@coupefeuilles, Alénya) | une page Facebook trouvée par recherche doit partager les mots distinctifs du nom (« Coupe Feuilles »), jamais seulement le métier, la ville ou le numéro de département |
| Au Jardin De L'economie (Perpignan) | gardé | registre au même nom en 52.2A (fruits et légumes, 1991) ; la fiche Google du nom dit « Primeur » | une société du même nom dans une activité sans rapport donne au mieux « à confirmer » |
| Espaces Verts Peyret (Canet-en-Roussillon) | gardé | sa fiche déclare `espaces-verts-peyret.com`, qui mène à `espaces-verts-peyret.fr`, en ligne | à comprendre : pourquoi le site de la fiche n'a pas été lu ni vu par la vérification |
| debrenne paysagiste (Mulhouse) | gardé | adresse de fiche « 2 passage de l'Hôtel de Ville » (la mairie), aucune entreprise à ce nom dans le Haut-Rhin, la famille inscrite ailleurs avec « rattachement mairie » | une adresse de fiche à la mairie est une commune de rattachement, pas un atelier : « à confirmer » |

- N° 21 (garages France, 2 demandés) : 3 gardés à Narbonne, tous bons (Ghossain Auto, Technic Auto, Yes Auto).
  Technic Auto validé (n° 443, le 17ᵉ garage français), les deux autres laissés en réserve.
- Envoyé à la session de corrections le 1er novembre vers 4 h 30 et 6 h.

### Résultat

Moteur corrigé le 1er novembre (`d4151782`). Aucune recherche relancée en prod, aucun candidat touché : chaque cas a
été rejoué en lecture seule depuis sa seule fiche Google (vérification, recherche de contact, registres), Bright
Data, le juge, les registres et les sites lus pour de vrai.

| Règle | Avant | Après |
|---|---|---|
| Une page Facebook trouvée par recherche doit partager un mot propre du nom qui ne soit pas un nombre : un numéro de département (« 66 »), le métier ou la ville ne suffisent pas | Coupe Feuilles : la page « … Le Jardinier 66 » d'un autre jardinier, et son email | aucune page ni email : écarté, sans contact. Au balayage, M.A.S ELEC 30 perd aussi la page « BC Elec » |
| Une page dont le titre ne nomme pas l'entreprise, qui écrit une autre rue que la sienne et jamais son numéro, est celle d'une autre entreprise : ni son email ni son patron ne sont pris | Le Mechanic Moderne, Garage Bonito : l'email de l'autre garage, « à confirmer » ; Bonito avait aussi pour patron celui de l'autre garage | ni email ni patron : Bonito mis de côté (portable seul), Le Mechanic Moderne sans contact |
| Un email écrit depuis le domaine du site en ligne d'une autre affaire (un mot du métier et un nom qui n'est pas le sien : `viviane-auto.ch`) est oublié ; le domaine d'un groupe (« groupe-….ch », sans mot du métier) reste « à vérifier » | MML Automobiles : « à confirmer » | email oublié (« viviane-auto.ch est le site en ligne d'une autre entreprise ») : écarté, sans contact |
| Stop+Go est un réseau : son nom (« stop+go »), son site `stopgo.ch` et ses sous-domaines, le nom du panneau Google | Garage Autotec : « à confirmer, site déclaré pas retrouvé » | écarté : réseau |
| Une page du site d'une marque (`garage.toyota.ch/…`, `kia.fr/…`) qui nomme le garage dans sa ville en fait un concessionnaire de la marque | Willemin : gardé | écarté : « Agent ou concessionnaire Toyota » (rejoué sur les résultats Google du 1er novembre) |
| Un email qui porte le nom, écrit à côté du propre numéro de l'entreprise sur une page qui la nomme, est publié par elle : preuve « a » | le paysagiste du Landeron (c6212) : preuve « c » | preuve « a » ; au balayage, 4 emails passent de « b » à « a » (Aubane Paysage, Jardins Grégory, C-velec, Garage Autotec), aucun candidat ne change de place |
| La seule société ouverte au nom exact, inscrite dans l'activité d'un autre métier, laisse le prospect « à confirmer » ; les codes de l'ancienne nomenclature (« 50.2Z » garage, « 45.3A » électricien, « 01.4A » paysagiste) comptent pour le métier | Au Jardin De L'economie : gardé | « à confirmer » : « Le registre inscrit « AU JARDIN DE L'ECONOMIE » sous une autre activité (52.2A) » |
| Quand aucun site n'est connu et que la fiche n'a pas dit « pas de site », la vérification lit la page d'accueil des domaines qui épellent le nom (`espaces-verts-peyret.fr`, puis `.com`, avec et sans tirets) : c'est son site si la page nomme l'entreprise et montre son numéro ou sa ville | Espaces Verts Peyret : gardé sans site | écarté : a déjà un site (`espaces-verts-peyret.fr`) |
| Une page d'hébergeur « Bienvenue sur … » ou une page vide est une page d'attente (`placeholder`), plus un site mort | `garage2s.ch`, `paratte-carrosserie.ch` : site mort ; `flojardinier.com` : en ligne | page d'attente pour les trois : jamais « a un site », jamais « votre site ne répond plus » |

- Peyret, la cause : la page de résultats locaux qui contenait sa fiche (Perpignan, 3ᵉ page, 3 h 13) a été lue par
  le repli JSON de Bright Data, qui ne donne aucun bouton « Site Web » (« 20 fiches Google lues, 0 sans site déclaré,
  20 à vérifier »). La recherche de son nom n'a montré que des annuaires, et le panneau Google, qui porte le site,
  n'est pas toujours là. Le 1er novembre, le panneau le donnait ; la lecture du domaine à son nom le trouve sans lui.
- Balayage hors ligne des 74 candidats avec email des n° 18 et 20 (gardés, à confirmer, mis de côté, refusés à la
  main) : aucun gardé ne perd son email ni sa page.
- Non écrit : la catégorie « Concessionnaire automobile » seule (un garage qui vend aussi des voitures reste dans le
  métier) ; d'autres réseaux suisses que Stop+Go, faute de cas.
- Hors de la liste envoyée au départ, écrit ensuite (`d7dec829`) :
  - le numéro CHE que la recherche a lu désigne la société, où qu'elle siège : radiée depuis moins de trois ans ou
    en liquidation, le candidat est écarté dès la recherche, comme « Société cessée » en France. Rejoué : le
    paysagiste du Landeron (c6212), inscrit à Cornaux et radié en février 2025, est écarté (« Société radiée selon
    Registre du commerce (Zefix) ») ;
  - sans numéro, une société du même nom, à part un mot de métier (« Garage Exemple » pour « Exemple »), compte à
    son siège ou au code postal de son adresse inscrite : une commune fusionnée garde son code postal ;
  - une fiche à l'adresse de la mairie (« Hôtel de ville », « mairie »), sans entreprise de son nom inscrite dans le
    département, est « à confirmer » : une commune de rattachement, pas un atelier. Rejoué : debrenne paysagiste
    (c6728) passe « à confirmer ». Un commerce de la « rue de l'Hôtel de Ville » a sa société au registre : il n'est
    pas touché.
- Non écrit : une seconde vérification dans la ville du registre quand elle diffère de celle de la fiche (une
  requête payante de plus ; la radiation suffit à écarter c6212, dont le site se trouve en cherchant à Cornaux).

## Manche 16 — les réseaux vus sur les photos des sites, vague 5 (1er novembre, matin)

Pas une recherche : la revue des sites générés pour les 29 garages validés, par une planche-contact de leurs photos
d'en-tête et « à propos », puis les légendes que l'enrichissement écrit pour chaque photo (`photo_labels`). Elle a
fait écarter **7 garages validés** que ni la recherche ni l'enrichissement n'avaient vus.

| Prospect | Ce qui l'a trahi | Vérité | Règle à écrire |
|---|---|---|---|
| GARAGE CS AUTO (n° 377, Châtellerault) | photo d'en-tête : le visuel 3D « PRECISIUM Garage Automobiles Services » | réseau Precisium | ajouter Precisium aux réseaux |
| MJV AUTOMOBILES (n° 379) | légende de photo : « Panneau promotionnel avec logo AD Garage Expert… » | réseau AD | un nom de réseau lu sur une enseigne ou un panneau du garage (pas sur un produit) écarte, ou signale « réseau ? » |
| GARAGE NORVILLE (n° 381, Montluçon) | enseigne RENAULT sur la photo ; « Garage Norville Agent Renault » dans tous les annuaires | agent Renault | « agent / agréé / concessionnaire <marque> » dans un titre d'annuaire, la description ou la catégorie fait un réseau de marque |
| Garage SELECTION AUTO CHOLET (n° 386) | façade « TOP GARAGE » et « G Groupauto » ; 5 légendes « Top Garage » | réseau Top Garage (Groupauto) | ajouter Top Garage et Groupauto aux réseaux |
| Auto Expert (n° 388, Illzach) | enseigne EUROREPAR ; fiche eurorepar.fr « réseau Euro Repar Car Service » | réseau Eurorepar | ajouter Eurorepar aux réseaux |
| GARAGE SERV'AUTO (n° 390, Saint-Paul-lès-Dax) | un résultat Bing : `servauto.fr` | site en ligne (WordPress, © 2026), même adresse et même téléphone sur sa page contact | « Serv'Auto » doit reconnaître le domaine `servauto` : normaliser apostrophes et tirets dans le contrôle du domaine propre |
| Garage Jean-Baptiste (n° 445, Saint-Pierre, Martinique) | sa propre description : « agréé Renault » | réparateur agréé de la marque | règle « agent / agréé » ci-dessus |

- Les légendes ne suffisent pas toujours seules : une marque de produit (« batterie Bosch », « calculateur Bosch
  EDC17 », « huile Total Quartz ») ne fait pas un réseau.
- Remplacés : Ghossain Auto (n° 446) et Yes Auto (n° 447), les deux réserves de la n° 21 ; recherche n° 24 (6
  garages France) mise en file, en pause avec les autres depuis la suspension de Bright Data (voir
  `~/.claude/skills/devleadhunter/reference/wave-5-plan.md`).
- Envoyé à la session de corrections le 1er novembre vers 6 h 20.
- Leçon de méthode : la planche-contact des photos d'un lot de garages coûte dix minutes et voit ce que les textes
  cachent. La faire avant de compter un garage, pas après avoir généré son site.
