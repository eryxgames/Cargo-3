"""Places: locations, the kinds of location, and the manager that unlocks and reveals them."""
import random

# Define the Location base class, updated
class Location:
    def __init__(self, name, location_type, tech_level, agri_level, research_points, economy):
        self.name = name
        self.location_type = location_type
        self.tech_level = tech_level
        self.agri_level = agri_level
        self.research_points = research_points
        self.economy = economy
        self.stockmarket_base = False
        self.stockmarket_cost = 5000
        self.buildings = []
        self.exogeology = self.get_base_exogeology()
        self.banned_commodities = []
        self.ban_duration = {}
        self.mineral_deposits = {}
        self.mining_platforms = []
        self.production_cooldown = {}
        # Generate market after initializing attributes
        self.market = self.generate_market()
        self.security_level = 5  # Initialize with medium security level

    @property
    def commands(self):
        """Get all commands for this location"""
        return LocationCommands.get_commands_for_location(self)


    def build_mining_platform(self, deposit_type, cost):
        """Build a new mining platform for specified deposit"""
        if deposit_type in self.mineral_deposits:
            if self.mineral_deposits[deposit_type] > 0:
                self.mining_platforms.append({
                    'type': deposit_type,
                    'efficiency': self.exogeology,
                    'capacity': random.randint(100, 200)
                })
                self.mineral_deposits[deposit_type] -= 1
                return True
        return False

    def generate_market(self):
        # Generate base market prices based on tech and agri levels
        market = {
            'tech': max(10, 100 - (self.tech_level * 10)),
            'agri': 50 + (self.agri_level * 5),
            'salt': 0,
            'fuel': 0
        }

        # Apply refinery effects
        if "Halide Extraction Refinery" in self.buildings:
            # Salt refinery lowers agri prices, sets salt price
            market['salt'] = random.randint(100, 150)
            market['agri'] = max(1, int(market['agri'] * 0.8))

        if "Plasma Catalysis Refinery" in self.buildings:
            # Fuel refinery lowers tech prices, sets fuel price
            market['fuel'] = random.randint(150, 200)
            market['tech'] = max(1, int(market['tech'] * 0.8))

        if "Elemental Fusion Refinery" in self.buildings:
            # Combined refinery raises tech and agri prices
            market['tech'] = int(market['tech'] * 1.3)
            market['agri'] = int(market['agri'] * 1.3)

        return market


    # A full hold (about 440 units) moves a planet's price by about 8%. A stock market
    # makes the market deeper.
    MARKET_DEPTH = {"Planet": 700, "AsteroidBase": 500, "DeepSpaceOutpost": 350, "ResearchColony": 300}
    MARKET_IMPACT = 0.13

    def trades_bulk(self, item):
        """Salt and fuel trade only where they are mined: a platform here, or an asteroid
        base, which mines its own (and is where convoys and in-system ships fuel up)."""
        return self.location_type == "AsteroidBase" or any(p['type'] == item for p in self.mining_platforms)

    def market_depth(self):
        return self.MARKET_DEPTH.get(self.location_type, 400) * (2 if self.stockmarket_base else 1)

    def equilibrium(self):
        """The prices this market drifts back to. A market that opened later (a refinery)
        takes its first price as its usual one."""
        base = self.__dict__.setdefault("base_market", dict(self.market))
        for item, price in self.market.items():
            if price > 0 and not base.get(item):
                base[item] = price
        return base

    def trade_price(self, item, quantity, selling):
        """The average price per unit for a trade of this size: big loads move the price."""
        price = self.market[item]
        shift = self.MARKET_IMPACT * quantity / self.market_depth()
        return price * (1 - shift / 2) if selling else price * (1 + shift / 2)

    def trade_impact(self, item, quantity, selling):
        """After a trade the price stays where the load pushed it, then recovers slowly."""
        base = self.equilibrium().get(item) or self.market[item]
        if self.market[item] <= 0 or base <= 0:
            return
        shift = self.MARKET_IMPACT * quantity / self.market_depth()
        price = self.market[item] * ((1 - shift) if selling else (1 + shift))
        self.market[item] = round(max(base * 0.35, min(base * 2.5, price)), 1)

    def recover(self, rate=0.15):
        """Once a turn: prices drift a little way back to their usual level."""
        base = self.equilibrium()
        for item, price in self.market.items():
            usual = base.get(item, 0)
            if usual > 0 and price > 0:
                self.market[item] = round(price + (usual - price) * rate, 1)

    def calculate_tax_rate(self, player_rank, profit):
        """Calculate tax rate based on player rank and location type"""
        base_tax = 0.05  # 5% base tax
        # famous captains pay a little more (it was up to 2.5 times; with markets that feel
        # every load, that left late traders no margin at all)
        rank_multiplier = {
            "Explorer": 1,
            "Pilot": 1.07,
            "Captain": 1.14,
            "Commander": 1.21,
            "Star Commander": 1.28,
            "Space Admiral": 1.35,
            "Stellar Hero": 1.42,
            "Galactic Legend": 1.5
        }

        # Reduce tax based on number of buildings
        building_discount = len(self.buildings) * 0.02  # 2% reduction per building

        # Location-specific tax adjustments
        location_tax_modifier = {
            "Planet": 1.0,
            "AsteroidBase": 0.8,  # Lower taxes to encourage mining
            "DeepSpaceOutpost": 1.2,  # Higher taxes for premium services
            "ResearchColony": 1.5   # Highest taxes due to research benefits
        }

        location_modifier = location_tax_modifier.get(self.location_type, 1.0)
        final_tax_rate = (base_tax * rank_multiplier.get(player_rank, 1) * location_modifier) - building_discount
        return max(0.01, min(0.25, final_tax_rate))  # Keep between 1% and 25%

    def add_temporary_ban(self, commodity, duration):
        """Add a temporary trade ban for a commodity"""
        if commodity not in self.banned_commodities:
            self.banned_commodities.append(commodity)
            self.ban_duration[commodity] = duration


    def get_capabilities(self):
        """Get capabilities for this location type"""
        return LocationCapabilities.CAPABILITIES.get(self.location_type, {})


    def can_trade(self, commodity):
        """Check if this location can trade a specific commodity"""
        # First, check if commodity is banned - this should be the first check
        if commodity in self.banned_commodities:
            return False

        # Always allow standard commodities
        if commodity in self.get_capabilities().get("can_trade", []):
            return True

        # Allow salt/fuel if corresponding refinery exists
        if commodity == 'salt' and any(b == "Halide Extraction Refinery" for b in self.buildings):
            return True

        if commodity == 'fuel' and any(b == "Plasma Catalysis Refinery" for b in self.buildings):
            return True

        # Allow trading all commodities if Combined Refinery exists
        if any(b == "Elemental Fusion Refinery" for b in self.buildings):
            return True

        return False

    def can_build(self, building_type):
        """Check if this location can build a specific building with debug info"""
        capabilities = self.get_capabilities()
        can_build_list = capabilities.get("can_build", [])

        # Convert building type to match capability format
        building_type = building_type.lower()

        # Remove any facility/paradise/authority suffix for comparison
        building_base = building_type.split()[0]

        # Return whether the base building type is in capabilities
        return building_base in can_build_list

    def can_mine(self, resource_type):
        """Check if this location can mine a specific resource"""
        return resource_type in self.get_capabilities().get("can_mine", [])

    def get_base_exogeology(self):
        """Get base mining efficiency with randomized ranges per location type"""
        ranges = {
            "Planet": (35, 65),
            "AsteroidBase": (68, 78),
            "DeepSpaceOutpost": (42, 52),
            "ResearchColony": (16, 36)
        }
        base_range = ranges.get(self.location_type, (50, 60))
        return random.randint(*base_range)

    # Log, player log. Example usage:
    # game.story_manager.display_story_progress()

