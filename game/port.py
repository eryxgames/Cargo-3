"""Ports and shops, and the Game's visits to cantina, shop and shipyard."""
import random
import time

class Port:
    def __init__(self, game):
        self.game = game
        self.available_modules = {
                "1": {
                    "name": "Basic Passenger",
                    "capacity": 4,
                    "comfort_level": 1,
                    "cost": 5000
                },
                "2": {
                    "name": "Standard Passenger",
                    "capacity": 8,
                    "comfort_level": 2,
                    "cost": 10000
                },
                "3": {
                    "name": "Luxury Passenger",
                    "capacity": 4,
                    "comfort_level": 4,
                    "cost": 20000
                },
                "4": {
                    "name": "Life Support Module",
                    "capacity": 4,
                    "comfort_level": 1,
                    "cost": 8000
                },
                "5": {
                    "name": "Business Class A",
                    "capacity": 2,
                    "comfort_level": 5,
                    "cost": 25000
                },
                "6": {
                    "name": "Research Lab Module",
                    "capacity": 2,
                    "comfort_level": 3,
                    "cost": 30000,
                    "special": "research_bonus"
                },
                "7": {
                    "name": "Colony Transport Mod.",
                    "capacity": 12,
                    "comfort_level": 2,
                    "cost": 35000,
                    "special": "colonist_bonus"
                },
                "8": {
                    "name": "Diplomatic Suite Mod.",
                    "capacity": 1,
                    "comfort_level": 6,
                    "cost": 40000,
                    "special": "diplomatic_bonus"
                }
            }

        # List of passengers waiting at each location
        self.waiting_passengers = {}

        # Passenger names for random generation
        self.first_names = ["John", "Emma", "Zara", "Chen", "Raj", "Ana", "Igor", "Yuki", "Omar", "Luna"]
        self.last_names = ["Smith", "Patel", "Wong", "Garcia", "Petrov", "Tanaka", "Mueller", "Kim", "Hassan", "Silva"]


    def generate_passenger(self, current_location):
        """Generate a random passenger"""
        name = f"{random.choice(self.first_names)} {random.choice(self.last_names)}"
        # Choose destination from known locations except current
        possible_destinations = [loc for loc in self.game.known_locations if loc != current_location]
        if not possible_destinations:
            return None
        destination = random.choice(possible_destinations)
        wealth_level = random.randint(1, 5)
        return Passenger(name, destination, wealth_level)


    def update_passengers(self, location):
        """Update passenger list at a location (once per turn: new arrivals, longer waits)"""
        if location not in self.waiting_passengers:
            self.waiting_passengers[location] = []
        updated = self.__dict__.setdefault("updated_turn", {})
        if updated.get(location) == self.game.turn:
            return
        updated[location] = self.game.turn

        # Remove passengers waiting too long (a quest's passenger waits for you)
        self.waiting_passengers[location] = [p for p in self.waiting_passengers[location]
                                           if p.turns_waiting < 10 or getattr(p, "is_quest_passenger", False)]

        # Check for special character spawning
        if random.random() < 0.2:  # 20% chance per turn
            self.game.reputation_manager.spawn_special_passenger()

        # Add new passengers (1-3 per turn)
        new_passengers = random.randint(1, 3)
        for _ in range(new_passengers):
            passenger = self.generate_passenger(location)
            if passenger:
                self.waiting_passengers[location].append(passenger)

        # Update waiting turns
        for passenger in self.waiting_passengers[location]:
            passenger.turns_waiting += 1


    def calculate_fare(self, passenger, module):
        """Calculate passenger fare based on distance, comfort, and wealth"""
        base_fare = 100 * passenger.wealth_level
        comfort_multiplier = 1 + (module.comfort_level * 0.2)
        distance_multiplier = 1.25 if self.game.ship.items.get("temporal_accelerator") else 1
        if "steward" in self.game.ship.crew:          # a steward makes any cabin feel first class
            comfort_multiplier += 0.15

        # Add distance calculation if game has that mechanic
        # distance_multiplier = calculate_distance(current, destination)

        return int(base_fare * comfort_multiplier * distance_multiplier)

    def display_port_info(self):
        """Display port information and options"""
        content = []

        # Show installed modules
        content.append(["Installed Passenger Modules"])
        if hasattr(self.game.ship, 'passenger_modules'):
            for module in self.game.ship.passenger_modules:
                passengers = len(module.passengers)
                content.append([
                    f"{module.name}",
                    f"({passengers}/{module.capacity} passengers)",
                    f"Comfort Lvl.: {module.comfort_level}"
                ])
        else:
            content.append(["No passenger modules installed"])

        # Show current passengers
        content.append([""])
        content.append(["Current Passengers"])
        total_passengers = 0
        if hasattr(self.game.ship, 'passenger_modules'):
            for module in self.game.ship.passenger_modules:
                for passenger in module.passengers:
                    total_passengers += 1
                    content.append([
                        f"{passenger.name}",
                        f"→ {passenger.destination}",
                        f"Satisfaction: {passenger.satisfaction}%"
                    ])
        if total_passengers == 0:
            content.append(["No passengers currently aboard"])

        # Show waiting passengers at current location
        content.append([""])
        content.append(["Waiting Passengers"])
        location = self.game.current_location.name
        if location in self.waiting_passengers and self.waiting_passengers[location]:
            for passenger in self.waiting_passengers[location]:
                content.append([
                    f"{passenger.name}",
                    f"→ {passenger.destination}",
                    f"Class: {passenger.wealth_level}"
                ])
        else:
            content.append(["No passengers waiting"])

        return self.game.create_box(content, 'double')


    def handle_port_menu(self):
        """Handle port menu options"""
        self.game.clear_screen()
        self.game.display_simple_message("Welcome to the Stardock Port!", 0)
        self.game.story.visit_venue("port")

        while True:
            options = {
                'view': ('v', "View Port Info"),
                'modules': ('m', "Purchase Modules"),
                'board': ('b', "Board Passengers"),
                'unload': ('u', "Unload Passengers"),
                'contracts': ('c', "Manage Contracts"),
                'prices': ('pr', "Ask the broker robot about prices elsewhere"),
                'travel': ('t', "Travel"),
                'back': ('', "Return to Main Menu")
            }

            # Show menu
            menu_content = [[f"Port Services {self.game.current_location.name} | PAX Checkout: {sum(len(module.passengers) for module in self.game.ship.passenger_modules)}/{sum(module.capacity for module in self.game.ship.passenger_modules)}"]]
            menu_content.append([f""])
            for cmd, (shortcut, desc) in options.items():
                menu_content.append([f"{cmd}/{shortcut if shortcut else ''}: {desc}"])
            print(self.game.create_box(menu_content, 'single'))

            valid_inputs = [cmd for cmd in options.keys()] + [s[0] for s in options.values() if s[0]]
            action = self.game.validate_input("Port - choose (Enter to leave): ", valid_inputs)

            if action in ['back', None]:
                break

            elif action in ['view', 'v']:
                print(self.display_port_info())
                time.sleep(2)

            elif action in ['modules', 'm']:
                self.handle_module_purchase()

            elif action in ['board', 'b']:
                self.handle_passenger_boarding()

            elif action in ['unload', 'u']:
                self.handle_passenger_unloading()
                time.sleep(2)

            elif action in ['contracts', 'c']:
                self.game.contract_manager.handle_contract_menu()

            elif action in ['prices', 'pr']:
                self.game.show_forecast(self.game.story.fill("{port_broker}, the port's broker robot, "
                                                             "quotes other docks"))

            elif action in ['travel', 't']:
                if self.game.handle_travel():
                    break

            self.game.clear_screen()

    def handle_module_purchase(self):
        """Handle purchase of new modules with numbered selection"""
        while True:
