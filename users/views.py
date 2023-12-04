# users views
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required # login required decorator
from django.contrib.admin.views.decorators import staff_member_required # staff member required decorator
import pandas as pd # pandas package used for data export
# plotly package used to diplay graphs
import plotly.express as px
import plotly.offline as opy
import plotly.graph_objs as go
# Import forms
from .forms import (
    UserRegisterForm, 
    ConstructionForm, 
    DecommissionForm, 
    BiddingForm,      
    SettingsForm,     
    NextRoundForm,    
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
# Import models
from .models import ( 
    generation_system, 
    Profile,           
    construction,      
    bids,              
    bids_meritorder,
    )
from game.models import (
    tech,       
    settings,   
    sessions,
    demand_cf,
    backup,
    )
from django.contrib.auth.models import User

from django.db.models.signals import post_save  # Importing post save signal
from django.dispatch import receiver # Signal receiver decorator
from django.db.models import Sum, Count
from decimal import Decimal

# User Register view
def register(request):
    if request.method == "POST":
        # Register new user (Form)
        form = UserRegisterForm(request.POST)
        if form.is_valid(): 
            form.save() 
            username = form.cleaned_data.get("username")
            messages.success(request, f'Hello {username}, Your Accout has been created! You ar now able to log in.') # Pop-up message
            return redirect('users-profile') # Redirect user
    else:
        form = UserRegisterForm()
    # Define HTML variables
    context = {
        "title": "Register",
        'form': form,
    }
    return render(request, 'users/register.html', context)

# Create a Player Profile for each new registered User
@receiver(post_save, sender=User) # Get signal from user creation
def user_created_handler(sender, instance, created,*args,**kwargs):
    if created:
        # Set initial profile values
        Profile(user=instance, budget=0, revenue=0, profit=0, total_cost=0).save()       

# Profile Page view
@login_required # Decorator, only logged in users can access profile page
def profil(request):
    # Redirect gamemaster
    if request.user.is_staff:
        return redirect('users-staff_profile')
    # Get data
    profile = Profile.objects.get(user_id = request.user.id)
    joined_game = Profile.objects.values_list('joined_game', flat=True).get(user_id = request.user.id)
    # User can only enter profile if the joined a game and the game has started
    if profile.joined_game is not None:
        if not profile.ready and sessions.objects.get(name = joined_game).ready:
            current_game = sessions.objects.get(name = joined_game)
            # Redirect players if the game is over
            if current_game.final:
                messages.success(request, f'The Game has ended!')
                return redirect('users-overview')
            # Get data
            cap = generation_system.objects.filter(user_id = request.user.id)                       
            current_round = settings.objects.get(game_id = joined_game, name = 'round').value
            cf_wind = demand_cf.objects.get(key = current_game.variables, round = current_round).cf_wind
            cf_pv = demand_cf.objects.get(key = current_game.variables, round = current_round).cf_pv
            user_bids = bids.objects.filter(user_id = request.user.id)        
            # Decommission Generators (Form)
            form_d = DecommissionForm()
            if 'delete_generator' in request.POST: # Check for the forms hidden boolean
                if request.method == "POST":
                    form_d = DecommissionForm(request.POST)
                    if form_d.is_valid():
                        units = form_d.cleaned_data['units']
                        technology = form_d.cleaned_data['techs']
                        # Order units by lifetime rounds left, then delete the first x entries where x = the chosen amount of units
                        gen = generation_system.objects.filter(user = request.user, technology = technology).order_by('until_decommissioned')[:units]
                        # Cannot delete more Generators than exist
                        if len(gen) < units:
                            messages.warning(request, f'You currently do not own {units} {technology} units in your generation system!')
                            return redirect('users-profile')
                        # Calculate player capacities
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
            # Construct Generators (Form)
            form_c = ConstructionForm()
            if 'add_generator' in request.POST: # hidden boolean 
                if request.method == "POST":
                    form_c = ConstructionForm(request.POST)
                    form_c.instance.user = request.user # Pass user instance (logged in user) to form
                    p = Profile.objects.get(user_id=request.user)
                    # Check if players budget is sufficient
                    if form_c.is_valid() and (p.budget >= (tech.objects.get(technology=form_c.instance.technology).investment_cost * int(form_c.data['amount']))): 
                        t = tech.objects.get(technology=form_c.instance.technology)
                        # Get build_time from tech DB, has to be after 'form.is_valid()' otherwise error 'RelatedObjectDoesNotExist'--> Form entries only accessible after validation
                        form_c.instance.until_constructed = t.build_time
                        instance = form_c.save(commit=False) # Calling save with commit=False returns an instance that is not saved to the database
                        for i in range(int(form_c.data['amount'])): # Loop over the chosen amount of units
                            instance.id = None # By setting the primary key to None, a new object will be saved each time
                            instance.save() 
                            p.budget -= t.investment_cost   # Update budget
                            p.save()                        
                        messages.success(request, f'Construction Order Successfull!')
                        return redirect('users-profile')
                    else:
                        messages.warning(request, f'Not enough funds!')
                        form_c = ConstructionForm()  
                else:
                    form_c = ConstructionForm()
            # Change Player "ready" state (Form)
            form_pr = PlayerReadyForm()
            if 'player_ready' in request.POST: # hidden boolean
                if request.method == "POST": 
                    form_pr = PlayerReadyForm(request.POST)
                    if form_pr.is_valid():
                        profile.ready = not profile.ready
                        profile.save()
                        return redirect('users-ready_room')
                    else:
                        messages.warning(request, f'Error! Something went wrong.')
                        form_pr = PlayerReadyForm() 
            # Get data for templates
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
            # Generation Systems
            generation_systems = (
                generation_system.objects
                .filter(user_id=request.user.id)
                .values('technology', 'until_decommissioned')
                .annotate(entry_count=Count('id'), total_capacity=Sum('capacity'))
                .order_by('until_decommissioned')
            )
        # Redirect if player is ready for the next raound (and the game has started)
        elif profile.ready and sessions.objects.get(name = joined_game).ready: 
            messages.warning(request, f'Please wait for the next round to start!')
            return redirect('users-ready_room')
        # Redirect if the game has not yet started 
        elif not sessions.objects.get(name = joined_game).ready: 
            messages.warning(request, f'Please wait for the Game to start!')
            return redirect('users-waiting_room')
    # Redirect if the player has not joined a game
    else: 
        messages.warning(request, f'Please join a Game')
        return redirect('users-join_game')
    # Define HTML Variables
    context = { 
        "title": "Generation System",
        'generation_systems': generation_systems,
        "profiles": Profile.objects.filter(user_id=request.user.id),                     
        "constructions": constructions,
        'form_construction': form_c,                                                     
        'form_decommission': form_d,                                                      
        'form_playerready': form_pr,
        'round': settings.objects.values_list('value', flat=True).get(name='round', game = joined_game),     
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

# Gamemaster profile view
@staff_member_required #only staff members can access staff-profile page
def staff_profil(request):
    profile = Profile.objects.get(user_id = request.user.id)
    # Check if gamemaster has joined a Game
    if profile.joined_game is not None:
        hosted_game = sessions.objects.get(name = profile.joined_game)
        not_staff = User.objects.filter(is_staff=False)
        staff = User.objects.filter(is_staff=True)        
        joined_players = Profile.objects.filter(joined_game = hosted_game).exclude(user = request.user)
        gamemasters = joined_players.select_related('user').filter(user_id__in = staff)
        # Change Settings (Form)
        form_s = SettingsForm(user = request.user) # pass request.user to forms.py
        if 'change_settings' in request.POST: # hidden boolean 
            if request.method == "POST":
                instance_name = request.POST.get('name')
                instance = settings.objects.get(name=instance_name, game=hosted_game)
                form_s = SettingsForm(request.POST, instance=instance, user=request.user)  # pass request.user to forms.py
                if form_s.is_valid():
                    form_s.save()
                    messages.success(request, 'Settings Update Successful!')
                    return redirect('users-staff_profile')
                else:
                    messages.warning(request, 'Error! Check Values')
        # Initialize the next round (Form)
        form_n = NextRoundForm()
        if 'next_round' in request.POST: # hidden boolean 
            if request.method == "POST":
                form_n = NextRoundForm(request.POST)
                # Check if all players are 'ready' for the next round
                if form_n.is_valid() and all(i for i in joined_players.values_list('ready', flat=True)): 
                    # Get data
                    demand_cf_set = demand_cf.objects.filter(key = hosted_game.variables)
                    current_round = settings.objects.get(name='round', game = hosted_game)
                    max_round = settings.objects.get(name='max_round', game = hosted_game)
                    # Market Clearing
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
                    marginal_bids = list(bids.objects.filter(user_id__in = joined_players.values_list('user_id', flat=True)).values_list('price', flat=True)).count(clearing_price) # number of bids with price=clearing_price
                    # Save Clearing Price into DB
                    if settings.objects.filter(name = 'clearing_price', game_id = hosted_game).exists():
                        cp = settings.objects.get(name = 'clearing_price', game_id = hosted_game)
                        cp.value = clearing_price
                        cp.save()
                        backup(name = 'clearing_price', value = clearing_price, game = hosted_game, round = current_round.value).save() # Save into Clearing Price History
                    else:
                        backup(name = 'clearing_price', value = clearing_price, game = hosted_game, round = current_round.value).save() # Save into Clearing Price History
                        settings(name = 'clearing_price', value = clearing_price, game_id = hosted_game).save()
                    # Reset Carbon Emissions
                    total_emissions =  0 
                    # Reset Revenue & Total Cost (not cumulative)
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
                            profile.profit += profit # cumulative
                            profile.save()
                            # Emissions
                            total_emissions += (bid.amount * carbon_content)
                        elif bid.price == clearing_price:
                            if supply_larger_than_demand:
                                # Check if supply was larger than demand
                                # If marginal_bids is larger than 1 the remaining demand is split evenly between the marginal bids
                                fuel_cost = tech.objects.get(technology=bid.technology).fuel_cost
                                carbon_price = settings.objects.get(name='carbon_price', game = hosted_game).value
                                carbon_content = tech.objects.get(technology=bid.technology).carbon_content
                                # Profit Calculation
                                remaining_demand_per_player = Decimal((current_demand - bidsum) / marginal_bids)
                                revenue = (clearing_price * remaining_demand_per_player)
                                total_cost = (fuel_cost * remaining_demand_per_player) + (carbon_price * carbon_content * remaining_demand_per_player)
                                profit = revenue - total_cost
                                profile.budget += profit
                                profile.revenue += revenue
                                profile.total_cost += total_cost
                                profile.profit += profit # cumulative
                                profile.save()
                                # Emissions
                                total_emissions += (remaining_demand_per_player * carbon_content)
                            else: 
                                # Check if supply was lower than demand
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
                                profile.profit += profit # cumulative
                                profile.save()
                                # Emissions
                                total_emissions += (bid.amount * carbon_content)
                    # Update Budgets (fixed cost) 
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
                    # Calculate new Carbon Price
                    carbon_price_max = settings.objects.get(name = 'carbon_price_max', game = hosted_game).value # €/t
                    total_emissions_max = settings.objects.get(name = 'total_emissions_max', game = hosted_game).value # tC02
                    new_carbon_price = settings.objects.get(name = 'carbon_price', game = hosted_game)
                    backup(name = 'carbon_price', value = new_carbon_price.value, game = hosted_game, round = current_round.value).save() # Save into Carbon Price history
                    if total_emissions_max > 0:
                        new_carbon_price.value = (total_emissions / total_emissions_max) * carbon_price_max
                    else:
                        new_carbon_price.value = 0
                    new_carbon_price.save()
                    # Save Backup Variables
                    total_bid_capacity = ordered_bids.aggregate(Sum('amount'))
                    if total_bid_capacity['amount__sum'] is not None:
                        backup(name = 'total_bid_capacity', value = total_bid_capacity['amount__sum'], game = hosted_game, round = current_round.value).save()
                    elif total_bid_capacity['amount__sum'] is None:
                        backup(name = 'total_bid_capacity', value = 0, game = hosted_game, round = current_round.value).save()
                    all_gens = generation_system.objects.filter(user_id__in = joined_players.values_list('user_id', flat=True))
                    total_installed_capacity = all_gens.aggregate(Sum('capacity'))
                    if total_installed_capacity['capacity__sum'] is not None:
                        backup(name = 'total_installed_capacity', value = total_installed_capacity['capacity__sum'], game = hosted_game, round = current_round.value).save()
                    elif total_installed_capacity['capacity__sum'] is None:
                        backup(name = 'total_installed_capacity', value = 0, game = hosted_game, round = current_round.value).save()
                    for t in tech.objects.all().values_list('technology', flat=True):
                        temp_var = all_gens.filter(technology = t).aggregate(Sum('capacity'))
                        if temp_var['capacity__sum'] is not None:
                            backup(
                                name = f"total_installed_{t}", 
                                value = temp_var['capacity__sum'], 
                                game = hosted_game,
                                round = current_round.value
                                ).save()
                        elif temp_var['capacity__sum'] is None:
                            backup(
                                name = f"total_installed_{t}", 
                                value = 0, 
                                game = hosted_game,
                                round = current_round.value
                                ).save()
                    # Update Generation Systems
                    all_generators = list(generation_system.objects.filter(user_id__in = joined_players.values_list('user_id', flat=True)).values_list('id', flat=True))
                    for i in all_generators:
                        generator = generation_system.objects.get(id=i)
                        # update remaining lifetime, delete if = 0
                        if generator.until_decommissioned > 1:
                            generator.until_decommissioned -= 1
                            generator.save()
                        else:
                            generator.delete()
                    # Update Construction Orders 
                    all_orders = list(construction.objects.filter(user_id__in = joined_players.values_list('user_id', flat=True)).values_list('id', flat=True))
                    for i in all_orders:
                        order = construction.objects.get(id=i)
                        # update remaining construction time, move to generation system if = 0
                        if order.until_constructed > 1: 
                            order.until_constructed -= 1 
                            order.save()
                        else: 
                            new_generator = generation_system(
                                technology = order.technology, 
                                user_id = order.user.id, 
                                until_decommissioned = tech.objects.values_list('operation_time', flat=True).get(technology=order.technology),
                                capacity = tech.objects.values_list('capacity', flat=True).get(technology=order.technology)
                                )
                            new_generator.save()
                            order.delete()
                    # Flip 'ready' state of all Players back to False to enable redirect to users-profile
                    for i in all_profiles:
                        profile = Profile.objects.get(id=i) 
                        profile.ready = not profile.ready
                        profile.save()
                    # Save Bids for Gamemaster Overview (Merit Order)
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
                    # Flip game final state, if the the game reaches the end of the last round
                    if not hosted_game.final and current_round.value == max_round.value:
                        # Switch final to true
                        hosted_game.final = not hosted_game.final
                        hosted_game.save()
                        # Final round redirect
                        messages.success(request, f'Final Round Initialized!')
                        return redirect('users-overview')
                    # Update round counter
                    current_round.value += 1
                    current_round.save()
                    # redirect 
                    messages.success(request, f'Next Round Initialized!')
                    return redirect('users-overview')
                else:
                    messages.warning(request, f'Not all Players are ready!')
                    form_n = NextRoundForm()
        # Start or End the Game (Form)
        form_se = StartEndGameSessionForm()
        if 'start_end_game' in request.POST: # hidden boolean
            if request.method == "POST":
                form_se = StartEndGameSessionForm(request.POST)
                if form_se.is_valid():
                    # Check if the game has started
                    if not hosted_game.ready: 
                        # Flip game state 
                        hosted_game.ready = not hosted_game.ready 
                        hosted_game.save()
                        # Flip game final state to false
                        if hosted_game.final:
                            hosted_game.final = not hosted_game.final
                            hosted_game.save()
                        # Reset round counter
                        current_round = settings.objects.get(name='round', game = hosted_game) # Get Round Setting
                        current_round.value = 1                                                
                        current_round.save() 
                        # Reset Generation System of all joined players
                        generation_system.objects.filter(user_id__in = joined_players.values_list('user_id', flat=True)).delete() 
                        # Get all technologies and convert to list
                        techlist = list(tech.objects.all().values_list('technology', flat=True))  
                        # For each technology create specified default amount of generation units
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
                    # If the game is running, end the game
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
                        # Reset Round Counter
                        current_round = settings.objects.get(name='round', game = hosted_game)
                        current_round.value = 1                                                
                        current_round.save() 
                        # Reset all Player Profiles
                        for p in joined_players: 
                            if p.ready:
                                p.ready = not p.ready
                            p.revenue = 0
                            p.total_cost = 0
                            p.profit = 0
                            p.budget = settings.objects.get(name = 'starting_budget', game = hosted_game).value
                            p.save()
                        messages.success(request, f'Game Ended!')
                        return redirect('users-staff_profile')
        # Delete the Game (Form)
        form_dg = DeleteGameSessionForm()
        if 'delete_game' in request.POST: # hidden boolean
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
        # Remove Player from Game (Form)
        form_rp = RemovePlayerForm()
        if 'remove_player' in request.POST:
            if request.method == "POST":
                form_rp = RemovePlayerForm(request.POST)
                if form_rp.is_valid() and (form_rp.cleaned_data['id'] in joined_players.values_list('user_id', flat=True)): # Check if chosen player has joined game
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
        # Enforce Ready (Form)
        form_enforce = EnforceReadyForm()
        if 'enforce_ready' in request.POST: # hidden boolean
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
        # Export Data as XLSX (Form)
        form_export = ExportForm()
        if 'export_data' in request.POST:
            if request.method == "POST":
                # Export only possible if all players are ready or if the game is finished
                if not all(i for i in joined_players.values_list('ready', flat=True)) and not hosted_game.final:
                    messages.warning(request, f'Not all Players are Ready! Make shure all players are Ready for the next round before attempting data export.')
                    return redirect('users-staff_profile')
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
        # Get data
        demand_cf_set = demand_cf.objects.filter(key = hosted_game.variables)
        current_round = settings.objects.get(name='round', game = hosted_game).value
        max_round = settings.objects.get(name='max_round', game = hosted_game).value  
        player_count = len(joined_players.select_related('user').filter(user_id__in = not_staff).values_list('id', flat=True))
    else: # Redirect
        messages.warning(request, f'Please choose a Game to host')
        return redirect('users-staff_new_game')
    # Define HTML variables
    context = {
        "title": "Gamemaster Controlcenter",
        "generation_systems": generation_system.objects.filter(user_id__in = joined_players.values_list('user_id', flat=True)).select_related('user').order_by('user_id'), # Queryset mit anderem Queryset filtern: model.objects.filter(field__in = nother_model.objects.filter())
        "profiles": joined_players.select_related('user').filter(user_id__in = not_staff).order_by('-profit'), # select_related('user') returns related user aswell
        "constructions": construction.objects.filter(user_id__in = joined_players.values_list('user_id', flat=True)).select_related('user').order_by('user_id'),
        'settings': settings.objects.filter(game = hosted_game).exclude(name = 'round').exclude(name = 'clearing_price'),
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
        'player_count': player_count,
        'demand_cf_set': demand_cf_set.order_by('round'),
        'gamemasters': gamemasters,
    }
    return render(request,'users/staff_profile.html', context)

# Bidding View (Player)
@login_required # only logged in users can view this page
def bidding(request):
    # Redirect gamemaster
    if request.user.is_staff:
        return redirect('users-staff_profile')
    profile = Profile.objects.get(user_id = request.user.id)
    # Check if player has joined a game
    if profile.joined_game is not None: 
        joined_game = sessions.objects.get(name = profile.joined_game)
        # Redirect Players if the game is over
        if joined_game.final:
            messages.success(request, f'The Game has ended!')
            return redirect('users-overview')
        # Check if the player is 'ready' for the next round and the game has started
        if joined_game.ready and not profile.ready:
            cap = generation_system.objects.filter(user_id=request.user.id)                            
            techs = tech.objects.values_list('technology', flat=True)                                  
            current_round = settings.objects.get(game_id = joined_game, name = 'round').value 
            cf_wind = demand_cf.objects.get(key = sessions.objects.get(name = joined_game).variables, round = current_round).cf_wind
            cf_pv = demand_cf.objects.get(key = sessions.objects.get(name = joined_game).variables, round = current_round).cf_pv
            # Sum capacity of each technology of the current user as dict                              
            capsum = {} # empty dictionary
            for t in techs:
                if t == 'Wind':
                    capsum[t] = sum(cap.filter(technology = t).values_list('capacity', flat=True)) * cf_wind
                if t == 'Solar':  
                    capsum[t] = sum(cap.filter(technology = t).values_list('capacity', flat=True)) * cf_pv
                elif t != 'Solar' and t != 'Wind':
                    capsum[t] = sum(cap.filter(technology = t).values_list('capacity', flat=True))          
            # All bids of the current user
            user_bids = bids.objects.filter(user_id=request.user.id)        
            # Calculate remaining capacities                                                                                           
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
            # Submit Bid (Form)
            form_b = BiddingForm()
            if 'submit_bid' in request.POST:
                if request.method == "POST":
                    form_b = BiddingForm(request.POST)
                    form_b.instance.user = request.user  # Pass user instance (logged in user) to form
                    # Check if remaining capacity is sufficient
                    if form_b.is_valid() and (remaining_cap[form_b.instance.technology.technology] >= form_b.instance.amount):
                        form_b.save()
                        messages.success(request, f'Bid Successfull!')
                        return redirect('users-bidding')
                    else:
                        messages.warning(request, f'Not enough capacity!')
                else:
                    form_b = BiddingForm()
            # Delete Bid (Form)
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
            # Player declares 'ready' for the next round(Form)
            form_pr = PlayerReadyForm()
            if 'player_ready' in request.POST:
                if request.method == "POST":
                    form_pr = PlayerReadyForm(request.POST)
                    if form_pr.is_valid():
                        profile.ready = not profile.ready # Flip 'ready' state
                        profile.save()
                        return redirect('users-ready_room')
                    else:
                        messages.warning(request, f'Error! Something went wrong.')
                        form_pr = PlayerReadyForm()
            # Get data
            demand_cf_set = demand_cf.objects.filter(key = joined_game.variables)
            not_staff = User.objects.filter(is_staff=False)
            player_count = len(Profile.objects.filter(joined_game = joined_game).select_related('user').filter(user_id__in = not_staff).values_list('id', flat=True))
            demand = demand_cf_set.get(round = current_round).demand * player_count
            demand_forecast_plus1 = demand_cf_set.get(round = (current_round + 1)).demand * player_count
            demand_forecast_plus2 = demand_cf_set.get(round = (current_round + 2)).demand * player_count
            carbon_price = settings.objects.get(name='carbon_price', game = joined_game).value
        # If the player is 'ready' and the game has started redirect to ready room
        elif joined_game.ready and profile.ready: 
            messages.warning(request, f'Please wait for the next round to start!')
            return redirect('users-ready_room')
        # If the Game has not yet started redirect to waiting room
        elif not joined_game.ready: 
            messages.warning(request, f'Please wait for the Game to start!')
            return redirect('users-waiting_room')
    else: 
        messages.warning(request, f'Please join a Game')
        return redirect('users-join_game')
    # Define HTML Variables
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

# New Game View (Staff)
@staff_member_required # only staff users (gamemasters) can view this page
def staff_new_game(request):
    # Ccreate a new Game Session (Form)
    form_ng = NewGameSessionForm()
    if 'new_game' in request.POST:
        if request.method == "POST":
            form_ng = NewGameSessionForm(request.POST)
            if form_ng.is_valid():
                form_ng.save()
                # Define and save inital settings of the game session
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
    # Host a game session (Form)
    form_hg = HostGameSessionForm()
    if 'host_game' in request.POST:
        if request.method == "POST":
            instance = sessions.objects.get(name=HostGameSessionForm(request.POST).data['name'])
            form_hg = HostGameSessionForm(request.POST, instance=instance)
            if form_hg.is_valid():
                profile = Profile.objects.get(user_id=request.user.id)
                profile.joined_game = sessions.objects.get(name = form_hg.instance.name) # the session is saved in the gamemasters profile
                profile.save()
                messages.success(request, f'Game hosted!')
                return redirect('users-staff_profile') 
        else:
            messages.warning(request, f'Error!')  
    # Define HTML Variables
    context = {
        "title": "Create or Join Game",
        "form_newgame": form_ng,
        "form_hostgame": form_hg,
        "game": sessions.objects.all(),
    }
    return render(request,'users/staff_new_game.html', context)

# Join Game View
@login_required # only logged in users can view this page
def join_game(request):
    if request.user.is_staff:
        return redirect('users-staff_new_game')
    # Joining a game (Form)
    form_jg = JoinGameSessionForm()
    if request.method == "POST":
        instance = sessions.objects.get(name=JoinGameSessionForm(request.POST).data['name'])
        form_jg = JoinGameSessionForm(request.POST, instance=instance)
        if form_jg.is_valid():
            profile = Profile.objects.get(user_id=request.user.id)
            profile.joined_game = sessions.objects.get(name = form_jg.instance.name)
            # Reset player profile when joining a new game
            profile.revenue = 0
            profile.total_cost = 0
            profile.profit = 0
            profile.budget = settings.objects.get(name = 'starting_budget', game = form_jg.instance.name).value
            profile.save()
            messages.success(request, f'Game joined!')
            return redirect('users-waiting_room') 
    # Define HTML Variables
    context = {
        "title": "Join Game",
        "game": sessions.objects.all(),
        "form_joingame": form_jg,
    }
    return render(request,'users/join_game.html', context)

# Waiting Room View (Player are redirected here if they are waiting for their session to start)
@login_required # only logged in users can view this page
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
    # Define HTML Variables
    context = {
        "title": "Waiting Room",
    }
    return render(request,'users/waiting_room.html', context)

# Ready Room View (Player are redirected here if they are waiting for the next round to start)
@login_required # only logged in users can view this page
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

# Last Round Overview (Results)
@login_required # only logged in users can view this page
def overview(request):
    profile = Profile.objects.get(user_id = request.user.id)
    # Staff View
    if request.user.is_staff:
        if profile.joined_game is None:
            messages.warning(request, f'Please create or host a Game!')
            return redirect('users-staff_new_game')
        joined_game = sessions.objects.get(name = profile.joined_game)
        if not joined_game.ready:
            messages.warning(request, f'Overview available after the first Round!')
            return redirect('users-staff_profile')
        round = settings.objects.values_list('value', flat=True).get(name='round', game = joined_game)
        if round == 1:
            messages.warning(request, f'Overview available after the first Round!')
            return redirect('users-staff_profile')
        previous_round = round - 1    
        joined_players = Profile.objects.filter(joined_game = joined_game)
        clearing_price = settings.objects.get(name = 'clearing_price', game = joined_game).value
        carbon_price = settings.objects.get(name = 'carbon_price', game = joined_game).value
        merit_order = bids_meritorder.objects.filter(user_id__in = joined_players.values_list('user_id', flat=True)).select_related('user').order_by('price')
        not_staff = User.objects.filter(is_staff=False)
        players_ranking = joined_players.select_related('user').filter(user_id__in = not_staff).order_by('-profit')
        player_count = len(joined_players.select_related('user').filter(user_id__in = not_staff).values_list('id', flat=True))
        demand_minus_one = demand_cf.objects.get(round = previous_round, key = joined_game.variables).demand * player_count
        backup_set = backup.objects.filter(game = joined_game)
        total_tech_cap = {}
        for t in tech.objects.all().values_list('technology', flat=True):
            total_tech_cap[t] = backup_set.get(name = f'total_installed_{t}', round = previous_round).value
        total_installed_capacity = backup_set.get(name = 'total_installed_capacity', round = previous_round).value
    # Player View
    if not request.user.is_staff:
        # Redirect if Player has not joined a Game 
        if profile.joined_game is None:
            messages.warning(request, f'Please join a Game!')
            return redirect('users-join_game')
        # Redirect if the joined game has not started
        joined_game = sessions.objects.get(name = profile.joined_game)
        if not joined_game.ready:
            messages.warning(request, f'Please wait for the Game to start!')
            return redirect('users-waiting_room')
        # Redirect if Player has declared 'ready' for the next round
        if profile.ready:
            messages.warning(request, f'Please wait for the next round to start!')
            return redirect('users-ready_room')
        # Redirect if the game is in the first round
        round = settings.objects.values_list('value', flat=True).get(name='round', game = joined_game)
        if round == 1:
            messages.warning(request, f'Overview available after the first Round!')
            return redirect('users-profile')
        previous_round = round - 1  
        joined_players = Profile.objects.filter(joined_game = joined_game)
        clearing_price = settings.objects.get(name = 'clearing_price', game = joined_game).value
        carbon_price = settings.objects.get(name = 'carbon_price', game = joined_game).value
        merit_order = bids_meritorder.objects.filter(user_id__in = joined_players.values_list('user_id', flat=True)).select_related('user').order_by('price')
        not_staff = User.objects.filter(is_staff=False)
        players_ranking = joined_players.select_related('user').filter(user_id__in = not_staff).order_by('-profit')
        player_count = len(joined_players.select_related('user').filter(user_id__in = not_staff).values_list('id', flat=True))
        demand_minus_one = demand_cf.objects.get(round = previous_round, key = joined_game.variables).demand * player_count
        backup_set = backup.objects.filter(game = joined_game)
        technology = tech.objects.all().values_list('technology', flat=True)
        total_tech_cap = {}
        for t in technology:
            total_tech_cap[t] = backup_set.get(name = f'total_installed_{t}', round = previous_round).value
        total_installed_capacity = backup_set.get(name = 'total_installed_capacity', round = previous_round).value
    
    # plotly charts 
    # Chart 1 (Total Capacity per Technology, Bar Chart)
    capacity_data = {
        'technology': list(total_tech_cap.keys()),
        'total_capacity_tech': list(total_tech_cap.values()),
    }
    capacity_bar_chart = px.bar(
        x = capacity_data['technology'],
        y = capacity_data['total_capacity_tech'],
        color = capacity_data['technology'],
        title = '<b>Total Installed Capacity Per Technology <br>(All Players)</b>',
        labels={'x': 'Technology', 'y': 'Capacity [MW]'},  # Set axis labels
    )
    # Update layout
    capacity_bar_chart.update_layout(
        title_font=dict(
        size=20,  # Set the size as needed
        color='black',
        ),
        legend_title_text='Technology',
    )
    # Define hoverover data
    capacity_bar_chart.update_traces(hovertemplate='Technology: %{x}<br>Capacity: %{y} MW<br>')
    # Convert figure to an HTML string representation
    plot_capacity_bar_chart = capacity_bar_chart.to_html(full_html = False)

    # Chart 2 (Demand & Total Capacity, Bar Chart)
    capacity_bar_chart_2 = px.bar(
        x = ('Demand', 'Total Installed Capacity'),
        y = (demand_minus_one, total_installed_capacity),
        color = ('Demand', 'Total Installed Capacity'),
        color_discrete_map = {
            "Demand": "slategrey",
            "Total Installed Capacity": "green",
            },
        title = '<b>Demand and Total Installed Capacity <br> (All Players, All Technologies)</b>',
        labels={'x': '', 'y': 'MW'}, 
    )
    # Update layout
    capacity_bar_chart_2.update_layout(
        title_font=dict(
        size=20,  
        color='black',
        ),
        legend_title_text='Legend',
    )
    # Define hoverover data
    capacity_bar_chart_2.update_traces(hovertemplate='%{y} MW')
    # Convert figure to an HTML string representation
    plot_capacity_bar_chart_2 = capacity_bar_chart_2.to_html(full_html = False)

    # Chart 3 (Carbon Price & Clearing Price, Line Chart)
    price_data = backup.objects.filter(game = joined_game).order_by('round')
    # Values
    x_values = list(price_data.values_list('round', flat=True).distinct())
    y1_values = list(price_data.filter(name = 'clearing_price').values_list('value', flat=True))
    y2_values = list(price_data.filter(name = 'carbon_price').values_list('value', flat=True))
    hover_template = '%{y} €/MWh' # Define the hovertemplate
    # Lines
    trace1 = go.Scatter(x=x_values, y=y1_values, mode='lines+markers', name='Clearing Price', line=dict(color='green'), marker=dict(size=10), hovertemplate=hover_template)
    trace2 = go.Scatter(x=x_values, y=y2_values, mode='lines+markers', name='Carbon Price', line=dict(color='crimson'), marker=dict(size=10), hovertemplate=hover_template)
    data = [trace1, trace2]
    # Layout
    layout = go.Layout(
        title='<b>Clearing Price & Carbon Price History</b>', 
        xaxis=dict(title='Round', type='linear', tickmode='linear', tick0=0, dtick=1), 
        yaxis=dict(title='Price [€/MWh]'),
        hovermode="x",
        separators= ',.', # Define decimal seperator
        )
    
    price_line_chart = go.Figure(data=data, layout=layout)
    plot_price_line_chart = opy.plot(price_line_chart, auto_open=False, output_type='div')

    # Define HTML Variables
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
        'previous_carbon_price': price_data.get(round = previous_round, name = 'carbon_price').value,
        'demand_minus_one': demand_minus_one,
        'total_bid_capacity': backup_set.get(name = 'total_bid_capacity', round = previous_round).value,
        'total_installed_capacity': total_installed_capacity,
        'total_tech_cap': total_tech_cap,
        'plot_capacity_bar_chart': plot_capacity_bar_chart,
        'plot_capacity_bar_chart_2': plot_capacity_bar_chart_2,
        'plot_price_line_chart': plot_price_line_chart,
    }
    return render(request,'users/overview.html', context)


# Dynamic Value Views: used to display dynamic content in HTML templates via JavaScript
from django.http import JsonResponse

# Dynamic Values for the construction form
def get_dynamic_content(request):
    # pass selected values
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

# Dynamic Values for the decommission form
def get_dynamic_content_decommission(request):
    # pass selected values
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