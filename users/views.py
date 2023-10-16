from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required # login required decorator
from django.contrib.admin.views.decorators import staff_member_required # staff member required decorator
from .forms import (
    UserRegisterForm, # Neuer User Register Formular
    ConstructionForm, # Bauauftrag Formular
    DecommissionForm, # Stillegung Formular
    BiddingForm,      # Formular zur Abgabe von Geboten
    SettingsForm,     # Change Game Settings Form
    NextRoundForm,    # End current round/Start the next round Form
    DeleteBidForm,  
    )
from .models import ( 
    generation_system, # importiert Kraftwerkspark
    Profile,           # importiert Spielerprofile
    construction,      # importiert Bauaufträge
    bids               # importiert Gebote
    )
from game.models import (
    tech, # importiert Start-Kraftwerkspark & Daten (default)
    settings,
    )
from django.contrib.auth.models import User
from django.db.models.signals import post_save  # importing signal
from django.dispatch import receiver # Signale receiver decorator

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
    return render(request, 'users/register.html', {'form': form})

# Create default Generation System for each new registered User
@receiver(post_save, sender=User)
def user_created_handler(sender, instance, created,*args,**kwargs):
    techlist = list(tech.objects.all().values_list('technology', flat=True))  #get all technologies and convert to list
    default_budget = 200000000 # ZUm Setting machen!
    if created:
        for tech_var in techlist: #for each technology create specified default amount for new user
            tech_var = tech.objects.filter(technology=tech_var).first()
            amount = list(tech.objects.filter(technology=tech_var).values_list('default_amount', flat=True))
            until = list(tech.objects.filter(technology=tech_var).values_list('operation_time', flat=True))
            cap = list(tech.objects.filter(technology=tech_var).values_list('capacity', flat=True))
            for i in range(amount[0]):
                generation_system(user=instance, technology=tech_var, capacity=cap[0], until_decommissioned=until[0]).save() #Datenbankeintrag für Kraftwerkspark
        Profile(user=instance, budget=default_budget, revenue=0, profit=0, total_cost=0).save()             #Datenbankeintrag für Profil/Budget
    if instance.is_staff: # wenn ein User zum Spielleiter(Staff) gemacht wird, werden alle seine Kraftwerke+Spielerprofil gelöscht (er spielt nicht mit) --> kann evtl. später direkt bei der Berechnung eingefügt werden, dass Staff nicht berücksichtigt wird
        generation_system.objects.filter(user=instance).delete()
        Profile.objects.filter(user=instance).delete()

# Profile Page view
@login_required # decorator, only logged in users can access profile page
def profil(request):
    # Decommission is only possible, if the generator is not scheduled for current round (e.g. the capacity is not required to fullfill bids)
    cap = generation_system.objects.filter(user_id = request.user.id)                            # Kraftwerkspark des Spielers
    techs = tech.objects.values_list('technology', flat=True)                                    # Liste aller Technologien
    # Summe der Kapazität je Technologie des Spielers (als dict)                                  
    capsum = {} # empty dictionary
    for t in techs:
        capsum[t] = sum(cap.filter(technology = t).values_list('capacity', flat=True))             
    # Alle Gebote des Spielers 
    user_bids = bids.objects.filter(user_id = request.user.id)        
    # Verbleidende Kapazität zum Anbieten berechnen                                                                                           
    remaining_cap = {}                                                                           
    for t in techs:
        remaining_cap[t] = sum(cap.filter(technology = t).values_list('capacity', flat=True))
    for t in techs:
        remaining_cap[t] -= sum(user_bids.filter(technology = t).values_list('amount', flat=True))
    # Formular 1
    form_d = DecommissionForm()
    if 'delete_generator' in request.POST:  # prüfen ob versteckte Boolean Variable aus forms.py in POST vorhanden um Formulare zu unterscheiden 
        if request.method == "POST":
            form_d = DecommissionForm(request.POST)
            gen_sys = generation_system.objects.filter(user_id=request.user)    # Alle Kraftwerke des Spielers
            if form_d.is_valid() and (form_d.cleaned_data['generator_id'] in gen_sys.values_list('id', flat=True)): # Bedingung: Formular valide UND die eingegebene Kraftwerks-ID muss im Kraftwerkspark des Users vorhanden sein
                gen_tech = gen_sys.get(id = form_d.cleaned_data['generator_id']).technology
                if remaining_cap[f'{gen_tech}'] >= gen_sys.get(id = form_d.cleaned_data['generator_id']).capacity:
                    generation_system.objects.filter(id=form_d.cleaned_data['generator_id']).delete() # Kraftwerk löschen
                    messages.success(request, f'Decommission Successfull!')
                    return redirect('users-profile')
                else:
                    messages.warning(request, f'The chosen Generator is already scheduled for production! The remaining { gen_tech } capacity must be larger than capacity of the chosen Generator (ID:{ form_d.cleaned_data["generator_id"] }). Please edit your Biddings acordingly.')
                    form_d = DecommissionForm()
            else:
                messages.warning(request, f'Error! Generator not found. Please enter a valid Generator ID.')
                form_d = DecommissionForm()
        else:
            form_d = DecommissionForm()
    # Formular 2
    form_c = ConstructionForm()
    if 'add_generator' in request.POST:    # prüfen ob versteckte Boolean Variable aus forms.py in POST vorhanden um Formulare zu unterscheiden 
        if request.method == "POST":
            form_c = ConstructionForm(request.POST)
            form_c.instance.user = request.user # User instance (logged in user) an Formular übergeben
            p = Profile.objects.get(user_id=request.user)
            if form_c.is_valid() and (p.budget >= tech.objects.get(technology=form_c.instance.technology).investment_cost): # Bedingung: Formular korrekt ausgefüllt UND Budget ausreichend
                t = tech.objects.get(technology=form_c.instance.technology)
                form_c.instance.until_constructed = t.build_time # Einfügen der Bauzeit aus der Tech-DB, muss unter 'form.is_valid()' weil sonst Fehlermelung 'RelatedObjectDoesNotExist'--> Erst nach der Validierung existiert die Formulareingabe
                form_c.save()                   # Formular in DB speichern
                p.budget -= t.investment_cost   # Budget_neu = Budget_alt - investment
                p.save()                        # Profile aktualisieren
                messages.success(request, f'Construction Order Successfull!')
                return redirect('users-profile')
            else:
                messages.warning(request, f'Not enough funds!')
                form_c = ConstructionForm()  
        else:
            form_c = ConstructionForm()
    # HTML Variablen
    context = { 
        "generation_systems": generation_system.objects.filter(user_id=request.user.id),  # gefiltert nach dem logged-in User
        "profiles": Profile.objects.filter(user_id=request.user.id),                      # gefiltert nach dem logged-in User
        "constructions": construction.objects.filter(user_id=request.user.id),            # gefiltert nach dem logged-in User
        'form_construction': form_c,                                                      # Formular für Bauaufträge
        'form_decommission': form_d,                                                      # Formular für Stilllegung
        'round': settings.objects.values_list('value', flat=True).get(name='round'),      # Rundenzähler
    } 
    return render(request, 'users/profile.html', context)

