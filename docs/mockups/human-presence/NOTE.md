# Présence humaine sur la démo : maquettes à valider

Ticket Asana « [IA Code] Présence humaine sur la démo : carte « Qui est derrière ce site » + réceptionniste Dibodev dans le bandeau » (validé et élargi le 03/10). Rien n'est codé : ce dossier contient trois maquettes HTML autonomes et cette note. Décision produit à prendre, puis on implémente.

**État au 03/10 (soir)** : le choix 1 est tranché (carte en variante C : la photo et le nom de A, le texte court de B), les sept autres attendent. Voir « Décisions et avis » plus bas.

Ouvrir les maquettes dans un navigateur (double-clic suffit, aucun serveur) :

- `banner-card.html` : la carte dans le bandeau, 3 variantes (C retenue, A, B) × 3 états (pastille, ouvert bureau, ouvert mobile 375), site clair ou sombre derrière, vue scène ou planche.
- `banner-receptionist.html` : la réceptionniste Léa dans le bandeau, 2 positions × entrée/conversation × bureau/mobile, planche.
- `email-frank.html` : l'email du modèle 30 en HTML, référence actuelle + 2 variantes côte à côte, signature réelle ou allégée, compteurs (images, poids, liens) et grille de contrôle délivrabilité.

Seules dépendances réseau : le portrait de Léo (`dibodev.fr/images/about/leo-guillaume-portrait-800.webp` pour le bandeau, `dibodev.fr/email/sig-portrait.png` pour l'email), le portrait de Léa (`demo.dibodev.fr/avatars/lea.webp`) et les 4 icônes de la signature réelle. Les polices sont celles du poste (IBM Plex et Fraunces si installées, sinon système et Georgia) pour ne rien charger.

## Pourquoi (rappel chiffré)

Le mur de la vague 3 est clic → contact : environ 95 sessions humaines sur les sites démo, 1 seul message envoyé depuis le bandeau « Ce site vous plaît ? ». Plusieurs prospects ont vu le bandeau s'ouvrir seul en bas de page et l'ont refermé (Timagine 2 fois, Barbershop63). Les visites tombent le soir (19 h 50, 20 h, 22 h 44), quand personne ne répond. Les trois intéressés ont voulu parler à un humain avant de payer. Objectif des trois briques : une tête, des informations sur Léo, et la même franchise que le mail (prix, date de retrait, comment dire non), au moment où le prospect regarde son site.

Un seul jeu de mots dans les trois maquettes, repris du modèle 30 : « 500 €, une seule fois. Pas d'abonnement. », « En ligne jusqu'au 2 novembre, après je le retire. », « Vous modifiez textes et photos vous-même. », « Un mot me suffit, même un non. ». Exemple fictif : Menuiserie Lefort, Saint-Herblain (aucun prospect réel).

## Ce que propose chaque maquette

### 1. Carte « Qui est derrière ce site » (`banner-card.html`)

Comportement conservé du bandeau actuel (`demo-host/app/components/DemoCtaBanner.vue`) : jamais fermable (réduit en pastille seulement), ouverture automatique une fois la page lue jusqu'en bas, formulaire sans coordonnées demandées (le mail connaît l'adresse), tracking `demo_cta_banner_*`, identité crème/encre littérale pour se poser sur n'importe quel template clair ou sombre.

Ce qui change : la pastille montre la photo de Léo (déjà prévu par `owner_profile_photo_url`, jamais renseigné en prod), la carte répond à « qui est derrière ce site » et dit le prix et la date, le bouton devient « Me répondre ».

