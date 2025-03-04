from django.shortcuts import render, redirect, get_object_or_404
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg
from django.http import JsonResponse
from .models import Cart, CartItem, Order, OrderItem, Review
from django.conf import settings
from restaurants.models import Restaurant, MenuItem
from core.models import Address
from .forms import CartItemForm, OrderForm, ReviewForm, AddressForm, CustomerProfileForm
from payments.utils import create_payment_intent
import stripe

@login_required
def dashboard(request):
    """Customer dashboard with quick links and order status"""
    
    # Get active orders
    active_orders = Order.objects.filter(
        customer=request.user,
        status__in=['pending', 'confirmed', 'preparing', 'ready_for_pickup', 'out_for_delivery']
    ).order_by('-created_at')[:5]
    
    # Get recent orders
    recent_orders = Order.objects.filter(
        customer=request.user,
        status='delivered'
    ).order_by('-created_at')[:5]
    
    # Get favorite restaurants (based on order history)
    favorite_restaurants = Restaurant.objects.filter(
        orders__customer=request.user
    ).distinct().order_by('-average_rating')[:4]
    
    context = {
        'active_orders': active_orders,
        'recent_orders': recent_orders,
        'favorite_restaurants': favorite_restaurants,
    }
    
    return render(request, 'customers/dashboard.html', context)

@login_required
def restaurant_list(request):
    """List all restaurants with search and filter options"""
    
    query = request.GET.get('q', '')
    cuisine = request.GET.get('cuisine', '')
    
    restaurants = Restaurant.objects.filter(is_active=True)
    
    if query:
        restaurants = restaurants.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query) |
            Q(cuisine_type__icontains=query)
        )
    
    if cuisine:
        restaurants = restaurants.filter(cuisine_type__icontains=cuisine)
    
    # Get all available cuisine types for the filter
    cuisine_types = Restaurant.objects.values_list('cuisine_type', flat=True).distinct()
    
    context = {
        'restaurants': restaurants,
        'cuisine_types': cuisine_types,
        'query': query,
        'cuisine': cuisine,
    }
    
    return render(request, 'customers/restaurant_list.html', context)

@login_required
def restaurant_detail(request, restaurant_id):
    """Display restaurant details and menu"""
    
    restaurant = get_object_or_404(Restaurant, id=restaurant_id, is_active=True)
    
    # Get menu items grouped by category
    menu_items = MenuItem.objects.filter(restaurant=restaurant, is_available=True)
    
    # Group by category
    categories = {}
    for item in menu_items:
        category = item.get_category_display()
        if category not in categories:
            categories[category] = []
        categories[category].append(item)
    
    context = {
        'restaurant': restaurant,
        'categories': categories,
    }
    
    return render(request, 'customers/restaurant_detail.html', context)

@login_required
def add_to_cart(request, menu_item_id):
    """Add item to cart"""
    
    menu_item = get_object_or_404(MenuItem, id=menu_item_id, is_available=True)
    
    # Get or create customer cart
    cart, created = Cart.objects.get_or_create(customer=request.user)
    
    # Check if adding from different restaurant
    if cart.items.exists() and cart.restaurant != menu_item.restaurant:
        if request.POST.get('confirm_clear') == 'yes':
            cart.items.all().delete()
        else:
            return JsonResponse({
                'error': 'Items in cart from different restaurant',
                'current_restaurant': cart.restaurant.name,
                'new_restaurant': menu_item.restaurant.name,
            }, status=400)
    
    # Process the cart item form
    if request.method == 'POST':
        form = CartItemForm(request.POST)
        if form.is_valid():
            quantity = form.cleaned_data.get('quantity', 1)
            special_instructions = form.cleaned_data.get('special_instructions', '')
            
            # Check if item already in cart
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                menu_item=menu_item,
                defaults={
                    'quantity': quantity,
                    'special_instructions': special_instructions
                }
            )
            
            # If item already exists, update quantity
            if not created:
                cart_item.quantity += quantity
                cart_item.special_instructions = special_instructions
                cart_item.save()
            
            messages.success(request, f"{menu_item.name} added to your cart.")
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'cart_count': cart.item_count
                })
            
            return redirect('customers:restaurant_detail', restaurant_id=menu_item.restaurant.id)
    
    # Default to GET view with empty form
    form = CartItemForm(initial={'quantity': 1})
    
    context = {
        'menu_item': menu_item,
        'form': form,
    }
    
    return render(request, 'customers/add_to_cart.html', context)

