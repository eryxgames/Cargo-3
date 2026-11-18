#!/usr/bin/env python3
"""The engine's systems (from Cargo 2), checked one by one on a real game: standing with the
factions, the needles between the stars and the hops inside a system, the ship's modules, convoy
fights, research, achievements (and whatever later systems add here).

    python3 tools/systems.py
"""
import os, random, re, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ["CARGO_SAGA_HOME"] = tempfile.mkdtemp(prefix="cargo-systems-")
import headless  # noqa: E402

cargo = headless.load(os.path.join(os.path.dirname(HERE), "game", "world.py"))
problems = []


def expect(ok, what):
    if not ok:
        problems.append(what)


# ---- standing ------------------------------------------------------------------------
game, io = headless.new_game(cargo)
expect(game.standing == {"hansa": 0, "mandate": 0, "concord": 0}, "a new game starts at standing 0: %s" % game.standing)
game.story.apply({"standing.hansa": 30, "standing.mandate": -250, "dawn_trust": 15})
expect(game.standing_of("hansa") == 30, "an effect moves the Hansa standing")
expect(game.standing_of("mandate") == -100, "standing stops at -100")
expect(game.dawn_trust == 15, "the dawn's trust moves")
snap = game.story_snapshot()["stats"]
expect(snap.get("standing.hansa") == 30 and snap.get("standing.mandate") == -100 and snap.get("dawn_trust") == 15,
       "the story sees the standings: %s" % {k: v for k, v in snap.items() if "standing" in k or "dawn" in k})
expect(game.story.check({"standing.hansa": 25}, game.story.snapshot()), "a condition reads a standing")
expect(not game.story.check({"standing.concord": 1}, game.story.snapshot()), "a condition fails on a low standing")
expect(abs(game.hansa_fare_factor() - 0.88) < 1e-9, "the Hansa's fares follow its standing")
game.standing["mandate"] = 100
random.seed(1)
expect(all(game.waved_through("militia") for _ in range(20)), "a trusted captain is waved through by cutters")
expect(not any(game.waved_through("pirate") for _ in range(20)), "pirates wave nobody through")
game.standing["mandate"] = 10
expect(not any(game.waved_through("militia") for _ in range(50)), "a captain the Mandate barely knows is stopped")
game.standing["concord"] = 100
expect(abs(game.concord_research_factor() - 1.5) < 1e-9, "the Concord shares more with a trusted captain")
io.queue.clear(); io.feed([""])
with headless.quiet() as out:
    game.story.journal()
expect("The Hansa: +30, trusted" in out.getvalue(), "the journal shows standing")

# a save from before standing existed loads with every standing at 0
game, io = headless.new_game(cargo)
del game.standing, game.dawn_trust
with headless.quiet():
    game.save_game("old")
    loaded = cargo.load_game("old")
expect(loaded.standing == {"hansa": 0, "mandate": 0, "concord": 0} and loaded.dawn_trust == 0,
       "an older save gets standing 0")

# ---- the needles -----------------------------------------------------------------------
game, io = headless.new_game(cargo)
game.turn = 50
here = game.current_location
by_name = {loc.name: loc for loc in game.locations + [l for g in game.hidden_locations.values() for l in g]
           + [l for c in game.chapter_locations.values() for g in c.values() for l in g]}
expect(game.same_system("Omega XIV", "Ancient Ruins Alpha") and not game.same_system("Alpha", "Beta"),
       "places in the same star system are told from the rest")
middle = game.needle_fare("middle")
expect(game.needle_fare("front") in (2 * middle, 2 * middle + 1) and abs(game.needle_fare("tail") - middle / 2) <= 1,
       "front costs twice the middle, the tail half: %s" % [game.needle_fare(p) for p in ("front", "middle", "tail")])
game.hansa_bonds = 2
expect(game.needle_fare("middle") < middle, "bonds lower the fare")
game.hansa_bonds = 0
game.standing["hansa"] = -100
expect(game.needle_fare("middle") > middle, "a Hansa that distrusts the captain charges more")
game.standing["hansa"] = 0
other = next(loc for loc in game.locations if not game.same_system(loc, here))
money, turn = game.ship.money, game.turn
io.queue.clear(); io.feed([""])                                     # Enter at the needle office: stay
with headless.quiet():
    went = game.travel_to_location(other.name)
expect(not went and game.current_location is here and game.turn == turn and game.ship.money == money,
       "Enter at the needle office: no needle, no turn, no fare")
game.ship.money = 100000
io.queue.clear(); io.feed(["2"] + [""] * 30)
random.seed(3)
with headless.quiet():
    went = game.travel_to_location(other.name)
