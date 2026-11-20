#!/usr/bin/env python3
"""Fights on foot (game/brawl.py): the odds of every order and what moves them (skills, gear,
wounds, allies, a guard, how hurt they are), every way a fight ends (won, talked, ran, paid,
robbed, locked up, dragged clear, dead), trouble at the docks (when, where, who, how often),
the outfitter, the picket line, the story's `brawl` hook, the story's stats, saves, the screens at
36 columns, and with the bot: how often a hand fights, and that a careful one does not die.

    python3 tools/brawl.py
"""
import json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ["CARGO_SAGA_HOME"] = tempfile.mkdtemp(prefix="cargo3-brawl-")
os.environ["NO_COLOR"] = "1"
import headless  # noqa: E402

cargo = headless.load(os.path.join(os.path.dirname(HERE), "game", "world.py"))
import game.brawl as brawl  # noqa: E402
import game.story as story  # noqa: E402
FOES, GEAR = brawl.FOES, brawl.GEAR
problems = []


def expect(ok, what):
    if not ok:
        problems.append(what)
        print("FAIL", what)


def screen(cols, show):
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


def flat(text):
    return " ".join(text.replace("│", " ").replace("║", " ").split())


def fresh(place="Beta", money=900, gear=()):
    game, io = headless.new_game(cargo)
    game.labour = []
    game.current_location = game.location_named(place)
    game.person.money = money
    game.person.gear = list(gear)
    game.turn = 10
    return game, io


def scripted(game, keys, shown=None):
    """Answer the fight's rounds with these orders; keep what each round offered (and showed)."""
    offered = []

    def ask(title, lines, options, default):
        offered.append([k for k, _ in options])
        if shown is not None:
            shown.extend(lines)
        return keys.pop(0)
    game.ask_move = ask
    return offered


def fight(game, foe, keys, rolls, **kw):
    shown = []
    offered = scripted(game, list(keys), shown)
    with headless.quiet() as out:
        outcome = game.brawl(foe, rolls=rolls, **kw)
    return outcome, flat(" ".join(shown) + " " + out.getvalue()), offered


def near(a, b):
    return abs(a - b) < 1e-9


# ---- the odds -----------------------------------------------------------------------------------------
game, io = fresh()
state = {"marks": 2}
expect(near(game.brawl_odds("strike", "dock_tough", state), 0.37), "a bare-handed untried strike at a dock tough: 0.37")
game.person.gear = ["knife"]
game.person.skills["gunner"] = 2
expect(near(game.brawl_odds("strike", "dock_tough", state), 0.61), "a knife and an able gunner: 0.61")
expect(near(game.brawl_odds("strike", "dock_tough", dict(state, read=True)), 0.76), "after a guard: 0.15 more")
game.person.wounds = 50
expect(near(game.brawl_odds("strike", "dock_tough", state), 0.41), "fifty wounds: a fifth less")
game.person.wounds = 0
expect(near(game.brawl_odds("strike", "dock_tough", dict(state, edge=2)), 0.71), "two allies: a tenth more")
expect("shoot" not in [k for k, _ in game.brawl_options("dock_tough", state)], "nothing to shoot with, no shooting")
game.person.gear = ["knife", "rivet gun", "stunner"]
expect(game.gear_best("ranged") == "stunner", "the stunner before the rivet gun (same odds, dearer)")
expect("shoot" in [k for k, _ in game.brawl_options("dock_tough", state)], "a gun: shoot")
expect([k for k, _ in game.brawl_options("feral_loader", {"marks": 3})] == ["strike", "shoot", "grapple", "guard", "run"],
       "an agrobot gone wild does not talk and wants no money")
expect(near(game.brawl_odds("talk", "dock_tough", {"marks": 1}) - game.brawl_odds("talk", "dock_tough", {"marks": 2}), 0.08),
       "hurt them, and they listen better")
game.person.skills["broker"] = 3
expect(game.talk_skill(FOES["dock_tough"]) == "broker" and game.talk_skill(FOES["company_guards"]) == "broker",
       "talk as the better of steward and broker; papers to the company guards")
game.person.skills["steward"] = 4
expect(game.talk_skill(FOES["dock_tough"]) == "steward" and game.talk_skill(FOES["mandate_troopers"]) == "broker",
       "the Mandate reads papers, whoever talks better")
