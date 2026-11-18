"""The needles: how a ship crosses between the stars in 2460.

A lead hauler with a Dharr Santor drive pushes a captured asteroid ahead of it as shield and
reaction mass; the ships behind it fly in single file in its wake, and at the right speed the
whole needle jumps as one. A hauler books a place in the file at the Hansa's needle office:
near the front it is warm, shielded and dear; the tail is cheap and cold, and the Cargolytes
work the tail. Fights happen where the wake does not protect, while a needle forms and after
it breaks up, so the place in the file sets how likely trouble is on the way. Inside a star
system a ship flies free, on its own fuel.

The fare grows with the routes, as Cargo 1's dues did; Hansa bonds lower it, and so does the
Hansa's standing (game/factions.py). A captain who cannot pay may ride on account, up to a
limit; the convoy master takes cargo against what is owed past it.
"""
import random

POSITIONS = {   # place in the file: (fare factor, chance of trouble on the way, how it is)
    "front": (2.0, 0.4, "behind the lead hauler and its asteroid: warm, shielded, dear"),
    "middle": (1.0, 1.0, "the middle of the file"),
    "tail": (0.5, 1.6, "the tail: cheap and cold, and the Cargolytes work the tail"),
}
HOP_FUEL = 3            # fuel for a hop inside a star system
OUTPOST_EVERY = 3       # needles leave a planet every turn, anywhere else every third turn
FUEL_PRICE = 30         # credits a unit, from a yard's tanks, when the hold has none
ACCOUNT_LIMIT = 6       # the needle office carries a captain for up to this many middle fares


def system_of(place_name):
    """The star system a place is in: the story's place data, up to the first comma."""
    from .story import story_data          # story imports the game's modules; fetch when needed
    place = story_data()["places"].get(place_name) or {}
    return (place.get("system") or place_name).split(",")[0].strip()


