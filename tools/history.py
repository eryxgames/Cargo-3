#!/usr/bin/env python3
"""The captain's history across the parts (game/record.py, copied from the Cargo repository),
and Cargo 3's errands to the past: level nine's plaque (to 2420, Cargo 1) and the word for the
Kraal vault (to 2460, Cargo 2). An errand is given here, travels in the record, is done in the
earlier part, and shows here in a new game begun as that captain. Also: keys from newer games
kept, a record from an older game joined back up, notes for versions too old, hostile histories
cleaned, saves from before the history.

    python3 tools/history.py
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from headless import IO, patch, quiet  # noqa: E402
from storytest import captains, cargo, expect, flat, play, problems, record, start  # noqa: E402
from game import record as history  # noqa: E402
from game import start as starting  # noqa: E402

nodes = cargo.story_data()["nodes"]


def sealed(rec):
    rec["check"] = captains._captain_check(rec)
    return rec


def came_back(game, era, flags, version, turns=120):
    """The record this game exports, carried through an earlier part that did its errands there:
    what that part (1.3.0 / 2.3.0) writes back. Returns the record as that part would export it."""
    rec = game.captain_record()
    rec = json.loads(json.dumps(rec))
    start = history.start_from(rec, __import__("random").Random(7), known=captains.CAPTAIN_KEYS)
    errands = [dict(e) for e in start["errands"]]
    for errand in errands:
        if errand["to"] == era:
            errand["state"] = "done"
    rec["origin"] = {"game": era, "version": version}
    rec["story"] = {"chapter": "", "completed": [], "ending": "", "flags": list(flags), "plot_points": 9}
    rec["career"]["turns"] = turns
    history.write_history(rec, start, era, version, turns, flags, "", errands)
    return captains.clean_captain(sealed(rec))


def sights(game, place):
    game.current_location = next(loc for loc in game.locations if loc.name == place)
    return game.sights_here()


def thoughts(game):
    snap = game.story.snapshot()
    return {nid for nid, n in nodes.items() if n.get("kind") == "thought" and game.story.check(game.story.requires_of(n), snap)}


# ---- a fresh captain's record ------------------------------------------------------------------
game, io, _ = start(None)
game.turn = 25
rec = game.captain_record()
expect(rec["id"].startswith("C3-") and rec["line"].startswith("L-") and rec["own_time"] == 25 and rec["parent"] == "",
       "a fresh captain: a Cargo 3 id, a line, own time: %s" % {k: rec[k] for k in ("id", "line", "own_time")})
expect(set(rec["ledger"]) == {"cargo3"} and rec["errands"] == [], "the ledger holds this part, no errands")

# ---- level nine's plaque: the errand to 2420 ----------------------------------------------------------
game, io, _ = start(None)
play(game, io, "opening.pod")
play(game, io, "hall.first")
expect("sight.gamma.plaque" in sights(game, "Gamma"), "the plaque is a sight at Gamma")
text = flat(play(game, io, "sight.gamma.plaque", "1", where="Gamma"))
expect("blank" in text and "Errands to the past travel in your captain's record" in text and "Cargo 1 (1.3.0 or newer)" in text,
       "taking the errand says how to go back")
expect(history.errand_state(game.errands, "thirteenth_line") == "open", "the errand is open")
expect("thought.errand.plaque" in thoughts(game), "a thought keeps the way back")
game.turn = 30
rec = game.captain_record()
expect([(e["id"], e["to"], e["state"], e["needs"]) for e in rec["errands"]] == [("thirteenth_line", "cargo1", "open", "1.3.0")],
       "the record carries the errand: %s" % rec["errands"])
text = flat(play(game, io, "sight.gamma.plaque", "1", where="Gamma"))
expect("You have promised it a name" in text and "Errands to the past" not in text, "looking again: the promise, no choice")
# 2420: the plaque is cut with the captain's name; a new 2533 remembers
for flag, words, mine in (("thirteenth_name", "It says Tester.", "a thirteenth: yours"),
                          ("thirteenth_blank", "still blank", "you let stay blank")):
    back = came_back(game, "cargo1", ["saved_level_nine", flag], "1.3.0")
    again, aio, _ = start(back)
    expect(again.captain_id == game.captain_id and again.captain_start["parent"] == back["line"]
           and again.captain_start["own_time"] == 30 + 120, "%s: the same captain, a new line, own time 150" % flag)
    expect(history.errand_state(again.errands, "thirteenth_line") == "done", "%s: the errand came back done" % flag)
    play(again, aio, "opening.pod")
    play(again, aio, "hall.first")
    text = flat(play(again, aio, "sight.gamma.plaque", "1", where="Gamma"))
    expect(words in text, "%s: the plaque remembers (%r)" % (flag, words))
    expect(history.errand_state(again.errands, "thirteenth_line") == "done", "%s: and offers no new errand" % flag)
    expect("thought.errand.plaque" not in thoughts(again), "%s: the thought is gone" % flag)
    expect(mine in " ".join(again.story.text_of("floor.mine", again.story.snapshot())), "%s: the deep levels remember it" % flag)
# a Cargo 1 captain who brought the air before the plaque could be cut (or in 1.2.1)
old, oio, _ = start(record("cargo1", "trade", ["saved_level_nine"]))
play(old, oio, "opening.pod")
play(old, oio, "hall.first")
text = flat(play(old, oio, "sight.gamma.plaque", "2", where="Gamma"))
expect("That was you, in 2420" in text and history.errand_state(old.errands, "thirteenth_line") == "none",
       "a Cargo 1 captain who saved level nine: 'that was you', and may leave the line")

# ---- the Kraal vault: the errand to 2460 ---------------------------------------------------------------------
game, io, _ = start(None)
play(game, io, "opening.pod")
expect("sight.delta.conte" not in sights(game, "Delta"), "the Conte waits until the first old friend")
game.story_manager.story_states["first_friend"] = True
expect("sight.delta.conte" in sights(game, "Delta"), "then she sits at Delta")
text = flat(play(game, io, "sight.delta.conte", "1", where="Delta"))
expect("the newest memories first" in text and "Cargo 2 (2.3.0 or newer)" in text, "her loss, and the way back to 2460")
expect(history.errand_state(game.errands, "vault_word") == "open" and "thought.errand.vault" in thoughts(game),
       "the errand is open, and remembered in a thought")
game.turn = 40
for flag, words in (("vault_word_patience", "'Patience,' she said"), ("vault_word_coffee", "your idea"),
                    ("vault_word_tuesday", "It is a Tuesday")):
    back = came_back(game, "cargo2", ["ottavine_patron", "vault_word_known", flag], "2.3.0")
    again, aio, _ = start(back)
    expect(set(again.captain_start["ledger"]) == {"cargo2", "cargo3"}, "%s: 2460 and 2533 in the past" % flag)
    expect("thought.vault_word" in thoughts(again) and "thought.errand.vault" not in thoughts(again),
           "%s: the captain knows the word" % flag)
    again.story_manager.story_states["first_friend"] = True
    text = flat(play(again, aio, "sight.delta.conte", "1", where="Delta"))
    expect(words in text and "The vault opens" in text, "%s: she hears the word and the vault opens" % flag)
    expect(again.person.items.get("procrustes_analyzer") == 1 and again.story_manager.story_states.get("vault_opened"),
           "%s: the Procrustes Analyzer is the captain's" % flag)
    expect(sights(again, "Delta").count("sight.delta.vault") == 1 and "sight.delta.conte" not in sights(again, "Delta"),
           "%s: the vault stands open after" % flag)
# taking neither errand
game, io, _ = start(None)
game.story_manager.story_states["first_friend"] = True
play(game, io, "sight.delta.conte", "2", where="Delta")
expect(history.errand_state(game.errands, "vault_word") == "none" and game.person.items.get("procrustes_analyzer") is None,
       "leaving her to her coffee gives no errand")

# ---- the errands travel through older versions ---------------------------------------------------------------
game, io, _ = start(None)
play(game, io, "opening.pod")
play(game, io, "hall.first")
play(game, io, "sight.gamma.plaque", "1", where="Gamma")
rec = game.captain_record()
notes = history.import_notes(rec, "cargo1", "1.2.1", cargo.story_data()["features"])
expect(len(notes) == 1 and "Cargo 1 1.3.0 or newer" in notes[0], "Cargo 1 1.2.1 would be told to update: %s" % notes)
# what 1.2.1 writes back: no history, its own id; joined again here by name
dropped = {k: v for k, v in json.loads(json.dumps(rec)).items() if k not in history.HISTORY_KEYS}
dropped.update({"id": "C1-12121212", "origin": {"game": "cargo1", "version": "1.2.1"}, "log": []})
dropped["story"] = dict(dropped["story"], flags=["saved_level_nine"])
dropped = captains.clean_captain(sealed(dropped))
for name in os.listdir(cargo.captain_folder()) if os.path.isdir(cargo.captain_folder()) else []:
    os.remove(os.path.join(cargo.captain_folder(), name))
cargo.write_json(os.path.join(cargo.captain_folder(), "ada-cargo3.captain"), rec)
io2 = IO()
patch(cargo, io2)
io2.feed(["y"])
with quiet() as out:
    joined = starting.join_and_tell(dropped)
expect(joined["id"] == rec["id"] and "Cargo 1 1.2.1" in out.getvalue() and "1.3.0" in out.getvalue(),
       "a record that went through 1.2.1 is joined back up, and the note names both versions")
expect(history.errand_state(joined["errands"], "thirteenth_line") == "open", "the errand sent through 1.2.1 stays open")
again, aio, _ = start(joined)
expect("saved_level_nine" in again.captain_start["ledger"]["cargo1"]["flags"]
       and "cargo3" in again.captain_start["ledger"], "and the joined past has 2420 from 1.2.1 and 2533 from before")

# ---- keys from newer games, other lines, hostile histories ------------------------------------------------------
newer = dict(record("cargo3", "", name="Vega Orl"))
newer.update({"devices": {"hausdorff_reader": {"half": "reader"}}, "line": "L-0000AAAA"})
newer = captains.clean_captain(sealed(newer))
game, io, _ = start(newer)
expect(game.captain_record()["devices"] == {"hausdorff_reader": {"half": "reader"}}, "a newer game's key is kept and written out")
mine = game.captain_record()
expect("own record" in game.receive_captain(mine), "a captain cannot take in this very record")
other = dict(mine, line="L-0000FFFF")
expect("crossed" in game.receive_captain(sealed(other)), "the same captain from another line can cross over")
junk = dict(record("cargo2", "", name="Junk"))
junk.update({"own_time": "x", "ledger": {"cargo1": 5, "cargo2": {"flags": list(range(500))}},
             "errands": [{"id": "z" * 99, "to": "cargo1"}, None], "big": ["x"] * 9000, "bad key!": 1})
clean = captains.clean_captain(sealed(junk))
expect(clean["own_time"] == 0 and set(clean["ledger"]) == {"cargo2"} and clean["ledger"]["cargo2"]["flags"] == []
       and len(clean["errands"]) == 1 and len(clean["errands"][0]["id"]) == 32 and "big" not in clean and "bad key!" not in clean,
       "a hostile history is cut down")

# ---- saves from before the history ----------------------------------------------------------------------------------
game, io, _ = start(record("cargo1", "trade", ["saved_level_nine"]))
del game.captain_start
del game.errands
with quiet():
    game.save_game("old")
    loaded = cargo.load_game("old")
expect(isinstance(loaded.captain_start, dict) and "saved_level_nine" in loaded.captain_start["ledger"]["cargo1"]["flags"],
       "a save from before the history gets one, from the record it began as")
loaded.captain_start = []
loaded.errands = "x"
loaded.bring_up_to_date()
expect(isinstance(loaded.captain_start, dict) and loaded.errands == [], "a damaged history in a save is mended")

print("history: %s" % ("ok" if not problems[0] else "%d problems" % problems[0]))
sys.exit(1 if problems[0] else 0)
