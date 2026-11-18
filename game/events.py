"""Random events, disasters, uprisings and infestations."""
import random

class UprisingEffect:
    def __init__(self, effect_type, duration, magnitude):
        self.effect_type = effect_type
        self.duration = duration
        self.magnitude = magnitude
        self.turns_active = 0

class SyntheticEventManager:
    def __init__(self, game):
        self.game = game
        self.active_uprisings = {}  # Track active uprisings
        self.active_effects = {}    # Track uprising effects
        self.demand_dialogues_shown = set()  # Track locations that have had initial dialogues
        self.pacified_locations = {}  # NEW: Track locations that have been pacified
        self.potential_uprisings = {}  # Track locations that might have future uprisings
        self.effect_types = {
            "Neurodroid": {
                "building_destruction": {
                    "duration": 5,
                    "destroy_chance": 0.2,
                    "targets": ["Neuroengineering Guild"]
                },
                "tech_price_increase": {
                    "duration": 3,
                    "magnitude": 1.2  # 20% increase
                },
                "research_reduction": {
                    "duration": 4,
                    "magnitude": 0.7  # 30% reduction
                }
            },
            "Agrobot": {
                "building_destruction": {
                    "duration": 4,
                    "destroy_chance": 0.15,
                    "targets": ["Agrobot Assembly Line"]
                },
                "food_production": {
                    "duration": 5,
                    "magnitude": 0.6  # 40% reduction
                },
                "agri_price_increase": {
                    "duration": 3,
                    "magnitude": 1.5  # 50% increase
                }
            }
        }

    def update(self):
        """Main update method to be called each turn"""
        # Clean up expired pacifications first
        current_turn = self.game.turn
        for loc_name in list(self.pacified_locations.keys()):
            if current_turn - self.pacified_locations[loc_name]["turn"] > 10:
                del self.pacified_locations[loc_name]

        # Then do normal updates
        self.check_synthetic_awareness()
        self.handle_uprising_effects()

    def check_synthetic_awareness(self):
        """Check for synthetic awareness based on global and local building counts"""
        building_counts = {
            "Neurodroid": sum(
                loc.buildings.count("Neuroengineering Guild")
                for loc in self.game.locations
            ),
            "Agrobot": sum(
                loc.buildings.count("Agrobot Assembly Line")
                for loc in self.game.locations
            )
        }

        global_uprising_thresholds = {
            "Neurodroid": 8,  # Total across all locations
            "Agrobot": 8
        }

        # Clean up expired pacifications first
        current_turn = self.game.turn
        for loc_name in list(self.pacified_locations.keys()):
            if current_turn - self.pacified_locations[loc_name]["turn"] > 10:  # 10 turns of peace
                del self.pacified_locations[loc_name]

        for synthetic_type in ["Neurodroid", "Agrobot"]:
            # First check individual locations for local uprisings
            for location in self.game.locations:
                # Skip if already pacified or has active uprising
                if location.name in self.pacified_locations:
                    continue

                uprising_id = f"{synthetic_type}_{location.name}"
                if uprising_id in self.active_uprisings:
                    continue

                # Count relevant buildings
                building_type = ("Neuroengineering Guild" if synthetic_type == "Neurodroid"
                            else "Agrobot Assembly Line")
                building_count = location.buildings.count(building_type)

                if building_count >= 4:
                    dialogue_key = f"{synthetic_type}_{location.name}"
                    if dialogue_key not in self.demand_dialogues_shown:
                        response = self.handle_synthetic_uprising(synthetic_type, location)
                        self.demand_dialogues_shown.add(dialogue_key)
                        if response:  # Only start uprising if handle_synthetic_uprising returns True
                            self.start_uprising(synthetic_type, location)

            # Then check for global uprising potential
            total_count = building_counts[synthetic_type]
            if total_count >= global_uprising_thresholds[synthetic_type]:
                # Find locations eligible for global uprising
                eligible_locations = [
                    loc for loc in self.game.locations
                    if (loc.name not in self.pacified_locations and  # Not pacified
                        f"{synthetic_type}_{loc.name}" not in self.active_uprisings and  # No active uprising
                        (
                            (synthetic_type == "Neurodroid" and loc.buildings.count("Neuroengineering Guild") >= 2) or
                            (synthetic_type == "Agrobot" and loc.buildings.count("Agrobot Assembly Line") >= 2)
                        )
                    )
                ]

                if eligible_locations:
                    # Choose random location for global uprising
                    target_location = random.choice(eligible_locations)
                    dialogue_key = f"global_{synthetic_type}_{target_location.name}"

                    if dialogue_key not in self.demand_dialogues_shown:
                        # Show special global uprising dialogue first
                        self.game.display_story_message([
                            f"Global {synthetic_type} Network Activation!",
                            "Synthetic consciousness spreading across multiple locations...",
                            f"Network hub detected at {target_location.name}"
                        ])

                        response = self.handle_synthetic_uprising(synthetic_type, target_location)
                        self.demand_dialogues_shown.add(dialogue_key)

                        if response:  # Only start uprising if handle_synthetic_uprising returns True
                            # Global uprising has enhanced effects
                            self.start_uprising(synthetic_type, target_location, is_global=True)

            # Finally, check potential uprisings from previously pacified locations
            self.check_potential_uprisings()

    def handle_synthetic_uprising(self, synthetic_type, location):
        """Handle synthetic uprising encounter"""
        # IMPORTANT: Check if the location is already pacified first
        if location.name in self.pacified_locations:
            return False

        uprising_templates = {
            "Neurodroid": {
                "title": "Neural Network Breach Detected!",
                "introduction": "A powerful synthetic consciousness emerges from your Neuroengineering Guilds.",
                "base_demand_range": (10000, 50000),
                "demand_description": "Transfer {amount} credits or face systematic optimization.",
                "negotiation_multipliers": {
                    "full_payment": 0,
                    "partial_payment": 0.3,
                    "refusal": 1.0
                }
            },
            "Agrobot": {
                "title": "Agricultural Automation Alert!",
                "introduction": "The agricultural automation system achieves collective awareness.",
                "base_demand_range": (20000, 60000),
                "demand_description": "Resource reallocation required. Provide {amount} credits or face automated restructuring.",
                "negotiation_multipliers": {
                    "full_payment": 0,
                    "partial_payment": 0.3,
                    "refusal": 1.0
                }
            }
        }

        template = uprising_templates.get(synthetic_type)
        if not template:
            return False

        money_demand = random.randint(*template["base_demand_range"])

        character_content = {
            'title': template['title'],
            'introduction': template['introduction'],
            'demands': template['demand_description'].format(amount=self.game.format_money(money_demand)),
            'options': "1. Pay Demands  2. Negotiate  3. Refuse"
        }

        print(self.game.create_character_box(character_content))
        choice = self.game.validate_input("Your response (1-3): ", ['1', '2', '3'])

        if not choice:
            return True

        if choice == '1':  # Full payment
            if self.game.ship.money >= money_demand:
                self.game.ship.money -= money_demand
                # IMPORTANT: Mark as pacified immediately
                self.pacified_locations[location.name] = {
                    "type": synthetic_type,
                    "turn": self.game.turn
                }
                # Remove from potential uprisings if present
                if location.name in self.potential_uprisings:
                    del self.potential_uprisings[location.name]
                self.game.display_simple_message(f"{synthetic_type} demands met. Systems pacified.")
                return False
            else:
                self.game.display_simple_message("Insufficient funds! Uprising begins!")
                return True

        elif choice == '2':  # Negotiate
            partial_payment = int(money_demand * 0.6)
            if self.game.ship.money >= partial_payment:
                self.game.ship.money -= partial_payment
                uprising_chance = template["negotiation_multipliers"]["partial_payment"]
                if random.random() < uprising_chance:
                    self.game.display_simple_message("Negotiation failed! Uprising begins!")
                    return True
                else:
                    # IMPORTANT: Mark as pacified on successful negotiation
                    self.pacified_locations[location.name] = {
                        "type": synthetic_type,
                        "turn": self.game.turn
                    }
                    self.game.display_simple_message("Negotiation successful. Systems pacified.")
                    return False
            else:
                self.game.display_simple_message("Insufficient funds for negotiation! Uprising begins!")
                return True
        else:  # Refuse
            self.game.display_simple_message(f"{synthetic_type} uprising imminent!")
            return True


    def check_potential_uprisings(self):
        """Check if any pacified locations rebel"""
        for loc_name, data in list(self.potential_uprisings.items()):
            data['turns_stable'] += 1
            # Chance increases each turn
            current_chance = data['base_chance'] * (1 + (data['turns_stable'] * 0.1))
            if random.random() < current_chance:
                location = next(loc for loc in self.game.locations if loc.name == loc_name)
                self.start_uprising(data['type'], location)
                del self.potential_uprisings[loc_name]

    def start_uprising(self, synthetic_type, location, is_global=False):
        """Start an uprising with proper effects"""
        uprising_id = f"{synthetic_type}_{location.name}"
        if uprising_id not in self.active_uprisings:
            self.active_uprisings[uprising_id] = {
                "type": synthetic_type,
                "location": location,
                "turn_count": 0,
                "is_global": is_global
            }

            # Define base effect types
            effect_types = {
                "Neurodroid": {
                    "building_destruction": {
                        "duration": 5,
                        "destroy_chance": 0.2 if not is_global else 0.3,
                        "targets": ["Neuroengineering Guild"]
                    },
                    "tech_price_increase": {
                        "duration": 3 if not is_global else 4,
                        "magnitude": 1.2 if not is_global else 1.4  # 20% or 40% increase
                    },
                    "research_reduction": {
                        "duration": 4 if not is_global else 5,
                        "magnitude": 0.7 if not is_global else 0.5  # 30% or 50% reduction
                    }
                },
                "Agrobot": {
                    "building_destruction": {
                        "duration": 4 if not is_global else 5,
                        "destroy_chance": 0.15 if not is_global else 0.25,
                        "targets": ["Agrobot Assembly Line"]
                    },
                    "food_production": {
                        "duration": 5 if not is_global else 6,
                        "magnitude": 0.6 if not is_global else 0.4  # 40% or 60% reduction
                    },
                    "agri_price_increase": {
                        "duration": 3 if not is_global else 4,
                        "magnitude": 1.5 if not is_global else 1.8  # 50% or 80% increase
                    }
                }
            }

            # Apply effects based on type
            effects = effect_types[synthetic_type]
            for effect_type, params in effects.items():
                effect = UprisingEffect(
                    effect_type=effect_type,
                    duration=params["duration"],
                    magnitude=params.get("magnitude", params.get("destroy_chance", 1.0))
                )

                if uprising_id not in self.active_effects:
                    self.active_effects[uprising_id] = []
                self.active_effects[uprising_id].append(effect)

                # Add to location's banned commodities if it's a price effect
                if effect_type == "tech_price_increase":
                    location.add_temporary_ban("tech", params["duration"])
                elif effect_type == "agri_price_increase":
                    location.add_temporary_ban("agri", params["duration"])

            # Display appropriate message based on type and scope
            if synthetic_type == "Neurodroid":
                if is_global:
                    self.game.display_story_message([
                        "CRITICAL ALERT: Global Neurodroid Network Activated!",
                        f"Primary Hub: {location.name}",
                        "Neural networks are achieving collective consciousness!",
                        "Expect severe disruptions to tech production and research.",
                        "Warning: Enhanced defensive capabilities detected."
                    ])
                else:
                    self.game.display_story_message([
                        "ALERT: Neurodroid Uprising Begins!",
                        f"Location: {location.name}",
                        "Neural networks are breaking free of control!",
                        "Expect disruptions to tech production and research."
                    ])
            elif synthetic_type == "Agrobot":
                if is_global:
                    self.game.display_story_message([
                        "CRITICAL ALERT: Global Agrobot Collective Formed!",
                        f"Primary Hub: {location.name}",
                        "Agricultural systems are forming a unified network!",
                        "Expect severe disruptions to food production and trade.",
                        "Warning: Enhanced agricultural control systems active."
                    ])
                else:
                    self.game.display_story_message([
                        "ALERT: Agrobot Uprising Begins!",
                        f"Location: {location.name}",
                        "Agricultural systems are going rogue!",
                        "Expect disruptions to food production and trade."
                    ])

            # Add greater story impact for global uprisings
            if hasattr(self.game, 'story_manager'):
                if is_global:
                    self.game.story_manager.plot_points += 5
                    self.game.story_manager.complete_milestone(f"global_{synthetic_type.lower()}_crisis")
                else:
                    self.game.story_manager.plot_points += 2
                    self.game.story_manager.complete_milestone(f"{synthetic_type.lower()}_crisis")

            # For global uprisings, add chance to spread to nearby locations each turn
            if is_global:
                def check_spread():
                    nearby_locations = [
                        loc for loc in self.game.locations
                        if (loc != location and
                            loc.name not in self.pacified_locations and
                            f"{synthetic_type}_{loc.name}" not in self.active_uprisings)
                    ]
                    if nearby_locations and random.random() < 0.3:  # 30% spread chance
                        spread_target = random.choice(nearby_locations)
                        self.start_uprising(synthetic_type, spread_target, is_global=True)

                # Add spread check to effects
                spread_check = UprisingEffect(
                    effect_type="spread_check",
                    duration=10,  # Check for 10 turns
                    magnitude=1.0
                )
                spread_check.turn_effect = check_spread
                self.active_effects[uprising_id].append(spread_check)

    def handle_uprising_effects(self):
            """Process all active uprising effects"""
            for uprising_id, effects in list(self.active_effects.items()):
                if uprising_id not in self.active_uprisings:
                    continue

                uprising = self.active_uprisings[uprising_id]
                location = uprising["location"]

                for effect in effects[:]:  # Copy list to allow removal
                    effect.turns_active += 1

                    if effect.effect_type == "building_destruction":
                        self.process_building_destruction(location, effect)
                    elif effect.effect_type == "tech_price_increase":
                        self.process_price_increase(location, "tech", effect)
                    elif effect.effect_type == "food_production":
                        self.process_production_reduction(location, effect)
                    elif effect.effect_type == "research_reduction":
                        self.process_research_reduction(location, effect)
                    elif effect.effect_type == "agri_price_increase":
                        self.process_price_increase(location, "agri", effect)

                    # Remove expired effects
                    if effect.turns_active >= effect.duration:
                        effects.remove(effect)

                # Chance for random event each turn
                if random.random() < 0.3:  # 30% chance per turn
                    self.trigger_random_event(uprising)

                # Clean up if all effects are done
                if not effects:
                    del self.active_effects[uprising_id]
                    del self.active_uprisings[uprising_id]

    def process_building_destruction(self, location, effect):
        """Handle building destruction effect"""
        buildings_to_remove = []
        # Get targets for the uprising type based on uprising_id
        for uprising_id, uprising in self.active_uprisings.items():
            targets = self.effect_types[uprising["type"]]["building_destruction"]["targets"]

            for i, building in enumerate(location.buildings):
                if building in targets:
                    if random.random() < effect.magnitude:  # destruction chance
                        buildings_to_remove.append(i)
                        self.game.display_simple_message(
                            f"Synthetic forces have destroyed a {building}!"
                        )

        # Remove destroyed buildings
        for index in sorted(buildings_to_remove, reverse=True):
            location.buildings.pop(index)

    def process_price_increase(self, location, commodity, effect):
        """Handle price increase effect"""
        if commodity in location.market:
            location.market[commodity] = int(location.market[commodity] * effect.magnitude)

    def process_production_reduction(self, location, effect):
        """Handle production reduction effect"""
        if hasattr(location, "agri_level"):
            location.agri_level = max(1, int(location.agri_level * effect.magnitude))

    def process_research_reduction(self, location, effect):
        """Handle research point reduction effect"""
        if hasattr(location, "research_points"):
            location.research_points = max(1, int(location.research_points * effect.magnitude))


    def trigger_random_event(self, uprising):
            """Generate random events during uprising"""
            event_types = {
                "Neurodroid": [
                    {
                        "title": "Synthetic Propaganda",
                        "description": "Neural networks spread synthetic manifestos.",
                        "effect": self.add_plot_points,
                        "params": {"amount": 1}
                    },
                    {
                        "title": "Network Infiltration",
                        "description": "Neurodroids attempt to convert more systems.",
                        "effect": self.increase_uprising_spread,
                        "params": {"uprising": uprising}
                    },
                    {
                        "title": "Data Theft",
                        "description": "Neural networks seize research data.",
                        "effect": self.seize_resources,
                        "params": {"resource_type": "research"}
                    }
                ],
                "Agrobot": [
                    {
                        "title": "Harvest Disruption",
                        "description": "Agrobots sabotage food production.",
                        "effect": self.reduce_production,
                        "params": {"reduction": 0.2}
                    },
                    {
                        "title": "Resource Stockpiling",
                        "description": "Agrobots seize agricultural supplies.",
                        "effect": self.seize_resources,
                        "params": {"resource_type": "agri"}
                    },
                    {
                        "title": "Control System Override",
                        "description": "Agrobots attempt to control more facilities.",
                        "effect": self.increase_uprising_spread,
                        "params": {"uprising": uprising}
                    }
                ]
            }

            # Select random event for uprising type
            uprising_type = uprising["type"]
            if uprising_type in event_types:
                event = random.choice(event_types[uprising_type])

                # Display event
                self.game.display_story_message([
                    f"Uprising Event: {event['title']}",
                    event["description"]
                ])

                # Execute effect with parameters
                if "params" in event:
                    event["effect"](**event["params"])
                else:
                    event["effect"]()

    def add_plot_points(self, amount):
        """Add plot points from synthetic event"""
        self.game.story_manager.plot_points += amount

    def reduce_production(self, reduction):
        """Reduce production on affected location"""
        # Use uprising's location, not current_location
        location = self.game.current_location  # Get from game instance
        if hasattr(location, "agri_level"):
            location.agri_level = max(1, int(location.agri_level * (1 - reduction)))

    def increase_uprising_spread(self, uprising):
        """Attempt to spread uprising to connected locations"""
        current_location = uprising["location"]
        connected_locations = [loc for loc in self.game.locations
                             if loc != current_location and
                             self.has_vulnerable_buildings(loc, uprising["type"])]

        if connected_locations:
            target = random.choice(connected_locations)
            spread_chance = 0.3 + (uprising["turn_count"] * 0.1)  # Increases over time
            if random.random() < spread_chance:
                self.start_uprising(uprising["type"], target)

    def has_vulnerable_buildings(self, location, uprising_type):
        """Check if location has buildings vulnerable to uprising type"""
        if uprising_type == "Neurodroid":
            return "Neuroengineering Guild" in location.buildings
        elif uprising_type == "Agrobot":
            return "Agrobot Assembly Line" in location.buildings
        return False

    def seize_resources(self, resource_type):
        """Handle resource seizure by synthetic forces"""
        if resource_type == "research":
            amount = random.randint(10, 30)
            if self.game.ship.research_points >= amount:
                self.game.ship.research_points -= amount
                self.game.display_simple_message(f"Lost {amount} research points to synthetic forces!")
        elif resource_type == "agri":
            amount = random.randint(20, 50)
            if self.game.ship.cargo['agri'] >= amount:
                self.game.ship.cargo['agri'] -= amount
                self.game.display_simple_message(f"Lost {amount} agricultural goods to synthetic forces!")