#            self.game.clear_screen()
            content = [["", f"¤: {self.game.format_money(self.game.ship.money)}"]]
    #        content.append([""])  # Empty line for spacing
            content.append(["#", "Module Types:", "Cap.", "Comf.", "Cost"])
#            content.append(["#", "Module Types:", "Cap.", "Comf.", "Cost", "Special"])

            for module_id, module in self.available_modules.items():
                special = module.get("special", "-")
                content.append([
                    module_id,
                    module["name"],
                    str(module["capacity"]),
                    str(module["comfort_level"]),
                    str(self.game.format_money(module["cost"])),
#                    special #yet uinimplemented module special
                ])

            print(self.game.create_box(content, 'double'))

            module_id = self.game.validate_input(
                "Enter module number to buy (or 'back'): ",
                list(self.available_modules.keys()) + ['back']
            )

            if module_id == 'back':
                self.game.clear_screen()
                return

            if module_id in self.available_modules:
                module = self.available_modules[module_id]
                if self.game.ship.money >= module["cost"]:
                    self.game.ship.money -= module["cost"]

                    if not hasattr(self.game.ship, 'passenger_modules'):
                        self.game.ship.passenger_modules = []

                    new_module = PassengerModule(
                        module["name"],
                        module["capacity"],
                        module["comfort_level"],
                        module["cost"]
                    )
                    if "special" in module:
                        new_module.special = module["special"]

                    self.game.ship.passenger_modules.append(new_module)

                    self.game.display_simple_message(f"Purchased {module['name']}!")
