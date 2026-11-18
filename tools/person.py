#!/usr/bin/env python3
"""The captain as a person, apart from the ship (Cargo 3): the money, items and research points
are the captain's, a ship the captain owns spends and earns through them, and everything the
story and the records touch still works when there is no ship at all.

    python3 tools/person.py
"""
import os, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ["CARGO_SAGA_HOME"] = tempfile.mkdtemp(prefix="cargo3-person-")
import headless  # noqa: E402

cargo = headless.load(os.path.join(os.path.dirname(HERE), "game", "world.py"))
problems = []


def expect(ok, what):
    if not ok:
        problems.append(what)


# ---- the ship spends the owner's money ---------------------------------------------------------
game, io = headless.new_game(cargo, afloat=True)
person, ship = game.person, game.ship
expect(isinstance(person, cargo.Person) and ship.owner is person, "a captain with a ship owns it")
expect("money" not in ship.__dict__ and "items" not in ship.__dict__, "the ship keeps no money or items of its own")
person.money = 5000
expect(ship.money == 5000, "the ship's money is its owner's")
ship.money -= 1200
expect(person.money == 3800, "what the ship spends, the captain pays")
ship.acquire_item("auto_loader")
expect(person.items.get("auto_loader") == 1, "equipment bought for the ship is the captain's")
ship.research_points += 7
expect(person.research_points == 7, "research points are the captain's")
loose = cargo.Ship()
expect(loose.money == 1000 and loose.items == {} and loose.research_points == 0, "a ship without an owner keeps its own")

# ---- skills -------------------------------------------------------------------------------------
fresh = cargo.Person()
expect(set(fresh.skills) == set(cargo.SKILLS) and not any(fresh.skills.values()), "six skills, all at 0")
rose = [fresh.train("loader") for _ in range(3)]
expect(rose == [None, None, 1] and fresh.skill("loader") == 1, "three turns of practice make a level: %s" % rose)
for _ in range(200):
    fresh.train("loader")
expect(fresh.skill("loader") == cargo.SKILL_TOP, "a skill stops at the top")
expect(fresh.train("knitting") is None, "there is no such skill as knitting")
expect(fresh.best_skill() == "loader", "the best skill is the highest")

# ---- the story and the records without a ship ------------------------------------------------------
game, io = headless.new_game(cargo)
expect(game.ship is None, "a new game has no ship")
game.person.money = 2000
snap = game.story_snapshot()
expect(snap["stats"]["money"] == 2000 and snap["stats"]["hull_class"] == 0 and snap["sets"]["crew"] == [],
       "the story sees the captain's money and no ship")
with headless.quiet():
    game.story.apply({"money": 300, "research_points": 4, "give": {"items": ["keepsake"], "crew": ["gunner"]},
                      "cargo.tech": 20, "passenger_reputation": 5, "plot_points": 2})
expect(game.person.money == 2300 and game.person.research_points == 4 and game.person.items.get("keepsake") == 1,
       "story effects pay and give to the captain")
expect(sorted(game.story.shipless) == ["cargo.tech", "give", "passenger_reputation"],
       "what only a ship can take is noted, not done: %s" % getattr(game.story, "shipless", None))
for hook in ("damage 10", "repair 5", "crew joins gunner", "crew leaves gunner", "stow 5 crate as a crate",
             "unstow crate", "hull repaired at cost", "lose money 0.1 min 100", "take keepsake", "profit 500"):
    io.queue.clear()
    try:
        with headless.quiet():
            cargo.story_hook(game, hook)
    except Exception as error:                    # noqa: BLE001
        problems.append("story hook %r without a ship: %r" % (hook, error))
expect("keepsake" not in game.person.items, "'take' takes from the captain")
expect(game.person.money == 2300 - 230 + 500, "money hooks work on the captain: %s" % game.person.money)
req = cargo.MilestoneRequirements
expect(req._check_single_requirement("money", 2000, game), "a money requirement reads the captain")
expect(not req._check_single_requirement("combat_rating", 1, game), "a ship's requirement is not met without a ship")
record = game.captain_record()
expect(record["career"]["money"] == 2570 and record["ship"] == {"attack": 0, "defense": 0, "speed": 0},
       "the captain's record carries the money and no ship: %s" % record["ship"])
io.queue.clear(); io.feed([""] * 5)
try:
    with headless.quiet():
        game.story.journal()
except Exception as error:                        # noqa: BLE001
    problems.append("the journal without a ship: %r" % error)
expect(game.save_summary()["money"] == 2570, "a save names the captain's money")
with headless.quiet():
    game.save_game("shipless")
    loaded = cargo.load_game("shipless")
expect(loaded.ship is None and loaded.person.money == 2570, "a game without a ship saves and loads")

# ---- an older save: the ship's money becomes the captain's -------------------------------------------
game, io = headless.new_game(cargo, afloat=True)
ship = game.ship
ship.owner = None
ship.__dict__.update(money=4321, items={"combat_drone": 2}, research_points=11)
del game.person
summary = cargo.Game.save_summary
cargo.Game.save_summary = lambda self: {"player": self.player_name, "turn": self.turn}   # as it was then
try:
    with headless.quiet():
        game.save_game("older")
finally:
    cargo.Game.save_summary = summary
with headless.quiet():
    loaded = cargo.load_game("older")
expect(isinstance(loaded.person, cargo.Person) and loaded.person.money == 4321
       and loaded.person.items == {"combat_drone": 2} and loaded.person.research_points == 11,
       "an older save gives the captain the ship's money, items and research")
expect(loaded.ship.owner is loaded.person and "money" not in loaded.ship.__dict__, "and the ship is the captain's")

for problem in problems:
    print("FAIL", problem)
print("person: %s" % ("ok" if not problems else "%d problems" % len(problems)))
sys.exit(1 if problems else 0)
