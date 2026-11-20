# Cargo 3

The last part of the Cargo trilogy, set in the [Eryxian universe](https://github.com/eryxgames/eryxian/wiki).
A captain without a ship, centuries after the Debacle, works the docks and other people's holds
until they are trusted with a bridge again.

```console
>>>
        ╔═══════ C Δ R G Ω ≡ ═══════╗
        ║     Space Trading Saga    ║
        ╚═══════════════════════════╝
               Version 3.0.0-dev
```

## Status

Being built (November 2026). The first milestone (M0) starts from Cargo 2.2's engine and turns
it around: the captain begins on foot.

- **Now:** Cargo 2.2's engine running as Cargo 3, with CLIo 2.2.1's screen and sound layer
  (banners, pictures in pixels, blocks or braille, animation effects) beside it, and a story
  frame of three chapters to be written into: the hiring hall, old friends, a bridge again.
- The person and the ship apart: money, equipment, research points and six skills (loader,
  mechanic, gunner, navigator, steward, broker) are the captain's; a ship the captain owns
  spends and earns through them, and the story and the records work without a ship.
- On foot as an able hand, until the story gives a ship (chapter III). The stats box shows the
  logo, the turn, money, the place, the chapter and plot points, and wounds and the locker when
  there are any. `work` a shift at the cargo ring, the hovertank plant at Delta, the deep levels
  at Gamma and the asteroid bases, or the farm drums at Beta and Geod's Row at Delta; sign on
  from the `berths` board (five captains fly routes of their own, other ships come and go) and
  handle a duty on each turn of the way, paid at the destination; buy `passage`; keep a
  `locker` of private trade; `skills` shows the captain. Work and duties can put a captain down;
  a fight can kill.
- Act 1 (chapter I, The Hiring Hall): who the captain is now, by record, in a line or a pun;
  the needle that shed them into a pod, asleep for years until a salvager found it, while the
  ship flew on without them; the hiring hall; the hovertank plant, the deep levels and the farm
  drums seen from the floor; the five berths captains; and the first old friend, Adit, whose
  lists say the ship never came out of the needle. Finding Adit ends the chapter. Chapters II
  and III are a frame still to be written.
- Errands to the past: a name for level nine's plaque and the shape of Kren's samples (both
  from 2420), and the word for the Kraal vault (from 2460), carried in the captain's record
  (`game/record.py`).
- People named by what they do (`story/cargo3/roles.json`): a perimeter guard, a medic, a
  cybersurgeon, a battle engineer, an armored commander, a squad of soldiers and its heavy
  infantry commander; a needle office clerk, a company store cashier, a Hansa auditor, a convoy
  tail gunner and a Rockwarden prospector. Names stay for the people who matter.
- The labour market (`game/labour.py`): strikes, rush orders, gas, rich seams, harvests,
  convoys, audits, crackdowns and pilgrimages at the docks move the wages, close jobs and change
  the berths board for a few turns; word of them comes from the other docks. A hand can change
  most of them: cross a picket line or settle a strike, clear the gas, run cargo past a
  crackdown or inform on it; the docks remember.
- What money buys (`game/training.py`): lessons with a master at each dock, and implants at
  Epsilon, a whole level at once, on steep curves, so a hand with money has a reason to spend
  it and to travel.
- Fights on foot (`game/brawl.py`): a few rounds of orders at odds in words (strike, shoot,
  grapple, guard, talk them down, run, pay), gear from the outfitter (`gear`), trouble at rough
  docks; a hand who goes down is robbed, locked up or dragged clear, and a few people mean to
  kill.
- What the game shows stays on screen until it is read: a turn's screen waits for Enter when
  the last thing shown was a message the player has not answered.
- **Next:** chapter II (old friends, centuries on), fights on foot, and the ways to a first ship.

The plan (the shipless chapters, the ways to the first ship, fights on foot, investments
matured from Cargo 2) is in the project's design document.

## Playing

Python 3.8 or newer, nothing else to install:

```bash
git clone https://github.com/eryxgames/Cargo-3.git
cd Cargo-3
python3 cargo3.py
```

In Termux: `pkg install python git` first. Any terminal from 36 columns wide works; `style` picks
the look and `sound` turns the music on or off. Sound plays through whatever player the machine
has (paplay or aplay on Linux, afplay on macOS, play-audio or mpv in Termux, the built-in player
on Windows; `CLIO_AUDIO` picks one) and is silent otherwise.

Saves and captain records are shared with Cargo 1 and Cargo 2 in `~/.cargo-saga`; set
`CARGO_SAGA_HOME` to keep them elsewhere. A captain who finished an earlier part can start
Cargo 3 as themselves: their record is offered when a new game starts.

Some things in 2533 can only be mended in the past. The story gives the captain an errand,
which travels in the captain's record: export it (`captain`), start Cargo 1 or Cargo 2 as this
captain (Cargo 1 1.3.0 and Cargo 2 2.3.0 or newer), do it there, and start Cargo 3 again as the
same captain. Every game begun from a record is a new line of the timeline, so no save is ever
rewritten; the new 2533 remembers what the captain did.

## Layout

```
cargo3.py       launcher
game/           the game, Cargo 2.2's engine:
  world.py        Game: its state and the turn loop; inherits the mixins of the modules below
  start.py        continue a save, or a new game (fresh or as a recorded captain)
  terminal.py     width, narrow layouts, wrapping, boxes;  screens.py: the Game's screens
  look.py         CLIo's terminal detection and themes, applied to the boxes
  person.py       the captain as a person: money, things carried, skills, wounds, locker, berth
  hand.py         the captain without a ship: work, the berths board, voyages, passage, locker
  labour.py       the docks' events (strikes, gas, crackdowns...) and what a hand does about them
  training.py     what money buys: lessons with the masters, implants
  brawl.py        fights on foot, trouble at the docks, the outfitter
  saves.py  captain.py      saves; the captain's record carried between the parts
  story.py  chapters.py     the storykit runtime; chapters, milestones, endings
  ship.py  travel.py  market.py  hansa.py  encounters.py  events.py  research.py
  actions.py  port.py  places.py  quests.py  contracts.py  people.py  passengers.py
  ranks.py  commands.py  factions.py  needles.py  modules.py  tactics.py  achievements.py  sound.py
  looking.py      look and think: people on their routes, sights, thoughts, special equipment
music/          cargo3.music.json: the songs (moods and seeds for CLIo's synthesizer)
kit/            CLIo's screen and sound layer, copied in by tools/sync_kit.py (Apache-2.0)
story/          the story: cargo3.story.json and the files in story/cargo3/, built into
                cargo3.game.json for the game; saga.json and Cargo 1's story, copied
storykit/       the trilogy's story tools (format, validator, map), copied
themes/         the game's own styles (CLIo theme files), beside CLIo's in kit/style/
tools/          checks: smoke, bot, fuzzing, save round trips, hostile files, kit, story,
                act 1, systems, the person, the able hand, the labour market, training,
                fights on foot, convoy fights, sound
.github/        the release workflow: tag vX.Y.Z to build, release and push to itch.io
```

`kit/` is never edited here: change the files in CLIo and copy them again with
`python3 tools/sync_kit.py ../CLIo`. `tools/check.sh` (or `tools/check.sh quick`) runs every
check, including one that fails if a copied file was changed.

Releasing (from 3.0.0 on): set `VERSION` in `game/__init__.py`, add a `## X.Y.Z` section to
`CHANGELOG.md`, then `git tag vX.Y.Z && git push origin vX.Y.Z`. The workflow checks, builds
`cargo3.exe`, makes the GitHub release and, with a `BUTLER_API_KEY` secret, pushes to itch.io
(`ITCH_PROJECT` in the workflow names the page). The release's description is
`.github/release-intro.md` followed by the version's changelog section
(`sh tools/release_notes.sh X.Y.Z` shows it). Running the workflow by hand (Actions, Release,
Run workflow) builds and smoke-tests both zips without releasing anything.

## Writing the story

The story is data in the storykit format (`storykit/FORMAT.md`): scenes, choices, conditions and
effects in `story/cargo3/*.json`, listed in `story/cargo3.story.json`. The chapters, their
milestones and the endings are there too (`story/cargo3/main.json`): their conditions are the ones
the game uses. Characters who span the trilogy are named once, in `story/saga.json`. After a
change:

```bash
python3 tools/build_story.py                         # builds story/cargo3.game.json
python3 storykit/validate.py story/cargo3.story.json # unknown names, broken links
python3 tools/scenes.py                              # plays every scene with every choice
python3 tools/act1.py                                # act 1 for every kind of captain
```

`storykit/`, `story/saga.json` and Cargo 1's story are copies from the Cargo repository
(`python3 tools/sync_story.py ../Cargo`); change them there.

## Credits

Eryx Games. The `kit/` folder is from [CLIo](https://github.com/eryxgames/CLIo) by Daniel
Sandner, under the Apache License 2.0 (`kit/LICENSE`, `kit/NOTICE`).
