from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from customers.models import Order
from .models import Payment
from .utils import create_payment_intent, get_payment_intent

import stripe
import json

# Set up Stripe API key
stripe.api_key = settings.STRIPE_SECRET_KEY

@login_required
def process_payment(request, order_id):
    """Process payment for an order"""
    
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    
    if order.payment_status == 'completed':
        messages.info(request, "This order has already been paid for.")
        return redirect('customers:order_detail', order_id=order.id)
    
    # Get or create payment intent
    if order.stripe_payment_intent_id:
        payment_intent = get_payment_intent(order.stripe_payment_intent_id)
    else:
        payment_intent = create_payment_intent(order)
        order.stripe_payment_intent_id = payment_intent.id
        order.save()
    
    # Calculate total amount
    total_amount = order.order_total
    
    context = {
        'order': order,
        'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
        'client_secret': payment_intent.client_secret,
        'total_amount': total_amount,
    }
    
    return render(request, 'payments/process.html', context)

@login_required
def payment_complete(request, order_id):
    """Handle successful payment"""
    
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    
    # Update order and create payment record
    if request.method == 'POST':
        payment_intent_id = request.POST.get('payment_intent_id')
        
        if payment_intent_id and payment_intent_id == order.stripe_payment_intent_id:
            # Verify payment status with Stripe
            payment_intent = get_payment_intent(payment_intent_id)
            
            if payment_intent.status == 'succeeded':
                # Update order
                order.payment_status = 'completed'
                order.status = 'confirmed'
                order.save()
                
                # Create payment record
                Payment.objects.create(
                    order=order,
                    amount=order.order_total,
                    transaction_id=payment_intent_id,
                    status='completed'
                )
                
                messages.success(request, "Payment successful! Your order has been confirmed.")
            else:
                messages.error(request, "Payment verification failed. Please contact support.")
    
    return redirect('customers:order_detail', order_id=order.id)

@login_required
def payment_cancel(request, order_id):
    """Handle cancelled payment"""
    
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    
    messages.warning(request, "Payment was cancelled. Your order has not been placed.")
    
    return redirect('customers:cart')

@csrf_exempt
def stripe_webhook(request):
    """Handle Stripe webhooks"""
    
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET
    payload = request.body
    
    try:
        event = None
        if webhook_secret:
            signature = request.headers.get('stripe-signature')
            event = stripe.Webhook.construct_event(
                payload, signature, webhook_secret
            )
        else:
            event = json.loads(payload)
        
        # Handle the event
        if event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            
            # Find the order
            try:
                order = Order.objects.get(stripe_payment_intent_id=payment_intent['id'])
                
                # Update order status
                if order.payment_status != 'completed':
                    order.payment_status = 'completed'
                    order.status = 'confirmed'
                    order.save()
                    
                    # Create payment record
                    Payment.objects.get_or_create(
                        order=order,
                        defaults={
                            'amount': order.order_total,
                            'transaction_id': payment_intent['id'],
                            'status': 'completed'
                        }
                    )
            except Order.DoesNotExist:
                # Log the error but return success to Stripe
                print(f"Order not found for payment_intent: {payment_intent['id']}")
        
        return HttpResponse(status=200)
    except Exception as e:
        return HttpResponse(content=str(e), status=400)
    