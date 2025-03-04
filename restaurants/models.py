
from django.db import models
from django.conf import settings
from core.models import Address

class Restaurant(models.Model):
    """Restaurant model"""
    manager = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField()
    logo = models.ImageField(upload_to='restaurant_logos/')
    banner_image = models.ImageField(upload_to='restaurant_banners/', blank=True, null=True)
    address = models.OneToOneField(Address, on_delete=models.CASCADE)
    cuisine_type = models.CharField(max_length=50)
    phone = models.CharField(max_length=15)
    email = models.EmailField()
    website = models.URLField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    delivery_fee = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    min_order_amount = models.DecimalField(max_digits=6, decimal_places=2, default=0.0)
    preparation_time = models.PositiveIntegerField(default=30, help_text='Average preparation time in minutes')
    opening_time = models.TimeField()
    closing_time = models.TimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

class MenuItem(models.Model):
    """Menu item model"""
    CATEGORY_CHOICES = (
        ('appetizer', 'Appetizer'),
        ('main', 'Main Course'),
        ('dessert', 'Dessert'),
        ('beverage', 'Beverage'),
        ('side', 'Side Dish'),
    )
    
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='menu_items')
    name = models.CharField(max_length=100)
    description = models.TextField()
    image = models.ImageField(upload_to='menu_items/')
    price = models.DecimalField(max_digits=6, decimal_places=2)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    is_vegetarian = models.BooleanField(default=False)
    is_vegan = models.BooleanField(default=False)
    is_gluten_free = models.BooleanField(default=False)
    spice_level = models.PositiveSmallIntegerField(default=0, help_text='Spice level from 0 to 5')
    is_available = models.BooleanField(default=True)
    preparation_time = models.PositiveIntegerField(default=15, help_text='Preparation time in minutes')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} - {self.restaurant.name}"