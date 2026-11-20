#!/usr/bin/env python3
"""Chapter II, Old Friends (story/cargo3/friends.json): five things a ship needs from five old
friends, each way of getting each one (by skill, by money, by a fight on foot won or lost, by
what a captain record carries), the stat that counts them, the chapter that ends at three, the
thoughts that point the way, and the people closing in (Serac's men, the Rockwarden envoy, the
time broker's clerk). Every scene is played at 36 columns.

    python3 tools/friends.py
"""
import os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from storytest import cargo, expect, flat, play, problems, record, start  # noqa: E402

SIZE = os.terminal_size((36, 40))
shutil.get_terminal_size = lambda fallback=(80, 24): SIZE
os.get_terminal_size = lambda *a: SIZE
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storykit"))
import story as kit  # noqa: E402
nodes = cargo.story_data()["nodes"]
chars = kit.load(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "story", "cargo3.story.json"))["characters"]
screens = []


def ready(rec=None, money=900, friend=True):
    game, io, _ = start(rec)
    play(game, io, "opening.pod")
    play(game, io, "hall.first")
    if friend:
        game.story_manager.story_states.update(first_friend=True, adit_friend=True)
    game.person.money = money
    return game, io


def scene(game, io, nid, answer="1", where=None):
    text = play(game, io, nid, answer, where)
    screens.append((nid, text))
    return flat(text)


