# Nouvelles Fonctionnalités - Gestion des Prospects

Ce document décrit les nouvelles fonctionnalités implémentées pour améliorer la gestion des prospects dans l'application.

## 📋 Fonctionnalités Implémentées

### 1. 💾 Sauvegarde des Prospects en Base de Données

**Problème résolu:** Les prospects n'étaient pas sauvegardés et disparaissaient après chaque recherche.

**Solution:**
- Création d'un modèle SQLAlchemy `ProspectDB` pour persister les prospects
- Tous les prospects trouvés sont automatiquement sauvegardés dans la base de données
- Chaque prospect est lié à l'utilisateur qui l'a trouvé

**Fichiers modifiés:**
- `server/models/prospect_db.py` - Nouveau modèle de base de données
- `server/services/prospect_service.py` - Service mis à jour pour utiliser la DB
- `server/core/database.py` - Ajout du modèle ProspectDB à l'initialisation

### 2. 🔍 Page "Mes Prospects"

**Nouvelle page:** `/dashboard/my-prospects`

**Fonctionnalités:**
- Affichage de tous les prospects sauvegardés par l'utilisateur
- Statistiques en temps réel (total, avec email, avec site web, avec téléphone)
- Filtres de recherche (nom, ville, email, source, catégorie)
- Pagination des résultats (50 prospects par page)
- Actions: Voir, Supprimer, Ajouter à une campagne

**Fichiers créés:**
- `client/pages/dashboard/my-prospects.vue`

### 3. 🚫 Skip des Prospects Déjà Enregistrés

**Problème résolu:** Les doublons s'accumulaient lors de recherches répétées.

**Solution:**
- Option "Ignorer les prospects déjà enregistrés" activée par défaut
- Vérification basée sur nom + ville + user_id
- Compteur des doublons ignorés affiché dans les résultats

**Fichiers modifiés:**
- `server/services/prospect_service.py` - Méthode `check_duplicate()`
- `server/services/scraping_job_service.py` - Intégration de la vérification

### 4. ⚡ Recherche Asynchrone avec Progression en Temps Réel

**Problème résolu:** Le scraping était long et bloquant, l'utilisateur devait attendre sans feedback.

**Solution:**
- Système de jobs asynchrones pour le scraping
- Affichage de la progression en temps réel (pourcentage, prospect en cours)
- Estimation du temps restant
- Possibilité de quitter la page et revenir plus tard
- Polling automatique toutes les 2 secondes pour la mise à jour

**Architecture:**
```
Frontend (search-prospects.vue)
    ↓ Crée un job
API (/api/v1/scraping-jobs)
    ↓ Lance le job en arrière-plan
ScrapingJobService
    ↓ Exécute le scraping
    ↓ Met à jour la progression
    ↓ Sauvegarde les prospects
Frontend (polling)
    ↓ Récupère le statut
    ↓ Affiche la progression
```

**Fichiers créés:**
- `server/models/scraping_job.py` - Modèles pour les jobs
- `server/services/scraping_job_service.py` - Service de gestion des jobs
- `server/api/v1/routes/scraping_jobs.py` - Routes API pour les jobs
- `client/pages/dashboard/search-prospects.vue` - Page de recherche avec suivi

## 🚀 Utilisation

### Migration de la Base de Données

Avant d'utiliser les nouvelles fonctionnalités, exécutez la migration :

```bash
cd server
python migrations/add_prospects_table.py
```

### Utilisation Frontend

1. **Rechercher des Prospects:**
   - Aller sur `/dashboard/search-prospects`
   - Remplir le formulaire (catégorie, ville, nombre max, source)
   - Cocher "Ignorer les prospects déjà enregistrés" (recommandé)
   - Cliquer sur "Lancer la recherche"
   - Suivre la progression en temps réel
   - Vous pouvez quitter la page et revenir plus tard

2. **Voir Mes Prospects:**
   - Aller sur `/dashboard/my-prospects`
   - Utiliser les filtres pour trouver des prospects spécifiques
   - Cliquer sur un prospect pour voir les détails
   - Supprimer ou ajouter à une campagne