#                    time.sleep(1)
                    self.game.clear_screen()
                    return
                else:
                    self.game.display_simple_message("Not enough money!")
#                    time.sleep(1)
                    self.game.clear_screen()
                    return


    def handle_passenger_boarding(self):
        """Handle passenger boarding with removal from waiting list"""
        while True:
            location = self.game.current_location.name

            if not hasattr(self.game.ship, 'passenger_modules'):
                self.game.display_simple_message("No passenger modules installed!")
                self.game.clear_screen()
                return

            if location not in self.waiting_passengers or not self.waiting_passengers[location]:
                self.game.display_simple_message("No passengers waiting!")
                self.game.clear_screen()
                return

            available_modules = [m for m in self.game.ship.passenger_modules
                            if len(m.passengers) < m.capacity]

            if not available_modules:
                self.game.display_simple_message("No room for more passengers!")
                self.game.clear_screen()
                return

            # Show module status
            self.display_module_status()

            # Show waiting passengers
            self.display_waiting_passengers()

            # Get command
            self.game.display_simple_message(
                "Enter numbers to select passengers, 'refresh/r' to refresh list, 'autoboard/a' for auto boarding, or Enter to cancel:", 0
            )

            selection = input(">>> ").strip().lower()

            if not selection:  # Empty Enter
                return

            if selection in ['refresh', 'r']:
                # Regenerate waiting passengers
                self.update_passengers(location)
                continue

            if selection in ['autoboard', 'a']:
                self.handle_autoboard(available_modules)
                continue

            try:
                # Parse space-separated numbers
                passenger_nums = [int(num) - 1 for num in selection.split()]
                waiting_passengers = self.waiting_passengers[location]

                # Validate numbers and get passengers
                selected_passengers = []
                if all(0 <= num < len(waiting_passengers) for num in passenger_nums):
                    # Get passengers and remove them from waiting list
                    selected_passengers = [waiting_passengers[num] for num in sorted(passenger_nums, reverse=True)]
                    for num in sorted(passenger_nums, reverse=True):
                        del waiting_passengers[num]

                    if selected_passengers:
                        self.handle_module_assignment(selected_passengers, available_modules)
                else:
                    self.game.display_simple_message("Invalid passenger number(s)")

            except ValueError:
                self.game.display_simple_message("Invalid input. Please enter numbers separated by spaces.")

    def handle_passenger_unloading(self):
            """Handle passenger unloading with reputation effects and bonuses"""
            if not hasattr(self.game.ship, 'passenger_modules'):
                self.game.display_simple_message("No passenger modules installed!")
                return

            current_location = self.game.current_location.name
            passengers_to_unload = []
            total_earnings = 0

            # Find passengers that have reached their destination
            for module in self.game.ship.passenger_modules:
                for passenger in module.passengers[:]:
                    if passenger.destination == current_location:
                        # Calculate fare with reputation multiplier
                        base_fare = self.calculate_fare(passenger, module)
                        reputation_multiplier = self.game.reputation_manager.get_fare_multiplier()
                        satisfaction_multiplier = passenger.satisfaction / 100
                        bonus_multiplier = 1.0  # Default multiplier

                        # Apply organization bonus if applicable
                        org_bonus = self.get_bonus_type(passenger)
                        bonus_message = None
                        if org_bonus:
                            org_name, multiplier, message = org_bonus
                            bonus_multiplier = multiplier
                            bonus_message = f"{org_name} doubles the revenue! {message} Plot points +1"
                            self.game.story_manager.plot_points += 1

                        # Calculate final payment with all multipliers
                        final_payment = int(base_fare * satisfaction_multiplier * reputation_multiplier * bonus_multiplier)

                        # Update reputation based on passenger satisfaction
                        reputation_change = self.game.reputation_manager.update_reputation(passenger.satisfaction, passenger)

                        # Handle special passengers
                        if hasattr(passenger, 'is_vip'):
                            self.game.reputation_manager.handle_vip_delivery(passenger)

                        # Update contract progress if available
                        if hasattr(self.game, 'contract_manager'):
                            passenger_data = {
                                "class": passenger.classification["code"],
                                "satisfaction": passenger.satisfaction
                            }
                            event_data = {
                                "location": current_location,
                                "passenger_data": passenger_data,
                                "action": "unload"
                            }
                            for contract in self.game.contract_manager.active_contracts:
                                contract.update_progress(event_data)

                        # Increment total passengers delivered
                        self.game.reputation_manager.total_passengers += 1

                        # Record unloading result
                        passengers_to_unload.append({
                            'passenger': passenger,
                            'payment': final_payment,
                            'satisfaction': passenger.satisfaction,
                            'reputation_change': reputation_change,
                            'bonus_message': bonus_message
                        })

                        # Apply payment and remove passenger
                        self.game.ship.money += final_payment
                        module.passengers.remove(passenger)
                        total_earnings += final_payment

            # Display unloading results
            if passengers_to_unload:
                content = [["Passengers Disembarked"]]

                for result in passengers_to_unload:
                    passenger = result['passenger']
                    content.append([
                        passenger.name,
                        f"Fare: {self.game.format_money(result['payment'])}",
                        f"Satisfied: {result['satisfaction']}%"
                    ])

                    # Add reputation change if significant
                    if abs(result['reputation_change']) >= 0.1:
                        content.append([
                            f"└─ Reputation Change: {'+' if result['reputation_change'] > 0 else ''}{result['reputation_change']:.1f}"
                        ])

                    # Add bonus message if any
                    if result['bonus_message']:
                        content.append([f"└─ {result['bonus_message']}"])

                content.append([""])
                content.append([f"Total Earnings: {self.game.format_money(total_earnings)}"])

                print(self.game.create_box(content, 'double'))
            else:
                self.game.display_simple_message("No passengers to unload here!")
