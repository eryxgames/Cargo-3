#!/usr/bin/env python3
"""Act 1 on foot, played for every kind of captain: who they are now (the intro), why they have
no ship (the two reasons that fit their record, and what each does), the hiring hall, the work
sites seen from the floor, the berths captains, and the first old friend, which ends chapter I.

    python3 tools/act1.py
"""
from storytest import cargo, expect, flat, play, problems, record, start, unfilled

CAPTAINS = {    # name: (record, the intro it gets, the reasons it is offered)
    "fresh": (None, "intro.fresh", {"zero", "rockwardens"}),
    "Cargo 1, the Conte and the Rockwardens": (record("cargo1", "discovery", ["neon_sleeper_carried", "rockwarden_share"]),
                                               "intro.from_cargo1", {"slept", "rockwardens"}),
    "Cargo 1, the Conte": (record("cargo1", "combat", ["neon_land"]), "intro.from_cargo1", {"slept", "pod"}),
    "Cargo 1, the Rockwardens": (record("cargo1", "discovery", ["aela_member"]), "intro.from_cargo1", {"rockwardens", "pod"}),
    "Cargo 1, a founder": (record("cargo1", "trade"), "intro.founder", {"pod", "rockwardens"}),
    "Cargo 1, Serac's colonel": (record("cargo1", "combat", ["took_the_commission"]), "intro.colonel", {"pod", "rockwardens"}),
    "Cargo 2": (record("cargo2", "trade"), "intro.from_cargo2", {"impounded", "pod"}),
    "Cargo 2, the Rockwardens' books": (record("cargo2", "combat", ["rockwarden_books"]), "intro.from_cargo2",
                                        {"impounded", "rockwardens"}),
    "Cargo 3, again": (record("cargo3"), "intro.again", {"impounded", "pod"}),
}
MONEY = {"zero": 0, "impounded": 200, "rockwardens": 0, "pod": 150, "slept": -100}
nodes = cargo.story_data()["nodes"]
opening = nodes["opening.ship"]


def offered(game):
    snap = game.story.snapshot()
    return {c["id"] for c in opening["choices"] if game.story.check(c.get("requires"), snap)}


# ---- who you are now, and why there is no ship -------------------------------------------------------
seen = set()
for name, (rec, intro, reasons) in CAPTAINS.items():
    game, io, text = start(rec)
    expect(game.ship is None, "%s: no ship" % name)
    expect(intro in game.story.done, "%s: the intro is %s (%s)" % (name, intro, sorted(n for n in game.story.done if n.startswith("intro"))))
    expect(not unfilled(text), "%s: the opening leaves %s unfilled" % (name, unfilled(text)))
    got = offered(game)
    expect(got == reasons, "%s: offered %s, not %s" % (name, sorted(got), sorted(reasons)))
    order = [c["id"] for c in opening["choices"] if c["id"] in got]
    for number, reason in enumerate(order, 1):
        game, io, _ = start(rec)
        money = game.person.money
        shown = flat(play(game, io, "opening.ship", answer=str(number)))
        expect(game.story_manager.story_states.get("reason_" + reason), "%s: choosing %s sets its flag" % (name, reason))
        expect(game.person.money == money + MONEY[reason], "%s: %s leaves %s credits" % (name, reason, game.person.money))
        expect("opening." + reason in game.story.done, "%s: %s tells what happened" % (name, reason))
        expect(not unfilled(shown), "%s: %s leaves %s unfilled" % (name, reason, unfilled(shown)))
        seen.add(reason)
expect(seen == set(MONEY), "every reason is offered to somebody: %s" % sorted(seen))

# ---- the hiring hall, and a thought for the way there -----------------------------------------------
game, io, _ = start(None)
play(game, io, "opening.ship", answer="1")
points = game.story_manager.plot_points
text = flat(play(game, io, "hall.first"))
expect("berths board" in text and game.story_manager.plot_points == points + 2, "the hiring hall is introduced")
snap = game.story.snapshot()
thoughts = {nid for nid, n in nodes.items() if n.get("kind") == "thought" and game.story.check(game.story.requires_of(n), snap)}
expect({"thought.first_work", "thought.find_adit", "thought.reason_zero"} <= thoughts, "the first thoughts: %s" % sorted(thoughts))

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

# ---- the first old friend ------------------------------------------------------------------------------------
adit = nodes["friends.adit"]
for rec, words in ((record("cargo2", "trade", ["loader_patch"]), "USE NO HOOKS"),
                   (record("cargo2", "trade"), "Beta, 2460"),
                   (record("cargo1", "trade"), "always square"),
                   (None, "You will last")):
    game, io, _ = start(rec)
    play(game, io, "opening.ship", answer="2")
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
    with __import__("headless").quiet():
        game.story_manager.check_milestone_progress()
        game.story_manager.check_chapter_progress()
    expect(game.story_manager.current_chapter == "ch2", "chapter I ends with the first old friend: %s"
           % game.story_manager.current_chapter)
game, io, _ = start(None)
play(game, io, "opening.ship", answer="1")
game.shifts = {"ring": 2}
game.turn = 0
game.current_location = game.location_named("Beta")
snap = game.story.snapshot()
expect([c["id"] for c in adit["choices"] if game.story.check(c.get("requires"), snap)] == ["who", "work"],
       "a captain who never had a ship does not ask about it")
loader = game.person.skill("loader")
play(game, io, "friends.adit", answer="2", where="Beta")
expect(game.person.skill("loader") == loader + 1 and "friends.adit_work" in game.story.done,
       "working beside Adit makes a better loader")
for reason, answer, words in (("impounded", "1", "Yard nine"), ("pod", "2", "Salvage has an owner")):
    game, io, _ = start(record("cargo2", "trade"))
    play(game, io, "opening.ship", answer=answer)
    game.turn = 0
    text = flat(play(game, io, "friends.adit", answer="1", where="Beta"))
    expect(words in text and game.story_manager.story_states.get("adit_on_the_ship"),
           "Adit finds out about a ship that was %s" % reason)

print("act 1: %s" % ("ok" if not problems[0] else "%d problems" % problems[0]))
raise SystemExit(1 if problems[0] else 0)
