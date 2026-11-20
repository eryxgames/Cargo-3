#!/usr/bin/env python3
"""The people named by what they do (story/cargo3/roles.json): the guard at the impound yard, the
medic on the berths, the cybersurgeon at Epsilon, the battle engineer and the armored commander on
Delta's test range, and the Mandate squad with its heavy infantry commander. Each scene is played
with every answer, at 36 columns, and what it says about the named cast is checked.

    python3 tools/roles.py
"""
import os, re, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from storytest import cargo, expect, flat, options, play, problems, record, start  # noqa: E402

SIZE = os.terminal_size((36, 40))
shutil.get_terminal_size = lambda fallback=(80, 24): SIZE
os.get_terminal_size = lambda *a: SIZE
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storykit"))
import story as kit  # noqa: E402
data = cargo.story_data()
nodes = data["nodes"]
chars = kit.load(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "story", "cargo3.story.json"))["characters"]
screens = []


def scene(game, io, nid, answer="1", where=None):
    text = play(game, io, nid, answer, where)
    screens.append((nid, text))
    return flat(text)


def ready(rec=None, money=None):
    game, io, _ = start(rec)
    play(game, io, "opening.pod")
    play(game, io, "hall.first")
    if money is not None:
        game.person.money = money
    return game, io


def bring(game, cid, place):
    """Move the clock on until the character's route has them at this place."""
    route = chars[cid]["route"]
    turn = game.turn
    while route["places"][((turn + route.get("start", 0)) // route["stay"]) % len(route["places"])] != place:
        turn += 1
    game.turn = turn
    game.current_location = next(loc for loc in game.locations if loc.name == place)


def sights(game, place=None):
    if place:
        game.current_location = next(loc for loc in game.locations if loc.name == place)
    return game.sights_here()


# ---- the cast: roles have no personal names; one of them earns one --------------------------------------
roles = [cid for cid, info in chars.items() if info.get("anonymous") or info.get("group")]
expect(sorted(roles) == sorted(["perimeter_guard", "medic", "cybersurgeon", "battle_engineer", "armored_commander",
                                "infantry_squad", "heavy_infantry_commander", "needle_clerk", "store_cashier",
                                "hansa_auditor", "tail_gunner", "rockwarden_prospector",
                                "rockwarden_envoy", "chronos_clerk"]), "fourteen roles (two in chapter II): %s" % roles)
expect(all(not chars[cid].get("short") for cid in roles) and chars["infantry_squad"].get("group"),
       "roles have no short names, and the squad is a group")
expect(chars["gabion"].get("was") == "battle_engineer", "Gabion is the battle engineer, once named")

# ---- the impound yard at Alpha ---------------------------------------------------------------------------------
game, io = ready()
expect("sight.alpha.yard" in sights(game, "Alpha"), "the impound yard is a sight at Alpha")
text = scene(game, io, "sight.alpha.yard", "1", "Alpha")
expect("Perimeter Guard" in text and "a loader one hand short" in text, "the guard points at the loader with the lists")
money = game.person.money
text = scene(game, io, "sight.alpha.yard", "1", "Alpha")          # asked already: the list is the first choice now
expect(game.person.money == money - 100 and "Forty-one hulls" in text and "The paint is new" in text,
       "100 credits for the yard's list: one hull with no name")
text = scene(game, io, "sight.alpha.yard", "1", "Alpha")
expect("the way you nod to a debt" in text and options(screens[-1][1]) == 1, "afterwards only a nod, and walking on")
game, io = ready(money=50)
game.story_manager.story_states["first_friend"] = True
text = scene(game, io, "sight.alpha.yard", "1", "Alpha")
expect("You know Adit?" in text, "a captain who found Adit hears so from the guard")
expect(options(screens[-1][1]) == 2, "no list without 100 credits")
game, io = ready()
game.person.items["procrustes_analyzer"] = 1
text = scene(game, io, "sight.alpha.yard", "2", "Alpha")
expect("The Procrustes Analyzer turns the nameless hull" in text, "with the Analyzer the nameless hull is tried, and fails")

# ---- the medic on the berths ---------------------------------------------------------------------------------------
game, io = ready()
bring(game, "medic", "Beta")
expect("people.medic" in sights(game), "the medic is on Beta's berths on her turns there")
bring(game, "medic", "Gamma")
expect("people.medic" in sights(game), "and on Gamma's on hers")
game.person.wounds = 45
money = game.person.money
text = scene(game, io, "people.medic", "1", game.current_location.name)
expect("pushes a stool at you" in text and game.person.wounds == 15 and game.person.money == money - 40,
       "a wounded hand is patched up for 40 credits: 45 down to 15")
scene(game, io, "people.medic", "1", game.current_location.name)
expect(game.person.wounds == 0 and game.person.money == money - 80, "and again, for another 40")
text = scene(game, io, "people.medic", "1", game.current_location.name)
expect("Brother Caboose sends me his crews" in text and "Lieutenant Caspic" in text and "Jak Ghillie" in text,
       "whole, a hand can only ask who sends her patients: the named captains")
scene(game, io, "people.medic", "1", game.current_location.name)
expect(options(screens[-1][1]) == 1, "and after that, only leaving")

# ---- the clinic at Epsilon --------------------------------------------------------------------------------------------
game, io = ready(money=1000)
expect("sight.epsilon.clinic" in sights(game, "Epsilon"), "the clinic is a sight at Epsilon")
text = scene(game, io, "sight.epsilon.clinic", "1", "Epsilon")
expect("The cold took the newest memories first" in text and "Conte" not in text, "the pod's damage, read")
money = game.person.money
text = scene(game, io, "sight.epsilon.clinic", "1", "Epsilon")
expect("The implant catalogue" in text and "Gunner: untried to green, 500" in text and game.person.money == money,
       "the catalogue: a level of any skill, priced on a curve (and nothing bought by leaving)")
expect("Have the pod's damage read" not in text, "once read, the pod's damage is not read again")
game, io = ready(money=100)
game.story.done["sight.delta.conte"] = 1
text = scene(game, io, "sight.epsilon.clinic", "1", "Epsilon")
expect("Conte Ottavine sat in this chair" in text and "ask the past" in text,
       "a captain who has met the Conte hears she was in the chair")
expect(options(screens[-1][1]) == 3, "the scan, the catalogue (whatever the purse), and leaving")

# ---- the test range at Delta -----------------------------------------------------------------------------------------------
game, io = ready()
expect("sight.delta.range" not in sights(game, "Delta"), "the test range waits for a shift at the plant")
game.shifts = {"hovertank": 1}
expect("sight.delta.range" in sights(game, "Delta"), "then the range is a sight")
text = scene(game, io, "sight.delta.range", "1", "Delta")
expect("Battle Engineer" in text and "Armored Commander" in text and "On something that mattered more to you" in text,
       "rigging the skirt with the engineer")
expect(game.person.practice["mechanic"] == 3 or game.person.skills["mechanic"] >= 1, "three practice at mechanic")
expect(options(screens[-1][1]) == 2, "an untried gunner cannot ride the trial, nor ask a name yet")
game.person.skills["gunner"] = 2
money = game.person.money
text = scene(game, io, "sight.delta.range", "1", "Delta")
expect("You shoot like somebody who learned on a hauler" in text and "Serac" in text and game.person.money == money + 120,
       "the live-fire trial: paid, and compared to Serac's people")
game.shifts = {"hovertank": 4}
text = scene(game, io, "sight.delta.range", "1", "Delta")
expect("'Gabion,' she says" in text and game.story_manager.story_states.get("gabion_named"), "four shifts on: she tells her name")
text = scene(game, io, "sight.delta.range", "1", "Delta")
expect(text.startswith("The test range Gabion is under") or "Gabion is under the hovertank again" in text,
       "from then on the range calls her Gabion")
expect("Battle Engineer" not in text, "and not the Battle Engineer")
for flag, words in (("delivered_the_hovertank", "nobody can read the name"), ("sold_the_hovertank", "Serac's depot")):
    game, io = ready(record("cargo1", "trade", [flag]))
    game.shifts = {"hovertank": 1}
    text = scene(game, io, "sight.delta.range", "2", "Delta")
    expect(words in text, "%s: the range remembers (%s)" % (flag, words))

# ---- the squad and its commander ----------------------------------------------------------------------------------------------
for rec, answer, words, flag in ((None, "2", "Serac likes to find people himself", "squad_carried"),
                                 (record("cargo1", "", ["took_the_commission"]), "1", "a commission nobody closed", None),
                                 (record("cargo1", "", ["defied_serac"]), "1", "in his own hand", None)):
    game, io = ready(rec)
    game.turn = 8
    bring(game, "infantry_squad", "Gamma")
    expect(game.story.check(game.story.requires_of(nodes["squad.sweep"]), game.story.snapshot()),
           "the squad's sweep can come at Gamma on its turns there")
    text = scene(game, io, "squad.sweep", answer, "Gamma")
    expect("Squad of Soldiers" in text and "Heavy Infantry Commander" in text and words in text,
           "the sweep: %s" % words)
    if flag:
        expect(game.story_manager.story_states.get(flag) and "a kind of thanks" in text, "carrying the kit")
    expect(options(screens[-1][1]) == 2, "a green navigator cannot slip away")
    expect("people.squad" in sights(game, "Gamma"), "after the sweep the squad can be seen on its rounds")
game, io = ready()
game.turn = 8
game.person.skills["navigator"] = 1
bring(game, "infantry_squad", "Beta")
text = scene(game, io, "squad.sweep", "3", "Beta")
expect("somebody else's problem" in text and game.story_manager.story_states.get("squad_dodged"), "a navigator slips away")
text = scene(game, io, "people.squad", "1", "Beta")
expect("writes something on the slate" in text, "and the commander remembers the face")

# ---- the sweep starts a customs crackdown on the berths -----------------------------------------------------------------------
game, io = ready()
game.turn = 8
bring(game, "infantry_squad", "Alpha")
scene(game, io, "squad.sweep", "1", "Alpha")
expect(game.labour_left("berths_crackdown") == 3 and not any(o["kind"] == "smuggler" for o in game.berths()),
       "after the squad's sweep, a crackdown: no smugglers on the board for three turns")

# ---- the needle office at Beta ----------------------------------------------------------------------------------------------------
game, io = ready()
game.known_locations.extend(n for n in ("Delta", "Gamma") if n not in game.known_locations)
game.start_labour("plant_strike", "Delta", 2)
text = scene(game, io, "sight.beta.needle_office", "1", "Beta")
expect("Needle Office Clerk" in text and "The board says: A strike at Delta's hovertank plant." in text,
       "the needle office's board says what is on at the other docks")
expect("Ask Korai: she rides every needle" in text, "the clerk sends the hand to Korai")
game.start_labour("berths_crackdown", "Beta", 2)
text = scene(game, io, "sight.beta.needle_office", "1", "Beta")
expect("a customs desk inside it this week" in text and options(screens[-1][1]) == 1, "in a crackdown, customs in the office")

# ---- the company store at Gamma -----------------------------------------------------------------------------------------------------
game, io = ready()
text = scene(game, io, "sight.gamma.store", "1", "Gamma")
expect("Company Store Cashier" in text and "Eela" in text and "the cooperative" in text, "who pays cash at Gamma: Eela")
expect(options(screens[-1][1]) == 2, "no tab to pay while the shafts are open")
game.start_labour("mine_gas", "Gamma", 2)
money = game.person.money
text = scene(game, io, "sight.gamma.store", "1", "Gamma")
expect("cannot earn" in text and game.person.money == money - 60 and "two children and one boot" in text,
       "with the shafts shut for gas, a hand can pay a miner's tab")
game, io = ready(record("cargo1", "trade", ["aela_member"]))
text = scene(game, io, "sight.gamma.store", "1", "Gamma")
expect("a share is forever" in text, "a captain who gave Eela a share hears that it asked after them")

# ---- the Hansa auditor, with an audit ----------------------------------------------------------------------------------------------------
game, io = ready()
expect("people.auditor" not in sights(game, "Alpha"), "no auditor without an audit")
game.start_labour("ring_audit", "Alpha", 2)
expect("people.auditor" in sights(game, "Alpha"), "an audit brings the auditor")
money = game.person.money
text = scene(game, io, "people.auditor", "1", "Alpha")
expect("Ola Plumb" in text and "never had to count twice" in text and game.person.money == money + 50,
       "counting with the auditor pays 50, and points at Ola Plumb")
scene(game, io, "people.auditor", "1", "Alpha")
expect(options(screens[-1][1]) == 1 and game.person.money == money + 50, "once")

# ---- the convoy's tail gunner, with a convoy forming -----------------------------------------------------------------------------------
game, io = ready()
expect("people.tail_gunner" not in sights(game, "Delta"), "no tail gunner without a convoy")
game.start_labour("berths_convoy", "Delta", 2)
text = scene(game, io, "people.tail_gunner", "1", "Delta")
expect("Convoy Tail Gunner" in text and "Brother Caboose's lot, singing" in text, "the tail gunner points at Brother Caboose")

# ---- the Rockwarden prospector, with a rich seam --------------------------------------------------------------------------------------------
game, io = ready()
game.start_labour("mine_seam", "Gamma", 3)
expect("people.prospector" in sights(game, "Gamma"), "a rich seam brings a Rockwarden prospector")
text = scene(game, io, "people.prospector", "1", "Gamma")
expect("Eela dug our first gallery" in text and options(screens[-1][1]) == 2, "a green surveyor can only ask about the cooperative")
game.person.skills["navigator"] = 2
money = game.person.money
text = scene(game, io, "people.prospector", "1", "Gamma")
expect(game.person.money == money + 150 and "Stonewright's people are coming home" in text,
       "an able surveyor sells the seam's survey to the cooperative")

# ---- what the hand did about the docks' events is remembered --------------------------------------------------------------------
game, io = ready()
game.shifts = {"hovertank": 1}
game.labour_marks()["crossed"] = 1
text = scene(game, io, "sight.delta.range", "4", "Delta")
expect("'line crosser'" in text, "on the test range, a line crosser is called one")
game, io = ready()
game.labour_marks()["cleared_gas"] = 1
text = scene(game, io, "sight.gamma.store", "2", "Gamma")
expect("You went down with the fire boss" in text, "at the company store, the hand who cleared the gas is known")
game, io = ready()
game.turn = 8
bring(game, "infantry_squad", "Gamma")
scene(game, io, "squad.sweep", "1", "Gamma")
game.labour_marks()["informed"] = 1
text = scene(game, io, "people.squad", "1", "Gamma")
expect("nods to you like a colleague" in text, "and the squad's commander knows an informer")

# ---- every screen fits 36 columns ----------------------------------------------------------------------------------------------
wide = [(nid, line) for nid, text in screens for line in text.splitlines() if len(line) > 36]
expect(not wide, "lines wider than 36 columns: %s" % wide[:2])
played = {nid for nid, _ in screens}
mine = {nid for nid, n in nodes.items() if n.get("arc") == "roles" and n.get("kind") == "sight"}
expect(mine <= played, "every roles sight played: %s" % sorted(mine - played))

print("roles: %d scenes played, %s" % (len(screens), "ok" if not problems[0] else "%d problems" % problems[0]))
sys.exit(1 if problems[0] else 0)
