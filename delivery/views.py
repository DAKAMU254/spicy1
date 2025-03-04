from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from .models import DeliveryProfile
from .forms import DeliveryProfileForm, LocationUpdateForm
from customers.models import Order
from core.decorators import delivery_required

@login_required
@delivery_required
def dashboard(request):
    """Delivery person dashboard"""
    
    # Get or create delivery profile
    profile, created = DeliveryProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = DeliveryProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('delivery:dashboard')
    else:
        form = DeliveryProfileForm(instance=profile)
    
    context = {
        'form': form,
        'profile': profile,
    }
    
    return render(request, 'delivery/profile.html', context)

@login_required
@delivery_required
def toggle_availability(request):
    """Toggle delivery person availability"""
    
    profile = get_object_or_404(DeliveryProfile, user=request.user)
    
    if request.method == 'POST':
        profile.is_available = not profile.is_available
        profile.save()
        
        status = "available" if profile.is_available else "unavailable"
        messages.success(request, f"You are now {status} for deliveries.")
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': profile.is_available})
    
    return redirect('delivery:dashboard')

@login_required
@delivery_required
def update_location(request):
    """Update delivery person location"""
    
    profile = get_object_or_404(DeliveryProfile, user=request.user)
    
    if request.method == 'POST':
        form = LocationUpdateForm(request.POST)
        if form.is_valid():
            profile.current_location_lat = form.cleaned_data['latitude']
            profile.current_location_lng = form.cleaned_data['longitude']
            profile.last_location_update = timezone.now()
            profile.save()
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
            
            messages.success(request, "Location updated successfully.")
            return redirect('delivery:dashboard')
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    
    return redirect('delivery:dashboard')
@login_required
@delivery_required
def active_deliveries(request):
    """View active deliveries"""
    
    profile = get_object_or_404(DeliveryProfile, user=request.user)
    
    # Get active deliveries
    active_deliveries = Order.objects.filter(
        delivery_person=request.user,
        status__in=['ready_for_pickup', 'out_for_delivery']
    ).order_by('updated_at')
    
    # Get available orders for pickup
    available_orders = Order.objects.filter(
        status='ready_for_pickup',
        delivery_person__isnull=True
    ).order_by('updated_at')
    
    context = {
        'profile': profile,
        'active_deliveries': active_deliveries,
        'available_orders': available_orders,
    }
    
    return render(request, 'delivery/active_deliveries.html', context)
@login_required
@delivery_required
def delivery_history(request):
    """View delivery history"""
    
    profile = get_object_or_404(DeliveryProfile, user=request.user)
    
    # Get completed deliveries
    completed_deliveries = Order.objects.filter(
        delivery_person=request.user,
        status='delivered'
    ).order_by('-updated_at')
    
    context = {
        'profile': profile,
        'completed_deliveries': completed_deliveries,
    }
    
    return render(request, 'delivery/delivery_history.html', context)
@login_required
@delivery_required
def order_detail(request, order_id):
    """View order details"""
    
    order = get_object_or_404(Order, id=order_id)
    
    # Check if user is assigned to this delivery or if it's an available order
    if order.delivery_person != request.user and order.delivery_person is not None:
        messages.error(request, "You are not authorized to view this order.")
        return redirect('delivery:dashboard')
    
    context = {
        'order': order,
        'order_items': order.items.all(),
    }
    
    return render(request, 'delivery/order_detail.html', context)
@login_required
@delivery_required
def update_order_status(request, order_id):
    """Update order status"""
    
    order = get_object_or_404(Order, id=order_id)
    
    # Check if user is assigned to this delivery
    if order.delivery_person != request.user:
        # If order is available for pickup, assign it to this delivery person
        if order.status == 'ready_for_pickup' and order.delivery_person is None:
            order.delivery_person = request.user
            order.save()
            messages.success(request, f"Order #{order.id} assigned to you.")
        else:
            messages.error(request, "You are not authorized to update this order.")
            return redirect('delivery:dashboard')
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        
        if new_status in ['out_for_delivery', 'delivered']:
            order.status = new_status
            
            # If delivered, set actual delivery time
            if new_status == 'delivered':
                order.actual_delivery_time = timezone.now()
            
            order.save()
            messages.success(request, f"Order #{order.id} status updated to {order.get_status_display()}.")
        else:
            messages.error(request, "Invalid status update.")
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    
    return redirect('delivery:order_detail', order_id=order.id)
@login_required
@delivery_required
def delivery_profile(request):
    """View and edit delivery profile"""
    
    profile, created = DeliveryProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = DeliveryProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('delivery:dashboard')
    else:
        form = DeliveryProfileForm(instance=profile)
    
    context = {
        'form': form,
        'profile': profile,
    }
    
    return render(request, 'delivery/profile.html', context)