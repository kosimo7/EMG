from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required # login required decorator
from django.contrib.admin.views.decorators import staff_member_required # staff member required decorator
import pandas as pd
from .forms import (
    UserRegisterForm, # Neuer User Register Formular
    ConstructionForm, # Bauauftrag Formular
    DecommissionForm, # Stillegung Formular
    BiddingForm,      # Formular zur Abgabe von Geboten
    SettingsForm,     # Change Game Settings Form
    NextRoundForm,    # End current round/Start the next round Form
    DeleteBidForm,
    NewGameSessionForm,
    HostGameSessionForm,
    JoinGameSessionForm,
    StartEndGameSessionForm,
    DeleteGameSessionForm,
    PlayerReadyForm,
    RemovePlayerForm,
    ExportForm,
    EnforceReadyForm,
    )
from .models import ( 
    generation_system, # importiert Kraftwerkspark
    Profile,           # importiert Spielerprofile
    construction,      # importiert Bauaufträge
    bids,              # importiert Gebot
    bids_meritorder,
    )
from game.models import (
    tech,       # importiert Start-Kraftwerkspark & Daten (default)
    settings,   # Spieleinstellungen
    sessions,
    demand_cf,
    backup,
    )
from django.contrib.auth.models import User
from django.db.models.signals import post_save  # importing post save signal
from django.dispatch import receiver # Signal receiver decorator
from django.db.models import Sum, Count
from decimal import Decimal

# User Register view
def register(request):
    if request.method == "POST":
        form = UserRegisterForm(request.POST)
        if form.is_valid(): # checks if entered data is valid
            form.save() # User wird in DB gespeichert
            username = form.cleaned_data.get("username")
            messages.success(request, f'Hello {username}, Your Accout has been created! You ar now able to log in.') # Pop-up message, wenn Registration funktioniert hat; f'' --> formatierter String
            return redirect('users-profile') # User wird zur Login Page und dann zum Profil weitergeleitet
    else:
        form = UserRegisterForm()
    context = {
        "title": "Register",
        'form': form,
    }
    return render(request, 'users/register.html', context)

# Create a Player Profile for each new registered User
@receiver(post_save, sender=User)
def user_created_handler(sender, instance, created,*args,**kwargs):
    if created:
        Profile(user=instance, budget=0, revenue=0, profit=0, total_cost=0).save()       