talk = game.brawl_odds("talk", "mandate_troopers", {"marks": 4})
game.person.gear.append("slug pistol")
expect(near(talk - game.brawl_odds("talk", "mandate_troopers", {"marks": 4}), 0.15), "a slug pistol: the Mandate listens less")
run = game.brawl_odds("run", "dock_tough", state)
expect(near(run - game.brawl_odds("run", "claim_jumpers", state), 0.15), "running from people who shoot is harder")
game.person.gear.append("exoskeleton knees")
expect(near(game.brawl_odds("run", "dock_tough", state) - run, 0.10), "exoskeleton knees: running")
expect(near(game.brawl_odds("grapple", "dock_tough", state), 0.40 + 0.15 - 0.08), "and grappling")
game, io = fresh()
expect(near(game.foe_hit_chance("dock_tough", {}, "strike"), 0.37), "a dock tough's blow lands at 0.37")
expect(near(game.foe_hit_chance("dock_tough", {}, "guard"), 0.17), "a guard: 0.2 less")
expect(near(game.foe_hit_chance("dock_tough", {}, "shoot"), 0.27), "shooting a man with a chain: from a distance")
expect(near(game.foe_hit_chance("claim_jumpers", {}, "shoot"), 0.44), "not a man with a rivet gun")
expect(near(game.foe_hit_chance("dock_tough", {}, "run", free=True), 0.52), "a failed run: a free blow")
game.person.gear = ["vacuum suit"]
expect(near(game.foe_hit_chance("dock_tough", {}, "strike"), 0.40), "a vacuum suit slows you")
game.person.money = 900
expect(game.brawl_toll(FOES["dock_tough"]) == 225, "a dock tough wants a quarter of the purse")
game.person.money = 20000
expect(game.brawl_toll(FOES["dock_tough"]) == 300, "but no more than 300: a hand's savings are not in one pocket")
game.person.money = 100
expect(game.brawl_toll(FOES["dock_tough"]) == 40, "and at least 40")
game.person.money = 25
expect(game.brawl_toll(FOES["dock_tough"]) == 25, "or what there is")
game.person.money = 0
expect("pay" not in [k for k, _ in game.brawl_options("dock_tough", state)], "nothing to pay with, no paying")

# ---- how fights end -----------------------------------------------------------------------------------
game, io = fresh(money=500)
practice = game.person.practice["gunner"]
outcome, text, offered = fight(game, "dock_tough", ["strike", "strike"], [0.0, 0.99, 0.0])
expect(outcome == "won" and "You find" in text and game.person.money > 500 and game.story_manager.plot_points >= 1,
       "two blows, a dock tough beaten: his purse and a plot point")
expect(game.story_manager.story_states.get("fight_won_dock_tough") and game.brawls == {"won": 1},
       "the story knows it was won")
expect(game.person.practice["gunner"] == practice + 1 or game.person.skill("gunner") == 1, "and the gunner's practice")
expect(offered[0] == ["strike", "grapple", "guard", "talk", "run", "pay"], "the orders: %s" % offered[0])
game, io = fresh(gear=["cutting torch"])
outcome, text, _ = fight(game, "dock_tough", ["strike"], [0.0])
expect(outcome == "won", "a cutting torch: one blow counts twice")
game, io = fresh()
outcome, text, _ = fight(game, "dock_tough", ["grapple", "grapple"], [0.0, 0.0])
expect(outcome == "won" and game.person.wounds == 0 and "in a hold" in text, "a hold: they cannot hit back")
game, io = fresh(gear=["stunner"])
outcome, text, _ = fight(game, "cargolyte_stevedores", ["shoot", "shoot", "shoot"], [0.0, 0.0, 0.0])
expect(outcome == "won" and game.person.wounds == 0 and "stunner" in text, "a stunner: no blow back after a hit")
game, io = fresh()
outcome, text, _ = fight(game, "dock_tough", ["guard", "strike", "strike"], [0.99, 0.0, 0.99, 0.0])
expect(outcome == "won" and "watch how they move" in text and game.person.wounds == 0, "a guard, then two blows")
game, io = fresh()
outcome, text, _ = fight(game, "dock_tough", ["talk"], [0.0])
expect(outcome == "talked" and "weather" in text and game.story_manager.story_states.get("fight_talked_dock_tough"),
       "talked down")
