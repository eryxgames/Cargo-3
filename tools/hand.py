#!/usr/bin/env python3
"""The able hand (Cargo 3's first chapters, game/hand.py): a new game has no ship; shifts pay
and train; the berths board, voyages worked to their end, passage and the locker; wounds and
death; the stats box without a ship; saves; and the moment the story gives a ship.

    python3 tools/hand.py
"""
import os, random, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ["CARGO_SAGA_HOME"] = tempfile.mkdtemp(prefix="cargo3-hand-")
os.environ["NO_COLOR"] = "1"
import headless  # noqa: E402

cargo = headless.load(os.path.join(os.path.dirname(HERE), "game", "world.py"))
problems = []


def expect(ok, what):
    if not ok:
        problems.append(what)


def at(game, name):
    game.current_location = game.location_named(name)
    return game.current_location


def screen(game, cols, show):
    size = os.terminal_size((cols, 40))
    old = shutil.get_terminal_size
    shutil.get_terminal_size = lambda fallback=(80, 24): size
    try:
        with headless.quiet() as out:
            show()
    finally:
        shutil.get_terminal_size = old
    return out.getvalue()


def widest(text):
    return max(cargo.visible_len(line) for line in text.splitlines())


# ---- a new game is on foot ------------------------------------------------------------------------
random.seed(3)
game, io = headless.new_game(cargo)
expect(game.ship is None and game.person.money == cargo.STARTING_PURSE, "Cargo 3 begins without a ship")
expect(game.story_snapshot()["stats"]["afloat"] == 0, "the story sees no ship")
for cols in (36, 50, 100):
    text = screen(game, cols, game.display_turn_info)
    expect(widest(text) <= cols, "the stats box fits %d columns (%d)" % (cols, widest(text)))
    flat = " ".join(text.split())
    for word in ("Turn: 0", "¤: %d" % cargo.STARTING_PURSE, "Chapter I", "Plot Points", game.current_location.name):
        expect(word in flat, "the stats box at %d columns shows %r" % (cols, word))
    expect("ATK" not in flat and "Hold" not in flat, "the stats box shows no ship at %d columns" % cols)
game.person.wounds = 30
game.person.locker = {"tech": 3}
flat = " ".join(screen(game, 36, game.display_turn_info).split())
expect("Wounds: 30% (hurt)" in flat and "Locker: 3/10" in flat, "wounds and the locker show when there are any")
game.person.wounds, game.person.locker = 0, {}

# ---- work ---------------------------------------------------------------------------------------------
sites = {name: [s["id"] for s in (at(game, name) and game.sites_here())] for name in ("Alpha", "Beta", "Gamma", "Delta")}
expect(sites == {"Alpha": ["ring"], "Beta": ["ring", "biomass"], "Gamma": ["ring", "mine"],
                 "Delta": ["ring", "hovertank", "biomass"]}, "work sites by place: %s" % sites)
at(game, "Delta")
expect(game.site_name(cargo.SITES[3]) == "Geod's Row", "Delta's farm drums are Geod's Row")
plant = cargo.SITES[1]
money, turn, points = game.person.money, game.turn, game.story_manager.plot_points
with headless.quiet():
    outcome = game.work_shift(plant, plant["jobs"][0], roll=0.0)
expect(outcome == "good" and game.person.money == money + 135, "a good shift pays half again: %s" % (game.person.money - money))
expect(game.person.practice["mechanic"] == 2 and game.turn == turn + 1, "a shift trains its skill and takes a turn")
expect(game.story_manager.plot_points == points + cargo.FIRST_SHIFT_POINTS, "a first shift at a site is worth plot points")
money, points = game.person.money, game.story_manager.plot_points
with headless.quiet():
    outcome = game.work_shift(plant, plant["jobs"][0], roll=0.999)
expect(outcome == "bad" and game.person.money == money + 45, "a bad shift pays half: %s" % (game.person.money - money))
expect(game.story_manager.plot_points == points and game.shifts == {"hovertank": 2}, "only the first shift is worth points")
game.person.skills["mechanic"] = 3
expect(game.shift_wage(90, "mechanic") == 145, "skill raises the wage: %s" % game.shift_wage(90, "mechanic"))
good, bad = game.shift_chances("mechanic")
expect(good > 0.5 and bad < 0.15, "skill makes good shifts likelier: %s %s" % (good, bad))

# ---- the berths board -----------------------------------------------------------------------------------
game, io = headless.new_game(cargo)
at(game, "Alpha")
game.turn = 0                                   # Ola Plumb's Level Best is at Alpha for turns 0-1
board = game.berths()
expect(board == game.berths(), "the board is the same each time it is looked at in a turn")
named = [o for o in board if o["who"] == "plumb"]
expect(named and named[0]["ship"] == "Level Best" and named[0]["to"] == "Beta" and named[0]["legs"] == 2,
       "Ola Plumb posts a berth to her next stop, Beta, two turns away: %s" % named)
