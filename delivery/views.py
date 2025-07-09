from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, Http404
from django.utils import timezone
from django.db import transaction
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from django.views.generic import ListView
from django.db.models import Q, Count
import logging

from .models import DeliveryProfile
from .forms import DeliveryProfileForm, LocationUpdateForm
from customers.models import Order
from core.decorators import delivery_required

logger = logging.getLogger(__name__)

# Constants
ORDERS_PER_PAGE = 10
AVAILABLE_ORDER_STATUSES = ['ready_for_pickup', 'out_for_delivery']
VALID_STATUS_TRANSITIONS = ['out_for_delivery', 'delivered']


class DeliveryProfileMixin:
    """Mixin to get or create delivery profile"""
    
    def get_delivery_profile(self):
        profile, created = DeliveryProfile.objects.get_or_create(user=self.request.user)
        if created:
            logger.info(f"Created new delivery profile for user {self.request.user.id}")
        return profile


@login_required
@delivery_required
def dashboard(request):
    """Enhanced delivery person dashboard with stats"""
    
    profile, created = DeliveryProfile.objects.get_or_create(user=request.user)
    
    # Get dashboard stats
    stats = {
        'active_deliveries': Order.objects.filter(
            delivery_person=request.user,
            status__in=AVAILABLE_ORDER_STATUSES
        ).count(),
        'completed_today': Order.objects.filter(
            delivery_person=request.user,
            status='delivered',
            actual_delivery_time__date=timezone.now().date()
        ).count(),
        'total_completed': Order.objects.filter(
            delivery_person=request.user,
            status='delivered'
        ).count(),
        'available_orders': Order.objects.filter(
            status='ready_for_pickup',
            delivery_person__isnull=True
        ).count(),
    }
    
    if request.method == 'POST':
        form = DeliveryProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('delivery:dashboard')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = DeliveryProfileForm(instance=profile)
    
    context = {
        'form': form,
        'profile': profile,
        'stats': stats,
    }
    
    return render(request, 'delivery/dashboard.html', context)


@login_required
@delivery_required
@require_POST
def toggle_availability(request):
    """Toggle delivery person availability with better error handling"""
    
    try:
        profile = get_object_or_404(DeliveryProfile, user=request.user)
        
        with transaction.atomic():
            old_status = profile.is_available
            profile.is_available = not profile.is_available
            profile.save()
            
            status_text = "available" if profile.is_available else "unavailable"
            message = f"You are now {status_text} for deliveries."
            
            # Log status change
            logger.info(f"User {request.user.id} changed availability: {old_status} -> {profile.is_available}")
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'status': profile.is_available,
                    'message': message
                })
            
            messages.success(request, message)
            
    except Exception as e:
        logger.error(f"Error toggling availability for user {request.user.id}: {str(e)}")
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': 'Unable to update availability. Please try again.'
            }, status=500)
        
        messages.error(request, "Unable to update availability. Please try again.")
    
    return redirect('delivery:dashboard')


@login_required
@delivery_required
@require_POST
def update_location(request):
    """Update delivery person location with validation"""
    
    profile = get_object_or_404(DeliveryProfile, user=request.user)
    
    form = LocationUpdateForm(request.POST)
    if form.is_valid():
        try:
            with transaction.atomic():
                profile.current_location_lat = form.cleaned_data['latitude']
                profile.current_location_lng = form.cleaned_data['longitude']
                profile.last_location_update = timezone.now()
                profile.save()
                
                logger.info(f"Location updated for user {request.user.id}")
                
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': 'Location updated successfully'
                    })
                
                messages.success(request, "Location updated successfully!")
                
        except Exception as e:
            logger.error(f"Error updating location for user {request.user.id}: {str(e)}")
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'Unable to update location'
                }, status=500)
            
            messages.error(request, "Unable to update location. Please try again.")
    else:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'errors': form.errors
            }, status=400)
        
        messages.error(request, "Invalid location data provided.")
    
    return redirect('delivery:dashboard')


@login_required
@delivery_required
def active_deliveries(request):
    """View active deliveries with pagination and filtering"""
    
    profile = get_object_or_404(DeliveryProfile, user=request.user)
    
    # Get active deliveries with related data
    active_deliveries = Order.objects.select_related(
        'customer', 'restaurant'
    ).prefetch_related('items').filter(
        delivery_person=request.user,
        status__in=AVAILABLE_ORDER_STATUSES
    ).order_by('created_at')
    
    # Get available orders for pickup with distance calculation if location available
    available_orders_query = Order.objects.select_related(
        'customer', 'restaurant'
    ).filter(
        status='ready_for_pickup',
        delivery_person__isnull=True
    ).order_by('created_at')
    
    # Pagination for available orders
    paginator = Paginator(available_orders_query, ORDERS_PER_PAGE)
    page_number = request.GET.get('page')
    available_orders = paginator.get_page(page_number)
    
    context = {
        'profile': profile,
        'active_deliveries': active_deliveries,
        'available_orders': available_orders,
        'has_location': bool(profile.current_location_lat and profile.current_location_lng),
    }
    
    return render(request, 'delivery/active_deliveries.html', context)