#                self.game.clear_screen()

    def get_bonus_type(self, passenger):
        """Get bonus type based on passenger classification"""
        bonus_types = {
            "S": ("Scientific Institute", 2.0, "Scientific research strengthened!"),
            "M": ("Planetary Defense Council", 3.0, "Military recruitment enhanced!"),
            "E": ("Engineering Corps", 2.5, "Engineering capacity expanded!"),
            "T": ("Trade Federation", 2.0, "Commercial networks expanded!"),
            "D": ("Diplomatic Service", 3.0, "Diplomatic relations improved!"),
            "R": ("Research Foundation", 2.5, "Research capabilities enhanced!")
        }
        passenger_class = passenger.classification["code"]
        if random.random() < 0.3:  # 30% chance for bonus
            return bonus_types.get(passenger_class)
        return None


    def handle_autoboard(self, available_modules):
        """Handle automatic passenger boarding based on destination"""
        location = self.game.current_location.name
        waiting_passengers = self.waiting_passengers[location]

        # Get unique destinations
        destinations = sorted(set(p.destination for p in waiting_passengers))

        # Show destinations
        content = [["Available Destinations"]]
        for i, dest in enumerate(destinations, 1):
            matching = sum(1 for p in waiting_passengers if p.destination == dest)
            content.append([f"{i}. {dest}", f"{matching} passengers waiting"])
        print(self.game.create_box(content, 'single'))

        # Get destination choice
        self.game.display_simple_message("Choose destination number:", 0)
        try:
            choice = int(input(">>> "))
            if 1 <= choice <= len(destinations):
                target_dest = destinations[choice-1]

                # Get matching passengers
                matching_passengers = [p for p in waiting_passengers if p.destination == target_dest]

                # Board as many as possible
                modules_space = sum(m.capacity - len(m.passengers) for m in available_modules)
                to_board = matching_passengers[:modules_space]

                if to_board:
                    self.handle_module_assignment(to_board, available_modules)
                else:
                    self.game.display_simple_message("No matching passengers to board!")

        except (ValueError, IndexError):
            self.game.display_simple_message("Invalid choice!")

    def display_module_status(self):
        """Display current module status"""
        module_status = [["Current Module Status"]]
        for module in self.game.ship.passenger_modules:
            passengers_info = []
            for p in module.passengers:
                passengers_info.append(f"{p.name} [{p.classification['code']}] → {p.destination}")
            module_status.append([
                f"{module.name}",
                f"({len(module.passengers)}/{module.capacity})",
                f"Comfort: {module.comfort_level}"
            ])
            for p_info in passengers_info:
                module_status.append([f"└─ {p_info}"])
        print(self.game.create_box(module_status, 'single'))

    def display_waiting_passengers(self):
        """Display waiting passengers"""
        location = self.game.current_location.name
        content = [[""]]
        content.append(["#", f"Waiting on {location}", "Dest.", "Cls.", "≈Fare"])

        waiting_passengers = self.waiting_passengers[location]
        for i, passenger in enumerate(waiting_passengers, 1):
            best_module = max(
                (m for m in self.game.ship.passenger_modules if len(m.passengers) < m.capacity),
                key=lambda m: m.comfort_level
            )
            est_fare = self.calculate_fare(passenger, best_module)
            content.append([
                str(i),
                f"{passenger.name} [{passenger.classification['code']}]",
                passenger.destination,
                f"L{passenger.wealth_level}",
                self.game.format_money(est_fare)
            ])

        print(self.game.create_box(content, 'double'))

    def handle_module_assignment(self, selected_passengers, available_modules):
        """Handle assigning selected passengers to modules"""
        passengers_left = selected_passengers.copy()

        while passengers_left and available_modules:
            # Show remaining passengers
            content = [["Remaining Passengers"]]
            for i, passenger in enumerate(passengers_left, 1):
                content.append([
                    f"{i}. {passenger.name} [{passenger.classification['code']}]",
                    passenger.destination
                ])
            print(self.game.create_box(content, 'single'))

            # Show available modules
            module_content = [["Available Modules"]]
            for i, module in enumerate(available_modules, 1):
                module_content.append([
                    f"{i}. {module.name}",
                    f"({len(module.passengers)}/{module.capacity})",
                    f"Comfort: {module.comfort_level}"
                ])
            print(self.game.create_box(module_content, 'single'))

            # Get module choice with auto option
            self.game.display_simple_message(
                "Choose module number, 'auto/a' for automatic assignment, or 'back':", 0
            )
            choice = input(">>> ").strip().lower()

            if choice == 'back':
                break

            if choice in ['auto', 'a']:
                self.auto_assign_modules(passengers_left, available_modules)
                break

            try:
                module_num = int(choice)
                if 1 <= module_num <= len(available_modules):
                    chosen_module = available_modules[module_num - 1]
                    if len(chosen_module.passengers) >= chosen_module.capacity:
                        self.game.display_simple_message("Module is full!")
                        continue

                    # Add first remaining passenger
                    passenger = passengers_left.pop(0)
                    chosen_module.passengers.append(passenger)
                    self.game.display_simple_message(f"Assigned {passenger.name} to {chosen_module.name}")

                    # Remove full modules from available list
                    if len(chosen_module.passengers) >= chosen_module.capacity:
                        available_modules.remove(chosen_module)
                else:
                    self.game.display_simple_message("Invalid module number")
            except ValueError:
                self.game.display_simple_message("Invalid input")

    def auto_assign_modules(self, passengers, modules):
        """Automatically assign passengers to modules"""
        # Sort modules by comfort level (highest first)
        sorted_modules = sorted(modules, key=lambda m: m.comfort_level, reverse=True)

        # Sort passengers by wealth level (highest first)
        sorted_passengers = sorted(passengers, key=lambda p: p.wealth_level, reverse=True)

        assigned = 0
        location = self.game.current_location.name

        for passenger in sorted_passengers[:]:  # Use slice to create copy for iteration
            for module in sorted_modules:
                if len(module.passengers) < module.capacity:
                    module.passengers.append(passenger)
                    if passenger in self.waiting_passengers[location]:  # Remove from waiting list
                        self.waiting_passengers[location].remove(passenger)
                    assigned += 1
                    self.game.display_simple_message(
                        f"Auto-assigned {passenger.name} to {module.name}"
                    )
                    break

        remaining = len(passengers) - assigned
        if remaining > 0:
            self.game.display_simple_message(f"Could not assign {remaining} passengers - no space left")


    def update_passenger_satisfaction(self):
        """Update passenger satisfaction during travel"""
        if not hasattr(self.game.ship, 'passenger_modules'):
            return

        for module in self.game.ship.passenger_modules:
            for passenger in module.passengers:
                # Base satisfaction change
                change = 0

                # Comfort level effect
                if module.comfort_level >= passenger.wealth_level:
                    change += 2  # Satisfied with comfort
                else:
                    change -= 3  # Dissatisfied with comfort

                # Ship damage effect
                if self.game.ship.damage > 50:
                    change -= 5
                elif self.game.ship.damage > 25:
                    change -= 2

                # Update satisfaction
                passenger.satisfaction = max(0, min(100, passenger.satisfaction + change))

