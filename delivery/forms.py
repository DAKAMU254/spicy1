from django import forms
from .models import DeliveryProfile

class DeliveryProfileForm(forms.ModelForm):
    """Form for delivery profile"""
    class Meta:
        model = DeliveryProfile
        fields = ['vehicle_type', 'vehicle_number', 'license_number']

class LocationUpdateForm(forms.Form):
    """Form for updating delivery person location"""
    latitude = forms.DecimalField(max_digits=9, decimal_places=6)
    longitude = forms.DecimalField(max_digits=9, decimal_places=6)