- **Variante A, photo en tête.** Photo 56 px, « Léo Guillaume », « Développeur à Rennes · dibodev.fr », titre « J'ai construit ce site pour vous. », trois faits (prix, date, autonomie), champ « Une question, un oui, un non : écrivez-moi. », bouton « Me répondre », téléphone. La pastille dit « Ce site vous plaît ? / Léo Guillaume, développeur à Rennes ». C'est la variante qui répond le plus directement à « ils ont voulu parler à un humain » : la personne avant la demande.
- **Variante B, photo discrète.** Titre actuel « Ce site vous plaît ? », une phrase franche (prix, date, « même un non »), le champ, puis la signature compacte (photo 34 px, nom, ville, dibodev.fr) et le bouton. Pastille actuelle avec la photo. Changement minimal, l'offre reste le sujet.
- **Variante C, retenue le 03/10.** L'en-tête de A (photo 56 px, nom, « Développeur à Rennes · dibodev.fr ») puis le texte de B (« Ce site vous plaît ? » et la phrase prix, date, « même un non »), le champ « Votre message (optionnel) », le bouton et le téléphone. Pastille de A (la deuxième ligne nomme la personne). Le texte de A prenait trop de place.

Recommandation : A. La carte s'ouvre souvent seule en fin de page ; à ce moment-là le prospect a lu son site et la question qu'il se pose est « c'est qui, c'est combien, c'est sérieux ? ». A répond aux trois dans l'ordre. B garde la hiérarchie actuelle qui n'a produit qu'un message.

### 2. Réceptionniste Dibodev dans le bandeau (`banner-receptionist.html`)

La réceptionniste « Léa » existe déjà (assistant public `dibodev`, slug utilisé par `dibodev.fr` via `ai-assistant.js`, palette violette #7464d6, portrait `/avatars/lea.webp`, puces « Vous faites des sites web pour artisans ? »). L'idée : la brancher sur les démos actives avec une base de connaissance dédiée à l'offre site et le contexte du site regardé (nom, prix, date d'expiration, lien), pour qu'elle réponde à 22 h, prenne le contact et alerte Léo.

- **Position 1, onglet dans la carte.** Deux onglets sous l'en-tête : « Laissez-moi un mot » (asynchrone, l'expéditeur répond) et « Une question ? » (Léa, tout de suite). La conversation vit dans la carte, habillée crème/encre comme le bandeau, avec une ligne de contexte « Elle connaît ce site : Menuiserie Lefort, 500 € une fois, en ligne jusqu'au 2 novembre ». Un seul objet à l'écran, une seule identité visuelle. Coût : un habillage de chat à écrire dans le demo-host (la logique, le streaming et la capture de contact sont réutilisés via les composables `useAssistantConversation` / `useAssistantLeadForm`).
- **Position 2, panneau Léa depuis la carte.** Une ligne discrète sous le bouton « Me répondre » : « Une question maintenant ? Léa, mon assistante IA, vous répond tout de suite, même le soir. [Lui écrire] ». Le clic ouvre le panneau Léa tel qu'il tourne sur dibodev.fr (iframe `/embed/dibodev` avec le slug de la démo en paramètre), carte réduite en pastille. Zéro habillage, mais deux identités se suivent (bandeau crème puis panneau blanc/violet).