@login_required
def clear_cart(request):
    """Clear cart contents"""
    
    cart = get_object_or_404(Cart, customer=request.user)
    
    if request.method == 'POST':
        cart.items.all().delete()
        messages.success(request, "Cart cleared successfully.")
    
    return redirect('customers:cart')

@login_required
def cart_view(request):
    """View cart contents"""
    
    cart, created = Cart.objects.get_or_create(customer=request.user)
    
    context = {
        'cart': cart,
        'cart_items': cart.items.all(),
        'total': cart.total_price,
    }
    
    return render(request, 'customers/cart.html', context)

@login_required
def remove_from_cart(request, cart_item_id):
    """Remove item from cart"""
    
    cart_item = get_object_or_404(CartItem, id=cart_item_id, cart__customer=request.user)
    cart_item.delete()
    
    messages.success(request, "Item removed from cart.")
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    
    return redirect('customers:cart')

@login_required
def update_cart_item(request, cart_item_id):
    """Update cart item quantity"""
    
    cart_item = get_object_or_404(CartItem, id=cart_item_id, cart__customer=request.user)
    
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        
        if quantity <= 0:
            cart_item.delete()
            messages.success(request, "Item removed from cart.")
        else:
            cart_item.quantity = quantity
            cart_item.save()
            messages.success(request, "Cart updated.")
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'subtotal': cart_item.subtotal if quantity > 0 else 0,
            'total': cart_item.cart.total_price,
        })
    
    return redirect('customers:cart')

@login_required
def checkout(request):
    """Checkout process"""
    publishable_key = settings.STRIPE_PUBLISHABLE_KEY
    cart = get_object_or_404(Cart, customer=request.user)
    
    if not cart.items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect('customers:restaurant_list')
    
    # Get customer addresses
    addresses = Address.objects.filter(user=request.user)
    default_address = addresses.filter(is_default=True).first()
    
    # Calculate order details
    restaurant = cart.restaurant
    
    if not restaurant:
        messages.error(request, "There was an error with your cart. Please try again.")
        return redirect('customers:cart')
    
    subtotal = cart.total_price
    delivery_fee = restaurant.delivery_fee
    tax_rate = Decimal(0.1 ) # 10% tax rate (would normally be configured)
    tax_amount = subtotal * tax_rate
    total = subtotal + delivery_fee + tax_amount
    
    if request.method == 'POST':
        order_form = OrderForm(request.POST)
        address_form = AddressForm(request.POST)
        
        # Process order
        if order_form.is_valid():
            # Create new address or use existing
            use_existing_address = request.POST.get('use_existing_address')
            
            if use_existing_address:
                delivery_address = get_object_or_404(Address, id=use_existing_address, user=request.user)
            elif address_form.is_valid():
                delivery_address = address_form.save(commit=False)
                delivery_address.user = request.user
                delivery_address.save()
            else:
                # Address form has errors
                context = {
                    'cart': cart,
                    'addresses': addresses,
                    'default_address': default_address,
                    'order_form': order_form,
                    'address_form': address_form,
                    'subtotal': subtotal,
                    'delivery_fee': delivery_fee,
                    'tax_amount': tax_amount,
                    'total': total,
                }
                return render(request, 'customers/checkout.html', context)
            
            # Create order
            order = Order.objects.create(
                customer=request.user,
                restaurant=restaurant,
                delivery_address=delivery_address,
                total_amount=subtotal,
                delivery_fee=delivery_fee,
                tax_amount=tax_amount,
                special_instructions=order_form.cleaned_data.get('special_instructions', ''),
            )
            
            # Add order items
            for cart_item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    menu_item=cart_item.menu_item,
                    quantity=cart_item.quantity,
                    price=cart_item.menu_item.price,
                    special_instructions=cart_item.special_instructions,
                )
            
            # Create payment intent
            payment_intent = create_payment_intent(order)
            order.stripe_payment_intent_id = payment_intent.id
            order.save()
            
            # Clear cart after successful order
            cart.items.all().delete()
            
            return redirect('payments:process', order_id=order.id)
    else:
        order_form = OrderForm()
        address_form = AddressForm()
    
    context = {
        'cart': cart,
        'addresses': addresses,
        'default_address': default_address,
        'order_form': order_form,
        'address_form': address_form,
        'subtotal': subtotal,
        'delivery_fee': delivery_fee,
        'tax_amount': tax_amount,
        'total': total,
    }
    
    return render(request, 'customers/checkout.html', context)

