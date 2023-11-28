# Forms
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from users.models import (
    construction,
    bids,
    Profile,
    )
from game.models import (
    settings, # Game settings
    sessions,
    demand_cf,
    tech
    )
# User Registration Form (based on default django UserCreationForm)
class UserRegisterForm(UserCreationForm): # RegisterForm basiert auf Standard UserCreationForm
    email = forms.EmailField()
    is_staff = forms.BooleanField(initial=False, label='Create a Gamemaster Account? Tick this box if you want to host a game, otherwise leave blank.', required=False)
    
    class Meta:
        model = User # DB, in welche gespeichert werden soll
        fields = ['username', 'email', 'is_staff', 'password1', 'password2'] # Eingabefelder und deren Reihenfolge
        labels = {
            'is_staff': 'Create a Gamemaster Account? Tick this box if you want to host a game, otherwise leave blank.'
        }

# Construction Form
class ConstructionForm(forms.ModelForm): # Formular basierend auf der construction-Datenbank
    add_generator = forms.BooleanField(widget=forms.HiddenInput, initial=True) # Versteckte Variable
    amount = forms.IntegerField(initial=1, label='How many units?', required=True, min_value=1)
    
    class Meta:
        model = construction             # zugrundliegende Datenbank
        fields = ['technology']          # Eingabefelder
        labels = {
            'technology': 'Choose Technology'
        }

# Decomission Form
class DecommissionForm(forms.Form): 
    delete_generator = forms.BooleanField(widget=forms.HiddenInput, initial=True)   # Versteckte Variable
    choices = list(tech.objects.values_list('technology', 'technology')) + [('','---------')] 
    techs = forms.ChoiceField(choices=choices, label='Choose Technology')
    units = forms.IntegerField(initial=1, label='How many units?', required=True, min_value=1)

# Bidding Form
class BiddingForm(forms.ModelForm):
    submit_bid = forms.BooleanField(widget=forms.HiddenInput, initial=True)   # Versteckte Variable
    price = forms.DecimalField(min_value=0, max_value=999 ,decimal_places=2, max_digits=10, label='Price in €/MWh')
    amount = forms.DecimalField(min_value=0, decimal_places=2, max_digits=10, label='Capacity in MW')

    class Meta:
        model = bids
        fields = ['technology', 'price', 'amount']
        labels = {
            'technology': 'Choose Technology',
        }

# Delete Bids Form
class DeleteBidForm(forms.Form):
    # Get request.user from view.py
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # Remove 'user' from kwargs if it exists
        super(DeleteBidForm, self).__init__(*args, **kwargs)
        self.user = user
        # Update the queryset for the name field based on users bids
        self.fields['bid_id'].queryset = bids.objects.filter(user = self.user).order_by('price', 'amount')
    
    delete_bid = forms.BooleanField(widget=forms.HiddenInput, initial=True)   # Versteckte Variable
    bid_id = forms.ModelChoiceField(queryset=bids.objects.none(), to_field_name='id', required=True, widget=forms.Select(attrs={'class': 'form-control'}), label="Choose a Bid to delete")

    class Meta:
        model = bids
        fields = ['id']

# Settings Form
class SettingsForm(forms.ModelForm):
    # Get request.user from view.py
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # Remove 'user' from kwargs if it exists
        super(SettingsForm, self).__init__(*args, **kwargs)
        self.user = user
        # Update the queryset for the name field based on profile.joined_game
        profile = Profile.objects.get(user = self.user)
        self.fields['name'].queryset = settings.objects.filter(game = profile.joined_game).exclude(name = 'round').exclude(name = 'clearing_price')

    change_settings = forms.BooleanField(widget=forms.HiddenInput, initial=True)
    name = forms.ModelChoiceField(queryset=settings.objects.none(), to_field_name='name', required=True, widget=forms.Select(attrs={'class': 'form-control'}), label="Choose Setting")

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

# New Game Session Form
class NewGameSessionForm(forms.ModelForm):
    new_game = forms.BooleanField(widget=forms.HiddenInput, initial=True)
    variables = forms.ModelChoiceField(queryset=demand_cf.objects.values_list('key', flat=True).distinct(), to_field_name='key', label="Choose Scenario")

    class Meta:
        model = sessions
        fields = ['name', 'variables']
        labels = {
            'name': 'Enter a unique Name for your Game',
        }

# Delete Game Session Form
class DeleteGameSessionForm(forms.Form):
    delete_game = forms.BooleanField(widget=forms.HiddenInput, initial=True)

# Host Game Session Form (STAFF ONLY)
class HostGameSessionForm(forms.ModelForm):
    host_game = forms.BooleanField(widget=forms.HiddenInput, initial=True)
    name = forms.ModelChoiceField(queryset=sessions.objects.filter(ready=False), to_field_name='name', required=True, widget=forms.Select(attrs={'class': 'form-control'}), label="Choose a Game")

    class Meta:
        model = sessions
        fields = ['name']

# Join Game Session Form 
class JoinGameSessionForm(forms.ModelForm):
    name = forms.ModelChoiceField(queryset=sessions.objects.filter(ready=False), to_field_name='name', required=True, widget=forms.Select(attrs={'class': 'form-control'}), label="Choose a Game")

    class Meta:
        model = sessions
        fields = ['name']    

# Start Game Session Form
class StartEndGameSessionForm(forms.Form):
    start_end_game = forms.BooleanField(widget=forms.HiddenInput, initial=True)

# Player Ready for next Round Form
class PlayerReadyForm(forms.Form):
    player_ready = forms.BooleanField(widget=forms.HiddenInput, initial=True)

# Remove Player from a Game Form
class RemovePlayerForm(forms.Form):
    remove_player = forms.BooleanField(widget=forms.HiddenInput, initial=True)
    id = forms.IntegerField(required=True, label='Enter Players Profile ID')

# Export Data Form
class ExportForm(forms.Form):
    export_data = forms.BooleanField(widget=forms.HiddenInput, initial=True)

# Enforce Ready Form
class EnforceReadyForm(forms.Form):
    enforce_ready = forms.BooleanField(widget=forms.HiddenInput, initial=True)
