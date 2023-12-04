from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import (
    tech,
    settings,
    )
from users.models import (
    Profile,
    sessions,
    )

# Home Page View
def home(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('users-staff_profile')
        else:
            return redirect('users-profile')
    return render(request, 'game/home.html', {"title": "Home"})

# About Page View
def about(request):
    return render(request, 'game/about.html', {"title": "About"})

# Data Page View (alternative to display technology data)
@login_required
def data(request):
    profile = Profile.objects.get(user_id = request.user.id)
    joined_game = Profile.objects.values_list('joined_game', flat=True).get(user_id = request.user.id)
    # Player View
    if not request.user.is_staff: 
        if profile.joined_game is not None:
            if not profile.ready and sessions.objects.get(name = joined_game).ready:
                current_game = sessions.objects.get(name = joined_game)
                carbon_price = settings.objects.get(name='carbon_price', game = current_game).value
            elif profile.ready and sessions.objects.get(name = joined_game).ready: 
                messages.warning(request, f'Please wait for the next round to start!')
                return redirect('users-ready_room')
            elif not sessions.objects.get(name = joined_game).ready:
                messages.warning(request, f'Please wait for the Game to start!')
                return redirect('users-waiting_room')
        else: 
            messages.warning(request, f'Please join a Game')
            return redirect('users-join_game')
    # Gamemaster View
    else: 
        if profile.joined_game is not None:
                current_game = sessions.objects.get(name = joined_game)
                carbon_price = settings.objects.get(name='carbon_price', game = current_game).value
        else:
            messages.warning(request, f'Please host a Game')
            return redirect('users-staff_new_game')
    # HTML Variablen
    context ={
        "title": "Technology Data",
        "datas": tech.objects.all(), 
        "carbon_price": carbon_price,
    }
    return render(request, 'game/data.html', context)
