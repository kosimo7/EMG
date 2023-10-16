from django.db import models
from django.contrib.auth.models import User
from game.models import tech

class Profile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE) # User und Profile habe 1-zu-1 Beziehung und User is Fremdschlüssel; Beim Löschen des Users wird auch Profile gelöscht
    budget = models.IntegerField(default=0)
    revenue = models.IntegerField(default=0)
    profit = models.IntegerField(default=0)
    total_cost = models.IntegerField(default=0)
    
    def __str__(self):
        return f'{self.user.username} Profile'
    
class generation_system(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE) #id
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
    price = models.PositiveIntegerField()   # €/MWh
    amount = models.PositiveIntegerField()  # MW

    def __str__(self):
        return f'Bid_ID: {self.id}, User: {self.user.username}, Tech: {self.technology}, Price: {self.price}, Capacity: {self.amount}'

