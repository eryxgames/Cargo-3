"""The Game: its state and the turn loop. Its screens, travel, market, fights and the rest live in
the mixins it inherits, one module each."""
import random
import time
from . import VERSION
from .screens import ScreensMixin
from .saves import SavingMixin
from .captain import CaptainMixin
from .travel import TravelMixin
from .market import MarketMixin
from .hansa import HansaMixin
from .encounters import EncountersMixin
from .events import EventsMixin
from .research import ResearchMixin
from .actions import ActionsMixin
from .port import PortMixin
from .ranks import RanksMixin
from .factions import FactionsMixin
from .needles import NeedlesMixin
from .modules import ModulesMixin
from .tactics import TacticsMixin
from .achievements import AchievementsMixin
from .sound import SoundMixin
from .looking import LookMixin


class Game(ScreensMixin, SavingMixin, CaptainMixin, TravelMixin,
           MarketMixin, HansaMixin, EncountersMixin, EventsMixin,
           ResearchMixin, ActionsMixin, PortMixin, RanksMixin,
           FactionsMixin, NeedlesMixin, ModulesMixin, TacticsMixin, AchievementsMixin, SoundMixin,
           LookMixin):
    # How often something happens between docks, by difficulty: an easy game has calmer lanes
    LANE_ACTIVITY = {0: 0.55, 1: 0.85, 2: 1.0}

    def __init__(self, difficulty=None, player_name=None, intro=True, origin=None, voyage=None):
        self.standing = {name: 0 for name in FACTIONS}     # with the Hansa, the Mandate, the Concord
        self.dawn_trust = 0                                 # the Binary Dawn's, hidden until it speaks
        self.front_berths = 0                               # front places owed at the middle's fare
        self.achievements = {}                              # earned: {id: turn} (game/achievements.py)
        self.term_width = self.get_terminal_width()
        self.term_height = self.get_terminal_height()
        asked = difficulty is None
        self.difficulty = self.choose_difficulty() if difficulty is None else difficulty
        self.voyage = voyage or (self.choose_voyage() if asked else "standard")
        self.locations = self.generate_initial_locations()  # Generate all locations
        self.current_location = random.choice([loc for loc in self.locations if isinstance(loc, Planet)])  # Start at a planet
        self.shop = Shop()  # Initialize the shop system
        self.ship = Ship()
        self.ship.game = self  # connect ship to game
        self.turn = 0
        self.known_locations = [self.current_location.name]
        self.event_log = []
        self.player_name = player_name or self.get_player_name()
        self.rank = "Explorer"
        self.reputation = 0
        self.story_manager = StoryManager(self)
        self.quest_system = QuestSystem(self)
        self.unlocked_location_types = {"Planet"}
        self.location_manager = LocationManager(self)
        self.secret_quest_available = False
        self.stellar_portal_available = False
        self.research = Research()
        self.action = Action()
        # Add new tracking attributes for story milestones
        self.trades_completed = 0
        self.combat_difficulty = 1.0
        self.pirate_frequency = 1.0
        self.event_risk = 1.0
        self.event_probability = 0.2
        self.crisis_active = False
        self.endgame_active = False
        self.enable_stellar_portal = False
        self.legendary_items_available = False
        self.final_crisis_events = False
        self.trade_bonus = 0
        self.repair_discount = 0
        self.combat_bonus = 0
        # Initialize character generators
        self.character_generators = {
            "human": SpecialCharacterGenerator(self),
            "synthetic": SyntheticCharacterGenerator(self),
            "alien": AlienCharacterGenerator(self)
        }
        # Add systems
        self.port_system = Port(self)
        self.contract_manager = ContractManager(self)
        self.resource_transport = ResourceTransportQuest(self)
        self.reputation_manager = PassengerReputationManager(self)
        self.synthetic_events = SyntheticEventManager(self)
        self.character_encounters = SpecialCharacterEncounters(self)
        self.discovered_locations = set()
        self.cooldowns = {}
        self.story_events = {}
        self.infestation_manager = InfestationManager(self)
        self.story = StoryRuntime(self)
        self.story.origin = origin

        # The captain's record: an identity that can travel between the games,
        # and the records of captains who crossed over into this one
        self.captain_id = "C1-%08X" % random.getrandbits(32)
        self.captain_log = []
        self.visiting_captains = []
        self.ending_reached = None

        # Initialize the story
        if intro:
            self.story.introduce()
            self.story_manager.start_game()
            self.display_starting_info()
        else:
            self.story_manager.current_chapter = "ch1"

    # ------------------------------------------------------------------
    # The story's view of the game
    # ------------------------------------------------------------------
    def story_snapshot(self):
        """This moment of play, as the story's conditions see it (storykit State)."""
        ship = self.ship
        sm = self.story_manager
        stats = {
            "money": int(ship.money),
            "plot_points": sm.plot_points,
            "research_points": ship.research_points,
            "trades_completed": self.trades_completed,
            "trade_profit": int(sum(ship.trade_profits.values())),
            "passengers_transported": self.reputation_manager.total_passengers,
            "passenger_reputation": ship.passenger_reputation,
            "combat_rating": ship.attack + ship.defense + ship.speed,
            "combat_victories": ship.combat_victories.get("total", 0),
            "discovered": len(set(self.discovered_locations)),
            "mining_platforms": sum(len(loc.mining_platforms) for loc in self.locations),
            "controlled_locations": sum(1 for loc in self.locations if hasattr(loc, "controlled_by_player")),
            "milestones_done": len(sm.completed_story_beats),
            "turns_since_vip": self.turn - self.reputation_manager.last_vip_spawn,
            "best_cabin": max([m.comfort_level for m in getattr(ship, "passenger_modules", [])
                               if hasattr(m, "comfort_level")] or [0]),
            "crew_size": len(ship.crew),
            "hansa_bonds": getattr(self, "hansa_bonds", 0),
            "hull_class": ship.hull,
            "modules_fitted": len(ship.modules),
            "hold_free": ship.hold_room("tech"),
            "dues_arrears": getattr(self, "dues_arrears", 0),
            "dawn_trust": getattr(self, "dawn_trust", 0),
        }
        for good in ('tech', 'agri', 'salt', 'fuel'):
            stats["cargo." + good] = ship.cargo[good]
        for faction in FACTIONS:
            stats["standing." + faction] = self.standing_of(faction)
        for kind in STORY_VICTORY_TYPES[1:]:
            stats["combat_victories." + kind] = ship.combat_victories.get(kind, 0)
        for building in STORY_BUILDINGS:
            stats["buildings." + building] = sum(loc.buildings.count(building) for loc in self.locations)
        for place_type in STORY_PLACE_TYPES:
            stats["discovered." + place_type] = self.count_discovered(place_type)
        markets = [loc for loc in self.locations if loc.location_type in ("Planet", "AsteroidBase", "DeepSpaceOutpost")]
        stats["stockmarket_everywhere"] = int(bool(markets) and all(loc.stockmarket_base for loc in markets))
        done = set(sm.completed_chapters) | set(self.story.done)
        for cid, chapter in sm.chapters.items():
            for mid, milestone in chapter.milestones.items():
                if milestone.completed:
                    done.add("%s.%s" % (cid, mid))
        return {
            "turn": self.turn,
            "player": self.player_name,
            "act": sm.get_chapter_number(),
            "chapter": sm.current_chapter,
            "place": self.current_location.name,
            "place_type": self.current_location.location_type,
            "stats": stats,
            "sets": {
                "researched": sorted(self.research.unlocked_options),
                "items": sorted(k for k, v in ship.items.items() if isinstance(v, int) and v > 0),
                "unlocked_types": sorted(getattr(self, "unlocked_location_types", set())),
                "crew": sorted(ship.crew),
            },
            "flags": sorted(f for f, on in sm.story_states.items() if on),
            "done": sorted(done),
            "done_at": {n: t for n, t in self.story.done.items() if ":" not in n},
            "visitors": list(getattr(self, "visiting_captains", [])),
        }

    def reveal_place(self, name):
        """Put a place the story describes on the map (story effect 'reveal')."""
        if any(loc.name == name for loc in self.locations):
            return
        place = story_data()["places"].get(name) or {}
        made = place.get("made") or {}
        location = Location(name, place.get("type", "Planet"), made.get("tech", 10), made.get("agri", 1),
                            made.get("research", 50), made.get("economy", "Mysterious"))
        self.locations.append(location)
        if name not in self.known_locations:
            self.known_locations.append(name)
        self.display_story_message(["New location: %s" % name] +
                                   ([place["system"]] if place.get("system") else []), pause=1)

    def open_portal(self):
        """Through a Stellar Portal: a new set of places, somewhere else in time."""
        self.stellar_portal_available = True
        self.story_manager.story_states["stellar_portal"] = True
        new_locations = self.generate_new_locations()
        self.locations.extend(new_locations)
        self.current_location = random.choice(new_locations)
        self.known_locations = [self.current_location.name]
        self.display_story_message(self.story.text_of(
            "stellar_portal", fallback="You have traveled to a new set of locations."), pause=2)
        self.story.mark("stellar_portal")

    def bring_up_to_date(self):
        """A save from an older version: rename places, start missing systems."""
        def rename(location):
            if location is None:
                return
            location.name = RENAMED_PLACES.get(location.name, location.name)
            location.location_type = RENAMED_TYPES.get(location.location_type, location.location_type)
        for location in self.locations:
            rename(location)
        for group in getattr(self, "chapter_locations", {}).values():
            for locations in group.values():
                for location in locations:
                    rename(location)
        self.known_locations = [RENAMED_PLACES.get(n, n) for n in self.known_locations]
        self.discovered_locations = {RENAMED_PLACES.get(n, n) for n in self.discovered_locations}
        if not isinstance(getattr(self, "story", None), StoryRuntime):
            self.story = StoryRuntime(self)
        if not isinstance(getattr(self, "standing", None), dict):
            self.standing = {}
        for name in FACTIONS:
            self.standing.setdefault(name, 0)
        self.dawn_trust = getattr(self, "dawn_trust", 0)
        self.front_berths = getattr(self, "front_berths", 0)
        if not isinstance(getattr(self, "achievements", None), dict):
            self.achievements = {}
        if not isinstance(self.ship.__dict__.get("modules"), list):
            self.ship.__dict__["modules"] = []      # a save from before the ship had modules
        sm = getattr(self, "story_manager", None)
        if sm is not None and isinstance(getattr(sm, "chapters", None), dict):
            for cid, chapter in sm.initialize_chapters().items():      # chapters added since the save
                if cid not in sm.chapters:
                    sm.chapters[cid] = chapter
                else:
                    for nxt in chapter.next_chapters:
                        if nxt not in sm.chapters[cid].next_chapters:
                            sm.chapters[cid].next_chapters.append(nxt)
        for cid, chapter in getattr(sm, "chapters", {}).items():
            for milestone in chapter.milestones.values():
                milestone.chapter_id = cid          # the story file may state its condition
        self.story_manager.apply_story_text()

    def count_discovered(self, location_type=None):
        """How many discovered locations there are, optionally of one type."""
        names = set(self.discovered_locations)
        if location_type is None:
            return len(names)
        return sum(1 for loc in self.locations
                   if loc.name in names and loc.location_type == location_type)

    def generate_initial_locations(self):
        """Generate initial game locations and store hidden locations for later unlock"""
        # Starting planets - always available
        initial_locations = [
            Planet("Alpha", 5, 3, 10, "Stable"),
            Planet("Beta", 2, 7, 15, "Booming"),
            Planet("Gamma", 8, 2, 20, "Declining"),
            Planet("Delta", 4, 6, 25, "Formative"),
            Planet("Epsilon", 7, 4, 30, "Stable")
        ]

        # Hidden locations - unlocked through story progression
        self.hidden_locations = {
            "AsteroidBase": [
                AsteroidBase("Omega XIV", 6, 2, 15, "Stable"),
                AsteroidBase("Sigma VII", 7, 1, 20, "Declining"),
                AsteroidBase("Theta III", 5, 3, 25, "Booming")
            ],
            "DeepSpaceOutpost": [
                DeepSpaceOutpost("DSO-Alpha", 8, 3, 25, "Formative"),
                DeepSpaceOutpost("DSO-Beta", 9, 2, 30, "Booming"),
                DeepSpaceOutpost("DSO-Gamma", 7, 4, 35, "Stable")
            ],
            "ResearchColony": [
                ResearchColony("Nova Labs", 10, 4, 40, "Stable"),
                ResearchColony("Quantum Center", 9, 5, 35, "Booming"),
                ResearchColony("Stellar Institute", 8, 6, 45, "Formative")
            ]
        }

        # Add chapter-specific locations
        self.chapter_locations = {
            3: {  # Available in Chapter 3
                "AncientRuins": [
                    Location("Ancient Ruins Alpha", "Ancient Ruins", 12, 1, 50, "Mysterious"),
                    Location("Ancient Ruins Beta", "Ancient Ruins", 15, 1, 60, "Mysterious")
                ]
            },
            4: {  # Available in Chapter 4
                "AlienOutpost": [
                    Location("Alien Signal Research Outpost X", "Alien Signal Research Outpost", 20, 5, 100, "Unknown"),
                    Location("Alien Signal Research Outpost Y", "Alien Signal Research Outpost", 25, 5, 120, "Unknown")
                ]
            }
        }

        # Initialize unlocked locations tracking
        self.unlocked_location_types = {"Planet"}  # Start with only regular planets
        self.discovered_locations = set()  # Track which specific locations player has found

        return initial_locations


    def choose_difficulty(self):
        self.clear_screen()
        display_logo(logo_data, centered=False)
        difficulty_info = [
#            ["DIFFICULTY SELECTION"],
            [""],
            ["  1. EASY   (calm lanes)"],
            ["  2. NORMAL"],
            ["  3. EXPERT (busy lanes)"],
            ["     "]

        ]

        for line in difficulty_info:
            print(line[0])
            time.sleep(0.1)

        while True:
            self.display_simple_message("Select difficulty (1-3):", 0)
            choice = input(">>> ").strip()

            if choice in ['1', '2', '3']:
                difficulty_names = ['EASY', 'NORMAL', 'EXPERT']
                selected = difficulty_names[int(choice) - 1]
                self.display_simple_message(f"Setting difficulty: {selected}")
                return int(choice) - 1
            else:
                self.display_simple_message("Please select 1, 2, or 3.", 1)


    def choose_voyage(self):
        """Short, standard or long: how much each chapter asks before the story moves on."""
        self.display_simple_message([
            "Voyage length:", "",
            "1. Short haul: every chapter asks for less; a game of an evening or two",
            "2. Standard",
            "3. Long haul: chapters ask for half as much again; more time for everything",
            "", "Enter for standard."], 0)
        for _ in range(3):
            choice = input(">>> ").strip()
            if choice in ("1", "2", "3", ""):
                voyage = {"1": "short", "3": "long"}.get(choice, "standard")
                self.display_simple_message("Voyage: %s." % voyage)
                return voyage
            self.display_simple_message("Please select 1, 2 or 3.", 1)
        return "standard"

    def voyage_factor(self):
        return VOYAGES.get(getattr(self, "voyage", "standard"), 1.0)

    def unlock_advanced_equipment(self):
        """Unlock advanced equipment in shop"""
        # (these were bare prices, which crashed the shop the next time it was opened)
        new_equipment = {
            "neutron_shield": {"price": 40000, "description": "Neutron shield: +2 defense in fights",
                               "tech_required": 3, "plot_required": 0},
            "quantum_drive": {"price": 50000, "description": "Quantum drive: much better odds of outrunning anyone",
                              "tech_required": 3, "plot_required": 0},
            "warp_core": {"price": 75000, "description": "Warp core: +2 attack; the guns never run short of power",
                          "tech_required": 3, "plot_required": 0},
        }
        self.shop.base_equipment.update(new_equipment)


    def get_player_name(self):
        self.clear_screen()

        display_logo(logo_data, centered=False)

        self.display_simple_message([
            "Enter your pilot name",
            "Press Enter for random"
        ], 0)

        name = input(">>> ").strip()

        if not name:
            titles = ["Captain", "Commander", "Pilot", "Hauler", "Trucker", "Starfarer", "Operator", "Rigger","Freerunner","Navigator", "Doc", "Docker" ]
            surnames = ["Aen Stark", "Orr-Slagg", "Dragg Voxx", "Swigg", "Doc Brainac", "Json", "Nova", "Drake", "Phoenix", "Wolf", "Kayo Wu", "Lyra Nyx", "Elerra Solis", "Bryce", "Q'Ella", "Cael Yaro", "Q'Orin"]
            name = f"{random.choice(titles)} {random.choice(surnames)}"
            self.display_simple_message(f"Neural Signature Verified: {name}")

        self.display_simple_message(f"Welcome aboard, {name}!")
        return name


    def play_turn(self):
            self.new_turn()
            self.display_turn_info()
            self.check_location_unlocks()  # Check for new unlocks each turn
            self.check_milestone_triggers() # Check for StoryManager
            # New chapter and milestone system
            self.story_manager.check_milestone_progress()
            self.story_manager.check_chapter_progress()
            self.story.tick()           # the story's scenes (story/cargo1/*.json)
            self.quest_system.check_active_quests()
            # Get location commands
            location_commands = self.current_location.commands


            self.infestation_manager.check_global_infestations()
            if hasattr(self.ship, 'active_infestations'):
                self.infestation_manager.update_ship_infestations()

            # Update synthetic events (if they exist)
            if hasattr(self, 'synthetic_events'):
                self.synthetic_events.update()

            # For each location, check building counts
            for location in self.locations:
                neuroguild_count = location.buildings.count("Neuroengineering Guild")
                agrobot_count = location.buildings.count("Agrobot Assembly Line")

                if neuroguild_count >= 4 and random.random() < 0.2:  # 20% chance per turn
                    self.synthetic_events.start_uprising("Neurodroid", location)
                if agrobot_count >= 4 and random.random() < 0.2:
                    self.synthetic_events.start_uprising("Agrobot", location)

            # Update port system if port command is available
            port_is_available = False
            for cmd, shortcut in location_commands["available"]:
                if cmd == 'port' or shortcut == 'p':
                    port_is_available = True
                    self.port_system.update_passengers(self.current_location.name)

            # Create list of valid actions
            valid_actions = []
            for cmd, shortcut in location_commands["available"]:
                valid_actions.extend([cmd, shortcut])

            # Add global commands
            for cmd, shortcut in GLOBAL_COMMANDS:
                valid_actions.extend([cmd, shortcut])

            action = self.validate_input("Choose action: ", valid_actions)

            # Handle cancelled command
            if action is None:
                return

            elif action in ['save', 'sv']:
                self.handle_save()
                return

            elif action in ['load', 'ld']:
                self.handle_load()
                return

            elif action in ['captain', 'cap']:
                self.handle_captain_menu()
                return

            # Handle research/repair based on location type ('r' is research at a colony)
            elif action in ['research', 'r', 'repair']:
                if action != 'repair' and isinstance(self.current_location, ResearchColony):
                    self.handle_research_options()
                else:
                    if self.ship.damage > 0:
                        cost = int(self.ship.damage * self.ship.repair_rate())
                        if self.ship.repair(cost):
                            self.display_simple_message("Ship repaired.")
                        else:
                            self.display_simple_message(
                                f"Not enough money to repair. Cost: {self.format_money(cost)}"
                            )
                    else:
                        self.display_simple_message("Ship doesn't need repairs.")

            elif action in ['buy', 'b']:
                item = commodity_from(self.validate_input(
                    "Buy which? tech/t, agri/a, salt/s, fuel/f: ",
                    [w for name, cuts in COMMODITIES.items() for w in (name,) + cuts]))
                if item is None:
                    return

                if not self.current_location.can_trade(item):
                    self.display_simple_message(f"Trading of {item} is banned on this planet!")
                    return

                if item in ['salt', 'fuel']:
                    has_platform = self.current_location.trades_bulk(item)
                    if not has_platform:
                        self.display_simple_message(f"No mining platform for {item} on this planet.")
                        return

                quantity = self.validate_quantity_input("Enter quantity (max/m, half/h): ")
                if quantity is None:
                    return

                price = self.current_location.market[item]
                if price <= 0:
                    self.display_simple_message(f"Cannot calculate amount: {item} has no valid price.")
                    return

                tax_rate = self.ship.trade_tax(self.current_location.calculate_tax_rate(self.rank, price))
                room = self.ship.hold_room(item)
                max_quantity = self.affordable(item, tax_rate, room)

                if quantity == 'max':
                    quantity = max_quantity
                elif quantity == 'half':
                    quantity = (max_quantity + 1) // 2  # Round up division
                elif quantity > room:
                    self.display_simple_message(f"The hold has room for {room} more {item}.")
                    quantity = room

                if quantity <= 0:
                    self.display_simple_message("The hold is full." if room <= 0 else
                                                f"Not enough money for one unit of {item}.")
                elif self.ship.buy(item, quantity, self.current_location.market[item],
                                   self.current_location, self.rank):
                    self.display_simple_message(
                        f"Bought {self.format_money(quantity)} {item}. The price here is now "
                        f"{self.format_money(self.current_location.market[item])}.")
                    self.handle_trade('buy')
                else:
                    self.display_simple_message(f"Not enough money for {quantity} {item}.")

            elif action in ['sell', 's']:
                item = commodity_from(self.validate_input(
                    "Sell which? tech/t, agri/a, salt/s, fuel/f: ",
                    [w for name, cuts in COMMODITIES.items() for w in (name,) + cuts]))
                if item is None:
                    return

                if not self.current_location.can_trade(item):
                    self.display_simple_message(f"Trading of {item} is banned on this planet!")
                    return

                quantity = self.validate_quantity_input("Enter quantity to sell (max/m, half/h): ")
                if quantity is None:
                    return

                if quantity == 'max':
                    quantity = self.ship.cargo[item]
                if quantity == 'half':
                    quantity = (self.ship.cargo[item]) // 2

                profit_before = sum(self.ship.trade_profits.values())
                if self.ship.sell(item, quantity, self.current_location.market[item],
                                self.current_location, self.rank):
                    profit = sum(self.ship.trade_profits.values()) - profit_before
                    note = ""
                    # a good deal is worth telling at the bar: a plot point, once a turn
                    if profit >= 5000 and getattr(self, "good_deal_turn", None) != self.turn:
                        self.good_deal_turn = self.turn
                        self.story_manager.plot_points += 1
                        note = " A good deal: +1 plot point."
                    self.display_simple_message(f"Sold {self.format_money(quantity)} {item}, "
                                                f"profit {self.format_money(int(profit))}. The price here is now "
                                                f"{self.format_money(self.current_location.market[item])}.{note}")
                    self.handle_trade('sell')

            elif action in ['upgrade', 'u']:
                property_name = self.validate_input(
                    "Choose property to upgrade (attack/defense/speed/hull/modules): ",
                    ['attack', 'defense', 'speed', 'hull', 'modules', 'mod']
                )
                if property_name is None:
                    return
                if property_name == 'hull':
                    self.handle_hull_overhaul()
                    return
                if property_name in ('modules', 'mod'):
                    self.handle_yard()
                    return

                cost = self.ship.upgrade_costs[property_name]
                if self.ship.upgrade(property_name, cost):
                    self.display_simple_message(f"Upgraded {property_name}.")
                    self.ship.upgrade_costs[property_name] = int(cost * 1.5)

            elif action in ['travel', 't']:
                self.handle_travel()

            elif action in ['info', 'i']:
                self.display_location_info()

            elif action in ['build', 'bl']:
                building_costs = {
                    'stockmarket': 5000,
                    'permaculture': 3000,
                    'organic': 4000,
                    'agrobot': 5000,
                    'nanotech': 6000,
                    'neuroengineering': 7000,
                    'mining': 10000,
                    'salt_refinery': 15000,
                    'fuel_refinery': 15000,
                    'combined_refinery': 25000
                }

                valid_options = [
                    'stockmarket', 'sm',
                    'permaculture', 'pc',
                    'organic', 'oc',
                    'agrobot', 'ab',
                    'nanotech', 'nt',
                    'neuroengineering', 'ne',
                    'mining', 'm',
                    'salt refinery', 'sr',
                    'fuel refinery', 'fr',
                    'combined refinery', 'cr'
                ]

                building_name = self.validate_input(
                    "Choose building type: ",
                    valid_options
                )

                if building_name is None:
                    return

                self.handle_building_construction(building_name, building_costs)

            elif action in ['cantina', 'c']:
                self.visit_cantina()

            elif action in ['shop', 'sh']:
                self.visit_shop()

            elif action in ['action', 'a']:
                self.handle_actions()

            elif action in ['mine', 'm']:
                self.handle_mining()

            elif action in ['port', 'p']:
                if port_is_available:
                    self.port_system.handle_port_menu()
                    self.port_system.update_passenger_satisfaction()
                else:
                    self.display_simple_message("No port available at this location.")

            elif action in ['log', 'l']:
                self.story_manager.display_story_progress()
                return    # Return after showing log to avoid counting it as a turn

            elif action in ['journal', 'j']:
                self.story.journal()
                return

            elif action in ['hansa', 'ha']:
                self.handle_hansa()
                return

            elif action in ['help', 'h']:
                self.show_help()
                return

            elif action in ['style', 'st']:
                self.choose_style()
            elif action in ['sound', 'so']:
                self.handle_sound()
            elif action in ['look', 'lk']:
                self.handle_look()
            elif action in ['think', 'th']:
                self.handle_think()
                return

            elif action in ['version', 'v']:
                display_logo(logo_data, centered=True)
                print_centered_text("")
                print_centered_text("Created by Dan Sandner")
                print_centered_text(f"v{VERSION}, ©2025-2026")

                time.sleep(3)
                return

            # Handle quit and resign commands
            elif action in ['quit', 'q']:
                if self.validate_input("Are you sure you want to quit? (yes/no): ", ['yes', 'no']) == 'yes':
                    self.display_simple_message("Thanks for playing!")
                    exit()
                return

            elif action in ['resign', 'rs']:
                if self.validate_input("Are you sure you want to resign? (yes/no): ", ['yes', 'no']) == 'yes':
                    self.display_score()
                    exit()
                return

            elif action in ['hunt', 'hu']:
                if self.handle_hunt():
                    # the hunt took the day: the turn ends without another event
                    if port_is_available:
                        self.port_system.update_passenger_satisfaction()
                    self.turn += 1
                    self.shop.reset_turn()
                    self.autosave()
                return

            elif action in ['end', 'e']:
                # Update passenger satisfaction at end of turn if port is available
                if port_is_available:
                    self.port_system.update_passenger_satisfaction()
                self.turn += 1
                self.random_event()
                self.shop.reset_turn()  # Reset shop state at end of each turn
                self.autosave()
                return

            else:
                self.display_simple_message("Invalid action.")
        # Implement trade tip functionality here

    def unlock_location_type(self, location_type):
        """Unlock a new type of location and add its instances to available locations"""
        if location_type not in self.unlocked_location_types:
            self.unlocked_location_types.add(location_type)

            # Add locations from hidden pool
            if location_type in self.hidden_locations:
                self.locations.extend(self.hidden_locations[location_type])

                # Display unlock message
                self.display_story_message([
                    f"New {location_type}s Discovered!",
                    "Check your map for new locations to explore.",
                    "",
                    "New trading opportunities await!"
                ])

                # Add specific location effects
                if location_type == "AsteroidBase":
                    self.display_simple_message("Asteroid Bases offer improved mining efficiency!")
                elif location_type == "DeepSpaceOutpost":
                    self.display_simple_message("Deep Space Outposts have unique equipment available!")
                elif location_type == "ResearchColony":
                    self.display_simple_message("Research Colonies provide bonus research points!")

            # Also check chapter-specific locations
            if hasattr(self, 'chapter_locations'):
                for chapter in self.chapter_locations.values():
                    if location_type in chapter:
                        self.locations.extend(chapter[location_type])

    def update_location_status(self, event_type, outcome, details):
        """Update location based on event outcomes with specific details"""
        location = self.current_location

        if event_type == "combat" and outcome == "victory":
            # Use combat details to adjust security
            damage_taken = details.get('damage_taken', 0)
            security_increase = 1 if damage_taken < 20 else 0
            location.security_level = min(10, location.security_level + security_increase)

            # Check equipment unlocks based on combat performance
            if isinstance(location, DeepSpaceOutpost) and damage_taken < 10:
                self.unlock_advanced_equipment()

        elif event_type == "disaster":
            # Use disaster details to affect economy
            damage_amount = details.get('damage_taken', 0)
            cargo_lost = details.get('cargo_lost', {})

            if damage_amount > 30 or sum(cargo_lost.values()) > 100:
                location.economy = "Declining"
                self.display_simple_message(f"Major disaster has affected {location.name}'s economy!")

    def new_turn(self):
        """Things that happen once a turn, whatever the captain does: markets recover, prices
        here are noted. (The Hansa's fares are paid per jump, at the needle office.)"""
        if getattr(self, "ticked_turn", None) == self.turn:
            return
        first = getattr(self, "ticked_turn", None) is None
        self.ticked_turn = self.turn
        if not first:
            for loc in self.locations:
                loc.recover()
            self.mend_on_the_way()
            self.check_achievements()
        self.play_music()
        self.note_prices()

    def story_flag(self, *flags):
        states = self.story_manager.story_states
        return any(states.get(flag) for flag in flags)


    def check_milestone_triggers(self):
        """Check for milestone triggers each turn"""
        # First trade
        if self.trades_completed == 2:
            self.story_manager.complete_milestone("first_trade")

        # First combat
        if self.ship.combat_victories['total'] == 1:
            self.story_manager.complete_milestone("first_combat")

        # Basic license (after 5 successful trades)
        if self.trades_completed >= 5 and "basic_license" not in self.story_manager.completed_story_beats:
            self.story_manager.complete_milestone("basic_license")

        # Pirates and route security
        if self.ship.combat_victories.get('pirate', 0) >= 5:
            self.story_manager.complete_milestone("defeat_pirates")
            if self.trades_completed >= 20:
                self.story_manager.complete_milestone("secure_route")

        # Mining milestones
        if any(loc.mining_platforms for loc in self.locations):
            self.story_manager.complete_milestone("first_mining")
            miners_defended = self.ship.combat_victories['total'] >= 10
            if miners_defended:
                self.story_manager.complete_milestone("defend_miners")

        # Research milestones
        if any(isinstance(loc, ResearchColony) for loc in self.locations):
            self.story_manager.complete_milestone("research_hub")
        if len(self.research.unlocked_options) >= 3:
            self.story_manager.complete_milestone("tech_breakthrough")

    def play(self):
        while True:
            # Play a turn
            turn_result = self.play_turn()

            # Check if player quit or resigned
            if turn_result == "quit":
                self.display_simple_message("Thanks for playing!")
                break
            elif turn_result == "resign":
                self.display_simple_message("Resigning from current game...")
                self.display_score()
                break

            self.update_rank()

            # Check game over conditions
            if self.ship.money <= 0 and self.ship.is_empty_cargo():
                self.display_simple_message("Game Over: No money and no cargo left.", 2)
                self.display_score()
                break

            if self.ship.damage >= 100:
                self.display_simple_message("Game Over: Ship destroyed!", 2)
                self.display_score()
                break

            # Check for special quest availability
            # Only check planets and locations that can have stockmarkets
            valid_locations = [loc for loc in self.locations
                            if isinstance(loc, Planet) or
                            loc.location_type in ["Planet", "AsteroidBase", "DeepSpaceOutpost"]]

            if valid_locations and all(loc.stockmarket_base for loc in valid_locations) \
                    and not self.stellar_portal_available \
                    and self.turn - getattr(self, "tycoon_offered", -100) >= 10:
                # every market is yours: retire, go through the portal, or keep trading
                self.tycoon_offered = self.turn
                self.secret_quest_available = True
                self.story.mark("tycoon_offer")
                self.display_story_message(self.story.text_of("tycoon_offer", fallback=(
                    "Retire as Galactic Tycoon, or pay 1,500 credits and continue into the unknown.")) + [
                    "", "1. Keep trading here (asked again in 10 turns)",
                    "2. Retire as Galactic Tycoon (the game ends)",
                    "3. Pay 1,500 and fly through the portal (no way back)"], pause=0)
                answer = self.validate_input("Your response (1-3): ", ['1', '2', '3'])
                if answer == '2':
                    self.story.mark("ending_tycoon")
                    self.display_story_message(self.story.text_of("ending_tycoon", fallback=(
                        "You are the Galactic Tycoon!")))
                    self.display_score()
                    self.story.epilogue()
                    self.close_record("tycoon")
                    break
                elif answer == '3':
                    if self.ship.money >= 1500:
                        self.ship.money -= 1500
                        self.open_portal()
                    else:
                        self.display_simple_message("Not enough money for the coordinate.")

            # Ask to play again
            if turn_result == "quit":
                play_again = self.validate_input("Do you want to play again? (yes/no): ", ['yes', 'no'])
                if play_again == 'yes':
                    raise SwitchGame(Game())
                break

    def generate_new_locations(self):
        """Generate new locations for the late-game content"""
        new_locations = [
            Planet("Zeta", 10, 1, 5, "Stable"),
            Planet("Eta", 1, 10, 5, "Booming"),
            Planet("Theta", 8, 8, 10, "Declining"),
            AsteroidBase("Omega-1", 5, 5, 15, "Formative"),
            DeepSpaceOutpost("DSO-Delta", 7, 3, 20, "Stable")
        ]

        # Add some special bonuses for late-game locations
        for location in new_locations:
            location.exogeology += 20  # Better mining in new locations
            location.research_points *= 2     # Double research points
            location.tech_level += 2         # Higher tech levels

            # Special location-type bonuses
            if isinstance(location, AsteroidBase):
                location.exogeology += 10  # Extra mining bonus
            elif isinstance(location, DeepSpaceOutpost):
                location.market['tech'] = max(1, location.market['tech'] * 0.8)  # Better tech prices

        return new_locations

