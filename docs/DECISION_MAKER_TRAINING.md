# Entraînement du décisionnaire

Carnet des manches qui rendent la recherche du décisionnaire (« le patron », dont le prénom ouvre le
mail) meilleure que la recherche faite à la main avec Claude Code. Commencé le 8 octobre 2026, sur les
leads de la vague 4, avec la méthode des carnets `docs/PROSPECT_SEARCH_TRAINING.md` et
`docs/ENRICHMENT_TRAINING.md`.

**Le but (8 octobre) : que l'app trouve le décisionnaire mieux que Claude à la main, petit à petit,
campagne après campagne.** Les décisionnaires « à confirmer » dont Claude est sûr ou quasiment sûr,
Claude les valide lui-même.

## La méthode

1. À la main d'abord : registre français (recherche-entreprises), registre suisse (Zefix et ses
   publications FOSC), annuaires, page Facebook, avis et réponses du patron, adresse mail.
2. L'app sur les mêmes leads, sans rien enregistrer : la résolution de l'app tourne sur les données de
   la prod (script de mesure à blanc), puis en prod après correction.
3. Comparaison lead par lead. Un prénom faux compte plus qu'un prénom manquant : il ouvre le mail.
4. Chaque écart reçoit sa cause, une correction et un test ; on mesure l'« après ».

Note d'un lead : juste (la bonne personne, bien nommée), faux (une autre personne), ou rien.

## Manche 1 — les 23 « à confirmer » de la vague 4, et les « sûrs » douteux (8 octobre)

### À la main

