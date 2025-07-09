from django.db import models
from django.conf import settings
from customers.models import Order

class DeliveryProfile(models.Model):
    """Delivery person profile"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='delivery_profile')
    vehicle_type = models.CharField(max_length=50)
    vehicle_number = models.CharField(max_length=20, blank=True)
    license_number = models.CharField(max_length=20)
    is_available = models.BooleanField(default=False)
    current_location_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    current_location_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    last_location_update = models.DateTimeField(null=True, blank=True)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Delivery Profile: {self.user.username}"

class DeliveryReview(models.Model):
    """Review for delivery person"""
    delivery_person = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='delivery_reviews')
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='delivery_review')
    rating = models.PositiveSmallIntegerField(help_text='Rating from 1 to 5')
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Delivery Review for {self.delivery_person.username} - Order #{self.order.id}"


# In models.py
class OrderManager(models.Manager):
    def available_for_pickup(self):
        return self.filter(status='ready_for_pickup', delivery_person__isnull=True)