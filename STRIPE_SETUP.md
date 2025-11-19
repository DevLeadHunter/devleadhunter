# Configuration Stripe pour DevLeadHunter

Ce guide vous explique comment configurer Stripe pour accepter les paiements en production.

## 📋 Prérequis

- Un compte Stripe (créez-en un sur https://dashboard.stripe.com)
- Accès aux GitHub Secrets de votre dépôt

## 🔑 Récupérer vos Clés Stripe

### 1. Connectez-vous à Stripe Dashboard

Allez sur https://dashboard.stripe.com et connectez-vous.

### 2. Activez le Mode Production (si ce n'est pas déjà fait)

En haut à droite, vous verrez un toggle **"Mode test"** / **"Mode production"**.

- **Mode test** : Pour le développement (clés commençant par `pk_test_` et `sk_test_`)
- **Mode production** : Pour la production (clés commençant par `pk_live_` et `sk_live_`)

### 3. Récupérer les Clés API

1. Dans le menu, allez sur **Developers** > **API keys**
2. Vous verrez deux clés :

#### Publishable key (Clé publique)
```
pk_live_51xxxxxxxxxxxxxxxxxxxxx
```
→ C'est votre **`STRIPE_PUBLIC_KEY`**

#### Secret key (Clé secrète) ⚠️
```
sk_live_51xxxxxxxxxxxxxxxxxxxxx
```
→ C'est votre **`STRIPE_SECRET_KEY`**

⚠️ **ATTENTION** : Ne partagez JAMAIS votre clé secrète ! Elle donne un accès complet à votre compte Stripe.

### 4. Configurer le Webhook

Les webhooks permettent à Stripe de notifier votre API lors d'un paiement réussi.

#### Étape 4.1 : Créer le Webhook

1. Dans le menu, allez sur **Developers** > **Webhooks**
2. Cliquez sur **Add endpoint**
3. Entrez l'URL de votre endpoint :
   ```
   https://api.devleadhunter.dibodev.fr/api/v1/payments/webhook
   ```

#### Étape 4.2 : Sélectionner les Événements

Cochez ces événements :
- ✅ `checkout.session.completed`
- ✅ `payment_intent.succeeded`

#### Étape 4.3 : Récupérer le Signing Secret

Après avoir créé le webhook, cliquez dessus et vous verrez :

```
Signing secret
whsec_xxxxxxxxxxxxxxxxxxxxxxxxxx
```
→ C'est votre **`STRIPE_WEBHOOK_SECRET`**

## 🔐 Ajouter les Secrets dans GitHub

### 1. Accédez aux GitHub Secrets

1. Allez sur votre dépôt GitHub
2. **Settings** > **Secrets and variables** > **Actions**
3. Cliquez sur **New repository secret**

### 2. Ajoutez les 3 Secrets Stripe

| Nom du Secret | Valeur | Exemple |
|---------------|--------|---------|
| `STRIPE_SECRET_KEY` | Votre clé secrète Stripe | `sk_live_51...` |
| `STRIPE_PUBLIC_KEY` | Votre clé publique Stripe | `pk_live_51...` |
| `STRIPE_WEBHOOK_SECRET` | Votre signing secret webhook | `whsec_...` |

## 🚀 Déployer les Modifications

Une fois les secrets configurés :

```bash
# Les modifications du workflow sont déjà poussées
# Il suffit de déclencher un nouveau déploiement
git commit --allow-empty -m "chore: Trigger deployment with Stripe config"
git push origin main
```

Ou attendez simplement le prochain déploiement automatique !

## 🧪 Tester le Paiement

### 1. En Mode Test (développement local)

Utilisez les cartes de test Stripe :

| Numéro de carte | Résultat |
|----------------|----------|
| `4242 4242 4242 4242` | ✅ Paiement réussi |
| `4000 0000 0000 0002` | ❌ Carte déclinée |
| `4000 0025 0000 3155` | 🔐 Nécessite 3D Secure |

- **Date d'expiration** : N'importe quelle date future (ex: 12/34)
- **CVC** : N'importe quel 3 chiffres (ex: 123)
- **Code postal** : N'importe quel code postal valide

### 2. En Production

1. Allez sur https://devleadhunter.dibodev.fr
2. Connectez-vous
3. Allez sur **Acheter des crédits**
4. Sélectionnez un montant et testez avec une vraie carte (mode test ou production)

## 🔍 Vérifier que Tout Fonctionne

### 1. Vérifier les Logs du Serveur

```bash
ssh votre_user@votre_vps
sudo journalctl -u devleadhunter-api.service -n 100 -f
```

Essayez de créer une session de paiement et vérifiez qu'il n'y a pas d'erreur.

### 2. Vérifier les Webhooks dans Stripe

1. Allez sur **Developers** > **Webhooks** dans Stripe
2. Cliquez sur votre webhook
3. Onglet **Logs** : Vous verrez les événements reçus
   - ✅ Statut 200 = Succès
   - ❌ Statut 400/500 = Erreur

### 3. Test Complet

1. **Créer une session de paiement** :
   ```bash
   curl -X POST https://api.devleadhunter.dibodev.fr/api/v1/payments/create-checkout-session \
     -H "Authorization: Bearer VOTRE_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"credits": 10}'
   ```

2. **Résultat attendu** :
   ```json
   {
     "id": "cs_test_...",
     "url": "https://checkout.stripe.com/c/pay/cs_test_...",
     "amount": 1000,
     "credits": 10
   }
   ```

3. **Compléter le paiement** :
   - Ouvrez l'URL retournée dans votre navigateur
   - Complétez le paiement avec une carte test (en mode test) ou vraie carte (en prod)

4. **Vérifier les crédits** :
   - Les crédits devraient être ajoutés automatiquement au compte
   - Vérifiez dans le dashboard utilisateur

## 🔒 Sécurité

### Bonnes Pratiques

- ✅ **Ne commitez JAMAIS** les clés Stripe dans le code
- ✅ **Utilisez les secrets GitHub** pour stocker les clés
- ✅ **Mode test** pour le développement, **mode production** pour la prod
- ✅ **Vérifiez les webhooks** avec le signing secret
- ✅ **Logs** : Surveillez les logs pour détecter les problèmes

### Rotation des Clés

Si vous pensez qu'une clé a été compromise :

1. Allez sur **Developers** > **API keys** dans Stripe
2. Cliquez sur **Roll key** à côté de la clé secrète
3. Mettez à jour le secret GitHub `STRIPE_SECRET_KEY`
4. Redéployez l'application

## 💰 Configuration des Prix

Les prix sont configurés dans la base de données via les **Credit Settings**.

Pour modifier le prix par crédit :

1. Connectez-vous en tant qu'admin
2. Allez sur **Settings** > **Credit Settings**
3. Modifiez le prix par crédit

Ou directement en base de données :

```sql
UPDATE credit_settings 
SET price_per_credit = 0.10 
WHERE id = 1;
```

## 📊 Tableau de Bord Stripe

Dans votre Dashboard Stripe, vous pouvez :

- 📈 Voir les paiements en temps réel
- 💳 Gérer les remboursements
- 📧 Envoyer des reçus aux clients
- 📊 Consulter les statistiques
- 🔔 Configurer les notifications

## ❓ Résolution des Problèmes

### Erreur 503 "Stripe payment service is not configured"

**Cause** : Les secrets Stripe ne sont pas configurés ou sont vides.

**Solution** :
1. Vérifiez que les 3 secrets sont bien configurés dans GitHub
2. Vérifiez qu'ils ne sont pas vides
3. Redéployez l'application

### Erreur "Invalid API Key"

**Cause** : La clé API est incorrecte ou vous mélangez mode test/production.

**Solution** :
1. Vérifiez que vous utilisez la bonne clé (test vs production)
2. Vérifiez qu'il n'y a pas d'espaces dans la clé
3. Régénérez une nouvelle clé si nécessaire

### Webhook non reçu

**Cause** : URL du webhook incorrecte ou firewall qui bloque.

**Solution** :
1. Vérifiez l'URL du webhook : `https://api.devleadhunter.dibodev.fr/api/v1/payments/webhook`
2. Vérifiez que votre serveur est accessible depuis internet
3. Testez le webhook depuis Stripe Dashboard (bouton "Send test webhook")

### Les crédits ne sont pas ajoutés après paiement

**Cause** : Webhook non configuré ou erreur dans le traitement.

**Solution** :
1. Vérifiez les logs du serveur pendant un paiement
2. Vérifiez les logs des webhooks dans Stripe Dashboard
3. Vérifiez que le webhook secret est correct

## 📚 Ressources

- [Documentation Stripe](https://stripe.com/docs)
- [API Stripe](https://stripe.com/docs/api)
- [Webhooks Stripe](https://stripe.com/docs/webhooks)
- [Cartes de test](https://stripe.com/docs/testing)
- [Dashboard Stripe](https://dashboard.stripe.com)

## ✅ Checklist Finale

- [ ] Compte Stripe créé et vérifié
- [ ] Mode production activé (pour la prod)
- [ ] Clés API récupérées (public + secret)
- [ ] Webhook configuré avec l'URL correcte
- [ ] Signing secret du webhook récupéré
- [ ] 3 secrets ajoutés dans GitHub Actions
- [ ] Application redéployée
- [ ] Test de paiement effectué
- [ ] Crédits correctement ajoutés après paiement
- [ ] Webhooks reçus et traités (vérifiés dans Stripe Dashboard)

---

Une fois tous les secrets configurés, votre système de paiement Stripe sera opérationnel ! 🎉