class LocationManager:
    """Manages location interactions with story and quest systems"""
    def __init__(self, game):
        self.game = game
        self.location_quests = {
            "AsteroidBase": {
                "unlock_requirements": {
                    # was "mining_quests_completed": 3, which nothing in the game can
                    # satisfy before Asteroid Bases exist; a working mine is the proof
                    "mining_platforms_built": 1,
                    "research_points": 50
                },
                "unlock_quest": {
                    "name": "Mysterious Mining Signals",
                    "description": "Investigate unusual mining activity signals",
                    "reward_money": 10000,
                    "reward_rp": 100
                }
            },
            "DeepSpaceOutpost": {
                "unlock_requirements": {
                    "combat_victories": 5,
                    "research_points": 75
                },
                "unlock_quest": {
                    "name": "Frontier Defense",
                    "description": "Help establish a secure trading route",
                    "reward_money": 15000,
                    "reward_rp": 150
                }
            },
            "Planet": {
                "unlock_requirements": {
                    "research_points": 50,
                    "trades_completed": 5
                },
                "unlock_quest": {
                    "name": "Establish Trading Network",
                    "description": "Complete trades across multiple systems",
                    "reward_money": 5000,
                    "reward_rp": 50,
                    "completion_criteria": {
                        "trades_completed": 10,
                        "different_locations": 3
                    }
                }
            },
            "ResearchColony": {
                "unlock_requirements": {
                    "research_points": 100,
                    "discoveries": 3
                },
                "unlock_quest": {
                    "name": "Scientific Breakthrough",
                    "description": "Assist in a major research project",
                    "reward_money": 20000,
                    "reward_rp": 200,
                    "completion_criteria": {
                        "research_points_gained": 150,
                        "analysis_completed": 3,
                        "experiments_conducted": 2
                    }
                }
            }
        }

        self.location_story_events = {
            "AsteroidBase": [
                "mineral_discovery",
                "pirate_hideout",
                "ancient_technology"
            ],
            "DeepSpaceOutpost": [
                "smuggler_network",
                "alien_contact",
                "trade_revolution"
            ],
            "ResearchColony": [
                "breakthrough_discovery",
                "experiment_crisis",
                "alien_artifacts"
            ]
        }

    def handle_location_discovery(self, location):
        """Handle discovery of a new location"""
        if location.name not in self.game.discovered_locations:
            # Calculate discovery rewards based on location type
            base_reward = 1000
            base_research = 20

            location_multipliers = {
                "Planet": 1.0,
                "AsteroidBase": 1.5,
                "DeepSpaceOutpost": 2.0,
                "ResearchColony": 2.5
            }

            multiplier = location_multipliers.get(location.location_type, 1.0)

            # Apply chapter progression bonus
            chapter_bonus = 1.0 + (self.game.story_manager.get_chapter_number() * 0.2)


            # Calculate final rewards
            discovery_reward = int(base_reward * multiplier * chapter_bonus)
            research_reward = int(base_research * multiplier * chapter_bonus)

            # Award rewards
            self.game.ship.money += discovery_reward
            self.game.ship.research_points += research_reward

            # Update discovered locations
            if not hasattr(self.game, 'discovered_locations'):
                self.game.discovered_locations = set()
            self.game.discovered_locations.add(location.name)

            # Trigger story progression
            self.game.story_manager.check_discovery_milestone(location)

            # Check for quest updates if quest system exists
            if hasattr(self.game, 'quest_system'):
                self.game.quest_system.update_discovery_quests(location)

            # Display discovery message
            self.game.display_story_message([
                f"Discovered new location: {location.name}!",
                f"Earned {self.game.format_money(discovery_reward)} credits",
                f"Gained {research_reward} research points"
            ])


    def trigger_location_events(self, location):
        """Trigger events specific to a location type"""
        if location.location_type in self.location_story_events:
            possible_events = self.location_story_events[location.location_type]
            if possible_events and random.random() < 0.3:  # 30% chance for event
                event = random.choice(possible_events)
                self.game.story_manager.trigger_story_event(event,
                    {"location": location.name, "type": location.location_type})

    def check_location_unlock_progress(self, location_type):
        """Check if a location type can be unlocked based on player progress"""
        if location_type not in self.location_quests:
            return False

        requirements = self.location_quests[location_type]["unlock_requirements"]

        # Check mining quest requirement
        if "mining_quests_completed" in requirements:
            completed = len([q for q in self.game.quest_system.completed_quests
                           if q.quest_type == "mining"])
            if completed < requirements["mining_quests_completed"]:
                return False

        # Check mining platforms built anywhere
        if "mining_platforms_built" in requirements:
            platforms = sum(len(loc.mining_platforms) for loc in self.game.locations)
            if platforms < requirements["mining_platforms_built"]:
                return False

        # Check combat victories - now using total from dictionary
        if "combat_victories" in requirements:
            total_victories = self.game.ship.combat_victories['total']
            if total_victories < requirements["combat_victories"]:
                return False

        # Check research points
        if "research_points" in requirements:
            if self.game.ship.research_points < requirements["research_points"]:
                return False

        # Check discoveries
        if "discoveries" in requirements:
            if len(self.game.story_manager.completed_story_beats) < requirements["discoveries"]:
                return False

        return True

    def trigger_location_unlock_quest(self, location_type):
        """Create and trigger the unlock quest for a location type"""
        if location_type in self.location_quests:
            quest_data = self.location_quests[location_type]["unlock_quest"]

            # Create quest with unique type
            story = self.game.story
            nid = "unlock." + location_type
            quest = Quest(
                name=story.title_of(nid, quest_data["name"]),
                description=" ".join(story.text_of(nid, fallback=quest_data["description"])),
                reward_money=quest_data["reward_money"],
                reward_rp=quest_data["reward_rp"],
                quest_type=f"unlock_{location_type}",  # Make type unique
                requirements={"location_type": location_type},
                on_complete=("unlock_location", location_type)
            )

            # Use central quest addition method
            self.game.quest_system.add_quest(quest)

    def complete_location_unlock(self, location_type):
        """Handle the completion of a location unlock quest"""
        # Reveal the hidden locations of this type (this also records the type as unlocked)
        self.game.unlock_location_type(location_type)
        self.game.story.mark("unlock." + location_type)

        # Generate location-specific quests
        self.generate_location_quests(location_type)

        # Enable location-specific story events
        self.enable_location_story_events(location_type)

    def generate_location_quests(self, location_type):
        """Generate location-specific quests"""
        quest_templates = {
            "AsteroidBase": [
                {
                    "type": "mining",
                    "name": "Rich Mineral Deposits",
                    "description": "Extract valuable minerals",
                    "reward_multiplier": 1.5
                }
            ],
            "DeepSpaceOutpost": [
                {
                    "type": "combat",
                    "name": "Outpost Defense",
                    "description": "Protect the outpost from raiders",
                    "reward_multiplier": 1.4
                }
            ],
            "ResearchColony": [
                {
                    "type": "research",
                    "name": "Scientific Analysis",
                    "description": "Assist with research projects",
                    "reward_multiplier": 2.0
                }
            ]
        }

        if location_type in quest_templates:
            for template in quest_templates[location_type]:
                self.game.quest_system.add_quest(self.game.quest_system.generate_quest(
                    template["type"], template["reward_multiplier"]))

    def enable_location_story_events(self, location_type):
        """Enable story events specific to the location type"""
        if location_type in self.location_story_events:
            for event in self.location_story_events[location_type]:
                self.game.story_manager.enable_story_event(event)

