# Cycle de vie d'une campagne email

De la mise en file à la relance, en passant par le test A/B et la fenêtre d'envoi.
La logique vit dans `api/services/campaign_queue_service.py`, tournée en boucle par
`api/services/email_queue_worker.py`.

## Mise en file au lancement

```mermaid
flowchart TD
    START(["Lancement de la campagne"]) --> LOAD["Charger les templates<br/>variante A et variante B"]
    LOAD --> SPLIT{"Test A/B activé ?"}
    SPLIT -->|non| ALL_A["Tous les prospects<br/>reçoivent la variante A"]
    SPLIT -->|oui| AB["Répartition 50/50<br/>index pair → A, impair → B"]

    ALL_A --> GUARD
    AB --> GUARD

    GUARD{"La template utilise<br/>un lien démo ou vidéo ?"}
    GUARD -->|non| SLOT
    GUARD -->|"oui, et le prospect<br/>a bien une démo active"| SLOT
    GUARD -->|"oui, mais aucune<br/>démo active"| SKIP["Écarté : skipped_no_demo<br/>rendu à l'opérateur"]

    SLOT["Calcul du créneau d'envoi"] --> POLICY{"Une SendPolicy<br/>existe pour cet utilisateur ?"}
    POLICY -->|oui| WINDOW["Créneaux dans la fenêtre<br/>jours + heures autorisés,<br/>plafond quotidien réparti"]
    POLICY -->|non| DELAY["Un envoi tous les<br/>send_delay_minutes"]

    WINDOW --> QUEUE
    DELAY --> QUEUE
    QUEUE[("EmailQueue<br/>items J1 en pending")]

    NOTE["Relancer une campagne est sûr :<br/>les créneaux s'ajoutent après le dernier pending,<br/>et un prospect déjà en file n'est jamais redoublé."]
    QUEUE -.- NOTE
```

## Dépilement par le worker

```mermaid
sequenceDiagram
    autonumber
    participant W as email_queue_worker
    participant Q as EmailQueue
    participant R as Resend
    participant P as Prospect
    participant H as Webhooks

    loop À chaque tick
        W->>Q: Prendre le prochain item dû<br/>(pending, échéance passée, campagne active)
        alt Rien à envoyer
            Q-->>W: aucun item
        else Un item est dû
            Q-->>W: item
            W->>Q: Passer en sending<br/>(verrou contre le double envoi)
            W->>W: Résoudre les variables<br/>lien démo, lien vidéo, signature
            W->>R: Envoyer l'email
            alt Envoi accepté
                R-->>W: accepté
                W->>Q: Passer en sent + créer l'EmailLog
                W->>Q: Programmer les relances<br/>chaque étape décalée de delay_days
                R->>P: Livraison de l'email
                P-->>H: delivered, opened, clicked
                H->>W: Mise à jour de l'EmailLog<br/>et du score de lead
            else Envoi refusé
                R-->>W: erreur
                W->>Q: Passer en failed
            end
        end
    end
```

## Séquence vue côté prospect

```mermaid
flowchart LR
    J1["J1 · Email initial<br/>variante A ou B"] --> R1["Relance 1<br/>+ delay_days"]
    R1 --> R2["Relance 2<br/>+ delay_days"]
    R2 --> RN["Relance n<br/>selon campaign_follow_ups"]

    J1 -.->|"échec d'envoi"| STOP(["Aucune relance :<br/>elles ne sont créées<br/>qu'après un J1 réussi"])
    RN --> END(["Fin de séquence"])
```

Chaque relance hérite de la variante A/B de son J1, ce qui garde le test cohérent
sur toute la séquence. Les étapes viennent de `campaign_follow_ups` ; un repli sur
les anciens champs `follow_up_template_id` / `follow_up_delay_days` couvre les
campagnes créées avant la relance multi-étapes.
