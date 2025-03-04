from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta
from core.decorators import restaurant_required
from core.models import Address
from .models import Restaurant, MenuItem
from .forms import RestaurantForm, MenuItemForm
from customers.models import Order, Review, OrderItem

@login_required
@restaurant_required
def dashboard(request):
    """Restaurant dashboard with key metrics"""
    
    # Try to get existing restaurant
    try:
        restaurant = Restaurant.objects.get(manager=request.user)
    except Restaurant.DoesNotExist:
        # Create a new restaurant with default values
        current_time = timezone.now().time()  # ✅ Fixed issue here
        
        # First create an address for the restaurant
        address = Address.objects.create(
            user=request.user,
            address_line1="123 Restaurant St",
            city="Your City",
            state="Your State",
            postal_code="12345",
            is_default=True
        )

        # Then create the restaurant with all required fields
        restaurant = Restaurant.objects.create(
            manager=request.user,
            name=f"{request.user.first_name}'s Restaurant",
            description="Restaurant description",
            address=address,
            cuisine_type="Other",
            phone=request.user.phone_number or "000-000-0000",
            email=request.user.email,
            delivery_fee=3.99,
            min_order_amount=10.00,
            preparation_time=30,
            opening_time=current_time,
            closing_time=current_time,
        )

        messages.info(request, "Please complete your restaurant profile.")
        return redirect('restaurants:settings')

    # Get today's orders
    today = timezone.now().date()
    today_orders = Order.objects.filter(
        restaurant=restaurant,
        created_at__date=today
    )

    # Get key metrics
    pending_orders = today_orders.filter(status__in=['pending', 'confirmed', 'preparing']).count()
    completed_orders = today_orders.filter(status='delivered').count()
    cancelled_orders = today_orders.filter(status='cancelled').count()

    today_revenue = today_orders.filter(status='delivered').aggregate(Sum('total_amount'))['total_amount__sum'] or 0

    # Get recent orders
    recent_orders = Order.objects.filter(
        restaurant=restaurant
    ).order_by('-created_at')[:10]

    # Get recent reviews
    recent_reviews = Review.objects.filter(
        restaurant=restaurant
    ).order_by('-created_at')[:5]

    context = {
        'restaurant': restaurant,
        'pending_orders': pending_orders,
        'completed_orders': completed_orders,
        'cancelled_orders': cancelled_orders,
        'today_revenue': today_revenue,
        'recent_orders': recent_orders,
        'recent_reviews': recent_reviews,
    }

    return render(request, 'restaurants/dashboard.html', context)

@login_required
@restaurant_required
def menu_management(request):
    """Manage restaurant menu"""
    
    restaurant = get_object_or_404(Restaurant, manager=request.user)
    menu_items = MenuItem.objects.filter(restaurant=restaurant).order_by('category', 'name')
    
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
    
    return render(request, 'restaurants/menu_management.html', context)

@login_required
@restaurant_required
def add_menu_item(request):
    """Add a new menu item"""
    
    restaurant = get_object_or_404(Restaurant, manager=request.user)
    
    if request.method == 'POST':
        form = MenuItemForm(request.POST, request.FILES)
        if form.is_valid():
            menu_item = form.save(commit=False)
            menu_item.restaurant = restaurant
            menu_item.save()
            messages.success(request, f"{menu_item.name} added to your menu.")
            return redirect('restaurants:menu')
    else:
        form = MenuItemForm()
    
    context = {
        'form': form,
        'restaurant': restaurant,
        'action': 'Add',
    }
    
    return render(request, 'restaurants/menu_item_form.html', context)

@login_required
@restaurant_required
def edit_menu_item(request, item_id):
    """Edit an existing menu item"""
    
    restaurant = get_object_or_404(Restaurant, manager=request.user)
    menu_item = get_object_or_404(MenuItem, id=item_id, restaurant=restaurant)
    
    if request.method == 'POST':
        form = MenuItemForm(request.POST, request.FILES, instance=menu_item)
        if form.is_valid():
            form.save()
            messages.success(request, f"{menu_item.name} updated successfully.")
            return redirect('restaurants:menu')
    else:
        form = MenuItemForm(instance=menu_item)
    
    context = {
        'form': form,
        'restaurant': restaurant,
        'menu_item': menu_item,
        'action': 'Edit',
    }
    
    return render(request, 'restaurants/menu_item_form.html', context)

