# Configuration du Stockage FTP pour les Images du Support

Ce guide vous explique comment configurer le stockage FTP pour les images uploadées dans le système de support.

## 📋 Prérequis

Vous devez avoir :
- Un serveur FTP accessible depuis internet
- Les identifiants FTP (utilisateur et mot de passe)
- Un répertoire sur le FTP pour stocker les images
- Une URL publique pour accéder aux fichiers uploadés

## 🔐 Configuration des GitHub Secrets

### 1. Accédez aux GitHub Secrets

1. Allez sur votre dépôt GitHub
2. Cliquez sur **Settings** > **Secrets and variables** > **Actions**
3. Cliquez sur **New repository secret**

### 2. Ajoutez les Secrets suivants

#### `API_BASE_URL`
- **Valeur** : `https://api.devleadhunter.dibodev.fr`
- **Description** : URL de base de votre API en production

#### `SUPPORT_FTP_HOST`
- **Valeur** : Adresse de votre serveur FTP (ex: `ftp.votredomaine.com`)
- **Description** : Adresse du serveur FTP

#### `SUPPORT_FTP_PORT`
- **Valeur** : `21` (ou le port de votre serveur FTP)
- **Description** : Port du serveur FTP (généralement 21)

#### `SUPPORT_FTP_USER`
- **Valeur** : Votre nom d'utilisateur FTP
- **Description** : Nom d'utilisateur pour la connexion FTP

#### `SUPPORT_FTP_PASSWORD`
- **Valeur** : Votre mot de passe FTP
- **Description** : Mot de passe pour la connexion FTP

#### `SUPPORT_FTP_BASE_DIR`
- **Valeur** : `/public_html/uploads/support` (ou le chemin sur votre FTP)
- **Description** : Répertoire de base sur le serveur FTP où seront stockées les images
- **Note** : Le dossier sera créé automatiquement s'il n'existe pas

#### `SUPPORT_FTP_PUBLIC_BASE_URL`
- **Valeur** : `https://votredomaine.com/uploads/support`
- **Description** : URL publique pour accéder aux fichiers uploadés
- **Important** : Cette URL doit pointer vers le même répertoire que `SUPPORT_FTP_BASE_DIR`

#### `SUPPORT_FTP_USE_TLS`
- **Valeur** : `true` ou `false`
- **Description** : Utiliser TLS/SSL pour la connexion FTP (recommandé : `true`)

## 🖼️ Configuration du Serveur Web pour servir les Images

### Option 1 : Nginx (Recommandé)

Si votre FTP pointe vers un répertoire accessible par votre serveur web, configurez Nginx pour servir les fichiers :

```nginx
# Dans votre fichier de configuration nginx
location /uploads/support {
    alias /chemin/vers/public_html/uploads/support;
    
    # Headers pour les images
    add_header Cache-Control "public, max-age=31536000, immutable";
    add_header Access-Control-Allow-Origin "*";
    
    # Types MIME
    types {
        image/jpeg jpg jpeg;
        image/png png;
        image/webp webp;
    }
    
    # Désactiver les logs d'accès pour les images
    access_log off;
}
```

### Option 2 : Serveur FTP avec accès HTTP

Si votre hébergeur FTP fournit directement un accès HTTP aux fichiers uploadés, utilisez simplement l'URL fournie par votre hébergeur comme `SUPPORT_FTP_PUBLIC_BASE_URL`.

## 🧪 Test de la Configuration

### 1. Après avoir ajouté les secrets GitHub

1. Faites un commit et push sur la branche `main`
2. Le workflow de déploiement va se déclencher automatiquement
3. Vérifiez que le déploiement se passe bien dans l'onglet **Actions**

### 2. Test de l'upload d'image

1. Connectez-vous à votre application en production
2. Allez dans le support et créez un ticket
3. Uploadez une image
4. Vérifiez que l'image s'affiche correctement

### 3. Vérification sur le FTP

Connectez-vous à votre serveur FTP et vérifiez que les fichiers sont bien uploadés dans le répertoire configuré :

```
/public_html/uploads/support/
  └── 2025/
      └── 11/
          └── [hash].jpg
```

## 🔍 Résolution des Problèmes

### Erreur 404 sur les images

**Cause** : L'URL publique ne correspond pas au chemin FTP

**Solution** :
1. Vérifiez que `SUPPORT_FTP_PUBLIC_BASE_URL` pointe bien vers le bon répertoire
2. Vérifiez la configuration nginx/apache pour servir les fichiers

### Erreur lors de l'upload

**Cause** : Problème de connexion FTP ou permissions

**Solution** :
1. Vérifiez les identifiants FTP (host, port, user, password)
2. Vérifiez que l'utilisateur FTP a les permissions d'écriture
3. Vérifiez les logs du serveur : `sudo journalctl -u devleadhunter-api.service -n 50`

### Les fichiers sont uploadés mais pas accessibles

**Cause** : Permissions sur les fichiers ou configuration du serveur web

**Solution** :
1. Vérifiez les permissions des fichiers sur le FTP (644 pour les fichiers, 755 pour les dossiers)
2. Vérifiez la configuration de votre serveur web (nginx/apache)

## 📊 Structure des Fichiers

Les fichiers sont organisés automatiquement par année et mois :

```
/uploads/support/
  └── YYYY/           # Année (ex: 2025)
      └── MM/         # Mois (ex: 11)
          └── [hash][extension]  # Fichier avec hash unique
```

## 🔒 Sécurité

- ✅ Les mots de passe sont stockés dans GitHub Secrets (chiffrés)
- ✅ La connexion FTP utilise TLS si `SUPPORT_FTP_USE_TLS=true`
- ✅ Les fichiers ont des noms aléatoires (hash UUID)
- ✅ Seuls les formats d'image autorisés sont acceptés (JPG, PNG, WEBP)
- ✅ Limite de taille : 8 MB par fichier

## 📝 Exemple de Configuration Complète

```env
# Dans GitHub Secrets
API_BASE_URL=https://api.devleadhunter.dibodev.fr
SUPPORT_FTP_HOST=ftp.votredomaine.com
SUPPORT_FTP_PORT=21
SUPPORT_FTP_USER=votre_user_ftp
SUPPORT_FTP_PASSWORD=votre_mot_de_passe_secure
SUPPORT_FTP_BASE_DIR=/public_html/uploads/support
SUPPORT_FTP_PUBLIC_BASE_URL=https://devleadhunter.dibodev.fr/uploads/support
SUPPORT_FTP_USE_TLS=true
```

## 🚀 Déploiement

Une fois tous les secrets configurés dans GitHub :

1. Commit et push vos modifications
2. Le workflow GitHub Actions va automatiquement :
   - Déployer le nouveau code
   - Créer le fichier .env avec toutes les variables
   - Redémarrer le service

3. Les prochains uploads utiliseront automatiquement le FTP !

## ℹ️ Remarques

- **En développement** : Les fichiers sont stockés localement dans `server/uploads/support/`
- **En production** : Les fichiers sont automatiquement envoyés sur le FTP si configuré
- **Fallback** : Si le FTP n'est pas configuré, le système utilise le stockage local même en production

