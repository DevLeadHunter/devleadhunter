# Configuration Stripe

Ce document explique comment configurer Stripe pour le système de paiement de crédits.

## 1. Création d'un compte Stripe

1. Créez un compte sur [Stripe](https://stripe.com)
2. Récupérez vos clés API depuis le [Dashboard Stripe](https://dashboard.stripe.com/apikeys) 

## 2. Configuration des variables d'environnement

Ajoutez les variables suivantes dans votre fichier `.env` du serveur :

```env
# Stripe Configuration
STRIPE_SECRET_KEY=sk_test_...  # Clé secrète Stripe (commence par sk_test_ en mode test)
STRIPE_PUBLIC_KEY=pk_test_...  # Clé publique Stripe (commence par pk_test_ en mode test)
STRIPE_WEBHOOK_SECRET=whsec_... # Secret du webhook Stripe
FRONTEND_URL=http://localhost:3000  # URL de votre frontend
```

### Clés de test vs production

- **Mode test** : Utilisez `sk_test_...` et `pk_test_...` pour tester
- **Mode production** : Utilisez `sk_live_...` et `pk_live_...` pour les vrais paiements

## 3. Configuration du Webhook

### En développement (localhost)

#### Option 1 : Stripe CLI installé localement

Utilisez [Stripe CLI](https://stripe.com/docs/stripe-cli) pour transférer les webhooks :

```bash
# Installer Stripe CLI
# Sur Windows : téléchargez depuis https://github.com/stripe/stripe-cli/releases

# Se connecter à Stripe
stripe login

# Transférer les webhooks vers votre serveur local
stripe listen --forward-to http://localhost:8000/api/v1/payments/webhook
```

La commande `stripe listen` affichera un secret webhook (commence par `whsec_`). Copiez-le dans votre `.env` :

```env
STRIPE_WEBHOOK_SECRET=whsec_...
```

#### Option 2 : Utiliser Stripe CLI via Docker (Recommandé)

Un service Stripe CLI est disponible dans `docker-compose.yml` qui utilise automatiquement votre `STRIPE_SECRET_KEY` :

1. **Configurez votre `.env`** avec les clés Stripe :
   ```env
   STRIPE_SECRET_KEY=sk_test_...
   ```

2. **Démarrez le service Stripe CLI** :
   ```bash
   docker-compose up -d stripe_cli
   ```

3. **Récupérez le webhook secret** :
   ```bash
   docker-compose logs stripe_cli | grep "whsec_"
   ```
   
   Copiez le secret dans votre `.env` :
   ```env
   STRIPE_WEBHOOK_SECRET=whsec_...
   ```
   
4. **Vérifiez que tout fonctionne** :
   ```bash
   docker-compose logs -f stripe_cli
   ```

Vous devriez voir des événements webhook apparaître en temps réel lorsque vous effectuez des paiements de test.

### En production

1. Allez sur [Stripe Dashboard > Webhooks](https://dashboard.stripe.com/webhooks)
2. Cliquez sur "Add endpoint"
3. URL : `https://votre-domaine.com/api/v1/payments/webhook`
4. Sélectionnez les événements :
   - `checkout.session.completed`
   - `payment_intent.succeeded` (optionnel, backup)
5. Copiez le "Signing secret" dans votre `.env`

## 4. Méthodes de paiement disponibles

Stripe Checkout supporte automatiquement :
- ✅ **Cartes bancaires** (Visa, Mastercard, etc.)
- ✅ **Apple Pay** (si configuré dans Stripe Dashboard)
- ✅ **Google Pay** (si configuré)
- ✅ **Liens de paiement Stripe**
- ✅ **Autres méthodes** selon votre région

### Activer Apple Pay

1. Allez dans [Stripe Dashboard > Settings > Apple Pay](https://dashboard.stripe.com/settings/payment_methods)
2. Ajoutez votre domaine
3. Vérifiez votre domaine (DNS)

## 5. Test des paiements

### Cartes de test Stripe

Utilisez ces cartes pour tester :

```
# Carte acceptée
Numéro : 4242 4242 4242 4242 ou 4000002500000003
Date : n'importe quelle date future
CVC : n'importe quel 3 chiffres

# Carte refusée (insuffisant)
Numéro : 4000 0000 0000 9995

# Carte nécessitant 3D Secure
Numéro : 4000 0027 6000 3184
```

### Tester le webhook localement

```bash
# Dans un terminal, lancez stripe listen
stripe listen --forward-to http://localhost:8000/api/v1/payments/webhook

# Dans un autre terminal, déclenchez un événement de test
stripe trigger checkout.session.completed
```

## 6. Vérification de la configuration

Une fois configuré, vous pouvez :

1. **Vérifier la page d'achat** : `/dashboard/buy-credits`
2. **Créer une session de test** : Sélectionnez un nombre de crédits et cliquez sur "Proceed to Payment"
3. **Vérifier les logs** : Les erreurs Stripe apparaîtront dans les logs du serveur

## 7. Sécurité

⚠️ **IMPORTANT** :
- ⛔ **Ne jamais** commiter les clés Stripe dans Git
- ✅ Ajoutez `.env` à `.gitignore`
- ✅ Utilisez des variables d'environnement sécurisées en production
- ✅ Vérifiez toujours les signatures webhook en production

## 8. Dépannage

### Erreur "Stripe payment service is not configured"
→ Vérifiez que `STRIPE_SECRET_KEY` est défini dans `.env`

### Erreur "Invalid webhook signature"
→ Vérifiez que `STRIPE_WEBHOOK_SECRET` correspond au secret de votre endpoint webhook

### Les crédits ne sont pas ajoutés après paiement
→ Vérifiez :
1. Que le webhook est bien configuré
2. Que l'événement `checkout.session.completed` est bien envoyé
3. Les logs du serveur pour voir les erreurs

## 9. Personnalisation de l'apparence

Pour améliorer l'affichage du panneau gauche (gris/noir) de la page de paiement Stripe :

1. Connectez-vous au [Dashboard Stripe](https://dashboard.stripe.com)
2. Allez dans **Paramètres > Mise à l'épreuve > Personnalisation**
3. Personnalisez :
   - **Logo** : Ajoutez votre logo pour améliorer l'apparence
   - **Couleurs** : Ajustez les couleurs de votre marque
   - **Texte** : Personnalisez les messages d'aide

⚠️ **Note** : Le style du panneau gauche est généré par Stripe et ne peut pas être personnalisé via l'API. Seule la personnalisation via le Dashboard Stripe permet d'améliorer l'apparence.

## 10. Ressources

- [Documentation Stripe Checkout](https://stripe.com/docs/payments/checkout)
- [Guide des webhooks Stripe](https://stripe.com/docs/webhooks)
- [Stripe Testing](https://stripe.com/docs/testing)
- [Personnaliser Stripe Checkout](https://dashboard.stripe.com/settings/branding)

