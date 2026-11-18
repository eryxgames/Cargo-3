"""The ship: hold, money, crew, items, hull and damage."""

# Define the Ship class
class Ship:
    # Passenger reputation runs from 0 to 100 (it multiplies fares and VIP rewards)
    passenger_reputation = property(
        lambda self: self.__dict__.get("passenger_reputation", 0),
        lambda self, value: self.__dict__.__setitem__("passenger_reputation", max(0, min(100, value))))

    def __init__(self, game=None):
        self.game = game
        # Basic cargo and resources
        self.cargo = {
            'tech': 0,
            'agri': 0,
            'salt': 0,
            'fuel': 0
        }
        self.special_cargo = {}     # what the story puts aboard: {name: units of hold}
        self.special_labels = {}    # and what to call it: {name: words}
        self.money = 1000
        self.damage = 0
        self.research_points = 0

        # Ship stats
        self.attack = 1
        self.defense = 1
        self.speed = 1

        # Equipment and upgrades
        self.upgrades = []
        self.items = {}

        # Upgrade costs
        self.upgrade_costs = {
            'attack': 2000,
            'defense': 2000,
            'speed': 2000
        }

        # Item tracking
        self.item_purchase_count = {}

        # Combat statistics
        self.combat_victories = {
            'total': 0,
            'pirate': 0,
            'raider': 0,
            'militia': 0,
            'alien': 0
        }
        self.combat_defeats = {
            'total': 0,
            'pirate': 0,
            'raider': 0,
            'militia': 0,
            'alien': 0
        }
        self.combat_stats = {
            'pirates_defeated': 0,
            'raiders_defeated': 0,
            'militia_defeated': 0,
            'defeats_by_type': {}
        }

        # Trade statistics
        self.trade_profits = {}

        # Enemy-specific victories
        self.enemy_victories = {
            'pirate': 0,
            'raider': 0,
            'militia': 0,
            'alien': 0
        }

                # Initialize passenger-related attributes
        self.passenger_modules = []
        self.passenger_reputation = 0

    def record_combat_victory(self, enemy_type=None):
        """Record a combat victory with proper type tracking"""
        self.combat_victories['total'] += 1
        if enemy_type:
            self.combat_victories[enemy_type] = self.combat_victories.get(enemy_type, 0) + 1

    def record_combat_defeat(self, enemy_type=None):
        """Record a combat defeat with proper type tracking"""
        self.combat_defeats['total'] += 1
        if enemy_type:
            self.combat_defeats[enemy_type] = self.combat_defeats.get(enemy_type, 0) + 1

    # The hold: room for HOLD_BASE units of goods, more with equipment from the shop.
    # Salt and fuel can also use the special containers.
    HOLD_BASE = 400
    HOLD_BONUS = {"cargo_extender": 0.2, "quantum_compressor": 0.5, "containment_optimizer": 0.25}
    SPECIAL_HOLD_BONUS = {"containment_field": 0.3, "stasis_vault": 0.75, "mining_compressor": 0.4,
                          "cargo_scanner": 0.2}

    def hold_sizes(self):
        """(general, special): units for any goods, and extra units for salt and fuel."""
        base = self.HOLD_BASE
        general = base * (1 + sum(b for item, b in self.HOLD_BONUS.items() if self.items.get(item))
                          + (0.1 if "loader" in self.crew else 0) + self.hull_info()["hold"]) \
            + (CONTAINER_UNITS + (50 if self.researched("bulk_logistics") else 0)) * self.working("container")
        special = base * sum(b for item, b in self.SPECIAL_HOLD_BONUS.items() if self.items.get(item))
        return int(general), int(special)

    # Hulls: the ship the captain started with, and two overhauls from a planet's shipyard.
    # A better hull fights and carries better, rides out rough and deep lanes, and costs
    # far more to repair.
    HULLS = [
        {"name": "Old hauler", "price": 0, "attack": 0, "defense": 0, "hold": 0.0, "repair": 10,
         "about": "the ship the loan bought: honest, slow, patched"},
        {"name": "Ironback", "price": 60000, "attack": 0, "defense": 1, "hold": 0.2, "repair": 50,
         "about": "a reinforced long-hauler hull: thicker plating, a bigger hold; Hansa-rated for the outposts, "
                  "the ruins and the listening posts"},
        {"name": "Farstrider", "price": 220000, "attack": 1, "defense": 2, "hold": 0.4, "repair": 120,
         "about": "a deep-range hull for the far edge of our own system and the systems past the portal; "
                  "heavy, roomy, and every dent costs a fortune"},
    ]
    hull = property(lambda self: self.__dict__.get("hull", 0),
                    lambda self, value: self.__dict__.__setitem__("hull", value))

    def hull_info(self):
        return self.HULLS[min(self.hull, len(self.HULLS) - 1)]

    # Modules on the spine's grips (game/modules.py): [{"kind": "container", "condition": 100}, ...]
    modules = property(lambda self: self.__dict__.setdefault("modules", []))

    def grips(self):
        """How many modules the hull's spine carries."""
        return GRIPS[min(self.hull, len(GRIPS) - 1)]

    def researched(self, option):
        """Whether the captain has researched this (the Game's research, when the ship has a game)."""
        research = getattr(getattr(self, "game", None), "research", None)
        return option in getattr(research, "unlocked_options", ())

    def working(self, kind):
        """How many modules of this kind are fitted and not broken."""
        return sum(1 for m in self.modules if m["kind"] == kind and m["condition"] > 0)

    def repair_rate(self):
        """Credits per point of damage: the hull's rate, less with a mechanic or a repair bay aboard."""
        return self.hull_info()["repair"] * (0.7 if "mechanic" in self.crew else 1.0) \
            * (0.7 if self.working("repair") else 1.0)

    # Fighting equipment: (attack bonus, defense bonus)
    FIGHT_GEAR = {"combat_drone": (1, 0), "shield_booster": (0, 1), "mining_laser": (0, 1),
                  "neutron_shield": (0, 2), "warp_core": (2, 0)}

    # The crew: helpers hired in cantinas (names in the story file, story/cargo1/crew.json)
    crew = property(lambda self: self.__dict__.setdefault("crew", []))
    CREW_BUNKS = 4

    def fight_attack(self):
        return self.attack + sum(g[0] for item, g in self.FIGHT_GEAR.items() if self.items.get(item)) \
            + (1 if "gunner" in self.crew else 0) + self.hull_info()["attack"] \
            + self.working("turret") + self.working("hangar") * (2 if self.researched("drone_autonomy") else 1)

    def fight_defense(self):
        return max(1, self.defense + sum(g[1] for item, g in self.FIGHT_GEAR.items() if self.items.get(item))
                   + self.hull_info()["defense"] + self.working("shield"))

    def trade_tax(self, rate):
        """The tax rate after the ship's loading gear and broker (never below 1%)."""
        if self.items.get("auto_loader"):
            rate -= 0.02
        if "broker" in self.crew:
            rate -= 0.02
        if self.working("offloader"):
            rate -= 0.02
        return max(0.01, rate)

    def research_bonus(self):
        """Extra share of research points from travel and discoveries."""
        return (0.2 if self.items.get("research_module") else 0) + (0.1 if self.items.get("data_analyzer") else 0) \
            + (0.1 if self.working("scanner") else 0)

    def stowed(self):
        """Units of hold taken by special cargo the story put aboard (a hovertank, sealed crates)."""
        return sum(getattr(self, "special_cargo", {}).values())

    def hold_room(self, item):
        """How many more units of `item` fit in the hold."""
        general, special = self.hold_sizes()
        general -= self.stowed()
        dry = self.cargo['tech'] + self.cargo['agri']
        bulk = self.cargo['salt'] + self.cargo['fuel']
        if item in ('salt', 'fuel'):
            return max(0, general + special - dry - bulk)
        return max(0, general - dry - max(0, bulk - special))

    def hold_text(self):
        general, special = self.hold_sizes()
        return "%d/%d" % (sum(self.cargo.values()) + self.stowed(), general + special)

    def buy(self, item, quantity, price, planet, player_rank):
        if not planet.can_trade(item):
            return False
        if quantity <= 0 or quantity > self.hold_room(item):
            return False

        if item in ['salt', 'fuel']:
            has_platform = planet.trades_bulk(item)
            if not has_platform:
                return False

        price = planet.trade_price(item, quantity, selling=False)
        cost = quantity * price
        if self.money >= cost:
            tax_rate = self.trade_tax(planet.calculate_tax_rate(player_rank, cost))
            tax_amount = cost * tax_rate
            total_cost = cost + tax_amount

            if self.money >= total_cost:
                self.money -= total_cost
                self.cargo[item] += quantity
                # what the goods in the hold cost, so a sale can tell profit from revenue
                basis = self.__dict__.setdefault("cost_basis", {})
                if self.cargo[item] == quantity:          # the hold was empty: start afresh
                    basis[item] = 0
                basis[item] = basis.get(item, 0) + total_cost
                planet.trade_impact(item, quantity, selling=False)

                # Add contract progress tracking for buy events
                if hasattr(self, 'game') and hasattr(self.game, 'contract_manager'):
                    event_data = {
                        "action": "buy",
                        "commodity": item,
                        "amount": quantity,
                        "location": planet.name,
                        "turn": self.game.turn
                    }
                    self.game.contract_manager.update_contract_progress(event_data)

                return True
            return False
        return False

    def sell(self, item, quantity, price, planet, player_rank):
        if not planet.can_trade(item):
            return False

        if item in ['salt', 'fuel']:
            has_platform = planet.trades_bulk(item)
            if not has_platform:
                return False

        if self.cargo[item] >= quantity:
            price = planet.trade_price(item, quantity, selling=True)
            revenue = quantity * price
            tax_rate = self.trade_tax(planet.calculate_tax_rate(player_rank, revenue))
            tax_amount = revenue * tax_rate
            net_revenue = revenue - tax_amount

            # Profit is what the sale brought in minus what those goods cost.
            # Goods that cost nothing (mined, found, given) are all profit.
            basis = self.__dict__.setdefault("cost_basis", {})
            held = self.cargo[item]
            cost_of_sold = basis.get(item, 0) * quantity / held if held else 0
            basis[item] = max(0, basis.get(item, 0) - cost_of_sold) if held > quantity else 0

            self.money += net_revenue
            self.cargo[item] -= quantity
            planet.trade_impact(item, quantity, selling=True)

            # Track trade profits
            if item not in self.trade_profits:
                self.trade_profits[item] = 0
            self.trade_profits[item] += net_revenue - cost_of_sold

            # Add contract progress tracking for sell events
            if hasattr(self, 'game') and hasattr(self.game, 'contract_manager'):
                event_data = {
                    "action": "sell",
                    "commodity": item,
                    "amount": quantity,
                    "location": planet.name,
                    "turn": self.game.turn
                }
                self.game.contract_manager.update_contract_progress(event_data)

            return True
        return False

    def repair(self, cost):
        if self.money >= cost:
            self.money -= cost
            self.damage = 0
            return True
        return False

    def upgrade(self, property_name, cost):
        if self.money >= cost:
            self.money -= cost
            if property_name == 'attack':
                self.attack += 1
            elif property_name == 'defense':
                self.defense += 1
            elif property_name == 'speed':
                self.speed += 1
            return True
        return False

    def acquire_item(self, item_name):
        if item_name in self.items:
            self.items[item_name] += 1
        else:
            self.items[item_name] = 1

    def is_empty_cargo(self):
        return all(amount == 0 for amount in self.cargo.values())

    def upgrade_property(self, property_name, amount):
        if property_name == 'attack':
            self.attack += amount
        elif property_name == 'defense':
            self.defense += amount
        elif property_name == 'speed':
            self.speed += amount


from .modules import CONTAINER_UNITS, GRIPS  # noqa: E402  (modules.py imports nothing from here)
