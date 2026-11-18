"""The ship's modules: the hauler as a spine with container grips and hardpoints.

After the Universal Interstellar Transport platform in the hauler manuals: a command module
with its own small hold, and a train of modules clamped on behind it. The hull sets how many
grips the spine has (the old hauler three, an Ironback five, a Farstrider seven). A yard at a
planet or an asteroid base fits modules, strips them and mends them.

Modules wear. Hits in a fight and the rough lanes knock them about; a module with nothing left
is broken and does nothing until a yard (or a repair bay) mends it. Every effect goes through
the Ship's own sums (hold, attack, defense, repairs, tax, research) and a few places in the
game: needles (the scanner), lanes (radiation shielding), fights (salvage) and the turn (the
repair bay).
"""
import random

# kind: (name, price, what it does, one-line effect for the list)
MODULES = {
    "container": ("Container module", 8000,
                  "a cylinder on the container grips, climate held, inventory counted", "+100 hold"),
    "turret": ("Turret mount", 15000,
               "a connecting module with a hardpoint and a pulse laser on it", "+1 attack"),
    "shield": ("Shield module", 15000,
               "adaptive shielding and countermeasures: chaff, flares and a jammer", "+1 defense"),
    "rad": ("Radiation shielding", 10000,
            "layered shielding for the hard lanes", "lanes hit half"),
    "scanner": ("Scanner module", 12000,
                "multi-spectrum sensors: you see trouble before it sees you", "less trouble"),
    "repair": ("Repair bay", 18000,
               "printers and repair drones; they mend the hull and the other modules a little every turn",
               "mends"),
    "offloader": ("Robotic offloader", 10000,
                  "robot arms that load and unload without a dock gang", "tax -2%"),
    "salvage": ("Debris retrieval", 9000,
                "tractor beams and a crusher: what a won fight leaves behind is worth money", "salvage"),
    "hangar": ("Drone hangar", 20000,
               "two escort drones, the ankle-biters, that fly on your wing", "+1 attack"),
}
GRIPS = (3, 5, 7)               # module slots on the old hauler, an Ironback, a Farstrider
CONTAINER_UNITS = 100           # hold a container module adds
SCANNER_RISK = 0.8              # trouble on the way with a scanner
FULL = 100                      # a new module's condition


def condition_word(condition):
    if condition <= 0:
        return "broken"
    if condition < 40:
        return "patched"
    if condition < 75:
        return "worn"
    return "sound"


def module_name(kind):
    return MODULES.get(kind, (kind,))[0]


def mend_cost(module):
    """What a yard charges to bring one module back to sound."""
    price = MODULES.get(module["kind"], ("", 10000))[1]
    return int((FULL - module["condition"]) * price / 500)


