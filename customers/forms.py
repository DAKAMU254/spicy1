from django import forms
from django.contrib.auth import get_user_model
from .models import CartItem, Order, Review
from core.models import Address

User = get_user_model()

class CartItemForm(forms.ModelForm):
    """Form for adding items to cart"""
    class Meta:
        model = CartItem
        fields = ['quantity', 'special_instructions']
        widgets = {
            'quantity': forms.NumberInput(attrs={'min': 1, 'max': 20, 'class': 'form-control'}),
            'special_instructions': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }

class OrderForm(forms.ModelForm):
    """Form for placing an order"""
    class Meta:
        model = Order
        fields = ['special_instructions']
        widgets = {
            'special_instructions': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Any special instructions for delivery?'}),
        }

class ReviewForm(forms.ModelForm):
    """Form for reviewing a restaurant"""
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.Select(choices=[(i, i) for i in range(1, 6)]),
            'comment': forms.Textarea(attrs={'rows': 4}),
        }

class CustomerProfileForm(forms.ModelForm):
    """Form for updating customer profile"""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'profile_picture']
from django import forms
from core.models import Address
from django.contrib.auth import get_user_model
from .models import CartItem, Order, Review

User = get_user_model()

class CartItemForm(forms.ModelForm):
    """Form for adding items to cart"""
    class Meta:
        model = CartItem
        fields = ['quantity', 'special_instructions']
        widgets = {
            'quantity': forms.NumberInput(attrs={'min': 1, 'max': 20, 'class': 'form-control'}),
            'special_instructions': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }

class OrderForm(forms.ModelForm):
    """Form for placing an order"""
    class Meta:
        model = Order
        fields = ['special_instructions']
        widgets = {
            'special_instructions': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Any special instructions for delivery?'}),
        }

class ReviewForm(forms.ModelForm):
    """Form for reviewing a restaurant"""
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.Select(choices=[(i, i) for i in range(1, 6)]),
            'comment': forms.Textarea(attrs={'rows': 4}),
        }

class CustomerProfileForm(forms.ModelForm):
    """Form for updating customer profile"""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'profile_picture']
        widgets = {
            'phone_number': forms.TextInput(attrs={'placeholder': 'e.g. 555-123-4567'}),
        }

# Add the missing AddressForm
class AddressForm(forms.ModelForm):
    """Form for adding/editing addresses"""
    class Meta:
        model = Address
        fields = ['address_line1', 'address_line2', 'city', 'state', 'postal_code', 'is_default']
        widgets = {
            'address_line1': forms.TextInput(attrs={'placeholder': 'Street address'}),
            'address_line2': forms.TextInput(attrs={'placeholder': 'Apartment, suite, unit, etc. (optional)'}),
            'city': forms.TextInput(attrs={'placeholder': 'City'}),
            'state': forms.TextInput(attrs={'placeholder': 'State/Province'}),
            'postal_code': forms.TextInput(attrs={'placeholder': 'Postal code'}),
        }     

# JavaScript code should be placed in an HTML template, not in a Python file.
# Remove the JavaScript code from this file and place it in the appropriate HTML template.