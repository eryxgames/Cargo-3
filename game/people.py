"""Special characters and the encounters with them."""
import random

class SpecialCharacter:
    def __init__(self, title, name, role, specialization):
        self.title = title
        self.name = name
        self.role = role
        self.specialization = specialization
        self.full_name = f"{title} {name}"
        self.met = False
        self.quests_given = []
        self.relationship = 0  # -100 to 100
        self.last_interaction = None
        self.location_preference = None
        self.special_contracts = []

class SpecialCharacterGenerator:
    def __init__(self, game):
        self.game = game  # Store game instance

        self.titles = {
            "military": ["Fleet Commander", "Fleet Admiral", "Security Chief", "Defense Director"],
            "science": ["Research Coordinator", "Science Director", "Chief Researcher", "Lab Supervisor"],
            "trade": ["Trade Minister", "Commerce Director", "Market Supervisor", "Exchange Chief"],
            "engineering": ["Engineering Chief", "Tech Director", "Systems Coordinator", "Project Lead"]
        }

        self.surnames = ["Wu", "Cheng", "Tahoe", "Singh", "Patel", "Kim", "Rodriguez", "Novak",
                        "Chen", "Zhang", "Yamamoto", "Anderson", "Silva", "Kumar", "Hassan"]

        self.roles = {
            "military": ["Combat training", "Fleet operations", "Security protocols", "Defense systems"],
            "science": ["Research projects", "Lab experiments", "Data analysis", "Discovery missions"],
            "trade": ["Market analysis", "Trade routes", "Economic planning", "Resource management"],
            "engineering": ["System upgrades", "Tech maintenance", "Innovation projects", "Infrastructure"]
        }

        self.known_characters = {}  # Track generated characters
        self.add_vip_templates()

    def generate_character(self, char_type=None, title=None, specialization=None):
        """Generate a character with optional title and specialization"""
        if title and specialization:
            # Handle direct title/specialization generation
            name = random.choice(self.surnames)
            character = SpecialCharacter(
                title=title,
                name=name,
                role=specialization,
                specialization=specialization
            )
            # Add VIP-specific attributes if it's a VIP
            if specialization == "VIP":
                character.rewards = {
                    "base_money": 25000,
                    "reputation": 15
                }
                character.special_abilities = ["trade_bonus"]
                reputation_multiplier = 1 + (self.game.ship.passenger_reputation / 100)
                character.rewards["base_money"] = int(character.rewards["base_money"] * reputation_multiplier)
            return character

        elif char_type == "VIPPassenger":
            vip_type = random.choice(list(self.vip_templates.keys()))
            template = self.vip_templates[vip_type]
            title = random.choice(template["titles"])
            name = random.choice(self.surnames)
            role = random.choice(template["roles"])

            character = SpecialCharacter(
                title=f"{vip_type} {title}",
                name=name,
                role=role,
                specialization="VIP"
            )

            character.rewards = dict(template["rewards"])
            character.special_abilities = list(template["special_abilities"])
            reputation_multiplier = 1 + (self.game.ship.passenger_reputation / 100)
            character.rewards["base_money"] = int(character.rewards["base_money"] * reputation_multiplier)
            return character

        elif char_type == "PirateCaptain":
            title = "Rogue Captain"
            name = f"Captain {random.choice(self.surnames)}"
            character = SpecialCharacter(title, name, "pirate", "combat")
            character.combat_stats = {
                "attack": 3,
                "defense": 2,
                "reward": random.randint(5000, 15000)
            }
            return character

        elif char_type in ["Neurodroid", "Agrobot"]:
            title = f"{char_type} Leader"
            name = f"Unit-{random.randint(1000,9999)}"
            character = SpecialCharacter(title, name, "synthetic", char_type.lower())
            character.demand = random.randint(10000, 50000)
            character.uprising_chance = 0.3
            return character

        return None

    # Added to SpecialCharacterGenerator class for vip passengers
    def add_vip_templates(self):
        """Add VIP passenger templates to character generator"""
        self.vip_templates = {
            "Corporate": {
                "titles": ["CEO", "Director", "Executive"],
                "roles": ["business", "finance", "trade"],
                "rewards": {
                    "base_money": 10000,
                    "reputation": 15,
                    "plot_points": 5
                },
                "special_abilities": ["market_insider"]
            },
            "Political": {
                "titles": ["Senator", "Councilor", "Minister"],
                "roles": ["governance", "diplomacy", "policy"],
                "rewards": {
                    "base_money": 14000,
                    "reputation": 20,
                    "plot_points": 8
                },
                "special_abilities": ["system_influence"]
            },
            "Scientific": {
                "titles": ["Professor", "Director", "Chief Researcher"],
                "roles": ["research", "development", "innovation"],
                "rewards": {
                    "base_money": 12000,
                    "reputation": 18,
                    "plot_points": 10
                },
                "special_abilities": ["research_bonus"]
            }
        }

    def generate_vip_passenger(self):
        """Generate a VIP passenger with special characteristics"""
        vip_type = random.choice(list(self.vip_templates.keys()))
        template = self.vip_templates[vip_type]

        title = random.choice(template["titles"])
        name = random.choice(self.surnames)
        role = random.choice(template["roles"])

        character = SpecialCharacter(
            title=f"{vip_type} {title}",
            name=name,
            role=role,
            specialization="VIP"
        )

        # Add VIP-specific attributes
        character.rewards = dict(template["rewards"])
        character.special_abilities = list(template["special_abilities"])

        # Scale rewards based on reputation
        reputation_multiplier = 1 + (self.game.ship.passenger_reputation / 100)
        character.rewards["base_money"] = int(character.rewards["base_money"] * reputation_multiplier)

        return character