class ModulesMixin:
    """The Game's yard and the wear on modules. Game inherits it (game/world.py)."""

    def has_yard(self):
        return type(self.current_location).__name__ in ("Planet", "AsteroidBase")

    def wear_modules(self, amount, reason=None):
        """Something knocked the ship about: one module takes it. Returns the module, or None."""
        fitted = [m for m in self.ship.modules if m["condition"] > 0]
        if not fitted or amount <= 0:
            return None
        module = random.choice(fitted)
        if self.has_equipment("loader_patch"):
            amount = max(1, int(amount * LOADER_WEAR))
        module["condition"] = max(0, module["condition"] - int(amount))
        if module["condition"] == 0:
            sfx("broken")
            self.display_simple_message("%s is broken%s. It does nothing until it is mended (upgrade/u, modules)."
                                        % (module_name(module["kind"]), " (" + reason + ")" if reason else ""),
                                        2, color='31')
        return module

    def mend_on_the_way(self):
        """Once a turn: a working repair bay patches the hull and the other modules."""
        ship = self.ship
        if not ship.working("repair"):
            return
        swarm = 2 if ship.researched("repair_swarm") else 1
        ship.damage = max(0, ship.damage - 2 * swarm)
        for module in ship.modules:
            if module["kind"] != "repair" and module["condition"] > 0:
                module["condition"] = min(FULL, module["condition"] + 5 * swarm)

    def module_rows(self):
        """The ship's train, one line per grip."""
        ship = self.ship
        rows = [["%s: %d grips" % (ship.hull_info()["name"], ship.grips())]]
        for number in range(ship.grips()):
            if number < len(ship.modules):
                module = ship.modules[number]
                text = "%s, %s (%s)" % (module_name(module["kind"]), condition_word(module["condition"]),
                                        MODULES[module["kind"]][3])
            else:
                text = "(empty grip)"
            rows.extend([line] for line in self.option_lines(number + 1, text))
        return rows

    def handle_yard(self):
        """The yard: fit, strip and mend modules."""
        if not self.has_yard():
            self.display_simple_message("Only the yards at planets and asteroid bases fit modules.")
            return
        ship = self.ship
        while True:
            rows = [["Yard - " + self.current_location.name], [""]] + self.module_rows()
            owed = sum(mend_cost(m) for m in ship.modules)
            rows.extend([[""], ["Money: %s. Mending everything: %s." % (
                self.format_money(ship.money), self.format_money(owed))]])
            print(self.create_box(rows, 'double'))
            answer = self.validate_input("Yard: fit/f, strip/s, mend/m, Enter to leave: ",
                                         ["fit", "f", "strip", "s", "mend", "m"])
            if answer is None:
                return
            if answer in ("fit", "f"):
                self.fit_module()
            elif answer in ("strip", "s"):
                self.strip_module()
            else:
                self.mend_modules()

    def fit_module(self):
        ship = self.ship
        if len(ship.modules) >= ship.grips():
            self.display_simple_message("Every grip on the spine is taken. Strip a module first, or overhaul the "
                                        "hull for more grips (upgrade/u, hull).")
            return
        kinds = list(MODULES)
        rows = [["Modules the yard can fit"], [""]]
        for number, kind in enumerate(kinds, 1):
            name, price, about, effect = MODULES[kind]
            rows.extend([line] for line in self.option_lines(number, "%s, %s: %s. %s." % (
                name, self.format_money(price), effect, about[0].upper() + about[1:])))
        print(self.create_box(rows, 'double'))
        answer = self.validate_input("Fit which (1-%d, Enter for none): " % len(kinds),
                                     [str(i) for i in range(1, len(kinds) + 1)])
        if answer is None:
            return
        kind = kinds[int(answer) - 1]
        name, price = MODULES[kind][:2]
        if ship.money < price:
            self.display_simple_message("The yard wants %s for a %s." % (self.format_money(price), name.lower()))
            return
        ship.money -= price
        ship.modules.append({"kind": kind, "condition": FULL})
        sfx("fit")
        self.display_simple_message("The yard's spanner monkeys clamp a %s onto grip %d." % (
            name.lower(), len(ship.modules)), 2, color='32')

    def strip_module(self):
        ship = self.ship
        if not ship.modules:
            self.display_simple_message("There is nothing on the grips to strip.")
            return
        answer = self.validate_input("Strip which grip (1-%d, Enter for none): " % len(ship.modules),
                                     [str(i) for i in range(1, len(ship.modules) + 1)])
        if answer is None:
            return
        module = ship.modules.pop(int(answer) - 1)
        name, price = MODULES[module["kind"]][:2]
        paid = int(price * 0.4 * module["condition"] / FULL)
        ship.money += paid
        self.display_simple_message("The yard takes the %s back for %s." % (name.lower(), self.format_money(paid)), 2)

    def mend_modules(self):
        ship = self.ship
        worn = [m for m in ship.modules if m["condition"] < FULL]
        if not worn:
            self.display_simple_message("Every module is sound.")
            return
        mended = 0
        for module in sorted(worn, key=lambda m: m["condition"]):
            cost = mend_cost(module)
            if ship.money < cost:
                break
            ship.money -= cost
            module["condition"] = FULL
            mended += 1
        if mended:
            self.display_simple_message("Mended %d module%s." % (mended, "" if mended == 1 else "s"), 2, color='32')
        if mended < len(worn):
            self.display_simple_message("Not enough money to mend the rest.", 2, color='33')


from .sound import sfx  # noqa: E402
from .looking import LOADER_WEAR  # noqa: E402
