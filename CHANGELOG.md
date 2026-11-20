# Changelog

Cargo 3, the last part of the Cargo trilogy. Versions follow the game (`game/__init__.py`).

## 3.0.0-dev

- Fixed: the port's price forecast (`prices`, with a ship) was titled "{port_broker}", a Cargo 1
  name this part never declared. `tools/placeholders.py` makes sure no name is shown as a raw
  {placeholder}, in the story or the code.
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
- **Chapter II, Old Friends** (`story/cargo3/friends.json`). The chapter ends when old friends
  have given three of the five things a ship needs (the story's stat `ship_needs`); it used to
  end at 80 plot points. A thought for each points the way.
  - **A navigator's key**: Korai, in the needle office's signal loft on her route, teaches the
    count that tells a needle where to put a ship. An untried navigator learns how it goes; a
    green one rides a needle with her and holds the count (and can ask where the ship went: a
    ship without a file comes out late, and the Mandate tows those to Alpha). A captain who
    learned needle-talk in 2460 sings her the verse.
  - **Someone to vouch for you**: Eela digs at Gamma, and claim jumpers come for its seam. Stand
    on the seam with it (a fight on foot, Eela at your side), or survey it as an able navigator;
    the captain who made Eela a shareholder in 2420 is in the cooperative's book already. Then a
    Rockwarden envoy writes: Stonewright is coming home.
  - **Papers**: the Magister at the Kraal counting room at Delta can charter a family captain,
    with the family seal. The seal is in a yacht in the Mandate's yard at Alpha: pay the guard
    300, show him the Magister's letter as an able broker, or go over the fence at night past
    the night watch. Or pay 2,500 and fill in the forms.
  - **A debt called in**: Meza Voce, on her route between Beta and Gamma, wants twelve crates of
    AGROBOT SPARES walked past the company's guards at Gamma's gallery gate (100 credits, an able
    broker's manifest, or a fight). Family from 2420 or 2460 call the debt in at once; a captain
    who sold her run to customs settles first, with 1,500 credits or with her androids. The
    Rootstock will open a yard that asks no questions, once.
  - **The truth about your ship**: in the Mandate's yard at Alpha, CU-113 counts the hulls. Take
    its count for a shift (or spend the hour you gave it in 2420, or pay the machine you sold a
    wage in advance) and it reads the nameless hull's keel log: the hull is yours. It came out of
    a needle last year, tumbling and empty; somebody cut out its name before the Mandate found it.
  - **Closing in**: with two things in hand, two men in grey wait at the bunk: Serac can have the
    ship released, for an errand. Hear them out, or say no and see what they do about it (a
    colonel of his says no politely). A Chronos Corporation clerk brings word that something of
    the captain's has matured. Two new roles: the Rockwarden Envoy and the Chronos clerk.
  - Measured with the curious bot: chapter I ends at turn 8 to 18, chapter II at 44 to 62 (it
    ended at 50 to 70 on plot points); by turn 300 it has four or five of the five. Checks:
    `tools/friends.py` plays every way to each, at 36 columns.
- **Chapter III, A Bridge Again** (`story/cargo3/ship.json`). The captain's ship is the nameless
  hull in the Mandate's yard at Alpha; the chapter is getting it out, and the first run that
  way's price sends it on. In the yard, by what the earlier chapters opened:
  - **Serac** has it released, in person, unaged: 3,000 for expenses, a sealed Mandate container
    for the garrison at Scholz's Star, and a transponder under the console (a colonel of his, or
    a captain who once said no, hears it differently);
  - **the Rockwarden envoy** buys it at auction and plates it as an Ironback, advances 4,000, and
    sends stores for Stonewright, coming home after a century under sublight;
  - **the time broker's clerk** pays the release fee with matured money (6,000 of your own on top
    for a fresh captain's great-aunt's bonds, 3,000 for an old account), 2,000 back; no strings;
  - **the salvage court**, with the Kraal papers and CU-113's keel log, and the cooperative's word
    (2,000) or an advocate (4,000); the Mandate pays back 3,000 of storage;
  - **at night**: the Rootstock open the gate, Korai's count takes the ship through a needle with
    no file, if you get past the night watch (a fight on foot; caught, try another night); the
    Rootstock leave seed stock and 1,000 in the hold, and the Mandate has the hull on a list;
  - **the auction**: 25,000.
  The ship is named (Late Arrival, Second Chance, or Nameless, as it came out of the yard;
  `{ship_name}` in the story) and the turn is a captain's from then on. Every way leaves working
  capital, so nobody starts afloat broke.
  - **The first run** ends at Scholz's Star's garrison (DSO-Gamma), where a Bushing, the third of
    that name, still guards the grey layer in the ice and a heading: Serac's container delivered
    sealed (6,000) or opened (a receiver tuned to the beacon, and Serac will know); Stonewright
    docking with Maret Rockwarden, Anselm's granddaughter, in command (the saga's promise
    `the_stonewright`, paid; 4,000); or your own run (a Cargo 1 captain who filed the course
    home in 2420 finds it still on file).
  - **Chapter IV, The Heading**, begins: fly to the Builder Site in Scholz's Star's wake, where
    the segment hangs with its beacon pointing at an empty patch of sky.
  - New story hooks: `ship <hull>` and `rename <words>`; effects after a `ship` code in the same
    scene see the ship. Serac's men and the broker's clerk keep coming until the ship is out.
  - Measured with the curious bot (8 games of 400 turns): the ship comes at turn 76 to 222
    (mostly by the envoy or Serac), chapter III ends at 94 to 244, the Builder Site is reached at
    97 to 295, and no captain went bankrupt on the way. `tools/ship.py` plays every way, run and
    ending at 36 columns; the bot's hand measurements keep it ashore (`--ashore`).