game, io = fresh()
outcome, text, _ = fight(game, "dock_tough", ["talk", "run"], [0.99, 0.0, 0.0])
expect(outcome == "ran" and "not listening" in text and game.person.wounds > 0, "not listening, a free blow, then away")
game, io = fresh(money=1000)
outcome, text, _ = fight(game, "dock_tough", ["pay"], [])
expect(outcome == "paid" and game.person.money == 750 and "count it twice" in text, "paid off: 250")

game, io = fresh(money=1000, gear=["knife", "work suit"])
game.person.wounds = 85
turn = game.turn
outcome, text, _ = fight(game, "dock_tough", ["strike"], [0.99, 0.0, 0.2])
expect(outcome == "robbed" and game.person.money == 750 and "pockets inside out" in text, "down: robbed of what they wanted")
expect("knife" not in game.person.gear and "took your knife" in text and "work suit" in game.person.gear,
       "and sometimes the best weapon too")
expect(game.turn == turn + 2 and game.person.wounds == 70, "two turns lost, resting: %d" % game.person.wounds)
expect(game.story_manager.story_states.get("fight_lost_dock_tough") and game.brawls == {"robbed": 1}, "the story knows")
game, io = fresh("Gamma", money=1000, gear=["slug pistol"])
game.person.wounds = 85
outcome, text, _ = fight(game, "company_guards", ["strike"], [0.99, 0.0])
expect(outcome == "carried" and game.person.money == 920 and "lock-up" in text, "the company's guards lock a hand up: a fine")
game, io = fresh(money=1000, gear=["slug pistol"])
game.person.wounds = 85
outcome, text, _ = fight(game, "mandate_troopers", ["strike"], [0.99, 0.0])
expect(outcome == "carried" and game.person.money == 800 and "slug pistol" not in game.person.gear,
       "the Mandate: a holding cell, a fine and the pistol")
game, io = fresh()
game.person.wounds = 85
outcome, text, _ = fight(game, "pickets", ["strike"], [0.99, 0.0])
expect(outcome == "saved" and "medic" in text, "the pickets do not rob: the plant's medic patches you")
game, io = fresh()
game.person.wounds = 85
outcome, text, _ = fight(game, "feral_loader", ["strike"], [0.99, 0.0, 0.1])
expect(outcome == "dead" and game.person.wounds == cargo.WOUNDS_DEAD and "stacks you" in text,
       "a loader gone wild can kill (a sixth of the time a hand goes down)")
game, io = fresh()
game.person.wounds = 85
outcome, text, _ = fight(game, "feral_loader", ["strike"], [0.99, 0.0, 0.5])
expect(outcome == "saved" and game.person.wounds < cargo.WOUNDS_DOWN, "or the stevedores drag you out")
game, io = fresh()
outcome, text, offered = fight(game, "grey_men", ["run"], [0.0])
expect("They mean to kill" in text and outcome == "ran", "killers are named as killers")

# ---- trouble at the docks -----------------------------------------------------------------------------
game, io = fresh("Beta", money=0)
expect(near(game.trouble_chance(), 0.04), "an ordinary dock, an empty purse: 1 turn in 25")
game.person.money = 3000
expect(near(game.trouble_chance(), 0.08), "3,000 in the purse: twice as likely")
game.person.money = 50000
expect(near(game.trouble_chance(), 0.12), "and at most three times")
game.person.money = 0
game.current_location = game.location_named("Gamma")
expect(near(game.trouble_chance(), 0.06), "Gamma is rough")
game.current_location = game.location_named("Alpha")
expect(near(game.trouble_chance(), 0.02), "Alpha is the Mandate's")
game.turn = 3
expect(game.trouble_chance() == 0, "nothing in the first turns")
game.turn = 20
game.last_brawl = 18
expect(game.trouble_chance() == 0, "nor right after a fight")
game.last_brawl = 16
expect(game.trouble_chance() > 0, "four turns after, again")
pools = {}
for place in ("Alpha", "Beta", "Gamma", "Delta", "Epsilon"):
    game.current_location = game.location_named(place)
    pools[place] = sorted(f for f, _ in game.trouble_foes())
