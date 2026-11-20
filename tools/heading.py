#!/usr/bin/env python3
"""Chapters IV to VI and the endings (story/cargo3/heading.json, the frame in main.json): the beacon
and each way to record the beat, the midpoint, Serac's copy, the Mandate's cutter, Stonewright's
escort, the long leg (nineteen years: {year}), the Stator Field; who holds the segments (by Cargo 2's
ending), the five claims and the side taken, Serac's move and the low point (thirty-eight years);
the allies and what each needs, the restart's three choices, the three endings through the
chapters, the epilogue and the record. The fixed point holds: nobody is ever said to have
restarted the ring. Every scene is played at 36 columns.

    python3 tools/heading.py
"""
import os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from storytest import cargo, expect, flat, play, problems, record, start  # noqa: E402
from headless import quiet  # noqa: E402

SIZE = os.terminal_size((36, 40))
shutil.get_terminal_size = lambda fallback=(80, 24): SIZE
os.get_terminal_size = lambda *a: SIZE
nodes = cargo.story_data()["nodes"]
screens = []


def ready(chapter="ch4", rec=None, money=50000, **flags):
    """A captain with a ship, in this chapter, with the earlier chapters' flags."""
    game, io, _ = start(rec)
    play(game, io, "opening.pod")
    play(game, io, "hall.first")
    game.give_ship()
    sm = game.story_manager
    sm.story_states.update(first_friend=True, ship_truth=True, first_run_done=True, reached_builder_site=True)
    sm.story_states.update(flags)
    sm.current_chapter = chapter
    for done in ("ch1", "ch2", "ch3", "ch4", "ch5")[:("ch1", "ch2", "ch3", "ch4", "ch5", "ch6").index(chapter)]:
        sm.chapters[done].completed = True
        sm.completed_chapters.add(done)
    game.person.money = money
    for place in ("Builder Site", "Stator Field Megastructure", "DSO-Gamma"):
        with quiet():
            game.reveal_place(place)
    return game, io


def flag(game, name):
    return bool(game.story_manager.story_states.get(name))


def choice_ids(game, nid):
    snap = game.story.snapshot()
    return [c["id"] for c in nodes[nid].get("choices") or [] if game.story.check(c.get("requires"), snap)]


def pick(game, nid, cid):
    return str(choice_ids(game, nid).index(cid) + 1)


def scene(game, io, nid, answers=("1",), where=None):
    plain = io.feed
    io.feed = lambda items: plain(list(answers) + [""] * 12)
    try:
        text = play(game, io, nid, answers[0], where)
    finally:
        io.feed = plain
    screens.append((nid, text))
    return flat(text)


def holds(game, nid):
    return game.story.check(game.story.requires_of(nodes[nid]), game.story.snapshot())


def sights(game, place):
    game.current_location = game.location_named(place)
    return game.sights_here()


def stat(game, name):
    return game.story_snapshot()["stats"][name]


# ---- IV. The Heading -------------------------------------------------------------------------------------
game, io = ready(money=100)
expect("h4.beacon" in sights(game, "Builder Site"), "the beacon at the Builder Site")
expect(choice_ids(game, "h4.beacon") == ["leave"], "with nothing to record it with, only watching")
game, io = ready(navigator_key=True)
game.person.items["vertex_array"] = 1
game.person.research_points = 200
expect(choice_ids(game, "h4.beacon") == ["array", "count", "sensors", "recorder", "leave"], "every way, when every way is open")
text = scene(game, io, "h4.beacon", ["1"], "Builder Site")
expect(flag(game, "array_fitted") and "like a key in a lock" in text and "Only one person has ever carried both" in text,
       "the Vertex Array fits the beacon: a hint, never an answer")
expect(flag(game, "midpoint_known") and "Stator Field Megastructure" in game.known_locations and "cannot turn" in text,
       "the midpoint: the ring cannot turn without the segment, or its timing")
game, io = ready(navigator_key=True)
text = scene(game, io, "h4.beacon", [pick(game, "h4.beacon", "count")], "Builder Site")
expect(flag(game, "timing_recorded") and "the needles' count" in text, "held the way Korai taught")
game, io = ready()
game.person.research_points = 200
text = scene(game, io, "h4.beacon", [pick(game, "h4.beacon", "sensors")], "Builder Site")
expect(flag(game, "timing_recorded") and game.person.research_points == 150 and "cheese sandwich" in text,
       "the sensors, for a quarter of the research")