# Profile Page view
@login_required # decorator, only logged in users can access profile page
def profil(request):
    if request.user.is_staff:
        return redirect('users-staff_profile')
    profile = Profile.objects.get(user_id = request.user.id)
    joined_game = Profile.objects.values_list('joined_game', flat=True).get(user_id = request.user.id)
    if profile.joined_game is not None:
        if not profile.ready and sessions.objects.get(name = joined_game).ready: # User können das Profil nur aufrufen, wenn sie einem Spiel beigetreten sind und dieses gestartet ist
            current_game = sessions.objects.get(name = joined_game)
            # Redirect Players if the game is over
            if current_game.final:
                messages.success(request, f'The Game has ended!')
                return redirect('users-overview')
            # Decommission is only possible, if the generator is not scheduled for current round (e.g. the capacity is not required to fullfill bids)
            cap = generation_system.objects.filter(user_id = request.user.id)                            # Kraftwerkspark des Spielers
            current_round = settings.objects.get(game_id = joined_game, name = 'round').value
            cf_wind = demand_cf.objects.get(key = current_game.variables, round = current_round).cf_wind
            cf_pv = demand_cf.objects.get(key = current_game.variables, round = current_round).cf_pv
            user_bids = bids.objects.filter(user_id = request.user.id)        
            # Formular Kraftwerk löschen
            form_d = DecommissionForm()
            if 'delete_generator' in request.POST:  # prüfen ob versteckte Boolean Variable aus forms.py in POST vorhanden um Formulare zu unterscheiden 
                if request.method == "POST":
                    form_d = DecommissionForm(request.POST)
                    if form_d.is_valid():
                        units = form_d.cleaned_data['units']
                        technology = form_d.cleaned_data['techs']
                        # Order units by rounds left, then delete the first x entries where x = the chosen amount of units
                        gen = generation_system.objects.filter(user = request.user, technology = technology).order_by('until_decommissioned')[:units]
                        # Cannot delete more Generators than exist
                        if len(gen) < units:
                            messages.warning(request, f'You currently do not own {units} {technology} units in your generation system!')
                            return redirect('users-profile')
                        # Calculate Capacities
                        bid_cap = (user_bids.filter(technology = technology).aggregate(Sum('amount')))['amount__sum']
                        if str(technology) == 'Wind':
                            cap = (generation_system.objects.filter(user_id = request.user.id, technology = technology).aggregate(Sum('capacity')))['capacity__sum'] * cf_wind
                        elif str(technology) == 'Solar':
                            cap = (generation_system.objects.filter(user_id = request.user.id, technology = technology).aggregate(Sum('capacity')))['capacity__sum'] * cf_pv
                        elif str(technology) != 'Solar' and str(technology) != 'Wind':
                            cap = (generation_system.objects.filter(user_id = request.user.id, technology = technology).aggregate(Sum('capacity')))['capacity__sum']
                        # You cannot delete generators if the capacity is already placed in a bid
                        if cap is not None and bid_cap is not None:
                            remaining_cap = cap - bid_cap
                            if str(technology) == 'Wind':
                                delete_cap = (gen.aggregate(Sum('capacity')))['capacity__sum'] * cf_wind
                            elif str(technology) == 'Solar':
                                delete_cap = (gen.aggregate(Sum('capacity')))['capacity__sum'] * cf_pv
                            elif str(technology) != 'Solar' and str(technology) != 'Wind':
                                delete_cap = (gen.aggregate(Sum('capacity')))['capacity__sum']
                            if delete_cap > remaining_cap:
                                messages.warning(request, f'The chosen units are already scheduled for production! Please edit your placed bids until enough remaining capacity is available.')
                                return redirect('users-profile')
                        # Delete Generators
                        gens = gen.values_list('id', flat=True)
                        generation_system.objects.filter(id__in = gens).delete()
                        messages.success(request, f'Decommission Successfull!')
                        return redirect('users-profile')
                    else:
                        form_d = DecommissionForm()
            # Formular 2
            form_c = ConstructionForm()
            if 'add_generator' in request.POST:    # prüfen ob versteckte Boolean Variable aus forms.py in POST vorhanden um Formulare zu unterscheiden 
                if request.method == "POST":
                    form_c = ConstructionForm(request.POST)
                    form_c.instance.user = request.user # User instance (logged in user) an Formular übergeben
                    p = Profile.objects.get(user_id=request.user)
                    if form_c.is_valid() and (p.budget >= (tech.objects.get(technology=form_c.instance.technology).investment_cost * int(form_c.data['amount']))): # Bedingung: Budget ausreichend
                        t = tech.objects.get(technology=form_c.instance.technology)
                        form_c.instance.until_constructed = t.build_time # Einfügen der Bauzeit aus der Tech-DB, muss unter 'form.is_valid()' weil sonst Fehlermelung 'RelatedObjectDoesNotExist'--> Erst nach der Validierung existiert die Formulareingabe
                        instance = form_c.save(commit=False) # Calling save with commit=False returns an instance that is not saved to the database.
                        for i in range(int(form_c.data['amount'])): # Loop over the chosen amount of units
                            instance.id = None # By setting the primary key to None, a new object will be saved each time
                            instance.save() 
                            p.budget -= t.investment_cost   # Budget_neu = Budget_alt - investment
                            p.save()                        # Profile speichern
                        messages.success(request, f'Construction Order Successfull!')
                        return redirect('users-profile')
                    else:
                        messages.warning(request, f'Not enough funds!')
                        form_c = ConstructionForm()  
                else:
                    form_c = ConstructionForm()
            # Formular 3 (PlayerReadyForm)
            form_pr = PlayerReadyForm()
            if 'player_ready' in request.POST:
                if request.method == "POST":
                    form_pr = PlayerReadyForm(request.POST)
                    if form_pr.is_valid():
                        profile.ready = not profile.ready # Ready Status des Spielers wird geändert
                        profile.save()
                        return redirect('users-ready_room')
                    else:
                        messages.warning(request, f'Error! Something went wrong.')
                        form_pr = PlayerReadyForm() 
            # Market Data
            demand_cf_set = demand_cf.objects.filter(key = current_game.variables)
            not_staff = User.objects.filter(is_staff=False)
            player_count = len(Profile.objects.filter(joined_game = current_game).select_related('user').filter(user_id__in = not_staff).values_list('id', flat=True))
            demand = demand_cf_set.get(round = current_round).demand * player_count
            demand_forecast_plus1 = demand_cf_set.get(round = (current_round + 1)).demand * player_count
            demand_forecast_plus2 = demand_cf_set.get(round = (current_round + 2)).demand * player_count
            cf_wind_forecast_plus1 = demand_cf_set.get(round = (current_round + 1)).cf_wind
            cf_solar_forecast_plus1 = demand_cf_set.get(round = (current_round + 1)).cf_pv
            cf_wind_forecast_plus2 = demand_cf_set.get(round = (current_round + 2)).cf_wind
            cf_solar_forecast_plus2 = demand_cf_set.get(round = (current_round + 2)).cf_pv
            carbon_price = settings.objects.get(name='carbon_price', game = current_game).value
            carbon_price_max = settings.objects.get(name='carbon_price_max', game = current_game).value
            # Construction Orders
            constructions = (
                construction.objects
                .filter(user_id=request.user.id)
                .values('technology', 'until_constructed')
                .annotate(entry_count=Count('id'))
                .order_by('until_constructed')
            )
            # Generation System
            generation_systems = (
                generation_system.objects
                .filter(user_id=request.user.id)
                .values('technology', 'until_decommissioned')
                .annotate(entry_count=Count('id'), total_capacity=Sum('capacity'))
                .order_by('until_decommissioned')
            )
        elif profile.ready and sessions.objects.get(name = joined_game).ready: # Spieler ist ready für die nächste Runde und das Spiel ist gestartet
            messages.warning(request, f'Please wait for the next round to start!')
            return redirect('users-ready_room')
        elif not sessions.objects.get(name = joined_game).ready: # Spieler ist einem Spiel beigetreten aber das Spiel ist noch nicht gestartet 
            messages.warning(request, f'Please wait for the Game to start!')
            return redirect('users-waiting_room')
    else: 
        messages.warning(request, f'Please join a Game')
        return redirect('users-join_game')
    # HTML Variablen
    context = { 
        "title": "Generation System",
        'generation_systems': generation_systems,
        "profiles": Profile.objects.filter(user_id=request.user.id),                      # gefiltert nach dem logged-in User
        "constructions": constructions,
        'form_construction': form_c,                                                      # Formular für Bauaufträge
        'form_decommission': form_d,                                                      # Formular für Stilllegung
        'form_playerready': form_pr,
        'round': settings.objects.values_list('value', flat=True).get(name='round', game = joined_game),      # Rundenzähler
        'max_round': settings.objects.values_list('value', flat=True).get(name='max_round', game = joined_game),
        'demand': demand,
        'demand_forecast_plus1': demand_forecast_plus1,
        'demand_forecast_plus2': demand_forecast_plus2,
        'cf_wind': cf_wind,
        'cf_solar': cf_pv,
        'cf_wind_forecast_plus1': cf_wind_forecast_plus1,
        'cf_wind_forecast_plus2': cf_wind_forecast_plus2,
        'cf_solar_forecast_plus1': cf_solar_forecast_plus1,
        'cf_solar_forecast_plus2': cf_solar_forecast_plus2,
        'game': current_game.name,
        'carbon_price': carbon_price,
        'carbon_price_max': carbon_price_max,
        'player_count': player_count,
        "datas": tech.objects.all(),
    } 
    return render(request, 'users/profile.html', context)

