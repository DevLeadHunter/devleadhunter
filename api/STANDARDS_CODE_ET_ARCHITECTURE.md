# Standards de code & Architecture — DevLeadHunter API

> Source de vérité pour `api/` — backend FastAPI (scraping, campagnes, Storyblok, Stripe, organisations).
> Aligné sur le niveau PrePeers B2B : typage strict, classes de service, docstrings utiles, structure claire.

## Sommaire

- [Stack](#stack)
- [Architecture](#architecture)
- [Couches & responsabilités](#couches--responsabilités)
- [Classes & services](#classes--services)
- [Modèles & schémas](#modèles--schémas)
- [Routes FastAPI](#routes-fastapi)
- [Commentaires & docstrings](#commentaires--docstrings)
- [Nommage](#nommage)
- [Tests](#tests)
- [Sécurité & multi-tenant](#sécurité--multi-tenant)
- [Règles hard](#règles-hard)

---

## Stack

| Package    | Version |
| ---------- | ------- |
| Python     | 3.11+   |
| FastAPI    | 0.1xx   |
| Pydantic   | v2      |
| SQLAlchemy | 2.x     |
| MySQL      | 8.x     |

---

## Architecture

```
api/
├── api/v1/
│   ├── router.py
│   └── routes/           # Un fichier par ressource HTTP
├── core/
│   ├── config.py         # Settings pydantic-settings
│   └── database.py
├── enums/                # StrEnum / Enum métier
├── models/               # SQLAlchemy ORM
├── schemas/              # Pydantic request/response
├── services/             # Logique métier — classes
│   ├── templates/        # Registre + modules par template_id
│   └── decision_maker/   # Sous-package cohérent
├── scrappers/            # Scraping nodriver / HTTP
├── migrations/           # Scripts manuels run_migrations.py
├── seeders/
├── tests/
├── main.py
└── STANDARDS_CODE_ET_ARCHITECTURE.md
```

---

## Couches & responsabilités

| Couche | Rôle | Interdit |
| ------ | ---- | -------- |
| `routes/` | HTTP : validation entrée, auth, appel service, réponse | Logique métier lourde |
| `schemas/` | Contrats Pydantic in/out | Requêtes SQL |
| `models/` | Tables SQLAlchemy | Logique métier |
| `services/` | Orchestration, règles métier, appels externes | Dépendance à `Request` FastAPI |
| `scrappers/` | Extraction données externes | Persistance directe sans service |
| `enums/` | Constantes typées partagées | Logique |

Flux standard : **Route → Service (classe) → Model/DB + intégrations**.

---

## Classes & services

Préférer des **classes** pour la logique métier regroupée. Deux patterns acceptés :

### 1. Classe instanciée + singleton module

```python
class ProspectService:
    """Prospect CRUD and search operations scoped per user."""

    def list_for_user(self, db: Session, user_id: int, …) -> list[Prospect]:
        …

prospect_service = ProspectService()
```

Usage dans les routes : `prospect_service.list_for_user(db, current_user.id, …)`.

### 2. Classe à méthodes statiques (helpers purs)

```python
class ValidationService:
    """Static validators for prospect contact fields."""

    @staticmethod
    def is_valid_website(url: str | None) -> bool:
        …
```

Règles :

- Une classe par domaine (`CampaignQueueService`, `StoryblokService`, `LeadScoring`…).
- Ne pas éparpiller des fonctions module-level quand elles forment un ensemble.
- Les méthodes async quand I/O (HTTP, DB async si un jour migration).
- **Pas de logique métier dans les routes** au-delà de l'assemblage.
- Un fichier qui ne contient **qu'une seule** fonction n'a pas besoin de classe.

### Les deux seules exceptions au « tout en classe »

**1. Dépendances FastAPI.** `Depends()` inspecte un callable simple ; les gardes d'auth restent donc des fonctions module-level qui **délèguent** à la classe :

```python
def require_admin(current_user: User = Depends(get_current_active_user)) -> User: ...
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    return AuthService.resolve_user_from_token(token, db)
```

**2. Workers de fond.** `asyncio.create_task()` reçoit la méthode du singleton, pas une fonction libre : `asyncio.create_task(email_queue_worker.run_forever())`.

### Singleton de module

Une classe porteuse d'état (client HTTP, cache, connexion) expose un singleton en bas de fichier — c'est ce que les appelants importent :

```python
r2_storage = R2StorageService()          # services/r2_storage_service.py
email_queue_worker = EmailQueueWorker()  # services/email_queue_worker.py
```

Une classe **sans état** (`EmailVariables`, `AuthService`, `EnrichmentContentMapper`) n'a pas de singleton : on appelle directement `EmailVariables.build_for_prospect(...)`.

---

## Modèles & schémas

### SQLAlchemy (`models/`)

- Un fichier par entité (`prospect.py`, `campaign.py`…).
- Relations explicites ; `user_id` sur toutes les ressources scopées.
- Enums Python dans `enums/`, référencés par les colonnes.

### Pydantic (`schemas/`)

- Pydantic v2 : `model_config = ConfigDict(from_attributes=True)` pour lire l'ORM.
- Schémas séparés : `Create`, `Update`, `Response` quand les champs divergent.
- **Pas de `dict` non typé** — modèles explicites.

```python
class ProspectResponse(BaseModel):
    """Public prospect payload returned to the dashboard."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str | None = None
```

---

## Routes FastAPI

```python
@router.get("/{prospect_id}", response_model=ProspectResponse)
async def get_prospect(
    prospect_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProspectResponse:
    return prospect_service.get_for_user(db, current_user.id, prospect_id)
```

- Dépendances : `get_db`, `get_current_user`, guards org/reservation.
- `response_model` explicite.
- Erreurs métier : `HTTPException` avec code adapté — ou exceptions custom centralisées si le pattern existe.
- Préfixe versionné : `/api/v1/…`

---

## Commentaires & docstrings

- Docstrings **en anglais** sur chaque **classe** et chaque **méthode publique**.
- Format : une ligne de résumé + `Args:` / `Returns:` / `Raises:` si utile.
- **Jamais de tags JSDoc** (`@param`, `@returns`, `@throws`) : c'est la syntaxe TypeScript, pas Python.
- **Pas de docstring qui paraphrase** le nom de la méthode.
- **Pas de commentaire** sur chaque ligne de logique évidente.
- **Pas de bandeau de section** (`# ---- Helpers ----`) : si un fichier en a besoin, il mérite d'être découpé.
- Les `#` inline sont réservés aux contraintes non évidentes (workaround, piège prod).

```python
def resolve_demo_slug(demo_site: DemoSite | None, email_log: EmailLog | None) -> str | None:
    """
    Resolve the canonical PostHog distinct_id (demo slug) from a site or email log.

    Returns None when neither source carries a slug.
    """
```

---

## Nommage

- Fichiers : `snake_case.py`
- Classes : `PascalCase` + suffixe rôle (`Service`, `Scraper`, `Resolver`)
- Fonctions / méthodes : `snake_case` verbe + objet (`create_demo_site`, `assert_prospect_actionable`)
- Booléens : `is_`, `has_`, `can_` + sujet explicite
- Éviter : `data`, `item`, `process`, `handle` seuls

---

## Tests

- `pytest` dans `api/tests/`
- Nommage : `test_<module>_<behavior>.py` ou fonctions `test_…`
- Tester la logique métier des services et helpers — pas les routes seules sauf intégration ciblée.
- Lancer : `cd api && python -m pytest`

---

## Sécurité & multi-tenant

- **Toutes** les ressources utilisateur sont scopées par `user_id` (ou `organization_id` pour les prospects partagés).
- Ne jamais écrire de requête qui fuit les données d'un autre user.
- Secrets : `encryption_service` + variables d'environnement — jamais en dur.
- Routes admin : guard `UserRole.ADMIN` explicite.

---

## Règles hard

| Règle | Statut |
| ----- | ------ |
| Requête sans scope `user_id` sur ressource privée | ❌ INTERDIT |
| Logique métier lourde dans une route | ❌ INTERDIT |
| `dict` / `Any` non justifié dans les schémas | ❌ INTERDIT |
| Secrets en dur dans le code | ❌ INTERDIT |
| Fonctions éparses pour un domaine qui mérite une classe | 🟠 À refactorer |
| Tags JSDoc (`@param`) dans une docstring Python | ❌ INTERDIT |
| Docstring en français | ❌ INTERDIT |
| Docstring sur classes et méthodes publiques | ✅ REQUIS |
| Pydantic v2 pour les contrats API | ✅ REQUIS |
| Enums dans `enums/` | ✅ REQUIS |
| Services testables sans HTTP | ✅ REQUIS |