@login_required
def order_list(request):
    """List all customer orders"""
    
    orders = Order.objects.filter(customer=request.user).order_by('-created_at')
    
    context = {
        'orders': orders,
    }
    
    return render(request, 'customers/order_list.html', context)

@login_required
def order_detail(request, order_id):
    """Show order details"""
    
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    review = Review.objects.filter(order=order).first()
    
    # Handle review submission
    if request.method == 'POST' and not review:
        review_form = ReviewForm(request.POST)
        if review_form.is_valid():
            review = review_form.save(commit=False)
            review.customer = request.user
            review.restaurant = order.restaurant
            review.order = order
            review.save()
            
            # Update restaurant rating
            restaurant = order.restaurant
            avg_rating = Review.objects.filter(restaurant=restaurant).aggregate(Avg('rating'))['rating__avg']
            restaurant.average_rating = avg_rating
            restaurant.save()
            
            messages.success(request, "Thank you for your review!")
            return redirect('customers:order_detail', order_id=order.id)
    else:
        review_form = ReviewForm()
    
    context = {
        'order': order,
        'order_items': order.items.all(),
        'review': review,
        'review_form': review_form,
    }
    
    return render(request, 'customers/order_detail.html', context)

@login_required
def customer_profile(request):
    """Customer profile view and edit"""
    
    if request.method == 'POST':
        user_form = CustomerProfileForm(request.POST, request.FILES, instance=request.user)
        if user_form.is_valid():
            user_form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('customers:profile')
    else:
        user_form = CustomerProfileForm(instance=request.user)
    
    # Get addresses
    addresses = Address.objects.filter(user=request.user)
    
    context = {
        'user_form': user_form,
        'addresses': addresses,
    }
    
    return render(request, 'customers/profile.html', context)
@login_required
def clear_cart(request):
    """Clear cart contents"""
    cart = get_object_or_404(Cart, customer=request.user)
    
    if request.method == 'POST':
        cart.items.all().delete()
        messages.success(request, "Cart cleared successfully.")
    
    return redirect('customers:cart')
def checkout_view(request):
    if request.method == 'POST':
        print("POST request received")
        print(request.POST)  # Print form data
        # Rest of your code
@login_required
def dashboard(request):
    """Customer dashboard with quick links and order status"""
    
    # Get active orders
    active_orders = Order.objects.filter(
        customer=request.user,
        status__in=['pending', 'confirmed', 'preparing', 'ready_for_pickup', 'out_for_delivery']
    ).order_by('-created_at')[:5]
    
    # Get recent orders
    recent_orders = Order.objects.filter(
        customer=request.user,
        status='delivered'
    ).order_by('-created_at')[:5]
    
    # Get favorite restaurants (based on order history)
    favorite_restaurants = Restaurant.objects.filter(
        orders__customer=request.user
    ).distinct().order_by('-average_rating')[:4]
    
    # If no favorites yet, show top rated restaurants
    if not favorite_restaurants.exists():
        favorite_restaurants = Restaurant.objects.filter(
            is_active=True
        ).order_by('-average_rating')[:4]
    
    context = {
        'active_orders': active_orders,
        'recent_orders': recent_orders,
        'favorite_restaurants': favorite_restaurants,
    }
    
    return render(request, 'customers/dashboard.html', context)       