#New additions to the game system


    def handle_location_discovery(self, location):
        """Handle discovery of a new location"""
        if location.name not in self.discovered_locations:
            self.discovered_locations.add(location.name)

            # Award discovery rewards
            discovery_reward = 1000 * (self.story_manager.get_chapter_number() + 1)
            research_reward = 20 * (self.story_manager.get_chapter_number() + 1)

            self.ship.money += discovery_reward
            self.ship.research_points += research_reward

            # Check for story progression
            self.story_manager.check_discovery_milestone(location)

            # Check for quest updates
            self.quest_system.update_discovery_quests(location)

            self.display_story_message([
                f"Discovered new location: {location.name}!",
                f"Earned {self.format_money(discovery_reward)} credits",
                f"Gained {research_reward} research points"
            ])

    def check_location_unlocks(self):
        """Check for new location type unlocks"""
        for location_type in self.location_manager.location_quests:
            if (location_type not in self.unlocked_location_types and
                self.location_manager.check_location_unlock_progress(location_type)):
                self.location_manager.trigger_location_unlock_quest(location_type)


# Every name of the game's modules, for the tools, which load game/world.py and reach the
# whole game through it.
from .terminal import (  # noqa: E402,F401
    MIN_COLUMNS, NARROW_COLUMNS, RULE, _ANSI_RE, box_inner_width,
    display_logo, flow_cells, is_narrow, logo_data, pad_to, plain_terminal, short_logo,
    print_centered_text, render_box, safe_output, say, terminal_columns, visible_len,
    wrap_text)
