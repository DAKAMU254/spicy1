from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('active/', views.active_deliveries, name='active'),
    path('history/', views.delivery_history, name='history'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('orders/<int:order_id>/update-status/', views.update_order_status, name='update_order_status'),
    path('profile/', views.delivery_profile, name='profile'),
    path('availability/', views.toggle_availability, name='toggle_availability'),
    path('location/update/', views.update_location, name='update_location'),
]