class Shop:
    def __init__(self):
        self.base_equipment = {
            "navcomp": {
                "price": 500,
                "description": "Navigation computer reveals all destinations",
                "tech_required": 1,
                "plot_required": 0
            },
            "scanner": {
                "price": 700,
                "description": "Basic scanner: tells a real distress call from bait",
                "tech_required": 2,
                "plot_required": 0
            },
            "probe": {
                "price": 900,
                "description": "Deep space probe: scouts debris fields ahead of the ship",
                "tech_required": 3,
                "plot_required": 10
            },
            "turrets": {
                "price": 1200,
                "description": "Defense turrets: better odds in every fight; shred drone swarms",
                "tech_required": 4,
                "plot_required": 15
            },
            "shield": {
                "price": 1500,
                "description": "Energy shield: 30% less fight damage; rides out storms and flares",
                "tech_required": 5,
                "plot_required": 20
            },
            "patcher": {
                "price": 300,
                "description": "Hull patcher: repairs 10% damage after every fight",
                "tech_required": 1,
                "plot_required": 0
            },
            # Transport Equipment
            "cargo_extender": {
                "price": 5000,
                "description": "Increases cargo capacity by 20%",
                "tech_required": 3,
                "plot_required": 25
            },
            "containment_field": {
                "price": 8000,
                "description": "Specialized storage for salt/fuel (+30% capacity)",
                "tech_required": 4,
                "plot_required": 30
            },
            "auto_loader": {
                "price": 12000,
                "description": "Loads and unloads for you: 2% less trade tax",
                "tech_required": 5,
                "plot_required": 35
            },
            # Advanced Transport Equipment
            "quantum_compressor": {
                "price": 20000,
                "description": "Advanced compression (+50% capacity for all cargo)",
                "tech_required": 6,
                "plot_required": 50
            },
            "stasis_vault": {
                "price": 25000,
                "description": "Perfect resource preservation (+75% capacity for special resources)",
                "tech_required": 7,
                "plot_required": 60
            },
            "temporal_accelerator": {
                "price": 30000,
                "description": "Faster deliveries: passengers pay 25% more",
                "tech_required": 8,
                "plot_required": 75
            }
        }

        # Location-specific items with requirements
        self.location_equipment = {
            "AsteroidBase": {
                "mining_laser": {
                    "price": 2000,
                    "description": "Mining laser: +1 defense; cuts drones, derelicts and debris",
                    "tech_required": 3,
                    "plot_required": 15
                },
                "cargo_scanner": {
                    "price": 1800,
                    "description": "Cargo scanner: +20% room for salt and fuel; clean scans for customs",
                    "tech_required": 4,
                    "plot_required": 20
                },
                "shield_booster": {
                    "price": 2500,
                    "description": "Stronger shields: +1 defense in fights",
                    "tech_required": 5,
                    "plot_required": 25
                },
                "mining_compressor": {
                    "price": 15000,
                    "description": "Mining compressor: +40% room for salt and fuel; skims comets",
                    "tech_required": 6,
                    "plot_required": 40
                }
            },
            "DeepSpaceOutpost": {
                "advanced_radar": {
                    "price": 2200,
                    "description": "Radar: slip away before a fight, or jam their targeting",
                    "tech_required": 4,
                    "plot_required": 30
                },
                "combat_drone": {
                    "price": 3000,
                    "description": "Combat drone: +1 attack; sent in first, it takes the first hit",
                    "tech_required": 5,
                    "plot_required": 35
                },
                "repair_bot": {
                    "price": 2800,
                    "description": "Repair bot: fixes breakdowns and some disaster damage",
                    "tech_required": 6,
                    "plot_required": 40
                },
                "emergency_warp": {
                    "price": 18000,
                    "description": "Emergency jump out of any fight or storm",
                    "tech_required": 7,
                    "plot_required": 50
                }
            },
            "ResearchColony": {
                "research_module": {
                    "price": 2500,
                    "description": "+20% research points from travel",
                    "tech_required": 5,
                    "plot_required": 40
                },
                "data_analyzer": {
                    "price": 2800,
                    "description": "+10% research points from travel",
                    "tech_required": 6,
                    "plot_required": 45
                },
                "quantum_scanner": {
                    "price": 3500,
                    "description": "Quantum scanner: +25% discovery rewards; finds weak spots",
                    "tech_required": 7,
                    "plot_required": 50
                },
                "containment_optimizer": {
                    "price": 22000,
                    "description": "Smart cargo optimization (+25% capacity)",
                    "tech_required": 8,
                    "plot_required": 60
                }
            }
        }

        # Track sold items per turn
        # Track items for current turn
        self.current_turn_items = []
        self.sold_items = set()
        self.current_turn = 0
        self.current_offerings = []  # Keep this

        # Track discounts and special offers
        self.current_discounts = {}
        self.special_offers = {}

    def get_available_items(self, location, plot_points):
        """Get available items based on location and plot points"""
        available_pool = []

        # Start with base equipment pool, filtering by requirements
        for name, data in self.base_equipment.items():
            if (location.tech_level >= data["tech_required"] and
                plot_points >= data["plot_required"]):
                available_pool.append((name, data))

        # Add location-specific items if applicable, also filtering
        location_type = location.location_type
        if location_type in self.location_equipment:
            for name, data in self.location_equipment[location_type].items():
                if (location.tech_level >= data["tech_required"] and
                    plot_points >= data["plot_required"]):
                    available_pool.append((name, data))

        # Select random items from filtered pool
        if available_pool:
            selected_items = random.sample(available_pool, min(2, len(available_pool)))
            self.current_offerings = [item[0] for item in selected_items]
            return selected_items

        return []


    def mark_item_sold(self, item_name):
        """Mark an item as sold for this turn"""
        self.sold_items.add(item_name)
        if item_name in self.current_offerings:
            self.current_offerings.remove(item_name)


    def clear_special_offers(self):
        """Clear all special offers"""
        self.current_discounts.clear()

    def is_item_sold(self, item_name):
        """Check if an item has been sold this turn"""
        return item_name in self.sold_items

    def reset_turn(self):
        """Reset shop state for new turn"""
        self.sold_items.clear()
        self.current_offerings.clear()
        self.clear_special_offers()
        self.current_turn_items = []


