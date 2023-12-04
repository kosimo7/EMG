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
from django.contrib.auth import views as auth_views # Import django Login Views; import Views always *as Variable* 
from users import views as user_views # import views.py from users-app as user_views
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('register/', user_views.register, name='users-register'), 
    path('login/', auth_views.LoginView.as_view(template_name='users/login.html'), name='users-login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='users/logout.html'), name='users-logout'),
    path('profile/', user_views.profil, name='users-profile'),
    path('staff_profile/', user_views.staff_profil, name='users-staff_profile'),
    path('', include('game.urls')), # include the game.urls file
    path('bidding/', user_views.bidding, name='users-bidding'),
    path('staff_new_game/', user_views.staff_new_game, name='users-staff_new_game'),
    path('join_game/', user_views.join_game, name='users-join_game'),
    path('waiting_room/', user_views.waiting_room, name='users-waiting_room'),
    path('ready_room/', user_views.ready_room, name='users-ready_room'),
    path('overview/', user_views.overview, name='users-overview'),
    path('profile/get_dynamic_content/', user_views.get_dynamic_content, name='get_dynamic_content'),
    path('profile/get_dynamic_content_decommission/', user_views.get_dynamic_content_decommission, name='get_dynamic_content_decommission'),
]
