"""Prices that climb. Whatever a hand or a captain buys to get better gets dearer the more they
already have, on one curve (Dan, 20 Nov: the implants' curve, for the equipment too):

    price = base × level² × (1 + LOAD × owned), rounded to 50

- level: the level being bought (an implant's level, the next point of an upgrade); 1 for a thing
  without levels;
- owned: how many of that family the buyer has already (implants fitted, upgrades bought, modules
  on the grips, items from the shop, gear carried).

Implants (game/training.py), ship upgrades (game/world.py), the yard's modules (game/modules.py),
the port shop's equipment (game/port.py) and the outfitter's gear (game/brawl.py) all use it.
The sellers say so when a price has climbed (`price_note`), and a captain who has paid a climbed
price notices it in a look now and then (game/looking.py) and in a thought (story/cargo3/prices.json).
tools/prices.py checks the curve, every seller and the old saves.
"""
import math
import random

LOAD = 0.3
UPGRADE_BASE = 1000         # a point of attack, defense or speed: 1,000 for the first


def round_to(value, step=50):
    """A price as a seller would say it: to the nearest step, never below one step."""
    return max(step, int(round(value / float(step))) * step)


def curve(base, level=1, owned=0):
    return round_to(base * level ** 2 * (1 + LOAD * owned))


def upgrades_bought(ship):
    """Points of attack, defense and speed bought at a yard: {property: n}. A save from before
    the curve kept only the next price (2,000, then half again each time): count back from it."""
    bought = ship.__dict__.get("upgrades_bought")
    if not isinstance(bought, dict):
        bought = {}
        for prop, cost in (getattr(ship, "upgrade_costs", None) or {}).items():
            try:
                bought[prop] = max(0, int(round(math.log(max(cost, 2000) / 2000.0, 1.5))))
            except (TypeError, ValueError):
                bought[prop] = 0
        ship.__dict__["upgrades_bought"] = bought
    for prop in ("attack", "defense", "speed"):
        bought.setdefault(prop, 0)
    return bought


def upgrade_price(ship, prop):
    bought = upgrades_bought(ship)
    return curve(UPGRADE_BASE, bought[prop] + 1, sum(bought.values()))


# What the people who sell say when a price has climbed: the yard master (modules), the yard
# foreman (upgrades), the chandler (the port shop), the outfitter (gear), the cybersurgeon (implants)
PRICE_COMMENTS = {
    "yard": [
        "The yard master taps the grips. 'Every module you hang on her costs more to fit than the last. "
        "Physics, captain. And invoices.'",
        "'The spine takes the load,' says the yard master, 'and the bill takes the rest.'",
        "'Full grips, full price,' the yard master says. 'Fuller grips, fuller price.'",
    ],
    "upgrade": [
        "'The square of the work,' says the yard foreman. 'The second point of armour is four times the first. "
        "Nobody knows why. We just bill it.'",
        "The yard foreman shows you the price on a slate, then turns the slate so you can see it is not a typo.",
        "'Every point on top of the last one costs more,' the foreman says. 'Like stairs. Expensive stairs.'",
    ],
    "shop": [
        "The chandler adds it up twice. 'Collectors' prices,' she says. 'You're a collector now.'",
        "'A well-equipped captain pays a well-equipped price,' says the chandler, who is very well equipped.",
        "The chandler's price board ticks up as you walk in. It knows you.",
    ],
    "gear": [
        "'Kit gets dearer when you've already got kit,' the outfitter says. 'You look like you can afford it.'",
        "The outfitter looks at your belt, counts what is on it, and adds a little to every price.",
        "'Second knife's always dearer than the first,' says the outfitter. 'The first one, you needed.'",
    ],
    "implant": [
        "'Each one makes the next one harder to fit,' the cybersurgeon says. 'I bill for harder.'",
        "The cybersurgeon reads your scans and sighs. 'Crowded in there. Crowded costs.'",
    ],
}


def price_note(kind, rng=random):
    """A seller's line about a climbed price."""
    return rng.choice(PRICE_COMMENTS[kind])


def paid_dearer(game, kind):
    """Note that the captain paid a climbed price (the story's stat `paid_dearer`)."""
    counts = game.__dict__.setdefault("paid_dearer", {})
    if not isinstance(counts, dict):
        counts = game.paid_dearer = {}
    counts[kind] = counts.get(kind, 0) + 1
