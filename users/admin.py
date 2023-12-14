from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import (
    Profile, 
    generation_system, 
    construction,
    bids,
    bids_meritorder,
    )

# Resources for export
class ProfileResource(resources.ModelResource):

    class Meta:
        model = Profile
        exclude = ('ready', )

# Connect Resources to Admin Model
class UsersImportExports(ImportExportModelAdmin):
    resource_classes = [ProfileResource]


# Register your models here. (Damit die Datenbanken auf der Admin-Seite sichtbar sind)
admin.site.register(Profile, ImportExportModelAdmin)
admin.site.register(generation_system)
admin.site.register(construction)
admin.site.register(bids)
admin.site.register(bids_meritorder)

