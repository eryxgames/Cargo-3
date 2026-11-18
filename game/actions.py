"""Actions at a location: scouting, mining, building, maps."""
import random

class Action:
    def __init__(self):
        # Base costs for actions
        self.action_costs = {
            'research': 100,
            'scout': 50,
            'geoscan': 75,
            'revolution': 100,
            'psychodynamics': 60
        }

        # Success chances for various actions
        self.base_success_rates = {
            'scout': 0.65,
            'geoscan': 0.70,
            'revolution': 0.50,
            'psychodynamics': 0.60
        }

    def research(self, planet, option, research_system):
        """
        Attempt to research a new technology
        Returns: (bool success, str message)
        """
        if option in research_system.unlocked_options:
            return False, "This research has already been completed."

        # Apply immediate benefits based on research type
        if option == 'exogeology':
            planet.exogeology = min(100,
                int(planet.exogeology * (1 + research_system.research_benefits['exogeology']['output_bonus'])))

        research_system.unlock(option)
        return True, f"Successfully researched {option}!"

    def scout_area(self, planet, research_system):
        """
        Scout the area for resources or items
        Returns: (bool success, str type, any value, str message)
        """
        # Calculate success chance
        success_chance = self.base_success_rates['scout']
        if 'telemetry' in research_system.unlocked_options:
            success_chance += research_system.research_benefits['telemetry']['scout_success']

        if random.random() < success_chance:
            discovery_type = random.choice(['tech', 'agri', 'item'])

            if discovery_type == 'item':
                item = random.choice(['scanner', 'probe', 'turrets', 'shield'])
                return True, 'item', item, f"Found a {item}!"
            else:
                amount = random.randint(10, 30)
                return True, discovery_type, amount, f"Found {amount} units of {discovery_type}!"

        return False, None, None, "Scouting attempt failed!"

    def geoscan(self, planet, research_system):
        """
        Scan for mineral deposits
        Returns: (bool success, str deposit_type, int amount, str message)
        """
        # Calculate success chance
        success_chance = self.base_success_rates['geoscan']
        if 'geophysics' in research_system.unlocked_options:
            success_chance += research_system.research_benefits['geophysics']['exogeology']

        if random.random() < success_chance:
            deposit_type = random.choice(['salt', 'fuel'])
            amount = random.randint(1000, 5000)

            if deposit_type not in planet.mineral_deposits:
                planet.mineral_deposits[deposit_type] = amount
                return True, deposit_type, amount, f"Found {amount} units of {deposit_type} deposits!"
            else:
                bonus = random.randint(500, 1000)
                planet.mineral_deposits[deposit_type] += bonus
                return True, deposit_type, bonus, f"Found additional {bonus} units of {deposit_type} deposits!"

        return False, None, None, "Geoscan failed to find any deposits!"

    def incite_revolution(self, planet, research_system):
        """
        Attempt to change planet's economy
        Returns: (bool success, str new_economy, str message)
        """
        # Calculate success chance
        success_chance = self.base_success_rates['revolution']
        if 'chronopolitics' in research_system.unlocked_options:
            success_chance += research_system.research_benefits['chronopolitics']['revolution_success']

        if random.random() < success_chance:
            current_economy = planet.economy
            possible_economies = ['Booming', 'Stable', 'Declining', 'Formative']
            possible_economies.remove(current_economy)
            new_economy = random.choice(possible_economies)
            planet.economy = new_economy
            return True, new_economy, f"Revolution successful! Economy changed to {new_economy}!"

        return False, None, "Revolution attempt failed!"

    def manipulate_market(self, planet, commodity, research_system):
        """
        Attempt to manipulate market prices
        Returns: (bool success, float price_change, str message)
        """
        if random.random() < self.base_success_rates['psychodynamics']:
            manipulation_power = research_system.research_benefits['psychodynamics']['price_control']
            current_price = planet.market[commodity]

            # Determine direction of manipulation (increase/decrease)
            direction = random.choice([-1, 1])
            change = direction * random.uniform(0.1, manipulation_power) * current_price

            # Apply change with bounds checking
            new_price = max(1, current_price + change)
            if commodity == 'salt':
                new_price = min(new_price, 150)
            elif commodity == 'fuel':
                new_price = min(new_price, 250)
            else:
                new_price = min(new_price, 200)

            planet.market[commodity] = new_price
            price_change = new_price - current_price
            return True, price_change, f"Successfully manipulated {commodity} price by {abs(price_change):.1f}!"

        return False, 0, "Market manipulation attempt failed!"


