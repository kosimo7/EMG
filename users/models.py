from django.db import models
from django.contrib.auth.models import User
from game.models import (
    tech,
    sessions,
    )

# User profiles
class Profile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE) # Foreign Key to the User model
    budget = models.DecimalField(decimal_places=2, max_digits=100, default=0.00)
    revenue = models.DecimalField(decimal_places=2, max_digits=100, default=0.00)
    profit = models.DecimalField(decimal_places=2, max_digits=100, default=0.00)
    total_cost = models.DecimalField(decimal_places=2, max_digits=100, default=0.00)
    joined_game = models.ForeignKey(sessions, on_delete=models.SET_NULL, to_field="name", db_column="name", blank=True, null=True) # Name of the joined Game
    ready = models.BooleanField(default=False) # Truie= player is ready for the next round; False= player is not yet ready
    
    def __str__(self):
        return f'{self.user.username} Profile'

# User generation system    
class generation_system(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE) # Foreign Key to the User model
    technology = models.ForeignKey(tech, on_delete=models.CASCADE, to_field="technology", db_column="technology") # Generation Technology, Foreign Key to the tech model
    capacity = models.IntegerField(default=0) # Capacity in MW
    until_decommissioned = models.PositiveIntegerField(default=0) # Remaining operational periods

    def __str__(self):
        return f'Sys_ID: {self.id}, User: {self.user.username}, Tech: {self.technology} ' 

# User construction orders
class construction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE) # Foreign Key to the User model
    technology = models.ForeignKey(tech, on_delete=models.CASCADE, to_field="technology", db_column="technology") # Generation Technology, Foreign Key to the tech model
    until_constructed = models.PositiveIntegerField(default=0) # Remaining build time in rounds

    def __str__(self):
        return f'Cons_ID:{self.id}, User: {self.user.username}, Tech: {self.technology}' 

# User bids
class bids(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE) # Foreign Key to the User model
    technology  = models.ForeignKey(tech, on_delete=models.CASCADE, to_field="technology", db_column="technology") # Chosen Technology, Foreign Key to the tech model
    price = models.DecimalField(decimal_places=2, max_digits=10)   # €/MWh
    amount = models.DecimalField(decimal_places=2, max_digits=10)  # MW

    def __str__(self):
        return f'Bid_ID: {self.id}, User: {self.user.username}, Tech: {self.technology}, Price: {self.price}, Capacity: {self.amount}'

# Accepted bids/ merit order
class bids_meritorder(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE) # Foreign Key to the User model
    technology  = models.ForeignKey(tech, on_delete=models.CASCADE, to_field="technology", db_column="technology") # Chosen Technology, Foreign Key to the tech model
    price = models.DecimalField(decimal_places=2, max_digits=10)  # €/MWh
    amount = models.DecimalField(decimal_places=2, max_digits=10)  # MW