#Spielleiter-Profil View
@staff_member_required #only staff members can access staff-profile page
def staff_profil(request):
    profile = Profile.objects.get(user_id = request.user.id)
    if profile.joined_game is not None:
        hosted_game = sessions.objects.get(name = profile.joined_game)
        not_staff = User.objects.filter(is_staff=False)    
        joined_players = Profile.objects.filter(joined_game = hosted_game).exclude(user = request.user)
        # Settings Form
        form_s = SettingsForm(user = request.user) # pass request.user to forms.py
        if 'change_settings' in request.POST:
            if request.method == "POST":
                instance_name = request.POST.get('name')
                instance = settings.objects.get(name=instance_name, game=hosted_game)
                form_s = SettingsForm(request.POST, instance=instance, user=request.user)  # Pass the user again
                if form_s.is_valid():
                    form_s.save()
                    messages.success(request, 'Settings Update Successful!')
                    return redirect('users-staff_profile')
                else:
                    messages.warning(request, 'Error! Check Values')
        # Initialize Next Round Form
        form_n = NextRoundForm()
        if 'next_round' in request.POST:
            if request.method == "POST":
                form_n = NextRoundForm(request.POST)
                if form_n.is_valid() and all(i for i in joined_players.values_list('ready', flat=True)): # Test, ob alle Spieler 'Ready' für die nächste Runde sind
                    # Variables
                    demand_cf_set = demand_cf.objects.filter(key = hosted_game.variables)
                    current_round = settings.objects.get(name='round', game = hosted_game) # Get current Round Number
                    max_round = settings.objects.get(name='max_round', game = hosted_game)
                    # Market Clearing (working)
                    player_count = len(joined_players.select_related('user').filter(user_id__in = not_staff).values_list('id', flat=True))
                    current_demand = (demand_cf_set.get(round = current_round.value).demand * player_count)
                    all_bids = list(bids.objects.filter(user_id__in = joined_players.values_list('user_id', flat=True)).values_list('id', flat=True).order_by('price'))
                    ordered_bids = bids.objects.filter(user_id__in = joined_players.values_list('user_id', flat=True)).order_by('price') # all bids ordered by price
                    bidsum = 0
                    clearing_price = 0.0
                    supply_larger_than_demand = False
                    for b in all_bids:
                        bid = ordered_bids.get(id=b)
                        if (bidsum + bid.amount) < current_demand:
                            bidsum += bid.amount
                            clearing_price = bid.price
                        elif (bidsum + bid.amount) == current_demand:
                            clearing_price = bid.price
                            break
                        elif (bidsum + bid.amount) > current_demand:
                            clearing_price = bid.price
                            supply_larger_than_demand = not supply_larger_than_demand
                            break
                    marginal_bids = list(bids.objects.filter(user_id__in = joined_players.values_list('user_id', flat=True)).values_list('price', flat=True)).count(clearing_price) # Anzahl der Angebote zum Gleichgewichtspreis
                    # Save Clearing Price into DB
                    if settings.objects.filter(name = 'clearing_price', game_id = hosted_game).exists():
                        cp = settings.objects.get(name = 'clearing_price', game_id = hosted_game)
                        cp.value = clearing_price
                        cp.save()
                    else:
                        settings(name = 'clearing_price', value = clearing_price, game_id = hosted_game).save()
                    # Reset Carbon Emissions
                    total_emissions =  0 
                    # Reset Revenue & Total Cost (diese Werte sind nicht kumuliert)
                    for player in joined_players:
                        player.revenue = 0 
                        player.total_cost = 0
                        player.save()
                    # Update Budgets (Revenue, Fuel Cost)
                    for b in all_bids:
                        bid = ordered_bids.get(id=b)
                        user = bid.user.id
                        profile = Profile.objects.get(user_id=user)
                        if bid.price < clearing_price:
                            fuel_cost = tech.objects.get(technology=bid.technology).fuel_cost
                            carbon_price = settings.objects.get(name='carbon_price', game = hosted_game).value
                            carbon_content = tech.objects.get(technology=bid.technology).carbon_content
                            # Profit Calculation
                            revenue = (clearing_price * bid.amount)
                            total_cost = (fuel_cost * bid.amount) + (carbon_price * carbon_content * bid.amount)
                            profit = revenue - total_cost
                            profile.budget += profit
                            profile.revenue += revenue
                            profile.total_cost += total_cost
                            profile.profit += profit # kumuliert
                            profile.save()
                            # Emissions
                            total_emissions += (bid.amount * carbon_content)
                        elif bid.price == clearing_price:
                            if supply_larger_than_demand:
                                # Wenn das Angebot größer als die Nachfrage war:
                                # Wenn mehrere Spieler zum Gleichgewichtspreis anbieten UND das Angebot die Nachfrage übersteigt wird die verbleiden Nachfrage in gleichen Teilen aufgeteilt
                                fuel_cost = tech.objects.get(technology=bid.technology).fuel_cost
                                carbon_price = settings.objects.get(name='carbon_price', game = hosted_game).value
                                carbon_content = tech.objects.get(technology=bid.technology).carbon_content
                                # Profit Calculation
                                remaining_demand_per_player = (current_demand - bidsum) / marginal_bids
                                revenue = (clearing_price * remaining_demand_per_player)
                                total_cost = (fuel_cost * remaining_demand_per_player) + (carbon_price * carbon_content * remaining_demand_per_player)
                                profit = revenue - total_cost
                                profile.budget += profit
                                profile.revenue += revenue
                                profile.total_cost += total_cost
                                profile.profit += profit # kumuliert
                                profile.save()
                                # Emissions
                                total_emissions += (remaining_demand_per_player * carbon_content)
                            else: 
                                # Wenn das Angebot niedriger als die Nachfrage war:
                                fuel_cost = tech.objects.get(technology=bid.technology).fuel_cost
                                carbon_price = settings.objects.get(name='carbon_price', game = hosted_game).value
                                carbon_content = tech.objects.get(technology=bid.technology).carbon_content
                                # Profit Calculation
                                revenue = (clearing_price * bid.amount)
                                total_cost = (fuel_cost * bid.amount) + (carbon_price * carbon_content * bid.amount)
                                profit = revenue - total_cost
                                profile.budget += profit
                                profile.revenue += revenue
                                profile.total_cost += total_cost
                                profile.profit += profit # kumuliert
                                profile.save()
                                # Emissions
                                total_emissions += (bid.amount * carbon_content)
                    # Update Budgets (fixed cost) (working)
                    all_profiles = list(Profile.objects.filter(user_id__in = joined_players.values_list('user_id', flat=True)).values_list('id', flat=True)) # List of all Profile ID's
                    for i in all_profiles:  # for each Profile
                        profile = Profile.objects.get(id=i) # Current Profile
                        generators = generation_system.objects.filter(user_id=profile.user.id).values_list('technology', flat=True) # List of all Generators of current Profile
                        total_fixed_cost = 0 # initialize/reset variable
                        for g in generators: # for each Generator
                            fixed_cost = tech.objects.get(technology=g).fixed_cost
                            total_fixed_cost += fixed_cost
                        profile.budget -= total_fixed_cost
                        profile.total_cost += total_fixed_cost
                        profile.profit -= total_fixed_cost
                        # check if budget would be negativ
                        if profile.budget < 0:
                            profile.budget = 0
                        profile.save()
                    # Update Generation Systems (working)
                    all_generators = list(generation_system.objects.filter(user_id__in = joined_players.values_list('user_id', flat=True)).values_list('id', flat=True))
                    for i in all_generators:
                        generator = generation_system.objects.get(id=i)
                        if generator.until_decommissioned > 1:
                            generator.until_decommissioned -= 1
                            generator.save()
                        else:
                            generator.delete()
                    # Update Construction Orders (working)
                    all_orders = list(construction.objects.filter(user_id__in = joined_players.values_list('user_id', flat=True)).values_list('id', flat=True))
                    for i in all_orders:
                        order = construction.objects.get(id=i)
                        if order.until_constructed > 1: 
                            order.until_constructed -= 1 # Verbleibende Bauzeit anpassen
                            order.save()
                        else: # Wenn Bauzeit abgelaufen, wird der Generator dem Kraftwerkspark hinzugefügt
                            new_generator = generation_system(
                                technology = order.technology, 
                                user_id = order.user.id, 
                                until_decommissioned = tech.objects.values_list('operation_time', flat=True).get(technology=order.technology),
                                capacity = tech.objects.values_list('capacity', flat=True).get(technology=order.technology)
                                )
                            new_generator.save()
                            order.delete()
                    # Flip Ready State of all Players back to False to enable redirect to users-profile
                    for i in all_profiles:
                        profile = Profile.objects.get(id=i) # Current Profile
                        profile.ready = not profile.ready
                        profile.save()
                    # Reset Backup Variables
                    backup.objects.filter(game = hosted_game).delete()
                    # Save Backup Variables
                    total_bid_capacity = ordered_bids.aggregate(Sum('amount'))
                    if total_bid_capacity['amount__sum'] is not None:
                        backup(name = 'total_bid_capacity', value = total_bid_capacity['amount__sum'], game = hosted_game).save()
                    elif total_bid_capacity['amount__sum'] is None:
                        backup(name = 'total_bid_capacity', value = 0, game = hosted_game).save()
                    all_gens = generation_system.objects.filter(user_id__in = joined_players.values_list('user_id', flat=True))
                    total_installed_capacity = all_gens.aggregate(Sum('capacity'))
                    if total_installed_capacity['capacity__sum'] is not None:
                        backup(name = 'total_installed_capacity', value = total_installed_capacity['capacity__sum'], game = hosted_game).save()
                    elif total_installed_capacity['capacity__sum'] is None:
                        backup(name = 'total_installed_capacity', value = 0, game = hosted_game).save()
                    for t in tech.objects.all().values_list('technology', flat=True):
                        temp_var = all_gens.filter(technology = t).aggregate(Sum('capacity'))
                        if temp_var['capacity__sum'] is not None:
                            backup(
                                name = f"total_installed_{t}", 
                                value = temp_var['capacity__sum'], 
                                game = hosted_game
                                ).save()
                        elif temp_var['capacity__sum'] is None:
                            backup(
                                name = f"total_installed_{t}", 
                                value = 0, 
                                game = hosted_game
                                ).save()
                    # Save Bids for Overview (Merit Order)
                    bids_meritorder.objects.filter(user_id__in = joined_players.values_list('user_id', flat=True)).delete() # Reset
                    bid_sum = 0
                    for bid in ordered_bids:
                        if bid.price < clearing_price:
                            bid_sum += bid.amount
                            if  bid_sum < current_demand:
                                bids_meritorder(
                                    user_id = bid.user_id,
                                    technology = bid.technology,
                                    price = bid.price,
                                    amount = bid.amount
                                ).save()
                        elif bid.price == clearing_price:
                            if supply_larger_than_demand:
                                remaining_demand_pp = (current_demand - bid_sum) / marginal_bids
                                bids_meritorder(
                                    user_id = bid.user_id,
                                    technology = bid.technology,
                                    price = bid.price,
                                    amount = remaining_demand_pp
                                ).save()
                            elif not supply_larger_than_demand:
                                bids_meritorder(
                                    user_id = bid.user_id,
                                    technology = bid.technology,
                                    price = bid.price,
                                    amount = bid.amount
                                ).save()
                    # Reset all Players Bids
                    ordered_bids.delete()
                    # Update Carbon Price
                    carbon_price_max = settings.objects.get(name = 'carbon_price_max', game = hosted_game).value # €/t
                    total_emissions_max = settings.objects.get(name = 'total_emissions_max', game = hosted_game).value # tC02
                    new_carbon_price = settings.objects.get(name = 'carbon_price', game = hosted_game)
                    if total_emissions_max > 0:
                        new_carbon_price.value = (total_emissions / total_emissions_max) * carbon_price_max
                    else:
                        new_carbon_price.value = 0
                    new_carbon_price.save()
                    # Flip Game Final state, if the the game reaches the last round
                    if not hosted_game.final and current_round.value == max_round.value:
                        # switch final to true
                        hosted_game.final = not hosted_game.final
                        hosted_game.save()
                        # Final Round Redirect
                        messages.success(request, f'Final Round Initialized!')
                        return redirect('users-overview')
                    # Update Round Counter
                    current_round.value += 1
                    current_round.save()
                    # Redirect
                    messages.success(request, f'Next Round Initialized!')
                    return redirect('users-overview')
                else:
                    messages.warning(request, f'Not all Players are ready!')
                    form_n = NextRoundForm()
        # Start or End the Game
        form_se = StartEndGameSessionForm()
        if 'start_end_game' in request.POST:
            if request.method == "POST":
                form_se = StartEndGameSessionForm(request.POST)
                if form_se.is_valid():
                    # Wenn noch nicht getartet, starte das Spiel
                    if not hosted_game.ready: 
                        hosted_game.ready = not hosted_game.ready 
                        hosted_game.save()
                        # Flip Game Final state to false
                        if hosted_game.final:
                            hosted_game.final = not hosted_game.final
                            hosted_game.save()
                        # Reset Round Counter
                        current_round = settings.objects.get(name='round', game = hosted_game) # Get Round Setting
                        current_round.value = 1                                                
                        current_round.save() 
                        # Reset Generation System of all joined players
                        generation_system.objects.filter(user_id__in = joined_players.values_list('user_id', flat=True)).delete() 
                        # get all technologies and convert to list
                        techlist = list(tech.objects.all().values_list('technology', flat=True))  
                        #for each technology create specified default amount of generation units
                        for tech_var in techlist: 
                            tech_var = tech.objects.filter(technology=tech_var).first()
                            amount = list(tech.objects.filter(technology=tech_var).values_list('default_amount', flat=True))
                            until = list(tech.objects.filter(technology=tech_var).values_list('operation_time', flat=True))
                            cap = list(tech.objects.filter(technology=tech_var).values_list('capacity', flat=True))
                            for p in joined_players:
                                for i in range(amount[0]):
                                    generation_system(user=p.user, technology=tech_var, capacity=cap[0], until_decommissioned=until[0]).save()
                        # Reset Bids of all joined_players
                        bids.objects.filter(user_id__in = joined_players.values_list('user_id', flat=True)).delete()
                        # Reset Construction Orders of all joined_players
                        construction.objects.filter(user_id__in = joined_players.values_list('user_id', flat=True)).delete()
                        # Reset Merit Order Table
                        bids_meritorder.objects.filter(user_id__in = joined_players.values_list('user_id', flat=True)).delete()
                        # Reset Backup Variables
                        backup.objects.filter(game = hosted_game).delete()
                        # Redirect
                        messages.success(request, f'Game Started!')
                        return redirect('users-staff_profile')
                    # Wenn Spiel getartet, beende das Spiel
                    if hosted_game.ready: 
                        hosted_game.ready = not hosted_game.ready
                        hosted_game.save()
                        # Reset Generation System of all joined players
                        generation_system.objects.filter(user_id__in = joined_players.values_list('user_id', flat=True)).delete()
                        # Reset Bids of all joined_players
                        bids.objects.filter(user_id__in = joined_players.values_list('user_id', flat=True)).delete()
                        # Reset Construction Orders of all joined_players
                        construction.objects.filter(user_id__in = joined_players.values_list('user_id', flat=True)).delete()
                        # Reset Merit Order Table
                        bids_meritorder.objects.filter(user_id__in = joined_players.values_list('user_id', flat=True)).delete()
                        # Reset Backup Variables
                        backup.objects.filter(game = hosted_game).delete() 
                        # Alle Spieler werden aus dem Spiel entfernt
                        for p in joined_players: 
                            p.joined_game = None
                            if p.ready:
                                p.ready = not p.ready
                            p.save()
                        messages.success(request, f'Game Ended!')
                        return redirect('users-staff_profile')
        # Delete the Game
        form_dg = DeleteGameSessionForm()
        if 'delete_game' in request.POST:
            if request.method == "POST":
                form_dg = DeleteGameSessionForm(request.POST)
                if form_dg.is_valid():
                    # Reset Bids of all joined_players
                    bids_meritorder.objects.filter(user_id__in = joined_players.values_list('user_id', flat=True)).delete()
                    # Reset Merit Order Table 
                    bids.objects.filter(user_id__in = joined_players.values_list('user_id', flat=True)).delete()
                    # Reset Construction Orders of all joined_players
                    construction.objects.filter(user_id__in = joined_players.values_list('user_id', flat=True)).delete()
                    # Reset Generation System of all joined players
                    generation_system.objects.filter(user_id__in = joined_players.values_list('user_id', flat=True)).delete()
                    # Reset Backup Variables
                    backup.objects.filter(game = hosted_game).delete() 
                    # Remove any remaining joined Players
                    for p in joined_players: 
                        p.joined_game = None
                        if p.ready:
                            p.ready = not p.ready
                        p.save()
                    # Delete Game
                    hosted_game.delete()
                    messages.success(request, f'Game Deleted!')
                    return redirect('users-staff_new_game')
        # Remove Player from Game
        form_rp = RemovePlayerForm()
        if 'remove_player' in request.POST:
            if request.method == "POST":
                form_rp = RemovePlayerForm(request.POST)
                if form_rp.is_valid() and (form_rp.cleaned_data['id'] in joined_players.values_list('user_id', flat=True)): # Check if chosen player is joined game
                    player = joined_players.get(user_id = form_rp.cleaned_data['id'])
                    player.joined_game = None # Remove Player from the game
                    if player.ready:
                        player.ready = not player.ready # Reset Player Ready state
                    player.save()
                    messages.success(request, f'Player Removed!')
                    return redirect('users-staff_profile')
                else:
                    messages.warning(request, f'Player not found!')
                    form_rp = RemovePlayerForm()
        # Enforce Ready Form
        form_enforce = EnforceReadyForm()
        if 'enforce_ready' in request.POST:
            if request.method == "POST":
                form_enforce = EnforceReadyForm(request.POST)
                if form_enforce.is_valid():
                    # Enforce 'Ready' on all joined Players
                    for p in joined_players:
                        if not p.ready:
                            p.ready = not p.ready
                            p.save()
                    messages.success(request, f'All Players are now Ready!')
                    return redirect('users-staff_profile')
                else:
                    messages.warning(request, f'Something went wrong')
                    form_rp = RemovePlayerForm()
        # Export Data as XLSX
        form_export = ExportForm()
        if 'export_data' in request.POST:
            if request.method == "POST":
                form_export = ExportForm(request.POST)
                if form_export.is_valid():
                    # Export the DataFrame to an Excel file
                    round = settings.objects.values_list("value", flat=True).get(name="round", game = hosted_game)
                    response = HttpResponse(content_type='application/ms-excel')
                    response['Content-Disposition'] = f'attachment; filename="exported_data_{hosted_game.name}_Round{round}.xlsx"'
                    # Create a Pandas ExcelWriter object with the response
                    writer = pd.ExcelWriter(response, engine='xlsxwriter')
                    # Iterate over the data you want in each sheet
                    sheet_data = {
                        'Profiles': joined_players,
                        'Generation_Sys': generation_system.objects.filter(user_id__in = joined_players.values_list('user_id', flat=True)),
                        'Constructions': construction.objects.filter(user_id__in = joined_players.values_list('user_id', flat=True)),
                        'Bids': bids.objects.filter(user_id__in = joined_players.values_list('user_id', flat=True)).order_by('price', 'amount'),
                        'Merit Order (previous round)': bids_meritorder.objects.filter(user_id__in = joined_players.values_list('user_id', flat=True)).order_by('price', 'amount'),
                        'Settings': settings.objects.filter(game = hosted_game),
                        # Add more sheets as needed
                    }
                    for sheet_name, queryset in sheet_data.items():
                        df = pd.DataFrame(list(queryset.values()) if queryset else None)
                        if df is not None and not df.empty:
                            df.to_excel(writer, sheet_name=sheet_name, index=False)
                    # Save the ExcelWriter object and return the response
                    writer.close()
                    return response
        # Market Data
        demand_cf_set = demand_cf.objects.filter(key = hosted_game.variables)
        current_round = settings.objects.get(name='round', game = hosted_game).value
        max_round = settings.objects.get(name='max_round', game = hosted_game).value  
        player_count = len(joined_players.select_related('user').filter(user_id__in = not_staff).values_list('id', flat=True))
        demand = demand_cf_set.get(round = current_round).demand * player_count
        demand_forecast_plus1 = demand_cf_set.get(round = (current_round + 1)).demand * player_count
        demand_forecast_plus2 = demand_cf_set.get(round = (current_round + 2)).demand * player_count
        cf_wind = demand_cf_set.get(round = (current_round)).cf_wind
        cf_pv = demand_cf_set.get(round = (current_round)).cf_pv
        cf_wind_forecast_plus1 = demand_cf_set.get(round = (current_round + 1)).cf_wind
        cf_solar_forecast_plus1 = demand_cf_set.get(round = (current_round + 1)).cf_pv
        cf_wind_forecast_plus2 = demand_cf_set.get(round = (current_round + 2)).cf_wind
        cf_solar_forecast_plus2 = demand_cf_set.get(round = (current_round + 2)).cf_pv
    else: # Weiterleitung
        messages.warning(request, f'Please choose a Game to host')
        return redirect('users-staff_new_game')
    context = {
        "title": "Gamemaster Controlcenter",
        "generation_systems": generation_system.objects.filter(user_id__in = joined_players.values_list('user_id', flat=True)).select_related('user').order_by('user_id'), # Queryset mit anderem Queryset filtern: model.objects.filter(field__in = nother_model.objects.filter())
        "profiles": joined_players.select_related('user').order_by('-profit'), # select_related('user') returns related user aswell
        "constructions": construction.objects.filter(user_id__in = joined_players.values_list('user_id', flat=True)).select_related('user').order_by('user_id'),
        'settings': settings.objects.filter(game = hosted_game),
        'bids': bids.objects.filter(user_id__in = joined_players.values_list('user_id', flat=True)).select_related('user').order_by('price'),
        'round': settings.objects.values_list('value', flat=True).get(name='round', game = hosted_game),
        'max_round': max_round,
        'hosted_game': hosted_game,
        "form_settings": form_s,
        "form_nextround": form_n,
        "form_startend": form_se,
        'form_deletegame': form_dg,
        'form_removeplayer': form_rp,
        'form_ex': form_export,
        'form_enforce': form_enforce,
        'demand': demand,
        'demand_forecast_plus1': demand_forecast_plus1,
        'demand_forecast_plus2': demand_forecast_plus2,
        'cf_wind': cf_wind,
        'cf_solar': cf_pv,
        'cf_wind_forecast_plus1': cf_wind_forecast_plus1,
        'cf_wind_forecast_plus2': cf_wind_forecast_plus2,
        'cf_solar_forecast_plus1': cf_solar_forecast_plus1,
        'cf_solar_forecast_plus2': cf_solar_forecast_plus2,
    }
    return render(request,'users/staff_profile.html', context)

