#!/usr/bin/env python3
"""What a hand's money buys (game/training.py): implants at the clinic and lessons with the
masters. The price curves, what each gives, the limits (skilled is the top for implants, the
surgeon will not cut a hurt hand), the screens at 36 columns, saves, and the balance the bot
measures (money and skills by turn 120, with and without spending).

    python3 tools/training.py
"""
import json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ["CARGO_SAGA_HOME"] = tempfile.mkdtemp(prefix="cargo3-training-")
os.environ["NO_COLOR"] = "1"
import headless  # noqa: E402

cargo = headless.load(os.path.join(os.path.dirname(HERE), "game", "world.py"))
import game.training as training  # noqa: E402
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


def flat(text):
    return " ".join(text.replace("│", " ").replace("║", " ").split())


def fresh(place="Epsilon", money=50000):
    game, io = headless.new_game(cargo)
    game.labour = []
    game.current_location = game.location_named(place)
    game.person.money = money
    return game, io


# ---- the curves ---------------------------------------------------------------------------------------
expect([training.implant_price(level, 0) for level in range(1, 5)] == [500, 2000, 4500, 8000],
       "implants: 500, 2,000, 4,500 and 8,000 for green to skilled")
expect(training.implant_price(4, 3) == 15200 and training.implant_price(1, 2) == 800,
       "each implant fitted makes the next dearer by three tenths: %s" % training.implant_price(4, 3))
expect([training.lesson_price(level) for level in range(5)] == [40, 160, 360, 640, 1000]
       and [training.lesson_practice(level) for level in range(5)] == [1, 3, 5, 7, 9],
       "lessons: 40 to 1,000, teaching 1 to 9 practice")
expect(all(training.implant_price(level + 1, 0) > 4 * training.lesson_price(level) for level in range(4)),
       "an implant always costs more than four lessons at the same level")

# ---- implants -------------------------------------------------------------------------------------------
game, io = fresh()
with headless.quiet():
    fitted = game.implant_clinic(pick="3", sure=True)
expect(fitted == "gunner" and game.person.skill("gunner") == 1 and game.person.money == 50000 - 500
       and game.person.wounds == 15 and game.person.implants == {"gunner": 1},
       "a gunner implant: green, 500, 15 wounds (10 and 5 a level)")
with headless.quiet():
    game.implant_clinic(pick="3", sure=True)
expect(game.person.skill("gunner") == 2 and game.person.money == 50000 - 500 - 2600 and game.person.wounds == 35,
       "the next, to able: 2,000 and three tenths for the one fitted (2,600), 20 wounds")
with headless.quiet():
    refused = game.implant_clinic(pick="3", sure=True)
game.person.wounds = 35
expect(refused == "gunner", "35 wounds is still not too hurt")
game.person.wounds = 60
with headless.quiet() as out:
    refused = game.implant_clinic(pick="3", sure=True)
expect(refused is None and "too hurt for surgery" in flat(out.getvalue()), "the surgeon will not cut a hand hurt worse than 50")
game.person.wounds = 0
game.person.skills["navigator"] = 4
with headless.quiet() as out:
    refused = game.implant_clinic(pick="4", sure=True)
expect(refused is None and "a master's level is earned, not fitted" in flat(out.getvalue()), "nothing is fitted above skilled")
game.person.money = 100
with headless.quiet() as out:
    refused = game.implant_clinic(pick="5", sure=True)
expect(refused is None and "you cannot pay it" in flat(out.getvalue()), "no money, no implant")
game.person.money = 5000
with headless.quiet():
    left = game.implant_clinic(pick="", sure=True)
expect(left is None and game.person.money == 5000, "Enter leaves the catalogue")
game.person.practice["steward"] = 2
with headless.quiet():
    game.implant_clinic(pick="5", sure=True)
expect(game.person.practice["steward"] == 0 and "steward" not in game.person.next_at,
       "an implant starts the new level's practice from nothing, with a new draw")
