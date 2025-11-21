# Configuration du système d'envoi d'emails

## Vue d'ensemble

Ce système permet d'envoyer des emails de prospection depuis votre application en utilisant :
- **Mailjet** pour les domaines personnalisés (avec vérification SPF/DKIM)
- **Gmail OAuth** pour envoyer via Gmail

## 📋 Prérequis

### 1. Compte Mailjet

1. Créez un compte sur [Mailjet](https://www.mailjet.com/)
2. Récupérez vos identifiants :
   - API Key
   - Secret Key
3. Ajoutez-les à votre fichier `.env` :

```bash
MAILJET_API_KEY=votre_api_key
MAILJET_SECRET_KEY=votre_secret_key
```

### 2. Google OAuth (pour Gmail)

1. Allez dans la [Google Cloud Console](https://console.cloud.google.com/)
2. Créez un nouveau projet ou sélectionnez-en un existant
3. Activez l'API Gmail :
   - API & Services > Bibliothèque
   - Recherchez "Gmail API"
   - Cliquez sur "Activer"
4. Créez des identifiants OAuth 2.0 :
   - API & Services > Identifiants
   - Créer des identifiants > ID client OAuth
   - Type d'application : Application Web
   - Nom : DevLeadHunter
   - URI de redirection autorisés :
     ```
     http://localhost:8000/api/v1/email-accounts/gmail/callback
     https://votredomaine.com/api/v1/email-accounts/gmail/callback
     ```
5. Téléchargez les identifiants et ajoutez-les à `.env` :

```bash
GOOGLE_CLIENT_ID=votre_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=votre_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/email-accounts/gmail/callback
```

## 🗄️ Configuration de la base de données

Créez les tables nécessaires en exécutant :

```bash
cd server
python init_db.py
```

Cela créera les tables :
- `email_accounts` - Comptes d'expéditeur
- `email_templates` - Templates d'emails
- `email_logs` - Historique des envois

## 🚀 Utilisation

### 1. Configurer un compte d'expéditeur

#### Option A : Domaine personnalisé

1. Allez dans **Dashboard > Comptes Email**
2. Cliquez sur **+ Domaine personnalisé**
3. Remplissez les informations :
   - Nom d'expéditeur : "Votre Nom"
   - Email : contact@votredomaine.com
   - Domaine : votredomaine.com
4. **Configurez les enregistrements DNS** :

**SPF (obligatoire) :**
```
Type: TXT
Host: @
Valeur: v=spf1 include:spf.mailjet.com ~all
```

**DKIM (obligatoire) :**
1. Connectez-vous à [Mailjet Dashboard](https://app.mailjet.com/)
2. Allez dans Account Settings > Sender domains & addresses
3. Ajoutez votre domaine
4. Copiez les enregistrements DKIM fournis
5. Ajoutez-les à votre DNS

5. Revenez dans l'application et cliquez sur **Vérifier maintenant**

#### Option B : Gmail OAuth

1. Allez dans **Dashboard > Comptes Email**
2. Cliquez sur **+ Connecter Gmail**
3. Vous serez redirigé vers Google pour autoriser l'accès
4. Acceptez les permissions
5. Vous serez redirigé vers l'application avec le compte configuré

### 2. Créer des templates d'email

1. Allez dans **Dashboard > Templates d'Email**
2. Cliquez sur **+ Nouveau template**
3. Remplissez le formulaire :

```
Nom: Proposition site web
Sujet: Création de site web pour {company_name}
Corps:
Bonjour {name},

Je me présente, [votre nom], développeur web spécialisé...

J'ai remarqué que {company_name} n'a pas encore de site web...

Variables disponibles:
- {name} - Nom du contact
- {company_name} - Nom de l'entreprise
- {email} - Email du contact
- {phone} - Téléphone
- {city} - Ville
- {address} - Adresse
```

### 3. Envoyer une campagne

1. Créez une campagne et ajoutez des prospects
2. Allez dans **Dashboard > Campagnes**
3. Cliquez sur **Envoyer** sur votre campagne
4. Sélectionnez :
   - Compte d'expéditeur
   - Template d'email
5. Vérifiez l'aperçu
6. Cliquez sur **Envoyer la campagne**

## 📊 Suivi des emails

Les emails envoyés sont enregistrés dans la table `email_logs` avec les statuts :
- `pending` - En attente
- `sent` - Envoyé
- `delivered` - Délivré
- `opened` - Ouvert (si tracking activé)
- `clicked` - Lien cliqué
- `bounced` - Rejeté
- `failed` - Échec

## 🔒 Sécurité

### Tokens OAuth

Les tokens Gmail OAuth sont stockés dans la base de données. **En production** :

1. Chiffrez les tokens avant stockage :
```python
from cryptography.fernet import Fernet

# Générez une clé de chiffrement
key = Fernet.generate_key()
cipher = Fernet(key)

# Chiffrer
encrypted_token = cipher.encrypt(token.encode())

# Déchiffrer
decrypted_token = cipher.decrypt(encrypted_token).decode()
```

2. Stockez la clé de chiffrement dans les variables d'environnement :
```bash
ENCRYPTION_KEY=votre_cle_de_chiffrement
```

### Limites d'envoi

#### Mailjet (Plan gratuit)
- 200 emails/jour
- 6 000 emails/mois
- **Plan payant recommandé** : 9,65€/mois pour 15 000 emails

#### Gmail OAuth
- 500 emails/jour (compte Gmail standard)
- 2 000 emails/jour (Google Workspace)

## 🐛 Dépannage

### "Email account not verified"
→ Vérifiez que les enregistrements DNS SPF et DKIM sont configurés correctement
→ Attendez jusqu'à 48h pour la propagation DNS

### "Failed to send email via Mailjet"
→ Vérifiez vos identifiants API Mailjet
→ Vérifiez que votre compte Mailjet est actif
→ Vérifiez les limites d'envoi

### "Failed to refresh Gmail token"
→ L'utilisateur doit se reconnecter à Gmail
→ Supprimez et reconnectez le compte Gmail

### Emails arrivent en spam
→ Configurez correctement SPF et DKIM
→ Ajoutez un enregistrement DMARC :
```
Type: TXT
Host: _dmarc
Valeur: v=DMARC1; p=none; rua=mailto:admin@votredomaine.com
```
→ Réchauffez votre domaine en envoyant progressivement (10-20-50-100 emails/jour)
→ Personnalisez vos emails (évitez les templates génériques)

## 🔄 Webhooks Mailjet (optionnel)

Pour recevoir les événements de tracking (ouvertures, clics, bounces) :

1. Configurez l'endpoint dans Mailjet Dashboard
2. URL : `https://votredomaine.com/api/v1/webhooks/mailjet`
3. Implémentez le gestionnaire de webhook :

```python
@router.post("/webhooks/mailjet")
async def mailjet_webhook(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    
    for event in data:
        email_log = db.query(EmailLog).filter(
            EmailLog.provider_message_id == event.get("MessageID")
        ).first()
        
        if email_log:
            if event.get("event") == "open":
                email_log.status = EmailStatus.OPENED
                email_log.opened_at = datetime.utcnow()
            elif event.get("event") == "click":
                email_log.status = EmailStatus.CLICKED
                email_log.clicked_at = datetime.utcnow()
            # etc.
            
    db.commit()
    return {"status": "ok"}
```

## 📖 API Documentation

Documentation complète de l'API : `http://localhost:8000/docs`

Principales routes :
- `GET /api/v1/email-accounts` - Liste des comptes
- `POST /api/v1/email-accounts/custom-domain` - Ajouter domaine
- `POST /api/v1/email-accounts/gmail/auth-url` - URL OAuth Gmail
- `GET /api/v1/email-templates` - Liste des templates
- `POST /api/v1/email-templates` - Créer template
- `POST /api/v1/emails/send` - Envoyer email unique
- `POST /api/v1/emails/send-campaign` - Envoyer campagne
- `GET /api/v1/emails/logs` - Historique d'envois
- `GET /api/v1/emails/stats` - Statistiques

## 💡 Bonnes pratiques

1. **Testez d'abord** : Envoyez-vous des emails de test avant d'envoyer à vos prospects
2. **Personnalisez** : Utilisez les variables pour personnaliser chaque email
3. **Respectez la loi** : Incluez un lien de désinscription, conformez-vous au RGPD
4. **Surveillez vos métriques** : Taux d'ouverture <20% = problème de délivrabilité
5. **Limitez l'envoi** : Ne dépassez pas 50-100 emails/jour au début
6. **Variez le contenu** : Évitez d'envoyer exactement le même email à tout le monde
7. **Respectez les horaires** : Envoyez en semaine, entre 9h et 18h

## 🆘 Support

Pour toute question ou problème :
- GitHub Issues : [lien vers votre repo]
- Email : contact@votredomaine.com