#Spielleiter-Profil View
#only staff members can access staff-profile page
@staff_member_required
def staff_profil(request):
    # Settings Form
    form_s = SettingsForm()
    if 'change_settings' in request.POST:
        if request.method == "POST":
            instance = settings.objects.get(name=SettingsForm(request.POST).data['name']) # Get Mode Instance based on the chosen Technology in the Form
            form_s = SettingsForm(request.POST, instance=instance)
            if form_s.is_valid():
                form_s.save()
                messages.success(request, f'Settings Update Successfull!')
                return redirect('users-staff_profile')
            else:
                messages.warning(request, f'Error! Check Values')
                form_s = SettingsForm()  
    # Initialize Next Round Form
    form_n = NextRoundForm()
    if 'next_round' in request.POST:
        if request.method == "POST":
            form_n = NextRoundForm(request.POST)
            if form_n.is_valid():
                # Update Round Counter (working)
                current_round = settings.objects.get(name='round') # Get current Round Number
                current_round.value += 1                           # Round+1
                current_round.save()      
                # Market Clearing (working)
                current_demand = settings.objects.get(name='demand').value       # Get current Round Demand
                all_bids = list(bids.objects.all().values_list('id', flat=True).order_by('price'))
                ordered_bids = bids.objects.all().order_by('price')            # all bids ordered by price
                bidsum = 0
                clearing_price = 0
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
                marginal_bids = list(bids.objects.values_list('price', flat=True)).count(clearing_price) # Anzahl der Angebote zum Gleichgewichtspreis
                # Update Budgets (Revenue, Fuel Cost)
                for b in all_bids:
                    bid = ordered_bids.get(id=b)
                    user = bid.user.id
                    profile = Profile.objects.get(user_id=user)
                    if bid.price < clearing_price:
                        fuel_cost = tech.objects.get(technology=bid.technology).fuel_cost
                        carbon_price = settings.objects.get(name='carbon_price').value
                        carbon_content = tech.objects.get(technology=bid.technology).carbon_content
                        profile.budget += (bid.price * bid.amount * 8760) - (fuel_cost * bid.amount * 8760) - (carbon_price * carbon_content * bid.amount * 8760)
                        profile.save()
                    elif bid.price == clearing_price:
                        if supply_larger_than_demand:
                            # Wenn das Angebot größer als die Nachfrage war:
                            # Wenn mehrere Spieler zum Gleichgewichtspreis anbieten UND das Angebot die Nachfrage übersteigt wird die verbleiden Nachfrage in gleichen Teilen aufgeteilt
                            fuel_cost = tech.objects.get(technology=bid.technology).fuel_cost
                            carbon_price = settings.objects.get(name='carbon_price').value
                            carbon_content = tech.objects.get(technology=bid.technology).carbon_content
                            remaining_demand_per_player = (current_demand - bidsum) / marginal_bids
                            profile.budget += (clearing_price * remaining_demand_per_player * 8760) - (fuel_cost * remaining_demand_per_player * 8760) - (carbon_price * carbon_content * remaining_demand_per_player * 8760)
                            profile.save()
                        else: 
                            # Wenn das Angebot niedriger als die Nachfrage war:
                            fuel_cost = tech.objects.get(technology=bid.technology).fuel_cost
                            carbon_price = settings.objects.get(name='carbon_price').value
                            carbon_content = tech.objects.get(technology=bid.technology).carbon_content
                            profile.budget += (clearing_price * bid.amount * 8760) - (fuel_cost * bid.amount * 8760) - (carbon_price * carbon_content * bid.amount * 8760)
                            profile.save()
                # Update Budgets (fixed cost) (working)
                all_profiles = list(Profile.objects.all().values_list('id', flat=True)) # List of all Profile ID's
                for i in all_profiles:  # for each Profile
                    profile = Profile.objects.get(id=i) # Current Profile
                    generators = generation_system.objects.filter(user_id=profile.user.id).values_list('technology', flat=True) # List of all Generators of current Profile
                    total_fixed_cost = 0 # initialize/reset variable
                    for g in generators: # for each Generator
                        fixed_cost = tech.objects.get(technology=g).fixed_cost
                        total_fixed_cost += fixed_cost
                    profile.budget -= total_fixed_cost
                    profile.save()
                # Update Generation Systems (working)
                all_generators = list(generation_system.objects.all().values_list('id', flat=True))
                for i in all_generators:
                    generator = generation_system.objects.get(id=i)
                    if generator.until_decommissioned > 1:
                        generator.until_decommissioned -= 1
                        generator.save()
                    else:
                        generator.delete()
                # Update Construction Orders (working)
                all_orders = list(construction.objects.all().values_list('id', flat=True))
                for i in all_orders:
                    order = construction.objects.get(id=i)
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
                messages.success(request, f'Next Round initialized!')
                return redirect('users-staff_profile')
            else:
                messages.warning(request, f'Error!')
                form_n = NextRoundForm()
    context = {
        "generation_systems": generation_system.objects.all(),
        "profiles": Profile.objects.all(),
        "constructions": construction.objects.all(),
        'settings': settings.objects.all(),
        'bids': bids.objects.all(),
        'round': settings.objects.values_list('value', flat=True).get(name='round'),
        "form_settings": form_s,
        "form_nextround": form_n,
    }
    return render(request,'users/staff_profile.html', context)