game, io = ready(money=6000)
scene(game, io, "h4.beacon", [pick(game, "h4.beacon", "recorder")], "Builder Site")
expect(flag(game, "timing_recorded") and game.person.money == 1000, "or a recorder buoy, 5,000")
expect("thought.h4.home" in [n for n in nodes if n.startswith("thought.") and holds(game, n)], "then the thought: home")

game, io = ready(timing_recorded=True, way_serac=True)
expect(holds(game, "h4.serac_copy"), "Serac's man comes for a copy")
text = scene(game, io, "h4.serac_copy", ["1"])
expect(flag(game, "serac_has_copy") and game.person.money == 70000 and "feeding birds" in text, "sold, 20,000")
game, io = ready(timing_recorded=True, serac_offer=True, opened_serac_box=True)
text = scene(game, io, "h4.serac_copy", ["2"])
expect("You opened the container" in text and flag(game, "serac_refused_copy"), "the airlock; he remembers the box")
game, io = ready(timing_recorded=True, mandate_wants_it=True)
expect(holds(game, "h4.cutter"), "a hull taken at night: a Mandate cutter")
game, io = ready(timing_recorded=True, stonewright_met=True)
text = scene(game, io, "h4.escort", ["1"])
expect(flag(game, "stonewright_escort") and "We'll fly it with you" in text, "Stonewright escorts the long leg")

game, io = ready(timing_recorded=True, midpoint_known=True, stonewright_escort=True)
expect("h4.long_leg" in sights(game, "Builder Site"), "the long leg, from the Builder Site")
text = scene(game, io, "h4.long_leg", ["1"], "Builder Site")
expect(game.years_passed == 19 and "it is 2552" in text and "Eryxia" in text and "Stonewright beside it" in text,
       "nineteen years outside: 2552, Eryxia found")
text = scene(game, io, "h4.stator", ["1"], "Stator Field Megastructure")
expect(flag(game, "home_reached") and "Mandate grey" in text, "the Stator Field: everyone is waiting")
sm = game.story_manager
expect(all(m.check_completion(game) for m in sm.chapters["ch4"].milestones.values()), "chapter IV's three milestones")

# ---- V. Who Holds the Ring -------------------------------------------------------------------------------
for flags_, words in (({}, "common ground"), ({"segments_mandate": True}, "since 2460, when you helped it take them"),
                      ({"segments_hansa": True}, "voted them into its charter"),
                      ({"segments_rostrom": True}, "peer reviewed"), ({"segments_dawn": True}, "Binary Dawn")):
    rec = record("cargo2", flags=list(flags_)) if flags_ else None
    game, io = ready("ch5", rec)
    text = scene(game, io, "h5.holders", ["1"], "Stator Field Megastructure")
    expect(words in text, "the segments' holders by Cargo 2's ending: %s" % words)
game, io = ready("ch5")
expect("h5.mandate" in sights(game, "Alpha") and "h5.collective" in sights(game, "Alpha"), "Serac and the machines at Alpha")
expect("h5.concord" in sights(game, "Epsilon") and "h5.hansa" in sights(game, "Beta")
       and "h5.home" in sights(game, "Stator Field Megastructure"), "the Concord at Epsilon, the Hansa at Beta, your own people")
text = scene(game, io, "h5.mandate", ["1"], "Alpha")
expect(flag(game, "side_mandate") and "That is the frightening part" in text, "sided with the Mandate")
expect(choice_ids(game, "h5.concord") == ["heard"], "one side only")
scene(game, io, "h5.concord", ["1"], "Epsilon")
expect(stat(game, "claims") == 2 and not holds(game, "h5.crisis"), "two claims: not yet")
text = scene(game, io, "h5.home", ["1"], "Stator Field Megastructure")
expect(stat(game, "claims") == 3 and holds(game, "h5.crisis") and "Adit's lists" in text, "three: the Mandate moves")
expect(choice_ids(game, "h5.crisis") == ["give"], "a captain on the Mandate's side hands it over")
text = scene(game, io, "h5.crisis", ["1"])
expect(flag(game, "gave_serac_timing") and game.person.money == 80000 and "with you" in text, "30,000")
game.story.done["h5.crisis"] = game.turn - 5
text = scene(game, io, "h5.low", ["1"])
expect(flag(game, "low_point_done") and game.years_passed == 38 and "your beat" in text,
       "the ring turns a degree the wrong way: thirty-eight years")
