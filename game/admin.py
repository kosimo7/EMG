from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import (
    tech,
    sessions, 
    settings,
    demand_cf,
    backup,
    )

# Resources for export
class DemandCFResource(resources.ModelResource):

    class Meta:
        model = demand_cf

# Connect Resources to Admin Model
class GameImportExports(ImportExportModelAdmin):
    resource_classes = [DemandCFResource]


# Register your models here. (Display model on admin site)
admin.site.register(tech) 
admin.site.register(settings)
admin.site.register(sessions)
admin.site.register(demand_cf, ImportExportModelAdmin)
admin.site.register(backup)