expect(len(board) == 3 + sum(1 for o in board if o["who"]) and all(o["wage"] > 0 and o["legs"] >= 1 and o["to"] != "Alpha" for o in board),
       "a planet's board has three ships besides the named ones: %s" % [(o["ship"], o["to"]) for o in board])
expect(all(o["duty"] in cargo.KINDS[o["kind"]]["duties"] for o in board), "each ship hires for a duty of its kind")
game.turn = 1
expect([o for o in game.berths() if o["who"] == "plumb"][0]["legs"] == 1, "a turn later she leaves sooner")
game.turn = 2
expect(not [o for o in game.berths() if o["who"] == "plumb"], "and then she is gone")
text = screen(game, 36, lambda: (io.feed([""]), game.handle_berths()))
expect(widest(text) <= 36, "the board fits 36 columns")
for who in cargo.NAMED_SHIPS:
    expect(who in cargo.story_data()["characters"], "the berths captain %s is in the story" % who)

# ---- a voyage ---------------------------------------------------------------------------------------------
game, io = headless.new_game(cargo)
at(game, "Alpha")
game.turn = 0
offer = [o for o in game.berths() if o["who"] == "plumb"][0]
random.seed(5)
money, points = game.person.money, game.story_manager.plot_points
with headless.quiet():
    done = game.sail_with(offer, choices=["2"] * 8)
expect(game.current_location.name == "Beta" and game.turn == 2, "the voyage ends at Beta, two turns on")
expect(game.person.money == money + done["pay"] and done["pay"] > 0, "paid off on arrival")
expect(game.voyages == 1 and game.story_manager.plot_points >= points + cargo.VOYAGE_POINTS,
       "a voyage counts, and is worth plot points")
expect("Beta" in game.known_locations and "Beta" in game.discovered_locations, "the destination is known")
expect(sum(game.person.practice.values()) + sum(game.person.skills.values()) > 0, "duties train skills")
expect("plumb" in game.hand_regard, "the captain remembers the hand")
expect(game.story_snapshot()["stats"]["regard.plumb"] == game.hand_regard["plumb"], "the story sees her regard")
# a voyage given up half-way changes nothing
game, io = headless.new_game(cargo)
at(game, "Alpha")
game.turn = 0
offer = [o for o in game.berths() if o["who"] == "plumb"][0]
before = (game.person.money, game.turn, game.current_location.name, dict(game.person.practice), game.story_manager.plot_points)
asked = [0]
real_vi = cargo.Game.validate_input


def leave(self, *a, **k):
    asked[0] += 1
    if asked[0] == 2:
        raise EOFError
    return "2"


cargo.Game.validate_input = leave
try:
    with headless.quiet():
        game.sail_with(offer)
except EOFError:
    pass
finally:
    cargo.Game.validate_input = real_vi
after = (game.person.money, game.turn, game.current_location.name, dict(game.person.practice), game.story_manager.plot_points)
expect(before == after, "a voyage left half-way changes nothing: %s %s" % (before, after))
# bold duties: they pay more when they work, and hurt when they do not
game.person.skills["loader"] = 5
expect(game.duty_chance(0.4, "loader") == 0.9, "skill shows in the odds")
game.person.wounds = 50
expect(game.duty_chance(0.4, "loader") == 0.7, "wounds make the odds longer")

# ---- passage ---------------------------------------------------------------------------------------------
game, io = headless.new_game(cargo)
at(game, "Alpha")
game.known_locations = ["Alpha", "Gamma"]
fare, turns = game.passage_fare(game.location_named("Gamma"))
expect(fare == 2 * cargo.PASSAGE_FARE and turns == 1, "passage between the stars: %s" % fare)
game.person.money = fare - 1
with headless.quiet():
    expect(not game.take_passage(game.location_named("Gamma")) and game.current_location.name == "Alpha",
           "no passage without the fare")
game.person.money = 500
with headless.quiet():
    expect(game.take_passage(game.location_named("Gamma")), "passage booked")
expect(game.current_location.name == "Gamma" and game.person.money == 500 - fare and game.turn == 1,
       "passage takes the fare and a turn")

# ---- the locker -----------------------------------------------------------------------------------------
game, io = headless.new_game(cargo)
place = at(game, "Gamma")
game.person.money = 5000
with headless.quiet():
    expect(game.locker_buy("tech", 6) and game.person.locker == {"tech": 6}, "six tech into the locker")
    game.locker_buy("agri", 9)
expect(game.person.locker_units() == cargo.LOCKER_UNITS, "the locker holds ten units: %s" % game.person.locker)
paid = game.person.locker_cost["tech"]
at(game, "Beta")
money = game.person.money
with headless.quiet():
    expect(game.locker_sell("tech", 6), "sold at Beta")
expect("tech" not in game.person.locker and game.person.money > money + paid, "a profit: %s" % (game.person.money - money - paid))
expect(game.locker_profit > 0 and game.story_snapshot()["stats"]["locker_profit"] == game.locker_profit,
       "the story sees the locker's profit")