from .saves import (  # noqa: E402,F401
    AUTOSAVE_SLOT, GAME_ID, RENAMED_PLACES, RENAMED_TYPES, RETIRED_CLASSES, SAVE_FORMAT,
    SaveError, SwitchGame, _ADOPTED, _is_code, adopt_old_files, captain_folder,
    cargo_home, decode_world, describe_save, encode_world, game_classes, list_saves,
    load_game, safe_name, save_folder, write_json)
from .captain import (  # noqa: E402,F401
    CAPTAIN_CODE_PREFIX, CAPTAIN_FORMAT, CAPTAIN_GAMES, STORY_BUILDINGS, STORY_PLACE_TYPES, STORY_VICTORY_TYPES,
    _captain_check, _clean_number, _clean_text, captain_from_code, captain_to_code, clean_captain,
    list_captain_files, read_captain_file)
from .story import (  # noqa: E402,F401
    ENDING_TITLES, GAME_ENDING_TITLES, GAME_TITLES, ending_title, STORY_FILE, STORY_HOOKS, STORY_MOMENTS, StoryRuntime,
    VOYAGES, VOYAGE_STATS, _PLACEHOLDER, _as_list, _open_portal,
    _repair_at_cost, play_cue, record_matches, story_data, story_hook,
    story_links, voyage_condition, voyage_value)