- **Chapters IV to VI, and the endings** (`story/cargo3/heading.json`, the frame in `main.json`).
  The story now runs from 2533 to about 2600, and ends.
  - **IV, The Heading.** The beacon on the segment keeps the ring's beat and points at the gap.
    Record it: the Vertex Array fits it like a key (and only one person has ever carried both),
    or hold Korai's count, or spend a quarter of your research, or hire a recorder buoy (5,000).
    The midpoint: the ring cannot turn without the stolen segment, or its timing. Serac's man
    wants a copy (20,000, or the airlock), a Mandate cutter hunts a hull taken at night,
    Stonewright offers to fly the long leg home with you. The long leg: nineteen years outside,
    five weeks aboard; it is 2552, ERYX has a target the papers call Eryxia, and the timing goes
    to the Stator Field near Sedna's orbit.
  - **V, Who Holds the Ring.** Who holds the segments comes from the Cargo 2 ending a record
    carries (common ground, the Mandate, the Hansa, House Rostrom, the Binary Dawn). Five claims:
    Serac at Alpha, Yzode van Rostrom at Epsilon, the machines at Alpha, Ola Plumb (the Hansa's
    speaker now) at Beta, and your own people at the Stator Field: from home. Side with one
    faction, or none. Then the Mandate moves first: hand over the timing (30,000), or run its
    blockade (with Stonewright, if it came). It starts the ring from its end: one degree the
    wrong way, every needle in flight comes apart, and Korai comes out of hers thirty-eight
    years later, older at last.
  - **VI, From Home.** Find who will hold the ring with you: Stonewright, Korai, Eela and the
    cooperative, Meza Voce, CU-113, the Kraal family, each only if chapter II made them your
    friend. At the restart: from home (three allies or more), from the end of the side you took,
    or now, from where you stand.
  - **Three endings.** From Home: the ring turns, nobody saw whose hand moved first, and the
    first ERYX mission leaves on a road nobody owns. Their End: the mission leaves under the
    Mandate's flag, the Concord's committee, the machines' clock or the Hansa's ticket. The
    Loop: the ring turns once the wrong way and throws the captain back to 2420, to Cargo 1's
    portal, with a shard of grey alloy in a pocket and a warning to give (Cargo 1 already has
    the opening for that captain, and the older captain at the portal). The saga's promise
    `the_warning` is paid; who threw the switch is never said. An epilogue tells what became of
    ten of them.
  - New story code `years <n>` (a relativistic leg) and `{year}`; stats `claims` and `allies`. A
    chapter's opening is filled when it starts (it used to be filled at the start of the game,
    so a year in it would have been 2533). When the story has already decided between endings,
    the game does not ask.
  - Measured with the curious bot (8 games): every one reaches From Home, at turn 192 to 483;
    chapter IV takes 36 to 288 turns, V 12 to 40, VI 18 to 183. `tools/heading.py` plays every
    scene and all three endings at 36 columns.
