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
- **On foot.** A new game begins without a ship (`game/hand.py`), with 300 credits:
  - `work` (w): a shift at a site here, two jobs each, each training one skill: the cargo ring
    (stevedore, tally clerk), the hovertank assembly plant at Delta (line fitter, test-range
    hand), the deep levels at Gamma and the asteroid bases (ore hauler, gallery surveyor), the
    farm drums at Beta and Geod's Row at Delta (agrobot tender, shift steward);
  - `berths` (bb): ships leaving the dock that want a hand for one duty. Ola Plumb's Level Best,
    Jak Ghillie's Low Water, Lieutenant Caspic's Sealed Orders, Dr Vrtoch's Errata and Brother
    Caboose's Clean Lading fly routes of their own; other ships come and go. On each turn of
    the way a duty comes up, handled boldly or carefully at odds given in words, and riskier
    ships find trouble. Pay is on arrival; a voyage left half-way changes nothing;
  - `passage` (pa), `locker` (lo): ten units of private trade, `skills` (sk);
  - skills rise with practice (3, 12, 27, 48 and 75 for the five levels); wounds heal with time
    and faster with rest; work and duties can put a captain down but not kill.
- The stats box without a ship: C Δ R G Ω ]|[, turn, money, the place, the chapter and plot
  points, with wounds and the locker when there are any. `help` explains the hand's game.
- The story sees `afloat`, `wounds`, `voyages`, `shifts` (and by site), the six skills, each
  berths captain's regard and the locker's profit. `give_ship` gives the captain a ship.
- Checks: `tools/hand.py`; the bot plays an able hand; the fuzzer and the bot also play with a
  ship from the start (`--afloat`), so a captain's turns stay checked until the story gives one.
- A story frame of three chapters: The Hiring Hall, Old Friends, A Bridge Again.
- The checks (`tools/check.sh`) from the start: story, systems, sound, fights, looks, hostile
  files, save round trips, fuzzing at seven widths, and long bot games at 36 columns.