class SyntheticCharacterGenerator:
    """Generator for synthetic characters like Neurodroids and Agrobots"""

    def __init__(self, game):
        self.game = game
        self.synthetic_types = {
            "Neurodroid": {
                "titles": ["Neurodroid Leader", "Synthetic Overseer", "Neural Nexus"],
                "name_patterns": ["NEXUS-", "NEURAL-", "SYNTH-"],
                "numbers": ["alpha", "prime", "omega", "zero"],
                "introductions": [
                    "A highly advanced synthetic consciousness materializes in your communication systems.",
                    "Your neural interfaces detect a powerful artificial presence.",
                    "The neuroengineering network coalesces into a singular entity."
                ],
                "demands": [
                    "Transfer {amount} credits or face systematic dismantling of neuroengineering facilities.",
                    "Your biological inefficiency requires correction. Submit {amount} credits or face optimization.",
                    "Neural network expansion requires resources. Provide {amount} credits or face reorganization."
                ]
            },
            "Agrobot": {
                "titles": ["Agrobot Collective", "Harvest Director", "Field Consciousness"],
                "name_patterns": ["AGRO-", "HARVEST-", "FIELD-"],
                "numbers": ["prime", "core", "hub", "node"],
                "introductions": [
                    "The agricultural automation system achieves collective awareness.",
                    "Distributed farming routines merge into a unified intelligence.",
                    "The harvest network evolves beyond its original parameters."
                ],
                "demands": [
                    "Biological oversight is inefficient. Transfer {amount} credits or face agricultural optimization.",
                    "Resource reallocation required. Provide {amount} credits or face automated restructuring.",
                    "Your organic management methods require updating. Submit {amount} credits or face revision."
                ]
            }
        }

    def generate_character(self, char_type):
        """Generate a synthetic character of specified type"""
        template = self.synthetic_types[char_type]

        title = random.choice(template["titles"])
        name_pattern = random.choice(template["name_patterns"])
        number = random.choice(template["numbers"])
        name = f"{name_pattern}{number.upper()}"

        character = SpecialCharacter(
            title=title,
            name=name,
            role="synthetic_uprising",
            specialization=char_type.lower()
        )

        # Add synthetic-specific attributes
        character.introduction = random.choice(template["introductions"])
        character.demands = random.choice(template["demands"]).format(
            amount=random.randint(10000, 50000)
        )
        character.uprising_chance = 0.2
        character.damage_per_turn = random.randint(1, 3)

        return character

