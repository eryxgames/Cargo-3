#!/usr/bin/env python3
"""Act 1 on foot, played for every kind of captain: who they are now (the intro), the needle
that threw them out into a pod (one story for all, told for each record), the hiring hall, the
work sites seen from the floor, the berths captains, and the first old friend, which ends
chapter I.

    python3 tools/act1.py
"""
from storytest import cargo, expect, flat, play, problems, record, start, unfilled

CAPTAINS = {    # name: (record, the intro it gets, words of how the needle shed them)
    "fresh": (None, "intro.fresh", "nineteen years"),
    "Cargo 1, the Rockwardens": (record("cargo1", "discovery", ["aela_member"]), "intro.from_cargo1", "Rockwarden prospector"),
    "Cargo 1, the Conte": (record("cargo1", "combat", ["neon_land"]), "intro.from_cargo1", "early needles"),
    "Cargo 1, a founder": (record("cargo1", "trade"), "intro.founder", "early needles"),
    "Cargo 1, Serac's colonel": (record("cargo1", "combat", ["took_the_commission"]), "intro.colonel", "early needles"),
    "Cargo 2": (record("cargo2", "trade"), "intro.from_cargo2", "seventy-three years"),
    "Cargo 2, needle-talk": (record("cargo2", "combat", ["needle_talk"]), "intro.from_cargo2", "said something in needle-talk"),
    "Cargo 3, again": (record("cargo3"), "intro.again", "shed you again"),
}
nodes = cargo.story_data()["nodes"]

# ---- who you are now, and the needle ----------------------------------------------------------------
for name, (rec, intro, words) in CAPTAINS.items():
    game, io, text = start(rec)
    expect(game.ship is None and game.person.money == cargo.STARTING_PURSE, "%s: no ship, %s credits" % (name, cargo.STARTING_PURSE))
    expect(intro in game.story.done, "%s: the intro is %s (%s)" % (name, intro, sorted(n for n in game.story.done if n.startswith("intro"))))
    expect(not unfilled(text), "%s: the opening leaves %s unfilled" % (name, unfilled(text)))
    expect(game.story.check(game.story.requires_of(nodes["opening.pod"]), game.story.snapshot()),
           "%s: the needle's story comes on the first turn" % name)
    shown = flat(play(game, io, "opening.pod"))
    expect(words in shown and ("did not come with you" in shown or "never does" in shown),
           "%s: the needle shed them (%r)" % (name, words))
    expect(game.story_manager.story_states.get("the_pod") and game.person.money == cargo.STARTING_PURSE,
           "%s: the pod, and the salvager's three hundred credits" % name)
    expect(not unfilled(shown), "%s: the needle leaves %s unfilled" % (name, unfilled(shown)))
game, io, _ = start(None)
game.turn = 1
expect(not game.story.check(game.story.requires_of(nodes["opening.pod"]), game.story.snapshot()), "the needle is told only at the start")

# ---- the hiring hall, and a thought for the way there -----------------------------------------------
game, io, _ = start(None)
play(game, io, "opening.pod")
points = game.story_manager.plot_points
text = flat(play(game, io, "hall.first"))
expect("berths board" in text and game.story_manager.plot_points == points + 2, "the hiring hall is introduced")
snap = game.story.snapshot()
thoughts = {nid for nid, n in nodes.items() if n.get("kind") == "thought" and game.story.check(game.story.requires_of(n), snap)}
expect({"thought.first_work", "thought.find_adit", "thought.the_pod"} <= thoughts, "the first thoughts: %s" % sorted(thoughts))

# ---- the floor -------------------------------------------------------------------------------------------
for site, nid, flag, words in (("hovertank", "floor.hovertank", "delivered_the_hovertank", "mind the skirt"),
                               ("hovertank", "floor.hovertank", "sold_the_hovertank", "colonel's tank"),
                               ("mine", "floor.mine", "saved_level_nine", "for the hauler"),
                               ("mine", "floor.mine", "aela_member", "share badge"),
                               ("biomass", "floor.biomass", "first_node", "Nodes remember"),
                               ("biomass", "floor.biomass", "geod_fields", "given by a hauler"),
                               ("biomass", "floor.biomass", None, "nobody tends the people")):
    game, io, _ = start(record("cargo1", "trade", [flag]) if flag else None)
    expect(not game.story.check(game.story.requires_of(nodes[nid]), game.story.snapshot()), "%s waits for a shift" % nid)
    game.shifts = {site: 1}
    text = flat(play(game, io, nid, where="Delta"))
    expect(words in text, "%s with %s says %r" % (nid, flag or "no record", words))