@login_required
@delivery_required
def delivery_history(request):
    """View delivery history with filtering and search"""
    
    profile = get_object_or_404(DeliveryProfile, user=request.user)
    
    # Base queryset
    deliveries = Order.objects.select_related(
        'customer', 'restaurant'
    ).filter(
        delivery_person=request.user,
        status='delivered'
    )
    
    # Search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        deliveries = deliveries.filter(
            Q(id__icontains=search_query) |
            Q(customer__email__icontains=search_query) |
            Q(restaurant__name__icontains=search_query)
        )
    
    # Date filtering
    date_filter = request.GET.get('date_filter')
    if date_filter == 'today':
        deliveries = deliveries.filter(actual_delivery_time__date=timezone.now().date())
    elif date_filter == 'week':
        week_ago = timezone.now() - timezone.timedelta(days=7)
        deliveries = deliveries.filter(actual_delivery_time__gte=week_ago)
    elif date_filter == 'month':
        month_ago = timezone.now() - timezone.timedelta(days=30)
        deliveries = deliveries.filter(actual_delivery_time__gte=month_ago)
    
    deliveries = deliveries.order_by('-actual_delivery_time')
    
    # Pagination
    paginator = Paginator(deliveries, ORDERS_PER_PAGE)
    page_number = request.GET.get('page')
    completed_deliveries = paginator.get_page(page_number)
    
    context = {
        'profile': profile,
        'completed_deliveries': completed_deliveries,
        'search_query': search_query,
        'date_filter': date_filter,
    }
    
    return render(request, 'delivery/delivery_history.html', context)


@login_required
@delivery_required
def order_detail(request, order_id):
    """Enhanced order details view"""
    
    try:
        order = Order.objects.select_related(
            'customer', 'restaurant', 'delivery_person'
        ).prefetch_related('items__menu_item').get(id=order_id)
    except Order.DoesNotExist:
        messages.error(request, "Order not found.")
        return redirect('delivery:dashboard')
    
    # Authorization check
    if (order.delivery_person != request.user and 
        order.delivery_person is not None and 
        order.status != 'ready_for_pickup'):
        messages.error(request, "You are not authorized to view this order.")
        return redirect('delivery:dashboard')
    
    # Calculate order totals
    order_total = sum(item.subtotal for item in order.items.all())
    
    context = {
        'order': order,
        'order_items': order.items.all(),
        'order_total': order_total,
        'can_update_status': order.delivery_person == request.user,
        'can_accept_order': (order.status == 'ready_for_pickup' and 
                           order.delivery_person is None),
    }
    
    return render(request, 'delivery/order_detail.html', context)


@login_required
@delivery_required
@require_POST
def update_order_status(request, order_id):
    """Enhanced order status update with validation"""
    
    try:
        order = get_object_or_404(Order, id=order_id)
        new_status = request.POST.get('status', '').strip()
        
        # Validate status
        if new_status not in VALID_STATUS_TRANSITIONS:
            messages.error(request, "Invalid status provided.")
            return _handle_response(request, order_id, success=False)
        
        with transaction.atomic():
            # Handle order assignment
            if order.delivery_person != request.user:
                if order.status == 'ready_for_pickup' and order.delivery_person is None:
                    order.delivery_person = request.user
                    order.save()
                    messages.success(request, f"Order #{order.id} assigned to you!")
                    logger.info(f"Order {order_id} assigned to user {request.user.id}")
                else:
                    messages.error(request, "You are not authorized to update this order.")
                    return _handle_response(request, order_id, success=False)
            
            # Update status
            old_status = order.status
            order.status = new_status
            
            # Set delivery time if completed
            if new_status == 'delivered':
                order.actual_delivery_time = timezone.now()
            
            order.save()
            
            status_display = order.get_status_display()
            message = f"Order #{order.id} status updated to {status_display}."
            messages.success(request, message)
            
            logger.info(f"Order {order_id} status changed from {old_status} to {new_status} by user {request.user.id}")
            
            return _handle_response(request, order_id, success=True, message=message)
            
    except Exception as e:
        logger.error(f"Error updating order {order_id} status: {str(e)}")
        messages.error(request, "Unable to update order status. Please try again.")
        return _handle_response(request, order_id, success=False)


def _handle_response(request, order_id, success=True, message=""):
    """Helper function to handle AJAX and regular responses"""
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': success,
            'message': message
        })
    
    if success:
        return redirect('delivery:order_detail', order_id=order_id)
    else:
        return redirect('delivery:dashboard')


@login_required
@delivery_required
def delivery_profile(request):
    """Consolidated profile view (consider removing if duplicate of dashboard)"""
    
    # This seems to duplicate dashboard functionality
    # Consider redirecting to dashboard instead
    return redirect('delivery:dashboard')