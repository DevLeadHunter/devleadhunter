# Business Plan — DevLeadHunter (vente de sites web)

> **Statut** : v1 — 2026-07-15. **Périmètre** : uniquement la **vente de sites web** (le module
> actuel). Les autres livrables (cartes Apple Wallet, signatures, flyers…) et le modèle de revente
> multi-utilisateur sont **hors périmètre** de ce document tant que Léo ne les active pas.
>
> **Document VIVANT** : les chiffres ci-dessous sont des **hypothèses** à remplacer par les **vraies
> données** dès qu'elles tombent (PostHog + tracking Resend donnent open/clic/vente réels en quelques
> semaines). Mettre à jour le « Journal de révisions » à chaque itération.
>
> **Source de vérité** : ce fichier (`BUSINESS_PLAN.md`, racine du repo). Une copie vit dans le skill
> (`reference/business-plan.md`) — resynchroniser à chaque modif.

---

## 1. Le produit en une page

DevLeadHunter trouve des artisans **sans site web**, génère pour chacun **une vraie démo personnalisée
de SON site**, le démarche par cold email (A/B + relances), et le convertit en client **à 500 € une
fois, sans abonnement, site à vie**. Après paiement : mise en prod sur son domaine + remise des accès
CMS (Storyblok) pour qu'il gère tout lui-même.

