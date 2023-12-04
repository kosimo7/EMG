from django.db import models

# Generation Technology Data
class tech(models.Model):
    technology = models.CharField(max_length=30, unique=True) # Generation Technologies
    capacity = models.IntegerField(default=0) # Capacity per unit (MW)
    investment_cost = models.IntegerField() # Investment cost per unit 
    build_time = models.IntegerField() # Unit Build time in rounds
    operation_time = models.PositiveIntegerField() # Unit operation time in rounds
    fixed_cost = models.PositiveIntegerField(default=0) # Fixed cost per unit per round
    fuel_cost = models.DecimalField(decimal_places=2, max_digits=10) # Fuel cost per MWh produced
    carbon_content = models.DecimalField(decimal_places=2, max_digits=10) # Carbon content per MWh in tCO2
    default_amount = models.PositiveIntegerField(default=0) # Specified amount of units each player owns at the start of the game

    def __str__(self):
        return str(self.technology)

# Game sessions
class sessions(models.Model):
    name = models.CharField(max_length=30, unique=True)
    ready = models.BooleanField(default=False) # True= the game has started and is running; False= the game has not yet started
    variables = models.CharField(max_length=30, default='game_variables') # Chosen scenario
    final = models.BooleanField(default=False) # True= the game has finished (round=max_round); False= game has not yet finished (round<max_round)

    def __str__(self):
        return str(self.name)

# Basic Settings and Variables
class settings(models.Model):
    name = models.CharField(max_length=30)
    value = models.DecimalField(decimal_places=2, max_digits=20)
    game = models.ForeignKey(sessions, on_delete=models.CASCADE, to_field="name")

    def __str__(self):
        return str(self.name)

# Demand & Capacity Factors 
class demand_cf(models.Model):
    demand = models.IntegerField() # Demand per player (MW)
    cf_wind = models.DecimalField(decimal_places=2, max_digits=3)
    cf_pv = models.DecimalField(decimal_places=2, max_digits=3)
    round = models.IntegerField()
    key = models.CharField(max_length=30, default='game_variables') # key which describes the scenario

    class Meta:
        constraints = [
            models.UniqueConstraint(fields = ['round', 'key'], name = 'unique_set') # These fields have to be unique as a set
        ]

# Database for backup variables, used to save price history and installed capacities
class backup(models.Model):
    game = models.ForeignKey(sessions, on_delete=models.CASCADE, to_field="name")
    name = models.CharField(max_length=30)
    value = models.DecimalField(decimal_places=2, max_digits=20, null=True)
    round = models.IntegerField()