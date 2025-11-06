import random
import sys

# --- Game Constants -------------------------------------------------------
SEASONS = ['Summer', 'Fall', 'Winter', 'Spring']
SEASON_DATA = {
    'Summer': {
        'base_temp': 25,
        'hunger_mod': 0,
        'thirst_mod': 5,
        'health_mod': 0,
        'trap_chance': 0.6,
        'description': 'Hot days require more water'
    },
    'Fall': {
        'base_temp': 5,
        'hunger_mod': 2,
        'thirst_mod': 0,
        'health_mod': 0,
        'trap_chance': 0.5,
        'description': 'Mild temperatures, good for survival'
    },
    'Winter': {
        'base_temp': -15,
        'hunger_mod': 5,
        'thirst_mod': -5,
        'health_mod': -2,
        'trap_chance': 0.3,
        'description': 'Freezing nights require fire and shelter'
    },
    'Spring': {
        'base_temp': 10,
        'hunger_mod': -2,
        'thirst_mod': 0,
        'health_mod': 1,
        'trap_chance': 0.7,
        'description': 'Cool temperatures, occasional rain'
    }
}

# --- Difficulty presets & runtime modifier --------------------------------
DIFFICULTY_PRESETS = {
	'Easy': {
		'start_gold': 10,
		'start_food': 3,
		'start_water': 3,
		'start_strength': 1,
		'bandit_multiplier': 0.6,    # fewer/less aggressive bandits
		'trap_success_mod': 1.2,
		'merchant_chance_mod': 1.1
        ,
        # small positive bonus to player's d20 checks
        'player_roll_bonus': 2
	},
	'Normal': {
		'start_gold': 5,
		'start_food': 1,
		'start_water': 1,
		'start_strength': 1,
		'bandit_multiplier': 1.0,
        'trap_success_mod': 1.0,
        'merchant_chance_mod': 1.0,
        # no change to player's d20 checks
        'player_roll_bonus': 0
	},
	'Hard': {
		'start_gold': 2,
		'start_food': 0,
		'start_water': 0,
		'start_strength': 1,
		'bandit_multiplier': 1.5,    # more/fiercer bandits
        'trap_success_mod': 0.8,
        'merchant_chance_mod': 0.8,
        # small negative bonus to player's d20 checks
        'player_roll_bonus': -2
	},
     'impossible': {
		'start_gold': 0,
		'start_food': 0,
		'start_water': 0,
		'start_strength': 1,
		'bandit_multiplier': 10.0,
        'trap_success_mod': 0.1,
        'merchant_chance_mod': 0.1,
        # massive negative modifier to player's d20 checks
        'player_roll_bonus': -5
	},
     'HARDCORE': {
		'start_gold': 0,
		'start_food': 0,
		'start_water': 0,
		'start_strength': 1,
		'bandit_multiplier': 100.0,
        'trap_success_mod': 0.0,
        'merchant_chance_mod': 0.0,
        # massive negative modifier to player's d20 checks
        'player_roll_bonus': -50
	}
}

# runtime mod (set by menu/main)
CURRENT_DIFFICULTY = DIFFICULTY_PRESETS['Normal']

# Add customizable debug preset defaults for the dev console
DEFAULT_DEBUG_STATE = {
    'health': 100,
    'hunger': 0,
    'thirst': 0,
    'food': 10,
    'water': 10,
    'shelter': True,
    'day': 1,
    'season': 'Summer',
    'temperature': 25,
    'fire': True,
    'bandages': 5,
    'cloth': 2,
    'strength': 3,
    'agility': 3,
    'endurance': 3,
    'status_effects': {},
    'infection': False,
    'gold': 50,
    'merchant_hostile': False,
    # optional: allow preset to specify which difficulty label to use when starting
    'difficulty': 'Normal'
}
# Mutable preset that the dev console can modify
DEV_DEBUG_PRESET = dict(DEFAULT_DEBUG_STATE)

# --- Utilities -------------------------------------------------------------
def roll_dice(num_dice, sides):
    """Return the sum of rolling `num_dice` d`sides` (keeps randomness centralized)."""
    return sum(random.randint(1, sides) for _ in range(num_dice))


def roll_check(num_dice=1, sides=20):
    """Roll `num_dice` d`sides` for player skill checks and apply difficulty bonus.

    This centralizes difficulty adjustments for d20-style checks. It reads
    `CURRENT_DIFFICULTY['player_roll_bonus']` (default 0) and adds it to the
    raw roll total. Enemy rolls should continue to use `roll_dice` directly so
    difficulty affects the player only.
    """
    base = roll_dice(num_dice, sides)
    try:
        bonus = int(CURRENT_DIFFICULTY.get('player_roll_bonus', 0))
    except Exception:
        bonus = 0
    return base + bonus

