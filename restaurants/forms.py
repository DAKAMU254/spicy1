from django import forms
from .models import Restaurant, MenuItem
from core.models import Address

class RestaurantForm(forms.ModelForm):
    """Form for restaurant settings"""
    address_line1 = forms.CharField(max_length=100)
    address_line2 = forms.CharField(max_length=100, required=False)
    city = forms.CharField(max_length=50)
    state = forms.CharField(max_length=50)
    postal_code = forms.CharField(max_length=10)
    
    class Meta:
        model = Restaurant
        fields = [
            'name', 'description', 'logo', 'banner_image', 'cuisine_type',
            'phone', 'email', 'website', 'delivery_fee', 'min_order_amount',
            'preparation_time', 'opening_time', 'closing_time'
        ]
        widgets = {
            'opening_time': forms.TimeInput(attrs={'type': 'time'}),
            'closing_time': forms.TimeInput(attrs={'type': 'time'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # If restaurant has an address, populate the address fields
        if self.instance and self.instance.pk and hasattr(self.instance, 'address'):
            self.fields['address_line1'].initial = self.instance.address.address_line1
            self.fields['address_line2'].initial = self.instance.address.address_line2
            self.fields['city'].initial = self.instance.address.city
            self.fields['state'].initial = self.instance.address.state
            self.fields['postal_code'].initial = self.instance.address.postal_code
    
    def save(self, commit=True):
        restaurant = super().save(commit=False)
        
        # Save or update address
        if hasattr(restaurant, 'address'):
            address = restaurant.address
        else:
            address = Address(user=restaurant.manager)
        
        address.address_line1 = self.cleaned_data['address_line1']
        address.address_line2 = self.cleaned_data['address_line2']
        address.city = self.cleaned_data['city']
        address.state = self.cleaned_data['state']
        address.postal_code = self.cleaned_data['postal_code']
        address.is_default = True
        address.save()
        
        restaurant.address = address
        
        if commit:
            restaurant.save()
        
        return restaurant

class MenuItemForm(forms.ModelForm):
    """Form for menu items"""
    class Meta:
        model = MenuItem
        fields = [
            'name', 'description', 'image', 'price', 'category',
            'is_vegetarian', 'is_vegan', 'is_gluten_free', 'spice_level',
            'is_available', 'preparation_time'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'price': forms.NumberInput(attrs={'min': 0, 'step': 0.01}),
            'spice_level': forms.NumberInput(attrs={'min': 0, 'max': 5}),
            'preparation_time': forms.NumberInput(attrs={'min': 1}),
        }