expect(pools["Alpha"] == ["dock_tough", "pickpockets"] and pools["Beta"] == ["cargolyte_stevedores", "dock_tough", "pickpockets"]
       and pools["Gamma"] == ["cargolyte_stevedores", "company_guards", "dock_tough", "pickpockets"],
       "who turns up where: %s" % pools)
game.current_location = game.location_named("Gamma")
game.start_labour("mine_seam", "Gamma", 3)
expect("claim_jumpers" in [f for f, _ in game.trouble_foes()] and near(game.trouble_chance(), 0.12),
       "a rich seam brings claim jumpers, and trouble")
game.current_location = game.location_named("Beta")
game.start_labour("ring_agrobots", "Beta", 3)
expect("feral_loader" in [f for f, _ in game.trouble_foes()], "an agrobot trial, now and then an agrobot gone wild")
game, io = fresh("Beta")
expect(game.dock_trouble(roll=0.99) is None, "no trouble on a high roll")
scripted(game, ["pay"] * 3 + ["talk"] * 3 + ["run"] * 6)
with headless.quiet():
    outcome = game.dock_trouble(roll=0.0)
expect(outcome in ("paid", "talked", "ran", "robbed", "saved") and game.last_brawl == game.turn - (2 if outcome in ("robbed", "saved") else 0),
       "trouble on a low roll: a fight (%s)" % outcome)

# the hand's turn: trouble comes before the choice; a hand who goes down loses the turn
def choices(game):
    """Note the turn's choice of action (and rest), leave the other prompts to the game."""
    asked = []
    plain = game.validate_input

    def validate(prompt, valid, *a, **k):
        if prompt.startswith("Choose action"):
            asked.append(game.turn)
            return "end"
        return plain(prompt, valid, *a, **k)
    game.validate_input = validate
    return asked


game, io = fresh("Beta")
game.trouble_chance = lambda: 1.0
game.trouble_foes = lambda: [("pickpockets", 1)]
scripted(game, ["talk"] * 4 + ["pay"])
asked = choices(game)
with headless.quiet():
    game.play_hand_turn()
expect(game.brawls and asked == [10] and game.turn == 11, "a fight, then the turn goes on: %s" % asked)
game, io = fresh("Beta")
game.person.wounds = 89
game.trouble_chance = lambda: 1.0
game.trouble_foes = lambda: [("pickets", 1)]
game.foe_hit_chance = lambda *a, **k: 1.0
scripted(game, ["strike"] * 5)
game.brawl_odds = lambda *a, **k: 0.0
asked = choices(game)
with headless.quiet():
    game.play_hand_turn()
expect(asked == [] and game.turn == 12 and game.brawls == {"saved": 1}, "down: two turns lost, and no choice")

# ---- the outfitter -----------------------------------------------------------------------------------
for place, sold in (("Alpha", ("knife", "stunner", "work suit")), ("Delta", ("cutting torch", "exoskeleton knees", "rivet gun")),
                    ("Epsilon", ("stunner", "vacuum suit", "slug pistol"))):
    game, io = fresh(place)
    expect(game.outfitter_here() == sold, "%s sells %s" % (place, ", ".join(sold)))
expect(set(n for sold in brawl.OUTFITTERS.values() for n in sold) == set(GEAR), "everything is sold somewhere")
game, io = fresh("Delta", money=1000)
io.feed(["2"])
with headless.quiet():
    game.handle_gear()
expect(game.person.gear == ["exoskeleton knees"] and game.person.money == 200, "exoskeleton knees at Delta: 800")
io.feed(["2"])
with headless.quiet() as out:
    game.handle_gear()
expect(game.person.money == 200 and "already have" in flat(out.getvalue()), "not twice")
io.feed(["1"])
with headless.quiet() as out:
    game.handle_gear()
expect(game.person.money == 200 and "costs 600" in flat(out.getvalue()), "not without the money (450, and three tenths more for the knees)")
game.current_location = type("Place", (), {"name": "Wolf 359", "location_type": "ResearchColony"})()
with headless.quiet() as out:
    game.handle_gear()
