#!/bin/sh
# Run every check on Cargo 3. Usage: tools/check.sh [quick]
cd "$(dirname "$0")/.." || exit 1
export CARGO_SOUND=0          # the checks never start an audio player
T=tools
G=game/world.py
PY=${PYTHON:-python3}
if [ "$1" = "quick" ]; then SEEDS="1 2"; WIDTHS="80 40 36"; N=600; FIGHTS=100; else SEEDS="1 2 3 4"; WIDTHS="100 80 60 50 44 40 36"; N=1500; FIGHTS=300; fi
fail=0

echo "== CLIo's layer in kit/ is as copied"
$PY $T/sync_kit.py --check || fail=1

echo "== the story: copied tools and Cargo 1's story unchanged, built file current, no new"
echo "   findings, every scene plays"
$PY $T/sync_story.py --check || fail=1
$PY $T/build_story.py --check || fail=1
$PY storykit/validate.py story/cargo3.story.json --baseline story/findings-baseline.json > /tmp/cargo3-validate.txt; tail -2 /tmp/cargo3-validate.txt
grep -q "baseline: 0 new" /tmp/cargo3-validate.txt || fail=1
$PY $T/scenes.py $G > /tmp/cargo3-scenes.txt || fail=1
grep -E "CRASH|unfilled|FAIL" /tmp/cargo3-scenes.txt | head; tail -1 /tmp/cargo3-scenes.txt

echo "== act 1 for every kind of captain: the intro, the reasons for no ship, the hall, the floor,"
echo "   the berths captains, the first old friend"
$PY $T/act1.py || fail=1

echo "== the captain's history across the parts, and the errands to 2420 and 2460"
$PY $T/history.py || fail=1

echo "== people named by what they do: the guard, the medic, the cybersurgeon, the test range, the squad"
$PY $T/roles.py || fail=1

echo "== the labour market: strikes, rushes, convoys and audits move shifts and the berths board"
$PY $T/labour.py || fail=1

echo "== the engine's systems, one by one"
$PY $T/systems.py || fail=1

echo "== the captain as a person, apart from the ship"
$PY $T/person.py || fail=1

echo "== the able hand: work, the berths board, voyages, passage, the locker, wounds"
$PY $T/hand.py || fail=1

echo "== sound: songs composed and rendered, places, fights, effects, sound off (into a recorder)"
$PY $T/sound.py || fail=1

echo "== convoy fights against one-roll fights, every difficulty (win rate and damage)"
$PY $T/fights.py $FIGHTS > /tmp/cargo3-fights.txt || fail=1; grep OFF /tmp/cargo3-fights.txt; tail -1 /tmp/cargo3-fights.txt

echo "== each module of the game imports on its own"
$PY $T/modules.py || fail=1

echo "== every style at every width, with and without colour and Unicode"
$PY $T/looks.py || fail=1

echo "== wrong-object references"
$PY $T/attrlint.py $G | tail -1

echo "== the game starts and exits as a program (UTF-8 and cp1252 output)"
$PY $T/smoke.py $PY cargo3.py || fail=1

echo "== damaged and hostile save / captain files"
$PY $T/test_files.py $G > /tmp/cargo3-files.txt || fail=1; tail -1 /tmp/cargo3-files.txt

echo "== save / load round trips"
for s in $SEEDS; do $PY $T/roundtrip.py $G $s 1200 800 | $PY -c "
import json,sys
r=json.load(sys.stdin)
ok=r.get('identical') and r.get('captain_ok') and not r.get('stale_refs_to_old_game') and 'traceback' not in r
print('  seed', r['seed'], 'ok' if ok else 'FAIL', r.get('traceback','')[-300:])
sys.exit(0 if ok else 1)" || fail=1; done

echo "== random play at each width (crashes, lines wider than the screen), on foot and with a ship"
for w in $WIDTHS; do for s in $SEEDS; do for a in "" --afloat; do $PY $T/infuzz.py $G $w $N $s $a | $PY -c "
import json,sys
r=json.load(sys.stdin)
ok=not r['traceback'] and not r['overflow_kinds']
print('  cols', r['cols'], 'seed', r['seed'], 'with a ship' if r.get('afloat') else 'on foot', 'inputs', r['inputs'], 'ok' if ok else 'FAIL', (r['traceback'] or '')[-300:], r['overflow'][:2] if r['overflow_kinds'] else '')
sys.exit(0 if ok else 1)" || fail=1; done; done; done

echo "== long games through the real prompts at 36 columns, with saves and loads"
echo "   (trade plays on foot as an able hand, combat with a ship from the start; seed 2 plays"
echo "   a Cargo 1 captain; the story has no endings yet, so these only must not fail)"
for goal in trade combat; do for s in $SEEDS; do
captain=""; [ $s = 2 ] && captain="--captain=$goal"
afloat=""; [ $goal = combat ] && afloat="--afloat"
$PY $T/bot.py $G $goal $s 400 --save-every=9 --cols=36 $captain $afloat | $PY -c "
import json,sys
r=json.load(sys.stdin)
crash='traceback' in r
hand = '' if r.get('afloat', True) else ', on foot: %s voyages, %s shifts' % (r.get('voyages'), sum((r.get('shifts') or {}).values()))
print('  %-7s seed %s%s%s: %s at turn %s, chapter %s, %s loads%s %s' % (r['goal'], r['seed'], ' (Cargo 1 captain)' if r.get('captain') else '', ' (with a ship)' if r.get('afloat') else '', r.get('ending') or r.get('end') or 'playing', r.get('turn'), r.get('chapter'), r.get('loads'), hand, 'CRASH '+r['traceback'][-300:] if crash else ''))
sys.exit(1 if crash else 0)" || fail=1; done; done

echo "== a curious hand looks around every dock: when chapter I ends (the first old friend)"
for s in $SEEDS; do $PY $T/bot.py $G trade $s 150 --cols=36 --curious | $PY -c "
import json,sys
r=json.load(sys.stdin)
crash='traceback' in r
ch=r.get('docks',{}).get('chapters',{})
print('  seed %s: chapter I ends at turn %s, Adit met at turn %s %s' % (r['seed'], ch.get('ch1'), r.get('docks',{}).get('first',{}).get('dock_loader'), 'CRASH '+r['traceback'][-300:] if crash else ''))
sys.exit(1 if crash or 'ch1' not in ch else 0)" || fail=1; done

if [ $fail = 0 ]; then echo "ALL CHECKS PASSED"; else echo "SOME CHECKS FAILED"; exit 1; fi