class LocationCapabilities:
    """Centralized management of location type capabilities"""

    # Define capabilities for each location type
    CAPABILITIES = {
        "Planet": {
            "can_trade": ["tech", "agri", "salt", "fuel"],
            "can_build": [
                "stockmarket",
                "permaculture",
                "organic",
                "agrobot",
                "nanotech",
                "neuroengineering",
                "mining"
            ],
            "can_produce": ["tech", "agri"],
            "can_mine": ["salt", "fuel"],
            "has_cantina": True,
            "has_shop": True,
            "base_exogeology": 100,
            "research_multiplier": 1.0
        },
        "AsteroidBase": {
            "can_trade": ["salt", "fuel"],
            "can_build": ["mining", "stockmarket"],
            "can_produce": [],
            "can_mine": ["salt", "fuel"],
            "has_cantina": True,
            "has_shop": True,
            "base_exogeology": 150,  # Better at mining
            "research_multiplier": 0.8
        },
        "DeepSpaceOutpost": {
            "can_trade": ["tech", "agri"],
            "can_build": ["stockmarket", "nanotech"],
            "can_produce": ["tech"],
            "can_mine": [],
            "has_cantina": True,
            "has_shop": True,
            "base_exogeology": 0,
            "research_multiplier": 1.2
        },
        "ResearchColony": {
            "can_trade": ["tech"],
            "can_build": ["nanotech", "neuroengineering"],
            "can_produce": ["tech"],
            "can_mine": [],
            "has_cantina": False,
            "has_shop": True,
            "base_exogeology": 0,
            "research_multiplier": 2.0
        }
    }


class Planet(Location):
    def __init__(self, name, tech_level, agri_level, research_points, economy):
        super().__init__(name, "Planet", tech_level, agri_level, research_points, economy)

class AsteroidBase(Location):
    def __init__(self, name, tech_level, agri_level, research_points, economy):
        super().__init__(name, "AsteroidBase", tech_level, agri_level, research_points, economy)
        # the base mines its own ice and rock: there is always fuel and salt for sale
        if not self.market.get('fuel'):
            self.market['fuel'] = random.randint(110, 150)
        if not self.market.get('salt'):
            self.market['salt'] = random.randint(70, 110)

class DeepSpaceOutpost(Location):
    def __init__(self, name, tech_level, agri_level, research_points, economy):
        super().__init__(name, "DeepSpaceOutpost", tech_level, agri_level, research_points, economy)

class ResearchColony(Location):
    def __init__(self, name, tech_level, agri_level, research_points, economy):
        super().__init__(name, "ResearchColony", tech_level, agri_level, research_points, economy)


# The game's other modules, imported last so that the modules can refer to each other.
from .commands import LocationCommands  # noqa: E402
from .quests import Quest  # noqa: E402
