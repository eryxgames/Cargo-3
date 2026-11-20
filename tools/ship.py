#!/usr/bin/env python3
"""Chapter III, A Bridge Again (story/cargo3/ship.json): the captain's ship out of the Mandate's
yard by each way (Serac, the Rockwarden envoy, the time broker, the salvage court, the night and
the auction), what each costs and gives (working capital, so nobody starts afloat broke), the
name, the first run each way sends the ship on, Scholz's Star, the Builder Site, the chapter's
milestones, and the captain's turn that follows. Every scene is played at 36 columns.

    python3 tools/ship.py
"""
import os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from storytest import cargo, expect, flat, play, problems, record, start  # noqa: E402

SIZE = os.terminal_size((36, 40))
shutil.get_terminal_size = lambda fallback=(80, 24): SIZE
os.get_terminal_size = lambda *a: SIZE
nodes = cargo.story_data()["nodes"]
screens = []


def ready(rec=None, money=900, **flags):
    """A hand in chapter III, who knows which hull is theirs."""
    game, io, _ = start(rec)
    play(game, io, "opening.pod")
    play(game, io, "hall.first")
    sm = game.story_manager
    sm.story_states.update(first_friend=True, ship_truth=True)
    sm.story_states.update(flags)
    sm.current_chapter = "ch3"
    game.person.money = money
    game.current_location = game.location_named("Alpha")
    return game, io


def flag(game, name):
    return bool(game.story_manager.story_states.get(name))


def choice_ids(game, nid):
    snap = game.story.snapshot()
    return [c["id"] for c in nodes[nid].get("choices") or [] if game.story.check(c.get("requires"), snap)]


def pick(game, nid, cid):
    return str(choice_ids(game, nid).index(cid) + 1)


def scene(game, io, nid, answers, where=None):
    """A scene with its answers in turn (the way, then the name; Enter after that)."""
    plain = io.feed
    io.feed = lambda items: plain(list(answers) + [""] * 12)
    try:
        text = play(game, io, nid, answers[0], where)
    finally:
        io.feed = plain
    screens.append((nid, text))
    return flat(text)


def fights(game, win):
    plain = game.brawl
    game.ask_move = lambda title, lines, options, default: "strike"
    game.brawl_odds = lambda *a, **k: 1.0 if win else 0.0
    game.foe_hit_chance = lambda *a, **k: 0.0 if win else 1.0
    game.brawl = lambda foe, edge=0, **k: plain(foe, edge=edge, rolls=[0.0 if win else 0.99] * 60)


def thoughts(game):
    snap = game.story.snapshot()
    return [n for n, node in nodes.items() if node.get("kind") == "thought" and game.story.check(game.story.requires_of(node), snap)]


def yard(game):
    game.current_location = game.location_named("Alpha")
    return "ship.yard" in game.sights_here()


# ---- the yard ----------------------------------------------------------------------------------------------
game, io = ready()
game.story_manager.story_states["ship_truth"] = False
expect(not yard(game) and "thought.ship_where" in thoughts(game), "without the truth, no yard: a thought points at CU-113")
game, io = ready()
expect(yard(game) and "thought.ship_yard" in thoughts(game), "with it, the hull in the yard at Alpha")
expect(choice_ids(game, "ship.yard") == ["leave"], "with nothing to get it out with, not yet")
game, io = ready(money=30000, serac_offer=True, envoy_heard=True, broker_card=True, papers_in_order=True,
                 vouched_for=True, debt_called_in=True, navigator_key=True)
expect(choice_ids(game, "ship.yard") == ["serac", "envoy", "broker", "court", "night", "auction", "leave"],
       "every way, when every door is open: %s" % choice_ids(game, "ship.yard"))
game.story_manager.current_chapter = "ch2"
expect(not yard(game), "the yard is chapter III's")

# ---- Serac --------------------------------------------------------------------------------------------------
game, io = ready(serac_offer=True)
text = scene(game, io, "ship.yard", [pick(game, "ship.yard", "serac"), "1"], "Alpha")
expect(game.ship is not None and game.ship.name == "Late Arrival" and game.ship.hull == 0, "Serac's way: a ship, named")
expect(game.person.money == 3900 and game.ship.special_cargo == {"serac_container": 20}, "3,000 for expenses; his container")
expect("has not aged a day" in text and "DSO-Gamma is on your charts" in text and "Late Arrival is yours" in text,
       "the release, the run, the name in the text")
