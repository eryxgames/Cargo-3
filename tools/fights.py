#!/usr/bin/env python3
"""Are the convoy fights fair? For every difficulty, ship strength and enemy threat from 3 up,
play many convoy fights (always focusing fire) and as many one-roll fights (Cargo 1's), and
compare how often the captain wins and how much damage the hull takes.
A matchup passes when the convoy fight wins within 0.12 of the one-roll fight and the damage
is within 0.6 to 1.5 times; matchups the one-roll fight wins less than 15% or more than 92% of
the time are shown but not judged (nobody should fight them, or everybody wins them).

    python3 tools/fights.py [fights per matchup, default 300]
"""
import os, random, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ["CARGO_SAGA_HOME"] = tempfile.mkdtemp(prefix="cargo3-fights-")
import headless  # noqa: E402

cargo = headless.load(os.path.join(os.path.dirname(HERE), "game", "world.py"))
from game import encounters  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 300
game, io = headless.new_game(cargo)
io.default = "1"                                         # focus fire, every round
enemy_of = {}
for eid, enemy in cargo.ENEMIES.items():
    if enemy["power"] >= cargo.TACTICAL_FROM and not enemy.get("after"):
        enemy_of.setdefault(enemy["power"], eid)


def play(difficulty, attack, defense, eid, convoy, one_roll):
    wins = damage = 0
    encounters.TACTICAL_FROM = 99 if one_roll else cargo.TACTICAL_FROM
    for i in range(N):
        random.seed(i * 7919 + attack * 31 + defense)
        game.difficulty = difficulty
        ship = game.ship
        ship.attack, ship.defense, ship.damage, ship.money = attack, defense, 0, 100000
        ship.items.clear()
        ship.crew.clear()
        ship.modules.clear()
        game.in_needle = convoy
        with headless.quiet():
            out = game.fight(eid, 0, [])
        wins += out == "victory"
        damage += ship.damage
    encounters.TACTICAL_FROM = cargo.TACTICAL_FROM
    return wins / N, damage / N


judged = failed = 0
print("diff atk def threat | one roll: win dmg | convoy fight: win dmg | ")
for difficulty in (1, 2, 3):
    for attack in (2, 4, 6, 8, 10):
        defense = max(1, attack // 2)
        for power in sorted(enemy_of):
            eid = enemy_of[power]
            old_win, old_dmg = play(difficulty, attack, defense, eid, False, True)
            new_win, new_dmg = play(difficulty, attack, defense, eid, True, False)
            judge = 0.15 <= old_win <= 0.92
            ok = abs(new_win - old_win) <= 0.12 and 0.6 <= (new_dmg + 1) / (old_dmg + 1) <= 1.5
            judged += judge
            failed += judge and not ok
            print("  %d   %2d  %2d    %d    |   %.2f %5.1f  |   %.2f %5.1f   | %s" % (
                difficulty, attack, defense, power, old_win, old_dmg, new_win, new_dmg,
                "" if not judge else "ok" if ok else "OFF"))
print("fights: %d matchups judged, %d off" % (judged, failed))
sys.exit(1 if failed else 0)