La conversation type (même dans les deux positions) : Léa se présente comme IA (« l'assistante IA de Léo, le développeur qui a construit ce site »), répond prix / abonnement / paiement / date avec les mots du mail, et quand le prospect écrit « il peut m'appeler demain ? 06 12 34 56 78 », le numéro devient une demande (c'est déjà ce que fait `chat_contact_capture.py`) et Léo est prévenu (push opérateur déjà en place pour les démos de la réceptionniste, `request_follow_up`).

Recommandation : lancer la carte seule d'abord (brique 1), mesurer deux semaines, puis ajouter Léa en position 1 si la carte ne suffit pas. Raisons : (1) la carte seule répond déjà à « qui, combien, jusqu'à quand » ; (2) Léa sur une démo site doit être nourrie et bornée (une IA qui promet un délai ou un prix faux est pire que pas d'IA) ; (3) l'effort est 3 à 4 fois celui de la carte ; (4) on ne saura pas ce qui a marché si les deux partent ensemble.

### 3. Email HTML plus joli (`email-frank.html`)

Texte du modèle 30 « Franc - prix et date (France/Belgique) » mot pour mot (lu en prod), objet « le site de {entreprise} ». Aujourd'hui ce modèle part sans signature (`signature_id` vide) et sans aucun style : police par défaut du webmail, puis le pied de désinscription.

- **Variante (a), texte + signature avec photo.** Même texte dans un conteneur 600 px, 15 px, encre #141414 ; la signature « Signature Dibodev » (portrait 88×110) en dessous ; pied inchangé.
- **Variante (b), texte + carte « votre site est ici » + signature.** Même chose, plus une carte légère sous la phrase du lien : « Votre site, déjà en ligne », nom du site, lien en texte, bouton « Voir le site » violet dibodev.fr (#6f5fe0), « 500 €, une seule fois / en ligne jusqu'au 2 novembre ». Tables et styles inline uniquement, pas d'image dans la carte.
- **Bascule signature réelle / allégée.** La signature de prod compte 5 images (portrait + 4 icônes PNG d'environ 1 Ko). La version allégée remplace les icônes par du texte : une seule image dans tout l'email, le portrait. Je recommande l'allégée pour la campagne.

Recommandation : (a) avec la signature allégée pour la prochaine vague (zéro développement, la photo et dibodev.fr entrent dans le mail), (b) en test A/B dès que la variable de la carte existe. La carte répète le lien : utile pour ceux qui ne lisent pas le texte, mesurable (clic texte vs clic bouton, Resend trace chaque URL).

## Choix à trancher

1. Carte : variante **A** (photo en tête) ou **B** (photo discrète) ?
2. Libellé du bouton : « Me répondre » (ticket), « Je suis intéressé » (actuel) ou « Répondre à Léo » ?
3. Afficher **prix et date dans la carte** pour toutes les démos actives, ou seulement quand le prospect a reçu un mail franc ? (Les démos des vagues 1-2 ont reçu des mails sans prix ; je propose : afficher partout, c'est la règle n° 1.)
4. Réceptionniste : **position 1** (onglet, cohérent, plus de travail), **position 2** (panneau existant, rapide), ou **après le lancement** (ma recommandation) ?
5. Persona sur les démos : garder **Léa** (déjà sur dibodev.fr) ou un autre prénom ; se présente comme « assistante IA de Léo ».
6. Email : **(a)** ou **(b)**, signature **réelle** (5 images) ou **allégée** (1 image) ?
7. Attacher la signature aux modèles francs **30, 31, 32, 33** (un clic chacun dans Modèles) : oui ?
8. Deux détails de copie à confirmer : le délai annoncé par Léa (« met le site sur votre adresse sous 48 h ») et la phrase « le nom de domaine est compris » ; le tiret cadratin « — » dans la 4ᵉ phrase du modèle 30.

## Décisions et avis (état au 03/10, soir)

| # | Choix | État | Avis donné |
|---|---|---|---|
| 1 | Carte | **Tranché : variante C** (photo et nom de A, texte de B) | |
| 2 | Bouton | En attente | « Me répondre » : le champ invite au oui, au non ou à une question, « Je suis intéressé » contredit le non |
| 3 | Prix et date dans la carte | En attente | Partout (règle n° 1) ; une démo jamais envoyée n'affiche pas de date |
| 4 | Réceptionniste dans le bandeau | En attente | Après le lancement, pour mesurer la carte seule ; ensuite la position 1 (un seul objet, une seule identité) |
| 5 | Persona | En attente | Léa, présentée comme l'assistante IA de l'expéditeur (la même que sur dibodev.fr) |
| 6 | Email | En attente | (a) avec la signature allégée (une seule image) ; (b) ressemble à une newsletter et double le lien |
| 7 | Signature | En attente | Oui, mais sur les modèles « Franc - … » de la bibliothèque, qui servent pour la vague 4 (prix par pays) plutôt que sur 30 à 33. Prérequis : la photo et le téléphone du profil sont vides en prod |
| 8 | Copie de Léa | En attente | « Le nom de domaine est compris » est exact ; « sous 48 h » seulement si c'est tenable à chaque vente, sinon « dans les jours qui suivent le paiement ». Le tiret du modèle 30 ne compte plus : les modèles de la bibliothèque n'en ont pas |

## Contraintes de délivrabilité vérifiées (email)

- Largeur ≤ 600 px, tables simples, aucun CSS externe, aucune police web, pas de JS ni de formulaire.
- Une seule image (signature allégée) : PNG 176×220 affiché 88×110, 44,6 Ko, `width`/`height`/`alt` présents ; pas d'image de fond, pas de vignette lourde. Signature réelle : + 4 icônes ≈ 5 Ko (acceptable, mais 5 balises `<img>`).
- Texte dominant : environ 700 caractères pour une image de 88 px.
- Liens : 7 en (a), 9 en (b), tous vers dibodev.fr / demo.dibodev.fr / Malt / LinkedIn / GitHub, pas de raccourcisseur ; le lien démo répété deux fois avec la même URL est sans effet.
- Désinscription : pied conservé tel quel (`add_unsubscribe_footer`) + en-têtes `List-Unsubscribe` / `List-Unsubscribe-Post` déjà posés par `email_sending_service.send_via_user_identity`.
- Version texte : générée par Resend si absente (c'est le cas aujourd'hui).
- Mode sombre : couleurs explicites sur fond blanc, portrait sur fond noir lisible dans les deux modes.
- Mots : pas de majuscules, pas de « gratuit / urgent », un prix, une demande.
- À confirmer par un vrai envoi test avant la campagne : score mail-tester (9/10 aujourd'hui, le point manquant vient de l'infrastructure, pas du contenu) ; rendu Outlook bureau du `border-radius` (ignoré, sans casse).

## Estimation d'effort

| Brique | Effort | Contenu |
|---|---|---|
| Carte seule (A ou B) | **1 jour** | `DemoCtaBanner.vue` (copie, bloc identité, faits, bouton), type `DemoSitePublic` (ajouter `expires_at` déjà renvoyé par l'API, et `offer_price_label`), schéma `DemoSitePublicResponse` + route publique (prix de vente du user, `PricingService`), remplir `owner_profile_photo_url` (URL dibodev.fr) et le téléphone dans le profil, 3 événements PostHog, tests. Livrable cette semaine. |
| Réceptionniste dans le bandeau | **3 à 4 jours** (position 1) / **2 jours** (position 2) | Base de connaissance « offre site » (document texte attaché à l'assistant `dibodev` ou assistant dédié `dibodev-sites`), contexte par démo injecté dans le prompt (`knowledge_builder.render_system_prompt` : nom, prix, date, lien, nom de Léo), paramètre `demo` sur `/embed/{slug}` et `hostPage`, capture de contact qui rattache la demande au prospect de la démo + push à Léo, plafond de messages par démo, désactivation des puces photo/rendez-vous, événements PostHog, QA des réponses (prix, délai, paiement, refus). Position 1 ajoute l'habillage crème/encre du chat dans la carte. |
| Email (a) | **0 jour de dev** | Attacher la signature aux modèles 30-33 ; créer la signature allégée dans Signatures (copier-coller de `email-frank.html`). Optionnel (0,5 j) : conteneur 600 px / 15 px posé par le chemin d'envoi autour du corps. |
| Email (b) | **0,5 à 1 jour** | Nouvelle variable `{carte_demo}` rendue côté API comme `{vignette_video}` (`EmailVariables.build_demo_card_html` : nom, lien, bouton, prix, date), ajoutée au modèle 30 ; test A/B par campagne déjà disponible. |

## Plan d'implémentation

### Brique 1, carte

- `demo-host/app/components/DemoCtaBanner.vue` : nouveau bloc identité (`dlh-who`), liste des faits (`dlh-facts`), bouton « Me répondre », textes ; variante par prop ou par constante selon la décision.
- `demo-host/app/types/demoSite.ts` : `expires_at: string`, `offer_price_label?: string | null`.
- `api/schemas/demo_site.py` `DemoSitePublicResponse` + `api/api/v1/routes/demo_sites.py` (route publique) : `offer_price_label` depuis `PricingService` (prix du user), format « 500 € » ; la date vient d'`expires_at`, formatée côté demo-host comme `FrenchDateFormatter.day_month` (« 2 novembre »).
- Profil de l'expéditeur : `owner_profile_photo_url` = portrait dibodev.fr (ou une copie R2), `owner_contact_phone`, `owner_company_website_url`.
- PostHog (démo trackée via `captureDemoEvent`) : propriété `banner_variant` sur `demo_cta_banner_shown` / `_open` / `_auto_open` / `_submitted` ; nouvel événement `demo_cta_banner_owner_link_click` (clic dibodev.fr) ; `demo_cta_banner_facts_shown` (prix et date affichés : oui/non) pour comparer avec les démos sans prix. Beacon API inchangé (`demo_lead`).

### Brique 2, réceptionniste

- API : document « Offre site » (500 € une fois, espace d'administration, délai, domaine, qui est Léo, comment payer, date de retrait, comment refuser) via `AiAssistantDocumentService` sur l'assistant `dibodev` ; `render_system_prompt` reçoit un bloc « SITE REGARDÉ » (nom, prix, date, lien) ; `chat_contact_capture` / `request_service` : rattacher la demande au `prospect_id` de la démo ; push à Léo avec le nom du prospect (existant côté opérateur).
- demo-host : `pages/embed/[slug].vue` accepte `?demo=<slug>` et le passe dans `hostPage` ; `DemoCtaBanner.vue` : onglets (position 1) ou ligne « Une question maintenant ? » + iframe (position 2) ; désactiver photo-devis et rendez-vous sur ce contexte.
- PostHog : `demo_receptionist_open`, `demo_receptionist_message_sent` (compteur), `demo_receptionist_contact_left`, `demo_receptionist_handoff_requested` (« je veux parler à Léo »), avec `demo_slug` et `source` (`tab` / `card`).

### Brique 3, email

- Dashboard : signature allégée créée dans Signatures, attachée aux modèles 30-33.
- API (b) : `EmailVariables.CARD = "carte_demo"` + `build_demo_card_html(demo_link, business_name, price_label, expiry_label)` ; modèle 30 édité pour l'inclure sous le premier paragraphe.
- Optionnel : conteneur 600 px / 15 px posé autour du corps dans `send_via_user_identity` (avant le pied), pour que (a) ait une taille de lecture sans toucher aux 39 modèles.
- Mesure : Resend trace chaque URL (texte vs bouton), PostHog `email_clicked` existant, A/B par campagne existant.

## Mesure prévue

Baseline vague 3 : 1 message laissé sur environ 95 sessions humaines (≈ 1 %), 0 `demo_cta_banner_field_focus`, bandeau refermé après ouverture automatique.

- Carte : taux `field_focus` / sessions humaines, `submitted` / sessions humaines (cible : passer de 1 % à 3-5 %), clics dibodev.fr, temps d'ouverture, comparaison A/B si les deux variantes partent sur deux campagnes.
- Réceptionniste : conversations ouvertes / sessions, messages par conversation, contacts laissés (numéro ou mail) / conversations, demandes « parler à Léo », comparés au formulaire seul sur la même période.
- Email : clics humains / envoyés par variante (vague 3 : 35 % de clics humains, 45 % chez les artisans), réponses par mail, et surtout contacts laissés sur la démo après clic (le mur).

## Ce que je n'ai pas pu obtenir ou que j'ai supposé

- `owner_profile_photo_url`, `owner_contact_phone`, `owner_contact_email` sont vides sur l'assistant public `dibodev` et probablement sur le profil de l'expéditeur : la maquette utilise le portrait de dibodev.fr et le 06 de la signature ; l'adresse mail n'est affichée nulle part (non trouvée dans la signature).
- Le délai « sous 48 h » et « le nom de domaine est compris » dans la conversation de Léa sont mes formulations à partir des notes (domaine OVH inclus dans les 500 €) : à valider.
- La nouvelle version de dibodev.fr est violette (#6f5fe0 / #5b4bd0, Rubik) : l'email reprend le violet pour les liens et le bouton, la police reste la pile système (une police web n'est pas fiable en email). Le bandeau reste noir et blanc (identité DevLeadHunter) : seule Léa porte le violet, et seulement en position 2.
- IBM Plex (bandeau) et Fraunces (Léa) ne sont pas chargées par les maquettes (aucune dépendance réseau) : si elles ne sont pas installées sur le poste, le rendu utilise la police système et Georgia, légèrement différent de la prod.
- Le score mail-tester n'a pas été rejoué (pas d'envoi) : grille repassée mentalement, à confirmer par un envoi test.