expect("DSO-Gamma" in game.known_locations and flag(game, "run_serac") and not yard(game), "and the yard is behind you")
expect("thought.scholz" in thoughts(game), "a thought for the run")
game, io = ready(record("cargo1", flags=["took_the_commission"]), serac_offer=True)
text = scene(game, io, "ship.yard", ["1", "3"], "Alpha")
expect("pinned your commission on" in text and game.ship.name == "Nameless", "an old colonel; a ship left nameless")

# ---- the Rockwarden envoy --------------------------------------------------------------------------------------
game, io = ready(envoy_heard=True, vouched_for=True)
text = scene(game, io, "ship.yard", [pick(game, "ship.yard", "envoy"), "2"], "Alpha")
expect(game.ship.hull == 1 and game.ship.name == "Second Chance" and game.person.money == 4900,
       "the family buys it, plates it as an Ironback, advances 4,000")
expect(game.ship.special_cargo == {"stonewright_stores": 40} and "Stonewright is coming home" in text, "stores for Stonewright")

# ---- the time broker ----------------------------------------------------------------------------------------
game, io = ready(money=6500, broker_card=True)
expect("broker" in choice_ids(game, "ship.yard") and "account" not in choice_ids(game, "ship.yard"), "a fresh captain's bonds")
text = scene(game, io, "ship.yard", [pick(game, "ship.yard", "broker")], "Alpha")
expect(game.ship is not None and game.person.money == 2500 and "great-aunt" in text and flag(game, "run_own"),
       "6,000 on top, 2,000 of interest back; no strings")
game, io = ready(record("cargo2"), money=3000, broker_card=True)
text = scene(game, io, "ship.yard", [pick(game, "ship.yard", "account")], "Alpha")
expect(game.ship is not None and game.person.money == 2000 and "a century old" in text, "a captain's old account: 3,000")

# ---- the salvage court ------------------------------------------------------------------------------------------
game, io = ready(money=2500, papers_in_order=True, vouched_for=True)
text = scene(game, io, "ship.yard", [pick(game, "ship.yard", "court")], "Alpha")
expect(game.ship is not None and game.person.money == 3500 and "cooperative vouches" in text,
       "papers, the keel log and the cooperative's word: 2,000, and 3,000 storage back")
game, io = ready(money=4500, papers_in_order=True)
expect(choice_ids(game, "ship.yard") == ["advocate", "leave"], "without the cooperative, an advocate")
text = scene(game, io, "ship.yard", ["1"], "Alpha")
expect(game.ship is not None and game.person.money == 3500 and "objects to everything" in text, "4,000")

# ---- at night ---------------------------------------------------------------------------------------------------
game, io = ready(debt_called_in=True, navigator_key=True)
fights(game, win=False)
text = scene(game, io, "ship.yard", [pick(game, "ship.yard", "night")], "Alpha")
expect(game.ship is None and "another night" in text and not flag(game, "night_tried"), "caught by the night watch")
fights(game, win=False)
text = scene(game, io, "ship.yard", [pick(game, "ship.yard", "night")], "Alpha")
expect(game.ship is None and "another night" in text, "and again, another night")
fights(game, win=True)
text = scene(game, io, "ship.yard", [pick(game, "ship.yard", "night")], "Alpha")
expect(game.ship is not None and flag(game, "mandate_wants_it") and game.ship.cargo["agri"] == 150
       and "A START" in text, "out on the jets: the Rootstock's seed stock and a thousand in the hold")

# ---- the auction ------------------------------------------------------------------------------------------------
game, io = ready(money=26000)
text = scene(game, io, "ship.yard", [pick(game, "ship.yard", "auction")], "Alpha")
expect(game.ship is not None and game.person.money == 1000 and "spanner" in text, "25,000 at auction")