text = screen(36, lambda: game.implant_clinic(pick="", sure=False))
expect(max(cargo.visible_len(line) for line in text.splitlines()) <= 36, "the catalogue fits 36 columns")
expect(game.story_snapshot()["stats"]["implants"] == 4, "the story counts implants")
# the clinic's sight opens the catalogue (the story's code effect)
expect("implants" in cargo.STORY_HOOKS, "the story can open the catalogue")

# ---- lessons ----------------------------------------------------------------------------------------------
masters = {place: [s for s, _ in teachers] for place, teachers in training.MASTERS.items()}
expect(sorted(s for skills in masters.values() for s in skills) == sorted(cargo.SKILLS),
       "every skill has a master somewhere, and only one: %s" % masters)
game, io = fresh("Delta", money=1000)
offers = game.lessons_here()
expect([o[0] for o in offers] == ["mechanic", "gunner"] and offers[0][2:] == (40, 1), "Delta teaches mechanic and gunner")
shown, _ = game.work_options()
lessons = [i for i, (kind, _, _) in enumerate(shown) if kind == "lesson"]
expect(len(lessons) == 2 and "A lesson with the plant's line chief: mechanic practice, 40" in shown[lessons[0]][2],
       "the work screen offers the lessons after the jobs")
turn = game.turn
io.feed([str(lessons[0] + 1)])
with headless.quiet():
    game.handle_work()
expect(game.person.money == 960 and game.turn == turn + 1 and game.lessons == {"mechanic": 1}
       and (game.person.practice["mechanic"] == 1 or game.person.skill("mechanic") == 1), "a lesson: paid, practised, a turn")
game.person.skills["mechanic"] = 3
expect(game.lessons_here()[0][2:] == (640, 7), "dearer and fuller as the level rises")
game.person.skills["mechanic"] = 5
expect([o[0] for o in game.lessons_here()] == ["gunner"], "a master has nothing to learn")
game.person.money = 10
with headless.quiet() as out:
    game.take_lesson("gunner", "the range master", 40, 1)
expect(game.person.money == 10 and "costs 40" in flat(out.getvalue()), "no money, no lesson")
io.feed([""])
text = screen(36, game.handle_work)
expect(max(cargo.visible_len(line) for line in text.splitlines()) <= 36, "the work screen with lessons fits 36 columns")

# ---- saves --------------------------------------------------------------------------------------------------
game, io = fresh()
with headless.quiet():
    game.implant_clinic(pick="1", sure=True)
    game.save_game("training")
    loaded = cargo.load_game("training")
expect(loaded.person.implants == {"loader": 1} and loaded.implants_fitted() == 1, "a save keeps the implants")
del loaded.person.__dict__["implants"]
loaded.bring_up_to_date()
expect(loaded.implants_fitted() == 0 and loaded.person.implants == {}, "a save from before implants has none")

# ---- the balance, measured with the bot -------------------------------------------------------------------------
if "--quick" not in sys.argv:
    results = {}
    for mode in ("", "--no-spending"):
        runs = []
        for seed in (1, 2):
            out = subprocess.run([sys.executable, os.path.join(HERE, "bot.py"), os.path.join(os.path.dirname(HERE), "game", "world.py"),
                                  "trade", str(seed), "120", "--curious"] + ([mode] if mode else []),
                                 capture_output=True, text=True, timeout=900, env=dict(os.environ, CARGO_SOUND="0"))
            runs.append(json.loads(out.stdout.strip().splitlines()[-1]))
        results[mode or "spend"] = runs
    spend, save = results["spend"], results["--no-spending"]
    for a, b in zip(spend, save):
        expect(a["money"] < b["money"] * 0.6, "spending keeps the purse below six tenths: %d against %d" % (a["money"], b["money"]))
        expect(a["money"] > 1000, "and leaves money in it: %d" % a["money"])
        expect(sum(a["skills"].values()) >= sum(b["skills"].values()), "and buys skill: %s against %s" % (
            sum(a["skills"].values()), sum(b["skills"].values())))
    print("bot by turn 120: spending %s; saving %s" % ([r["money"] for r in spend], [r["money"] for r in save]))

print("training: %s" % ("ok" if not problems else "%d problems" % len(problems)))
sys.exit(1 if problems else 0)
