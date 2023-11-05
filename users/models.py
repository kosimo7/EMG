from django.db import models
from django.contrib.auth.models import User
from game.models import (
    tech,
    sessions,
    )

class Profile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE) # User und Profile habe 1-zu-1 Beziehung und User is Fremdschlüssel; Beim Löschen des Users wird auch Profile gelöscht
    budget = models.DecimalField(decimal_places=2, max_digits=100, default=0.00)
    revenue = models.DecimalField(decimal_places=2, max_digits=100, default=0.00)
    profit = models.DecimalField(decimal_places=2, max_digits=100, default=0.00)
    total_cost = models.DecimalField(decimal_places=2, max_digits=100, default=0.00)
    joined_game = models.ForeignKey(sessions, on_delete=models.SET_NULL, to_field="name", db_column="name", blank=True, null=True)
    ready = models.BooleanField(default=False)
    
    def __str__(self):
        return f'{self.user.username} Profile'
    
class generation_system(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE) 
    technology = models.ForeignKey(tech, on_delete=models.CASCADE, to_field="technology", db_column="technology")
    capacity = models.IntegerField(default=0)
    until_decommissioned = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f'Sys_ID: {self.id}, User: {self.user.username}, Tech: {self.technology} ' 
    
class construction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    technology = models.ForeignKey(tech, on_delete=models.CASCADE, to_field="technology", db_column="technology")
    until_constructed = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f'Cons_ID:{self.id}, User: {self.user.username}, Tech: {self.technology}' 

class bids(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    technology  = models.ForeignKey(tech, on_delete=models.CASCADE, to_field="technology", db_column="technology")
    price = models.DecimalField(decimal_places=2, max_digits=10)   # €/MWh
    amount = models.DecimalField(decimal_places=2, max_digits=10)  # MW

    def __str__(self):
        return f'Bid_ID: {self.id}, User: {self.user.username}, Tech: {self.technology}, Price: {self.price}, Capacity: {self.amount}'
    
class bids_meritorder(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    technology  = models.ForeignKey(tech, on_delete=models.CASCADE, to_field="technology", db_column="technology")
    price = models.DecimalField(decimal_places=2, max_digits=10)  # €/MWh
    amount = models.DecimalField(decimal_places=2, max_digits=10)  # MW


