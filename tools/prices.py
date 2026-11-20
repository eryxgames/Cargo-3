#!/usr/bin/env python3
"""Prices that climb (game/prices.py): the one curve, and everything on it (implants, ship
upgrades, the yard's modules, the port shop, the outfitter), what the sellers say when a price has
climbed, the captain's own sidenotes (a look's quiet line, thoughts that come and go), the story's
stats, a save from before the curve, and the screens at 36 columns.

    python3 tools/prices.py
"""
import os, random, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ["CARGO_SAGA_HOME"] = tempfile.mkdtemp(prefix="cargo3-prices-")
os.environ["NO_COLOR"] = "1"
import headless  # noqa: E402

cargo = headless.load(os.path.join(os.path.dirname(HERE), "game", "world.py"))
import game.prices as prices  # noqa: E402
import game.training as training  # noqa: E402
import game.modules as modules  # noqa: E402
import game.looking as looking  # noqa: E402
problems = []


def expect(ok, what):
    if not ok:
        problems.append(what)
        print("FAIL", what)


def screen(cols, show):
    size = os.terminal_size((cols, 40))
    old = shutil.get_terminal_size
    shutil.get_terminal_size = lambda fallback=(80, 24): size
    try:
        with headless.quiet() as out:
            show()
    finally:
        shutil.get_terminal_size = old
    return out.getvalue()


def flat(text):
    return " ".join(text.replace("│", " ").replace("║", " ").split())


def widest(text):
    return max(cargo.visible_len(line) for line in text.splitlines())


def afloat(money=200000, place="Alpha"):
    game, io = headless.new_game(cargo, afloat=True)
    game.current_location = game.location_named(place)
    game.ship.money = money
    return game, io


def said(kind, text):
    """Whether one of the sellers' remarks of this kind is on the screen."""
    plain = text.replace("'", "")
    return any(line.replace("'", "")[:30] in plain for line in prices.PRICE_COMMENTS[kind])


# ---- the curve -----------------------------------------------------------------------------------------
expect([prices.curve(500, level, 0) for level in range(1, 5)] == [500, 2000, 4500, 8000], "the implants' curve")
expect(prices.curve(500, 4, 3) == 15200 and prices.curve(8000, 1, 3) == 15200, "three owned: three tenths each")
expect(all(training.implant_price(level, fitted) == prices.curve(500, level, fitted) for level in range(1, 5) for fitted in range(4)),
       "the implants are on the same curve")
expect(prices.round_to(1234) == 1250 and prices.round_to(10) == 50, "prices to the nearest 50")

# ---- ship upgrades ---------------------------------------------------------------------------------------
game, io = afloat()
ship = game.ship
expect([prices.upgrade_price(ship, p) for p in ("attack", "defense", "speed")] == [1000] * 3, "the first point: 1,000")
spent = []
for _ in range(4):
    before = ship.money
    with headless.quiet():
        game.buy_upgrade("attack")
    spent.append(before - ship.money)
expect(spent == [1000, 5200, 14400, 30400], "attack points: the square of the level, and dearer for each bought: %s" % spent)
expect(prices.upgrade_price(ship, "defense") == 2200, "the first point of defense after four of attack: 2,200")
expect(game.paid_dearer == {"upgrade": 3} and game.story_snapshot()["stats"]["upgrades"] == 4, "three paid dearer; four upgrades")
ship.money = 100
with headless.quiet() as out:
    bought = game.buy_upgrade("speed")
expect(not bought and "The yard wants %s" % game.format_money(2200) in flat(out.getvalue()), "no money, no point")
text = screen(36, game.show_upgrade_prices)
expect(widest(text) <= 36 and "Attack" in text and said("upgrade", flat(text)), "the yard's list, with the foreman's remark")
game, io = afloat()
expect(not said("upgrade", flat(screen(80, game.show_upgrade_prices))), "no remark before anything was bought")
# a save from before the curve kept only the next price: count back from it
game, io = afloat()
game.ship.__dict__.pop("upgrades_bought", None)
game.ship.upgrade_costs = {"attack": 4500, "defense": 3000, "speed": 2000}
expect(prices.upgrades_bought(game.ship) == {"attack": 2, "defense": 1, "speed": 0}, "an old save: two of attack, one of defense")

# ---- the yard's modules -------------------------------------------------------------------------------------
game, io = afloat()
ship = game.ship
expect(modules.module_price(ship, "container") == 8000, "a first container: 8,000")
paid = []
for _ in range(3):
    before = ship.money
    io.feed([str(list(cargo.MODULES).index("container") + 1)])
    with headless.quiet() as out:
        game.fit_module()
    paid.append(before - ship.money)
expect(paid == [8000, 10400, 12800], "each module on the grips makes the next dearer: %s" % paid)
expect(game.paid_dearer == {"yard": 2}, "two paid dearer")
before = ship.money
io.feed(["1"])
with headless.quiet():
    game.strip_module()