# Bidding View (Player)
@login_required
def bidding(request):
    if request.user.is_staff:
        return redirect('users-staff_profile')
    profile = Profile.objects.get(user_id = request.user.id)
    if profile.joined_game is not None: 
        joined_game = sessions.objects.get(name = profile.joined_game)
        # Redirect Players if the game is over
        if joined_game.final:
            messages.success(request, f'The Game has ended!')
            return redirect('users-overview')
        # Spieler ist einem Spiel beigetreten, das Spiel ist gestartet und Spieler ist nicht ready für die nächste Runde
        if joined_game.ready and not profile.ready:
            cap = generation_system.objects.filter(user_id=request.user.id)                              # Kraftwerkspark des Spielers
            techs = tech.objects.values_list('technology', flat=True)                                    # Liste aller Technologien
            current_round = settings.objects.get(game_id = joined_game, name = 'round').value 
            cf_wind = demand_cf.objects.get(key = sessions.objects.get(name = joined_game).variables, round = current_round).cf_wind
            cf_pv = demand_cf.objects.get(key = sessions.objects.get(name = joined_game).variables, round = current_round).cf_pv
            # Summe der Kapazität je Technologie des Spielers (als dict)                                  
            capsum = {} # empty dictionary
            for t in techs:
                if t == 'Wind':
                    capsum[t] = sum(cap.filter(technology = t).values_list('capacity', flat=True)) * cf_wind
                if t == 'Solar':  
                    capsum[t] = sum(cap.filter(technology = t).values_list('capacity', flat=True)) * cf_pv
                elif t != 'Solar' and t != 'Wind':
                    capsum[t] = sum(cap.filter(technology = t).values_list('capacity', flat=True))          
            # Alle Gebote des Spielers 
            user_bids = bids.objects.filter(user_id=request.user.id)        
            # Verbleidende Kapazität zum Anbieten berechnen                                                                                           
            remaining_cap = {}                                                                           
            for t in techs:
                if t == 'Wind':
                    remaining_cap[t] = sum(cap.filter(technology = t).values_list('capacity', flat=True)) * cf_wind
                if t == 'Solar':  
                    remaining_cap[t] = sum(cap.filter(technology = t).values_list('capacity', flat=True)) * cf_pv
                elif t != 'Solar' and t != 'Wind':
                    remaining_cap[t] = sum(cap.filter(technology = t).values_list('capacity', flat=True)) 
            for t in techs:
                remaining_cap[t] -= sum(user_bids.filter(technology=t).values_list('amount', flat=True)) 
            # Submit Bid Form
            form_b = BiddingForm()
            if 'submit_bid' in request.POST:
                if request.method == "POST":
                    form_b = BiddingForm(request.POST)
                    form_b.instance.user = request.user                      # User instance (logged in user) an Formular übergeben
                    if form_b.is_valid() and (remaining_cap[form_b.instance.technology.technology] >= form_b.instance.amount): # Formulat valid UND die verbleibende Kapazität ist ausreichend für das Gebot
                        form_b.save()
                        messages.success(request, f'Bid Successfull!')
                        return redirect('users-bidding')
                    else:
                        messages.warning(request, f'Not enough capacity!')
                else:
                    form_b = BiddingForm()
            # Delete Bid Form
            form_db = DeleteBidForm(user = request.user)
            if 'delete_bid' in request.POST:
                if request.method == "POST":
                    form_db = DeleteBidForm(request.POST, user=request.user)
                    if form_db.is_valid():
                        instance = form_db.cleaned_data.get('bid_id')
                        instance.delete()
                        messages.success(request, f'Bid Deleted!')
                        return redirect('users-bidding')
                    else:
                        messages.warning(request, f'Error!')
                        form_db = DeleteBidForm() 
            # Formular Ready (PlayerReadyForm)
            form_pr = PlayerReadyForm()
            if 'player_ready' in request.POST:
                if request.method == "POST":
                    form_pr = PlayerReadyForm(request.POST)
                    if form_pr.is_valid():
                        profile.ready = not profile.ready # Ready Status des Spielers wird geändert
                        profile.save()
                        return redirect('users-ready_room')
                    else:
                        messages.warning(request, f'Error! Something went wrong.')
                        form_pr = PlayerReadyForm()
            # Market Data
            demand_cf_set = demand_cf.objects.filter(key = joined_game.variables)
            not_staff = User.objects.filter(is_staff=False)
            player_count = len(Profile.objects.filter(joined_game = joined_game).select_related('user').filter(user_id__in = not_staff).values_list('id', flat=True))
            demand = demand_cf_set.get(round = current_round).demand * player_count
            demand_forecast_plus1 = demand_cf_set.get(round = (current_round + 1)).demand * player_count
            demand_forecast_plus2 = demand_cf_set.get(round = (current_round + 2)).demand * player_count
            carbon_price = settings.objects.get(name='carbon_price', game = joined_game).value
        elif joined_game.ready and profile.ready: # Spieler ist einem Spiel beigetreten, das Spiel ist gestartet und Spieler ist ready! für die nächste Runde
            messages.warning(request, f'Please wait for the next round to start!')
            return redirect('users-ready_room')
        elif not joined_game.ready: # Spieler ist einem Spiel beigetreten und das Spiel ist noch nicht gestartet 
            messages.warning(request, f'Please wait for the Game to start!')
            return redirect('users-waiting_room')
    else: # Weiterleitung
        messages.warning(request, f'Please join a Game')
        return redirect('users-join_game')
    # HTML Variablen
    context = {
        "title": "Bidding",
        "bids": bids.objects.filter(user_id=request.user.id).order_by('price', 'amount'),
        "capsum": capsum,
        "form_bidding": form_b,
        'form_playerready': form_pr,
        'form_deletebid': form_db,
        "remaining_cap" : remaining_cap,
        'demand': demand,
        'demand_forecast_plus1': demand_forecast_plus1,
        'demand_forecast_plus2': demand_forecast_plus2,
        'carbon_price': carbon_price,
        "datas": tech.objects.all(),        
    }
    return render(request, 'users/bidding.html', context)

