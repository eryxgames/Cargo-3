# Changelog

Cargo 3, the last part of the Cargo trilogy. Versions follow the game (`game/__init__.py`).

## 3.0.0-dev

- Cargo 3 starts from Cargo 2.2's engine: the turn loop, docks and needles, look and think, the
  storykit runtime, saves and the captain's record shared in `~/.cargo-saga`, sound, twelve
  styles, every screen from 36 columns.
- CLIo 2.2.1's layer in `kit/`, now with banners, pictures (pixels, blocks, braille, LED,
  ASCII) and animation effects.
- The logo: C Δ R G Ω ≡ in the intro and the README, CΔRGΩ≡ in the stats box; the triple bar
  stands for Cargo 1 and 2's ]|[. Plain terminals show C A R G O ]|[ and CARGO]|[.
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
  - skills rise with practice through six levels: untried, green, able, handy, skilled, master.
    Each level takes more practice, on a curve (3, 12, 27, 48 and 75 on average), and each
    captain's way up differs: the practice a level really takes is drawn from half the curve's to
    half again and not shown, so every try makes the next level likelier and some get there
    sooner. `skills` shows each level with a bar toward the next. A hand playing steadily is
    able at a skill or two by turn 40, handy by turn 120;
  - wounds heal with time and faster with rest; work and duties can put a captain down but not
    kill;
  - `look` where there is nothing to note shows a line of the dock: each planet has its own,
    and there are more for any dock, one a turn.
- The stats box without a ship: CΔRGΩ≡, turn, money, the place, the chapter and plot
  points, with wounds and the locker when there are any. `help` explains the hand's game.
- The story sees `afloat`, `wounds`, `voyages`, `shifts` (and by site), the six skills, each
  berths captain's regard and the locker's profit. `give_ship` gives the captain a ship.
- Checks: `tools/hand.py`; the bot plays an able hand; the fuzzer and the bot also play with a
  ship from the start (`--afloat`), so a captain's turns stay checked until the story gives one.
- **Act 1, chapter I: The Hiring Hall** (`story/cargo3/act1.json`):
  - who the captain is now: a fresh captain, a Hansa founder, Serac's colonel, a Cargo 1
    captain, a Cargo 2 captain or a Cargo 3 captain again, each in a line or a pun;
  - why there is no ship: a needle shed the captain like a bad link, and a pod kept them cold
    and asleep for years (nineteen for a fresh captain, seventy-three for a Cargo 2 one, decades
    on decades for Cargo 1) until a salvager found it and paid a finder's tenth. The ship did not
    come with them. Told for each record: a Rockwarden prospector for a cooperative member,
    needle-talk heard on the way out for a Cargo 2 captain who learned it;
  - the hiring hall, and the old hands' talk of people who should be dead;
  - the hovertank plant, the deep levels and the farm drums seen from the floor, remembering
    what a Cargo 1 captain did there;
  - the five berths captains, to talk to at the docks (Brother Caboose's papers say
    Caboose-237; the old hands remember him as Officer Deks);
  - the first old friend: Adit, the loader agrobot, still on the cargo rings. A captain with a
    record is known at once; a fresh one works the ring first. Adit asks you to ask: about your
    ship (its lists say it never came out of the needle, and Korai would know where needles
    go), about who else is alive, or for a shift beside it. Finding Adit ends chapter I.
- **Errands to the past** (`story/cargo3/errands.json`). The captain's record now carries the
  captain's history (`game/record.py`, copied from the Cargo repository, as in Cargo 1 1.3.0 and
  Cargo 2 2.3.0): the same id and log from part to part, the captain's own time, the line of
  the timeline each game is, what the captain left in each part (`{"past": ...}`) and errands
  (`{"errand": ...}`, effects `errand` and `errand_done`). Two errands go back:
  - level nine's plaque at Gamma has a blank thirteenth line "for the hauler who brought the
    air". Promise it a name, export the record, start Cargo 1 as this captain, get the miners
    out, and give the name, or leave the line blank; a new 2533 begun from that record shows it,
    on the plaque and in the deep levels;
  - Conte Ottavine sits at Delta in front of a vault she cannot open: she chose its word in 2460
    and lost it in stasis, the newest memories first. Be in the room in Cargo 2 when she chooses
    it, and in a new 2533 the vault opens to it: inside is a Procrustes Analyzer, which finds a
    ship under a new name.
  - Tylde Kren's notes at Epsilon have a gap where the shape of the missing segment should be:
    measured from the samples in 2420, lost in the Institute fire. Promise to measure them, do
    it in Cargo 1 before the fire, and in a new 2533 the cartridge is taped into her notes,
    labelled in your own hand: the Vertex Array.
  Thoughts keep the way back. Keys a newer game writes into a record are kept; a record that went
  through an older game (Cargo 1 1.2.1) is offered a join with the captain's newer record, and
  an errand for a version too old is named at import and export. Checks: `tools/history.py`.
