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