# New Game (Staff) View
@staff_member_required
def staff_new_game(request):
    form_ng = NewGameSessionForm()
    if 'new_game' in request.POST:
        if request.method == "POST":
            form_ng = NewGameSessionForm(request.POST)
            if form_ng.is_valid():
                form_ng.save()
                settings(
                    name = "round",
                    value = 1,
                    game = form_ng.instance,
                ).save()
                settings(
                    name = "carbon_price",
                    value = 0,
                    game = form_ng.instance,
                ).save()
                settings(
                    name = "carbon_price_max",
                    value = 0,
                    game = form_ng.instance,
                ).save()
                settings(
                    name = "total_emissions_max",
                    value = 0,
                    game = form_ng.instance,
                ).save()
                settings(
                    name = "starting_budget",
                    value = 23000,
                    game = form_ng.instance,
                ).save()
                settings(
                    name = "max_round",
                    value = 20,
                    game = form_ng.instance,
                ).save()
                messages.success(request, f'Game created!')
                return redirect('users-staff_new_game')
            else:
                messages.warning(request, f'Choose a unique name!')
    form_hg = HostGameSessionForm()
    if 'host_game' in request.POST:
        if request.method == "POST":
            instance = sessions.objects.get(name=HostGameSessionForm(request.POST).data['name'])
            form_hg = HostGameSessionForm(request.POST, instance=instance)
            if form_hg.is_valid():
                profile = Profile.objects.get(user_id=request.user.id)
                profile.joined_game = sessions.objects.get(name = form_hg.instance.name) 
                profile.save()
                messages.success(request, f'Game hosted!')
                return redirect('users-staff_profile') 
        else:
            messages.warning(request, f'Error!')           
    context = {
        "title": "Create or Join Game",
        "form_newgame": form_ng,
        "form_hostgame": form_hg,
        "game": sessions.objects.all(),
    }
    return render(request,'users/staff_new_game.html', context)

