from django.contrib import admin
from .models import (
    Profile, 
    generation_system, 
    construction,
    bids
    )


# Register your models here. (Damit die Datenbanken auf der Admin-Seite sichtbar sind)
admin.site.register(Profile)
admin.site.register(generation_system)
admin.site.register(construction)
admin.site.register(bids)

