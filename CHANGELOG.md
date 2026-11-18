# Changelog

Cargo 3, the last part of the Cargo trilogy. Versions follow the game (`game/__init__.py`).

## 3.0.0-dev

- Cargo 3 starts from Cargo 2.2's engine: the turn loop, docks and needles, look and think, the
  storykit runtime, saves and the captain's record shared in `~/.cargo-saga`, sound, twelve
  styles, every screen from 36 columns.
- CLIo 2.2.1's layer in `kit/`, now with banners, pictures (pixels, blocks, braille, LED,
  ASCII) and animation effects.
- The logo reads C Δ R G Ω ]|[ (CARGO]|[ on plain terminals).
- The captain is a person apart from the ship (`game/person.py`): money, equipment and
  research points are the captain's, with six skills, wounds, gear for fights on foot, a locker
  and a berth. A ship the captain owns spends and earns through them. The story, the chapters'
  conditions, the journal, saves and the captain's record work without a ship; story effects
  that only a ship can take are noted for the checks and do nothing.
- A story frame of three chapters: The Hiring Hall, Old Friends, A Bridge Again.
- The checks (`tools/check.sh`) from the start: story, systems, sound, fights, looks, hostile
  files, save round trips, fuzzing at seven widths, and long bot games at 36 columns.
