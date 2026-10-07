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
| n° 13, 3 par métier (en cours à 10 h 40) | 4 | 4 (prospects 349 à 352) | aucun |

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
| Un paysagiste gardé : son seul email est sur « gmail.ch » | gmail.ch n'est pas Gmail : le domaine a son propre serveur de courrier, il passe tous les contrôles | Pas corrigé : un seul cas, et pas de filtre agressif sur les emails ; le contrôle à la main l'attrape |
| Un électricien français itinérant gardé en Suisse | Rien sur sa fiche ne le disait | Pas corrigé (cas isolé) |

Groq : la recherche n° 11 a épuisé le quota gratuit du jour (200 000 jetons sur gpt-oss-120b). Le juge passe désormais sur gpt-oss-20b, qui a son propre quota, quand celui du modèle principal est épuisé (`d4fbbbaa`).

### Résultat

Le 7 octobre à 10 h 40 : Suisse 39/40 (17 paysagistes, 18 garages, 4 électriciens). Les électriciens suisses restent la case la plus dure : 1 bon sur 24 villes dans la n° 11, aucun sur 12 villes dans la n° 12, 1 à Genève dans la n° 13 ; dans chaque ville, la plupart ont un site ou refusent la publicité.