text = scene(game, io, "h5.korai_back", ["1"])
expect("It is 2571" in text and "older at last" in text, "Korai comes out of the wreck in 2571")
game, io = ready("ch5", stonewright_escort=True, claim_home=True, claim_hansa=True, claim_concord=True)
expect(choice_ids(game, "h5.crisis") == ["give", "run", "escort"], "the others can run the blockade, with Stonewright")
text = scene(game, io, "h5.crisis", ["3"])
expect(flag(game, "ran_blockade") and "gunnery practice" in text, "the blockade run")
sm = game.story_manager
game.story_manager.story_states["low_point_done"] = True
expect(all(m.check_completion(game) for m in sm.chapters["ch5"].milestones.values()), "chapter V's three milestones")

# ---- VI. From Home ---------------------------------------------------------------------------------------
game, io = ready("ch6", navigator_key=True, vouched_for=True, papers_in_order=True, debt_called_in=True,
                 stonewright_met=True)
expect(choice_ids(game, "h6.restart") == ["now", "leave"], "no allies yet, no side: only the wrong end, or wait")
allies = [("h6.stonewright", "Stator Field Megastructure"), ("h6.collective", "Alpha"), ("h6.kraal", "Delta")]
for nid, place in allies:
    expect(nid in sights(game, place), "%s at %s" % (nid, place))
    text = scene(game, io, nid, ["1"], place)
expect(stat(game, "allies") == 3 and "far side" in text + flat(screens[-3][1]), "three allies")
for cid, wanted in (("h6.korai", "warp_singer"), ("h6.cooperative", "aela"), ("h6.rootstock", "meza_voce")):
    expect("here" in str(nodes[cid]["requires"]) and wanted in str(nodes[cid]["requires"]), "%s waits for %s" % (cid, wanted))
expect(choice_ids(game, "h6.restart") == ["home", "now", "leave"], "three allies: from home")
game2, io2 = ready("ch6", side_hansa=True)
expect(choice_ids(game2, "h6.restart") == ["faction", "now", "leave"], "a side taken: their end")
game3, io3 = ready("ch6", ship_truth=False)
expect(not any(n.startswith("h6.") and n.endswith(("stonewright", "korai", "cooperative", "rootstock", "collective", "kraal"))
               and holds(game3, n) for n in nodes), "nobody stands with a captain who befriended nobody")

# the endings, through the chapters
for flags_, choice, ending, words in (
        ({"navigator_key": True, "ally_korai": True, "ally_stonewright": True, "ally_kraal": True}, "home",
         "ending_home", "on a road nobody owns"),
        ({"side_collective": True}, "faction", "ending_faction", "counts the first turn aloud"),
        ({}, "now", "ending_loop", "a shard of grey alloy, still warm")):
    game, io = ready("ch6", **flags_)
    text = scene(game, io, "h6.restart", [pick(game, "h6.restart", choice)], "Stator Field Megastructure")
    sm = game.story_manager
    io.feed([""] * 40)
    with quiet() as out:
        sm.check_milestone_progress()
        sm.check_chapter_progress()
        sm.check_milestone_progress()
        sm.check_chapter_progress()
    shown = flat(out.getvalue())
    screens.append((ending, out.getvalue()))
    expect(sm.current_chapter == ending and words in shown, "%s: %s (%s)" % (choice, ending, sm.current_chapter))
    expect("What became of them" in shown, "%s: the epilogue" % ending)
    expect("{" not in shown, "%s: every name and year filled on screen" % ending)
    expect(not flag(game, "restarted_the_gyrotron"), "nobody is ever said to have restarted it")
    if ending == "ending_home":
        expect(game.years_passed == 10 and "2543" in shown and "Korai" in shown, "ten more years: the first mission leaves")
    if ending == "ending_loop":
        expect("2420" in shown and "make sure it starts from home" in shown.lower(), "the loop: back to the portal")

# ---- every scene fits 36 columns ----------------------------------------------------------------------------
wide = [(nid, max(cargo.visible_len(line) for line in text.splitlines())) for nid, text in screens if text.strip()]
expect(all(width <= 36 for _, width in wide), "every scene fits 36 columns: %s" % [w for w in wide if w[1] > 36])
print("heading: %d scenes played, %s" % (len(screens), "ok" if not problems[0] else "%d problems" % problems[0]))
sys.exit(1 if problems[0] else 0)