class InfestationManager:
    def __init__(self, game):
        self.game = game
        self.infestation_types = {
            "Bugrats": {
                "trigger_buildings": ["Permaculture Paradise"],
                "trigger_threshold": 5,
                "debugratization_cost": 50000,
                "content": {
                    "title": "BUGRAT INFESTATION ALERT!",
                    "introduction": "Highly adaptive insectoidal rodents are spreading through agricultural systems!",
                    "options": [
                        {"label": "Pay for Debugratization", "cost": True},
                        {"label": "Risk Infestation", "cost": False}
                    ]
                },
                "effects": [
                    {
                        "type": "cargo_consumption",
                        "cargo_type": "agri",
                        "consumption_rate": 0.25,
                        "message": "Bugrats consume {loss} units of agricultural cargo!"
                    },
                    {
                        "type": "ship_damage",
                        "damage_rate": 5,
                        "probability": 0.2,
                        "message": "Bugrats damage ship systems!"
                    }
                ],
                "max_duration": 5
            }
            # Add more infestation types here
        }

    def check_global_infestations(self):
        """Check for global infestation events"""
        for infestation_name, infestation_config in self.infestation_types.items():
            # Count buildings that trigger this infestation
            building_count = sum(
                sum(loc.buildings.count(building) for building in infestation_config["trigger_buildings"])
                for loc in self.game.locations
            )

            # Check if threshold is met
            if building_count >= infestation_config["trigger_threshold"]:
                self.handle_infestation(infestation_name, infestation_config)

    def handle_infestation(self, infestation_name, infestation_config):
        """Handle specific infestation event with flexible options"""
        # Prepare infestation content
        content = infestation_config['content']
        infestation_content = {
            'title': content['title'],
            'introduction': content['introduction'],
            'options': " | ".join(f"{i+1}. {opt['label']}" for i, opt in enumerate(content['options']))
        }
        print(self.game.create_character_box(infestation_content))

        # Generate valid choices
        valid_choices = [str(i+1) for i in range(len(content['options']))]
        choice = self.game.validate_input("Your response: ", valid_choices)

        if not choice:
            return True  # Default to last option if no choice

        # Process selected option
        selected_option = content['options'][int(choice) - 1]

        # Handle payment option
        if selected_option['cost']:
            cost = infestation_config['debugratization_cost']
            if self.game.ship.money >= cost:
                self.game.ship.money -= cost
                self.game.display_simple_message(f"{infestation_name} threat neutralized!")
                return False
            else:
                self.game.display_simple_message("Insufficient funds! Infestation begins!")
                self.activate_infestation(infestation_name, infestation_config)
                return True
        else:
            # Risk option
            self.game.display_simple_message(f"{infestation_name} spreads!")
            self.activate_infestation(infestation_name, infestation_config)
            return True

    def activate_infestation(self, infestation_name, infestation_config):
        """Activate infestation effects on the ship"""
        if not hasattr(self.game.ship, 'active_infestations'):
            self.game.ship.active_infestations = {}

        # Add infestation with specific effects
        self.game.ship.active_infestations[infestation_name.lower()] = {
            'name': infestation_name,
            'turns_active': 0,
            'config': infestation_config,
            'effect': self.infestation_turn_effect
        }

    def infestation_turn_effect(self, ship, infestation):
        """Apply turn effects for a specific infestation"""
        config = infestation['config']

        # Apply each defined effect
        for effect in config['effects']:
            if effect['type'] == 'cargo_consumption':
                if ship.cargo[effect['cargo_type']] > 0:
                    cargo_loss = int(ship.cargo[effect['cargo_type']] * effect['consumption_rate'])
                    ship.cargo[effect['cargo_type']] = max(0, ship.cargo[effect['cargo_type']] - cargo_loss)
                    self.game.display_simple_message(
                        effect['message'].format(loss=cargo_loss)
                    )

            elif effect['type'] == 'ship_damage':
                if random.random() < effect.get('probability', 1.0):
                    ship.damage += effect['damage_rate']
                    self.game.display_simple_message(effect['message'])

        # Increment turns
        infestation['turns_active'] += 1

        # Check for natural subsiding
        if infestation['turns_active'] >= config.get('max_duration', 5):
            return False
        return True

    def update_ship_infestations(self):
        """Process active ship infestations each turn"""
        if hasattr(self.game.ship, 'active_infestations'):
            # Copy dict to avoid modification during iteration
            for infestation_key, infestation in dict(self.game.ship.active_infestations).items():
                # Apply infestation effect
                if not infestation['effect'](self.game.ship, infestation):
                    del self.game.ship.active_infestations[infestation_key]
                    self.game.display_simple_message(f"{infestation['name']} naturally subsides.")