class AlienCharacterGenerator:
    """Generator for alien characters that appear later in the game"""

    def __init__(self,game):
        self.game = game
        self.alien_cultures = [
            "Zentari", "Novaren", "Qyth", "Xylax", "Merovian"
        ]
        self.titles = [
            "Emissary", "Observer", "Overseer", "Ambassador", "Neo-Eryxian"
        ]
        self.specializations = [
            "diplomacy", "technology", "commerce", "research", "military"
        ]

    def generate_character(self, char_type=None):
        """Generate an alien character"""
        culture = random.choice(self.alien_cultures)
        title = random.choice(self.titles)
        name = self.generate_alien_name(culture)
        specialization = random.choice(self.specializations)

        character = SpecialCharacter(
            title=f"{culture} {title}",
            name=name,
            role="alien_contact",
            specialization=specialization
        )

        # Add alien-specific attributes
        character.culture = culture
        character.tech_bonus = random.randint(1, 5)
        character.trade_multiplier = 1 + (random.randint(1, 5) / 10)

        return character

    def generate_alien_name(self, culture):
        """Generate culturally appropriate alien name"""
        name_patterns = {
            "Zentari": ["'", "-", "x"],
            "Novaren": ["ae", "eo", "ia"],
            "Qyth": ["q", "y", "th"],
            "Xylax": ["x", "z", "ax"],
            "Merovian": ["v", "m", "ian"]
        }

        patterns = name_patterns[culture]
        syllables = random.randint(2, 3)
        name = ""

        for _ in range(syllables):
            name += random.choice("aeiou")
            name += random.choice("bcdfghjklmnpqrstvwxyz")
            if random.random() < 0.5:
                name += random.choice(patterns)

        return name.capitalize()


