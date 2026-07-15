"""
Accounting service for retrieving financial data from Stripe and database.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
import stripe

from core.config import settings
from models.user import User
from schemas.accounting import (
    AccountingSummary,
    CreditPurchaseTransaction,
    StripePaymentInfo
)


class AccountingService:
    """
    Service for retrieving accounting and financial data.
    """
    
    def __init__(self):
        """Initialize accounting service."""
        self.stripe_client = None
        if settings.stripe_secret_key:
            try:
                stripe.api_key = settings.stripe_secret_key
                self.stripe_client = stripe
            except Exception as e:
                print(f"Warning: Could not initialize Stripe client: {e}")
                self.stripe_client = None
    
    def get_stripe_balance(self) -> Optional[Decimal]:
        """
        Get available balance from Stripe account.
        
        Returns:
            Available balance in cents, or None if Stripe is not configured
        """
        if not self.stripe_client:
            return None
        
        try:
            balance = self.stripe_client.Balance.retrieve()
            # Get available balance (not pending)
            available_balance = balance.available[0].amount if balance.available else 0
            # Convert from cents to euros
            return Decimal(available_balance) / 100
        except Exception as e:
            print(f"Error retrieving Stripe balance: {e}")
            return None
    
    def get_payment_intent_details(self, payment_intent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed payment intent information from Stripe.
        
        Args:
            payment_intent_id: Stripe Payment Intent ID
            
        Returns:
            Payment intent details or None
        """
        if not self.stripe_client:
            return None
        
        try:
            payment_intent = self.stripe_client.PaymentIntent.retrieve(
                payment_intent_id,
                expand=[
                    'charges.data.balance_transaction',
                    'charges.data.payment_method',
                    'payment_method',
                    'refunds'
                ]
            )
            return payment_intent
        except Exception as e:
            print(f"Error retrieving payment intent {payment_intent_id}: {e}")
            return None
    
    def get_checkout_session_details(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed checkout session information from Stripe.
        
        Args:
            session_id: Stripe Checkout Session ID
            
        Returns:
            Checkout session details or None
        """
        if not self.stripe_client:
            return None
        
        try:
            session = self.stripe_client.checkout.Session.retrieve(
                session_id,
                expand=[
                    'payment_intent',
                    'payment_intent.payment_method',
                    'payment_intent.charges',
                    'payment_intent.charges.data.balance_transaction',
                    'customer',
                    'customer_details'
                ]
            )
            return session
        except Exception as e:
            print(f"Error retrieving checkout session {session_id}: {e}")
            return None
    
    def find_stripe_session_by_email_and_date(
        self,
        email: str,
        transaction_date: datetime,
        time_window_hours: int = 24
    ) -> Optional[Dict[str, Any]]:
        """
        Find Stripe checkout session by customer email and approximate transaction date.
        
        Args:
            email: Customer email address
            transaction_date: Approximate transaction date
            time_window_hours: Time window in hours to search around transaction date
            
        Returns:
            Stripe checkout session or None
        """
        if not self.stripe_client or not email:
            return None
        
        try:
            # Calculate time window
            from datetime import timedelta
            start_time = int((transaction_date - timedelta(hours=time_window_hours)).timestamp())
            end_time = int((transaction_date + timedelta(hours=time_window_hours)).timestamp())
            
            # Search for checkout sessions by date range
            # Stripe API supports filtering by created timestamp
            sessions = self.stripe_client.checkout.Session.list(
                limit=100,
                created={'gte': start_time},
                expand=['data.payment_intent', 'data.payment_intent.charges']
            )
            
            # Find session with matching email and within date range
            for session in sessions.data:
                session_created = session.get('created', 0)
                
                # Check if session is within time window
                if session_created < start_time or session_created > end_time:
                    continue
                
                customer_email = session.get('customer_email')
                customer_details = session.get('customer_details', {})
                session_email = customer_details.get('email') or customer_email
                
                if session_email and session_email.lower() == email.lower():
                    if session.get('payment_status') == 'paid':
                        return session
            
            return None
        except Exception as e:
            print(f"Error finding Stripe session by email and date: {e}")
            return None
    
    def extract_stripe_payment_info(
        self,
        transaction_metadata: Optional[str],
        created_at: datetime,
        user_email: Optional[str] = None
    ) -> Optional[StripePaymentInfo]:
        """
        Extract Stripe payment information from transaction metadata.
        
        Args:
            transaction_metadata: Transaction metadata string
            created_at: Transaction creation date
            user_email: User email for fallback search (optional)
            
        Returns:
            Stripe payment info or None
        """
        if not self.stripe_client:
            return None
        
        try:
            payment_info = None
            
            # Check for session ID in metadata
            session_id = None
            if transaction_metadata:
                # Try to find session ID with different formats
                if "stripe_session_id:" in transaction_metadata:
                    session_id = transaction_metadata.split("stripe_session_id:")[1].split(",")[0].strip()
                elif transaction_metadata.startswith("cs_"):
                    # Direct session ID format
                    session_id = transaction_metadata.split()[0].strip()
                    if not session_id.startswith("cs_"):
                        session_id = None
            
            if session_id:
                session = self.get_checkout_session_details(session_id)
                
                if session:
                    payment_intent_id = session.get('payment_intent')
                    payment_intent_obj = None
                    
                    # Get payment intent object
                    if payment_intent_id:
                        if isinstance(payment_intent_id, str):
                            payment_intent_obj = self.get_payment_intent_details(payment_intent_id)
                        else:
                            payment_intent_obj = payment_intent_id
                    
                    # Get customer details
                    customer_details = session.get('customer_details', {})
                    shipping_details = customer_details.get('address', {})
                    
                    # Get payment method
                    payment_method_types = session.get('payment_method_types', [])
                    payment_method_type = payment_method_types[0] if payment_method_types else None
                    
                    # Calculate fees and net amount
                    amount_total = session.get('amount_total', 0) or 0
                    amount_received = None
                    application_fee_amount = None
                    refund_amount = None
                    refund_date = None
                    ip_address = None
                    user_agent = None
                    
                    if payment_intent_obj:
                        # Initialize amount_received with amount_total as fallback
                        amount_received = amount_total
                        
                        charges = payment_intent_obj.get('charges', {}).get('data', [])
                        if charges:
                            charge = charges[0]
                            amount_received = charge.get('amount_received', amount_total)
                            balance_transaction_ref = charge.get('balance_transaction')
                            
                            # Get IP and user agent from payment intent (best-effort placeholders)
                            payment_method_details = charge.get('payment_method_details', {})
                            if payment_method_details:
                                card = payment_method_details.get('card', {})
                                ip_address = charge.get('billing_details', {}).get('address', {})
                            
                            # balance_transaction can be an ID (str) or an expanded object (dict)
                            if isinstance(balance_transaction_ref, dict):
                                # Fee is in cents from Stripe, we'll convert later
                                application_fee_amount = balance_transaction_ref.get('fee', 0)
                                net_amount_stripe = balance_transaction_ref.get('net', amount_total)
                                # Check for refunds
                                if balance_transaction_ref.get('type') == 'refund':
                                    refund_amount = Decimal(balance_transaction_ref.get('amount', 0)) / 100
                                    refund_date = datetime.fromtimestamp(balance_transaction_ref.get('created', 0))
                            elif balance_transaction_ref:
                                try:
                                    balance_transaction = self.stripe_client.BalanceTransaction.retrieve(
                                        balance_transaction_ref
                                    )
                                    # Fee is in cents from Stripe, we'll convert later
                                    application_fee_amount = balance_transaction.get('fee', 0)
                                    net_amount_stripe = balance_transaction.get('net', amount_total)
                                    # Check for refunds
                                    if balance_transaction.get('type') == 'refund':
                                        refund_amount = Decimal(balance_transaction.get('amount', 0)) / 100
                                        refund_date = datetime.fromtimestamp(balance_transaction.get('created', 0))
                                except Exception as e:
                                    print(f"Error retrieving balance transaction {balance_transaction_ref}: {e}")
                                    application_fee_amount = None
                        
                        # If we still don't have fees, try to get them from the payment intent's latest_charge
                        # This can happen for payments that are still pending or when charges.data is empty
                        if not application_fee_amount or application_fee_amount == 0:
                            latest_charge_id = payment_intent_obj.get('latest_charge')
                            if latest_charge_id:
                                try:
                                    if isinstance(latest_charge_id, str):
                                        charge_detail = self.stripe_client.Charge.retrieve(
                                            latest_charge_id,
                                            expand=['balance_transaction']
                                        )
                                    else:
                                        charge_detail = latest_charge_id
                                    
                                    # Update amount_received if we have it
                                    if charge_detail.get('amount_received'):
                                        amount_received = charge_detail.get('amount_received')
                                    
                                    bt = charge_detail.get('balance_transaction')
                                    if isinstance(bt, dict):
                                        application_fee_amount = bt.get('fee', 0)
                                    elif bt:
                                        balance_transaction = self.stripe_client.BalanceTransaction.retrieve(bt)
                                        application_fee_amount = balance_transaction.get('fee', 0)
                                except Exception as e:
                                    print(f"Error retrieving charge details for fees: {e}")
                                    import traceback
                                    traceback.print_exc()
                        
                        # Check for refunds in payment intent
                        if payment_intent_obj.get('refunds'):
                            refunds = payment_intent_obj.get('refunds', {}).get('data', [])
                            if refunds:
                                total_refund = sum(refund.get('amount', 0) for refund in refunds)
                                refund_amount = Decimal(total_refund) / 100
                                if refunds:
                                    latest_refund = refunds[0]
                                    refund_date = datetime.fromtimestamp(latest_refund.get('created', 0))
                    
                    net_amount = None
                    if amount_received and application_fee_amount:
                        net_amount = Decimal(amount_received) / 100 - Decimal(application_fee_amount) / 100
                    elif amount_received:
                        net_amount = Decimal(amount_received) / 100
                    
                    # Adjust net amount for refunds
                    if refund_amount:
                        net_amount = (net_amount or Decimal(amount_total) / 100) - refund_amount
                    
                    payment_info = StripePaymentInfo(
                        session_id=session_id,
                        payment_intent_id=payment_intent_obj.get('id') if payment_intent_obj else None,
                        amount=Decimal(amount_total) / 100,
                        currency=session.get('currency', 'eur'),
                        status=session.get('payment_status', 'unknown'),
                        payment_method_type=payment_method_type,
                        payment_method_brand=None,
                        payment_method_last4=None,
                        payment_date=datetime.fromtimestamp(session.get('created', created_at.timestamp())),
                        amount_received=Decimal(amount_received) / 100 if amount_received else None,
                        application_fee_amount=Decimal(application_fee_amount) / 100 if application_fee_amount else None,
                        net_amount=net_amount,
                        customer_country=shipping_details.get('country'),
                        customer_email=customer_details.get('email'),
                        refund_amount=refund_amount,
                        refund_date=refund_date,
                        ip_address=ip_address,
                        user_agent=user_agent
                    )
            
            # Check for payment intent ID in metadata
            payment_intent_id = None
            if not payment_info and transaction_metadata:
                if "stripe_payment_intent:" in transaction_metadata:
                    payment_intent_id = transaction_metadata.split("stripe_payment_intent:")[1].split(",")[0].strip()
                elif transaction_metadata.startswith("pi_"):
                    # Direct payment intent ID format
                    payment_intent_id = transaction_metadata.split()[0].strip()
                    if not payment_intent_id.startswith("pi_"):
                        payment_intent_id = None
            
            if not payment_info and payment_intent_id:
                payment_intent = self.get_payment_intent_details(payment_intent_id)
                
                if payment_intent:
                    amount = payment_intent.get('amount', 0)
                    amount_received = amount
                    
                    charges = payment_intent.get('charges', {}).get('data', [])
                    charge = charges[0] if charges else {}
                    
                    # Get balance transaction for fees from charges if available
                    balance_transaction_ref = charge.get('balance_transaction')
                    application_fee_amount = None
                    if isinstance(balance_transaction_ref, dict):
                        # Fee is in cents from Stripe, we'll convert later
                        application_fee_amount = balance_transaction_ref.get('fee', 0)
                        amount_received = charge.get('amount_received', amount)
                    elif balance_transaction_ref:
                        try:
                            balance_transaction = self.stripe_client.BalanceTransaction.retrieve(
                                balance_transaction_ref
                            )
                            # Fee is in cents from Stripe, we'll convert later
                            application_fee_amount = balance_transaction.get('fee', 0)
                            amount_received = charge.get('amount_received', amount)
                        except Exception as e:
                            print(f"Error retrieving balance transaction {balance_transaction_ref}: {e}")
                            application_fee_amount = None
                    
                    # If we still don't have fees or charges is empty, try to get them from the payment intent's latest_charge
                    if not application_fee_amount or application_fee_amount == 0 or not charges:
                        latest_charge_id = payment_intent.get('latest_charge')
                        if latest_charge_id:
                            try:
                                if isinstance(latest_charge_id, str):
                                    charge_detail = self.stripe_client.Charge.retrieve(
                                        latest_charge_id,
                                        expand=['balance_transaction']
                                    )
                                else:
                                    charge_detail = latest_charge_id
                                
                                # Update amount_received if we have it
                                if charge_detail.get('amount_received'):
                                    amount_received = charge_detail.get('amount_received')
                                
                                bt = charge_detail.get('balance_transaction')
                                if isinstance(bt, dict):
                                    application_fee_amount = bt.get('fee', 0)
                                elif bt:
                                    balance_transaction = self.stripe_client.BalanceTransaction.retrieve(bt)
                                    application_fee_amount = balance_transaction.get('fee', 0)
                            except Exception as e:
                                print(f"Error retrieving charge details for fees: {e}")
                                import traceback
                                traceback.print_exc()
                    net_amount = None
                    if amount_received and application_fee_amount:
                        net_amount = Decimal(amount_received) / 100 - Decimal(application_fee_amount) / 100
                    elif amount_received:
                        net_amount = Decimal(amount_received) / 100
                    
                    payment_method = payment_intent.get('payment_method')
                    payment_method_type = None
                    if payment_method:
                        pm = self.stripe_client.PaymentMethod.retrieve(payment_method)
                        payment_method_type = pm.get('type')
                    
                    payment_info = StripePaymentInfo(
                        payment_intent_id=payment_intent_id,
                        amount=Decimal(amount) / 100,
                        currency=payment_intent.get('currency', 'eur'),
                        status=payment_intent.get('status', 'unknown'),
                        payment_method_type=payment_method_type,
                        payment_method_brand=None,
                        payment_method_last4=None,
                        payment_date=datetime.fromtimestamp(payment_intent.get('created', created_at.timestamp())),
                        amount_received=Decimal(amount_received) / 100 if amount_received else None,
                        application_fee_amount=Decimal(application_fee_amount) / 100 if application_fee_amount else None,
                        net_amount=net_amount,
                        customer_country=None,
                        customer_email=payment_intent.get('receipt_email'),
                        refund_amount=None,
                        refund_date=None,
                        ip_address=None,
                        user_agent=None
                    )
            
            # If we still don't have payment_info and we have user_email, try alternative search
            if not payment_info and user_email:
                session = self.find_stripe_session_by_email_and_date(
                    email=user_email,
                    transaction_date=created_at,
                    time_window_hours=48
                )
                
                if session:
                    # Extract payment info from the found session
                    session_id = session.get('id')
                    payment_intent_id = session.get('payment_intent')
                    payment_intent_obj = None
                    
                    if payment_intent_id:
                        if isinstance(payment_intent_id, str):
                            payment_intent_obj = self.get_payment_intent_details(payment_intent_id)
                        else:
                            payment_intent_obj = payment_intent_id
                    
                    customer_details = session.get('customer_details', {})
                    shipping_details = customer_details.get('address', {})
                    payment_method_types = session.get('payment_method_types', [])
                    payment_method_type = payment_method_types[0] if payment_method_types else None
                    
                    amount_total = session.get('amount_total', 0) or 0
                    amount_received = amount_total
                    application_fee_amount = None
                    
                    if payment_intent_obj:
                        amount_received = amount_total
                        charges = payment_intent_obj.get('charges', {}).get('data', [])
                        if charges:
                            charge = charges[0]
                            amount_received = charge.get('amount_received', amount_total)
                            balance_transaction_ref = charge.get('balance_transaction')
                            
                            if isinstance(balance_transaction_ref, dict):
                                application_fee_amount = balance_transaction_ref.get('fee', 0)
                            elif balance_transaction_ref:
                                try:
                                    balance_transaction = self.stripe_client.BalanceTransaction.retrieve(balance_transaction_ref)
                                    application_fee_amount = balance_transaction.get('fee', 0)
                                except Exception as e:
                                    print(f"Error retrieving balance transaction in alternative search: {e}")
                    
                    net_amount = None
                    if amount_received and application_fee_amount:
                        net_amount = Decimal(amount_received) / 100 - Decimal(application_fee_amount) / 100
                    elif amount_received:
                        net_amount = Decimal(amount_received) / 100
                    
                    payment_info = StripePaymentInfo(
                        session_id=session_id,
                        payment_intent_id=payment_intent_obj.get('id') if payment_intent_obj else None,
                        amount=Decimal(amount_total) / 100,
                        currency=session.get('currency', 'eur'),
                        status=session.get('payment_status', 'unknown'),
                        payment_method_type=payment_method_type,
                        payment_method_brand=None,
                        payment_method_last4=None,
                        payment_date=datetime.fromtimestamp(session.get('created', created_at.timestamp())),
                        amount_received=Decimal(amount_received) / 100 if amount_received else None,
                        application_fee_amount=Decimal(application_fee_amount) / 100 if application_fee_amount else None,
                        net_amount=net_amount,
                        customer_country=shipping_details.get('country'),
                        customer_email=customer_details.get('email') or user_email,
                        refund_amount=None,
                        refund_date=None,
                        ip_address=None,
                        user_agent=None
                    )
            
            return payment_info
            
        except Exception as e:
            print(f"Error extracting Stripe payment info: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_all_stripe_charges(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get all Stripe charges directly from Stripe API.
        
        Args:
            limit: Maximum number of charges to retrieve
            
        Returns:
            List of charge dictionaries with payment info
        """
        if not self.stripe_client:
            return []
        
        try:
            charges = self.stripe_client.Charge.list(
                limit=limit,
                expand=['data.balance_transaction', 'data.payment_intent', 'data.customer']
            )
            
            result = []
            for charge in charges.data:
                # Get balance transaction for fees
                bt = charge.get('balance_transaction')
                if isinstance(bt, str):
                    bt = self.stripe_client.BalanceTransaction.retrieve(bt)
                
                application_fee_amount = bt.get('fee', 0) if bt else 0
                amount_received = charge.get('amount_received', charge.get('amount', 0))
                net_amount = (amount_received - application_fee_amount) / 100 if amount_received and application_fee_amount else None
                
                # Get payment intent if available
                payment_intent = charge.get('payment_intent')
                if isinstance(payment_intent, str):
                    payment_intent = self.stripe_client.PaymentIntent.retrieve(payment_intent)
                
                payment_info = StripePaymentInfo(
                    payment_intent_id=payment_intent.get('id') if payment_intent else None,
                    session_id=None,  # We don't have session info from charges directly
                    amount=Decimal(charge.get('amount', 0)) / 100,
                    currency=charge.get('currency', 'eur'),
                    status=charge.get('status', 'unknown'),
                    payment_method_type=charge.get('payment_method_details', {}).get('type') if charge.get('payment_method_details') else None,
                    payment_method_brand=charge.get('payment_method_details', {}).get('card', {}).get('brand') if charge.get('payment_method_details') and charge.get('payment_method_details', {}).get('card') else None,
                    payment_method_last4=charge.get('payment_method_details', {}).get('card', {}).get('last4') if charge.get('payment_method_details') and charge.get('payment_method_details', {}).get('card') else None,
                    payment_date=datetime.fromtimestamp(charge.get('created', 0)),
                    amount_received=Decimal(amount_received) / 100 if amount_received else None,
                    application_fee_amount=Decimal(application_fee_amount) / 100 if application_fee_amount else None,
                    net_amount=Decimal(net_amount) if net_amount else None,
                    customer_country=charge.get('billing_details', {}).get('address', {}).get('country') if charge.get('billing_details') else None,
                    customer_email=charge.get('billing_details', {}).get('email') if charge.get('billing_details') else None,
                    refund_amount=Decimal(charge.get('amount_refunded', 0)) / 100 if charge.get('amount_refunded') else None,
                    refund_date=datetime.fromtimestamp(charge.get('refunded', {}).get('created', 0)) if charge.get('refunded') else None,
                    ip_address=None,
                    user_agent=None
                )
                
                result.append({
                    'charge_id': charge.get('id'),
                    'payment_info': payment_info,
                    'created': charge.get('created', 0)
                })
            
            return result
        except Exception as e:
            print(f"Error retrieving Stripe charges: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_stripe_payment_intents(
        self,
        limit: int = 100,
        statuses: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get Stripe payment intents with detailed payment information.

        Args:
            limit: Maximum number of payment intents to retrieve (max 100)
            statuses: Optional list of PaymentIntent statuses to fetch

        Returns:
            List of dictionaries containing StripePaymentInfo and created timestamp
        """
        if not self.stripe_client:
            return []

        try:
            fetch_limit = max(1, min(limit, 100))
            desired_statuses = set(statuses) if statuses else None

            payment_intents = self.stripe_client.PaymentIntent.list(
                limit=fetch_limit,
                expand=[
                    'data.latest_charge',
                    'data.latest_charge.balance_transaction',
                    'data.charges.data.balance_transaction',
                    'data.customer'
                ]
            )

            results: Dict[str, Dict[str, Any]] = {}

            for intent in payment_intents.data:
                status = intent.get('status', 'unknown')
                if desired_statuses and status not in desired_statuses:
                    continue

                intent_id = intent.get('id')
                if not intent_id or intent_id in results:
                    continue

                amount_value = intent.get('amount', 0) or 0
                amount_decimal = Decimal(amount_value) / Decimal('100')
                currency = intent.get('currency', 'eur')
                created_ts = intent.get('created', 0) or 0
                payment_date = datetime.fromtimestamp(created_ts) if created_ts else datetime.utcnow()

                amount_received_value = intent.get('amount_received')
                amount_received_decimal = (
                    Decimal(amount_received_value) / Decimal('100')
                    if amount_received_value is not None
                    else None
                )

                payment_method_type = None
                payment_method_brand = None
                payment_method_last4 = None
                customer_email = intent.get('receipt_email')
                customer_country = None
                customer_name = None
                application_fee_decimal: Optional[Decimal] = Decimal('0')
                available_on_timestamp: Optional[int] = None
                refund_amount_decimal: Optional[Decimal] = None
                refund_date: Optional[datetime] = None

                charges = intent.get('charges', {}).get('data', []) or []
                latest_charge = intent.get('latest_charge')
                if not charges and latest_charge:
                    if isinstance(latest_charge, dict):
                        charges = [latest_charge]
                    else:
                        try:
                            retrieved_charge = self.stripe_client.Charge.retrieve(
                                latest_charge,
                                expand=['balance_transaction']
                            )
                            charges = [retrieved_charge]
                        except Exception:
                            charges = []
                if not charges:
                    try:
                        charge_list = self.stripe_client.Charge.list(
                            payment_intent=intent_id,
                            limit=1,
                            expand=['data.balance_transaction']
                        )
                        charges = charge_list.data or []
                    except Exception:
                        charges = []

                if charges:
                    charge = charges[0]

                    billing_details = charge.get('billing_details') or {}
                    if billing_details:
                        customer_name = billing_details.get('name') or customer_name
                        customer_email = customer_email or billing_details.get('email')
                        address = billing_details.get('address') or {}
                        customer_country = address.get('country')

                    payment_method_details = charge.get('payment_method_details') or {}
                    if payment_method_details:
                        payment_method_type = payment_method_details.get('type')
                        card_details = payment_method_details.get('card') or {}
                        payment_method_brand = card_details.get('brand')
                        payment_method_last4 = card_details.get('last4')

                    amount_received_charge = charge.get('amount_received')
                    if amount_received_charge is not None:
                        amount_received_decimal = Decimal(amount_received_charge) / Decimal('100')

                    balance_transaction = charge.get('balance_transaction')
                    fee_value = 0
                    if isinstance(balance_transaction, dict):
                        fee_value = balance_transaction.get('fee') or 0
                        available_on_timestamp = balance_transaction.get('available_on')
                    elif balance_transaction:
                        try:
                            bt_obj = self.stripe_client.BalanceTransaction.retrieve(balance_transaction)
                            fee_value = bt_obj.get('fee') or 0
                            available_on_timestamp = bt_obj.get('available_on')
                        except Exception:
                            fee_value = 0

                    application_fee_decimal = Decimal(fee_value) / Decimal('100')
                    if amount_received_decimal is None:
                        amount_received_charge = charge.get('amount_received')
                        if amount_received_charge is not None:
                            amount_received_decimal = Decimal(amount_received_charge) / Decimal('100')

                    amount_refunded_value = charge.get('amount_refunded', 0) or 0
                    if amount_refunded_value:
                        refund_amount_decimal = Decimal(amount_refunded_value) / Decimal('100')
                        refunds = charge.get('refunds', {}).get('data', []) or []
                        if refunds:
                            refund_date = datetime.fromtimestamp(refunds[0].get('created', 0))
                else:
                    payment_method_types = intent.get('payment_method_types') or []
                    if payment_method_types:
                        payment_method_type = payment_method_types[0]

                # Fallback to customer object if available
                customer_obj = intent.get('customer')
                if isinstance(customer_obj, str):
                    try:
                        customer_obj = self.stripe_client.Customer.retrieve(customer_obj)
                    except Exception:
                        customer_obj = None
                if isinstance(customer_obj, dict):
                    if not customer_name:
                        customer_name = customer_obj.get('name')
                    if not customer_email:
                        customer_email = customer_obj.get('email')
                    if not customer_country:
                        customer_address = customer_obj.get('address') or {}
                        customer_country = customer_address.get('country')

                if not payment_method_type:
                    payment_method_types = intent.get('payment_method_types') or []
                    if payment_method_types:
                        payment_method_type = payment_method_types[0]

                metadata = intent.get('metadata') or {}
                available_on_datetime = (
                    datetime.fromtimestamp(available_on_timestamp)
                    if available_on_timestamp
                    else None
                )

                net_amount_decimal: Optional[Decimal] = None
                if amount_received_decimal is not None:
                    net_amount_decimal = amount_received_decimal
                    if application_fee_decimal:
                        net_amount_decimal -= application_fee_decimal
                    if refund_amount_decimal:
                        net_amount_decimal -= refund_amount_decimal
                else:
                    net_amount_decimal = None

                payment_info = StripePaymentInfo(
                    payment_intent_id=intent_id,
                    session_id=None,
                    amount=amount_decimal,
                    currency=currency,
                    status=status,
                    payment_method_type=payment_method_type,
                    payment_method_brand=payment_method_brand,
                    payment_method_last4=payment_method_last4,
                    payment_date=payment_date,
                    amount_received=amount_received_decimal,
                    application_fee_amount=application_fee_decimal,
                    net_amount=net_amount_decimal,
                    available_at=available_on_datetime,
                    customer_country=customer_country,
                    customer_name=customer_name,
                    customer_email=customer_email,
                    refund_amount=refund_amount_decimal,
                    refund_date=refund_date,
                    ip_address=None,
                    user_agent=None
                )

                results[intent_id] = {
                    'payment_info': payment_info,
                    'created': created_ts,
                    'metadata': metadata
                }

            return list(results.values())
        except Exception as e:
            print(f"Error retrieving Stripe payment intents: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_stripe_checkout_sessions(
        self,
        limit: int = 100,
        statuses: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve Stripe checkout sessions to capture abandoned or canceled payments.

        Returns a list of dictionaries containing:
            - 'session': raw session data
            - 'metadata': session metadata
        """
        if not self.stripe_client:
            return []

        try:
            fetch_limit = max(1, min(limit, 100))
            desired_statuses = set(statuses) if statuses else None

            sessions = self.stripe_client.checkout.Session.list(
                limit=fetch_limit,
                expand=[
                    'data.payment_intent',
                    'data.customer'
                ]
            )

            results: List[Dict[str, Any]] = []

            for session in sessions.data:
                status = session.get('status') or session.get('payment_status') or 'unknown'
                if desired_statuses and status not in desired_statuses:
                    continue

                # Ensure we have lightweight payment_intent data if available
                payment_intent = session.get('payment_intent')
                if isinstance(payment_intent, str):
                    try:
                        payment_intent = self.stripe_client.PaymentIntent.retrieve(payment_intent)
                        session['payment_intent'] = payment_intent
                    except Exception:
                        payment_intent = None

                results.append({
                    'session': session,
                    'metadata': session.get('metadata') or {}
                })

            return results
        except Exception as e:
            print(f"Error retrieving checkout sessions: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_accounting_data(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get accounting data including transactions and summary.
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            Dictionary with summary and transactions
        """
        fetch_limit = max(1, min(skip + limit if limit else 100, 100))
        statuses = [
            'succeeded',
            'processing',
            'requires_capture',
            'requires_confirmation',
            'requires_action',
            'requires_payment_method',
            'canceled'
        ]
        stripe_transactions = self.get_stripe_payment_intents(limit=fetch_limit, statuses=statuses)

        # Include checkout sessions for pending/canceled carts (e.g., abandoned)
        session_statuses = [
            'open',
            'expired',
            'complete'
        ]
        stripe_sessions = self.get_stripe_checkout_sessions(limit=fetch_limit, statuses=session_statuses)

        existing_intent_ids = {
            tx['payment_info'].payment_intent_id
            for tx in stripe_transactions
            if tx.get('payment_info') and tx['payment_info'].payment_intent_id
        }

        for session_data in stripe_sessions:
            session = session_data.get('session') or {}
            metadata = session_data.get('metadata') or {}

            payment_intent_obj = session.get('payment_intent')
            payment_intent_id: Optional[str] = None
            if isinstance(payment_intent_obj, str):
                payment_intent_id = payment_intent_obj
            elif isinstance(payment_intent_obj, dict):
                payment_intent_id = payment_intent_obj.get('id')

            if payment_intent_id and payment_intent_id in existing_intent_ids:
                continue

            amount_total = session.get('amount_total') or session.get('amount_subtotal') or 0
            amount_decimal = Decimal(amount_total) / Decimal('100') if amount_total else Decimal('0')
            created_ts = session.get('created', 0) or 0
            payment_date = datetime.fromtimestamp(created_ts) if created_ts else datetime.utcnow()

            session_status = session.get('payment_status') or session.get('status') or 'open'

            customer_details = session.get('customer_details') or {}
            customer_email = customer_details.get('email')
            customer_name = customer_details.get('name')
            address = customer_details.get('address') or {}
            customer_country = address.get('country')

            payment_info = StripePaymentInfo(
                payment_intent_id=payment_intent_id,
                session_id=session.get('id'),
                amount=amount_decimal,
                currency=session.get('currency', 'eur'),
                status=session_status,
                payment_method_type=None,
                payment_method_brand=None,
                payment_method_last4=None,
                payment_date=payment_date,
                amount_received=None,
                application_fee_amount=None,
                net_amount=None,
                available_at=None,
                customer_country=customer_country,
                customer_name=customer_name,
                customer_email=customer_email,
                refund_amount=None,
                refund_date=None,
                ip_address=None,
                user_agent=None
            )

            stripe_transactions.append({
                'payment_info': payment_info,
                'created': created_ts,
                'metadata': metadata
            })

            if payment_intent_id:
                existing_intent_ids.add(payment_intent_id)

        transactions: List[CreditPurchaseTransaction] = []
        total_paid = Decimal("0")
        total_refunded = Decimal("0")
        total_stripe_fees = Decimal("0")

        paid_statuses = {"succeeded", "processing", "requires_capture"}

        for transaction_data in stripe_transactions:
            payment_info = transaction_data.get('payment_info')
            if not payment_info:
                continue

            metadata = transaction_data.get('metadata') or {}

            metadata_user_id = metadata.get('user_id') if isinstance(metadata, dict) else None
            metadata_customer_name = metadata.get('customer_name') if isinstance(metadata, dict) else None
            metadata_customer_email = metadata.get('customer_email') if isinstance(metadata, dict) else None
            db_user: Optional[User] = None
            if metadata_user_id:
                try:
                    db_user = db.query(User).filter(User.id == int(metadata_user_id)).first()
                except Exception:
                    db_user = None

            if not db_user and payment_info.customer_email:
                db_user = db.query(User).filter(User.email == payment_info.customer_email).first()

            user_id = db_user.id if db_user else 0
            resolved_customer_name = (
                db_user.name if db_user else
                payment_info.customer_name or
                metadata_customer_name or
                payment_info.customer_email or
                "Client Stripe"
            )
            resolved_customer_email = (
                db_user.email if db_user else
                payment_info.customer_email or
                metadata_customer_email or
                "Unknown"
            )

            user_name = resolved_customer_name
            user_email = resolved_customer_email

            credits_from_metadata = 0
            if isinstance(metadata, dict):
                credits_value = metadata.get('credits')
                if credits_value is not None:
                    try:
                        credits_from_metadata = int(credits_value)
                    except (TypeError, ValueError):
                        credits_from_metadata = 0

            updated_payment_info = payment_info.copy(update={
                'customer_name': resolved_customer_name,
                'customer_email': resolved_customer_email if resolved_customer_email != "Unknown" else None
            })

            credits_available_date = updated_payment_info.payment_date
            euros_amount = updated_payment_info.amount

            credits_amount = credits_from_metadata

            transactions.append(CreditPurchaseTransaction(
                transaction_id=0,
                user_id=user_id,
                user_name=user_name,
                user_email=user_email,
                credits_amount=credits_amount,
                credits_available_date=credits_available_date,
                payment_info=updated_payment_info,
                euros_amount=euros_amount,
                description=f"Stripe payment intent {updated_payment_info.payment_intent_id}"
            ))

            if updated_payment_info.status in paid_statuses:
                if updated_payment_info.amount_received is not None:
                    total_paid += updated_payment_info.amount_received
                elif updated_payment_info.amount is not None:
                    total_paid += updated_payment_info.amount

                if updated_payment_info.application_fee_amount is not None:
                    total_stripe_fees += updated_payment_info.application_fee_amount

            if updated_payment_info.refund_amount:
                total_refunded += updated_payment_info.refund_amount

        transactions.sort(key=lambda x: x.payment_info.payment_date, reverse=True)
        paginated_transactions = transactions[skip:skip + limit]

        available_balance = self.get_stripe_balance()
        total_transactions = len(transactions)

        summary = AccountingSummary(
            total_paid=total_paid,
            total_refunded=total_refunded,
            total_stripe_fees=total_stripe_fees,
            net_total=total_paid - total_refunded - total_stripe_fees,
            total_transactions=total_transactions,
            available_balance=available_balance
        )

        return {
            "summary": summary,
            "transactions": paginated_transactions
        }


# Singleton instance
accounting_service = AccountingService()

