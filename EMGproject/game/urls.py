from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.home, name='game-home'), # Home Page
    path('about/', views.about, name='game-about'),
    path('data/', views.data, name='game-data'),
]