- **The labour market** (`game/labour.py`): the docks have their own weather, as the trade
  events move prices. Something starts at one of the docks on about one turn in two and runs
  a few turns: a rush order or a strike at the hovertank plant; gas or a rich seam in the deep
  levels; a harvest or a blight in the farm drums; a convoy unloading, a quiet ring, an agrobot
  trial or a Hansa audit on the cargo ring; crews short, hands cheap, a convoy forming, a customs
  crackdown, a Cargolyte pilgrimage or the needle delayed on the berths. Each moves the wages
  (from three tenths less to half again), closes jobs, adds risk, or changes the board: more or
  fewer ships, which kinds come (a crackdown keeps the smugglers dark, Jak Ghillie's Low Water
  too), a turn more a voyage. The turn's screen shows what is on here, the work and berths
  screens and arrival say it, and look gives word from the other docks. The story reads it
  (`labour.<id>`: turns left here) and starts it (the same name as an effect: the squad's sweep
  starts a crackdown); `{labour_news}` fills in the word from elsewhere. Kept in saves. Checks:
  `tools/labour.py`. Measured with the bot: money and voyages by turn 120 as before (11,000 to
  13,000 credits, 40 to 47 voyages).
- **What the hand does about it**: most of the docks' events can be changed, from the work
  screen (site events) or the berths board (berth events), each at odds given in words and for
  a turn. Cross a strike's picket line for a line fitter's shift twice over (the strike runs a
  turn longer, and the pickets remember), stand with the picket, or settle it as an able
  steward: both end it in a rush order. Go down with the fire boss to clear the gas, save the
  seed in a blight (a small harvest follows), race the agrobots on the stack, talk a hauler
  onto a quiet ring (a convoy follows). On the berths: run cargo past a crackdown (300, or a
  200 fine and the Mandate's list), inform on the runners (80, and the crackdown runs longer),
  organise the cheap hands, or pay the needle office 100 to end a delay. A failed try costs
  wounds or money and the event goes on. What the hand did is remembered (`work.crossed`,
  `work.informed`, `work.cleared_gas` and the like, for the story): the test range calls a line
  crosser one, the company store knows who went down for the gas, and the squad's commander
  nods to an informer like a colleague.
- **What money buys** (`game/training.py`), so a hand with money has something to spend it on,
  and a reason to go to the other docks:
  - **lessons** with a master at each dock, on the work screen: the Hansa's exchange clerk at
    Alpha (broker), the farm drums' canteen boss at Beta (steward), the crane master on Gamma's
    ring (loader), the plant's line chief and the range master at Delta (mechanic, gunner), a
    navigation tutor at Epsilon. A lesson takes a turn and gives the practice of one to nine
    shifts, at 40 to 1,000 credits: dearer as the hand gets better;
  - **implants** from the cybersurgeon at Epsilon: a whole level of a skill at once, up to
    skilled, at 500, 2,000, 4,500 and 8,000 credits for green to skilled, each implant already
    fitted making the next three tenths dearer; the surgery costs 10 wounds and 5 a level, and
    is refused to a hand hurt worse than half. A master's level is earned, not fitted;
  - measured with the bot by turn 120: a hand who spends ends with 6,000 to 8,000 credits
    instead of 13,000 to 15,000, and with more skill; by turn 250, 10,000 instead of 30,000,
    skills summing 20 to 22 instead of 16 to 18. Checks: `tools/training.py`.
- **Five more roles, with the labour market**: the **Needle Office Clerk** at Beta, whose board
  says what is on at every dock (and who sends the hand to Korai); the **Company Store Cashier**
  at Gamma (pay a miner's tab while the shafts are shut for gas; Eela pays cash); the **Hansa
  Auditor** at any dock with an audit (help with the count; Ola Plumb's manifests); the **Convoy
  Tail Gunner** where a convoy is forming (Brother Caboose's lot, singing); a **Rockwarden
  Prospector** wherever a rich seam is found (sell her the survey as an able navigator; Eela,
  and Stonewright's people coming home).
- **People named by what they do** (`story/cargo3/roles.json`), so the names keep their
  weight. Each points at the named cast:
  - the **Perimeter Guard** at Alpha's impound yard (ask, or pay 100 for the yard's list: one
    hull with no name);
  - a **Medic** on the berths of Beta, Gamma and Delta in turn (patched up for 40 credits, 30
    wounds a time; she knows which captains send her their crews);
  - a **Cybersurgeon** at Epsilon (reads what the pod's cold took; the implant catalogue, a
    level of any skill, dear and dearer);
  - the **Battle Engineer** and the **Armored Commander** on Delta's test range after a shift at
    the plant (rig a skirt, ride a live-fire trial as an able gunner). After four shifts the
    engineer tells you the crew's name for her: Gabion;
  - a **Squad of Soldiers** and its **Heavy Infantry Commander** on a route through Gamma, Beta,
    Alpha and Delta: a sweep of the berths, a list that is not theirs. Carry the kit, show the
    salvager's papers, or slip away as a navigator.
  Checks: `tools/roles.py`, every scene with every answer at 36 columns.
- Story effects can train a skill (`skill.loader`), give practice toward the next level on the
  same curve as work (`practice.loader`), and wound (`wounds`, healing when negative).
- A line that fits its box is kept as written (columns lined up with spaces stay lined up).
- Messages stay until read: every answer goes through one place (`terminal.ask`), and a turn's
  screen waits for Enter before clearing when a message since the last answer is still unread
  (a talk at the docks, a shift's result, a voyage's pay).
- A story frame of three chapters: The Hiring Hall, Old Friends, A Bridge Again (II and III are
  placeholders until their story is written).
- Checks: `tools/act1.py` plays act 1 for eight kinds of captain; the scene player plays every
  scene on foot and with a ship; a curious bot run measures when chapter I ends (about turn 10
  to 25).
- The checks (`tools/check.sh`) from the start: story, systems, sound, fights, looks, hostile
  files, save round trips, fuzzing at seven widths, and long bot games at 36 columns.
