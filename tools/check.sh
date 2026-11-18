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

echo "== the engine's systems, one by one"
$PY $T/systems.py || fail=1

echo "== the captain as a person, apart from the ship"
$PY $T/person.py || fail=1

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
$PY $T/test_files.py $G | tail -1 || fail=1

echo "== save / load round trips"
for s in $SEEDS; do $PY $T/roundtrip.py $G $s 1200 800 | $PY -c "
import json,sys
r=json.load(sys.stdin)
ok=r.get('identical') and r.get('captain_ok') and not r.get('stale_refs_to_old_game') and 'traceback' not in r
print('  seed', r['seed'], 'ok' if ok else 'FAIL', r.get('traceback','')[-300:])
sys.exit(0 if ok else 1)" || fail=1; done

echo "== random play at each width (crashes, lines wider than the screen)"
for w in $WIDTHS; do for s in $SEEDS; do $PY $T/infuzz.py $G $w $N $s | $PY -c "
import json,sys
r=json.load(sys.stdin)
ok=not r['traceback'] and not r['overflow_kinds']
print('  cols', r['cols'], 'seed', r['seed'], 'inputs', r['inputs'], 'ok' if ok else 'FAIL', (r['traceback'] or '')[-300:], r['overflow'][:2] if r['overflow_kinds'] else '')
sys.exit(0 if ok else 1)" || fail=1; done; done

echo "== long games through the real prompts at 36 columns, with saves and loads"
echo "   (seed 2 plays a Cargo 1 captain; the story has no endings yet, so these only must not fail)"
for goal in trade combat; do for s in $SEEDS; do
captain=""; [ $s = 2 ] && captain="--captain=$goal"
$PY $T/bot.py $G $goal $s 400 --save-every=9 --cols=36 $captain | $PY -c "
import json,sys
r=json.load(sys.stdin)
crash='traceback' in r
print('  %-7s seed %s%s: %s at turn %s, chapter %s, %s loads %s' % (r['goal'], r['seed'], ' (Cargo 1 captain)' if r.get('captain') else '', r.get('ending') or r.get('end') or 'playing', r.get('turn'), r.get('chapter'), r.get('loads'), 'CRASH '+r['traceback'][-300:] if crash else ''))
sys.exit(1 if crash else 0)" || fail=1; done; done

if [ $fail = 0 ]; then echo "ALL CHECKS PASSED"; else echo "SOME CHECKS FAILED"; exit 1; fi