class NeedlesMixin:
    """The Game's needle office and in-system hops. Game inherits it (game/world.py)."""

    def same_system(self, a, b):
        return system_of(a.name if hasattr(a, "name") else a) == system_of(b.name if hasattr(b, "name") else b)

    def needle_fare(self, position="middle"):
        """What a place in the next needle costs now."""
        base = 60 + 60 * (self.turn / 10.0) ** 1.35
        hike = getattr(self, "dues_hike", 1.0) if self.turn <= getattr(self, "dues_hike_until", 0) else 1.0
        fare = base * POSITIONS[position][0] * hike * self.hansa_fare_factor() * 0.88 ** getattr(self, "hansa_bonds", 0)
        if self.ship.researched("fast_turnaround"):
            fare *= 0.9
        if self.has_equipment("founders_transponder"):
            fare *= EQUIPMENT_FARE
        return max(10, int(fare))

    def needle_wait(self):
        """Turns until the next needle forms here: planets have one every turn, outposts, bases
        and colonies every third turn (their buoys see fewer lead haulers)."""
        if type(self.current_location).__name__ == "Planet":
            return 0
        return (OUTPOST_EVERY - self.turn % OUTPOST_EVERY) % OUTPOST_EVERY

    def fare_for(self, position):
        """The fare this captain pays: a berth owed by the needle office puts the front at the middle's fare."""
        if position == "front" and getattr(self, "front_berths", 0) > 0:
            return self.needle_fare("middle")
        return self.needle_fare(position)

    def book_needle(self, destination):
        """The needle office: pick a place in the file and pay. Returns the place, or None."""
        lines = [["Needle to %s (%s)" % (destination.name, system_of(destination.name))], [""]]
        for number, (position, (_, _, how)) in enumerate(POSITIONS.items(), 1):
            lines.append(["%d. %s: %s" % (number, how[0].upper() + how[1:], self.format_money(self.fare_for(position)))])
        berths = getattr(self, "front_berths", 0)
        if berths:
            lines.extend([[""], ["A berth at the front for the middle's fare: %d jump%s left." % (berths, "" if berths == 1 else "s")]])
        owed = getattr(self, "dues_arrears", 0)
        if owed:
            lines.extend([[""], ["On account with the needle office: %s." % self.format_money(owed)]])
        wait = self.needle_wait()
        if wait:
            lines.extend([[""], ["Few lead haulers call here: the next needle forms in %d turn%s, and you wait "
                                 "at the buoy." % (wait, "" if wait == 1 else "s")]])
        print(self.create_box(lines, 'double'))
        answer = self.validate_input("Your place in the needle (1-3, Enter to stay): ", ["1", "2", "3"])
        if answer is None:
            return None
        position = list(POSITIONS)[int(answer) - 1]
        fare = self.fare_for(position)
        if self.ship.money >= fare:
            self.ship.money -= fare
            self.display_simple_message("Booked: %s, %s." % (POSITIONS[position][2].split(":")[0], self.format_money(fare)), 1)
        elif owed + fare <= ACCOUNT_LIMIT * self.needle_fare("middle"):
            self.dues_arrears = owed + fare
            self.display_simple_message("You ride on account: %s owed to the needle office (pay at the Hansa terminal, "
                                        "hansa/ha)." % self.format_money(self.dues_arrears), 2, color='33')
        else:
            self.display_simple_message("The needle office will not carry you further on account. Pay what you owe "
                                        "(hansa/ha), sell something, or fly inside this system.", 2, color='31')
            self.convoy_master_takes()
            return None
        if position == "front" and berths:
            self.front_berths = berths - 1
        if wait:
            self.turn += wait               # waiting at the buoy; the jump itself is the trip's turn
        sfx("needle")
        self.needle_risk = POSITIONS[position][1] * (SCANNER_RISK if self.ship.working("scanner") else 1.0) \
            * (NEEDLE_TALK_RISK if self.has_equipment("needle_talk") else 1.0)
        self.needle_position = position
        return position

    def convoy_master_takes(self):
        """Past the limit, the convoy master takes cargo against what is owed."""
        ship, owed = self.ship, getattr(self, "dues_arrears", 0)
        lines = []
        for good in ('tech', 'agri', 'salt', 'fuel'):
            if owed <= 0 or ship.cargo[good] <= 0:
                continue
            price = max(1, self.current_location.market.get(good, 0) or 20)
            taken = min(ship.cargo[good], int(owed / price) + 1)
            ship.cargo[good] -= taken
            owed -= int(taken * price)
            lines.append("The convoy master takes %d %s against the debt." % (taken, good))
        if lines:
            self.dues_arrears = max(0, owed)
            self.display_simple_message(lines, 2, color='31')

    def fly_in_system(self, destination):
        """A hop inside the star system, on the ship's own fuel."""
        ship = self.ship
        burned = min(HOP_FUEL, ship.cargo["fuel"])
        ship.cargo["fuel"] -= burned
        bought = HOP_FUEL - burned
        cost = bought * FUEL_PRICE
        ship.money -= cost
        self.needle_risk = 1.0
        self.needle_position = None
        self.display_simple_message("A hop inside %s on your own engines: %d fuel%s." % (
            system_of(destination.name), HOP_FUEL,
            " (%d from the yard's tanks, %s)" % (bought, self.format_money(cost)) if bought else ""), 1)

    def after_needle(self):
        """At the end of a jump: in the tail, the Cargolytes may have cut containers off."""
        position, self.needle_position = getattr(self, "needle_position", None), None
        if position != "tail" or random.random() >= 0.12:
            return
        goods = [g for g in ('tech', 'agri', 'salt', 'fuel') if self.ship.cargo[g] >= 10]
        if not goods:
            return
        good = max(goods, key=lambda g: self.ship.cargo[g])
        lost = max(1, self.ship.cargo[good] // 10)
        self.ship.cargo[good] -= lost
        self.display_simple_message("Somewhere in the jump the Cargolytes cut two containers off the tail of the "
                                    "needle: %d %s gone." % (lost, good), 2, color='31')


from .modules import SCANNER_RISK  # noqa: E402
from .sound import sfx  # noqa: E402
from .looking import EQUIPMENT_FARE, NEEDLE_TALK_RISK  # noqa: E402