- 23 propositions vérifiées une à une, et les 42 décisionnaires « sûrs » relus (registre de
  l'entreprise, avis) ; environ 1 h 30.
- 13 propositions justes, 2 ambiguës (deux gérants), 2 personnes justes mais mal nommées (prénoms
  portugais coupés au mauvais endroit), **6 fausses** :
  - une société homonyme dans un autre département (2 cas : Normandie et Calvados pour deux paysagistes
    du Lot) ;
  - une société d'aide à domicile fermée pour un paysagiste ;
  - un client remercié dans une réponse du patron (« Merci beaucoup X pour ton commentaire ») ;
  - un administrateur parti en 2023 (« X et Y ne sont plus administrateurs ») ;
  - un garage homonyme d'un autre canton suisse.
- Parmi les « sûrs », un faux : la société « CF Électricité » pour « CFS électricité » (un avis nomme
  le vrai patron, autre nom, autre adresse).
- La main a trouvé ce que l'app ratait : l'entreprise individuelle « … (DIAG AUTO 64) » pour
  « DiagAuto64 », celle de « C.BO' Jardins », la société active qui a remplacé une entreprise
  individuelle fermée.

### Par l'app (avant correction)

13 justes sur 23 propositions, 6 fausses (26 %), et 1 « sûr » faux qui serait parti dans un SMS. Les
justes restaient « à confirmer » à cause d'un candidat parasite : une signature « Merci », un garage
voisin trouvé par la recherche web, un code d'activité (piscines déclarées en travaux du bâtiment).

### Écarts et causes

| Écart | Cause | Correction |
|---|---|---|
| Homonymes d'un autre département proposés | Sans code postal (prospect trouvé sur Facebook), le département n'était pas connu ; la recherche web oubliait le code postal | Département tiré du code postal, sinon de la ville (liste officielle des communes) ; le registre est interrogé dans ce département ; une société d'un autre département n'est plus proposée |
| Sociétés fermées retenues | L'état « cessée » du registre n'était pas lu | Une société cessée n'est jamais l'entreprise (sauf celle du numéro relevé par la recherche) |
| « DiagAuto64 », « C.BO' Jardins » introuvables | Le registre veut les mots du nom tels qu'il les classe ; l'enseigne entre parenthèses n'était pas comparée | Nom cherché aussi « tel que le registre le classe » (mots collés séparés, initiales à points jointes) ; enseignes comparées mot pour mot |
| Sociétés voisines trouvées par la recherche web (« CF ÉLECTRICITÉ », « BEARN HOME RENOV », « BEARN SERVICES » de nettoyage) | Un nom légal trouvé sur le web devait seulement partager un mot avec l'enseigne, même « électricité » ou « services » | Le nom légal doit partager un mot distinctif, et la société trouvée doit porter le nom de l'entreprise mot pour mot (mots du métier à part) ou avoir pour patron la personne dont l'enseigne porte le nom |
| Client pris pour le patron | L'IA lisait un prénom remercié dans une réponse du patron | Un prénom précédé de « merci », « bonjour », « cher »… dans la citation est celui d'un client |
| Administrateur parti retenu (Suisse) | Seul « X n'est plus » était lu, pas « X et Y ne sont plus » | Départs au pluriel lus |
| Garage d'un autre canton retenu (Suisse) | Une seule société du nom en Suisse suffisait, où qu'elle soit | Une société hors de la ville du prospect n'est retenue que dans la même région postale ; si son adresse est dans la ville du prospect (village de la commune), elle compte comme trouvée exactement |
| Prénoms portugais mal coupés (Suisse) | Dans l'ancien format « Nom Prénom » sans virgule, seul le dernier mot était le prénom | Les prénoms connus qui terminent le nom sont les prénoms (« … Pedro Sérgio »), le nom reste « à confirmer » |
| Justes restées « à confirmer » (code d'activité) | Un code d'activité sans rapport rétrogradait même la société qui porte le nom exact de l'entreprise | Le contrôle d'activité ne rétrograde plus la société qui porte le nom de l'entreprise mot pour mot |

### Résultat

Après correction (`c4b7ec55`), relance en prod sur les 24 leads (les 23 propositions et le « sûr » faux) :

| | Avant | Après |
|---|---|---|
| Faux (une autre personne) | 7, dont 1 « sûr » | **0** |
| Juste et validé seul par l'app | 0 | **10** |
| Juste, proposé à confirmer | 13 (dont 2 mal nommés) | 6, bien nommés |
| Rien, alors que la main a trouvé | 0 | 2 (un nom tiré d'une adresse mail, une réponse de l'IA qui varie) |
| Ambigus (deux gérants, ou registre contre signature du patron) | 2 | 3 |

- Mesure à blanc sur les 42 « sûrs » avec le nouveau moteur : aucun ne change, sauf le faux.
- Puis validation à la main de ce dont Claude est sûr ou presque : 6 propositions confirmées, 3 noms
  saisis (le patron qui signe « Gérant » ses réponses aux avis, alors que le registre en nomme un autre ;
  un nom lu dans l'adresse mail et les initiales de l'enseigne ; un nom que l'IA n'a pas redonné).
- Vivier de la campagne : 55 décisionnaires sûrs sur 124 prospects enrichis (36 avant), 1 à confirmer
  (21 avant), 68 sans nom.
- Les sources du web et de l'IA ne répondent pas toujours pareil d'une fois sur l'autre : un même lead
  peut sortir « sûr » ou « à confirmer » selon le passage, jamais faux.
- Reste à faire (manche 2) : les 68 sans nom, surtout au Québec (19 sur 21) et chez les garages et
  paysagistes suisses ; le nom tiré de l'adresse mail (« prenom.nom@ ») ; plusieurs gérants : l'app
  prend le premier, alors qu'un SMS part sur le portable de l'un d'eux.

## Manche 2 — les 68 prospects enrichis sans patron (8 octobre)

### À la main

- 68 prospects (26 en Suisse, 23 en France, 19 au Québec), cherchés un par un dans les sources publiques :
  registres, annuaires, pages Facebook (par les extraits de Google), avis, adresses mail.
- Résultat : **52 patrons sûrs, 10 probables, 6 introuvables** (une entreprise fermée, un entrepreneur qui
  refuse la diffusion de son nom, des initiales seules).
- Ce qui a donné les noms :
  - Suisse : le registre (Zefix et ses publications FOSC) pour 22 sur 26, à condition de chercher chaque mot du
    nom (le registre ajoute souvent le nom du patron : « Exemple Mécanique Modèle ») ;
  - Québec : le registre des licences RBQ pour les 4 électriciens ; pour les garages et paysagistes, les pages
    Facebook (messages signés « Prénom, propriétaire ») et la presse locale ;
  - France : le registre interrogé par un mot du nom, par le nom du patron lu dans l'adresse mail ou dans les
    avis (« Monsieur X »), ou filtré sur le code d'activité du métier ;
  - partout : l'adresse mail « prénom.nom ».
- Les pièges :
  - un nom de famille pris pour un prénom dans l'adresse mail (« martin_… ») ;
  - un nom composé collé dans l'adresse (« prenomnom1nom2@ »), pris pour « prénom nom » ;
  - la société immobilière propriétaire des murs (SCI) prise pour le garage ;
  - le fondateur nommé dans l'enseigne qui n'est plus le patron (deux cas au Québec) ;
  - une plateforme de réservation qui signe les réponses aux avis ;
  - un numéro d'entreprise suisse passé à une société immobilière ;
  - la liste des prénoms de l'app, écrite à la main : 172 prénoms, sans « Franck », « Guy » ni « Charles ».

### Par l'app (avant correction)

Sur les 68 : 3 justes validés seuls, 1 juste proposé, **1 faux validé seul** (la SCI d'un garage, que la règle
de la manche 1 sur le nom exact laissait passer), 58 manqués.

### Écarts et causes

| Écart | Cause | Correction |
|---|---|---|
| Prénoms inconnus (« Franck », « Guy »…) | 172 prénoms écrits à la main | Liste officielle des prénoms (naissances en France depuis 1900, au Québec depuis 1980) : 9 184 prénoms, avec le sexe de presque tous leurs porteurs |
| Électriciens québécois sans patron | Aucun registre lu au Québec | Registre des licences RBQ : le dirigeant qui répond de l'administration et de la gestion de la licence de l'entreprise |
| Registre suisse : société trouvée, personne lue | Particule en tête du nom (« Titulaire: de Modèle Jules »), « Personne inscrite » au singulier, faute « Peronne inscrite », deux associés joints par « et » | Lus |
| Registre suisse : société introuvable | Le registre ajoute le nom du patron, accentue, met au pluriel ou colle un mot | Chaque mot du nom est cherché ; une société est gardée si son adresse inscrite est celle du prospect (code postal ou ville) ; les noms sont comparés sans pluriel ni féminin |
| Entreprise individuelle sans publication en ligne | Inscrite avant la mise en ligne des publications | Patron lu dans le nom de l'entreprise (« …, Nom Prénom », « … - titulaire Nom Prénom ») |
| Numéro suisse passé à une autre société | La société du numéro est devenue immobilière | Une société dont le nom ne partage plus aucun mot avec l'enseigne ne nomme personne |
| Adresse mail jamais lue | — | « prénom.nom » lu ; validé seul quand le nom de l'entreprise porte aussi le nom de famille ou les initiales ; un prénom seul, ou un nom collé que l'enseigne ne confirme pas, ne nomment personne |
| Registre français : rien par le nom | L'entreprise est classée sous le nom de son patron ou une autre enseigne | Recherche par mot du nom, par le domaine de l'adresse mail, par le patron de l'adresse mail ou des avis, dans le département, filtrée sur les codes d'activité du métier ; à égalité, l'activité principale du métier départage |
| SCI prise pour le garage (faux validé seul) | Société immobilière au nom de l'enseigne, et contrôle d'activité sauté | Une SCI n'est jamais l'entreprise ; le contrôle d'activité n'est sauté que pour le nom exact, métier compris |
| « Exemple 05 » bloqué par « Vente Exemple 05 » | Autres sociétés partageant les mots | La société au nom exact écarte les autres |
| Signature « Avatacar » | Plateforme de réservation | Une signature qui n'est pas un prénom ne compte pas |
| Patron d'une autre entreprise de la famille | Trouvé par la recherche web, nom de famille de l'enseigne | Il doit être du même métier |

### Résultat (mesure à blanc avec le code final, sur les 68)

| | Avant | Après |
|---|---|---|
| Faux (une autre personne) | 1, validé seul | **0** |
| Juste et validé seul par l'app | 3 | **29** |
| Juste, proposé à confirmer | 1 | 4 |
| Rien, alors que la main a trouvé | 58 | 29 |
| Rien des deux côtés | 5 | 6 |

- Par pays, l'app trouve maintenant 18 patrons sur 26 en Suisse, 11 sur 23 en France et 4 sur 19 au Québec
  (la main : 26, 20 et 16).
- Les deux faux apparus pendant la manche ont été repris avant le déploiement : un mot de l'enseigne qui est
  le nom d'une commune (« … Pau-Lescar ») trouvait un autre garage de cette commune, et le mot « parc » de
  « … Entretien parc et jardin » trouvait un autre paysagiste. Un mot qui nomme une commune n'est plus cherché,
  et l'entreprise trouvée par un mot ne doit porter que des mots de l'enseigne.
- Contrôle des 61 décisionnaires « sûrs » avec le nouveau moteur : aucun ne devient faux. Deux étaient
  rétrogradés en « à confirmer » en cours de route (un prénom court « Fred » lu dans l'adresse mail contre
  « Frédéric » au registre, et un patron dont le registre porte le nom sans le mot du métier) : corrigés.
- Restent manqués : au Québec, 12 garages et paysagistes que seules leurs pages Facebook (messages signés
  « Prénom, propriétaire ») ou la presse nomment ; en Suisse, 8 (entreprises non inscrites, un sigle, un atelier
  à une autre adresse que le siège, un prénom que la liste ne connaît pas, une fiche qui mélange deux
  entreprises) ; en France, 9 (registre à interroger par l'adresse, sociétés intermédiaires, codes d'activité
  inattendus).

### En prod, puis validation à la main

- Relance en prod (`6581caf6`) sur les 68 : 29 patrons validés seuls par l'app. Un seul faux, aussitôt
  repris (`2c4abccd`) : « Espaces Verts », deux mots du métier pris pour un nom, était cherché avant le vrai mot
  de l'enseigne selon un ordre qui changeait d'un passage à l'autre. Les mots du métier ne sont plus cherchés,
  et l'ordre est fixe ; relancé, le lead a son vrai patron.
- Validation par Claude de ce dont il est sûr : 5 propositions confirmées, 18 noms saisis (registres, licences,
  pages et messages des entreprises). Laissés sans nom : deux co-propriétaires à égalité, les 9 « probables »,
  les 6 introuvables.
- Une entreprise fermée est écartée (n° 302). Un patron enregistré avec ses deux prénoms garde le premier, celui
  du mail (n° 371).
- Vivier de la campagne : **107 décisionnaires sûrs sur 124 prospects enrichis** (55 avant la manche), 1 à
  confirmer, 16 sans nom (dont le n° 302, écarté).

### Reste à faire (manche 3)

- Québec : lire les messages des pages Facebook des garages et paysagistes (« Prénom, propriétaire »).
- Suisse : l'annuaire search.ch (la personne derrière l'entreprise non inscrite), l'extrait cantonal vaudois
  pour les entreprises inscrites avant 2016, l'atelier inscrit à une autre adresse que le siège.
- France : le registre interrogé par l'adresse de l'établissement ; les mentions légales d'un site.
- Données de prospects à reprendre : le site d'une autre entreprise (n° 284), le téléphone d'un autre
  entrepreneur (n° 283), une fiche qui mélange deux entreprises (n° 256), une entreprise fermée (n° 302).
