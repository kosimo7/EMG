"""EMGproject URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views # Import der Standard django Login Views; Views immer *as Variable* importieren
from django.urls import path, include
from users import views as user_views # import von views.py aus users-app unter Variable user_views


urlpatterns = [
    path('admin/', admin.site.urls),
    path('register/', user_views.register, name='users-register'), # Hier nicht mit include weil views.py direkt importiert wird
    path('login/', auth_views.LoginView.as_view(template_name='users/login.html'), name='users-login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='users/logout.html'), name='users-logout'),
    path('profile/', user_views.profil, name='users-profile'),
    path('staff_profile/', user_views.staff_profil, name='users-staff_profile'),
    path('', include('game.urls')), # weil der path hier leer ist, wird diese App zur homepage
    path('construction_order/', user_views.construction_order, name='users-construction_order'),
    path('bidding/', user_views.bidding, name='users-bidding'),
]