class ActionsMixin:
    """The Game's actions at a location. Game inherits it (game/world.py)."""
    def build_mining_platform(self):
        """Build a new mining platform on the current planet"""
        if not self.current_location.mineral_deposits:
            self.display_simple_message("No mineral deposits found! Use geoscan first.")
            return

        available_deposits = list(self.current_location.mineral_deposits.keys())
        deposit_type = self.validate_input(
            f"Choose deposit type to mine ({', '.join(available_deposits)}): ",
            available_deposits
        )

        if deposit_type is None:
            return

        cost = 10000
        if self.ship.money >= cost:
            self.ship.money -= cost
            self.current_location.mining_platforms.append({
                'type': deposit_type,
                'efficiency': self.current_location.exogeology,
                'capacity': random.randint(100, 200)
            })
            self.display_simple_message(f"Mining platform for {deposit_type} built!")
        else:
            self.display_simple_message("Not enough money to build mining platform.")

    def handle_building_construction(self, building_name, building_costs):
        """Handle building construction with proper capability checking and building process"""
        # Map short commands to full building names and their base types
        building_mapping = {
            'stockmarket': ('stockmarket', 'stockmarket'),
            'sm': ('stockmarket', 'stockmarket'),
            'permaculture': ('Permaculture Paradise', 'permaculture'),
            'pc': ('Permaculture Paradise', 'permaculture'),
            'organic': ('Organic Certification Authority', 'organic'),
            'oc': ('Organic Certification Authority', 'organic'),
            'agrobot': ('Agrobot Assembly Line', 'agrobot'),
            'ab': ('Agrobot Assembly Line', 'agrobot'),
            'nanotech': ('The Nanotech Nexus', 'nanotech'),
            'nt': ('The Nanotech Nexus', 'nanotech'),
            'neuroengineering': ('Neuroengineering Guild', 'neuroengineering'),
            'ne': ('Neuroengineering Guild', 'neuroengineering'),
            'mining': ('Mining Facility', 'mining'),
            'm': ('Mining Facility', 'mining'),
            'salt_refinery': ('Halide Extraction Refinery', 'salt_refinery'),
            'salt refinery': ('Halide Extraction Refinery', 'salt_refinery'),
            'sr': ('Halide Extraction Refinery', 'salt_refinery'),
            'fuel_refinery': ('Plasma Catalysis Refinery', 'fuel_refinery'),
            'fuel refinery': ('Plasma Catalysis Refinery', 'fuel_refinery'),
            'fr': ('Plasma Catalysis Refinery', 'fuel_refinery'),
            'combined_refinery': ('Elemental Fusion Refinery', 'combined_refinery'),
            'combined refinery': ('Elemental Fusion Refinery', 'combined_refinery'),
            'cr': ('Elemental Fusion Refinery', 'combined_refinery')
        }

        if building_name not in building_mapping:
            self.display_simple_message("Invalid building type.")
            return False

        full_building_name, base_type = building_mapping[building_name]

        # Get base cost and calculate final cost
        base_cost = building_costs.get(base_type, 3000)
        cost_multiplier = self.current_location.buildings.count(full_building_name) + 1
        final_cost = base_cost * cost_multiplier

        # Debug info