def prompt_choice(options):
    """Print numbered options and return zero-based index of the chosen option."""
    for i, opt in enumerate(options, 1):
        print(f"{i}. {opt}")
    while True:
        choice = input("> ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return int(choice) - 1
        print("Please enter the number of your choice.")

# --- Game logic helpers ----------------------------------------------------
def apply_status_effects(state):
    """Apply ongoing status effect damages/benefits."""
    if 'status_effects' not in state:
        state['status_effects'] = {}
    
    effects = state['status_effects']
    if not isinstance(effects, dict):
        state['status_effects'] = {}
        effects = state['status_effects']
    
    if 'poison' in effects:
        damage = roll_dice(1, 4)
        state['health'] -= damage
        effects['poison'] -= 1
        print(f"Poison courses through your veins (-{damage} health)")
        if effects['poison'] <= 0:
            del effects['poison']
            print("The poison has worn off.")
    
    if 'bleeding' in effects:
        damage = roll_dice(1, 3)
        state['health'] -= damage
        effects['bleeding'] -= 1
        print(f"Your wounds continue bleeding (-{damage} health)")
        if effects['bleeding'] <= 0:
            del effects['bleeding']
            print("The bleeding has stopped.")
    
    if 'fever' in effects:
        state['thirst'] = min(100, state['thirst'] + 10)
        effects['fever'] -= 1
        print("The fever makes you extremely thirsty")
        if effects['fever'] <= 0:
            del effects['fever']
            print("Your fever breaks.")

def status_line(state):
    """Enhanced status line with stats and status effects."""
    season = state.get('season', 'Summer')
    temp = state.get('temperature', 0)
    temp_status = "Freezing" if temp <= -10 else "Cold" if temp <= 0 else "Mild" if temp <= 20 else "Hot" if temp <= 30 else "Scorching"
    status_effects = state.get('status_effects') or {}
    if not isinstance(status_effects, dict):
        try:
            status_effects = dict(status_effects)
        except Exception:
            status_effects = {}
    effects_keys = [str(k) for k in status_effects.keys()] if status_effects else []
    # Backwards-compatible: infection is stored as a top-level boolean in some
    # places (e.g. set in `action_scavenge_ruins`). Include it in effects
    # display so the status line shows "infection" when present.
    if state.get('infection'):
        if 'infection' not in effects_keys:
            effects_keys.append('infection')
    effects_str = f" | Effects: {', '.join(effects_keys) if effects_keys else 'None'}"
    stats_str = (f"Str: {state.get('strength',1)} | "
                 f"Agi: {state.get('agility',1)} | "
                 f"End: {state.get('endurance',1)}")
    return (f"Day {state.get('day',1)} | {season} ({temp_status}) | Health: {state.get('health',0)} | "
            f"Hunger: {state.get('hunger',0)} | Thirst: {state.get('thirst',0)} | "
            f"Food: {state.get('food',0)} | Water: {state.get('water',0)} | "
            f"{stats_str} | "
            f"Shelter: {'Yes' if state.get('shelter') else 'No'} | "
            f"Fire: {'Yes' if state.get('fire') else 'No'}" + effects_str)

def apply_night_effects(state, survived_night):
    """Apply hunger/thirst increases and health penalties overnight."""
    # Apply status effects first
    apply_status_effects(state)
    
    season = state.get('season', 'Summer')
    base_temp = SEASON_DATA[season]['base_temp']
    
    # Modify temperature based on shelter and fire
    temp_mod = 0
    if state['shelter']:
        temp_mod += 10
    if state.get('fire'):
        temp_mod += 15
    
    state['temperature'] = base_temp + temp_mod
    
    # Temperature effects on health
    if state['temperature'] <= -10:
        damage = roll_dice(2, 6)
        if not state.get('fire'):
            state['health'] -= damage
            print(f"The freezing cold causes {damage} damage!")
    elif state['temperature'] <= 0:
        if not state.get('fire'):
            damage = roll_dice(1, 4)
            state['health'] -= damage
            print(f"The cold causes {damage} damage.")
    elif state['temperature'] >= 35:
        # Extreme heat increases thirst
        state['thirst'] = min(100, state['thirst'] + 10)
        print("The scorching heat increases your thirst significantly.")
    
    mods = {
        'hunger': SEASON_DATA[season]['hunger_mod'],
        'thirst': SEASON_DATA[season]['thirst_mod'],
        'health': SEASON_DATA[season]['health_mod']
    }
    
    # Apply season-modified penalties
    state['hunger'] = min(100, state['hunger'] + (15 if not state['shelter'] else 10) + mods['hunger'])
    state['thirst'] = min(100, state['thirst'] + (20 if not state['shelter'] else 12) + mods['thirst'])
    
    # Season-specific health effects
    if not state['shelter']:
        state['health'] += mods['health']
    
    # If player couldn't do enough during day, surviving_night False indicates extra penalty
    if state['hunger'] >= 80:
        state['health'] -= 10 if not state['shelter'] else 6
    if state['thirst'] >= 80:
        state['health'] -= 15 if not state['shelter'] else 9
    if not survived_night:
        # small random damage from wounds/exposure if action failed
        state['health'] -= roll_dice(1, 4)

    # clamp health
    state['health'] = max(0, min(100, state['health']))

def check_game_over(state, max_days):
    """Return a tuple (over:bool, message:str)."""
    if state['health'] <= 0:
        return True, "You succumbed to your injuries and the harsh wilds."
    return False, ""

# --- Actions (easy to extend/add more) -----------------------------------
def action_forage(state):
    """Forage for food and water. Risk small injury."""
    print("\nYou search the nearby underbrush and streambeds for edible plants and water.")
    roll = roll_check(1, 20)
    # success thresholds: 10+ find small food/water, 5-9 partial, <5 minor injury
    if roll >= 15:
        food_found = random.randint(1, 3)
        water_found = random.randint(1, 2)
        state['food'] += food_found
        state['water'] += water_found
        print(f"Success! You find {food_found} food and {water_found} water.")
        check_stat_increase(state, 'endurance')
        return True
    elif roll >= 8:
        food_found = 1
        state['food'] += food_found
        print("You scavenge a little food (1). No clean water found.")
        return True
    else:
        wound = roll_dice(1, 6)
        state['health'] -= wound
        print(f"You stumble and injure yourself (-{wound} health). You find nothing useful.")
        return False

def action_hunt(state):
    """Enhanced hunting with strength bonus and stat progression."""
    print("\nYou set traps and stalk game deeper in the woods.")
    roll = roll_check(1, 20) + (0 if not state.get('knife') else 2) + state.get('strength', 0)
    if roll >= 16:
        food_found = random.randint(2, 5)
        state['food'] += food_found
        print(f"Great hunt! You secure {food_found} food.")
        check_stat_increase(state, 'strength', 0.2)  # Higher chance for successful hunt
        return True
    elif roll >= 9:
        food_found = 1
        state['food'] += food_found
        print("You catch something small (1 food).")
        return True
    else:
        injury = roll_dice(1, 8)
        state['health'] -= injury
        print(f"The hunt goes poorly and you get hurt (-{injury} health).")
        return False

def action_rest(state):
    """Rest to regain small amounts of health, but time passes."""
    print("\nYou take time to rest and recover.")
    heal = roll_dice(1, 6) + state.get('endurance', 1) // 2  # Endurance helps healing
    state['health'] = min(100, state['health'] + heal)
    check_stat_increase(state, 'endurance', 0.1)  # Small chance while resting
    print(f"You recover {heal} health.")

def action_drink(state):
    """Consume stored water to reduce thirst."""
    if state['water'] > 0:
        state['water'] -= 1
        old = state['thirst']
        state['thirst'] = max(0, state['thirst'] - 35)
        print(f"You drink water. Thirst {old} -> {state['thirst']}.")
        return True
    print("No clean water to drink.")
    return False

def action_eat(state):
    """Consume stored food to reduce hunger."""
    if state['food'] > 0:
        state['food'] -= 1
        old = state['hunger']
        state['hunger'] = max(0, state['hunger'] - 40)
        print(f"You eat some food. Hunger {old} -> {state['hunger']}.")
        return True
    print("No food to eat.")
    return False

def action_build_shelter(state):
    """Attempt to build or reinforce shelter to reduce future penalties."""
    if state['shelter']:
        print("Your shelter is already secure.")
        return True
    print("\nYou work to build a simple shelter for the night.")
    roll = roll_dice(1, 20) + 2
    if roll >= 12:
        state['shelter'] = True
        print("You build a shelter. Nights will be less harsh now.")
        return True
    else:
        print("Work is tiring, and the shelter is only half-built.")
        return False

# --- New actions / dangers -------------------------------------------------
def action_explore_river(state):
    """Explore the river for water, fish, or danger (slip/drown)."""
    print("\nYou head to the river, scanning for fish and clean water.")
    roll = roll_check(1, 20)
    if roll >= 15:
        food_found = random.randint(1, 3)
        water_found = random.randint(1, 3)
        state['food'] += food_found
        state['water'] += water_found
        print(f"You catch fish and scoop fresh water: +{food_found} food, +{water_found} water.")
        check_stat_increase(state, 'agility')
        return True
    elif roll >= 8:
        water_found = 1
        state['water'] += water_found
        print("You find a clean pool and refill your water (+1).")
        return True
    else:
        injury = roll_dice(1, 8)
        state['health'] -= injury
        print(f"You slip on slick rocks and injure yourself (-{injury} health).")
        # small chance of losing gear
        if random.random() < 0.12 and state.get('knife'):
            state.pop('knife')
            print("Your knife is lost to the river.")
        return False

def action_scavenge_ruins(state):
    """Search nearby ruins for supplies; traps or useful gear may be found."""
    print("\nYou cautiously search ruins and crumbling buildings.")
    bonus = 2 if state.get('hatchet') else 0
    roll = roll_check(1, 20) + bonus
    if roll >= 16:
        found = random.choice(['food', 'water', 'cloth', 'bandage', 'knife', 'hatchet'])
        if found in ('food', 'water'):
            qty = random.randint(1, 3)
            state[found] += qty
            print(f"You find {qty} {found}.")
        elif found == 'cloth':
            state['cloth'] = state.get('cloth', 0) + 1
            print("You salvage some cloth (useful for bandages).")
        elif found == 'bandage':
            state['bandages'] = state.get('bandages', 0) + 1
            print("You find a clean bandage.")
        else:
            state[found] = True
            print(f"You find a useful {found}.")
        return True
    elif roll >= 9:
        # small find
        state['food'] += 1
        print("You scavenge a little food (1).")
        return True
    else:
        damage = roll_dice(1, 10)
        state['health'] -= damage
        # chance of bleeding/infection
        if random.random() < 0.4:
            state['infection'] = True
            print(f"A trap wounds you (-{damage} health) and you may be infected.")
        else:
            print(f"A trap wounds you (-{damage} health).")
        return False

def action_craft_bandage(state):
    """Turn cloth/herbs into bandages for later use to heal bleeding or infection."""
    print("\nYou attempt to craft bandages from cloth/herbs.")
    if state.get('cloth', 0) > 0:
        state['cloth'] -= 1
        state['bandages'] = state.get('bandages', 0) + 1
        print("You craft a bandage from cloth.")
        return True
    # try to make from herbs with a skill check
    roll = roll_check(1, 20)
    if roll >= 12:
        state['bandages'] = state.get('bandages', 0) + 1
        print("You improvise a bandage from herbs.")
        return True
    print("You fail to craft a usable bandage.")
    return False

def action_make_fire(state):
    """Make a fire to cook food, warm the night, and improve success chances."""
    print("\nYou attempt to make a fire.")
    
    # Harder to make fire in certain conditions
    season = state.get('season', 'Summer')
    season_mod = {
        'Winter': -2,  # Wet/frozen wood
        'Summer': 2,   # Dry conditions
        'Spring': 0,
        'Fall': 1
    }[season]
    
    bonus = 2 if state.get('hatchet') else 0
    roll = roll_check(1, 20) + bonus + season_mod
    
    if roll >= 10:
        state['fire'] = True
        # Fire provides immediate warmth
        state['temperature'] = max(state.get('temperature', 0), 5)  # Won't let you freeze with fire
        print("You build a fire. Its warmth will help against the cold tonight.")
        
        # Chance to cook food if you have any
        if state['food'] > 0 and random.random() < 0.3:
            state['food'] += 1
            print("You cook your food more efficiently, making it last longer (+1 food).")
        return True
    else:
        state['fire'] = False
        print("You fail to get a proper fire going.")
        return False

def action_set_trap(state):
    """Set a trap to passively catch food overnight."""
    if state.get('trap_set'):
        print("You already have a trap set.")
        return True
    print("\nYou set a simple trap near trails.")
    roll = roll_check(1, 20)
    if roll >= 8:
        state['trap_set'] = True
        print("Trap set. You might get food in the morning.")
        return True
    else:
        print("The trap is improperly set and likely will not work.")
        return False

def use_bandage(state):
    """Use a bandage to reduce infection/bleeding and heal a bit."""
    if state.get('bandages', 0) > 0:
        state['bandages'] -= 1
        old_health = state.get('health', 0)
        state['health'] = min(100, old_health + 8)

        # Ensure status_effects is a dict
        effects = state.get('status_effects')
        if not isinstance(effects, dict):
            effects = {}
            state['status_effects'] = effects

        # Remove negative status effects from effects dict
        bleeding_stopped = False
        if 'bleeding' in effects:
            del effects['bleeding']
            bleeding_stopped = True
            print("The bandage stops your bleeding.")
        if 'infection' in effects:
            del effects['infection']
            print("The bandage helps clear the infection.")

        # Always clear top-level infection flag when using a bandage
        if state.get('infection'):
            state['infection'] = False
            print("The bandage helps clear your infection.")
        else:
            # Force the infection flag to False even if it wasn't properly set
            state['infection'] = False

        print(f"You use a bandage: health {old_health} -> {state['health']}.")
        return True

    print("No bandages available.")
    return False

def roll_attack(state, enemy):
    """Roll attack with strength bonus."""
    # Player rolls include difficulty-based bonus; enemies do not
    player_roll = roll_check(1, 20) + state.get('strength', 0)
    enemy_roll = roll_dice(1, 20) + enemy.get('strength', 0)
    return player_roll, enemy_roll

def check_stat_increase(state, stat, chance=0.15):
    """Check for potential stat increase and apply it."""
    try:
        if random.random() < chance:
            current = state.get(stat, 1)
            if current < 10:  # Cap stats at 10
                state[stat] = current + 1
                print(f"Your {stat} has increased to {state[stat]}!")
    except Exception as e:
        print(f"Error in stat increase: {e}")

def validate_state(state):
    """Ensure all state values are valid."""
    try:
        # Ensure all required keys exist
        required = {
            'health': 100, 'hunger': 0, 'thirst': 0, 
            'food': 0, 'water': 0, 'gold': 0,
            'strength': 1, 'agility': 1, 'endurance': 1,
            'bandages': 0, 'cloth': 0
        }
        for key, default in required.items():
            if key not in state:
                state[key] = default

        # Clamp numeric values
        state['health'] = max(0, min(100, state['health']))
        state['hunger'] = max(0, min(100, state['hunger']))
        state['thirst'] = max(0, min(100, state['thirst']))
        
        # Check for bleeding damage
        if state.get('status_effects', {}).get('bleeding'):
            state['health'] -= 5
            print("You take 5 damage from bleeding!")
            if state['health'] <= 0:
                print("You bleed out...")
            else:
                print(f"Health: {state['health']}")
        
        # Ensure non-negative resources
        for key in ['food', 'water', 'bandages', 'cloth', 'gold']:
            state[key] = max(0, state.get(key, 0))
        
        # Clamp stats between 1 and 10
        for key in ['strength', 'agility', 'endurance']:
            state[key] = max(1, min(10, state.get(key, 1)))
        
        # Ensure boolean values are correct
        for key in ['shelter', 'fire', 'merchant_hostile', 'infection']:
            if key in state and not isinstance(state[key], bool):
                state[key] = bool(state[key])
        
        # Initialize/fix dictionaries
        if not isinstance(state.get('status_effects'), dict):
            state['status_effects'] = {}
            
        return True
    except Exception as e:
        print(f"Error validating state: {e}")
        return False

def handle_combat(state, enemy):
    """Handle combat with improved error checking."""
    try:
        # Validate enemy
        if not isinstance(enemy, dict):
            print("Invalid enemy data")
            return False
        
        required_enemy = {'name': 'Unknown', 'health': 10, 'strength': 1}
        for key, default in required_enemy.items():
            enemy[key] = enemy.get(key, default)
        
        print(f"\nA {enemy['name']} appears! ({enemy['health']} health, {enemy['strength']} strength)")
        
        while enemy['health'] > 0 and state['health'] > 0:
            options = ["Attack", "Try to flee"]
            choice = prompt_choice(options)
            
            if choice == 0:  # Attack
                player_roll, enemy_roll = roll_attack(state, enemy)
                print(f"You roll {player_roll} vs enemy's {enemy_roll}")
                
                if player_roll >= enemy_roll:
                    damage = roll_dice(1, 6) + state.get('strength', 0)
                    enemy['health'] -= damage
                    print(f"You hit for {damage} damage!")
                    # Chance for special effects on critical hit
                    if player_roll >= enemy_roll + 10:
                        if random.random() < 0.3:
                            enemy['bleeding'] = True
                            print("Your attack causes the enemy to bleed!")
                else:
                    damage = roll_dice(1, 6) + enemy.get('strength', 0)
                    state['health'] -= damage
                    print(f"You are hit for {damage} damage!")
                    # Enemy special attacks
                    if enemy['name'] == 'Snake':
                        if random.random() < 0.4:
                            state.setdefault('status_effects', {})['poison'] = 3
                            print("The snake's venom enters your bloodstream!")
                    elif enemy['name'] == 'Bear' and enemy_roll >= player_roll + 5:
                        state.setdefault('status_effects', {})['bleeding'] = 2
                        print("The bear's claws leave you bleeding!")
            else:  # Flee
                flee_roll = roll_dice(1, 20) + state.get('agility', 0)
                if flee_roll >= 12:
                    check_stat_increase(state, 'agility', 0.2)
                    print("You successfully escape!")
                    return False  # Escaped
                else:
                    damage = roll_dice(1, 4) + enemy.get('strength', 0)
                    state['health'] -= damage
                    print(f"Failed to escape! You take {damage} damage while retreating!")
                    return False  # Still escaped, but took damage
        
        return enemy['health'] <= 0  # True if won, False if lost/fled
    except Exception as e:
        print(f"Combat error: {e}")
        return False

def handle_bandit_encounter(state):
    """Handle a bandit encounter with options to fight, pay, or flee."""
    bandits = random.randint(1, 3)
    gold_demanded = bandits * random.randint(3, 6)
    print(f"\n{bandits} bandits appear! They demand {gold_demanded} gold.")
    
    options = ["Fight", "Pay them", "Try to flee"]
    choice = prompt_choice(options)
    
    if choice == 0:  # Fight
        enemy = {
            'name': f"Bandit Group ({bandits})",
            'health': 10 * bandits,
            'strength': 1 + bandits
        }
        victory = handle_combat(state, enemy)
        if victory:
            loot = random.randint(2, 5) * bandits
            state['gold'] = state.get('gold', 0) + loot
            print(f"You defeat the bandits and find {loot} gold!")
            if random.random() < 0.3:
                state['knife'] = True
                print("You also find a knife!")
        return victory
    
    elif choice == 1:  # Pay
        if state.get('gold', 0) >= gold_demanded:
            state['gold'] -= gold_demanded
            print(f"You pay the bandits {gold_demanded} gold. They leave you alone.")
            return True
        else:
            print("You don't have enough gold! The bandits attack!")
            enemy = {
                'name': f"Angry Bandit Group ({bandits})",
                'health': 10 * bandits,
                'strength': 2 + bandits  # Angry bandits hit harder
            }
            return handle_combat(state, enemy)
    
    else:  # Flee
        flee_roll = roll_dice(1, 20) + state.get('agility', 0)
        if flee_roll >= 12 + bandits:  # Harder to flee from more bandits
            print("You successfully escape!")
            return True
        else:
            damage = roll_dice(2, 4) * bandits
            state['health'] -= damage
            gold_lost = min(state.get('gold', 0), random.randint(1, 5) * bandits)
            state['gold'] = max(0, state.get('gold', 0) - gold_lost)
            print(f"Failed to escape! You take {damage} damage and lose {gold_lost} gold!")
            return False

def handle_shop(state):
    """Simple merchant interaction: buy/sell items and possibly affect merchant attitude."""
    print("\nA traveling merchant approaches, offering a few goods.")
    options = [
        "Buy bandage (5 gold)",
        "Buy water (2 gold)",
        "Sell cloth (1 gold)",
        "Leave"
    ]
    choice = prompt_choice(options)
    if choice == 0:
        cost = 5
        if state.get('gold', 0) >= cost:
            state['gold'] -= cost
            state['bandages'] = state.get('bandages', 0) + 1
            print("You buy a bandage.")
        else:
            print("You don't have enough gold to buy a bandage.")
    elif choice == 1:
        cost = 2
        if state.get('gold', 0) >= cost:
            state['gold'] -= cost
            state['water'] = state.get('water', 0) + 1
            print("You buy a unit of water.")
        else:
            print("You don't have enough gold to buy water.")
    elif choice == 2:
        if state.get('cloth', 0) > 0:
            state['cloth'] -= 1
            state['gold'] = state.get('gold', 0) + 1
            print("You sell a scrap of cloth for 1 gold.")
        else:
            print("You have no cloth to sell.")
    else:
        print("You move on from the merchant.")

def danger_event(state):
	"""Enhanced danger event with better error handling."""
	try:
		if not validate_state(state):
			print("State validation failed, skipping event")
			return
		
		season = state.get('season', 'Summer')
		
		# Modify trap success based on season and difficulty
		if state.get('trap_set'):
			# respect preset trap chance, adjusted by difficulty
			base_chance = SEASON_DATA[season]['trap_chance'] * CURRENT_DIFFICULTY.get('trap_success_mod', 1.0)
			if random.random() < base_chance:
				caught = random.randint(1, 3)
				state['food'] += caught
				print(f"Your trap caught {caught} food overnight.")
			else:
				print("Your trap caught nothing.")
			state.pop('trap_set', None)

		# Season-specific events
		r = random.random()
		if season == 'Winter' and r < 0.15:
			damage = roll_dice(1, 8)
			state['health'] -= damage
			print(f"A freezing night causes {damage} damage!")
		elif season == 'Summer' and r < 0.12:
			state['food'] = max(0, state['food'] - 1)
			print("The intense heat spoils some of your food.")

		# Random major event
		r = random.random()
		if r < 0.10:
			# merchant chance adjusted by difficulty
			if not state.get('merchant_hostile', False) and random.random() < (0.4 * CURRENT_DIFFICULTY.get('merchant_chance_mod', 1.0)):
				handle_shop(state)
			else:
				# Combat encounter with chance of bandits (adjusted)
				if random.random() < (0.3 * CURRENT_DIFFICULTY.get('bandit_multiplier', 1.0)):
					handle_bandit_encounter(state)
				else:
					enemies = [
						{'name': 'Wolf', 'health': 12, 'strength': 2},
						{'name': 'Bear', 'health': 20, 'strength': 4},
						{'name': 'Hostile Survivor', 'health': 15, 'strength': 3},
						{'name': 'Snake', 'health': 8, 'strength': 1}
					]
					enemy = random.choice(enemies)
					victory = handle_combat(state, enemy.copy())
					if victory:
						# Rewards for winning
						food_reward = random.randint(1, 3)
						state['food'] += food_reward
						print(f"You defeat the {enemy['name']} and gain {food_reward} food!")
						# Chance to gain strength from combat
						if random.random() < 0.2:
							state['strength'] += 1
							print("You feel stronger from the battle! (+1 strength)")
		elif r < 0.18:
			# predator attack
			loss = roll_dice(1, 8)
			state['health'] -= loss
			if state['food'] > 0:
				stolen = min(state['food'], random.randint(1, 2))
				state['food'] -= stolen
				print(f"A predator attacks! You are hurt (-{loss} health) and lose {stolen} food.")
			else:
				print(f"A predator attacks! You are hurt (-{loss} health).")
		elif r < 0.25:
			# random traveler passes
			gift = random.choice(['water', 'food', 'cloth'])
			if gift in ('food', 'water'):
				state[gift] += 1
				print(f"A passing traveler leaves behind {gift} for you (+1 {gift}).")
			else:
				state['cloth'] = state.get('cloth',0) + 1
				print("A passing traveler leaves a scrap of cloth.")
		elif r < 0.30:
			# random traveler passes
			gift = random.choice(['water', 'food', 'cloth'])
			if gift in ('food', 'water'):
				state[gift] += 1
				print(f"A passing traveler leaves behind {gift} for you (+1 {gift}).")
			else:
				state['cloth'] = state.get('cloth',0) + 1
				print("A passing traveler leaves a scrap of cloth.")
				
		# Always check for infection damage
		if state.get('infection'):
			# infection worsens without treatment
			damage = roll_dice(1, 6)
			state['health'] -= damage
			print(f"Your infection worsens overnight (-{damage} health).")
	except Exception as e:
		print(f"Error in danger_event: {e}")
		state.setdefault('status_effects', {})
		return

# --- Main menu & main() integration ---------------------------------------
def main_menu():
	"""Show main menu and allow difficulty configuration before starting the game."""
	print("=== Survival Text Game ===")
	# Secret code to open developer console at main menu (hidden):
	DEV_CONSOLE_CODE = "developermode"
	difficulty = 'Normal'
	while True:
		print("\nMain Menu")
		options = [f"Start Game (Difficulty: {difficulty})", "Change Difficulty", "Quit"]
		# Print options but read raw input first to allow secret code
		for i, opt in enumerate(options, 1):
			print(f"{i}. {opt}")
		# Read raw input so the developer console can be triggered by a secret phrase
		raw = input("#> ").strip()
		if raw.lower() == DEV_CONSOLE_CODE:
			# Launch developer console (no game state yet)
			dev_console()
			continue
		# otherwise validate numeric choice
		if raw.isdigit() and 1 <= int(raw) <= len(options):
			choice = int(raw) - 1
		else:
			print("Please enter the number of your choice.")
			continue

		if choice == 0:
			# start game with chosen difficulty
			global CURRENT_DIFFICULTY
			CURRENT_DIFFICULTY = DIFFICULTY_PRESETS.get(difficulty, DIFFICULTY_PRESETS['Normal'])
			main(difficulty)  # call main with chosen difficulty label
			return
		elif choice == 1:
			# choose difficulty
			opts = list(DIFFICULTY_PRESETS.keys())
			print("\nChoose difficulty:")
			idx = prompt_choice(opts)
			difficulty = opts[idx]
			print(f"Difficulty set to {difficulty}")
		else:
			print("Goodbye.")
			sys.exit(0)


def dev_console():
	"""Hidden developer console reachable from main menu by entering the secret
	phrase. Provides simple read/write access to globals useful for testing.

	Commands:
	  help                 Show this help text
	  list                 List available globals (DIFFICULTY_PRESETS, CURRENT_DIFFICULTY)
	  show <name>          Show a global's value (e.g. show CURRENT_DIFFICULTY)
	  set_diff <label>     Set CURRENT_DIFFICULTY to a preset by label
	  start_debug          Start a quick debug game with extra resources
	  debug_show           Show current debug preset used by start_debug
	  debug_list           List editable keys in the debug preset
	  debug_set <k> <v>    Set key k to value v in the debug preset (ints/bools parsed)
	  debug_reset          Reset the debug preset to defaults
	  exit                 Return to main menu

	This console is intentionally minimal and only intended for developers.
	"""
	print("\n[Dev Console] Type 'help' for commands. Type 'exit' to return.")
	while True:
		cmd = input("dev> ").strip()
		if not cmd:
			continue
		parts = cmd.split()
		c = parts[0].lower()

		# helper to parse values for debug_set
		def _parse_value(val_str):
			l = val_str.lower()
			if l in ('true', 'false'):
				return l == 'true'
			try:
				# allow negative ints as well
				if val_str.startswith(('-', '+')) and val_str[1:].isdigit() or val_str.isdigit():
					return int(val_str)
				# try float if needed
				return float(val_str)
			except Exception:
				return val_str

		if c == 'help':
			print(dev_console.__doc__)
		elif c == 'list':
			print("Globals: DIFFICULTY_PRESETS, CURRENT_DIFFICULTY")
		elif c == 'show' and len(parts) > 1:
			name = parts[1]
			val = globals().get(name)
			print(f"{name} = {val}")
		elif c == 'set_diff' and len(parts) > 1:
			label = parts[1]
			if label in DIFFICULTY_PRESETS:
				globals()['CURRENT_DIFFICULTY'] = DIFFICULTY_PRESETS[label]
				print(f"CURRENT_DIFFICULTY set to preset '{label}'")
			else:
				print(f"Unknown difficulty label: {label}")
		elif c == 'start_debug':
			# Start a quick game with the current DEV_DEBUG_PRESET (copy to avoid mutations)
			print("Starting debug game with current debug preset...")
			_debug_state = dict(DEV_DEBUG_PRESET)
			# allow the preset to specify which difficulty label to use
			difficulty_label = _debug_state.pop('difficulty', 'Normal')
			try:
				main(difficulty_label, initial_state=_debug_state)
			except Exception as e:
				print(f"Error running debug game: {e}")
			print("Returned from debug game.")
		elif c == 'debug_show':
			print("Current debug preset:")
			for k, v in DEV_DEBUG_PRESET.items():
				print(f"  {k}: {v}")
		elif c == 'debug_list':
			print("Editable debug preset keys:")
			for k in sorted(DEV_DEBUG_PRESET.keys()):
				print(f"  {k}")
		elif c == 'debug_set' and len(parts) >= 3:
			key = parts[1]
			val = " ".join(parts[2:])
			parsed = _parse_value(val)
			DEV_DEBUG_PRESET[key] = parsed
			print(f"Set debug preset '{key}' = {parsed!r}")
		elif c == 'debug_reset':
			DEV_DEBUG_PRESET.clear()
			DEV_DEBUG_PRESET.update(DEFAULT_DEBUG_STATE)
			print("Debug preset reset to defaults.")
		elif c == 'exit':
			print("Exiting dev console.")
			return
		else:
			print("Unknown command. Type 'help' for a list of commands.")

# adjust main signature to accept difficulty (only minimal changes here)
def main(difficulty_label='Normal', initial_state=None):
    # Configuration
    MAX_DAYS = 20
    DAYS_PER_SEASON = 5

    # If an initial_state is provided (e.g. from dev console), use it.
    # Otherwise construct the normal starting state and apply the chosen difficulty.
    global CURRENT_DIFFICULTY
    if initial_state is None:
        # Enhanced initial state
        state = {
            'health': 100,
            'hunger': 10,
            'thirst': 10,
            'food': 1,
            'water': 1,
            'shelter': False,
            'day': 1,
            'season': 'Summer',
            'temperature': 25,
            'fire': False,
            'bandages': 0,
            'cloth': 0,
            'strength': 1,
            'agility': 1,
            'endurance': 1,
            'status_effects': {},
            'infection': False,  # Explicitly initialize infection status
            'gold': 5,  # Starting gold
            'merchant_hostile': False  # Tracks if you've angered merchants
        }
        # Apply difficulty starting bonuses
        preset = DIFFICULTY_PRESETS.get(difficulty_label, DIFFICULTY_PRESETS['Normal'])
        state['gold'] = preset.get('start_gold', state.get('gold', 0))
        state['food'] = state.get('food', 0) + preset.get('start_food', 0)
        state['water'] = state.get('water', 0) + preset.get('start_water', 0)
        state['strength'] = max(1, state.get('strength', 1) + preset.get('start_strength', 0))
        # set runtime difficulty mod
        CURRENT_DIFFICULTY = preset
    else:
        # Use provided initial_state (dev console debug). Ensure it's a dict copy
        # so modifications won't leak into dev_console's local dict accidentally.
        state = dict(initial_state)
        # Respect/override difficulty if label provided
        preset = DIFFICULTY_PRESETS.get(difficulty_label, CURRENT_DIFFICULTY)
        CURRENT_DIFFICULTY = preset

    print("Welcome to the Survival Text Game.")
    print(f"Survive for {MAX_DAYS} days through changing seasons.")
    print("\nYour starting stats:")
    print(f"Strength: {state['strength']} (combat, hunting)")
    print(f"Agility: {state['agility']} (fleeing, movement)")
    print(f"Endurance: {state['endurance']} (survival, health)")
    print("Each season brings different temperatures:")
    for season, data in SEASON_DATA.items():
        print(f"{season}: {data['description']}")
    print("\nTip: Fire is crucial for survival in cold weather!")

    while True:
        try:
            validate_state(state)  # Now uses global validate_state function

            # Update season
            current_season_idx = ((state['day'] - 1) // DAYS_PER_SEASON) % len(SEASONS)
            state['season'] = SEASONS[current_season_idx]

            if state['day'] % DAYS_PER_SEASON == 1:
                print(f"\nThe {state['season']} season has arrived!")

            print("\n" + "=" * 60)
            print(status_line(state))
            print("-" * 60)
            # Each day the player gets two daytime actions (choice/extendable)
            actions_left = 2
            survived_day = True  # set False if a serious failure happens

            while actions_left > 0:
                print(f"\nActions left this day: {actions_left}")
                options = [
                    "Forage (search for food/water)",
                    "Hunt (bigger risk, bigger reward)",
                    "Explore river (fish / water)",
                    "Scavenge ruins (risk of traps)",
                    "Rest (recover health)",
                    "Eat food",
                    "Drink water",
                    "Make fire (improve nights / cooking)",
                    "Set trap (passive food overnight)",
                    "Build shelter (reduce night penalties)",
                    "Craft bandage (requires cloth/herbs)",
                    "Use bandage (heal/cure effects)",
                    "Trade with merchant (if available)",
                    "Check status / Quit"
                ]
                choice = prompt_choice(options)

                # Update choice handling to match new options list
                if choice == 0:
                    ok = action_forage(state)
                    if not ok and state['health'] <= 0:
                        survived_day = False
                elif choice == 1:
                    ok = action_hunt(state)
                    if not ok and state['health'] <= 0:
                        survived_day = False
                elif choice == 2:
                    ok = action_explore_river(state)
                    if not ok and state['health'] <= 0:
                        survived_day = False
                elif choice == 3:
                    ok = action_scavenge_ruins(state)
                    if not ok and state['health'] <= 0:
                        survived_day = False
                elif choice == 4:
                    action_rest(state)
                elif choice == 5:
                    action_eat(state)
                elif choice == 6:
                    action_drink(state)
                elif choice == 7:
                    action_make_fire(state)
                elif choice == 8:
                    action_set_trap(state)
                elif choice == 9:
                    action_build_shelter(state)
                elif choice == 10:
                    action_craft_bandage(state)
                elif choice == 11:
                    use_bandage(state)
                elif choice == 12:
                    handle_shop(state)
                else:
                    # check inventory and possibility to quit
                    print(status_line(state))
                    print(f"Items: bandages={state.get('bandages',0)}, cloth={state.get('cloth',0)}, "
                          f"knife={state.get('knife',False)}, hatchet={state.get('hatchet',False)}, "
                          f"gold={state.get('gold',0)}")
                    confirm = input("Quit game? (yes/no) ").strip().lower()
                    if confirm == "yes":
                        print("You choose to give up. Game over.")
                        sys.exit(0)
                actions_left -= 1

                # Quick death check mid-day
                if state['health'] <= 0:
                    print("You have collapsed from your injuries.")
                    break

            # Night falls: apply increases/penalties
            try:
                apply_night_effects(state, survived_day)
                danger_event(state)
            except Exception as e:
                print(f"Error during night phase: {e}")
                state['status_effects'] = {}  # Reset status effects if corrupted
                continue

            # Day advance and check win/lose
            state['day'] += 1
            over, message = check_game_over(state, MAX_DAYS)
            if over:
                print("\n" + "=" * 60)
                print(message)
                print("Final status:", status_line(state))
                print("Thank you for playing.")
                break

            # Inform player of end-of-day results
            print("\nNight passes...")
            print(status_line(state))

            # small chance to find an item in ruins/area as random event (kept for backward compatibility)
            if random.random() < 0.08:
                found = random.choice(['knife', 'hatchet'])
                state[found] = True
                print(f"You discover an abandoned {found}! It may help future actions.")

        except Exception as e:
            print(f"Error in game loop: {e}")
            print("Attempting to recover...")
            if not validate_state(state):
                print("Fatal error - game state corrupted")
                break
            continue


if __name__ == "__main__":
	main_menu()