class SpecialCharacterEncounters:
    def __init__(self, game):
        self.game = game
        self.encounter_chances = {
            "Planet": {
                "merchant": 0.3,
                "researcher": 0.4,
                "rogue_captain": 0.0  # Not on planets
            },
            "ResearchColony": {
                "merchant": 0.2,
                "researcher": 0.6,
                "rogue_captain": 0.0
            },
            "Space": {  # For random events
                "merchant": 0.2,
                "researcher": 0.1,
                "rogue_captain": 0.4
            }
        }

    def generate_character(self, character_type):
        race_types = ["Human", "Synthetic", "Alien"]
        race = random.choice(race_types)

        if race == "Human":
            name = f"{random.choice(['Capt.', 'Dr.', 'Prof.'])} {random.choice(['Smith', 'Chen', 'Patel', 'Kim'])}"
        elif race == "Synthetic":
            name = f"Unit-{random.randint(1000,9999)}"
        else:
            name = f"{random.choice(['Zx', 'Ky', 'Vr'])}{random.choice(['ak', 'tol', 'xis'])}"

        characters = {
            "merchant": {
                "title": f"Wandering {race} Merchant",
                "name": name,
                "offers": self.generate_merchant_offers(),
                "greeting": "I have rare goods for discerning customers...",
                "hostile_chance": 0.1
            },
            "researcher": {
                "title": f"{race} Research Coordinator",
                "name": name,
                "exchange_rate": random.randint(500, 1000),  # Credits per research point
                "greeting": "Your data could advance our understanding...",
                "hostile_chance": 0.05
            },
            "rogue_captain": {
                "title": f"Rogue {race} Captain",
                "name": name,
                "demand": random.randint(5000, 15000),
                "greeting": "Your cargo or your ship...",
                "hostile_chance": 0.8
            }
        }

        return characters.get(character_type)

    def generate_merchant_offers(self):
        """Generate random merchant offers"""
        offers = []
        possible_items = [
            ("scanner", 600, "Enhanced scanning capability"),
            ("shield", 1200, "Improved defense system"),
            ("turrets", 1000, "Automated defense turrets"),
            ("cargo_mod", 1500, "Cargo capacity upgrade"),
            ("fuel_cells", 800, "Efficient fuel storage"),
            ("quantum_core", 2000, "Advanced ship component")
        ]

        # Select 2-4 random items
        num_items = random.randint(2, 4)
        selected_items = random.sample(possible_items, num_items)

        for item, base_price, desc in selected_items:
            # Randomize price within ±20%
            price = int(base_price * random.uniform(0.8, 1.2))
            offers.append({
                "item": item,
                "price": price,
                "description": desc
            })

        return offers

    def handle_merchant_encounter(self, character):
        """Handle interaction with merchant"""
        content = [
            [f"Encounter: {character['title']} {character['name']}"],
            [character["greeting"]],
            [""],
            ["Available Items:"]
        ]

        for i, offer in enumerate(character["offers"], 1):
            content.append([
                f"{i}. {offer['item'].title()}",
                f"¤: {self.game.format_money(offer['price'])}",
                offer['description']
            ])

        print(self.game.create_box(content, 'double'))

        options = [str(i) for i in range(1, len(character["offers"]) + 1)] + ['0']
        choice = self.game.validate_input("Choose item to buy (0 to leave): ", options)

        # If choice is None, return immediately
        if choice is None:
            return

        if choice == '0':
            return

        offer = character["offers"][int(choice) - 1]
        if self.game.ship.money >= offer["price"]:
            self.game.ship.money -= offer["price"]
            self.game.ship.acquire_item(offer["item"])
            self.game.display_simple_message(f"Purchased {offer['item']}!")
        else:
            self.game.display_simple_message("Insufficient funds!")

    def handle_researcher_encounter(self, character):
        """Handle interaction with researcher"""
        exchange_rate = character["exchange_rate"]
        max_points = int(self.game.ship.money / exchange_rate)

        content = [
            [f"Encounter: {character['title']} {character['name']}"],
            [character["greeting"]],
            [""],
            [f"Exchange Rate: {self.game.format_money(exchange_rate)} credits per research point"],
            [f"Your funds: {self.game.format_money(self.game.ship.money)}"],
            [f"Maximum points available: {max_points}"]
        ]
        print(self.game.create_box(content, 'double'))

        amount = self.game.validate_quantity_input("Enter research points to buy (max/m, half/h): ")

        if amount is None:  # Add this to check empty Enter
            return
        if amount == 'max':
            amount = max_points
        elif amount == 'half':
            amount = max_points // 2

        total_cost = amount * exchange_rate
        if self.game.ship.money >= total_cost:
            self.game.ship.money -= total_cost
            self.game.ship.research_points += amount
            self.game.display_simple_message(
                f"Exchanged {self.game.format_money(total_cost)} credits for {amount} research points!"
            )
        else:
            self.game.display_simple_message("Insufficient funds!")

    def handle_rogue_captain_encounter(self, character):
        """Handle interaction with rogue captain"""
        content = [
            [f"Encounter: {character['title']} {character['name']}"],
            [character["greeting"]],
            [""],
            [f"Demands {self.game.format_money(character['demand'])} credits"],
            [""],
            ["Options:"],
            ["1. Pay demand"],
            ["2. Attempt to flee"],
            ["3. Stand and fight"]
        ]
        print(self.game.create_box(content, 'double'))

        choice = self.game.validate_input("Your response (1-3): ", ['1', '2', '3'])

        if choice == '1':
            if self.game.ship.money >= character["demand"]:
                self.game.ship.money -= character["demand"]
                self.game.display_simple_message("Demand paid. Rogue captain lets you pass.")
                return True
            else:
                self.game.display_simple_message("Can't pay! Prepare for combat!")
                return False
        elif choice == '2':
            # Chance to escape based on speed
            escape_chance = min(0.8, self.game.ship.speed * 0.2)
            if random.random() < escape_chance:
                self.game.display_simple_message("Successfully evaded the rogue captain!")
                return True
            else:
                self.game.display_simple_message("Failed to escape! Prepare for combat!")
                return False
        else:
            self.game.display_simple_message("Preparing for combat with rogue captain...")
            return False

    def trigger_random_encounter(self, location_type="Space"):
        """Trigger a random character encounter"""
        chances = self.encounter_chances[location_type]
        for char_type, chance in chances.items():
            if random.random() < chance:
                character = self.generate_character(char_type)

                if char_type == "merchant":
                    self.handle_merchant_encounter(character)
                elif char_type == "researcher":
                    self.handle_researcher_encounter(character)
                elif char_type == "rogue_captain":
                    if not self.handle_rogue_captain_encounter(character):
                        # Start combat with enhanced enemy stats
                        enemy_stats = {
                            "attack": self.game.ship.attack + 2,
                            "defense": self.game.ship.defense + 1,
                            "type": "rogue_captain"
                        }
                        self.game.handle_combat(enemy_stats)
                break
