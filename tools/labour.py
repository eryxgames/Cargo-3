#!/usr/bin/env python3
"""The labour market (game/labour.py): events at the docks that move a hand's shifts and the
berths board, as the trade events move prices. How they start and end; what each kind does to
wages, jobs, risk, ships, kinds and voyages; how the hand hears of them (the turn's box, the work
and berths screens, arrival, look, word from other docks); the story's stats, effect and news;
saves; every screen at 36 columns.

    python3 tools/labour.py
"""
import os, random, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ["CARGO_SAGA_HOME"] = tempfile.mkdtemp(prefix="cargo3-labour-")
os.environ["NO_COLOR"] = "1"
import headless  # noqa: E402

cargo = headless.load(os.path.join(os.path.dirname(HERE), "game", "world.py"))
EVENTS = cargo.LABOUR_EVENTS
from game.hand import HEAL_PER_TURN  # noqa: E402
problems = []


def expect(ok, what):
    if not ok:
        problems.append(what)
        print("FAIL", what)


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


def flat(text):
    return " ".join(text.replace("│", " ").replace("║", " ").split())


def fresh(place="Alpha", known=()):
    game, io = headless.new_game(cargo)
    game.labour = []
    at(game, place)
    for name in known:
        if name not in game.known_locations:
            game.known_locations.append(name)
    return game, io


# ---- events start, run their turns and end ------------------------------------------------------------
game, io = fresh()
rng = random.Random(11)
seen, counts, overlaps = set(), [], 0
for _ in range(1500):
    game.turn += 1
    game.labour_tick(rng)
    counts.append(len(game.labour))
    taken = set()
    for item in game.labour:
        event = EVENTS[item["id"]]
        loc = game.location_named(item["place"])
        expect(game.labour_can_happen(item["id"], loc), "%s can happen at %s" % (item["id"], item["place"]))
        for scope in game.labour_scopes(event):
            overlaps += (item["place"], scope) in taken
            taken.add((item["place"], scope))
        expect(item["until"] >= game.turn and item["until"] - item["start"] + 1 <= event["turns"][1],
               "%s runs its turns, no more: %s" % (item["id"], item))
        seen.add(item["id"])
expect(seen == set(EVENTS), "every event happens in 1500 turns; never: %s" % sorted(set(EVENTS) - seen))
expect(not overlaps, "never two events on one site, or on one board, at a dock (%d)" % overlaps)
mean = sum(counts) / float(len(counts))
expect(0.6 < mean < 1.8 and max(counts) <= 6, "about one event on at a time across the docks: %.2f (most %d)" % (mean, max(counts)))
plants = [item for item in game.labour if EVENTS[item["id"]].get("site") == "hovertank"]
expect(all(item["place"] == "Delta" for item in plants), "the plant's events are at Delta")

# ---- start, lengthen, collide ---------------------------------------------------------------------------------
game, io = fresh("Delta", known=("Gamma", "Beta"))
game.turn = 10
game.start_labour("plant_rush", "Delta", 3)
expect(game.labour_left("plant_rush") == 3 and game.labour_left("plant_rush", "Gamma") == 0, "an event runs here, for its turns")
game.start_labour("plant_rush", "Delta", 5)
expect(game.labour_left("plant_rush") == 5 and len(game.labour) == 1, "started again, it runs longer, once")
game.start_labour("plant_strike", "Delta", 2)
expect(game.labour_left("plant_strike") == 2 and game.labour_left("plant_rush") == 0, "a strike ends the rush at the same plant")
game.start_labour("drums_harvest", "Delta", 2)
expect(game.labour_left("plant_strike") == 2 and game.labour_left("drums_harvest") == 2, "different sites at a dock keep their own events")
told = game.labour_fresh_lines()
expect(told == [EVENTS[e]["start"] for e in ("plant_strike", "drums_harvest")],
       "what starts here and is still on is told (not the rush the strike ended): %s" % told)
expect(game.labour_fresh_lines() == [], "and only once")
game.turn = 12
game.labour_tick(random.Random(0))
expect(game.labour_left("plant_strike") == 0 and game.labour_left("drums_harvest") == 0, "events end when their turns are up")