### API Endpoints

#### Jobs de Scraping

**POST** `/api/v1/scraping-jobs`
Crée un nouveau job de scraping

```json
{
  "category": "restaurant",
  "city": "Paris",
  "max_results": 50,
  "source": "google",
  "skip_duplicates": true
}
```

**GET** `/api/v1/scraping-jobs/{job_id}`
Récupère le statut d'un job

Response:
```json
{
  "id": "job_abc123",
  "status": "running",
  "progress": {
    "current": 15,
    "total": 50,
    "percentage": 30.0,
    "current_prospect": "Le Bon Restaurant",
    "estimated_time_remaining": 120
  },
  "results": [1, 2, 3],
  "skipped_duplicates": 2
}
```

**GET** `/api/v1/scraping-jobs`
Liste tous les jobs de l'utilisateur

**DELETE** `/api/v1/scraping-jobs/{job_id}`
Supprime un job (annule si en cours)

#### Prospects

**GET** `/api/v1/prospects`
Liste tous les prospects sauvegardés de l'utilisateur

**GET** `/api/v1/prospects/{id}`
Récupère un prospect par ID

**DELETE** `/api/v1/prospects/{id}`
Supprime un prospect

## 📊 Améliorations UX

1. **Feedback Visuel:**
   - Barre de progression avec pourcentage
   - Affichage du prospect en cours de traitement
   - Estimation du temps restant
   - Statistiques en temps réel

2. **Flexibilité:**
   - L'utilisateur peut quitter la page pendant le scraping
   - Les jobs continuent en arrière-plan
   - Historique des recherches récentes
   - Possibilité de revenir à un job en cours

3. **Performance:**
   - Scraping asynchrone (non-bloquant)
   - Polling intelligent (toutes les 2 secondes)
   - Pagination pour grandes listes
   - Filtres côté client pour recherche rapide

## 🔧 Configuration

### Variables d'Environnement

Aucune nouvelle variable d'environnement n'est requise. Les fonctionnalités utilisent la base de données existante.

### Nettoyage

Les jobs sont stockés en mémoire et peuvent être nettoyés avec:

```python
from services.scraping_job_service import scraping_job_service

# Nettoyer les jobs de plus de 24h
scraping_job_service.cleanup_old_jobs(max_age_hours=24)
```

## 📝 Notes Techniques

### Gestion des Doublons

La détection des doublons est basée sur:
- Nom du prospect (insensible à la casse)
- Ville (insensible à la casse)
- ID de l'utilisateur

### Sécurité

- Tous les endpoints nécessitent une authentification
- Les utilisateurs ne peuvent voir que leurs propres prospects
- Les jobs sont isolés par utilisateur

### Limitations

- Les jobs sont stockés en mémoire (redémarrage = perte des jobs en cours)
- Pas de limite sur le nombre de prospects par utilisateur
- Pas de nettoyage automatique des vieux jobs (à implémenter)

## 🐛 Dépannage

### La migration échoue

```bash
# Vérifier que la base de données est accessible
cd server
python -c "from core.database import engine; print(engine)"

# Réessayer la migration
python migrations/add_prospects_table.py
```

### Les jobs ne se mettent pas à jour

- Vérifier que le serveur backend est en cours d'exécution
- Vérifier les logs du serveur pour les erreurs
- Le polling s'arrête automatiquement quand le job est terminé

### Les prospects n'apparaissent pas

- Vérifier que le scraping s'est terminé avec succès
- Actualiser la page `/dashboard/my-prospects`
- Vérifier les crédits de l'utilisateur

## 🎯 Prochaines Étapes

Améliorations possibles:
- Persistance des jobs en base de données
- WebSocket pour mise à jour en temps réel (au lieu du polling)
- Export CSV des prospects
- Fusion manuelle de prospects
- Tags et catégories personnalisés
- Notifications par email quand un job est terminé