# Join Game View
@login_required
def join_game(request):
    if request.user.is_staff:
        return redirect('users-staff_new_game')
    form_jg = JoinGameSessionForm()
    if request.method == "POST":
        instance = sessions.objects.get(name=JoinGameSessionForm(request.POST).data['name'])
        form_jg = JoinGameSessionForm(request.POST, instance=instance)
        if form_jg.is_valid():
            profile = Profile.objects.get(user_id=request.user.id)
            profile.joined_game = sessions.objects.get(name = form_jg.instance.name)
            profile.revenue = 0
            profile.total_cost = 0
            profile.profit = 0
            profile.budget = settings.objects.get(name = 'starting_budget', game = form_jg.instance.name).value
            profile.save()
            messages.success(request, f'Game joined!')
            return redirect('users-waiting_room') 
    context = {
        "title": "Join Game",
        "game": sessions.objects.all(),
        "form_joingame": form_jg,
    }
    return render(request,'users/join_game.html', context)

# Waiting Room View
@login_required
def waiting_room(request):
    profile = Profile.objects.get(user_id = request.user.id)
    if profile.joined_game is not None and not profile.ready:
        games = sessions.objects.all()
        joined_game = Profile.objects.values_list('joined_game', flat=True).get(user_id = request.user.id)
        for g in games:
            if joined_game == g.name and g.ready:
                messages.success(request, f'Game has started!')
                return redirect('users-profile')
    else:
        return redirect('users-join_game')
    context = {
        "title": "Waiting Room",
    }
    return render(request,'users/waiting_room.html', context)