# ---- work: wages, closed jobs, risk ---------------------------------------------------------------------------
game, io = fresh("Delta")
plant = next(s for s in cargo.SITES if s["id"] == "hovertank")
ring = next(s for s in cargo.SITES if s["id"] == "ring")
mine = next(s for s in cargo.SITES if s["id"] == "mine")
base = game.shift_wage(90, "mechanic", "hovertank")
game.start_labour("plant_rush", "Delta", 3)
expect(game.shift_wage(90, "mechanic", "hovertank") == int(round(90 * 1.4 / 5.0) * 5) and base == 90,
       "a rush order: four tenths more (%d)" % game.shift_wage(90, "mechanic", "hovertank"))
money = game.person.money
with headless.quiet():
    game.work_shift(plant, plant["jobs"][0], roll=0.5)
expect(game.person.money == money + 125, "and the shift pays it: %d" % (game.person.money - money))
game.start_labour("plant_strike", "Delta", 3)
io.feed([""])
text = flat(screen(game, 36, game.handle_work))
expect("The hovertank assembly plant: no shifts (on strike, 3 turns)" in text and "Line fitter" not in text,
       "a strike: the plant's jobs are not offered, and the strike is named: %s" % text[-300:])
expect("Stevedore at the cargo ring" in text, "the ring still hires")
expect(widest(screen(game, 36, lambda: (io.feed([""]), game.handle_work()))) <= 36, "the work screen fits 36 columns")
at(game, "Alpha")
game.start_labour("ring_audit", "Alpha", 2)
expect(game.shift_wage(55, "broker", "ring") == int(round(55 * 1.6 / 5.0) * 5) and game.shift_wage(60, "loader", "ring") == 60,
       "an audit pays tally clerks six tenths more, stevedores the same")
game.start_labour("ring_agrobots", "Alpha", 2)
expect(game.site_terms("ring", "loader")[2] == "ring_agrobots" and game.site_terms("ring", "broker")[2] is None,
       "an agrobot trial closes the stevedores' shifts only (the audit ended: one event a site)")
at(game, "Gamma")
calm = game.shift_chances("loader")[1]
game.start_labour("mine_seam", "Gamma", 2)
risk = game.site_terms("mine", "loader")[1]
expect(abs(game.shift_chances("loader", risk)[1] - calm - 0.05) < 1e-9 and game.shift_wage(80, "loader", "mine") == 120,
       "a rich seam: half again, and a bad shift a little likelier")
game.start_labour("mine_gas", "Gamma", 1)
io.feed([""])
text = flat(screen(game, 36, game.handle_work))
expect("The deep levels: no shifts (gas, shafts shut, 1 turn)" in text, "gas shuts the deep levels: %s" % text[-300:])
at(game, "Alpha")
game.start_labour("ring_agrobots", "Alpha", 2)
io.feed([""])
text = flat(screen(game, 36, game.handle_work))
expect("Stevedore at the cargo ring: no shifts (agrobot trial, 2 turns)" in text and "Tally clerk" in text,
       "an agrobot trial: no stevedores' shifts, the tally clerks still work")

# ---- the berths board -------------------------------------------------------------------------------------------
def board(place, eid=None, turn=30, ghillie=False):
    game, io = fresh(place)
    game.turn = turn
    if eid:
        game.start_labour(eid, place, 3)
    return game, game.berths()


calm_game, calm = board("Alpha")
for eid, check, what in (
        ("berths_short", lambda b: len(b) == len(calm) + 1 and all(abs(x["wage"] - y["wage"] * 1.4) <= 2 for x, y in zip(b, calm)),
         "crews short: four tenths more, and one more ship"),
        ("berths_glut", lambda b: all(abs(x["wage"] - y["wage"] * 0.7) <= 2 for x, y in zip(b, calm)), "hands cheap: three tenths less"),
        ("berths_convoy", lambda b: len(b) == len(calm) + 2, "a convoy forming: two more ships"),
        ("berths_crackdown", lambda b: len(b) == len(calm) - 1 and all(o["kind"] != "smuggler" for o in b),
         "a crackdown: one ship fewer, and no smugglers"),
        ("berths_delay", lambda b: all(o["legs"] == 3 for o in b if not o["who"]), "the needle delayed: a turn more a voyage")):
    g, b = board("Alpha", eid)
    expect(check(b), "%s: %s" % (what, [(o["kind"], o["wage"], o["legs"]) for o in b]))
