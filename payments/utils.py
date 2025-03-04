import stripe
from django.conf import settings

# Set up Stripe API key
stripe.api_key = settings.STRIPE_SECRET_KEY

def create_payment_intent(order):
    """Create a Stripe payment intent for an order"""
    
    # Calculate total amount in cents (Stripe uses smallest currency unit)
    amount = int(order.order_total * 100)
    
    # Create payment intent
    intent = stripe.PaymentIntent.create(
        amount=amount,
        currency='usd',
        metadata={
            'order_id': order.id,
            'customer_id': order.customer.id,
            'customer_email': order.customer.email,
        }
    )
    
    return intent

def get_payment_intent(payment_intent_id):
    """Retrieve a payment intent from Stripe"""
    return stripe.PaymentIntent.retrieve(payment_intent_id)