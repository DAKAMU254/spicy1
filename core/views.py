from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import CustomUserCreationForm, CustomAuthenticationForm
from .models import User
from restaurants.models import Restaurant


def landing_page(request):
    """Landing page view"""
    restaurants = []  # Define the restaurants variable
    return render(request, 'landing.html', {'restaurants': restaurants})

def register_view(request):
    """User registration view"""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome, {user.username}! Your account has been created successfully.")
            
            # Redirect based on user type
            if user.user_type == 'customer':
                return redirect('customers:dashboard')
            elif user.user_type == 'restaurant':
                return redirect('restaurants:dashboard')
            elif user.user_type == 'delivery':
                return redirect('delivery:dashboard')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'register.html', {'form': form})

def login_view(request):
    """User login view"""
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome back, {user.username}!")
                
                # Redirect based on user type
                if user.user_type == 'customer':
                    return redirect('customers:dashboard')
                elif user.user_type == 'restaurant':
                    return redirect('restaurants:dashboard')
                elif user.user_type == 'delivery':
                    return redirect('delivery:dashboard')
                elif user.user_type == 'admin':
                    return redirect('admin:index')
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'login.html', {'form': form})

@login_required
def logout_view(request):
    """User logout view"""
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('landing')

@login_required
def profile_view(request):
    """User profile view"""
    return render(request, 'profile.html')
def landing_page(request):
    """Landing page view"""
    # Get featured restaurants (e.g., highest rated)
    featured_restaurants = Restaurant.objects.filter(
        is_active=True
    ).order_by('-average_rating')[:3]
    
    context = {
        'featured_restaurants': featured_restaurants,
    }
    
    return render(request, 'landing.html', context)