def share(eid, kind, turns=range(40, 100)):
    found = total = 0
    for turn in turns:
        g, b = board("Beta", eid, turn)
        found += sum(o["kind"] == kind for o in b if not o["who"])
        total += sum(1 for o in b if not o["who"])
    return found / float(total)


for eid, kind, usual, what in (("berths_convoy", "hauler", 0.5, "a convoy: mostly haulers"),
                               ("berths_pilgrimage", "tail", 1 / 6.0, "a pilgrimage: tail ships")):
    calm_share, busy_share = share(None, kind), share(eid, kind)
    expect(abs(calm_share - usual) < 0.12 and busy_share > 0.45 and busy_share > calm_share + 0.1, "%s (%.2f, usually %.2f)" % (what, busy_share, calm_share))
# Jak Ghillie stays dark in a crackdown
game, io = fresh("Gamma")
turn = next(t for t in range(200) if game.story.where_is("ghillie", t) == "Gamma" and game.story.where_is("ghillie", t + 1) != "Gamma")
game.turn = turn
expect(any(o["who"] == "ghillie" for o in game.berths()), "Jak Ghillie hires at Gamma on his turn there")
game.start_labour("berths_crackdown", "Gamma", 2)
expect(not any(o["who"] == "ghillie" or o["kind"] == "smuggler" for o in game.berths()),
       "in a crackdown Jak Ghillie's Low Water hires nobody")
io.feed([""])
text = screen(game, 36, game.handle_berths)
expect(widest(text) <= 36 and "Berths: customs crackdown (no smugglers, 2 turns)" in flat(text), "the board names the crackdown, at 36 columns")
# trouble on the way: a crackdown makes the way a little quieter
offer = dict(game.berths()[0])
expect(offer["risk"] == EVENTS["berths_crackdown"]["risk"], "the offer carries the board's risk")

# ---- telling the hand -------------------------------------------------------------------------------------------
game, io = fresh("Alpha", known=("Gamma", "Delta"))
game.turn = 5
game.start_labour("ring_convoy", "Alpha", 2)
game.start_labour("mine_gas", "Gamma", 2)
game.start_labour("plant_strike", "Delta", 2)
text = screen(game, 36, game.display_turn_info)
expect(widest(text) <= 36, "the turn's screen fits 36 columns with an event on")
expect("Ring: a convoy unloading (pay +40%, 2 turns)" in flat(text), "the turn's screen names what is on here")
expect(EVENTS["ring_convoy"]["start"].split(":")[0] in flat(text), "and the turn it starts, what it means")
expect(EVENTS["ring_convoy"]["start"].split(":")[0] not in flat(screen(game, 36, game.display_turn_info)), "once")
news = game.labour_news()
expect(news == ["a strike at Delta's hovertank plant", "gas in Gamma's deep levels"] or
       sorted(news) == sorted(["a strike at Delta's hovertank plant", "gas in Gamma's deep levels"]),
       "word from the other docks: %s" % news)
game.start_labour("drums_harvest", "Beta", 2)
expect(not any("Beta" in n for n in game.labour_news()), "only from docks the captain knows of")
lines = " ".join(game.happenings())
expect("Ring: a convoy unloading" in lines and "Word on the ring:" in lines, "look tells what is on, here and elsewhere")
io.feed([""])
text = screen(game, 36, game.handle_look)
expect(widest(text) <= 36, "look fits 36 columns with the news")
with headless.quiet() as out:
    game.arrive_on_foot(game.location_named("Gamma"), ["Passage to Gamma."])
expect(EVENTS["mine_gas"]["start"] in flat(out.getvalue()), "arriving where something is on, the hand is told")

