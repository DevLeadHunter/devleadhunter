# Modèles francs : emails et SMS (sites web + réceptionniste IA)

Document de validation des modèles de prospection. Rien ne part tant qu'il n'est pas relu : les modèles ci-dessous sont ceux du code (seeder et bibliothèque SMS).

## Pourquoi

Vague 3 (22/09 au 01/10/2026) : le modèle d'email franc (modèle 30, « le site de {entreprise} », prix et date écrits noir sur blanc) a obtenu 35 % de vrais clics (45 % chez les artisans), contre un ou deux clics réels sur 27 mails dans les vagues 1 et 2. Les deux intéressés ont réagi à l'offre écrite.

Règle n° 1 (décision produit du 02/10/2026), pour tous les modules, email et SMS : des messages simples, où le prospect n'a aucune raison de se méfier. Chaque message dit :

1. qui écrit et pourquoi, en une phrase ;
2. ce qu'on a préparé pour lui, avec le lien ;
3. le prix dès le premier message (site : `{prix}`, 500 €, une seule fois, pas d'abonnement ; réceptionniste : `{prix_assistant}`, 79 € par mois, premier mois satisfait ou remboursé) ;
4. la vraie date de retrait de la démo (`{date_expiration}`) ;
5. une sortie facile : si c'est non, il le dit et on ne le recontacte plus ;
6. une seule demande, légère : un mot suffit, oui, non ou une question.

Pour la réceptionniste : dire clairement que c'est une assistante virtuelle (IA), pas une personne, et qu'elle vit à une adresse à son nom (le prospect n'a pas besoin de site).

Les refus sont acceptés : aucun modèle n'a été adouci pour les éviter.

## 1. Audit d'usage réel (prod, lecture seule, 03/10/2026)

14 campagnes (12 email, 2 SMS), 23 SMS envoyés, 39 modèles d'email visibles sur le compte admin. Confirmé : les mêmes modèles ont servi à chaque vague.

### Emails : nombre de campagnes ayant utilisé chaque modèle

Usages = J1 (template A) / variante B / relances (`campaign_follow_ups`).

| id | Modèle (nom en prod) | Catégorie | Usages J1 / B / relance | Décision |
| --- | --- | --- | --- | --- |
| 1 à 17 | Ancienne bibliothèque de juillet (17 modèles) | mixte | 0 / 0 / 0 (déjà archivés) | Inchangés (déjà inactifs) |
| 18 | Visibilité - on vous cherche | premier email | 4 / 0 / 0 (vague 1) | Gardé, réécrit franc |
| 19 | Crédibilité - la première impression | premier email | 1 / 4 / 0 (vague 1 en B, vague 2 démo) | Gardé, réécrit franc |
| 20 | Bouche-à-oreille - on vous retrouve | premier email | 0 / 0 / 0 | Désactivé (jamais servi, n'apporte rien de plus que le franc) |
| 21 | Vidéo - je vous montre | premier email | 1 / 0 / 0 (vague 2 vidéo) | Gardé, réécrit franc (vidéo seule porte) |
| 22 | Site en panne - premier email | premier email | 0 / 0 / 0 | Gardé, réécrit franc (situation distincte : site mort, `{ancien_site}`) |
| 23 | Refonte - premier email | premier email | 1 / 0 / 0 (Barbier d'Antan) | Gardé, réécrit franc |
| 24 | Rappel court | relance | 0 / 0 / 4 (vague 1) | Gardé, réécrit franc |
| 25 | Offre à vie | relance | 0 / 0 / 2 (vague 2) | Gardé, réécrit franc |
| 26 | Autonomie - vous gardez la main | relance | 0 / 0 / 0 | Désactivé (jamais servi ; « vous modifiez vous-même » est dans tous les modèles francs) |
| 27 | Urgence douce | relance | 0 / 0 / 0 | Désactivé (jamais servi ; la vraie date remplace l'urgence floue) |
| 28 | Site en panne - relance | relance | 0 / 0 / 0 | Désactivé (jamais servi ; la relance franche convient) |
| 29 | Refonte - relance | relance | 0 / 0 / 1 (Barbier d'Antan) | Gardé, réécrit franc |
| 30 | Franc - prix et date (France/Belgique), modèle perso du compte admin | premier email | 2 / 0 / 0 (vague 3 FR, BE) | Intact. Base de « Franc - premier contact » |
| 31 | Franc - prix et date (Suisse), modèle perso | premier email | 1 / 0 / 0 (vague 3 CH) | Intact. Pas dupliqué : `{prix}` est résolu par pays à l'envoi |
| 32 | Franc - relance dernier rappel, modèle perso | relance | 0 / 0 / 3 (vague 3) | Intact. Base de « Franc - relance » |
| 33 | Franc - dernier rappel démos qui expirent (chauds), modèle perso | premier email | 1 / 0 / 0 (vague 3 dernier rappel) | Intact. Base de « Franc - dernier rappel avant retrait » |
| 34 | Assistant IA - réponses 24/7 | premier email | 1 / 0 / 0 (campagne 21 « Parcours client Dibodev », 1 prospect, test interne) | Renommé « Réceptionniste IA - le soir, personne ne répond », réécrit franc |
| 35 | Assistant IA - multilingue | premier email | 0 / 0 / 0 | Renommé « Réceptionniste IA - dans leur langue », réécrit franc |
| 36 | Assistant IA - devis par photo | premier email | 0 / 0 / 0 | Renommé « Réceptionniste IA - devis par photo », réécrit franc |
| 37 | Assistant IA - relance | relance | 0 / 0 / 0 | Renommé « Réceptionniste IA - relance », réécrit franc |
| 38 | Assistant IA - le prix cash | relance | 0 / 0 / 0 | Renommé « Réceptionniste IA - le prix, sans détour », réécrit franc |
| 39 | Assistant IA - vidéo | premier email | 0 / 0 / 0 | Renommé « Réceptionniste IA - en vidéo », réécrit franc |

Les modèles 30 à 33 sont les modèles personnels du compte admin (`is_library = 0`) : la migration ne les touche pas, ils restent tels quels.

### SMS : messages envoyés et clés utilisées

23 SMS en base (03/09 au 28/09/2026) :

| Modèle (clé) | Envois | Détail |
| --- | --- | --- |
| `direct` (premier contact par défaut) | 7 | Vague 2 SMS (campagne 14, 5 prospects, dont Germain Paysagiste parti en 2 segments) + Tasty Korea (06/09) + Direct Auto |
| `offre-a-vie` (relance J+30) | 7 | Campagne système « Relances SMS J+30 » (campagne 16), 6 délivrés, 1 échec (Chez Mimon) |
| `video` | 0 | Un seul envoi vidéo, manuel et réécrit à la main (Mayer Paysagiste, 10/09) |
| Texte libre | 2 | Relance manuelle Soup' R Burger (03/09), test « toto-bidule » |
| Tests | 3 | Deux envois de test en échec, « bonjour ceci est un test » |
| Messages de service (alertes réceptionniste) | 4 | Nouvelle demande de devis, rappels : pas de la prospection |
| `visibilite`, `credibilite`, `bouche-a-oreille`, `site-en-panne`, `refonte`, `rappel-court`, `offre-a-vie-video`, `autonomie`, `urgence-douce`, `site-en-panne-relance`, `refonte-relance`, `assistant-*` | 0 | Jamais envoyés |

Clés par défaut dans le code et la configuration du compte admin :

- `DEFAULT_FIRST_CONTACT_KEY = "direct"` (worker SMS froid et campagnes SMS sans clé) ;
- `DEFAULT_FOLLOW_UP_KEY = "rappel-court"` (jamais utilisé en vrai : le compte admin a choisi `offre-a-vie`) ;
- `sms_configs.relance_template_key = "offre-a-vie"` sur le compte admin ;
- `campaigns.sms_template_key` : `direct` (campagne 14), `offre-a-vie` (campagne 16).

## 2. Ce qui change

### Emails, module sites web (13 modèles, tous francs)

Premier email : **Franc - premier contact** (recommandé, épinglé en tête, repris du modèle 30 avec `{prix}` et `{date_expiration}`), Visibilité - on vous cherche, Crédibilité - la première impression, Vidéo - je vous montre, Site en panne - premier email, Refonte - premier email, Franc - dernier rappel avant retrait (repris du 33 ; catégorie premier email comme le 33, parce qu'il ouvre sa propre campagne vers les prospects dont la démo expire).

Relance : **Franc - relance** (recommandé, repris du 32), **Franc - relance vidéo** (nouveau : la relance J+3 en vidéo prévue pour la vague 4), Rappel court, Offre à vie, Refonte - relance.

Retirés (désactivés en prod, jamais supprimés) : Bouche-à-oreille - on vous retrouve, Autonomie - vous gardez la main, Urgence douce, Site en panne - relance. Aucun n'a jamais servi dans une campagne.

Choix de copy communs : plus de `{vignette_video}` dans les emails texte (une seule porte par mail : la vidéo est un angle à part, J1 « Vidéo - je vous montre » ou relance « Franc - relance vidéo ») ; « ici » et les tirets cadratins des modèles 30 à 33 ont été retirés des versions bibliothèque ; le corps finit nu, la signature vient du bloc signature à l'envoi.

### Emails, module réceptionniste IA (6 modèles, renommés et réécrits)

« Assistant IA - … » devient « Réceptionniste IA - … » (le renommage se fait sur la même ligne en base : la campagne 21 garde son modèle). Chaque modèle dit « une assistante virtuelle (IA), pas une personne », « à une adresse à son nom », `{prix_assistant}` par mois sans engagement, premier mois satisfait ou remboursé, `{date_expiration}`, et la sortie facile. Aucun ne parle de « votre site » ni d'installation.

### SMS (16 modèles, tous francs, 2 segments)

- Module sites web : `direct` (Franc - premier contact), `video`, `site-en-panne`, `refonte` ; relances `rappel-court`, `offre-a-vie`, `offre-a-vie-video`, `site-en-panne-relance`, `refonte-relance`.
- Module réceptionniste : `assistant-24-7`, `assistant-langues`, `assistant-demandes`, `assistant-video` ; relances `assistant-relance`, `assistant-relance-video`, `assistant-prix-cash`.
- Retirés du code : `visibilite`, `credibilite`, `bouche-a-oreille`, `autonomie`, `urgence-douce` (jamais envoyés ; leur angle tenait en une demi-phrase qui ne rentre plus dans un SMS franc). Les clés stockées en base (`direct`, `offre-a-vie`, `rappel-court`) sont conservées.
- Budget : un SMS de prospection franc prend 2 segments GSM-7 (306 caractères, mention de désinscription comprise : smsmode l'ajoute à l'envoi, 14 caractères réservés en France, 25 en Suisse). Les tests garantissent 2 segments au plus, en France comme en Suisse (prix écrits « env. 470 CHF »), avec un slug de 26 caractères, un nom d'entreprise de 26 caractères et un téléphone de 14 caractères. Les messages de service (alertes réceptionniste) restent à 1 segment.
- Nouvelle variable `{telephone}` : le téléphone public de l'expéditeur (`users.contact_phone`, celui du bandeau démo, Paramètres). L'expéditeur « Dibodev » ne reçoit pas de réponse : chaque SMS dit « Un mot me suffit, oui ou non, au {telephone}. » Si le téléphone public n'est pas renseigné, le SMS est refusé à l'envoi comme dans l'aperçu (« Renseignez votre téléphone de contact dans votre profil »).

### Migration de données (`reseed_frank_email_template_library`)

Jouée au prochain déploiement, sur les lignes de bibliothèque du compte admin uniquement : renomme les 6 modèles réceptionniste sur place, réécrit sujet et corps des modèles gardés (même nom), insère les nouveaux modèles francs, désactive les modèles retirés que personne n'a utilisés. Un modèle retiré mais encore référencé par une campagne resterait actif (signalé dans les logs). Les modèles personnels (30 à 33) ne sont pas touchés. Rejouable sans effet.

## 3. Valeurs d'exemple utilisées ci-dessous

Prospect « Garage Martin » à Clermont-Ferrand, décisionnaire « M. Martin », garagiste, ancien site `garage-martin.fr`, prix 500 €, réceptionniste « Nathan » à 79 € par mois, date d'expiration 24/10/2026 (rendue « 24 octobre »), téléphone public `06 12 34 56 78` et prénom d'expéditeur « Marc » (exemples : les vrais sont ceux des Paramètres et du compte). Dans les emails, les liens sont de vrais liens cliquables ; la vidéo est une vignette cliquable (image du site avec bouton lecture), rendue ici entre crochets. Les corps d'email s'affichent sans la signature, ajoutée à l'envoi. Les SMS montrent le texte envoyé : smsmode y ajoute ensuite sa mention de désinscription (STOP et numéro court en France, lien `no-sms.eu` en Suisse) ; le nombre de caractères indiqué compte les 14 caractères réservés en France.

## 4. Les modèles

WARNING: No ENCRYPTION_KEY found in environment. Generating new key.
This key will be lost when the server restarts!
Generated key: LDdwHn3sDAK0_C3CvUMav3k5kq0q1RbcYsTIleWj_yk=
Save this key in your .env file as ENCRYPTION_KEY
### Emails, module sites web

#### Franc - premier contact

- Catégorie : Premier email (recommandé, épinglé)
- Sujet : `le site de Garage Martin`

```
Bonjour M. Martin,

Je fais des sites web, et j'ai construit celui de Garage Martin. Il est déjà en ligne : demo.dibodev.fr/garage-martin

C'est 500 €, une seule fois. Pas d'abonnement : je le mets sur votre propre adresse, et vous modifiez ensuite textes et photos vous-même, sans dépendre de personne.

Je le garde en ligne jusqu'au 24 octobre. Après, je le retire.

Un mot me suffit : oui, non, ou une question. Si c'est non, dites-le-moi et je ne vous recontacte plus.
```

#### Visibilité - on vous cherche

- Catégorie : Premier email
- Sujet : `Garage Martin sur internet`

```
Bonjour M. Martin,

Quand quelqu'un cherche un garagiste à Clermont-Ferrand, il tombe sur ceux qui ont un site. Je fais des sites web, et j'ai construit celui de Garage Martin. Il est déjà en ligne : demo.dibodev.fr/garage-martin

C'est 500 €, une seule fois. Pas d'abonnement : je le mets sur votre propre adresse, et vous modifiez ensuite textes et photos vous-même, sans dépendre de personne.

Je le garde en ligne jusqu'au 24 octobre. Après, je le retire.

Un mot me suffit : oui, non, ou une question. Si c'est non, dites-le-moi et je ne vous recontacte plus.
```

#### Crédibilité - la première impression

- Catégorie : Premier email
- Sujet : `avant qu'on vous appelle`

```
Bonjour M. Martin,

Avant d'appeler un garagiste, on regarde son site. Je fais des sites web, et j'ai construit celui de Garage Martin pour qu'on voie votre travail avant de vous appeler. Il est déjà en ligne : demo.dibodev.fr/garage-martin

C'est 500 €, une seule fois. Pas d'abonnement : je le mets sur votre propre adresse, et vous modifiez ensuite textes et photos vous-même, sans dépendre de personne.

Je le garde en ligne jusqu'au 24 octobre. Après, je le retire.

Un mot me suffit : oui, non, ou une question. Si c'est non, dites-le-moi et je ne vous recontacte plus.
```

#### Vidéo - je vous montre

- Catégorie : Premier email
- Sujet : `le site de Garage Martin, en vidéo`

```
Bonjour M. Martin,

Je fais des sites web, et j'ai construit celui de Garage Martin. Plutôt que de l'expliquer, je vous le montre en 30 secondes :

[vignette cliquable de la vidéo, lien demo.dibodev.fr/v/garage-martin]

C'est 500 €, une seule fois. Pas d'abonnement : je le mets sur votre propre adresse, et vous modifiez ensuite textes et photos vous-même, sans dépendre de personne.

Je le garde en ligne jusqu'au 24 octobre. Après, je le retire.

Un mot me suffit : oui, non, ou une question. Si c'est non, dites-le-moi et je ne vous recontacte plus.
```

#### Site en panne - premier email

- Catégorie : Premier email
- Sujet : `votre site ne répond plus`

```
Bonjour M. Martin,

En cherchant Garage Martin, je suis tombé sur garage-martin.fr : il ne répond plus. Je fais des sites web, et j'en ai construit un nouveau pour vous. Il est déjà en ligne : demo.dibodev.fr/garage-martin

C'est 500 €, une seule fois. Pas d'abonnement : je le mets sur votre adresse actuelle, et vous modifiez ensuite textes et photos vous-même, sans dépendre de personne.

Je le garde en ligne jusqu'au 24 octobre. Après, je le retire.

Un mot me suffit : oui, non, ou une question. Si c'est non, dites-le-moi et je ne vous recontacte plus.
```

#### Refonte - premier email

- Catégorie : Premier email
- Sujet : `une nouvelle version de votre site`

```
Bonjour M. Martin,

Je fais des sites web. Je suis tombé sur celui de Garage Martin, et j'en ai construit une version plus moderne, à comparer avec l'actuel. Elle est déjà en ligne : demo.dibodev.fr/garage-martin

C'est 500 €, une seule fois. Pas d'abonnement : je la mets sur votre adresse actuelle, et vous modifiez ensuite textes et photos vous-même, sans dépendre de personne.

Je la garde en ligne jusqu'au 24 octobre. Après, je la retire.

Un mot me suffit : oui, non, ou une question. Si c'est non, dites-le-moi et je ne vous recontacte plus.
```

#### Franc - relance

- Catégorie : Relance (recommandé, épinglé)
- Sujet : `avant que je le retire`

```
Bonjour M. Martin,

Dernier message, promis. Le site de Garage Martin est toujours en ligne : demo.dibodev.fr/garage-martin

Je le retire le 24 octobre. Si vous le voulez, c'est 500 €, une seule fois. Sinon, rien à faire.

Même un « non merci » me va.
```

#### Franc - relance vidéo

- Catégorie : Relance (recommandé, épinglé)
- Sujet : `le site de Garage Martin, en vidéo`

```
Bonjour M. Martin,

Je vous ai écrit il y a quelques jours au sujet du site de Garage Martin. Cette fois, je vous le montre en 30 secondes :

[vignette cliquable de la vidéo, lien demo.dibodev.fr/v/garage-martin]

Il reste en ligne jusqu'au 24 octobre. Si vous le voulez, c'est 500 €, une seule fois, sans abonnement. Sinon, rien à faire.

Même un « non merci » me va.
```

#### Franc - dernier rappel avant retrait

- Catégorie : Premier email
- Sujet : `votre site sera retiré le 24 octobre`

```
Bonjour M. Martin,

Je range mes démos : le site de Garage Martin sera retiré le 24 octobre. Il est encore en ligne : demo.dibodev.fr/garage-martin

Si vous voulez le garder, c'est 500 €, une seule fois. Je le mets sur votre propre adresse, et vous pourrez ensuite tout modifier vous-même.

Un mot me suffit, même un non.
```

#### Rappel court

- Catégorie : Relance
- Sujet : `vous avez vu votre site ?`

```
Bonjour M. Martin,

Le site de Garage Martin est toujours en ligne : demo.dibodev.fr/garage-martin

C'est 500 €, une seule fois, sans abonnement. Je le retire le 24 octobre.

Un mot me suffit, même un non.
```

#### Offre à vie

- Catégorie : Relance
- Sujet : `un seul paiement, le site est à vous`

```
Bonjour M. Martin,

Le site de Garage Martin est toujours en ligne : demo.dibodev.fr/garage-martin

500 € une seule fois, et il est à vous : pas d'abonnement, vous ne me repayez jamais, et je m'occupe de la mise en ligne sur votre propre adresse.

Je le garde jusqu'au 24 octobre. Après, je le retire.

Un mot me suffit, même un non.
```

#### Refonte - relance

- Catégorie : Relance
- Sujet : `votre ancien site ou le nouveau ?`

```
Bonjour M. Martin,

La nouvelle version du site de Garage Martin est toujours en ligne, à comparer avec l'actuel : demo.dibodev.fr/garage-martin

C'est 500 €, une seule fois, sans abonnement. Je la mets sur votre adresse actuelle, et vous gardez la main sur tout le contenu.

Je la garde en ligne jusqu'au 24 octobre. Après, je la retire.

Un mot me suffit, même un non.
```

### Emails, module réceptionniste IA

#### Réceptionniste IA - le soir, personne ne répond

- Catégorie : Premier email
- Sujet : `une réceptionniste pour Garage Martin`

```
Bonjour M. Martin,

Je fais des outils web pour les artisans et les commerçants, et j'ai préparé pour Garage Martin une réceptionniste, Nathan : une assistante virtuelle (IA), pas une personne. Le soir et le week-end, elle répond tout de suite à vos clients et vous transmet chaque demande. Elle est déjà en ligne, à une adresse à son nom : demo.dibodev.fr/ia/garage-martin

[vignette cliquable de la vidéo, lien demo.dibodev.fr/va/garage-martin]

C'est 79 € par mois, sans engagement. Le premier mois est satisfait ou remboursé.

Je la garde en ligne jusqu'au 24 octobre. Après, je la retire.

Un mot me suffit : oui, non, ou une question. Si c'est non, dites-le-moi et je ne vous recontacte plus.
```

#### Réceptionniste IA - devis par photo

- Catégorie : Premier email
- Sujet : `une photo, une demande de devis`

```
Bonjour M. Martin,

Je fais des outils web pour les artisans et les commerçants, et j'ai préparé pour Garage Martin une réceptionniste, Nathan : une assistante virtuelle (IA), pas une personne. Un client lui envoie la photo de son problème à 22 h, elle pose les bonnes questions et vous transmet une demande de devis complète. Elle est déjà en ligne, à une adresse à son nom, et elle accepte n'importe quelle photo : demo.dibodev.fr/ia/garage-martin

[vignette cliquable de la vidéo, lien demo.dibodev.fr/va/garage-martin]

C'est 79 € par mois, sans engagement. Le premier mois est satisfait ou remboursé.

Je la garde en ligne jusqu'au 24 octobre. Après, je la retire.

Un mot me suffit : oui, non, ou une question. Si c'est non, dites-le-moi et je ne vous recontacte plus.
```

#### Réceptionniste IA - dans leur langue

- Catégorie : Premier email
- Sujet : `vos clients, dans leur langue`

```
Bonjour M. Martin,

Une partie des clients de Garage Martin n'ose pas écrire en français et repart sans rien demander. Je fais des outils web pour les artisans et les commerçants, et j'ai préparé pour vous une réceptionniste, Nathan : une assistante virtuelle (IA), pas une personne. Elle répond à vos clients dans leur langue, 24 h sur 24, et vous transmet leur demande en français. Elle est déjà en ligne, à une adresse à son nom : demo.dibodev.fr/ia/garage-martin

[vignette cliquable de la vidéo, lien demo.dibodev.fr/va/garage-martin]

C'est 79 € par mois, sans engagement. Le premier mois est satisfait ou remboursé.

Je la garde en ligne jusqu'au 24 octobre. Après, je la retire.

Un mot me suffit : oui, non, ou une question. Si c'est non, dites-le-moi et je ne vous recontacte plus.
```

#### Réceptionniste IA - en vidéo

- Catégorie : Premier email
- Sujet : `votre réceptionniste, en vidéo`

```
Bonjour M. Martin,

Je fais des outils web pour les artisans et les commerçants, et j'ai préparé pour Garage Martin une réceptionniste, Nathan : une assistante virtuelle (IA), pas une personne, qui répond à vos clients le soir et le week-end et vous transmet chaque demande. Je vous la montre en 30 secondes :

[vignette cliquable de la vidéo, lien demo.dibodev.fr/va/garage-martin]

C'est 79 € par mois, sans engagement. Le premier mois est satisfait ou remboursé.

Je la garde en ligne jusqu'au 24 octobre. Après, je la retire.

Un mot me suffit : oui, non, ou une question. Si c'est non, dites-le-moi et je ne vous recontacte plus.
```

#### Réceptionniste IA - relance

- Catégorie : Relance
- Sujet : `avant que je la retire`

```
Bonjour M. Martin,

Dernier message, promis. Nathan, la réceptionniste que j'ai préparée pour Garage Martin (une assistante virtuelle, IA), répond toujours à cette adresse : demo.dibodev.fr/ia/garage-martin

Je la retire le 24 octobre. Si vous la voulez, c'est 79 € par mois, sans engagement, premier mois satisfait ou remboursé. Sinon, rien à faire.

Même un « non merci » me va.
```

#### Réceptionniste IA - le prix, sans détour

- Catégorie : Relance
- Sujet : `le prix de la réceptionniste`

```
Bonjour M. Martin,

Sans détour : 79 € par mois pour que Nathan, votre réceptionniste (une assistante virtuelle, IA), réponde à vos clients à votre place quand vous ne pouvez pas. Sans engagement, premier mois satisfait ou remboursé.

Elle est toujours en ligne, à une adresse à son nom : demo.dibodev.fr/ia/garage-martin

Je la retire le 24 octobre. Un mot me suffit, même un non.
```

### SMS, module sites web

#### Franc - premier contact (`direct`)

- Catégorie : Premier contact ; 2 segments, 246 caractères (mention STOP comprise)

```
Bonjour M. Martin, je fais des sites web et j'ai construit celui de Garage Martin, il est en ligne : demo.dibodev.fr/s/garage-martin C'est 500 €, une seule fois, sans abonnement. Un mot me suffit, oui ou non, au 06 12 34 56 78. Marc
```

#### Vidéo - je vous montre (`video`)

- Catégorie : Premier contact, repli sans vidéo : `direct` ; 2 segments, 249 caractères (mention STOP comprise)

```
Bonjour M. Martin, je fais des sites web et j'ai construit celui de Garage Martin. En 30 s de vidéo : demo.dibodev.fr/s/v/garage-martin C'est 500 €, une seule fois, sans abonnement. Un mot me suffit, oui ou non, au 06 12 34 56 78. Marc
```

#### Site en panne (`site-en-panne`)

- Catégorie : Premier contact ; 2 segments, 270 caractères (mention STOP comprise)

```
Bonjour M. Martin, garage-martin.fr ne répond plus. Je fais des sites web et j'en ai construit un nouveau, il est en ligne : demo.dibodev.fr/s/garage-martin C'est 500 €, une seule fois, sans abonnement. Un mot me suffit, oui ou non, au 06 12 34 56 78. Marc
```

#### Refonte (`refonte`)

- Catégorie : Premier contact ; 2 segments, 271 caractères (mention STOP comprise)

```
Bonjour M. Martin, je fais des sites web et j'ai construit une version plus moderne de votre site, à comparer avec l'actuel : demo.dibodev.fr/s/garage-martin C'est 500 €, une seule fois, sans abonnement. Un mot me suffit, oui ou non, au 06 12 34 56 78. Marc
```

#### Rappel court (`rappel-court`)

- Catégorie : Relance J+30 ; 2 segments, 196 caractères (mention STOP comprise)

```
Bonjour M. Martin, le site envoyé par email est toujours en ligne : demo.dibodev.fr/s/garage-martin C'est 500 €, une seule fois. Un mot me suffit, oui ou non, au 06 12 34 56 78. Marc
```

#### Offre à vie (`offre-a-vie`)

- Catégorie : Relance J+30 ; 2 segments, 257 caractères (mention STOP comprise)

```
Bonjour M. Martin, le site de Garage Martin envoyé par email reste en ligne : demo.dibodev.fr/s/garage-martin 500 € une seule fois, sans abonnement, il est à vous, sur votre propre adresse. Un mot me suffit, oui ou non, au 06 12 34 56 78. Marc
```

#### Offre à vie - vidéo (`offre-a-vie-video`)

- Catégorie : Relance J+30, repli sans vidéo : `offre-a-vie` ; 2 segments, 222 caractères (mention STOP comprise)

```
Bonjour M. Martin, le site envoyé par email, en 30 s de vidéo : demo.dibodev.fr/s/v/garage-martin 500 € une seule fois, sans abonnement, et il est à vous. Un mot me suffit, oui ou non, au 06 12 34 56 78. Marc
```

#### Site en panne - relance (`site-en-panne-relance`)

- Catégorie : Relance J+30 ; 2 segments, 255 caractères (mention STOP comprise)

```
Bonjour M. Martin, garage-martin.fr est toujours en erreur. Le nouveau site, envoyé par email, est en ligne : demo.dibodev.fr/s/garage-martin C'est 500 €, une seule fois, sans abonnement. Un mot me suffit, oui ou non, au 06 12 34 56 78. Marc
```

#### Refonte - relance (`refonte-relance`)

- Catégorie : Relance J+30 ; 2 segments, 233 caractères (mention STOP comprise)

```
Bonjour M. Martin, la nouvelle version de votre site, envoyée par email, est en ligne : demo.dibodev.fr/s/garage-martin C'est 500 €, une seule fois, sans abonnement. Un mot me suffit, oui ou non, au 06 12 34 56 78. Marc
```

### SMS, module réceptionniste IA

#### Réceptionniste IA - le soir, personne ne répond (`assistant-24-7`)

- Catégorie : Premier contact ; 2 segments, 266 caractères (mention STOP comprise)

```
Bonjour M. Martin, j'ai préparé Nathan, votre réceptionniste virtuelle (une IA) : le soir, elle répond. demo.dibodev.fr/s/ia/garage-martin 79 €/mois sans engagement, 1er mois satisfait ou remboursé. Un mot me suffit, oui ou non, au 06 12 34 56 78. Marc
```

#### Réceptionniste IA - dans leur langue (`assistant-langues`)

- Catégorie : Premier contact ; 2 segments, 274 caractères (mention STOP comprise)

```
Bonjour M. Martin, j'ai préparé Nathan, votre réceptionniste virtuelle (une IA), qui parle la langue du client. demo.dibodev.fr/s/ia/garage-martin 79 €/mois sans engagement, 1er mois satisfait ou remboursé. Un mot me suffit, oui ou non, au 06 12 34 56 78. Marc
```

#### Réceptionniste IA - devis par photo (`assistant-demandes`)

- Catégorie : Premier contact ; 2 segments, 272 caractères (mention STOP comprise)

```
Bonjour M. Martin, j'ai préparé Nathan, votre réceptionniste virtuelle (une IA) : demande de devis par photo. demo.dibodev.fr/s/ia/garage-martin 79 €/mois sans engagement, 1er mois satisfait ou remboursé. Un mot me suffit, oui ou non, au 06 12 34 56 78. Marc
```

#### Réceptionniste IA - en vidéo (`assistant-video`)

- Catégorie : Premier contact, repli sans vidéo : `assistant-24-7` ; 2 segments, 262 caractères (mention STOP comprise)

```
Bonjour M. Martin, j'ai préparé Nathan, votre réceptionniste virtuelle (une IA). En 30 s de vidéo : demo.dibodev.fr/s/va/garage-martin 79 €/mois sans engagement, 1er mois satisfait ou remboursé. Un mot me suffit, oui ou non, au 06 12 34 56 78. Marc
```

#### Réceptionniste IA - relance (`assistant-relance`)

- Catégorie : Relance J+30 ; 2 segments, 265 caractères (mention STOP comprise)

```
Bonjour M. Martin, après mon email, Nathan, votre réceptionniste virtuelle (une IA), répond toujours : demo.dibodev.fr/s/ia/garage-martin 79 €/mois sans engagement, 1er mois satisfait ou remboursé. Un mot me suffit, oui ou non, au 06 12 34 56 78. Marc
```

#### Réceptionniste IA - relance vidéo (`assistant-relance-video`)

- Catégorie : Relance J+30, repli sans vidéo : `assistant-relance` ; 2 segments, 255 caractères (mention STOP comprise)

```
Bonjour M. Martin, la vidéo de mon email : votre réceptionniste virtuelle (une IA) en 30 s : demo.dibodev.fr/s/va/garage-martin 79 €/mois sans engagement, 1er mois satisfait ou remboursé. Un mot me suffit, oui ou non, au 06 12 34 56 78. Marc
```

#### Réceptionniste IA - le prix, sans détour (`assistant-prix-cash`)

- Catégorie : Relance J+30 ; 2 segments, 271 caractères (mention STOP comprise)

```
Bonjour M. Martin, le prix de mon email, sans détour : 79 €/mois pour Nathan, votre réceptionniste virtuelle (une IA). Sans engagement, 1er mois satisfait ou remboursé. demo.dibodev.fr/s/ia/garage-martin Un mot me suffit, oui ou non, au 06 12 34 56 78. Marc
```


## 5. Points à valider avant tout envoi

1. **Visibilité et Crédibilité** : gardés parce qu'ils ont servi (vagues 1 et 2) et réécrits en franc avec leur accroche en une phrase, ce qui donne un axe A/B « franc pur » contre « franc + raison ». Décision produit : les garder ou les désactiver aussi.
2. **« Je fais des sites web »** comme phrase « qui écrit » : le nom vient du bloc signature, pas du corps (sinon il doublerait). Pour la réceptionniste : « Je fais des outils web pour les artisans et les commerçants ». À valider ou à remplacer.
3. **« Franc - dernier rappel avant retrait »** est en catégorie premier email, comme le modèle 33 dont il vient, pour pouvoir ouvrir une campagne à part vers les démos qui expirent. Le passer dans l'onglet relance est un champ à changer.
4. **Relance vidéo** (« Franc - relance vidéo », `offre-a-vie-video`, `assistant-relance-video`) : la vidéo est la seule porte ; sans vidéo générée, l'email est retenu par la file et le SMS retombe sur son jumeau sans vidéo.
5. **SMS sans date de retrait** : les variables SMS n'ont pas `{date_expiration}` (le lien court `/s/{slug}` ne permet pas de retrouver la démo comme en email). À ajouter ou non (il reste 10 à 60 caractères selon le modèle).
6. **`{telephone}` vide** : réglé. Un modèle qui utilise `{telephone}` est refusé à l'envoi et dans l'aperçu tant que le téléphone public n'est pas renseigné dans Paramètres.
7. **2 segments** : réglé. Le service d'envoi autorise 2 segments pour un envoi de prospection, et le prénom n'est retiré qu'au-delà de 2 segments.
8. **Catalogue des variables SMS du composeur** (`web/app/utils/smsVariables.ts`) : réglé, `{telephone}` y est proposé (« Téléphone de contact »).