**Cible** : TPE/artisans locaux FR (plombier, électricien, mécanicien… d'abord), avec une fiche
Google/PagesJaunes mais **aucun site**. **Vendeur** : Léo Guillaume (marque Dibodev).

---

## 2. Forces (ce qui doit faire vendre)

| Force | Pourquoi ça compte |
|---|---|
| **Démo perso déjà construite** | On dit « voici **VOTRE** site », pas « on fait des sites ». C'est le vrai *moat* d'accroche : quasi personne ne fait ça à froid. Effet « waouh, c'est mon entreprise ». |
| **Moteur d'automatisation** | Envoyer des démos personnalisées à **grande échelle** là où un concurrent en fait 3 à la main. C'est le *moat durable* (le pitch, lui, est copiable). |
| **Vidéo webcam + voix** *(à venir)* | Visage + voix de Léo = confiance, on ne parle pas à un inconnu. Vignette cliquable dans le mail. |
| **Éditeur CMS (Storyblok)** | Client **autonome** : il modifie contenu/photos/horaires sans développeur. Argument « site à vie, vous gérez tout ». |
| **Templates de qualité, par métier** | Ne ressemblent **pas** à une landing générée par IA → crédibilité. |
| **Offre 500 € one-shot, sans abo** | « Oui » facile face aux agences (retainer) et aux site-builders (abo mensuel). Prix bas, décision rapide. |
| **Argument visibilité Google/Maps** | La fiche Google est **mieux mise en avant** avec un site rattaché — bénéfice concret que l'artisan comprend. |
| **Marge quasi totale** | Coût marginal par vente < 15 € (voir §7). |
| **Scoring comportemental + relance perso** | Détecte les prospects chauds (visite démo, engagement) → relance au **bon moment**. |
| **Signal de confiance email** | Apple Branded Mail (logo + « Dibodev » dans Apple Mail), **gratuit**, en cours. |

---

## 3. Faiblesses & risques (à ne pas se cacher)

| Faiblesse / risque | Impact | Atténuation |
|---|---|---|
| **Habitudes email de la cible** | Les artisans sont **sur le terrain**, pas devant leur boîte mail → ouverture potentiellement **plus basse** que la moyenne B2B. **C'est le risque n°1 du funnel.** | Objet local (`{ville} - {metier}`), envoi tôt le matin / fin de journée, relances. À terme : tester SMS/appel en complément. |
| **Délivrabilité (domaine neuf)** | Cold email depuis un domaine récent = risque spam, réputation à chauffer. | 20/j = volume prudent, DMARC `p=quarantine` OK, désinscription + headers RFC 8058, warm-up progressif. |
| **Plafond de volume** | À 20 J1/jour + throttle 1/20 min, l'outil est en **phase de test**, pas de scale. Le CA est **mécaniquement plafonné**. | Le test valide le funnel ; scaler = +domaines/inboxes d'envoi (voir §10). |
| **« Trop beau pour être vrai »** | Un site déjà construit envoyé gratuitement peut sonner **arnaque**. | Vidéo (visage/voix), Apple Branded Mail, ton humain, démo réelle vérifiable. |
| **Zéro preuve sociale au départ** | Pas de témoignages/études de cas → **les 1ères ventes sont les plus dures**. | Capitaliser chaque 1ʳᵉ vente en cas client / avis. |
| **Bug `{prenom}` actuel** | Les mails disent « Bonjour **Plomberie**, » (1er mot du nom d'entreprise) → **contre-productif** aujourd'hui. | Chantier #4 roadmap (cascade nom du décisionnaire). **À faire avant de pousser le volume.** |
| **Étapes post-vente manuelles** | Achat domaine + deploy + handover = **temps** par vente (pas 100 % auto). | ~1–3 h/vente aujourd'hui ; à automatiser progressivement. |
| **Pas de récurrent** | 500 € one-shot → **LTV plafonnée**, pas de revenu qui se cumule. | Futurs upsells (maintenance/SEO en option), autres modules (Wallet…). |
| **Dépendances tierces** | Storyblok (Starter gratuit = 1 space/compte), Resend, Vercel, Groq. | Handover Storyblok = space chez le client (voir roadmap #5). |
| **RGPD / légalité** | Cold email B2B + scraping = licite en FR sous conditions (pertinence pro, opt-out) mais à tenir **propre**. | Désinscription obligatoire déjà en place ; ne pas dériver. |
| **Cadence artisanale = temps de Léo** | Un seul homme : prospection supervisée + ventes + delivery. | Automatiser le tunnel, prioriser les leads chauds. |

---

## 4. Hypothèses de démarrage (cadence Léo)

- **Fenêtre d'envoi** : lundi → vendredi, **7 h–18 h**.
- **Volume** : **20 nouveaux prospects (J1) par jour** = 5 entreprises × 4 métiers, avec **4 templates**
  différentes (une par métier / variante A-B). Les **relances (J+5, J+10) s'ajoutent par-dessus**.
- **Débit** : throttle **1 mail / 20 min** → **plafond physique ≈ 33 mails/jour** (11 h × 3/h).

> ⚠️ **Contrainte opérationnelle à connaître** : 20 J1/jour laisse **~13 créneaux/jour pour les relances**.
> Dès que les relances affluent (semaine 3+), on **sature le plafond de ~33/j** → soit on retombe à
> **~15 J1/jour** en régime établi, soit on **élargit la fenêtre** (6 h–20 h) ou on **accélère le throttle**
> (1/15 min). **Décision produit à trancher.** Les projections ci-dessous en tiennent compte (régime
> établi ≈ 15–18 J1/j).

**Traduction en prospects neufs contactés :**

| Période | Prospects J1 neufs (nominal 20/j) | Régime réaliste (throttle) |
|---|---|---|
| Semaine 1–2 (pas encore de relances) | ~100/sem | ~100/sem |
| Régime établi (relances actives) | ~100/sem | **~75–90/sem** (~15–18 J1/j) |
| Par mois (≈ 21,7 jours ouvrés) | ~430/mois | **~330–390/mois** |

---

## 5. Le modèle de funnel (les taux)

> Fourchettes pour du **cold email très personnalisé** (démo perso = hook fort) vers des **TPE FR**,
> mesurées **au niveau séquence** (J1 + relances), pas d'un seul mail. **À remplacer par tes vrais chiffres.**

| Étape | Pessimiste | **Réaliste** | Optimiste | Notes |
|---|---|---|---|---|
| **Délivré en boîte** (du envoyé) | 80 % | **90 %** | 95 % | Dépend de l'auth + réputation du domaine neuf. |
| **Taux d'ouverture** (du délivré) | 25 % | **40 %** | 55 % | **Bruité** (Apple MPP gonfle, blocage d'images déflate). Artisans peu devant leur mail = risque bas. |
| **Clic démo** (du prospect, séquence) | 8 % | **15 %** | 25 % | Le hook « votre site » tire ce taux **au-dessus** des standards cold (2–5 %). |
| **Réponse positive / intérêt** (du prospect) | 2 % | **5 %** | 9 % | Séquence complète (relances comprises). |
| **Vente** (du prospect contacté) | 0,5 % | **1,5 %** | 3 % | 500 € one-shot, cycle court possible. Cohérent : ~5 % d'intérêt × ~30 % de closing ≈ 1,5 %. |

**Lecture** : pour **100 prospects** menés dans la séquence (réaliste) → ~40 ouvrent, ~15 cliquent la
démo, ~5 répondent avec intérêt, **~1,5 achètent** → **~750 € par tranche de 100 prospects**.

---

## 6. Projections (semaine / mois / 3 mois)

> Sur la base **régime réaliste ≈ 350 prospects neufs/mois** (throttle pris en compte) et du taux de vente
> ci-dessus. **Rampe assumée** : le mois 1 est un **rodage** (délivrabilité qui chauffe, copy pas encore
> optimisée, 0 preuve sociale, bug `{prenom}` si non corrigé) → il **sous-performe** structurellement.
> La **1ʳᵉ vente arrive réalistement en semaine 2–4**, pas en semaine 1.

**Par tranche de volume (régime établi, hors rampe) :**

| Horizon | Prospects neufs | Ventes (pess / **réaliste** / opti) | CA réaliste (× 500 €) |
|---|---|---|---|
| **1 semaine** | ~80 | 0,4 / **1,2** / 2,4 | **~600 €** |
| **1 mois** | ~350 | ~2 / **~5** / ~10 | **~2 500 €** |

**Cumulé sur 3 mois, avec rampe (le plus honnête) :**

| Scénario | Mois 1 (rodage) | Mois 2 | Mois 3 | **Total 3 mois** | **CA 3 mois** |
|---|---|---|---|---|---|
| **Pessimiste** | 1 | 2 | 2 | **~5 ventes** | **~2 500 €** |
| **Réaliste** | 2–3 | 5 | 6 | **~13 ventes** | **~6 500 €** |
| **Optimiste** | 5 | 11 | 13 | **~29 ventes** | **~14 500 €** |

> 🎯 **À retenir** : à cette cadence de **test**, on parle d'un **revenu d'appoint (≈ 1 000–3 000 €/mois)**
> qui **valide le funnel**, pas d'un revenu de scale. Le vrai potentiel se débloque quand (a) le funnel
> est prouvé et (b) on **augmente le volume d'envoi** (§10). Le but des 3 premiers mois : **prouver les
> taux réels** et **encaisser les 1ères ventes** pour la preuve sociale.

---

## 7. Économie unitaire & rendement

| Poste | Montant | Note |
|---|---|---|
| **Prix de vente** | **500 €** | One-shot, sans abo. |
| Domaine client | ~12 €/an | Souvent **payé par le client** ; sinon coût quasi nul. |
| Hébergement (Vercel) | ~0 € | Hobby/projet global. |
| CMS (Storyblok) | ~0 € | Plan **Starter gratuit** chez le client (1 space). |
| Envoi (Resend) | ~négligeable | ~0,001 €/mail × quelques mails. |
| Scraping + LLM (Groq) | ~négligeable | IP résidentielle + modèles bon marché. |
| **Coût variable / vente** | **< 15 €** | |
| **Marge brute / vente** | **~485 € (~97 %)** | Produit **très haute marge**. |
| **Temps / vente** | **~1–3 h** | Génération démo **automatisée** ; post-vente **manuel** (domaine + deploy + handover + échanges). |

**Rendement effectif** (réaliste, ~5 ventes/mois) : **~2 425 € de marge/mois** pour **~10–15 h** de
travail post-vente + supervision → **excellent €/h**, mais **plafonné par le volume (20/j) et le temps**.

- **Coûts fixes** : quasi nuls (quelques € d'outils/mois) → **break-even ≈ immédiat** : **1 vente couvre
  des mois** de fonctionnement.
- **CAC monétaire** : ~nul. Le vrai « coût d'acquisition » = **temps + délivrabilité**, pas de l'argent.
- **LTV** : **500 € one-shot** aujourd'hui (pas de récurrent). **Leviers LTV futurs** : option
  maintenance/SEO récurrente, refonte, autres modules (Apple Wallet…), parrainage.

---

## 8. Leviers pour améliorer chaque étape du funnel

| Étape | Levier prioritaire |
|---|---|
| **Délivrabilité** | Warm-up du domaine, volume progressif, auth carrée (DMARC/DKIM Resend), listes propres, désinscription respectée. |
| **Ouverture** | Objet court/local, **corriger `{prenom}`** (roadmap #4), horaire d'envoi adapté aux artisans, Apple Branded Mail (confiance visuelle). |
| **Clic démo** | La **démo perso** est déjà le levier ; ajouter la **vignette/vidéo** (roadmap #6) juste à côté du lien. |
| **Réponse / intérêt** | 1 argument = 1 mail, **variantes A/B** (fiche Google/Maps, crédibilité, autonomie… roadmap #8), CTA faible et humain. |
| **Vente** | Relance perso au **signal chaud** (scoring), CTA « testez votre espace admin » en 2ᵉ temps, lien magique, offre claire 500 € à vie. |
| **Delivery** | Automatiser le post-vente (domaine + deploy + handover Storyblok) pour baisser le temps/vente. |

---

## 9. Ce qu'il faut MESURER (remplacer les hypothèses par du réel)

Le funnel est **déjà instrumenté** (PostHog sur la démo + tracking Resend + `email_log`). À suivre
chaque semaine et à reporter dans le §10 :

1. **Délivré / bounce / spam** (Resend) — santé de la délivrabilité.
2. **Taux d'ouverture réel** (Resend) — en gardant en tête le bruit (Apple MPP).
3. **Clic sur `{lien_demo}`** — **la métrique clé** (intérêt réel, moins bruitée que l'ouverture).
4. **Visite démo + comportement** (PostHog : scroll, temps, sections, `demo_*`).
5. **Réponses positives** (manuel : Resend ne tracke pas les réponses — cf. mémoire `resend-tracking-limits`).
6. **Ventes** (`Order` payés) et **délai moyen contact → vente**.
7. **Taux par métier / par template** — pour identifier le **meilleur segment** et le **meilleur argument**.

> Objectif : après 3–4 semaines, **ce document ne contient plus d'hypothèses** sur open/clic — seulement
> tes vrais chiffres. Seuls vente et projections long terme restent estimés.

---

## 10. Au-delà du test : pistes de scale (hors périmètre v1, pour mémoire)

- **Augmenter le volume d'envoi** : plusieurs domaines/inboxes d'envoi + rotation → sortir du plafond
  ~33/j sans cramer la réputation. **C'est le principal multiplicateur de CA.**
- **Automatiser le post-vente** (domaine + deploy + handover) → baisser le temps/vente, encaisser plus.
- **Ajouter du récurrent** (maintenance/SEO en option) → lever le plafond de LTV.
- **Élargir les métiers/régions** → plus de prospects adressables.
- **Preuve sociale** → chaque vente = un cas client réutilisé dans le copy (lève le taux de conversion).

---

## 11. Journal de révisions

| Date | Version | Changement |
|---|---|---|
| 2026-07-15 | v1 | Création. Hypothèses de funnel, cadence 20 J1/j (relances par-dessus), projections S/M/3M, éco unitaire, leviers. **Aucun chiffre réel encore** — tout est estimation à valider. |

> **Prochaine mise à jour attendue** : après la 1ʳᵉ semaine d'envois réels → remplacer open/clic
> estimés par les vrais (PostHog + Resend), et corriger les projections.