# Ready Room View
@login_required
def ready_room(request):
    profile = Profile.objects.get(user_id = request.user.id)
    if not profile.ready:
        if sessions.objects.get(name = profile.joined_game).final:
            messages.success(request, f'The Game has ended!!')
            return redirect('users-overview')
        messages.success(request, f'Next Round started!')
        return redirect('users-overview')
    context = {
        "title": "Ready Room",
    }
    return render(request,'users/ready_room.html', context)

# Last Round Overview
@login_required
def overview(request):
    profile = Profile.objects.get(user_id = request.user.id)
    # Staff View
    if request.user.is_staff:
        if profile.joined_game is not None:
            joined_game = sessions.objects.get(name = profile.joined_game)
            round = settings.objects.values_list('value', flat=True).get(name='round', game = joined_game)
            if round > 1:
                joined_players = Profile.objects.filter(joined_game = joined_game)
                clearing_price = settings.objects.get(name = 'clearing_price', game = joined_game).value
                carbon_price = settings.objects.get(name = 'carbon_price', game = joined_game).value
                merit_order = bids_meritorder.objects.filter(user_id__in = joined_players.values_list('user_id', flat=True)).select_related('user').order_by('price')
                not_staff = User.objects.filter(is_staff=False)
                players_ranking = joined_players.select_related('user').filter(user_id__in = not_staff).order_by('-profit')
                player_count = len(joined_players.select_related('user').filter(user_id__in = not_staff).values_list('id', flat=True))
                demand_minus_one = demand_cf.objects.get(round = round, key = joined_game.variables).demand * player_count
                backup_set = backup.objects.filter(game = joined_game)
                total_tech_cap = {}
                for t in tech.objects.all().values_list('technology', flat=True):
                    total_tech_cap[t] = backup_set.get(name = f'total_installed_{t}').value
            else:
                messages.warning(request, f'Overview available after the first Round!')
                return redirect('users-staff_profile')    
        else:
            messages.warning(request, f'Please create or host a Game!')
            return redirect('users-staff_new_game')
    # Player View
    if not request.user.is_staff:
        if profile.joined_game is not None:
            joined_game = sessions.objects.get(name = profile.joined_game)
            if joined_game.ready:
                if not profile.ready:
                    round = settings.objects.values_list('value', flat=True).get(name='round', game = joined_game)
                    if round > 1:
                        joined_players = Profile.objects.filter(joined_game = joined_game)
                        clearing_price = settings.objects.get(name = 'clearing_price', game = joined_game).value
                        carbon_price = settings.objects.get(name = 'carbon_price', game = joined_game).value
                        merit_order = bids_meritorder.objects.filter(user_id__in = joined_players.values_list('user_id', flat=True)).select_related('user').order_by('price')
                        not_staff = User.objects.filter(is_staff=False)
                        players_ranking = joined_players.select_related('user').filter(user_id__in = not_staff).order_by('-profit')
                        player_count = len(joined_players.select_related('user').filter(user_id__in = not_staff).values_list('id', flat=True))
                        demand_minus_one = demand_cf.objects.get(round = round, key = joined_game.variables).demand * player_count
                        backup_set = backup.objects.filter(game = joined_game)
                        total_tech_cap = {}
                        for t in tech.objects.all().values_list('technology', flat=True):
                            total_tech_cap[t] = backup_set.get(name = f'total_installed_{t}').value
                    else:
                        messages.warning(request, f'Overview available after the first Round!')
                        return redirect('users-profile')
                else:
                    messages.warning(request, f'Please wait for the next round to start!')
                    return redirect('users-ready_room')
            else:
                messages.warning(request, f'Please wait for the Game to start!')
                return redirect('users-waiting_room')
        else:
            messages.warning(request, f'Please join a Game!')
            return redirect('users-join_game')
    context = {
        "title": "Overview",
        'clearing_price': clearing_price, 
        'players_ranking': players_ranking,
        'game': joined_game,
        'merit_order': merit_order,
        'accepted_bids': merit_order.filter(user_id = request.user),
        'profile': profile,
        'round': round,
        'last_round': round - 1,
        'carbon_price': carbon_price,
        'demand_minus_one': demand_minus_one,
        'total_bid_capacity': backup_set.get(name = 'total_bid_capacity').value,
        'total_installed_capacity': backup_set.get(name = 'total_installed_capacity').value,
        'total_tech_cap': total_tech_cap,
    }
    return render(request,'users/overview.html', context)


# Dynamic Values Views
from django.http import JsonResponse
def get_dynamic_content(request):
    selected_technology = request.GET.get('selected_technology')
    selected_amount = request.GET.get('selected_amount')
    if selected_technology is None or selected_technology == '':
        context = {
            'investment_cost': None,
            'build_time': None,
        }
    # You can fetch the dynamic content based on the selected values here
    else:
        techs = tech.objects.get(technology = selected_technology)
        investment_cost = techs.investment_cost * int(selected_amount)
        build_time = techs.build_time
        context = {
            'investment_cost': investment_cost,
            'build_time': build_time,
        }

    return JsonResponse(context)

def get_dynamic_content_decommission(request):
    selected_technology_delete = request.GET.get('selected_technology_delete')
    selected_amount_delete = request.GET.get('selected_amount_delete')
    if selected_technology_delete is None or selected_technology_delete == '':
        context = {
            'total_capacity': None,
        }
    # You can fetch the dynamic content based on the selected values here
    else:
        techs = tech.objects.get(technology = selected_technology_delete)
        total_capacity = techs.capacity * int(selected_amount_delete)
        context = {
            'total_capacity': total_capacity,
        }

    return JsonResponse(context)