# ---- the story: stats, the effect, the news ------------------------------------------------------------------------
game, io = fresh("Gamma", known=("Delta",))
game.turn = 9
game.start_labour("mine_seam", "Gamma", 3)
game.start_labour("plant_strike", "Delta", 2)
stats = game.story_snapshot()["stats"]
expect(stats["labour.mine_seam"] == 3 and stats["labour.plant_strike"] == 0 and stats["labour.ring_audit"] == 0,
       "the story sees what is on here, in turns left")
game.story.apply({"labour.berths_short": 2})
expect(game.labour_left("berths_short") == 2, "a story effect starts an event here")
expect(game.story.fill("{labour_news}") == "A strike at Delta's hovertank plant.", "{labour_news}: %s" % game.story.fill("{labour_news}"))
game.labour = []
expect(game.story.fill("{labour_news}") == "nothing much on at the other docks.", "and when nothing is on")

# ---- what the hand can do about it ------------------------------------------------------------------------------------
ACTIONS = cargo.LABOUR_ACTIONS


def act(game, eid, aid, roll):
    """An action, with nothing new starting at the docks during its turn (so what it ends stays ended)."""
    action = next(a for a in ACTIONS[eid] if a["id"] == aid)
    game.labour_tick = lambda: None
    try:
        with headless.quiet() as out:
            outcome = game.do_labour_action(eid, action, roll=roll)
    finally:
        del game.labour_tick
    return outcome, flat(out.getvalue())


game, io = fresh("Delta")
game.turn = 20
game.start_labour("plant_strike", "Delta", 2)
shown, _ = game.work_options()
offered = [d[1]["id"] for kind, d, _ in shown if kind == "action"]
expect(offered == ["cross", "picket"], "a strike: cross the line or stand with the picket (settling needs an able steward): %s" % offered)
money, turn = game.person.money, game.turn
outcome, text = act(game, "plant_strike", "cross", 0.0)
expect(outcome == "success" and game.person.money == money + 2 * game.shift_wage(90, "mechanic") and game.turn == turn + 1,
       "crossing the line pays a line fitter's shift twice over, and takes the turn")
expect(game.labour_left("plant_strike") == 2 and game.labour_marks()["crossed"] == 1,
       "a crossed line keeps the strike going a turn longer, and is remembered")
picket = next(a for a in ACTIONS["plant_strike"] if a["id"] == "picket")
expect(abs(game.labour_action_chance(picket) - 0.2) < 1e-9, "the pickets remember a line crosser: their odds fall a tenth")
game.person.skills["steward"] = 2
expect("settle" in [d[1]["id"] for kind, d, _ in game.work_options()[0] if kind == "action"], "an able steward can try to settle it")
money = game.person.money
outcome, text = act(game, "plant_strike", "settle", 0.0)
expect(outcome == "success" and game.person.money == money + 150 and game.labour_left("plant_strike") == 0
       and game.labour_left("plant_rush") == 3 and game.labour_marks()["settled"] == 1,
       "settled: a fee, the strike over, and a backlog that pays (a rush order)")
expect(game.story_snapshot()["stats"]["work.settled"] == 1 and game.story_snapshot()["stats"]["work.crossed"] == 1,
       "the story sees what the hand did")
game.start_labour("plant_strike", "Delta", 2)
outcome, text = act(game, "plant_strike", "settle", 0.99)
expect(outcome == "failure" and game.labour_left("plant_strike") == 1 and game.person.wounds > 0,
       "a failed settlement: shouting, something thrown, the strike goes on")
io.feed([""])
text = screen(game, 36, game.handle_work)
expect(widest(text) <= 36, "the work screen with actions fits 36 columns")

game, io = fresh("Gamma")
game.start_labour("mine_gas", "Gamma", 3)
money = game.person.money
outcome, text = act(game, "mine_gas", "clear", 0.0)
expect(outcome == "success" and game.person.money == money + 150 and game.labour_left("mine_gas") == 0,
       "the gas cleared with the fire boss: 150, and the shafts open")
game.start_labour("mine_gas", "Gamma", 3)
outcome, text = act(game, "mine_gas", "clear", 0.99)
expect(outcome == "failure" and game.person.wounds >= 15 - HEAL_PER_TURN and game.labour_left("mine_gas") == 2,
       "or dragged back up the ladder, hurt, and the shafts stay shut")