expect(went and game.current_location is other and game.turn == turn + 1, "a booked needle takes the ship there")
expect(game.ship.money <= 100000 - middle, "the middle place is paid: %s" % (100000 - game.ship.money))
# riding on account, and past the limit
game.ship.money = 0
fare = game.needle_fare("middle")
io.queue.clear(); io.feed(["2"])
with headless.quiet():
    booked = game.book_needle(here)
expect(booked == "middle" and getattr(game, "dues_arrears", 0) == fare, "a captain without money rides on account")
game.dues_arrears = 10 * fare
game.ship.cargo["salt"] = 40
io.queue.clear(); io.feed(["2"])
with headless.quiet():
    booked = game.book_needle(here)
expect(booked is None and game.ship.cargo["salt"] < 40, "past the limit the office refuses and the convoy master takes cargo")
# a hop inside a system burns fuel, or buys it
game, io = headless.new_game(cargo)
omega, ruins = by_name["Omega XIV"], by_name["Ancient Ruins Alpha"]
game.locations += [omega, ruins]
game.current_location = omega
game.ship.cargo["fuel"], game.ship.money = 10, 1000
io.queue.clear(); io.feed([""] * 30)
with headless.quiet():
    went = game.travel_to_location(ruins.name)
expect(went and game.ship.cargo["fuel"] == 7, "a hop inside the system burns 3 fuel")
game.ship.cargo["fuel"], money = 1, game.ship.money
game.current_location = omega
io.queue.clear(); io.feed([""] * 30)
with headless.quiet():
    game.travel_to_location(ruins.name)
expect(game.ship.cargo["fuel"] == 0 and money - game.ship.money >= 60, "fuel the hold lacks is bought from the yard")
# the tail: the Cargolytes sometimes cut containers off
game, io = headless.new_game(cargo)
game.ship.cargo["tech"] = 100
losses = 0
for seed in range(200):
    random.seed(seed)
    game.needle_position = "tail"
    before = game.ship.cargo["tech"]
    with headless.quiet():
        game.after_needle()
    losses += game.ship.cargo["tech"] < before
    game.ship.cargo["tech"] = 100
expect(5 < losses < 50, "the tail loses containers now and then: %d in 200" % losses)
game.needle_position = "front"
with headless.quiet():
    game.after_needle()
expect(game.ship.cargo["tech"] == 100, "the front loses nothing")

# ---- the ship's modules ------------------------------------------------------------------
def at(kind_name):
    return next(loc for loc in game.locations if type(loc).__name__ == kind_name)


def yard(answers):
    io.queue.clear(); io.feed(answers + [""] * 6)
    with headless.quiet():
        game.handle_yard()


game, io = headless.new_game(cargo)
ship = game.ship
game.current_location = at("Planet")
expect(ship.modules == [] and ship.grips() == 3, "a new ship has three empty grips")
general = ship.hold_sizes()[0]
attack, defense = ship.fight_attack(), ship.fight_defense()
ship.money = 100000
yard(["f", "1"])
expect(len(ship.modules) == 1 and ship.money == 92000 and ship.hold_sizes()[0] == general + 100,
       "a container module costs 8,000 and adds 100 units of hold")
yard(["f", "2", "f", "3"])
expect(ship.fight_attack() == attack + 1 and ship.fight_defense() == defense + 1, "a turret and a shield fight")
money = ship.money
yard(["f", "1"])
expect(len(ship.modules) == 3 and ship.money == money, "no module fits past the last grip")
ship.modules[1]["condition"] = 0
expect(ship.fight_attack() == attack, "a broken turret does not shoot")
expect(cargo.mend_cost(ship.modules[1]) == 3000, "mending a broken turret costs 3,000: %d" % cargo.mend_cost(ship.modules[1]))
yard(["m"])
expect(ship.modules[1]["condition"] == 100 and ship.money == money - 3000, "the yard mends what the money pays for")
yard(["s", "1"])
expect(len(ship.modules) == 2 and ship.money == money - 3000 + 3200 and ship.hold_sizes()[0] == general,
       "stripping a sound container pays 40% back")
random.seed(3)
with headless.quiet():
    worn = game.wear_modules(30)
expect(worn is not None and worn["condition"] == 70, "a hit wears one module")
with headless.quiet():
    for _ in range(5):
        game.wear_modules(30)
expect(any(m["condition"] == 0 for m in ship.modules), "enough hits break a module")
ship.hull = 1
expect(ship.grips() == 5, "an Ironback has five grips")
game.current_location = cargo.DeepSpaceOutpost("DSO-Test", 7, 3, 20, "Stable")
yard(["f", "1"])
expect(len(ship.modules) == 2, "outposts have no yard")

