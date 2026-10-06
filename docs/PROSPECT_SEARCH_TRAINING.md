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