expect("Nobody here sells gear" in flat(out.getvalue()), "a research colony has no outfitter")
game, io = fresh("Gamma", money=5000)
io.feed([""])
text = screen(36, game.handle_gear)
expect(widest(text) <= 36 and "Cutting torch, 450" in flat(text), "the outfitter fits 36 columns")
game.person.gear = ["work suit", "vacuum suit", "knife", "cutting torch"]
expect(game.gear_best("armour") == "vacuum suit" and game.gear_best("melee") == "cutting torch", "the best of each kind")

# ---- the picket line, and the story ----------------------------------------------------------------------
game, io = fresh("Delta")
game.start_labour("plant_strike", "Delta", 2)
cross = next(a for a in cargo.LABOUR_ACTIONS["plant_strike"] if a["id"] == "cross")
scripted(game, ["talk"] * 6 + ["run"] * 6)
with headless.quiet() as out:
    game.do_labour_action("plant_strike", cross, roll=0.99)
expect(game.brawls and any(k.endswith("_pickets") for k, v in game.story_manager.story_states.items() if v),
       "a crossed picket line that goes wrong: a fight at the gate")
game, io = fresh()
scripted(game, ["pay"])
with headless.quiet():
    story.story_hook(game, "brawl dock_tough")
expect(game.brawls, "the story can start a fight on foot ('brawl <foe>')")
game, io = fresh()
seen = {}
game.brawl = lambda foe, edge=0, **k: seen.update(foe=foe, edge=edge)
story.story_hook(game, "brawl grey_men edge 2")
expect(seen == {"foe": "grey_men", "edge": 2}, "with allies ('brawl <foe> edge <n>')")
game, io = fresh(gear=["knife"])
game.brawls = {"won": 2, "robbed": 1, "talked": 1}
stats = game.story_snapshot()["stats"]
expect(stats["brawls"] == 4 and stats["brawls.won"] == 2 and stats["brawls.lost"] == 1 and stats["armed"] == 1,
       "the story's stats: %s" % {k: stats[k] for k in ("brawls", "brawls.won", "brawls.lost", "armed")})

# ---- saves ----------------------------------------------------------------------------------------------
game, io = fresh(gear=["stunner", "work suit"])
game.brawls = {"won": 3}
with headless.quiet():
    game.save_game("brawl")
    loaded = cargo.load_game("brawl")
expect(loaded.person.gear == ["stunner", "work suit"] and loaded.brawls == {"won": 3}, "a save keeps gear and fights")
del loaded.__dict__["brawls"]
loaded.bring_up_to_date()
expect(loaded.brawl_counts() == {}, "a save from before fights on foot has none")

# ---- every screen at 36 columns --------------------------------------------------------------------------
game, io = fresh(money=900, gear=["knife", "rivet gun", "work suit", "exoskeleton knees"])
io.feed(["6", "", ""])
text = screen(36, lambda: game.brawl("cargolyte_stevedores"))
expect(widest(text) <= 36 and "Your move" in text, "a fight fits 36 columns")
game, io = fresh()
text = screen(36, game.show_hand_help)
expect(widest(text) <= 36 and "strike, shoot" in flat(text), "the help tells of fights on foot")

# ---- with the bot: how often a hand fights, and that a careful one lives -------------------------------------
if "--quick" not in sys.argv:
    runs = []
    for seed in (1, 2, 3):
        out = subprocess.run([sys.executable, os.path.join(HERE, "bot.py"), os.path.join(os.path.dirname(HERE), "game", "world.py"),
                              "trade", str(seed), "150", "--curious", "--ashore"],
                             capture_output=True, text=True, timeout=900, env=dict(os.environ, CARGO_SOUND="0"))
        runs.append(json.loads(out.stdout.strip().splitlines()[-1]))
    fights = [sum(r.get("brawls", {}).values()) for r in runs]
    expect(all(3 <= n <= 20 for n in fights), "a hand fights now and then, by turn 150: %s" % fights)
    expect(all(r["wounds"] < cargo.WOUNDS_DEAD and r["turn"] >= 150 for r in runs), "and a careful one lives")
    expect(all(r.get("gear") for r in runs), "and buys gear")
    print("bot by turn 150: fights %s; endings %s" % (fights, [r.get("brawls") for r in runs]))

print("brawl: %s" % ("ok" if not problems else "%d problems" % len(problems)))
sys.exit(1 if problems else 0)