# effects outside the ship's own sums
game, io = headless.new_game(cargo)
ship = game.ship
ship.money = 10 ** 6
game.current_location = at("Planet")
tax = ship.trade_tax(0.05)
for kind in ("repair", "offloader", "scanner"):
    ship.modules.append({"kind": kind, "condition": 100})
expect(abs(ship.trade_tax(0.05) - (tax - 0.02)) < 1e-9, "the offloader takes 2% off the tax")
ship.damage, ship.modules[1]["condition"] = 10, 50
game.ticked_turn = game.turn - 1
with headless.quiet():
    game.new_turn()
expect(ship.damage == 8 and ship.modules[1]["condition"] == 55, "the repair bay mends a little every turn")
here = game.current_location
there = next(loc for loc in game.locations if not game.same_system(loc, here))
io.queue.clear(); io.feed(["2"])
with headless.quiet():
    game.book_needle(there)
expect(abs(game.needle_risk - 0.8) < 1e-9, "a scanner sees trouble coming: %s" % game.needle_risk)
far = cargo.DeepSpaceOutpost("DSO-Test", 7, 3, 20, "Stable")
expect(game.lane_hazard(far) == 1, "an outpost is a rough lane for the old hauler")
ship.damage = 0
random.seed(5)
with headless.quiet():
    game.arrive_through_hazard(far)
plain = ship.damage
ship.damage = 0
ship.modules.append({"kind": "rad", "condition": 100})
random.seed(5)
with headless.quiet():
    game.arrive_through_hazard(far)
