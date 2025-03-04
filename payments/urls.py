from django.urls import path
from . import views

urlpatterns = [
    path('process/<int:order_id>/', views.process_payment, name='process'),
    path('complete/<int:order_id>/', views.payment_complete, name='complete'),
    path('cancel/<int:order_id>/', views.payment_cancel, name='cancel'),
    path('webhook/', views.stripe_webhook, name='webhook'),
]