@login_required
@restaurant_required
def delete_menu_item(request, item_id):
    """Delete a menu item"""
    
    restaurant = get_object_or_404(Restaurant, manager=request.user)
    menu_item = get_object_or_404(MenuItem, id=item_id, restaurant=restaurant)
    
    if request.method == 'POST':
        menu_item.delete()
        messages.success(request, f"{menu_item.name} has been deleted.")
        return redirect('restaurants:menu')
    
    context = {
        'menu_item': menu_item,
        'restaurant': restaurant,
    }
    
    return render(request, 'restaurants/delete_menu_item.html', context)

@login_required
@restaurant_required
def order_management(request):
    """Manage restaurant orders"""
    
    restaurant = get_object_or_404(Restaurant, manager=request.user)
    
    # Filter orders by status if provided
    status_filter = request.GET.get('status', '')
    
    orders = Order.objects.filter(restaurant=restaurant)
    
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    # Group by status
    order_groups = {
        'pending': orders.filter(status='pending'),
        'confirmed': orders.filter(status='confirmed'),
        'preparing': orders.filter(status='preparing'),
        'ready_for_pickup': orders.filter(status='ready_for_pickup'),
        'out_for_delivery': orders.filter(status='out_for_delivery'),
        'delivered': orders.filter(status='delivered').order_by('-updated_at')[:10],
        'cancelled': orders.filter(status='cancelled').order_by('-updated_at')[:10],
    }
    
    context = {
        'restaurant': restaurant,
        'order_groups': order_groups,
        'status_filter': status_filter,
    }
    
    return render(request, 'restaurants/order_management.html', context)

@login_required
@restaurant_required
def order_detail(request, order_id):
    """View order details"""
    
    restaurant = get_object_or_404(Restaurant, manager=request.user)
    order = get_object_or_404(Order, id=order_id, restaurant=restaurant)
    
    context = {
        'restaurant': restaurant,
        'order': order,
        'order_items': order.items.all(),
    }
    
    return render(request, 'restaurants/order_detail.html', context)

@login_required
@restaurant_required
def update_order_status(request, order_id):
    """Update order status"""
    
    restaurant = get_object_or_404(Restaurant, manager=request.user)
    order = get_object_or_404(Order, id=order_id, restaurant=restaurant)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        
        if new_status in dict(Order.STATUS_CHOICES).keys():
            order.status = new_status
            order.save()
            messages.success(request, f"Order #{order.id} status updated to {order.get_status_display()}.")
        else:
            messages.error(request, "Invalid status.")
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    
    return redirect('restaurants:order_detail', order_id=order.id)

@login_required
@restaurant_required
def restaurant_settings(request):
    """Restaurant profile settings"""
    
    restaurant = get_object_or_404(Restaurant, manager=request.user)
    
    if request.method == 'POST':
        form = RestaurantForm(request.POST, request.FILES, instance=restaurant)
        if form.is_valid():
            form.save()
            messages.success(request, "Restaurant settings updated successfully.")
            return redirect('restaurants:dashboard')
    else:
        form = RestaurantForm(instance=restaurant)
    
    context = {
        'form': form,
        'restaurant': restaurant,
    }
    
    return render(request, 'restaurants/settings.html', context)

@login_required
@restaurant_required
def analytics(request):
    """Restaurant analytics and reporting"""
    
    restaurant = get_object_or_404(Restaurant, manager=request.user)
    
    # Date range filter
    days = int(request.GET.get('days', 30))
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Get orders in date range
    orders = Order.objects.filter(
        restaurant=restaurant,
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    )
    
    # Sales data
    delivered_orders = orders.filter(status='delivered')
    total_sales = delivered_orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    order_count = delivered_orders.count()
    average_order_value = total_sales / order_count if order_count else 0
    
    # Popular items
    popular_items = OrderItem.objects.filter(
        order__in=delivered_orders
    ).values('menu_item__name').annotate(
        count=Sum('quantity')
    ).order_by('-count')[:10]
    
    # Daily sales
    daily_sales = delivered_orders.values('created_at__date').annotate(
        total=Sum('total_amount'),
        count=Count('id')
    ).order_by('created_at__date')
    
    # Convert to list for chart data
    daily_sales_data = [
        {
            'date': item['created_at__date'].strftime('%Y-%m-%d'),
            'total': float(item['total']),
            'count': item['count']
        }
        for item in daily_sales
    ]
    
    context = {
        'restaurant': restaurant,
        'total_sales': total_sales,
        'order_count': order_count,
        'average_order_value': average_order_value,
        'popular_items': popular_items,
        'daily_sales_data': daily_sales_data,
        'days': days,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    return render(request, 'restaurants/analytics.html', context)