expect(ship.damage == plain // 2, "radiation shielding halves a rough lane: %d against %d" % (ship.damage, plain))
ship.modules.append({"kind": "salvage", "condition": 100})
random.seed(2)
money = ship.money
lines = []
with headless.quiet():
    while not lines or not any("salvage" in line for line in lines):
        lines = []
        game.fight("skiff", 0, lines, edge=20)
expect(any("salvage" in line for line in lines), "debris retrieval salvages a won fight")

# a save keeps the modules; a save from before them gets an empty spine
with headless.quiet():
    game.save_game("modules")
    loaded = cargo.load_game("modules")
expect([m["kind"] for m in loaded.ship.modules] == [m["kind"] for m in ship.modules], "modules survive a save and a load")
del loaded.ship.__dict__["modules"]
loaded.bring_up_to_date()
expect(loaded.ship.modules == [] and loaded.ship.grips() == 3, "an old save gets an empty spine")

# ---- research branches -------------------------------------------------------------------------
game, io = headless.new_game(cargo)
research = game.research
expect("bulk_logistics" not in research.open_options(), "a branch waits for its root")
research.unlock("xenoeconomy")
expect({"bulk_logistics", "fast_turnaround"} <= set(research.open_options()), "a researched root opens both branches")
research.unlock("bulk_logistics")
expect("fast_turnaround" not in research.open_options() and research.closed("fast_turnaround"),
       "choosing one branch closes its twin")
game.ship.modules.append({"kind": "container", "condition": 100})
expect(game.ship.hold_sizes()[0] == headless.new_game(cargo)[0].ship.hold_sizes()[0] + 150,
       "bulk logistics: a container module holds 150")
research.unlock("chronopolitics")
expect("segment_acoustics" not in research.open_options(game.story.done), "ring science waits for the expedition")
expect("segment_acoustics" in research.open_options({"ring.expedition": 1}), "ring science opens after the expedition")
research.unlock("drone_autonomy")
attack = game.ship.fight_attack()
game.ship.modules.append({"kind": "hangar", "condition": 100})
expect(game.ship.fight_attack() == attack + 2, "drone autonomy: a hangar is worth two")
fare = game.needle_fare("middle")
research.unlock("fast_turnaround")
expect(game.needle_fare("middle") < fare, "fast turnaround lowers the fares")

# ---- achievements ----------------------------------------------------------------------------------
game, io = headless.new_game(cargo)
game.trades_completed = 26
game.ticked_turn = game.turn - 1
with headless.quiet() as buf:
    game.new_turn()
expect("no_more_deadheads" in game.achievements and "No more deadheads" in buf.getvalue(), "an achievement is announced")
with headless.quiet() as buf:
    game.check_achievements()
expect("No more deadheads" not in buf.getvalue(), "an achievement is announced once")
record = game.captain_record()
expect(record["achievements"] == ["no_more_deadheads"], "achievements go into the captain record: %s"
       % record["achievements"])
expect(cargo.clean_captain(record)["achievements"] == record["achievements"], "and come back out of it")
old = dict(record)
old.pop("achievements"); old.pop("standing")
old["check"] = cargo._captain_check(old)
back = cargo.clean_captain(old)
expect(back["achievements"] == [] and back["standing"] == {"hansa": 0, "mandate": 0, "concord": 0},
       "a record without them (Cargo 1's) reads as none, standing 0")
expect(all(isinstance(t[2], dict) for t in cargo.ACHIEVEMENTS.values()), "every achievement is a story condition")

# ---- needles from outposts wait at the buoy ---------------------------------------------------
game, io = headless.new_game(cargo)
game.ship.money = 10 ** 6
outpost = cargo.DeepSpaceOutpost("DSO-Test", 7, 3, 20, "Stable")
game.current_location = outpost
there = next(loc for loc in game.locations if not game.same_system(loc, outpost))
game.turn = 10
expect(game.needle_wait() == 2, "from an outpost the next needle forms on a turn divisible by three")
io.queue.clear(); io.feed(["2"])
with headless.quiet() as buf:
    game.book_needle(there)
expect(game.turn == 12, "booking from an outpost waits for the needle: turn %d" % game.turn)
game.current_location = next(loc for loc in game.locations if type(loc).__name__ == "Planet")
expect(game.needle_wait() == 0, "planets have a needle every turn")

# ---- convoy fights ---------------------------------------------------------------------------
from game import tactics  # noqa: E402


class Dice:
    """The tactics module's dice, loaded: rolls below `edge` are the captain's."""
    def __init__(self, rolls):
        self.rolls = list(rolls)

    def random(self):
        return self.rolls.pop(0) if self.rolls else 0.5

    def randint(self, a, b):
        return a

    def choice(self, seq):
        return seq[0]


def convoy(enemy_id, answers, rolls, needle=True, modules=()):
    game, io = headless.new_game(cargo)
    game.ship.money, game.ship.attack, game.ship.defense = 50000, 6, 4
    game.ship.modules.extend({"kind": k, "condition": 100} for k in modules)
    game.in_needle = needle
    io.queue.clear(); io.feed(answers + [""] * 10)
    tactics.random = Dice(rolls)
    with headless.quiet() as buf:
        out = game.fight(enemy_id, 0, [])
    tactics.random = random
    return game, out, buf.getvalue(), io.asked


game, out, text, asked = convoy("corsair", ["1", "1"], [0.0, 0.0])
expect(out == "victory" and "round 2" in text and "round 3" not in text, "two rounds of focused fire beat a corsair wing")
expect("Screen the convoy" in text, "in a needle the convoy is there to screen")
game, out, text, asked = convoy("corsair", ["1"], [0.0, 0.0], needle=False)
expect("Screen the convoy" not in text, "inside a system there is no convoy to screen")
game, out, text, asked = convoy("corsair", ["1", "1"], [0.99, 0.99])
expect(out == "defeat" and game.standing_of("hansa") == -4, "losing in a needle costs the file two containers: %s" % game.standing_of("hansa"))
game, out, text, asked = convoy("corsair", ["2", "2", "2"], [0.0, 0.99, 0.0])
expect(out == "victory" and game.standing_of("hansa") == 3, "screening the file keeps it whole: %s" % game.standing_of("hansa"))
game, out, text, asked = convoy("corsair", ["3", "1", "1"], [0.99, 0.0, 0.0], modules=("shield",))
flat = " ".join(re.sub(r"[\u2500-\u259f|]", " ", text).split())
expect(out == "victory" and "their volley goes wide" in flat, "countermeasures make their round miss")
expect(text.count("Countermeasures") == 1, "countermeasures work once a fight")
game, out, text, asked = convoy("corsair", ["1", "3"], [0.0, 0.0])
expect("Board them" in text and out == "victory", "pirates down to their last mark can be boarded")
game, out, text, asked = convoy("corsair", ["2"], [0.0], needle=False)
expect(out == "escaped" and game.ship.combat_victories["total"] == 0, "breaking off gets away")
game, out, text, asked = convoy("skiff", ["1"], [], needle=True)
expect("round" not in text, "a skiff is still settled in one roll")
expect(abs(tactics.round_chance(0.6) ** 2 * (3 - 2 * tactics.round_chance(0.6)) - 0.6) < 1e-6,
       "a race of rounds is won as often as the fight's odds")

for problem in problems:
    print("FAIL", problem)
print("systems: %s" % ("ok" if not problems else "%d problems" % len(problems)))
sys.exit(1 if problems else 0)