- **Prices that climb** (`game/prices.py`, Dan: the implants' curve on the equipment too). One
  curve, price = base × level² × (1 + 0.3 × owned):
  - ship upgrades: a point of attack, defense or speed costs 1,000 × its level², dearer for every
    point bought (the first four of attack: 1,000, 5,200, 14,400, 30,400); the yard shows the
    next price of each; saves from before count back from their stored price;
  - the yard's modules: three tenths dearer for each module on the grips (containers 8,000,
    10,400, 12,800); stripping and mending go by the module's own price;
  - the port shop's equipment: three tenths dearer for each piece of the shop's equipment aboard
    (story items do not count);
  - the outfitter's gear: three tenths dearer for each piece the hand carries;
  - the implants were already on it, and are now on the same code.
  The sellers say so when a price has climbed: the yard master, the yard foreman, the chandler,
  the outfitter and the cybersurgeon each have their lines. Once the captain has paid a climbed
  price, a quiet look now and then carries the captain's own sidenote ("the most expensive nap in
  history"), and thoughts come and go with what has been bought ("Armed to the teeth, charged to
  the eyeballs"; "A square deal, they call it. A round number would be cheaper"). Stats
  `paid_dearer`, `gear`, `upgrades`. `tools/prices.py` checks the curve and every seller.
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
- **Fights on foot** (`game/brawl.py`). A fight is a few rounds; each round the hand gives an
  order at odds in words: strike (gunner), shoot (with something that shoots), grapple and hold
  (loader; no blow back if it works), guard (the next blow likelier), talk them down (steward or
  broker; easier as they get hurt), run (navigator; harder from people who shoot), or pay what
  they want. Their blows are wounds, less with a suit on. A hand who goes down is robbed, locked
  up (the company's guards, the Mandate) or dragged clear, and loses two turns, resting; only
  people who mean to kill can do worse, and the screen says so.
  - **Who**: dock toughs, pickpockets, Cargolyte stevedores after a tithe (Beta, Gamma, the
    bases), the company's guards at Gamma, claim jumpers with rivet guns during a rich seam, a
    loader agrobot gone wild during an agrobot trial, the picket line (when crossing it goes
    wrong), and, for the story, the Rootstock's enforcers, a Mandate fire team and two men in
    grey from Serac.
  - **Trouble at the docks**: from turn 6, about one turn in 25 at an ordinary dock, half again
    at Gamma and the bases, half at Alpha; up to three times as often for a hand with a fat
    purse; more with claim jumpers or a wild agrobot about; never twice within four turns.
    Robbers take a share of the purse, within limits (a dock tough: a quarter, 40 to 300).
  - **The outfitter** (`gear`/`ge`): a knife (60), a work suit (120), a rivet gun (220), a
    stunner (300; a hit stops their next blow), a cutting torch (450) and a slug pistol (1,200;
    a hit counts twice, and the Mandate takes it off a hand it locks up), a vacuum suit (600),
    exoskeleton knees from Scholz's Star's old stock (800; grapple and run). Each dock sells a
    few; the hand fights with the best of each kind.
  - The story starts fights with `brawl <foe>` (and `edge <n>` for allies) and reads
    `fight_<won|talked|ran|paid|lost>_<foe>`, and the stats `brawls`, `brawls.won`,
    `brawls.lost` and `armed`.
  - The yard's night watch at Alpha joins the foes, for chapter II.
  - Measured with the bot over 250 turns (16 games): 9 to 18 fights, settled about evenly by
    beating them, talking and paying; no deaths; a saving hand ends with 24,000 to 28,000
    credits (29,000 to 32,000 before), a spending one with 6,000 to 12,000. Checks:
    `tools/brawl.py`.
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
