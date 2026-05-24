# Configuration des variables d'environnement pour l'envoi d'emails

Ajoutez ces variables à votre fichier `.env` dans le dossier `server/` :

## Variables Mailjet (pour domaines personnalisés)

```bash
# Mailjet API credentials
# Obtenez-les sur https://app.mailjet.com/account/api_keys
MAILJET_API_KEY=votre_api_key_mailjet
MAILJET_SECRET_KEY=votre_secret_key_mailjet
```

## Variables Google OAuth (pour Gmail)

```bash
# Google OAuth credentials
# Créez-les dans https://console.cloud.google.com/
GOOGLE_CLIENT_ID=votre_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=votre_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/email-accounts/gmail/callback
```

**Important :** En production, changez l'URI de redirection pour votre domaine :
```bash
GOOGLE_REDIRECT_URI=https://votredomaine.com/api/v1/email-accounts/gmail/callback
```

## Exemple de fichier .env complet

```bash
# Environment
ENV=development
DEBUG=true
API_BASE_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# Database
DATABASE_URL=mysql+pymysql://root:root@localhost:3310/devleadhunter

# JWT
SECRET_KEY=dev-secret-key-change-in-production

# Mailjet
MAILJET_API_KEY=votre_api_key
MAILJET_SECRET_KEY=votre_secret_key

# Google OAuth
GOOGLE_CLIENT_ID=votre_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=votre_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/email-accounts/gmail/callback
```

## Installation des dépendances Python

Après avoir ajouté les variables d'environnement, installez les dépendances nécessaires :

```bash
cd server
pip install -r requirements.txt
```

## Initialisation de la base de données

Créez les nouvelles tables pour le système d'emails :

```bash
python init_db.py
```

Cela créera les tables :
- `email_accounts` - Comptes d'expéditeur
- `email_templates` - Templates d'emails
- `email_logs` - Historique des envois

## Démarrage du serveur

```bash
python main.py
```

Le serveur démarre sur http://localhost:8000

Testez avec : http://localhost:8000/docs