def bring(game, cid, place):
    """Move the clock on until the character's route has them at this place."""
    route = chars[cid]["route"]
    turn = game.turn
    while route["places"][((turn + route.get("start", 0)) // route["stay"]) % len(route["places"])] != place:
        turn += 1
    game.turn = turn
    game.current_location = next(loc for loc in game.locations if loc.name == place)


def flag(game, name):
    return bool(game.story_manager.story_states.get(name))


def needs(game):
    return game.story_snapshot()["stats"]["ship_needs"]


def choice_ids(game, nid):
    snap = game.story.snapshot()
    return [c["id"] for c in nodes[nid].get("choices") or [] if game.story.check(c.get("requires"), snap)]


def pick(game, nid, cid):
    return str(choice_ids(game, nid).index(cid) + 1)


def fights(game, win):
    """Fights on foot in the story's scenes go one way: won at the first blow, or lost (downed,
    never killed)."""
    plain = game.brawl
    game.ask_move = lambda title, lines, options, default: "strike"
    game.brawl_odds = lambda *a, **k: 1.0 if win else 0.0
    game.foe_hit_chance = lambda *a, **k: 0.0 if win else 1.0
    game.brawl = lambda foe, edge=0, **k: plain(foe, edge=edge, rolls=[0.0 if win else 0.99] * 60)


def thoughts(game):
    snap = game.story.snapshot()
    return [nid for nid, node in nodes.items() if node.get("kind") == "thought" and game.story.check(game.story.requires_of(node), snap)]


def sights(game, place):
    game.current_location = next(loc for loc in game.locations if loc.name == place)
    return game.sights_here()


# ---- the thoughts point the way ----------------------------------------------------------------------------
game, io = ready(friend=False)
expect(not any(n.startswith("thought.") and n in ("thought.korai", "thought.eela", "thought.cu113") for n in thoughts(game)),
       "no chapter II thoughts before the first old friend")
game, io = ready()
now = thoughts(game)
expect(all(t in now for t in ("thought.korai", "thought.eela", "thought.papers", "thought.voce", "thought.cu113")),
       "after the first friend, a thought for each: %s" % [t for t in now if t.startswith("thought.")])
expect(needs(game) == 0, "nothing a ship needs yet")

# ---- Korai: the navigator's key ------------------------------------------------------------------------------
game, io = ready()
bring(game, "warp_singer", "Beta")
expect("friends.korai" in game.sights_here(), "Korai is in the signal loft at Beta")
expect(choice_ids(game, "friends.korai") == ["learn", "leave"], "an untried navigator can only ask how the count goes")
text = scene(game, io, "friends.korai", pick(game, "friends.korai", "learn"), "Beta")
expect("eleven beats" in text and flag(game, "korai_met") and not flag(game, "navigator_key"), "she counts it; you lose it")
game.person.skills["navigator"] = 1
expect(choice_ids(game, "friends.korai") == ["ride", "leave"], "a green navigator can ride with her")
text = scene(game, io, "friends.korai", pick(game, "friends.korai", "ride"), "Beta")
expect("Can you hold a count yet" in text and "stars go long" in text, "met again; the ride")
expect(flag(game, "navigator_key") and "That's the key" in text and needs(game) == 1, "the count held: the navigator's key")
expect("thought.korai" not in thoughts(game), "and the thought is gone")
game, io = ready()
game.person.skills["navigator"] = 1
bring(game, "warp_singer", "Delta")
text = scene(game, io, "friends.korai", pick(game, "friends.korai", "ride"), "Delta")
expect(flag(game, "navigator_key") and flag(game, "korai_pointed_yard") and "Mandate tows those to Alpha" in text,
       "Enter on the needle: hold the count and ask where the ship went")
game, io = ready()
game.person.skills["navigator"] = 1
bring(game, "warp_singer", "Beta")
plain = io.feed
io.feed = lambda items: plain(["1", "1"] + [""] * 10)      # ride, then hold the count
text = scene(game, io, "friends.korai", "1", "Beta")
io.feed = plain
expect(flag(game, "navigator_key") and not flag(game, "korai_pointed_yard"), "or just hold the count")
rec = record("cargo2", flags=["needle_talk"])
game, io = ready(rec)
bring(game, "warp_singer", "Epsilon")
expect(choice_ids(game, "friends.korai")[0] == "verse", "a captain who learned needle-talk in 2460 sings it back")
text = scene(game, io, "friends.korai", "1", "Epsilon")
expect("You still have the verse" in text and flag(game, "navigator_key"), "the verse is half of the count")

# ---- Eela: someone to vouch for you ------------------------------------------------------------------------------
game, io = ready()
bring(game, "aela", "Gamma")
expect("friends.eela" in game.sights_here(), "Eela digs at Gamma")
expect(choice_ids(game, "friends.eela") == ["seam", "leave"], "a stranger can only stand on its seam")
fights(game, win=False)
text = scene(game, io, "friends.eela", pick(game, "friends.eela", "seam"), "Gamma")
expect(not flag(game, "vouched_for") and "They will come back" in text and flag(game, "eela_met"),
       "the claim jumpers win: come back")
fights(game, win=True)
text = scene(game, io, "friends.eela", pick(game, "friends.eela", "seam"), "Gamma")
expect("still deciding" in text and flag(game, "vouched_for") and "'decided'" in text and needs(game) == 1,
       "the seam held: the cooperative vouches")
game, io = ready()
game.person.skills["navigator"] = 2
bring(game, "aela", "Gamma")
text = scene(game, io, "friends.eela", pick(game, "friends.eela", "survey"), "Gamma")
expect(flag(game, "vouched_for") and "cooperative jacket" in text, "an able navigator surveys the seam instead")
game, io = ready(record("cargo1", flags=["aela_member"]))
bring(game, "aela", "Gamma")
expect(choice_ids(game, "friends.eela")[0] == "member", "Eela's first machine shareholder asks")
text = scene(game, io, "friends.eela", "1", "Gamma")
expect("You put me in the cooperative" in text and flag(game, "vouched_for"), "and is vouched for at once")
text = scene(game, io, "closing.envoy", "1", "Alpha")
expect("Stonewright is coming home" in text and flag(game, "envoy_heard"), "then a Rockwarden envoy wants to talk")

# ---- The Kraal family: papers -------------------------------------------------------------------------------------
game, io = ready()
expect("friends.conte_papers" in sights(game, "Delta"), "the Kraal counting room at Delta")
expect(choice_ids(game, "friends.conte_papers") == ["fetch", "leave"], "with 900 credits: fetch the seal")
text = scene(game, io, "friends.conte_papers", "1", "Delta")
expect("the Magister keeps" in text and "letter" in text and flag(game, "seal_wanted"), "the Magister writes a letter")
expect("thought.seal" in thoughts(game) and "friends.yard_seal" in sights(game, "Alpha"), "the seal is at Alpha")
expect(choice_ids(game, "friends.yard_seal") == ["pay", "fence", "leave"], "pay the guard, or the fence")
fights(game, win=False)
text = scene(game, io, "friends.yard_seal", pick(game, "friends.yard_seal", "fence"), "Alpha")
expect("puts it back in the yacht" in text and not game.person.items.get("kraal_seal") and not flag(game, "seal_night"),
       "caught by the night watch: no seal")
fights(game, win=True)
text = scene(game, io, "friends.yard_seal", pick(game, "friends.yard_seal", "fence"), "Alpha")
expect("round your neck" in text and game.person.items.get("kraal_seal") == 1, "over the fence with the seal")
expect("friends.yard_seal" not in sights(game, "Alpha") and "thought.seal_held" in thoughts(game), "back to Delta")
expect(choice_ids(game, "friends.conte_papers") == ["give", "leave"], "give him the seal")
text = scene(game, io, "friends.conte_papers", "1", "Delta")
expect(flag(game, "papers_in_order") and "A family captain" in text and not game.person.items.get("kraal_seal"),
       "the papers: a family captain; the seal stays in the book")
game, io = ready(money=400)
game.story_manager.story_states["seal_wanted"] = True
text = scene(game, io, "friends.yard_seal", pick(game, "friends.yard_seal", "pay"), "Alpha")
expect(game.person.money == 100 and game.person.items.get("kraal_seal") == 1 and "cattle pen" in text, "300 to the guard")
game, io = ready()
game.story_manager.story_states["seal_wanted"] = True
game.person.skills["broker"] = 2
expect("letter" in choice_ids(game, "friends.yard_seal"), "an able broker shows the letter")
game, io = ready(money=3000)
text = scene(game, io, "friends.conte_papers", pick(game, "friends.conte_papers", "forms"), "Delta")
expect(flag(game, "papers_in_order") and game.person.money == 500 and "bills you for the ink" in text, "or 2,500 and forms")
game, io = ready(record("cargo1"))
text = scene(game, io, "friends.conte_papers", "1", "Delta")
expect("My grandfather read your family line" in text, "a Cargo 1 captain: the bill is still on file")

# ---- Meza Voce: a debt called in ----------------------------------------------------------------------------------
game, io = ready()
bring(game, "meza_voce", "Beta")
expect("friends.voce" in game.sights_here(), "Meza Voce in the back corridor at Beta")
expect(choice_ids(game, "friends.voce") == ["run", "leave"], "a stranger carries her crates")
text = scene(game, io, "friends.voce", "1", "Beta")
expect(flag(game, "voce_run") and "AGROBOT SPARES" in text and "friends.voce" not in game.sights_here(), "twelve crates")
expect("friends.voce_gate" in sights(game, "Gamma") and "thought.voce_run" in thoughts(game), "to the gallery gate")
expect(choice_ids(game, "friends.voce_gate") == ["bribe", "push", "leave"], "bribe the guards, or walk through")
fights(game, win=False)
text = scene(game, io, "friends.voce_gate", pick(game, "friends.voce_gate", "push"), "Gamma")
expect(not flag(game, "debt_called_in") and "come back next shift" in text, "stopped at the gate")
fights(game, win=True)
text = scene(game, io, "friends.voce_gate", pick(game, "friends.voce_gate", "push"), "Gamma")
expect(flag(game, "debt_called_in") and "miners' shoulders" in text and needs(game) == 1, "through the gate: the Rootstock owe you")
game, io = ready()
game.story_manager.story_states["voce_run"] = True
text = scene(game, io, "friends.voce_gate", pick(game, "friends.voce_gate", "bribe"), "Gamma")
expect(flag(game, "debt_called_in") and game.person.money == 800 and "does not appear on any chart" in text,
       "100 to the guards; a yard that asks no questions")
game, io = ready(record("cargo1", flags=["rootstock_family"]))
bring(game, "meza_voce", "Gamma")
expect(choice_ids(game, "friends.voce")[0] == "call", "family calls in the debt")
text = scene(game, io, "friends.voce", "1", "Gamma")
expect("'Family.'" in text and flag(game, "debt_called_in"), "at once")
game, io = ready(record("cargo1", flags=["double_cross"]), money=2000)
bring(game, "meza_voce", "Beta")
expect(choice_ids(game, "friends.voce") == ["pay", "settle", "leave"], "the double cross first: pay, or her androids")
text = scene(game, io, "friends.voce", "1", "Beta")
expect("crates you sold to customs" in text and flag(game, "voce_even") and game.person.money == 500, "1,500 and even")
expect(choice_ids(game, "friends.voce") == ["run", "leave"] and "Even," in flat(play(game, io, "friends.voce", "2", "Beta")),
       "then she has work for you")
game, io = ready(record("cargo1", flags=["double_cross"]), money=100)
bring(game, "meza_voce", "Beta")
fights(game, win=True)
text = scene(game, io, "friends.voce", pick(game, "friends.voce", "settle"), "Beta")
expect(flag(game, "voce_even") and "better at this than I remembered" in text, "her androids beaten: even, and respect")

# ---- CU-113: the truth about your ship -----------------------------------------------------------------------------
game, io = ready()
expect("friends.cu113" in sights(game, "Alpha") and choice_ids(game, "friends.cu113") == ["shift", "leave"],
       "a machine counting hulls at Alpha; take its count for a shift")
text = scene(game, io, "friends.cu113", "1", "Alpha")
expect("Curator Unit 113" in text and "The hull with no name is yours" in text and flag(game, "ship_truth"), "it is yours")
game, io = ready(record("cargo2", flags=["cu113_contract"]))
text = scene(game, io, "friends.cu113", "1", "Alpha")
expect("I still have the hour you gave me" in text and flag(game, "ship_truth"), "the hour from 2420, spent")
game, io = ready(record("cargo1", flags=["cu113_sold"]))
expect(choice_ids(game, "friends.cu113") == ["wage", "leave"], "a machine you sold wants a wage")
text = scene(game, io, "friends.cu113", "1", "Alpha")
expect("You sold me" in text and game.person.money == 600 and flag(game, "ship_truth"), "300, in advance")
game, io = ready()
game.person.items["procrustes_analyzer"] = 1
text = scene(game, io, "friends.cu113", "1", "Alpha")
expect("The Procrustes Analyzer gave up on it" in text, "with the Analyzer from the vault")

# ---- three end the chapter ---------------------------------------------------------------------------------------------
game, io = ready()
sm = game.story_manager
sm.current_chapter = "ch2"
sm.completed_chapters.add("ch1") if isinstance(sm.completed_chapters, set) else sm.completed_chapters.append("ch1")
milestone = sm.chapters["ch2"].milestones["friends"]
for name in ("navigator_key", "vouched_for"):
    sm.story_states[name] = True
expect(needs(game) == 2 and not milestone.check_completion(game), "two are not enough")
sm.story_states["ship_truth"] = True
expect(needs(game) == 3 and milestone.check_completion(game), "three end chapter II")

# ---- closing in --------------------------------------------------------------------------------------------------------
game, io = ready()
game.story_manager.current_chapter = "ch2"
for name in ("navigator_key", "vouched_for"):
    game.story_manager.story_states[name] = True
expect(game.story.check(game.story.requires_of(nodes["closing.serac"]), game.story.snapshot()), "two things, and Serac's men come")
expect(choice_ids(game, "closing.serac") == ["refuse", "hear"], "no, or hear them out (Enter: hear them out)")
text = scene(game, io, "closing.serac", "2")
expect("released from the yard" in text and flag(game, "serac_offer") and "card with no name" in text, "Serac's offer")
game, io = ready()
game.story_manager.current_chapter = "ch2"
for name in ("navigator_key", "vouched_for"):
    game.story_manager.story_states[name] = True
fights(game, win=True)
text = scene(game, io, "closing.serac", "1")
expect(flag(game, "serac_refused") and "now he has a reason to" in text and game.brawls == {"won": 1}, "no, and a fight won")
game, io = ready(record("cargo1", flags=["took_the_commission"]))
game.story_manager.current_chapter = "ch2"
for name in ("navigator_key", "vouched_for"):
    game.story_manager.story_states[name] = True
expect(choice_ids(game, "closing.serac") == ["polite", "hear"], "a colonel says no politely, and nobody fights")
text = scene(game, io, "closing.serac", "1")
expect("Colonel" in text and flag(game, "serac_refused") and not game.brawl_counts(), "no fight for an old officer")
game, io = ready()
game.story_manager.current_chapter = "ch2"
game.story_manager.story_states["ship_truth"] = True
text = scene(game, io, "closing.broker", "1")
expect("great-aunt's implant bonds" in text and flag(game, "broker_card"), "a time broker's card, for a fresh captain")
game, io = ready(record("cargo2"))
game.story_manager.current_chapter = "ch2"
game.story_manager.story_states["ship_truth"] = True
text = scene(game, io, "closing.broker", "1")
expect("An account opened in your name a century ago" in text, "and for a captain with a past")

# ---- every scene fits 36 columns -----------------------------------------------------------------------------------------
wide = [(nid, max(cargo.visible_len(line) for line in text.splitlines())) for nid, text in screens if text.strip()]
expect(all(width <= 36 for _, width in wide), "every scene fits 36 columns: %s" % [w for w in wide if w[1] > 36])
print("friends: %d scenes played, %s" % (len(screens), "ok" if not problems[0] else "%d problems" % problems[0]))
sys.exit(1 if problems[0] else 0)