# ---- Scholz's Star ----------------------------------------------------------------------------------------------
for answer, flags_after, money in (("sealed", ("serac_trusts",), 9900), ("open", ("opened_serac_box",), 3900)):
    game, io = ready(serac_offer=True)
    scene(game, io, "ship.yard", ["1", "1"], "Alpha")
    text = scene(game, io, "ship.scholz", [pick(game, "ship.scholz", answer)], "DSO-Gamma")
    expect(flag(game, "first_run_done") and all(flag(game, f) for f in flags_after) and game.person.money == money
           and not game.ship.special_cargo and "Builder Site" in game.known_locations,
           "Serac's container, %s: %s" % (answer, game.person.money))
    if answer == "open":
        expect("a receiver tuned to a single frequency" in text, "a receiver for the beacon")
    else:
        expect("transponder blinks" in text, "the transponder is pleased")
game, io = ready(envoy_heard=True, vouched_for=True)
scene(game, io, "ship.yard", ["1", "1"], "Alpha")
text = scene(game, io, "ship.scholz", ["1"], "DSO-Gamma")
expect("Maret Rockwarden" in text and "Anselm Rockwarden" in text and flag(game, "stonewright_met") and game.person.money == 8900,
       "Stonewright comes home with Anselm's granddaughter in command")
game, io = ready(money=26000)
scene(game, io, "ship.yard", ["1"], "Alpha")
text = scene(game, io, "ship.scholz", ["1"], "DSO-Gamma")
expect("a Bushing, the third of that name" in text and flag(game, "first_run_done"), "your own run: the quartermaster")
game, io = ready(record("cargo1", ending="discovery"), money=26000)
text = scene(game, io, "ship.yard", ["1"], "Alpha")
expect("you filed a course home from Scholz's Star" in text, "the course filed in 2420, read at last")

# ---- the Builder Site, and the chapters ---------------------------------------------------------------------------------
game, io = ready(money=26000)
sm = game.story_manager
ship_ms, run_ms = sm.chapters["ch3"].milestones["ship"], sm.chapters["ch3"].milestones["run"]
expect(not ship_ms.check_completion(game), "no ship yet")
scene(game, io, "ship.yard", ["1"], "Alpha")
expect(ship_ms.check_completion(game) and not run_ms.check_completion(game), "a ship again: the first milestone")
scene(game, io, "ship.scholz", ["1"], "DSO-Gamma")
expect(run_ms.check_completion(game), "the first run: the second")
text = scene(game, io, "ship.builder_site", ["1"], "Builder Site")
expect("points at an empty patch of sky" in text and flag(game, "reached_builder_site")
       and sm.chapters["ch4"].milestones["site"].check_completion(game), "the segment: chapter IV's first step")

# the captain's turn from here (game/world.py play_turn): the hand's commands are gone
game, io = ready(money=26000)
scene(game, io, "ship.yard", ["1"], "Alpha")
asked = []
game.validate_input = lambda prompt, valid, *a, **k: asked.append(sorted(valid)) or "end"
with open(os.devnull, "w") as sink:
    old, sys.stdout = sys.stdout, sink
    try:
        game.play_hand_turn()
    finally:
        sys.stdout = old
expect(not asked, "a captain with a ship has no hand's turn")

# Serac's men and the broker's clerk still come while the ship is in the yard, not after
game, io = ready(navigator_key=True, vouched_for=True)
snap = game.story.snapshot()
expect(game.story.check(game.story.requires_of(nodes["closing.serac"]), snap), "Serac's men come in chapter III too")

game.give_ship()
expect(not game.story.check(game.story.requires_of(nodes["closing.serac"]), game.story.snapshot()), "not once you have a ship")

# ---- every scene fits 36 columns ------------------------------------------------------------------------------------
wide = [(nid, max(cargo.visible_len(line) for line in text.splitlines())) for nid, text in screens if text.strip()]
expect(all(width <= 36 for _, width in wide), "every scene fits 36 columns: %s" % [w for w in wide if w[1] > 36])
print("ship: %d scenes played, %s" % (len(screens), "ok" if not problems[0] else "%d problems" % problems[0]))
sys.exit(1 if problems[0] else 0)