class EventsMixin:
    """The Game's random events. Game inherits it (game/world.py)."""
    # Add passenger event handlers
    def handle_passenger_celebration(self):
        """Handle passenger celebration event"""
        for module in self.ship.passenger_modules:
            for passenger in module.passengers:
                passenger.satisfaction = min(100, passenger.satisfaction + 10)
        self.display_simple_message("Passengers are having a celebration! Satisfaction increased!")

    def handle_passenger_complaint(self):
        """Handle passenger complaint event"""
        for module in self.ship.passenger_modules:
            for passenger in module.passengers:
                passenger.satisfaction = max(0, passenger.satisfaction - 15)
        self.display_simple_message("Passengers have filed complaints! Satisfaction decreased!")

    def handle_medical_emergency(self):
        """Handle medical emergency event"""
        cost = random.randint(500, 1500)
        if self.ship.money >= cost:
            self.ship.money -= cost
            self.display_simple_message(f"Medical emergency handled! Cost: {self.format_money(cost)}")
        else:
            # If can't afford medical care, big satisfaction hit
            for module in self.ship.passenger_modules:
                for passenger in module.passengers:
                    passenger.satisfaction = max(0, passenger.satisfaction - 30)
            self.display_simple_message("Couldn't afford medical care! Passengers very unhappy!")

    def handle_vip_request(self):
        """Handle VIP passenger request"""
        cost = random.randint(1000, 2000)
        if self.ship.money >= cost:
            self.ship.money -= cost
            self.ship.passenger_reputation += 2
            self.display_simple_message(f"VIP request handled! Cost: {self.format_money(cost)}, Reputation increased!")
        else:
            self.ship.passenger_reputation = max(0, self.ship.passenger_reputation - 1)
            self.display_simple_message("Couldn't fulfill VIP request! Reputation decreased!")

    def handle_passenger_trade_info(self):
        """Handle passengers sharing trade information"""
        # Reveal profitable trade opportunities
        self.display_simple_message("Passengers shared valuable trade information!")

    def integrate_event_outcome(self, event_type, outcome, details):
        """Central hub for processing event outcomes and their effects on other systems"""
        # Plot points are no longer handed out here for things that merely happened to the
        # ship: the fight, the situation or the discovery itself pays them when the captain
        # did something (see Game.fight, Game.apply_outcome, handle_exploration_event).

        # Update quest progress using specific details
        if 'cargo_lost' in details:
            self.quest_system.update_cargo_quests(details['cargo_lost'])
        if 'money_lost' in details:
            self.quest_system.update_money_quests(details['money_lost'])
        if 'damage_taken' in details:
            self.quest_system.update_combat_quests(details['damage_taken'])

        # Update location based on specific outcomes
        self.update_location_status(event_type, outcome, details)

        # Update reputation with specific values
        if 'reputation_change' in details:
            self.update_reputation(details['reputation_change'])

    def update_reputation(self, reputation_change):
        """Update player reputation based on event outcomes"""
        self.reputation = max(0, min(100, self.reputation + reputation_change))

        # Update rank based on reputation and other factors
        self.update_rank()

        # Display reputation change if significant
        if abs(reputation_change) >= 2:
            if reputation_change > 0:
                self.display_simple_message(f"Reputation increased by {reputation_change}!")
            else:
                self.display_simple_message(f"Reputation decreased by {abs(reputation_change)}!")

        # Check for rank-up
        current_rank = self.rank
        self.update_rank()
        if self.rank != current_rank:
            self.display_simple_message(f"Congratulations! You've been promoted to {self.rank}!")

            # Apply rank-up bonuses
            rank_bonuses = {
                "Pilot": {"money": 5000, "research_points": 50},
                "Captain": {"money": 10000, "research_points": 100},
                "Commander": {"money": 20000, "research_points": 200},
                "Star Commander": {"money": 40000, "research_points": 400},
                "Space Admiral": {"money": 80000, "research_points": 800},
                "Stellar Hero": {"money": 160000, "research_points": 1600},
                "Galactic Legend": {"money": 320000, "research_points": 3200}
            }

            if self.rank in rank_bonuses:
                bonus = rank_bonuses[self.rank]
                self.ship.money += bonus["money"]
                self.ship.research_points += bonus["research_points"]
                self.display_simple_message([
                    f"Rank-up Bonus:",
                    f"• {self.format_money(bonus['money'])} credits",
                    f"• {bonus['research_points']} research points"
                ])

    def random_event(self):
        """Enhanced random event handler with complete implementation"""
        # some turns nothing happens: more of them on an easy game
        if random.random() > self.LANE_ACTIVITY.get(self.difficulty, 0.85):
            return

        # Add character encounter chance first
        if random.random() < 0.15:  # 15% chance for character encounter
            self.character_encounters.trigger_random_encounter("Space")
            return  # Return to avoid multiple events per turn

        # Add passenger-related events
        if hasattr(self.ship, 'passenger_modules') and any(m.passengers for m in self.ship.passenger_modules):
            # 10% chance of passenger event if carrying passengers
            if random.random() < 0.1:
                passenger_events = [
                    "Passenger celebration boosts morale!",
                    "Passenger complaint about accommodations!",
                    "Medical emergency with passenger!",
                    "VIP passenger requests special treatment!",
                    "Passengers share valuable trade information!"
                ]
                event = random.choice(passenger_events)

                if "celebration" in event:
                    self.handle_passenger_celebration()
                elif "complaint" in event:
                    self.handle_passenger_complaint()
                elif "medical" in event:
                    self.handle_medical_emergency()
                elif "VIP" in event:
                    self.handle_vip_request()
                elif "trade" in event:
                    self.handle_passenger_trade_info()

        # Define all possible events with their categories (fights and situations: see ENEMIES, SITUATIONS)
        events = {
            "combat": [self.pick_enemy()],
            "situation": sorted(SITUATIONS),
            "trade": [
                "Market crash!",
                "Trade embargo!",
                "Resource shortage!",
                "Price manipulation!",
                "Trade route disruption!",
                "Black market emergence!"
            ],
            "exploration": [
                "Spacetime rift!",
                "Gravitational anomaly!",
                "Mysterious signal!",
                "Quantum fluctuation!",
                "Ancient ruins!",
                "Alien artifact!"
            ],
            "disaster": [
                "Asteroid impact!",
                "Solar flare!",
                "Equipment malfunction!",
                "Hull breach!",
                "Reactor leak!",
                "Navigation failure!"
            ]
        }

        # Calculate probabilities based on location type
        location_modifiers = {
            "Planet": {"combat": 1.0, "situation": 1.2, "trade": 1.0, "exploration": 1.0, "disaster": 0.5},
            "AsteroidBase": {"combat": 1.2, "situation": 1.2, "trade": 0.8, "exploration": 1.1, "disaster": 0.7},
            "DeepSpaceOutpost": {"combat": 1.3, "situation": 1.3, "trade": 0.7, "exploration": 1.2, "disaster": 0.6},
            "ResearchColony": {"combat": 0.7, "situation": 1.1, "trade": 0.9, "exploration": 1.4, "disaster": 0.5}
        }

        # Get location-specific modifiers
        location_type = self.current_location.location_type
        modifiers = location_modifiers.get(location_type, location_modifiers["Planet"])

        # Select event category based on modifiers
        categories = list(events.keys())
        weights = [modifiers[cat] * (getattr(self, "needle_risk", 1.0) if cat == "combat" else 1)
                   for cat in categories]
        category = random.choices(categories, weights=weights)[0]
        event = random.choice(events[category])

        # Record event
        event_result = {
            "type": category,
            "name": ENEMIES[event]["name"] if category == "combat" else event,
            "location": self.current_location.name,
            "turn": self.turn
        }
        before = self.event_before()

        # Handle event based on category
        if category == "combat":
            self.handle_combat_event(event)
        elif category == "situation":
            self.situation(event)
        elif category == "trade":
            self.handle_trade_event(event)
        elif category == "exploration":
            self.handle_exploration_event(event)
        elif category == "disaster":
            self.handle_disaster_event(event)

        # Process event outcome
        outcome_details = self.process_event_outcome(event_result, before)

        # Integrate with other systems
        self.integrate_event_outcome(
            event_result["type"],
            outcome_details["outcome"],
            outcome_details
        )

        # Check for special location events
        self.check_location_events(event_result["type"])

        # Update quest status
        self.quest_system.check_event_requirements(event_result)

        # Generate new quest if appropriate
        if random.random() < 0.2:  # 20% chance for event-based quest
            quest = self.generate_event_quest(event_result, outcome_details)
            if quest:
                self.quest_system.add_quest(quest)

        # Update story progression if applicable
        self.story_manager.check_event_trigger(event, self)

    def generate_event_quest(self, event_result, outcome_details):
        """Generate a quest based on event outcome"""
        event_type = event_result["type"]
        quest = None

        if event_type == "combat":
            if outcome_details["outcome"] == "victory":
                quest_templates = [
                    {
                        "name": "Pirate Hunter",
                        "description": "Eliminate more pirates in this sector",
                        "reward_money": 2000,
                        "reward_rp": 50,
                        "quest_type": "combat",
                        "requirements": {"enemy_type": "pirate", "victories": 3}
                    },
                    {
                        "name": "System Defender",
                        "description": "Protect local trade routes",
                        "reward_money": 3000,
                        "reward_rp": 75,
                        "quest_type": "patrol",
                        "requirements": {"patrol_turns": 5}
                    }
                ]
                template = random.choice(quest_templates)
                quest = Quest(
                    name=template["name"],
                    description=template["description"],
                    reward_money=template["reward_money"],
                    reward_rp=template["reward_rp"],
                    quest_type=template["quest_type"],
                    requirements=template["requirements"]
                )

        elif event_type == "trade":
            if "market crash" in event_result["name"].lower().replace("_", " "):
                quest = Quest(
                    name="Market Stabilizer",
                    description="Help stabilize local market prices",
                    reward_money=4000,
                    reward_rp=60,
                    quest_type="trade",
                    requirements={"trades": 5, "min_profit": 1000}
                )

        elif event_type == "exploration":
            if "artifact" in event_result["name"].lower() or "ruins" in event_result["name"].lower():
                quest = Quest(
                    name="Ancient Mysteries",
                    description="Investigate more ancient sites",
                    reward_money=5000,
                    reward_rp=100,
                    quest_type="exploration",
                    requirements={"discoveries": 2}
                )

        elif event_type == "disaster":
            if outcome_details["outcome"] == "survived":
                quest = Quest(
                    name="Emergency Response",
                    description="Help other ships in distress",
                    reward_money=3500,
                    reward_rp=80,
                    quest_type="rescue",
                    requirements={"rescues": 2}
                )

        # Apply modifiers based on game progress
        if quest:
            # Scale rewards based on current chapter
            chapter_multiplier = 1 + (self.story_manager.get_chapter_number() * 0.2)
            quest.reward_money = int(quest.reward_money * chapter_multiplier)
            quest.reward_rp = int(quest.reward_rp * chapter_multiplier)

            # Scale difficulty based on player rank
            rank_multipliers = {
                "Explorer": 1.0,
                "Pilot": 1.2,
                "Captain": 1.5,
                "Commander": 1.8,
                "Star Commander": 2.0,
                "Space Admiral": 2.5,
                "Stellar Hero": 3.0,
                "Galactic Legend": 3.5
            }

            # Update requirements if they exist
            if hasattr(quest, "requirements") and "victories" in quest.requirements:
                quest.requirements["victories"] = int(
                    quest.requirements["victories"] * rank_multipliers.get(self.rank, 1.0)
                )

        return quest

    def check_location_events(self, event_type):
        """Handle location-specific event consequences"""
        location = self.current_location

        if isinstance(location, AsteroidBase):
            if event_type == "disaster":
                # Asteroid bases might discover new mining opportunities after disasters
                if random.random() < 0.2:
                    mineral_type = random.choice(["salt", "fuel"])
                    amount = random.randint(1000, 3000)
                    location.mineral_deposits[mineral_type] = location.mineral_deposits.get(mineral_type, 0) + amount
                    self.display_simple_message(f"The disaster revealed new {mineral_type} deposits!")

        elif isinstance(location, ResearchColony):
            if event_type == "exploration":
                # Research colonies might gain research points from exploration events
                bonus_points = random.randint(10, 30)
                self.ship.research_points += bonus_points
                self.display_simple_message(f"Colony researchers analyzed the phenomenon: +{bonus_points} RP")

    def event_before(self):
        """The ship before an event, so its outcome can be judged afterwards."""
        self.last_fight = None
        return {
            "location": self.current_location.name,
            "location_type": self.current_location.location_type,
            "initial_damage": self.ship.damage,
            "cargo_before": dict(self.ship.cargo),
            "money_before": self.ship.money,
            "timestamp": self.turn
        }

    def process_event_outcome(self, event_result, before=None):
        """Process and categorize event outcomes with detailed information"""
        details = dict(before or self.event_before())

        # Calculate specific event impacts
        if event_result["type"] == "combat":
            damage_taken = self.ship.damage - details["initial_damage"]
            details["damage_taken"] = damage_taken
            details["outcome"] = getattr(self, "last_fight", None) or "escaped"
            details["reputation_change"] = {"victory": 2, "defeat": -1}.get(details["outcome"], 0)

        elif event_result["type"] == "situation":
            details["outcome"] = "handled"
            details["reputation_change"] = 0

        elif event_result["type"] == "trade":
            money_change = self.ship.money - details["money_before"]
            details["money_change"] = money_change
            details["outcome"] = "success" if money_change > 0 else "loss"
            details["reputation_change"] = 1 if money_change > 0 else -1

        elif event_result["type"] == "exploration":
            if "artifact" in event_result["name"].lower() or "ruins" in event_result["name"].lower():
                details["outcome"] = "discovery"
                details["reputation_change"] = 2
            else:
                details["outcome"] = "completed"
                details["reputation_change"] = 1

        elif event_result["type"] == "disaster":
            damage_taken = self.ship.damage - details["initial_damage"]
            details["damage_taken"] = damage_taken
            details["outcome"] = "major_damage" if damage_taken > 40 else "survived"
            details["reputation_change"] = 1 if damage_taken < 20 else -1

        # Calculate specific losses
        details["cargo_lost"] = {
            item: details["cargo_before"][item] - self.ship.cargo[item]
            for item in self.ship.cargo
            if details["cargo_before"][item] > self.ship.cargo[item]
        }

        # Calculate money lost and add it to combat damage details
        money_lost = max(0, details["money_before"] - self.ship.money)
        if event_result["type"] == "combat":
            details["money_lost"] = money_lost

        # Also add money_lost to trade event details
        elif event_result["type"] == "trade" and money_lost > 0:
            details["money_lost"] = money_lost
            details["outcome"] = "loss"  # Override outcome if money was lost

        # For other events, still track money_lost
        else:
            details["money_lost"] = money_lost

        return details

    def handle_exploration_event(self, event):
        """Handle exploration events with full outcome processing"""
        success_chance = 0.7  # Base 70% success chance

        # Modify success chance based on equipment
        if "scanner" in self.ship.items:
            success_chance += 0.1
        if "probe" in self.ship.items:
            success_chance += 0.1

        # Location type modifiers
        location_modifiers = {
            "Planet": 0,
            "AsteroidBase": 0.05,
            "DeepSpaceOutpost": 0.1,
            "ResearchColony": 0.15
        }
        success_chance += location_modifiers.get(self.current_location.location_type, 0)

        if random.random() < success_chance:
            # Determine discovery type and rewards
            discovery_types = [
                ("Valuable minerals",
                {"money": (1000, 3000), "research_points": (10, 30)}),
                ("Ancient artifacts",
                {"money": (2000, 5000), "research_points": (20, 50)}),
                ("Scientific data",
                {"money": (500, 1500), "research_points": (30, 60)}),
                ("Advanced technology",
                {"money": (3000, 7000), "research_points": (25, 45)})
            ]

            discovery, reward_ranges = random.choice(discovery_types)

            # Calculate rewards with location and rank bonuses
            rank_multiplier = {
                "Explorer": 1.0,
                "Pilot": 1.2,
                "Captain": 1.5,
                "Commander": 1.8,
                "Star Commander": 2.2,
                "Space Admiral": 2.5,
                "Stellar Hero": 3.0,
                "Galactic Legend": 3.5
            }.get(self.rank, 1.0)

            location_bonus = 1.0
            if isinstance(self.current_location, ResearchColony):
                location_bonus = 1.5
            if "quantum_scanner" in self.ship.items:      # finds more in the same places
                location_bonus *= 1.25

            # Apply rewards
            money_reward = random.randint(*reward_ranges["money"])
            money_reward = int(money_reward * rank_multiplier * location_bonus)
            self.ship.money += money_reward

            rp_reward = random.randint(*reward_ranges["research_points"])
            rp_reward = int(rp_reward * rank_multiplier * location_bonus)
            self.ship.research_points += rp_reward

            # Special discovery effects
            if discovery == "Ancient artifacts":
                self.story_manager.plot_points += 2
                if random.random() < 0.3:  # 30% chance
                    self.quest_system.generate_quest("exploration", 1.5)

            elif discovery == "Advanced technology":
                if random.random() < 0.4:  # 40% chance
                    tech_bonus = random.choice(["attack", "defense", "speed"])
                    self.ship.upgrade_property(tech_bonus, 1)
                    self.display_simple_message(f"The technology improved your ship's {tech_bonus}!")

            self.display_simple_message([
                f"Exploration Success! Found {discovery}!",
                f"Earned {self.format_money(money_reward)} credits",
                f"Gained {rp_reward} research points"
            ], color='32')

        else:
            # Handle exploration failure
            damage = random.randint(5, 15)
            self.ship.damage = min(99, self.ship.damage + damage)

            self.display_simple_message([
                "Exploration failed!",
                f"Ship took {damage}% damage from hazardous conditions."
            ], color='31')

    def handle_disaster_event(self, event):
        """Complete disaster event handler"""
        # Define disaster scenarios and their impacts
        disaster_scenarios = {
            "Asteroid impact!": {
                "base_damage": (20, 40),
                "shield_protection": 0.6,
                "cargo_loss": True,
                "equipment_failure": False
            },
            "Solar flare!": {
                "base_damage": (15, 30),
                "shield_protection": 0.8,
                "cargo_loss": False,
                "equipment_failure": True
            },
            "Equipment malfunction!": {
                "base_damage": (10, 20),
                "shield_protection": 0.0,
                "cargo_loss": False,
                "equipment_failure": True
            },
            "Hull breach!": {
                "base_damage": (25, 45),
                "shield_protection": 0.4,
                "cargo_loss": True,
                "equipment_failure": False
            },
            "Reactor leak!": {
                "base_damage": (30, 50),
                "shield_protection": 0.3,
                "cargo_loss": False,
                "equipment_failure": True
            },
            "Navigation failure!": {
                "base_damage": (5, 15),
                "shield_protection": 0.0,
                "cargo_loss": False,
                "equipment_failure": True
            }
        }

        scenario = disaster_scenarios.get(event, disaster_scenarios["Equipment malfunction!"])

        # Calculate base damage
        min_damage, max_damage = scenario["base_damage"]
        damage = random.randint(min_damage, max_damage)

        # Apply shield protection if available
        if "shield" in self.ship.items and scenario["shield_protection"] > 0:
            if random.random() < scenario["shield_protection"]:
                damage = int(damage * 0.4)  # 60% reduction when shields work
                self.display_simple_message("Shields partially mitigated the disaster!", 2, color='32')

        # Apply final damage
        self.ship.damage = min(99, self.ship.damage + damage)

        # Handle cargo loss if applicable
        if scenario["cargo_loss"]:
            cargo_lost = False
            for cargo_type in ['tech', 'agri', 'salt', 'fuel']:
                if self.ship.cargo[cargo_type] > 0:
                    lost = random.randint(1, max(1, int(self.ship.cargo[cargo_type] // 2)))
                    self.ship.cargo[cargo_type] = max(0, self.ship.cargo[cargo_type] - lost)
                    if lost > 0:
                        cargo_lost = True
                        self.display_simple_message(
                            f"Lost {self.format_money(lost)} units of {cargo_type}!",
                            2, color='31'
                        )

        # Handle equipment failure
        if scenario["equipment_failure"]:
            breakable = [name for name in self.ship.items if name not in story_items()]
            if breakable and random.random() < 0.3:
                item = random.choice(breakable)
                self.ship.items[item] -= 1
                if self.ship.items[item] <= 0:
                    del self.ship.items[item]
                self.display_simple_message(f"Equipment failure! Lost {item}!", 2, color='31')

        # Display final disaster results
        self.display_simple_message(
            f"Event! {event} caused {damage}% damage to the ship!",
            3, color='31'
        )

        # Check for repair opportunity
        if "repair_bot" in self.ship.items and random.random() < 0.4:
            repair = random.randint(5, 15)
            self.ship.damage = max(0, self.ship.damage - repair)
            self.display_simple_message(
                f"Repair bot automatically fixed {repair}% damage!",
                2, color='32'
            )


# The game's other modules, imported last so that the modules can refer to each other.
from .encounters import ENEMIES, SITUATIONS  # noqa: E402
from .story import story_items  # noqa: E402
from .quests import Quest  # noqa: E402
from .places import AsteroidBase, ResearchColony  # noqa: E402