expect(ship.money - before == int(8000 * 0.4), "stripping one pays back on its own price")
io.feed([""])
text = screen(36, game.fit_module)
expect(widest(text) <= 36 and said("yard", flat(text)) and "Container module, 12.8K" in flat(text),
       "the yard's list says so, with two on the grips, at 36 columns")

# ---- the port shop -------------------------------------------------------------------------------------------
game, io = afloat()
ship = game.ship
game.shop.current_turn_items = [("radar", dict(game.shop.base_equipment["radar"]))] \
    if "radar" in game.shop.base_equipment else [list(game.shop.base_equipment.items())[0]]
name, data = game.shop.current_turn_items[0]
base = data["price"]
ship.items.clear()
io.feed([name])
before = ship.money
with headless.quiet():
    game.visit_shop()
expect(before - ship.money == base and ship.items.get(name) == 1, "the first piece at its price: %s" % name)
other = next(n for n in game.shop.base_equipment if n != name)
game.shop.current_turn_items = [(other, dict(game.shop.base_equipment[other]))]
game.shop.sold_items = set() if hasattr(game.shop, "sold_items") else None
io.feed([other])
before = ship.money
with headless.quiet() as out:
    game.visit_shop()
expect(before - ship.money == prices.curve(game.shop.base_equipment[other]["price"], 1, 1) and said("shop", flat(out.getvalue())),
       "the second, three tenths dearer, and the chandler says so")
ship.items["procrustes_analyzer"] = 1
expect(sum(c for i, c in ship.items.items() if i in game.shop.base_equipment) == 2, "story items do not count")

# ---- the outfitter, and the clinic ----------------------------------------------------------------------------
game, io = headless.new_game(cargo)
game.labour = []
game.current_location = game.location_named("Gamma")
game.person.money = 5000
expect(game.gear_price("cutting torch") == 450, "a torch for a hand with nothing: 450")
game.person.gear = ["knife", "work suit"]
expect(game.gear_price("cutting torch") == 700, "with two pieces: 450 and six tenths, to the nearest 50")
io.feed([""])
text = screen(36, game.handle_gear)
expect(widest(text) <= 36 and said("gear", flat(text)), "the outfitter remarks on it")
io.feed(["2"])
with headless.quiet():
    game.handle_gear()
expect("cutting torch" in game.person.gear and game.paid_dearer == {"gear": 1}, "bought dearer")
game.current_location = game.location_named("Epsilon")
game.person.money = 50000
with headless.quiet() as out:
    game.implant_clinic(pick="", sure=False)
expect(not said("implant", flat(out.getvalue())), "no remark before the first implant")
game.person.implants = {"gunner": 1}
with headless.quiet() as out:
    game.implant_clinic(pick="", sure=False)
expect(said("implant", flat(out.getvalue())), "the surgeon remarks once one is fitted")

# ---- the captain's own sidenotes -------------------------------------------------------------------------------
game, io = headless.new_game(cargo)
lines = set()
for turn in range(200):
    game.turn = turn
    lines.add(game.quiet_line())
expect(not lines & set(looking.PRICE_QUIET), "no sidenotes on prices before paying a climbed one")
game.paid_dearer = {"gear": 1}
lines = set()
for turn in range(400):
    game.turn = turn
    lines.add(game.quiet_line())
expect(len(lines & set(looking.PRICE_QUIET)) >= 3, "after it, the look's quiet lines include them")
nodes = cargo.story_data()["nodes"]


def thoughts(game):
    snap = game.story.snapshot()
    return [n for n, node in nodes.items() if n.startswith("thought.price.") and game.story.check(game.story.requires_of(node), snap)]


game, io = headless.new_game(cargo)
expect(thoughts(game) == [], "no price thoughts at the start")
game.paid_dearer = {"gear": 1}
expect(thoughts(game) == ["thought.price.pod"], "the first: the most expensive nap in history")
game.paid_dearer = {"gear": 5}
game.person.implants = {"gunner": 1, "loader": 1}
game.person.gear = ["knife", "work suit", "rivet gun"]
got = thoughts(game)
expect("thought.price.pod" not in got and "thought.price.implants" in got and "thought.price.gear" in got,
       "they come and go with what was bought: %s" % got)
game.person.implants = {"gunner": 1, "loader": 1, "steward": 1, "broker": 1}
expect("thought.price.implants" not in thoughts(game), "and go again")
text = screen(36, game.handle_think)
expect(widest(text) <= 36 and "charged to the eyeballs" in flat(text), "the think screen at 36 columns")

# ---- saves --------------------------------------------------------------------------------------------------------
game, io = afloat()
with headless.quiet():
    game.buy_upgrade("attack")
    game.buy_upgrade("attack")
    game.save_game("prices")
    loaded = cargo.load_game("prices")
expect(prices.upgrades_bought(loaded.ship)["attack"] == 2 and loaded.paid_dearer == {"upgrade": 1}, "a save keeps the count")

print("prices: %s" % ("ok" if not problems else "%d problems" % len(problems)))
sys.exit(1 if problems else 0)