from .chapters import (  # noqa: E402,F401
    MilestoneRequirements, StoryChapter, StoryManager, StoryMilestone, chapter_requirements_met)
from .research import (  # noqa: E402,F401
    Research)
from .actions import (  # noqa: E402,F401
    Action)
from .ship import (  # noqa: E402,F401
    Ship)
from .commands import (  # noqa: E402,F401
    COMMODITIES, GLOBAL_COMMANDS, LocationCommands, commodity_from)
from .encounters import (  # noqa: E402,F401
    ENEMIES, FIGHT_TRICKS, SITUATIONS, odds_word)
from .events import (  # noqa: E402,F401
    InfestationManager, SyntheticEventManager, UprisingEffect)
from .contracts import (  # noqa: E402,F401
    Contract, ContractManager)
from .quests import (  # noqa: E402,F401
    Quest, QuestSystem, ResourceTransportQuest, run_quest_callback)
from .people import (  # noqa: E402,F401
    AlienCharacterGenerator, SpecialCharacter, SpecialCharacterEncounters, SpecialCharacterGenerator, SyntheticCharacterGenerator)
from .passengers import (  # noqa: E402,F401
    Passenger, PassengerModule, PassengerReputationManager)
from .port import (  # noqa: E402,F401
    Port, Shop)
from .places import (  # noqa: E402,F401
    AsteroidBase, DeepSpaceOutpost, Location, LocationCapabilities, LocationManager, Planet,
    ResearchColony)
from .factions import (  # noqa: E402,F401
    FACTIONS, HIGH, LOW, WORDS, standing_word)
from .needles import (  # noqa: E402,F401
    ACCOUNT_LIMIT, FUEL_PRICE, HOP_FUEL, POSITIONS, system_of)
from .modules import (  # noqa: E402,F401
    CONTAINER_UNITS, FULL, MODULES, SCANNER_RISK, condition_word, mend_cost, module_name)
from .tactics import MARKS, TACTICAL_FROM  # noqa: E402,F401
from .sound import CUES, MUSIC_FILE, audio, music_table, sfx  # noqa: E402,F401
from .looking import DECOY_WAVE, EQUIPMENT, EQUIPMENT_FARE  # noqa: E402,F401
from .achievements import ACHIEVEMENTS  # noqa: E402,F401
from .research import BRANCHES  # noqa: E402,F401
from .start import (  # noqa: E402,F401
    choose_captain, choose_saved_game, main, new_game, start_game)
