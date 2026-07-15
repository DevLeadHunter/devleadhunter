"""
Stripe payment service for handling credit purchases.
"""
import stripe
from typing import Optional, Dict, Any
from decimal import Decimal
from sqlalchemy.orm import Session

from core.config import settings
from models.user import User
from models.credit_settings import CreditSettings
from services.credit_service import credit_service, TransactionType


class StripePaymentService:
    """
    Service for managing Stripe payment operations.
    
    This service handles:
    - Creating Stripe Checkout Sessions
    - Processing webhook events
    - Adding credits after successful payment
    
    Attributes:
        stripe_client: Stripe client instance configured with secret key
    """
    
    def __init__(self):
        """
        Initialize Stripe payment service.
        
        Sets up the Stripe API client with the secret key from settings.
        """
        if not settings.stripe_secret_key:
            raise ValueError("STRIPE_SECRET_KEY is not configured in environment variables")
        
        stripe.api_key = settings.stripe_secret_key
        self.stripe_client = stripe
    
    def calculate_amount(self, credits: int, price_per_credit: Decimal) -> int:
        """
        Calculate payment amount in cents from credits and price per credit.
        
        Args:
            credits: Number of credits to purchase
            price_per_credit: Price per credit in EUR (Decimal)
            
        Returns:
            Amount in cents (integer, Stripe uses cents)
        """
        total_amount = Decimal(credits) * price_per_credit
        # Convert to cents (multiply by 100) and round to integer
        amount_cents = int((total_amount * 100).quantize(Decimal('1')))
        return amount_cents
    
    def create_checkout_session(
        self,
        db: Session,
        user_id: int,
        credits: int,
        success_url: str,
        cancel_url: str
    ) -> Dict[str, Any]:
        """
        Create a Stripe Checkout Session for credit purchase.
        
        This creates a payment session that supports:
        - Credit cards
        - Apple Pay (if configured)
        - Google Pay
        - Payment links
        - Other payment methods available in Stripe
        
        Args:
            db: Database session
            user_id: User ID purchasing credits
            credits: Number of credits to purchase
            success_url: URL to redirect after successful payment
            cancel_url: URL to redirect if payment is cancelled
            
        Returns:
            Dictionary containing checkout session data with 'id' and 'url'
            
        Raises:
            ValueError: If user not found, invalid credits amount, or credit settings not found
            Exception: If Stripe API call fails
        """
        # Validate user exists
        user: Optional[User] = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User with id {user_id} not found")
        
        # Validate credits amount
        if credits <= 0:
            raise ValueError("Credits amount must be greater than 0")
        
        # Get credit settings
        credit_settings: Optional[CreditSettings] = db.query(CreditSettings).filter(
            CreditSettings.id == 1
        ).first()
        if not credit_settings:
            raise ValueError("Credit settings not found. Please configure credit settings first.")
        
        # Validate minimum purchase amount
        if credits < credit_settings.minimum_credits_purchase:
            raise ValueError(
                f"Minimum purchase amount is {credit_settings.minimum_credits_purchase} credits. "
                f"You attempted to purchase {credits} credits."
            )
        
        # Calculate amount in cents
        amount_cents = self.calculate_amount(credits, credit_settings.price_per_credit)
        
        try:
            # Create Stripe Checkout Session
            checkout_session = self.stripe_client.checkout.Session.create(
                payment_method_types=['card'],  # Cartes + Apple/Google Pay (activés automatiquement)
                line_items=[
                    {
                        'price_data': {
                            'currency': 'eur',
                            'product_data': {
                                'name': f'{credits} Crédits Devleadhunter',
                            },
                            'unit_amount': amount_cents,
                        },
                        'quantity': 1,
                    }
                ],
                mode='payment',
                success_url=success_url,
                cancel_url=cancel_url,
                client_reference_id=str(user_id),
                customer_email=user.email,
                metadata={
                    'user_id': str(user_id),
                    'credits': str(credits),
                    'price_per_credit': str(credit_settings.price_per_credit),
                },
                payment_method_options={
                    'card': {
                        'request_three_d_secure': 'automatic',
                    }
                },
                # Enable automatic payment methods (Apple Pay, Google Pay, etc.)
                automatic_tax={'enabled': False},
                payment_intent_data={
                    'metadata': {
                        'user_id': str(user_id),
                        'credits': str(credits),
                    }
                }
            )
            
            return {
                'id': checkout_session.id,
                'url': checkout_session.url,
                'amount': amount_cents,
                'credits': credits
            }
            
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe error: {str(e)}")
    
    def create_order_payment_link(
        self,
        *,
        order_id: int,
        user_id: int,
        amount_cents: int,
        currency: str,
        product_label: str,
        business_name: Optional[str],
    ) -> Dict[str, Any]:
        """
        Create a persistent Stripe Payment Link for a website sale (not credits).

        Returns a dict with ``payment_link_id``, ``url`` and ``amount``. The link
        carries ``metadata.type = "order"`` so the webhook can route it correctly.
        """
        if amount_cents <= 0:
            raise ValueError("Order amount must be greater than 0")

        label = product_label if not business_name else f"{product_label} — {business_name}"
        try:
            product = self.stripe_client.Product.create(name=label)
            price = self.stripe_client.Price.create(
                product=product.id,
                unit_amount=amount_cents,
                currency=currency or "eur",
            )
            link = self.stripe_client.PaymentLink.create(
                line_items=[{"price": price.id, "quantity": 1}],
                metadata={
                    "type": "order",
                    "order_id": str(order_id),
                    "user_id": str(user_id),
                },
                after_completion={"type": "hosted_confirmation"},
            )
            return {
                "payment_link_id": link.id,
                "url": link.url,
                "amount": amount_cents,
            }
        except stripe.error.StripeError as exc:
            raise Exception(f"Stripe error: {str(exc)}")

    def deactivate_payment_link(self, payment_link_id: str) -> None:
        """Best-effort deactivation of a Stripe payment link (e.g. on cancel)."""
        try:
            self.stripe_client.PaymentLink.modify(payment_link_id, active=False)
        except stripe.error.StripeError:
            pass

    def handle_webhook_event(
        self,
        db: Session,
        event: Dict[str, Any]
    ) -> bool:
        """
        Handle Stripe webhook event.
        
        Processes payment completion events and adds credits to user account.
        
        Args:
            db: Database session
            event: Stripe webhook event dictionary
            
        Returns:
            True if event was processed successfully, False otherwise
        """
        event_type = event.get('type')
        
        # Handle successful payment
        if event_type == 'checkout.session.completed':
            session = event.get('data', {}).get('object', {})
            
            # Get metadata
            metadata = session.get('metadata', {})
            user_id = int(metadata.get('user_id', 0))
            credits = int(metadata.get('credits', 0))
            
            if user_id == 0 or credits == 0:
                return False
            
            # Check if payment was successful
            payment_status = session.get('payment_status', '')
            if payment_status != 'paid':
                return False
            
            # Check if credits were already added (idempotency)
            # Get all transactions for this user and check if this session was already processed
            session_id = session.get('id', '')
            existing_transactions = credit_service.get_user_transactions(db, user_id, limit=100)
            
            # Check if this session was already processed
            for transaction in existing_transactions:
                if transaction.transaction_metadata and f"stripe_session_id:{session_id}" in transaction.transaction_metadata:
                    # Already processed, skip
                    return True
            
            # Add credits to user account
            try:
                credit_service.add_credits(
                    db=db,
                    user_id=user_id,
                    amount=credits,
                    description=f"Credit purchase via Stripe ({credits} credits)",
                    transaction_type=TransactionType.PURCHASE,
                    metadata=f"stripe_session_id:{session.get('id', 'unknown')}"
                )
                return True
            except Exception as e:
                print(f"Error adding credits after payment: {e}")
                return False
        
        # Handle payment intent succeeded (alternative webhook)
        elif event_type == 'payment_intent.succeeded':
            payment_intent = event.get('data', {}).get('object', {})
            metadata = payment_intent.get('metadata', {})
            user_id = int(metadata.get('user_id', 0))
            credits = int(metadata.get('credits', 0))
            
            if user_id > 0 and credits > 0:
                payment_intent_id = payment_intent.get('id', '')
                
                # Check idempotency
                existing_transactions = credit_service.get_user_transactions(db, user_id, limit=100)
                for transaction in existing_transactions:
                    if transaction.transaction_metadata and f"stripe_payment_intent:{payment_intent_id}" in transaction.transaction_metadata:
                        # Already processed
                        return True
                
                try:
                    credit_service.add_credits(
                        db=db,
                        user_id=user_id,
                        amount=credits,
                        description=f"Credit purchase via Stripe ({credits} credits)",
                        transaction_type=TransactionType.PURCHASE,
                        metadata=f"stripe_payment_intent:{payment_intent_id}"
                    )
                    return True
                except Exception as e:
                    print(f"Error adding credits after payment: {e}")
                    return False
        
        return False
    
    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str
    ) -> Optional[Dict[str, Any]]:
        """
        Verify Stripe webhook signature and parse event.
        
        Args:
            payload: Raw webhook payload bytes
            signature: Stripe webhook signature from request header
            
        Returns:
            Parsed event dictionary if signature is valid, None otherwise
            
        Raises:
            ValueError: If webhook secret is not configured
        """
        if not settings.stripe_webhook_secret:
            raise ValueError("STRIPE_WEBHOOK_SECRET is not configured in environment variables")
        
        try:
            event = self.stripe_client.Webhook.construct_event(
                payload,
                signature,
                settings.stripe_webhook_secret
            )
            return event
        except ValueError as e:
            # Invalid payload
            print(f"Invalid webhook payload: {e}")
            return None
        except stripe.error.SignatureVerificationError as e:
            # Invalid signature
            print(f"Invalid webhook signature: {e}")
            return None


# Singleton instance (will be None if Stripe not configured)
# Initialized lazily to avoid errors at import time
stripe_payment_service: Optional[StripePaymentService] = None

def get_stripe_service() -> Optional[StripePaymentService]:
    """
    Get Stripe payment service instance (lazy initialization).
    
    Returns:
        StripePaymentService instance if configured, None otherwise
    """
    global stripe_payment_service
    if stripe_payment_service is None and settings.stripe_secret_key:
        try:
            stripe_payment_service = StripePaymentService()
        except ValueError:
            pass
    return stripe_payment_service

