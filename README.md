# Cargo 3

The last part of the Cargo trilogy, set in the [Eryxian universe](https://github.com/eryxgames/eryxian/wiki).
A captain without a ship, centuries after the Debacle, works the docks and other people's holds
until they are trusted with a bridge again.

```console
>>>
        ╔══════ C Δ R G Ω ]|[ ══════╗
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
- **Next in M0:** the person and the ship apart (money, kit and skills belong to the captain);
  a shipless start with its own stats box; dock jobs, the berths board and voyages as an able
  hand; the openings (why the captain has no ship); act 1's first scenes.

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

## Layout

```
cargo3.py       launcher
game/           the game, Cargo 2.2's engine:
  world.py        Game: its state and the turn loop; inherits the mixins of the modules below
  start.py        continue a save, or a new game (fresh or as a recorded captain)
  terminal.py     width, narrow layouts, wrapping, boxes;  screens.py: the Game's screens
  look.py         CLIo's terminal detection and themes, applied to the boxes
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
                systems, fights, sound
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
```

`storykit/`, `story/saga.json` and Cargo 1's story are copies from the Cargo repository
(`python3 tools/sync_story.py ../Cargo`); change them there.

## Credits

Eryx Games. The `kit/` folder is from [CLIo](https://github.com/eryxgames/CLIo) by Daniel
Sandner, under the Apache License 2.0 (`kit/LICENSE`, `kit/NOTICE`).