class PortMixin:
    """The Game's visits to cantina, shop and shipyard. Game inherits it (game/world.py)."""
    def handle_contract_menu(self):
        """Route contract menu handling to ContractManager"""
        if not hasattr(self, 'contract_manager'):
            self.contract_manager = ContractManager(self)
        self.contract_manager.handle_contract_menu()

    def handle_hull_overhaul(self):
        """A planet's shipyard rebuilds the ship on a heavier hull."""
        ship = self.ship
        if not isinstance(self.current_location, Planet):
            self.display_simple_message("Only a planet's shipyard can overhaul a hull.")
            return False
        if ship.hull + 1 >= len(ship.HULLS):
            self.display_simple_message("The %s is the best hull any yard here builds." % ship.hull_info()["name"])
            return False
        nxt = ship.HULLS[ship.hull + 1]
        rows = [["Shipyard - " + self.current_location.name], [""]]
        rows.extend([line] for line in self.word_wrap("Now: %s, %s." % (ship.hull_info()["name"], ship.hull_info()["about"])))
        rows.append([""])
        rows.extend([line] for line in self.word_wrap(
            "Overhaul to %s for %s: %s. Defense +%d, attack +%d, hold +%d%%. Repairs cost %d credits a point "
            "of damage (now %d)." % (nxt["name"], self.format_money(nxt["price"]), nxt["about"], nxt["defense"],
                                    nxt["attack"], int(nxt["hold"] * 100), nxt["repair"], ship.hull_info()["repair"])))
        print(self.create_box(rows, 'double'))
        if self.validate_input("Overhaul the hull? (yes/no): ", ['yes', 'no', 'y', 'n']) not in ('yes', 'y'):
            return False
        if ship.money < nxt["price"]:
            self.display_simple_message("Not enough money: the yard wants %s." % self.format_money(nxt["price"]))
            return False
        ship.money -= nxt["price"]
        ship.hull += 1
        ship.damage = 0
        self.story_manager.plot_points += 5
        self.display_simple_message("The yard takes your ship apart and gives you back a %s. +5 plot points." %
                                    nxt["name"], 3, color='32')
        return True

    def handle_gossip(self):
        """Handle gossip and quest generation in cantina"""
        if self.ship.money >= 150:
            self.ship.money -= 150
            gossip_content = [["Latest Market Gossip"]]
            gossip_content.append([""])

            # Generate market information
            found_gossip = False
            for location in self.locations:
                if location.name in self.known_locations:
                    location_gossip = []
                    if location.market['tech'] < 50:
                        location_gossip.append(f"Cheap tech goods available")
                    if location.market['agri'] < 30:
                        location_gossip.append(f"Cheap agri goods available")
                    if location.market['tech'] > 100:
                        location_gossip.append(f"High tech prices")
                    if location.market['agri'] > 80:
                        location_gossip.append(f"High agri prices")

                    if location_gossip:
                        found_gossip = True
                        gossip_content.append([location.name])
                        for gossip in location_gossip:
                            gossip_content.append([f"└─ {gossip}"])

            if found_gossip:
                print(self.create_box(gossip_content, 'double'))

                # 30% chance to get a quest
                if random.random() < 0.3:
                    self.quest_system.add_quest(self.quest_system.generate_cantina_quest())
            else:
                self.display_simple_message("No interesting gossip today!")
        else:
            self.display_simple_message("Not enough money to listen to gossip.")

    def visit_cantina(self):
        self.clear_screen()
        self.display_simple_message("Welcome to the Cantina!", 0)

        # Whoever is in the cantina today, and what people are saying
        self.story.visit_venue("cantina")
        self.story_manager.nudge()

        while True:
            options = {
                'map': ('bm', "Buy Map"),
                'update': ('um', "Update Map"),
                'gossip': ('lg', "Listen to Gossip"),
                'quests': ('q', "View Quests"),
                'contracts': ('c', "Manage Contracts"),
                'story': ('s', "View Story Progress"),
                'back': ('', "Return to Main Menu")
            }

            menu_content = [[f"Cantina Services - {self.current_location.name}"]]
            menu_content.append([f""])
            for cmd, (shortcut, desc) in options.items():
                menu_content.append([f"{cmd}/{shortcut if shortcut else ''}: {desc}"])
            print(self.create_box(menu_content, 'single'))

            valid_inputs = [cmd for cmd in options.keys()] + [s[0] for s in options.values() if s[0]]
            action = self.validate_input("Cantina - choose (Enter to leave): ", valid_inputs)

            if action in ['back', None]:
                break

            elif action in ['map', 'bm']:
                self.handle_buy_map()

            elif action in ['update', 'um']:
                self.handle_update_map()

            elif action in ['gossip', 'lg']:
                self.handle_gossip()

            elif action in ['quests', 'q']:
                self.quest_system.display_quests()

            elif action in ['contracts', 'c']:
                self.handle_contract_menu()

            elif action in ['story', 's']:
                self.display_story_status()

            time.sleep(1)
            self.clear_screen()

    def visit_shop(self):
        """Enhanced shop interface with persistent sold items"""
        self.display_simple_message("Welcome to the Shop!", 1)

        # Display current money and location info
        status_content = [
            [f"Credits: {self.format_money(self.ship.money)}"],
            [f"Tech Level: {self.current_location.tech_level}"]
        ]
        print(self.create_box(status_content, 'single'))

        # Display current inventory
        inventory_content = [["Your Items"]]
        if self.ship.items:
            for item, count in self.ship.items.items():
                inventory_content.append([f"{item}: {count}"])
        else:
            inventory_content.append(["No items"])
        print(self.create_box(inventory_content, 'single'))

        # Get available items for this location
        if not hasattr(self.shop, 'current_turn_items') or not self.shop.current_turn_items:  # Changed condition
            # Only get new items if we haven't already for this turn
            self.shop.current_turn_items = self.shop.get_available_items(
                location=self.current_location,
                plot_points=self.story_manager.plot_points
            )

        shop_content = [["Item", "¤", "Description", ""]]
        for item_name, item_data in self.shop.current_turn_items:
            status = "SOLD" if self.shop.is_item_sold(item_name) else "Avail"
            shop_content.append([
                item_name.title(),
                self.format_money(item_data["price"]),
                item_data["description"],
                status
            ])

        print(self.create_box(shop_content, 'double'))

        # Only show unsold items in options
        available_items_names = [
            item[0] for item in self.shop.current_turn_items
            if not self.shop.is_item_sold(item[0])
        ]

        if not available_items_names:
            self.display_simple_message("All items are sold out!")
            return

        item_choice = self.validate_input(
            "Choose item to buy (or 'none' to exit): ",
            available_items_names + ['none']
        )

        if item_choice == 'none':
            return

        for item_name, item_data in self.shop.current_turn_items:
            if item_choice == item_name:
                if self.ship.money >= item_data["price"]:
                    self.ship.money -= item_data["price"]
                    self.ship.acquire_item(item_name)
                    self.shop.mark_item_sold(item_name)

                    self.display_simple_message([
                        f"You bought a {item_name}!",
                        f"Effect: {item_data['description']}",
                        f"Remaining credits: {self.format_money(self.ship.money)}"
                    ])
                else:
                    missing = item_data["price"] - self.ship.money
                    self.display_simple_message([
                        "Not enough money to buy this item.",
                        f"Price: {self.format_money(item_data['price'])}",
                        f"Your credits: {self.format_money(self.ship.money)}",
                        f"Missing: {self.format_money(missing)}"
                    ])
                return

        time.sleep(1)


# The game's other modules, imported last so that the modules can refer to each other.
from .contracts import ContractManager  # noqa: E402
from .passengers import Passenger, PassengerModule  # noqa: E402
from .places import Planet  # noqa: E402