# Construction Order View (bisher nur als Test, kann verwendet werden falls nicht alle Formulare auf eine Seite sollen)
@login_required
def construction_order(request):
    context = {
        "constructions": construction.objects.filter(user_id=request.user.id)
    }
    return render(request,'users/construction_order.html', context)

# Bidding View (Spieler)
@login_required
def bidding(request):
    cap = generation_system.objects.filter(user_id=request.user.id)                              # Kraftwerkspark des Spielers
    techs = tech.objects.values_list('technology', flat=True)                                    # Liste aller Technologien
    # Summe der Kapazität je Technologie des Spielers (als dict)                                  
    capsum = {} # empty dictionary
    for t in techs:
        capsum[t] = sum(cap.filter(technology=t).values_list('capacity', flat=True))             
    # Alle Gebote des Spielers 
    user_bids = bids.objects.filter(user_id=request.user.id)        
    # Verbleidende Kapazität zum Anbieten berechnen                                                                                           
    remaining_cap = {}                                                                           
    for t in techs:
        remaining_cap[t] = sum(cap.filter(technology=t).values_list('capacity', flat=True))
    for t in techs:
        remaining_cap[t] -= sum(user_bids.filter(technology=t).values_list('amount', flat=True)) 
    # Formular Gebote Abgeben
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
                form_b = BiddingForm()
        else:
            form_b = BiddingForm()
    # Formular Gebote Löschen
    form_db = DeleteBidForm()
    if 'delete_bid' in request.POST:
        if request.method == "POST":
            form_db = DeleteBidForm(request.POST)
            biddings = bids.objects.filter(user_id = request.user) # Alle Bids des Users
            if form_db.is_valid() and (form_db.cleaned_data['bid_id'] in biddings.values_list('id', flat=True)): # Eingegebene ID muss zu den Bids des Users passen
                bids.objects.get(id = form_db.cleaned_data['bid_id']).delete()
                messages.success(request, f'Bid Deleted!')
                return redirect('users-bidding')
            else:
                messages.warning(request, f'Bid does not Exist! Please Enter a Valid ID from the List Above.')
                form_db = DeleteBidForm()   
    # HTML Variablen
    context = {
        "bids": bids.objects.filter(user_id=request.user.id),
        "capsum": capsum,
        "form_bidding": form_b,
        "remaining_cap" : remaining_cap,
        'form_deletebid': form_db,        
    }
    return render(request, 'users/bidding.html', context)