place = at(game, "Alpha")
place.banned_commodities.append("agri")
with headless.quiet():
    expect(not game.locker_sell("agri", 4), "a banned good does not sell")
place.banned_commodities.remove("agri")

# ---- wounds, rest and death -----------------------------------------------------------------------------
game, io = headless.new_game(cargo)
at(game, "Alpha")
game.person.wounds = 85
random.seed(1)
for _ in range(6):
    with headless.quiet():
        game.work_shift(cargo.SITES[0], cargo.SITES[0]["jobs"][0], roll=0.999)
expect(game.person.wounds <= cargo.WOUNDS_DOWN, "a bad shift puts a captain down, never further: %s" % game.person.wounds)
game.turn = 0
offer = [o for o in game.berths() if o["who"] == "plumb"][0]
game.person.wounds = 85
random.seed(2)
with headless.quiet():
    done = game.sail_with(offer, choices=["1"] * 8)
expect(game.person.wounds <= cargo.WOUNDS_DOWN and done["wounds"] <= 5,
       "a bold duty puts a hand down, never further: %s" % game.person.wounds)
game, io = headless.new_game(cargo)
game.person.wounds = 40
game.pass_turns(1)
expect(game.person.wounds == 38, "wounds heal with time")
game.pass_turns(1, resting=True)
expect(game.person.wounds == 28, "and faster with rest")
game.person.wounds = 100
io.queue.clear()
io.feed(["sk", ""] + [""] * 10)
with headless.quiet() as out:
    game.play()
expect("Game Over" in out.getvalue() and "is dead" in out.getvalue(), "a captain at 100 wounds is dead, and the game is over")

# ---- every hand screen at 36 columns -------------------------------------------------------------------
game, io = headless.new_game(cargo)
at(game, "Delta")
game.person.locker = {"tech": 2}
game.person.locker_cost = {"tech": 100}
game.hand_regard = {"plumb": 3}
for name, show, answers in (("work", game.handle_work, [""]), ("passage", game.handle_passage, [""]),
                            ("locker", game.handle_locker, [""]), ("skills", game.show_person, [""]),
                            ("help", game.show_hand_help, [""])):
    io.queue.clear()
    text = screen(game, 36, lambda: (io.feed(answers), show()))
    expect(widest(text) <= 36, "the %s screen fits 36 columns (%d)" % (name, widest(text)))
expect("Would sign you again: Ola Plumb" in " ".join(screen(game, 80, lambda: (io.feed([""]), game.show_person())).split()),
       "the skills screen names captains who would sign you again")

# ---- what was just shown stays until it is read ---------------------------------------------------------
game, io = headless.new_game(cargo)
at(game, "Alpha")
io.asked.clear(); io.queue.clear()
with headless.quiet():
    game.display_hand_info()
expect(io.asked == ["Press Enter to continue..."], "the opening's text waits to be read: %s" % io.asked)
io.asked.clear()
with headless.quiet():
    game.display_hand_info()
expect(not io.asked, "a turn with nothing new to read does not wait")
with headless.quiet():
    game.work_shift(cargo.SITES[0], cargo.SITES[0]["jobs"][0], roll=0.5)
    game.display_hand_info()
expect(io.asked == ["Press Enter to continue..."], "after a shift the result waits for Enter before the screen clears: %s" % io.asked)
io.asked.clear()
io.feed(["1"])
with headless.quiet():
    game.display_simple_message("Prompt", 0)
    game.validate_input("Pick: ", ["1"])
    game.display_hand_info()
expect(io.asked == [">>> "], "an answered prompt needs no extra Enter: %s" % io.asked)

# ---- saved on foot, and given a ship ----------------------------------------------------------------------
game, io = headless.new_game(cargo)
game.person.skills["broker"] = 2
game.person.locker = {"agri": 4}
game.shifts = {"ring": 3}
with headless.quiet():
    game.save_game("onfoot")
    loaded = cargo.load_game("onfoot")
expect(loaded.ship is None and loaded.person.skills["broker"] == 2 and loaded.person.locker == {"agri": 4}
       and loaded.shifts == {"ring": 3}, "a game on foot saves and loads")
money = loaded.person.money
ship = loaded.give_ship(hull=1, name="Second Chance")
expect(loaded.ship is ship and ship.owner is loaded.person and ship.money == money and ship.hull == 1,
       "a ship given by the story is the captain's, and spends the captain's money")
expect(loaded.story_snapshot()["stats"]["afloat"] == 1, "the story sees the ship")
io.queue.clear()
with headless.quiet() as out:
    loaded.display_turn_info()
expect("ATK" in out.getvalue(), "with a ship, the stats box is a captain's")

for problem in problems:
    print("FAIL", problem)
print("hand: %s" % ("ok" if not problems else "%d problems" % len(problems)))
sys.exit(1 if problems else 0)
