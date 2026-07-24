# Pipeline métier — du prospect à la vente

Chaîne complète : trouver un artisan sans site, l'enrichir, lui générer un site de
démonstration, le démarcher, encaisser, livrer.

Les étapes grisées sont **automatisables en séquence** par l'orchestrateur
d'acquisition (`api/services/acquisition_orchestrator.py`). En mode `semi_auto`
la séquence s'arrête avant le démarchage pour validation humaine ; en `full_auto`
elle enchaîne jusqu'à la campagne.

```mermaid
flowchart TD
    subgraph SOURCING["1 · Sourcing"]
        S1["Google Maps"]
        S2["Pages Jaunes"]
        S3["Yelp"]
        S4["OpenStreetMap / Overpass"]
        S5["BrightData<br/>(Web Unlocker + SERP)"]
        SCRAPE{{"Scraper<br/>failover entre sources"}}
        S1 --> SCRAPE
        S2 --> SCRAPE
        S3 --> SCRAPE
        S4 --> SCRAPE
        S5 --> SCRAPE
    end

    SCRAPE --> P[("Prospect<br/>artisan sans site web")]

    subgraph ENRICH["2 · Enrichissement"]
        E1["Décideur<br/>nom, rôle, email"]
        E2["Horaires, réseaux sociaux,<br/>photos, avis"]
        E3["Audit Lighthouse<br/>si un site existe déjà"]
        E4["Score de lead<br/>(règles + IA Groq)"]
    end

    P --> E1 --> E2 --> E3 --> E4

    subgraph GEN["3 · Génération du livrable"]
        G1["Choix de la template<br/>selon le métier"]
        G2["Contenu éditorial<br/>contrat SiteContent"]
        G3["Space Storyblok<br/>+ bloks pré-remplis"]
        G4["Déploiement demo-host<br/>Vercel"]
        G5["Clip de prospection<br/>Playwright + ffmpeg"]
    end

    E4 --> G1 --> G2 --> G3 --> G4
    G4 --> DEMO["Démo en ligne 14 jours<br/>demo.dibodev.fr/slug"]
    G4 --> G5 --> VIDEO["Page vidéo tracée<br/>/v/slug"]

    subgraph OUTREACH["4 · Démarchage"]
        C1["Campagne cold email<br/>A/B + relances"]
        C2["File d'attente throttlée<br/>selon la SendPolicy"]
        C3["Envoi via Resend"]
    end

    DEMO --> C1
    VIDEO --> C1
    C1 --> C2 --> C3 --> PROSPECT_MAIL(["Le prospect reçoit l'email"])

    subgraph SIGNAL["5 · Signaux de retour"]
        T1["Webhooks Resend<br/>delivered, opened, clicked"]
        T2["PostHog<br/>visite démo, lecture vidéo"]
    end

    PROSPECT_MAIL --> T1
    PROSPECT_MAIL --> T2
    T1 --> HOT["Lead chaud<br/>score démo + email"]
    T2 --> HOT

    subgraph SALE["6 · Vente et livraison"]
        O1["Commande créée"]
        O2["Lien de paiement Stripe<br/>envoyé au client"]
        O3["Webhook Stripe : payé"]
        O4["Déploiement sur le domaine client"]
        O5["Invitation Storyblok<br/>le client édite son site"]
        O6["Vérification de livraison"]
    end

    HOT --> O1 --> O2 --> O3 --> O4 --> O5 --> O6
    O6 --> DONE(["Site livré<br/>servi en permanence"])

```

## Ce que la machine fait seule, et ce qui reste humain

```mermaid
flowchart LR
    F["found"] --> EI["enriching"] --> E["enriched"]
    E --> GI["generating"] --> G["generated"]
    G -->|"semi_auto :<br/>pause pour validation"| REVIEW{{"Validation humaine<br/>des sites générés"}}
    G -->|"full_auto :<br/>sans pause"| C["campaigning"]
    REVIEW --> C
    E -.->|"pas assez de signal"| SK["skipped"]
    EI -.->|"erreur après retries"| FA["failed"]
    GI -.->|"erreur après retries"| FA
```

`campaigning`, `skipped` et `failed` sont terminaux : l'orchestrateur n'y revient plus.
