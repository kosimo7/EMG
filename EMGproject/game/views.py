from django.shortcuts import render
from django.http import HttpResponse
from .models import (
    tech,
    settings
    )

# Home Page View
def home(request):
    return render(request, 'game/home.html', {"title": "Home"})

# About Page View
def about(request):
    return render(request, 'game/about.html', {"title": "About"})

# Data Page View
def data(request):
    context ={
        "datas": tech.objects.all(), #Variable für data.html, welche die gesamte tech Tabelle enthält
        "carbon_price": settings.objects.values_list('value', flat=True).get(name='carbon_price'),
    }
    return render(request, 'game/data.html', context)