#        self.display_simple_message(f"Building request: {building_name}")
#        self.display_simple_message(f"Full name: {full_building_name}")
#        self.display_simple_message(f"Base type: {base_type}")
#        self.display_simple_message(f"Location type: {self.current_location.location_type}")
#        self.display_simple_message(f"Available money: {self.format_money(self.ship.money)}")
#        self.display_simple_message(f"Building cost: {self.format_money(final_cost)}")

        # Check if we can afford it
        if self.ship.money < final_cost:
            self.display_simple_message(f"Not enough money. Cost: {self.format_money(final_cost)}")
            return False

        # Deduct money first (will be refunded if build fails)
        self.ship.money -= final_cost

        # Add building directly to location's building list
        self.current_location.buildings.append(full_building_name)
        prices_before = dict(self.current_location.market)

        # Apply building effects
        if full_building_name == "Mining Facility":
            self.current_location.exogeology = min(100, self.current_location.exogeology + 10)
        elif full_building_name == "Permaculture Paradise":
            self.current_location.market['agri'] = max(1, self.current_location.market['agri'] * 0.8)
        elif full_building_name == "Organic Certification Authority":
            self.current_location.market['agri'] = self.current_location.market['agri'] * 1.2
        elif full_building_name == "Agrobot Assembly Line":
            self.current_location.market['agri'] = max(1, self.current_location.market['agri'] * 0.6)
        elif full_building_name == "The Nanotech Nexus":
            self.current_location.market['tech'] = max(1, self.current_location.market['tech'] * 0.85)
            self.current_location.market['agri'] = max(1, self.current_location.market['agri'] * 0.85)
        elif full_building_name == "Neuroengineering Guild":
            self.current_location.market['tech'] = self.current_location.market['tech'] * 1.3
        elif full_building_name == "stockmarket":
            self.current_location.stockmarket_base = True
            self.current_location.market['tech'] = max(1, self.current_location.market['tech'] - 10)
            self.current_location.market['agri'] = max(1, self.current_location.market['agri'] - 5)

        # a building changes what is usual here, not just today's price
        base = self.current_location.equilibrium()
        for good, before in prices_before.items():
            after = self.current_location.market[good]
            if before > 0 and after != before and base.get(good):
                base[good] = round(base[good] * after / before, 1)

        self.display_simple_message(f"Built {full_building_name} for {self.format_money(final_cost)} credits.")
        return True

    def handle_actions(self):
        # Display current research points
        self.display_simple_message(f"Available Research Points: {self.ship.research_points}")

        # Show available actions and their costs
        available_actions = {
            'research': "Research new technologies",
            'scout': f"Scout area (Cost: {self.action.action_costs['scout']} RP)",
            'geoscan': f"Geological scan (Cost: {self.action.action_costs['geoscan']} RP)",
            'revolution': f"Incite revolution (Cost: {self.action.action_costs['revolution']} RP)",
            'manipulate': f"Manipulate market (Cost: {self.action.action_costs['psychodynamics']} RP)",
            'status': "View research status",
            'back': "Return to main menu"
        }

        # Display available actions
        action_content = [["Actions:", "Cost/Description"]]
        for action, description in available_actions.items():
            action_content.append([action, description])
        print(self.create_box(action_content, 'single'))

        # Get user choice
        action = self.validate_input(
            "Choose action type: ",
            list(available_actions.keys())
        )

        if action == 'back':
            return

        if action == 'status':
            self.display_research_status()
            return

        if action == 'research':
            # Get available research options
            options = self.research.open_options(self.story.done)

            if not options:
                self.display_simple_message("All research options are unlocked!")
                return

            # Display research options and their costs
            research_content = [["Research Option", "Cost", "Description"]]
            research_descriptions = {
                'xenoeconomy': "Reduces trade taxes",
                'telemetry': "Increases scout success rate",
                'geophysics': "Improves mining efficiency",
                'chronopolitics': "Increases revolution success rate",
                'exogeology': "Increases mining output",
                'psychodynamics': "Allows market price manipulation"
            }

            for opt in options:
                cost = self.research.cost_of(opt)
                desc = research_descriptions.get(opt) or self.get_research_benefit_description(opt)
                if opt in BRANCHES:
                    desc += "; closes %s for good" % BRANCHES[BRANCHES[opt]["excludes"]]["name"].lower()
                research_content.append([opt, str(cost), desc])

            print(self.create_box(research_content, 'single'))

            option = self.validate_input(
                f"Choose research option ({', '.join(options)}): ",
                options
            )

            if option:
                if self.ship.research_points >= self.research.cost_of(option):
                    self.ship.research_points -= self.research.cost_of(option)
                    success, message = self.action.research(self.current_location, option, self.research)
                    if success:
                        self.story_manager.plot_points += 4
                        message += " +4 plot points."
                        if option == "segment_acoustics":
                            self.change_standing("dawn", 10)
                        elif option == "throw_dynamics":
                            self.change_standing("concord", 15)
                    self.display_simple_message(message)
                else:
                    self.display_simple_message(f"Not enough research points! Need: {self.research.cost_of(option)}")

        elif action == 'scout':
            if self.ship.research_points >= self.action.action_costs['scout']:
                self.ship.research_points -= self.action.action_costs['scout']
                success, type_, value, message = self.action.scout_area(self.current_location, self.research)
                self.display_simple_message(message)

                if success:
                    if type_ == 'item':
                        self.ship.acquire_item(value)
                        self.display_simple_message(f"Item added to inventory!")
                    else:
                        self.current_location.market[type_] += value
                        self.display_simple_message(f"Resources added to market!")
            else:
                self.display_simple_message(f"Not enough research points! Need: {self.action.action_costs['scout']}")

        elif action == 'geoscan':
            if self.ship.research_points >= self.action.action_costs['geoscan']:
                self.ship.research_points -= self.action.action_costs['geoscan']
                success, deposit_type, amount, message = self.action.geoscan(self.current_location, self.research)
                self.display_simple_message(message)

                if success:
                    self.display_simple_message(f"Use 'build mining' command to exploit the deposit.")
            else:
                self.display_simple_message(f"Not enough research points! Need: {self.action.action_costs['geoscan']}")

        elif action == 'revolution':
            if self.ship.research_points >= self.action.action_costs['revolution']:
                self.ship.research_points -= self.action.action_costs['revolution']
                success, new_economy, message = self.action.incite_revolution(self.current_location, self.research)
                self.display_simple_message(message)
            else:
                self.display_simple_message(f"Not enough research points! Need: {self.action.action_costs['revolution']}")

        elif action == 'manipulate':
            if 'psychodynamics' not in self.research.unlocked_options:
                self.display_simple_message("Market manipulation research required!")
                return

            if self.ship.research_points >= self.action.action_costs['psychodynamics']:
                # Show current market prices
                market_content = [["Commodity", "Current Price"]]
                for commodity in ['tech', 'agri', 'salt', 'fuel']:
                    if commodity not in self.current_location.banned_commodities:
                        market_content.append([commodity.capitalize(),
                                        str(self.format_money(self.current_location.market[commodity]))])
                print(self.create_box(market_content, 'single'))

                commodity = self.validate_input(
                    "Choose commodity to manipulate (tech/agri/salt/fuel): ",
                    ['tech', 'agri', 'salt', 'fuel']
                )

                if commodity:
                    self.ship.research_points -= self.action.action_costs['psychodynamics']
                    success, price_change, message = self.action.manipulate_market(
                        self.current_location, commodity, self.research
                    )
                    self.display_simple_message(message)
            else:
                self.display_simple_message(f"Not enough research points! Need: {self.action.action_costs['psychodynamics']}")

        # Update production cooldowns after any action
        for resource_type in list(self.current_location.production_cooldown.keys()):
            if self.current_location.production_cooldown[resource_type] > 0:
                self.current_location.production_cooldown[resource_type] -= 1

    def handle_buy_map(self):
        if self.ship.money >= 200:
            self.ship.money -= 200
            new_locations = []
            for location in self.locations:
                if location.name not in self.known_locations and location.location_type in self.unlocked_location_types:
                    new_locations.append(location)
                    self.known_locations.append(location.name)

            if new_locations:
                map_content = []
                # Header
                map_content.append(["New Locations!"])
                map_content.append([""])
                map_content.append(["Location", "Type", "Tech", "Agri", "Economy"])

                # Location data
                for location in new_locations:
                    features = []
                    if location.mining_platforms:
                        features.append("Mining")
                    if location.buildings:
                        features.append("Buildings")
                    if location.stockmarket_base:
                        features.append("Stock Market")

                    map_content.append([
                        location.name,
                        location.location_type,
                        str(location.tech_level),
                        str(location.agri_level),
                        location.economy
                    ])

                    # Add features as separate rows with proper indentation
                    if features:
                        map_content.append(["└─ Features: " + ", ".join(features), "", "", "", ""])

                print(self.create_box(map_content, 'double'))
                input("Press Enter to continue...")
            else:
                self.ship.money += 200  # Refund if no new locations
                self.display_simple_message("No new locations to discover!")
        else:
            self.display_simple_message("Not enough money to buy a map.")

    def handle_update_map(self):
        if self.ship.money >= 350:
            self.ship.money -= 350

            market_content = []
            # Header
            market_content.append(["Map Update"])
            market_content.append([""])
            market_content.append(["Location", "Tech", "Agri", "Salt", "Fuel"])

            # Show detailed info for known locations
            has_data = False
            for location_name in self.known_locations:
                location = next((loc for loc in self.locations if loc.name == location_name), None)
                if location:
                    has_data = True
                    tech_price = "BANNED" if 'tech' in location.banned_commodities else self.format_money(location.market['tech'])
                    agri_price = "BANNED" if 'agri' in location.banned_commodities else self.format_money(location.market['agri'])
                    salt_price = "BANNED" if 'salt' in location.banned_commodities else self.format_money(location.market['salt'])
                    fuel_price = "BANNED" if 'fuel' in location.banned_commodities else self.format_money(location.market['fuel'])

                    market_content.append([
                        location.name,
                        tech_price,
                        agri_price,
                        salt_price if location.trades_bulk('salt') else "No Mine",
                        fuel_price if location.trades_bulk('fuel') else "No Mine"
                    ])

                    # Add special features as separate rows
                    features = []
                    if location.stockmarket_base:
                        features.append("Stock Market")
                    if location.buildings:
                        features.append(f"Buildings: {', '.join(location.buildings)}")
                    if location.mining_platforms:
                        features.append(f"Mining Platforms: {len(location.mining_platforms)}")

                    if features:
                        for feature in features:
                            market_content.append(["└─ " + feature, "", "", "", ""])

            if has_data:
                print(self.create_box(market_content, 'double'))
                input("Press Enter to continue...")
            else:
                self.ship.money += 350  # Refund if no data to show
                self.display_simple_message("No new information available!")
        else:
            self.display_simple_message("Not enough money to update the map.")

    def handle_mining(self):
        """Handle mining-related actions"""
        options = ['build', 'status', 'research']
        choice = self.validate_input(
            "Mining options (build/status/research): ",
            options
        )

        if choice == 'build':
            self.build_mining_platform()
        elif choice == 'status':
            self.display_mining_status()
        elif choice == 'research':
            cost = self.research.research_costs['exogeology']
            if 'exogeology' in self.research.unlocked_options:
                self.display_simple_message("Mining efficiency research is already completed.")
            elif self.ship.research_points >= cost:
                self.ship.research_points -= cost
                self.action.research(self.current_location, 'exogeology', self.research)
                self.display_simple_message("Mining efficiency research completed!")
            else:
                self.display_simple_message(f"Not enough research points! Need: {cost}")

    def display_mining_status(self):
        """Display mining operations status"""
        content = [
            ["Mining Status"],
            [f"Planet Efficiency: {self.current_location.exogeology}%"],
            ["Active Platforms:"]
        ]

        for platform in self.current_location.mining_platforms:
            content.append([
                f"{platform['type'].capitalize()}: "
                f"Efficiency {platform['efficiency']}% "
                f"Capacity {platform['capacity']}"
            ])

        if self.current_location.mineral_deposits:
            content.append(["Available Deposits:"])
            for deposit, amount in self.current_location.mineral_deposits.items():
                content.append([f"{deposit.capitalize()}: {amount} units"])

        print(self.create_box(content, 'double'))
from .research import BRANCHES  # noqa: E402
