from django.db import models
from django.contrib.auth.models import User

# Technology Database
class tech(models.Model):
    technology = models.CharField(max_length=30, unique=True)
    capacity = models.IntegerField(default=0)
    investment_cost = models.IntegerField()
    build_time = models.IntegerField()
    operation_time = models.PositiveIntegerField()
    fixed_cost = models.PositiveIntegerField(default=0)
    fuel_cost = models.FloatField()
    carbon_content = models.FloatField()
    default_amount = models.PositiveIntegerField(default=0)

    def __str__(self):
        return str(self.technology)

# Variables/Settings
class settings(models.Model):
    name = models.CharField(max_length=30, unique=True)
    value = models.IntegerField()

    def __str__(self):
        return str(self.name)