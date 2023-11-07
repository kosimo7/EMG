from django.db import models
# from django.contrib.auth.models import User

# Technology Database
class tech(models.Model):
    technology = models.CharField(max_length=30, unique=True)
    capacity = models.IntegerField(default=0)
    investment_cost = models.IntegerField()
    build_time = models.IntegerField()
    operation_time = models.PositiveIntegerField()
    fixed_cost = models.PositiveIntegerField(default=0)
    fuel_cost = models.DecimalField(decimal_places=2, max_digits=10)
    carbon_content = models.DecimalField(decimal_places=2, max_digits=10)
    default_amount = models.PositiveIntegerField(default=0)

    def __str__(self):
        return str(self.technology)

# Game sessions
class sessions(models.Model):
    name = models.CharField(max_length=30, unique=True)
    ready = models.BooleanField(default=False)
    variables = models.CharField(max_length=30, default='game_variables')
    final = models.BooleanField(default=False)

    def __str__(self):
        return str(self.name)

# Basic Settings and Variables
class settings(models.Model):
    name = models.CharField(max_length=30)
    value = models.DecimalField(decimal_places=2, max_digits=20)
    game = models.ForeignKey(sessions, on_delete=models.CASCADE, to_field="name")

    def __str__(self):
        return str(self.name)

# Demand & Capacity Factor
class demand_cf(models.Model):
    demand = models.IntegerField()
    cf_wind = models.DecimalField(decimal_places=2, max_digits=3)
    cf_pv = models.DecimalField(decimal_places=2, max_digits=3)
    round = models.IntegerField()
    key = models.CharField(max_length=30, default='game_variables')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields = ['round', 'key'], name = 'unique_set') # Beide Felder müssen als Kombination unique sein
        ]

# database for backup variables
class backup(models.Model):
    game = models.ForeignKey(sessions, on_delete=models.CASCADE, to_field="name")
    name = models.CharField(max_length=30)
    value = models.DecimalField(decimal_places=2, max_digits=20, null=True)