# ---- the captains who hire hands -----------------------------------------------------------------------
for who in cargo.NAMED_SHIPS:
    game, io, _ = start(None)
    route = cargo.story_data()["characters"][who]["route"]
    game.turn = next(t for t in range(60) if game.story.where_is(who, t) == route["places"][0])
    text = flat(play(game, io, "hands." + who, where=route["places"][0]))
    expect(game.story.fill("{%s}" % who) in text, "the captain of the %s talks" % cargo.NAMED_SHIPS[who][0])
game, io, _ = start(record("cargo1", "combat", ["took_the_commission"]))
game.turn = 0
expect("stops saluting" in flat(play(game, io, "hands.caspic", where="Alpha")), "Caspic reads a colonel's file")
game, io, _ = start(None)
game.turn = next(t for t in range(60) if game.story.where_is("caboose", t) == "Beta")
text = flat(play(game, io, "hands.caboose", where="Beta"))
expect("Caboose-237" in text and "Officer Deks" in text, "Brother Caboose's papers and his old name")

# ---- the first old friend ------------------------------------------------------------------------------------
adit = nodes["friends.adit"]
for rec, words in ((record("cargo2", "trade", ["loader_patch"]), "USE NO HOOKS"),
                   (record("cargo2", "trade"), "Beta, 2460"),
                   (record("cargo1", "trade"), "always square"),
                   (None, "You will last")):
    game, io, _ = start(rec)
    play(game, io, "opening.pod")
    game.turn = 0                                   # Adit is at Beta on turns 0 and 1
    if rec is None:
        game.current_location = game.location_named("Beta")
        expect(not game.story.check(game.story.requires_of(adit), game.story.snapshot()),
               "a stranger has to work the ring before Adit talks")
        game.shifts = {"ring": 2}
    game.story_manager.plot_points = 40
    text = flat(play(game, io, "friends.adit", answer="1", where="Beta"))
    expect(words in text, "Adit greets %s with %r" % ((rec or {}).get("origin", {}).get("game", "a fresh captain"), words))
    expect(game.story_manager.story_states.get("first_friend"), "talking to Adit finds the first old friend")
    expect("never came out" in text and game.story_manager.story_states.get("ship_never_came_out"),
           "Adit's lists: the ship never came out of the needle")
    with __import__("headless").quiet():
        game.story_manager.check_milestone_progress()
        game.story_manager.check_chapter_progress()
    expect(game.story_manager.current_chapter == "ch2", "chapter I ends with the first old friend: %s"
           % game.story_manager.current_chapter)
game, io, _ = start(record("cargo2", "combat", ["needle_talk"]))
game.turn = 0
expect("what the needle said" in flat(play(game, io, "friends.adit", answer="1", where="Beta")),
       "a captain who speaks needle-talk is sent to ask Korai what the needle said")
game, io, _ = start(None)
play(game, io, "opening.pod")
game.shifts = {"ring": 2}
game.turn = 0
game.current_location = game.location_named("Beta")
snap = game.story.snapshot()
expect([c["id"] for c in adit["choices"] if game.story.check(c.get("requires"), snap)] == ["ship", "who", "work"],
       "Adit can be asked about the ship, about who is alive, or worked beside")
loader = game.person.skill("loader")
play(game, io, "friends.adit", answer="3", where="Beta")
expect(game.person.skill("loader") == loader + 1 and "friends.adit_work" in game.story.done,
       "working beside Adit makes a better loader")

print("act 1: %s" % ("ok" if not problems[0] else "%d problems" % problems[0]))
raise SystemExit(1 if problems[0] else 0)
