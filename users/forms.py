#Forms
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from users.models import (
    construction,
    bids
    )
from game.models import (
    settings, # Game settings
    )
# User Registration Form (based on default django UserCreationForm)
class UserRegisterForm(UserCreationForm): # RegisterForm basiert auf Standard UserCreationForm
    email = forms.EmailField()
    
    class Meta:
        model = User # DB, in welche gespeichert werden soll
        fields = ['username', 'email', 'password1', 'password2'] # Eingabefelder und deren Reihenfolge

# Construction Form
class ConstructionForm(forms.ModelForm): # Formular basierend auf der construction-Datenbank
    add_generator = forms.BooleanField(widget=forms.HiddenInput, initial=True) # Versteckte Variable
    
    class Meta:
        model = construction             # zugrundliegende Datenbank
        fields = ['technology']          # Eingabefelder
        labels = {
            'technology': 'Choose Technology'
        }

# Decomission Form
class DecommissionForm(forms.Form): # Formular basierend auf der generation_system-Datenbank
    delete_generator = forms.BooleanField(widget=forms.HiddenInput, initial=True)   # Versteckte Variable
    generator_id = forms.IntegerField(label="Please Enter Generator ID")

# Bidding Form
class BiddingForm(forms.ModelForm):
    submit_bid = forms.BooleanField(widget=forms.HiddenInput, initial=True)   # Versteckte Variable
    class Meta:
        model = bids
        fields = ['technology', 'price', 'amount']
        labels = {
            'technology': 'Choose Technology',
            'price': 'Price in €/MWh',
            'amount': 'Capacity in MW'
        }

# Delete Bids Form
class DeleteBidForm(forms.Form):
    delete_bid = forms.BooleanField(widget=forms.HiddenInput, initial=True)   # Versteckte Variable
    bid_id = forms.IntegerField(label="Please Enter Bid ID")

# Settings Form
class SettingsForm(forms.ModelForm):
    change_settings = forms.BooleanField(widget=forms.HiddenInput, initial=True)
    name = forms.ModelChoiceField(queryset=settings.objects.all(), to_field_name='name', required=True, widget=forms.Select(attrs={'class': 'form-control'}), label="Choose Setting")

    class Meta:
        model = settings
        fields = ['name', 'value']
        labels = {
            'value': 'Enter Value'
        }

# Next Round Form
class NextRoundForm(forms.Form):
    next_round = forms.BooleanField(widget=forms.HiddenInput, initial=True)
    confirm = forms.BooleanField(initial=False, required=True, label='Confirm')