game, io = fresh("Beta")
game.start_labour("drums_blight", "Beta", 3)
outcome, text = act(game, "drums_blight", "seed", 0.0)
expect(game.labour_left("drums_blight") == 0 and game.labour_left("drums_harvest") == 2, "the seed saved: a small harvest follows")
game.start_labour("ring_agrobots", "Beta", 3)
outcome, text = act(game, "ring_agrobots", "race", 0.0)
expect(game.labour_left("ring_agrobots") == 0, "the agrobots beaten on the stack: the trial ends")
game.start_labour("ring_quiet", "Beta", 3)
outcome, text = act(game, "ring_quiet", "lure", 0.0)
expect(game.labour_left("ring_quiet") == 0 and game.labour_left("ring_convoy") == 2, "a hauler talked in: the quiet ring gets a convoy")

game, io = fresh("Alpha")
game.turn = 30
game.start_labour("berths_crackdown", "Alpha", 3)
offers = game.berths()
actions = game.labour_actions_here("berths")
expect([a["id"] for _, a in actions] == ["run", "inform"], "a crackdown: run cargo past it, or inform")
io.feed([str(len(offers) + 1)])
money = game.person.money
with headless.quiet():
    game.handle_berths()
expect(game.labour_marks().get("ran_the_crackdown") == 1 and game.person.money in (money + 300, money - min(money, 200)),
       "the board offers the actions after its ships")
game.start_labour("berths_crackdown", "Alpha", 3)
money, mandate = game.person.money, game.standing_of("mandate")
outcome, text = act(game, "berths_crackdown", "run", 0.99)
expect(game.person.money == money - min(money, 200) and game.standing_of("mandate") == mandate - 3, "caught: fined, and on a list")
money, mandate = game.person.money, game.standing_of("mandate")
left = game.labour_left("berths_crackdown")
outcome, text = act(game, "berths_crackdown", "inform", 0.99)
expect(outcome == "success" and game.person.money == money + 80 and game.standing_of("mandate") == mandate + 2
       and game.labour_left("berths_crackdown") == left + 1, "informing always works: 80, the Mandate pleased, the crackdown longer")
game.start_labour("berths_glut", "Alpha", 3)
act(game, "berths_glut", "organise", 0.0)
expect(game.labour_left("berths_glut") == 0, "a glut organised away")
game.start_labour("berths_delay", "Alpha", 3)
money = game.person.money
outcome, text = act(game, "berths_delay", "grease", 0.5)
expect(game.labour_left("berths_delay") == 0 and game.person.money == money - 100, "100 to the needle office, and the needle is on time")
game.person.money = 50
game.start_labour("berths_delay", "Alpha", 3)
expect(not game.labour_actions_here("berths"), "no money, no greasing")
io.feed([""])
game.person.money = 500
text = screen(game, 36, game.handle_berths)
expect(widest(text) <= 36 and "Pay the needle office" in flat(text), "the board's actions fit 36 columns")

# ---- saves --------------------------------------------------------------------------------------------------------
game, io = fresh("Delta")
game.turn = 4
game.start_labour("plant_strike", "Delta", 3)
with headless.quiet():
    game.save_game("labour")
    loaded = cargo.load_game("labour")
expect(loaded.labour_left("plant_strike") == 3, "a save keeps what is on")
loaded.labour = [{"id": "nonsense", "place": "Delta", "until": 9}, "x", {"id": "plant_rush", "place": 3, "until": 9},
                 {"id": "mine_gas", "place": "Gamma", "until": True}, {"id": "ring_quiet", "place": "Alpha", "until": 9}]
loaded.bring_up_to_date()
expect([e["id"] for e in loaded.labour] == ["ring_quiet"], "a damaged list is mended: %s" % loaded.labour)
del loaded.labour
with headless.quiet():
    loaded.save_game("older")
    older = cargo.load_game("older")
expect(older.labour == [], "a save from before the labour market starts with nothing on")
expect(isinstance(older.labour_marks(), dict), "and remembers nothing done")

print("labour: %s" % ("ok" if not problems else "%d problems" % len(problems)))
sys.exit(1 if problems else 0)
