"""The captain as a person, apart from any ship: money, things carried, skills, wounds, the gear
for a fight on foot, a locker of private trade and the berth they work on another captain's ship.

In Cargo 1 and 2 the money and the equipment were the ship's. In Cargo 3 the captain begins
without a ship, so they are the person's; a ship the captain owns spends and earns through
its owner (Ship.money and Ship.items are the owner's, game/ship.py)."""

# The six things an able hand is hired for, and what a captain is good at
SKILLS = ("loader", "mechanic", "gunner", "navigator", "steward", "broker")
SKILL_WORDS = {
    "loader": "loading and stowing",
    "mechanic": "keeping machines running",
    "gunner": "turrets and fights",
    "navigator": "lanes, needles and charts",
    "steward": "people aboard",
    "broker": "prices and papers",
}
SKILL_TOP = 5              # a skill runs from 0 (never done it) to 5 (better than anyone aboard)
WOUNDS_DEAD = 100          # wounds run from 0 (whole) to 100 (dead: the game is over)
WOUNDS_DOWN = 90           # work and duties put a captain down here, never further: only a fight kills
LOCKER_UNITS = 10          # an able hand's locker: room for this many units of private trade


class Person:
    def __init__(self, money=1000):
        self.money = money
        self.items = {}                 # equipment and keepsakes: {name: count}
        self.research_points = 0
        self.skills = {skill: 0 for skill in SKILLS}
        self.practice = {skill: 0 for skill in SKILLS}  # toward the next level
        self.wounds = 0
        self.gear = []                  # what the captain fights with on foot
        self.locker = {}                # private trade carried as an able hand: {good: units}
        self.locker_cost = {}           # and what it cost: {good: credits}
        self.berth = None               # the ship they work on now (game/hand.py), or None

    def skill(self, name):
        return self.skills.get(name, 0)

    def best_skill(self):
        return max(SKILLS, key=lambda s: (self.skills.get(s, 0), -SKILLS.index(s)))

    def train(self, name, amount=1):
        """Practice at a skill; enough of it raises the level, and each level asks for more
        (3, 12, 27, 48, 75: a master has 165 behind them). Returns the new level when it rose,
        else None."""
        if name not in SKILLS or self.skills.get(name, 0) >= SKILL_TOP:
            return None
        self.practice[name] = self.practice.get(name, 0) + amount
        need = 3 * (self.skills.get(name, 0) + 1) ** 2
        if self.practice[name] >= need:
            self.practice[name] -= need
            self.skills[name] = self.skills.get(name, 0) + 1
            return self.skills[name]
        return None

    def locker_units(self):
        return sum(self.locker.values())

    def acquire_item(self, item_name):
        self.items[item_name] = self.items.get(item_name, 0) + 1


def person_from_ship(ship):
    """A person for a game saved before the captain was one: the ship's money, items and
    research points become theirs."""
    person = Person(money=0)
    own = ship.__dict__
    person.money = own.pop("money", 0) if isinstance(own.get("money"), (int, float)) else 0
    items = own.pop("items", {})
    person.items = items if isinstance(items, dict) else {}
    points = own.pop("research_points", 0)
    person.research_points = points if isinstance(points, (int, float)) else 0
    return person
