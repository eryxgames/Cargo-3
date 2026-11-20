"""The able hand: a captain without a ship (Cargo 3's first chapters).

Until the captain has a ship again (chapter III), the turn is a hand's turn:
- `work` a shift at a site here: the cargo ring at any dock, the hovertank plant at Delta, the
  deep levels at Gamma and the asteroid bases, the farm drums at Beta and Geod's Row at Delta;
  each has two jobs, each job trains one of the six skills (game/person.py) and pays a wage;
- `berths`: the berths board, ships leaving this dock wanting a hand for one duty; signing on
  plays the voyage, a duty to handle on each leg, and pays off at the destination. Some of the
  ships are the story's captains on their routes (NAMED_SHIPS), the rest come and go;
- `passage`: a paid place aboard, no duty;
- `locker`: an able hand's few units of private trade, bought and sold at the market here;
- `skills`: the captain as a person: skills, wounds, gear, the locker.
What is on at the docks (game/labour.py) moves the wages, closes jobs and changes the board.
Wounds heal with time, faster with rest (`end`). Work and duties can put the captain down
(WOUNDS_DOWN), never further; at WOUNDS_DEAD (a fight) the captain is dead and the game is over.
"""
import random
import zlib

from .labour import LABOUR_EVENTS

# Commands a hand has (long form, shortcut), besides the global ones (game/commands.py)
HAND_COMMANDS = [('work', 'w'), ('berths', 'bb'), ('passage', 'pa'), ('locker', 'lo'),
                 ('skills', 'sk'), ('end', 'e')]
HAND_GLOBAL_SKIP = ('hansa', 'ha')      # the Hansa's bonds and dues are a ship owner's business
STARTING_PURSE = 300                    # what a captain without a ship starts with

# Work sites: where (place names, or place types), what the place calls it, and two jobs each:
# (skill, job, wage per shift at skill 0)
SITES = [
    {"id": "ring", "name": "the cargo ring", "types": ("Planet", "AsteroidBase", "DeepSpaceOutpost", "ResearchColony"),
     "jobs": [("loader", "stevedore", 60), ("broker", "tally clerk", 55)]},
    {"id": "hovertank", "name": "the hovertank assembly plant", "places": ("Delta",),
     "jobs": [("mechanic", "line fitter", 90), ("gunner", "test-range hand", 85)]},
    {"id": "mine", "name": "the deep levels", "places": ("Gamma",), "types": ("AsteroidBase",),
     "jobs": [("loader", "ore hauler", 80), ("navigator", "gallery surveyor", 85)]},
    {"id": "biomass", "name": "the farm drums", "places": ("Beta", "Delta"), "names": {"Delta": "Geod's Row"},
     "jobs": [("mechanic", "agrobot tender", 75), ("steward", "shift steward", 70)]},
]
FIRST_SHIFT_POINTS = 2      # plot points for the first shift at each kind of site

# What a shift can bring, by skill: good (more pay, more practice), fair, or bad (less pay,
# maybe a wound)
SHIFT_LINES = {
    "loader": (["You find the trick of the stack and the crane boss notices.",
                "A whole hold out by the end of the shift, and nothing dropped."],
               ["Crates in, crates out. Your back keeps count."],
               ["A strap gives and a crate catches your shoulder.",
                "You stack it wrong and spend the shift unstacking it."]),
    "broker": (["Your tally catches a manifest short by forty crates.",
                "The Hansa clerk asks you to count his, too."],
               ["Seals, numbers, signatures. It adds up."],
               ["Your count is off by a pallet, and the pallet is docked from your pay."]),
    "mechanic": (["You find the fault the day shift missed.",
                  "The line runs faster for your fixes and the foreman writes your name down."],
                 ["Bolts, gaskets, a torque wrench that remembers better days."],
                 ["A seal blows in your face.", "You fix the wrong thing, carefully."]),
    "gunner": (["Every target down on the range, and the inspector signs without looking twice."],
               ["You test-fire the turrets and log the misses."],
               ["A turret jams on the range and the recoil throws you."]),
    "navigator": (["You find a seam the survey maps never showed."],
                  ["You walk the galleries with a lamp and a laser, measuring."],
                  ["You take a wrong turn in the galleries and lose half the shift finding the shaft."]),
    "steward": (["The shift ends without a fight in the canteen, which is a first."],
                ["Meals, rotas, complaints."],
                ["Two crews come to blows over the rota and you are in the middle."]),
}

# Ships: kinds, with their wages (a factor), how much trouble they find, and the duties they hire for
KINDS = {
    "hauler": {"words": "a Hansa hauler", "wage": 1.0, "risk": 1.0, "duties": ("loader", "mechanic", "broker")},
    "smuggler": {"words": "a hauler that files no manifest", "wage": 1.6, "risk": 1.8,
                 "duties": ("loader", "navigator", "gunner")},
    "courier": {"words": "a Mandate courier", "wage": 1.2, "risk": 0.8, "duties": ("navigator", "gunner", "steward")},
    "research": {"words": "a research ship that should not exist after the Debacle", "wage": 1.4, "risk": 1.4,
                 "duties": ("mechanic", "navigator", "steward")},
    "tail": {"words": "a Cargolyte tail ship", "wage": 0.8, "risk": 1.2, "duties": ("loader", "steward", "mechanic")},
}
# The story's captains, who fly their own routes (their characters, in story/cargo3/hands.json)
NAMED_SHIPS = {
    "plumb": ("Level Best", "hauler"),
    "ghillie": ("Low Water", "smuggler"),
    "caspic": ("Sealed Orders", "courier"),
    "vrtoch": ("Errata", "research"),
    "caboose": ("Clean Lading", "tail"),
}
# Ships that come and go
SHIP_NAMES = ["Slow Tally", "Broad Reach", "Ninth Pallet", "Coldwater", "Honest Weight", "Second Bell",
              "Ferrous Wheel", "Mercy of Ceres", "Long Division", "Sevenfold", "Dry Lease", "Quiet Ledger",
              "Hard Standing", "Saint Bulk", "Overdraft", "Lagrange Lady"]
LEG_WAGE = 70               # a hand's wage for a turn aboard, before the kind's factor
PASSAGE_FARE = 60           # a place aboard, no duty: per turn of the voyage
VOYAGE_POINTS = 2           # plot points for a voyage worked to its end
CLEAN_VOYAGE_POINTS = 1     # and one more when every duty went well
HEAL_PER_TURN = 2           # wounds heal this much a turn
HEAL_RESTING = 10           # and this much on a turn of rest

# Duties on the way, by skill: what happens, and two ways to handle it:
# (what you do, the base chance it goes well, bold or careful)
DUTIES = {
    "loader": [
        ("A container slips its grips in the burn and starts to walk down the spine.",
         [("Go out on the spine and clamp it", 0.40, "bold"), ("Call it in and wait for the mate", 0.70, "careful")]),
        ("The load shifts in the hold and the ship lists on its thrusters.",
         [("Restack it under thrust", 0.35, "bold"), ("Strap what you can and report it", 0.70, "careful")]),
    ],
    "mechanic": [
        ("The coolant loop starts to sing in a key it should not know.",
         [("Open it up while it runs", 0.40, "bold"), ("Throttle down and trace it cold", 0.70, "careful")]),
        ("A thruster quad fails its self-test on approach.",
         [("Bypass the test and fly it", 0.35, "bold"), ("Swap the controller board", 0.65, "careful")]),
    ],
    "gunner": [
        ("Something matches course at the edge of the plot, and stays there.",
         [("Light it up with the targeting laser", 0.40, "bold"), ("Keep the turret warm and wait", 0.70, "careful")]),
        ("The point-defence turret needs recalibrating mid-jump.",
         [("Calibrate it live on the debris", 0.40, "bold"), ("Run the slow routine", 0.70, "careful")]),
    ],
    "navigator": [
        ("The needle's lead hauler drifts off the wake and the file goes ragged.",
         [("Plot your own line through the wake", 0.35, "bold"), ("Hold station and follow the file", 0.70, "careful")]),
        ("The charts and the stars disagree by a few seconds of arc.",
         [("Trust the stars and correct", 0.45, "bold"), ("Trust the charts and ask the office", 0.65, "careful")]),
    ],
    "steward": [
        ("Two passengers decide they want the same bunk, with knives.",
         [("Step between them", 0.40, "bold"), ("Find a third bunk and a bottle", 0.65, "careful")]),
        ("The galley's printer jams and the crew starts counting meals.",
         [("Strip the printer down", 0.45, "bold"), ("Ration what is left", 0.70, "careful")]),
    ],
    "broker": [
        ("The manifest and the hold disagree by six crates.",
         [("Recount everything before the dock does", 0.45, "bold"), ("Write it up as it is", 0.70, "careful")]),
        ("A buyer at the destination calls ahead with an offer for the cargo.",
         [("Haggle for the captain", 0.40, "bold"), ("Pass it to the captain", 0.75, "careful")]),
    ],
}
# Trouble a ship of a kind finds on the way (by chance, more on riskier ships): any duty may
# handle it, the hand's best skill or the one named
TROUBLE = {
    "smuggler": ("A customs cutter hails and asks to see the manifest nobody filed.",
                 [("Talk them round", 0.40, "bold", "broker"), ("Keep out of sight below", 0.70, "careful", "loader")]),
    "research": ("The drive does something the manual does not mention, and the lights go blue.",
                 [("Pull the breaker", 0.40, "bold", "mechanic"), ("Strap in and log it", 0.75, "careful", "navigator")]),
    "tail": ("Brothers of the tail ship hold a lading service and want a convert.",
             [("Argue scripture with them", 0.40, "bold", "steward"), ("Bow your head and sign", 0.75, "careful", "broker")]),
    "hauler": ("A drone swarm brushes the convoy and the file closes up.",
               [("Man the point defence", 0.40, "bold", "gunner"), ("Seal the hold and wait", 0.75, "careful", "loader")]),
    "courier": ("A sealed crate aboard starts ticking.",
                [("Open it", 0.35, "bold", "mechanic"), ("Tell the lieutenant", 0.80, "careful", "steward")]),
}
TROUBLE_CHANCE = 0.25       # a turn's chance of trouble, times the kind's risk


def meter(share, width=5):
    """The way to the next level as a bar (full at the top): CLIo's bar glyphs, or # and -."""
    filled = width if share is None else max(0, min(width, int(share * width)))
    full, empty = ("#", "-") if plain_terminal() else ("█", "░")
    return full * filled + empty * (width - filled)


def wound_word(wounds):
    return ("whole" if wounds <= 0 else "bruised" if wounds < 20 else "hurt" if wounds < 50
            else "badly hurt" if wounds < 80 else "close to death")


def _rng(*parts):
    """A random generator for this place and turn: the same board each time it is looked at."""
    return random.Random(zlib.crc32(":".join(str(p) for p in parts).encode("utf-8")))


class HandMixin:
    """The Game's turns without a ship. Game inherits it (game/world.py)."""

    # -- the turn ------------------------------------------------------------------------------
    def play_hand_turn(self):
        self.new_turn()
        self.display_turn_info()
        self.story_manager.check_milestone_progress()
        self.story_manager.check_chapter_progress()
        self.story.tick()
        if self.ship is not None:           # the story gave the captain a ship this turn
            return None
        valid = []
        for cmd, cut in HAND_COMMANDS + [c for c in GLOBAL_COMMANDS if c != HAND_GLOBAL_SKIP]:
            valid.extend([cmd, cut])
        action = self.validate_input("Choose action: ", valid)
        if action is None:
            return None
        if action in ('work', 'w'):
            self.handle_work()
        elif action in ('berths', 'bb'):
            self.handle_berths()
        elif action in ('passage', 'pa'):
            self.handle_passage()
        elif action in ('locker', 'lo'):
            self.handle_locker()
        elif action in ('skills', 'sk'):
            self.show_person()
        elif action in ('end', 'e'):
            self.pass_turns(1, resting=True)
            self.autosave()
        else:
            return self.global_action(action)
        return None

    def pass_turns(self, turns, resting=False):
        """Turns go by: the world moves on, wounds heal."""
        for _ in range(turns):
            self.turn += 1
            self.shop.reset_turn()
            self.person.wounds = max(0, self.person.wounds - (HEAL_RESTING if resting else HEAL_PER_TURN))
            self.new_turn()

    def hand_stats_rows(self):
        """The stats box without a ship: the logo, turn, money, the place, the chapter, the plot."""
        sm = self.story_manager
        chapter = sm.chapters[sm.current_chapter]
        target = sm.plot_target()
        points = sm.plot_points
        person = self.person
        place = self.current_location
        rows = [[short_logo(), place.location_type],
                ["Turn: %d" % self.turn, "Name: %s" % place.name],
                ["¤: %s" % self.format_money(int(person.money)), "Chapter %s" % sm.get_chapter_number_roman()],
                ["Plot Points: %d/%d" % (points, target) if target and points < target else "Plot Points: %d" % points,
                 chapter.title]]
        hurt = "Wounds: %d%% (%s)" % (person.wounds, wound_word(person.wounds)) if person.wounds > 0 else ""
        locker = "Locker: %d/%d" % (person.locker_units(), LOCKER_UNITS) if person.locker else ""
        if hurt or locker:
            rows.append([hurt, locker])
        return rows

    def display_hand_info(self):
        self.clear_screen(hold=True)
        print(self.create_box(self.hand_stats_rows(), 'double', narrow='flow'))
        print(self.create_box(self.market_rows(), 'single'))
        if self.labour_at():
            print(self.create_box(self.labour_rows(), 'single'))
        fresh = self.labour_fresh_lines()
        if fresh:
            self.display_simple_message(fresh, 0)
        self.display_simple_message(
            "Commands: " + ", ".join("%s/%s" % pair for pair in HAND_COMMANDS) + " - help/h for more", 0)

    def market_rows(self):
        loc = self.current_location

        def price(good):
            if good in loc.banned_commodities:
                return "BANNED"
            if good in ("salt", "fuel") and not loc.trades_bulk(good):
                return "——"
            return str(self.format_money(loc.market[good]))
        return [["Tech: %s" % price("tech"), "Salt: %s" % price("salt")],
                ["Agri: %s" % price("agri"), "Fuel: %s" % price("fuel")]]

    # -- work ------------------------------------------------------------------------------------
    def sites_here(self):
        return self.sites_at(self.current_location)

    def sites_at(self, loc):
        found = []
        for site in SITES:
            if loc.name in site.get("places", ()) or loc.location_type in site.get("types", ()):
                found.append(site)
        return found

    def site_name(self, site):
        return site.get("names", {}).get(self.current_location.name, site["name"])

    def handle_work(self):
        jobs, shut = [], []
        for site in self.sites_here():
            closed = [(job, self.site_terms(site["id"], job[0])[2]) for job in site["jobs"]]
            for job, why in closed:
                if not why:
                    jobs.append((site, job))
            whys = [why for _, why in closed if why]
            if whys:
                why = whys[0]
                left = self.labour_left(why)
                name = self.site_name(site)
                what = ("%s: no shifts" % (name[0].upper() + name[1:])
                        if len(whys) == len(closed) else
                        "%s at %s: no shifts" % (", ".join(job[1].capitalize() for job, w in closed if w), self.site_name(site)))
                shut.append("%s (%s, %d turn%s)." % (what, LABOUR_EVENTS[why]["name"].split(": ", 1)[-1], left,
                                                     "" if left == 1 else "s"))
        footer = self.labour_screen_lines("work")
        if not jobs:
            self.display_simple_message(["Nobody here is hiring by the shift."] + shut + footer)
            return
        person = self.person
        rows = [["Work a shift"], [""]]
        for number, (site, (skill, job, wage)) in enumerate(jobs, 1):
            label = "%s at %s: %s a shift (%s, %s)" % (job.capitalize(), self.site_name(site),
                                                     self.format_money(self.shift_wage(wage, skill, site["id"])),
                                                     skill, skill_word(person.skill(skill)))
            rows.extend([line] for line in self.option_lines(number, label))
        if shut or footer:
            rows.append([""])
            for line in shut + footer:
                rows.extend([part] for part in self.word_wrap(line))
        print(self.create_box(rows, 'round'))
        answer = self.validate_input("Work which (1-%d, Enter to leave): " % len(jobs),
                                     [str(i) for i in range(1, len(jobs) + 1)])
        if answer is None:
            return
        site, job = jobs[int(answer) - 1]
        self.work_shift(site, job)

    def shift_wage(self, wage, skill, site_id=None):
        factor = self.site_terms(site_id, skill)[0] if site_id else 1.0
        return int(round(wage * factor * (1 + 0.2 * self.person.skill(skill)) / 5.0) * 5)

    def shift_chances(self, skill, risk=0.0):
        """(good, bad): a shift's chances, by skill and wounds (and what is on at the site)."""
        level = self.person.skill(skill)
        hurt = self.person.wounds / 200.0
        return min(0.85, 0.25 + 0.1 * level), max(0.03, 0.2 - 0.03 * level + hurt + risk)

    def work_shift(self, site, job, roll=None):
        """A shift: paid, practised, maybe hurt. The turn ends with it. Returns 'good', 'fair' or 'bad'."""
        skill, name, base = job
        person = self.person
        good, bad = self.shift_chances(skill, self.site_terms(site["id"], skill)[1])
        roll = random.random() if roll is None else roll
        lines = SHIFT_LINES[skill]
        wage = self.shift_wage(base, skill, site["id"])
        if roll < good:
            outcome, pay, practice, text = "good", int(wage * 1.5), 2, random.choice(lines[0])
        elif roll < 1 - bad:
            outcome, pay, practice, text = "fair", wage, 1, random.choice(lines[1])
        else:
            outcome, pay, practice, text = "bad", wage // 2, 1, random.choice(lines[2])
        person.money += pay
        risen = person.train(skill, practice)
        message = ["A shift as %s at %s." % (name, self.site_name(site)), "", text, "",
                   "Paid %s." % self.format_money(pay)]
        if outcome == "bad" and random.random() < 0.5 and person.wounds < WOUNDS_DOWN:
            hurt = min(random.randint(6, 18), WOUNDS_DOWN - person.wounds)
            person.wounds += hurt
            message.append("Wounds +%d%% (%s)." % (hurt, wound_word(person.wounds)))
            if person.wounds >= WOUNDS_DOWN:
                message.append("You go down, and they carry you off the floor.")
        if risen:
            message.append("%s: now %s." % (skill.capitalize(), skill_word(risen)))
        shifts = self.__dict__.setdefault("shifts", {})
        if not shifts.get(site["id"]):
            self.story_manager.plot_points += FIRST_SHIFT_POINTS
            message.append("Your first shift at a place like this: +%d plot points." % FIRST_SHIFT_POINTS)
        shifts[site["id"]] = shifts.get(site["id"], 0) + 1
        self.display_story_message(message, pause=1)
        self.pass_turns(1)
        self.autosave()
        return outcome

    # -- the berths board ------------------------------------------------------------------------
    def berths(self):
        """Ships leaving here that want a hand: the story's captains on their routes first, then
        ships that come and go. Each: {ship, kind, captain, who, to, legs, duty, wage, risk}. What
        is on here (game/labour.py) moves the wages, the number of ships and which kinds come;
        a kind kept away keeps the story's captain of that kind off the board too."""
        here = self.current_location.name
        names = {loc.name for loc in self.locations}
        offers = []
        chars = story_data()["characters"]
        terms = self.berth_terms()
        for who, (ship, kind) in NAMED_SHIPS.items():
            info = chars.get(who)
            if not info or self.story.where_is(who) != here or terms["kinds"].get(kind, 1) == 0:
                continue
            legs, dest = 1, None
            for ahead in range(1, 40):
                place = self.story.where_is(who, self.turn + ahead)
                if place != here:
                    legs, dest = ahead, place
                    break
            if dest is None or dest not in names:
                continue
            pick = _rng(who, self.turn - legs)
            duty = pick.choice(KINDS[kind]["duties"])
            offers.append({"ship": ship, "kind": kind, "who": who, "captain": self.story.fill("{%s}" % who),
                           "to": dest, "legs": legs, "duty": duty, "risk": terms["risk"],
                           "wage": int(LEG_WAGE * KINDS[kind]["wage"] * legs * terms["wage"])})
        pick = _rng(here, self.turn)
        places = sorted(n for n in names if n != here and self.location_named(n) is not None
                        and self.location_named(n).location_type in ("Planet", "AsteroidBase",
                                                                     "DeepSpaceOutpost", "ResearchColony"))
        count = max(0, (3 if self.current_location.location_type == "Planet" else 2) + terms["ships"])
        taken = {o["ship"] for o in offers}
        kinds = [k for k, weight in terms["kinds"].items() if weight > 0]
        for _ in range(count if places and kinds else 0):
            kind = pick.choices(kinds, weights=[terms["kinds"][k] for k in kinds])[0]
            ship = pick.choice([n for n in SHIP_NAMES if n not in taken])
            taken.add(ship)
            dest = pick.choice(places)
            legs = (1 if self.same_system(here, dest) else 2) + terms["legs"]
            offers.append({"ship": ship, "kind": kind, "who": None, "captain": None, "to": dest, "legs": legs,
                           "duty": pick.choice(KINDS[kind]["duties"]), "risk": terms["risk"],
                           "wage": int(LEG_WAGE * KINDS[kind]["wage"] * legs * pick.uniform(0.85, 1.15) * terms["wage"])})
        return offers

    def location_named(self, name):
        return next((loc for loc in self.locations if loc.name == name), None)

    def berth_label(self, offer):
        who = (" (%s)" % offer["captain"]) if offer["captain"] else ""
        known = "" if offer["to"] in self.known_locations else " (new to you)"
        return "%s%s to %s%s: %s wanted, %s, %d turn%s" % (
            offer["ship"], who, offer["to"], known, offer["duty"], self.format_money(offer["wage"]),
            offer["legs"], "" if offer["legs"] == 1 else "s")

    def handle_berths(self):
        offers = self.berths()
        footer = self.labour_screen_lines("berths")
        if not offers:
            self.display_simple_message(["No ship here wants a hand this turn."] + footer)
            return
        rows = [["Berths board: %s" % self.current_location.name], [""]]
        for number, offer in enumerate(offers, 1):
            rows.extend([line] for line in self.option_lines(number, self.berth_label(offer)))
        rows.extend([[""], ["Pay is on arrival. Your skill at the duty decides how the way goes."]])
        for line in footer:
            rows.extend([part] for part in self.word_wrap(line))
        print(self.create_box(rows, 'round'))
        answer = self.validate_input("Sign on (1-%d, Enter to leave): " % len(offers),
                                     [str(i) for i in range(1, len(offers) + 1)])
        if answer is None:
            return
        offer = offers[int(answer) - 1]
        skill = self.person.skill(offer["duty"])
        self.display_simple_message([
            "The %s, %s%s." % (offer["ship"], KINDS[offer["kind"]]["words"],
                               ", " + offer["captain"] + " commanding" if offer["captain"] else ""),
            "To %s, %d turn%s. Wanted: a %s (you: %s)." % (offer["to"], offer["legs"], "" if offer["legs"] == 1 else "s",
                                                         offer["duty"], skill_word(skill)),
            "Pays %s on arrival." % self.format_money(offer["wage"])], 0)
        if self.validate_input("Sign on? (yes/no): ", ['yes', 'no', 'y', 'n']) in ('yes', 'y'):
            self.sail_with(offer)

    def sail_with(self, offer, choices=None):
        """Work the way to the destination: a duty on each turn aboard, trouble now and then.
        Nothing changes until the ship docks (a voyage left half-way changes nothing). `choices`
        answers the duties in a test. Returns what happened: {pay, clean, wounds, practice}."""
        kind = KINDS[offer["kind"]]
        person = self.person
        duty = offer["duty"]
        pick = random.Random(random.random())
        practice = {}
        wounds = 0
        clean = True
        bonus = 0.0
        regard = 0
        down = False                # put down by a duty: the rest of the way in a bunk, half pay
        duties = list(DUTIES[duty])
        pick.shuffle(duties)
        for leg in range(offer["legs"]):
            if down:
                break
            moments = [(duty,) + duties[leg % len(duties)]]
            if pick.random() < TROUBLE_CHANCE * kind["risk"] + offer.get("risk", 0.0):
                text, options = TROUBLE[offer["kind"]]
                moments.append((None, text, options))
            for skill_of, text, options in moments:
                if down:
                    break
                rows = [["%s, turn %d of %d" % (offer["ship"], leg + 1, offer["legs"])], [""]]
                rows.extend([line] for line in self.word_wrap(text))
                rows.append([""])
                odds = []
                for number, option in enumerate(options, 1):
                    use = option[3] if len(option) > 3 else skill_of
                    chance = self.duty_chance(option[1], use, wounds)
                    odds.append((chance, use, option[2]))
                    rows.extend([line] for line in self.option_lines(
                        number, "%s (%s, %s)" % (option[0], use, odds_word(chance))))
                print(self.create_box(rows, 'round'))
                if choices:
                    answer = str(choices.pop(0))
                else:
                    answer = self.validate_input("Your call (1-%d, Enter = %d): " % (len(options), len(options)),
                                                 [str(i) for i in range(1, len(options) + 1)])
                chance, use, style = odds[int(answer) - 1 if answer else len(options) - 1]
                if pick.random() < chance:
                    practice[use] = practice.get(use, 0) + (2 if style == "bold" else 1)
                    if style == "bold":
                        bonus += 0.15
                        regard += 1
                    self.display_simple_message("It goes well.", 1, color='32')
                else:
                    clean = False
                    practice[use] = practice.get(use, 0) + 1
                    if style == "bold":
                        hurt = min(pick.randint(8, 22), WOUNDS_DOWN - person.wounds - wounds)
                        wounds += hurt
                        bonus -= 0.15
                        regard -= 1
                        if person.wounds + wounds >= WOUNDS_DOWN:
                            down = True
                            self.display_simple_message(
                                "It goes wrong, and you go down. You spend the rest of the way strapped "
                                "in a bunk.", 1, color='31')
                        else:
                            self.display_simple_message("It goes wrong. Wounds +%d%%." % hurt, 1, color='31')
                    else:
                        bonus -= 0.05
                        self.display_simple_message("It goes wrong, slowly. The mate writes it down.", 1, color='31')
        # docked: everything at once
        pay = max(0, int(offer["wage"] * (1 + bonus + 0.05 * person.skill(duty)) * (0.5 if down else 1)))
        person.money += pay
        person.wounds += wounds
        risen = [(s, person.train(s, n)) for s, n in sorted(practice.items())]
        key = offer["who"] or offer["ship"]
        marks = self.__dict__.setdefault("hand_regard", {})
        marks[key] = marks.get(key, 0) + regard + (1 if clean else 0)
        self.voyages = getattr(self, "voyages", 0) + 1
        points = VOYAGE_POINTS + (CLEAN_VOYAGE_POINTS if clean else 0)
        self.story_manager.plot_points += points
        self.pass_turns(offer["legs"])
        lines = ["Paid off at %s: %s." % (offer["to"], self.format_money(pay)),
                 "Plot points +%d%s." % (points, " (a clean run)" if clean else "")]
        lines += ["%s: now %s." % (s.capitalize(), skill_word(level)) for s, level in risen if level]
        if wounds:
            lines.append("Wounds +%d%% (%s)." % (wounds, wound_word(person.wounds)))
        self.arrive_on_foot(self.location_named(offer["to"]), lines)
        self.autosave()
        return {"pay": pay, "clean": clean, "wounds": wounds, "practice": practice}

    def duty_chance(self, base, skill, wounds=0):
        return max(0.05, min(0.95, base + 0.1 * self.person.skill(skill)
                             - (self.person.wounds + wounds) / 250.0))

    def arrive_on_foot(self, place, lines=()):
        """Off a ship at a dock: the place is known and visited, and a first visit counts."""
        lines = list(lines)
        self.current_location = place
        first = place.name not in self.discovered_locations
        self.discovered_locations.add(place.name)
        if place.name not in self.known_locations:
            self.known_locations.append(place.name)
        self.play_music()
        if first:
            self.story_manager.plot_points += 3
            about = (story_data()["places"].get(place.name) or {}).get("about")
            lines.append("First time at %s: +3 plot points." % place.name)
            if about:
                lines.extend([""] + self.word_wrap(about))
        news = self.labour_arrival_lines(place)
        self.__dict__.pop("labour_fresh", None)        # told here, not again on the turn's screen
        if news:
            lines.extend([""] + news)
        self.display_story_message(lines, pause=1)

    # -- passage ---------------------------------------------------------------------------------
    def passage_fare(self, dest):
        turns = 1
        return int(PASSAGE_FARE * (1 if self.same_system(self.current_location, dest) else 2)), turns

    def handle_passage(self):
        here = self.current_location.name
        places = [self.location_named(n) for n in self.known_locations if n != here and self.location_named(n)]
        if not places:
            self.display_simple_message("You know of nowhere else to go.")
            return
        rows = [["Passage from %s" % here], [""]]
        for number, place in enumerate(places, 1):
            fare, turns = self.passage_fare(place)
            rows.extend([line] for line in self.option_lines(
                number, "%s: %s, %d turn%s" % (place.name, self.format_money(fare), turns, "" if turns == 1 else "s")))
        print(self.create_box(rows, 'round'))
        answer = self.validate_input("Book (1-%d, Enter to leave): " % len(places),
                                     [str(i) for i in range(1, len(places) + 1)])
        if answer is None:
            return
        self.take_passage(places[int(answer) - 1])

    def take_passage(self, place):
        fare, turns = self.passage_fare(place)
        if self.person.money < fare:
            self.display_simple_message("The fare is %s; you have %s." % (
                self.format_money(fare), self.format_money(int(self.person.money))))
            return False
        self.person.money -= fare
        self.pass_turns(turns)
        self.arrive_on_foot(place, ["Passage to %s: %s." % (place.name, self.format_money(fare))])
        self.autosave()
        return True

    # -- the locker ------------------------------------------------------------------------------
    def locker_price(self, good, units, selling):
        loc = self.current_location
        price = loc.trade_price(good, units, selling=selling)
        tax = loc.calculate_tax_rate(self.rank, price * units)
        return int(round(price * units * ((1 - tax) if selling else (1 + tax))))

    def locker_goods_here(self):
        loc = self.current_location
        return [g for g in ("tech", "agri", "salt", "fuel")
                if loc.can_trade(g) and (g not in ("salt", "fuel") or loc.trades_bulk(g)) and loc.market[g] > 0]

    def handle_locker(self):
        person = self.person
        goods = self.locker_goods_here()
        rows = [["Your locker: %d/%d units" % (person.locker_units(), LOCKER_UNITS)], [""]]
        if person.locker:
            for good, units in sorted(person.locker.items()):
                rows.append(["%s: %d (paid %s)" % (good, units, self.format_money(person.locker_cost.get(good, 0)))])
        else:
            rows.append(["Empty."])
        rows.extend([[""], ["An able hand may carry a few units of private trade aboard. "
                                  "Buy here, sell where it is dear."]])
        print(self.create_box(rows, 'round'))
        if not goods:
            self.display_simple_message("Nothing trades here.")
            return
        what = self.validate_input("Buy or sell? (buy/b, sell/s, Enter to leave): ", ['buy', 'b', 'sell', 's'])
        if what is None:
            return
        good = commodity_from(self.validate_input("Which? %s: " % ", ".join(goods),
                                                  [w for g in goods for w in (g,) + COMMODITIES[g]]))
        if good is None:
            return
        if what in ('buy', 'b'):
            room = LOCKER_UNITS - person.locker_units()
            units = self.validate_input("How many (1-%d)? " % room, [str(i) for i in range(1, room + 1)]) if room else None
            if room <= 0:
                self.display_simple_message("The locker is full.")
            elif units:
                self.locker_buy(good, int(units))
        else:
            held = person.locker.get(good, 0)
            if not held:
                self.display_simple_message("You have no %s." % good)
                return
            units = self.validate_input("How many (1-%d)? " % held, [str(i) for i in range(1, held + 1)])
            if units:
                self.locker_sell(good, int(units))

    def locker_buy(self, good, units):
        person = self.person
        units = min(units, LOCKER_UNITS - person.locker_units())
        cost = self.locker_price(good, units, selling=False)
        if units <= 0 or good not in self.locker_goods_here():
            return False
        if person.money < cost:
            self.display_simple_message("%d %s cost %s; you have %s." % (
                units, good, self.format_money(cost), self.format_money(int(person.money))))
            return False
        person.money -= cost
        person.locker[good] = person.locker.get(good, 0) + units
        person.locker_cost[good] = person.locker_cost.get(good, 0) + cost
        self.current_location.trade_impact(good, units, selling=False)
        self.display_simple_message("Into the locker: %d %s for %s." % (units, good, self.format_money(cost)))
        return True

    def locker_sell(self, good, units):
        person = self.person
        held = person.locker.get(good, 0)
        units = min(units, held)
        if units <= 0 or good not in self.locker_goods_here():
            return False
        revenue = self.locker_price(good, units, selling=True)
        paid = person.locker_cost.get(good, 0) * units / held
        person.money += revenue
        person.locker[good] = held - units
        person.locker_cost[good] = person.locker_cost.get(good, 0) - paid
        if not person.locker[good]:
            person.locker.pop(good)
            person.locker_cost.pop(good, None)
        self.locker_profit = getattr(self, "locker_profit", 0) + int(revenue - paid)
        self.current_location.trade_impact(good, units, selling=True)
        self.display_simple_message("Sold from the locker: %d %s for %s (profit %s)." % (
            units, good, self.format_money(revenue), self.format_money(int(revenue - paid))))
        return True

    # -- the person ------------------------------------------------------------------------------
    def show_person(self):
        person = self.person
        rows = [[self.player_name], [""],
                ["Wounds: %d%% (%s)" % (person.wounds, wound_word(person.wounds))],
                ["Money: %s" % self.format_money(int(person.money))], [""], ["Skills"]]
        rows.extend([line] for line in self.word_wrap(
            "The bar fills with practice. The next level comes near its end: sooner for some, later for others."))
        rows.append([""])
        for skill in SKILLS:
            level = person.skill(skill)
            rows.append(["%-9s %-7s %s" % (skill.capitalize(), skill_word(level), meter(person.progress(skill)))])
            rows.extend([["  " + line] for line in self.word_wrap(SKILL_WORDS[skill], box_inner_width() - 4)])
        if person.gear:
            rows.extend([[""], ["Gear: " + ", ".join(person.gear)]])
        items = sorted(k for k, v in person.items.items() if isinstance(v, int) and v > 0)
        if items:
            rows.extend([[""], ["Carried: " + ", ".join(i.replace("_", " ") for i in items)]])
        if person.locker:
            rows.extend([[""], ["Locker: " + ", ".join("%s %d" % (g, n) for g, n in sorted(person.locker.items()))]])
        regard = getattr(self, "hand_regard", {})
        good = [k for k, v in sorted(regard.items()) if v >= 2]
        if good:
            names = [self.story.fill("{%s}" % k) if k in NAMED_SHIPS else k for k in good]
            rows.extend([[""], ["Would sign you again: " + ", ".join(names)]])
        print(self.create_box(rows, 'round'))
        ask("Press Enter to continue...")

    def show_hand_help(self):
        rows = [["How to play: without a ship"], [""],
                ["You have no ship. Until you do, you work: shifts at the docks and the plants (work/w) "
                 "pay a wage and train a skill; ships leaving the dock want hands for one duty each (berths/bb), "
                 "and signing on takes you to their destination, paid on arrival; or you can buy passage "
                 "(passage/pa). An able hand may carry a few units of private trade in a locker (locker/lo): "
                 "buy where it is cheap, sell at the next dock."],
                [""],
                ["The docks have their own weather: a strike or a rush order at the plant, gas or a rich seam "
                 "in the mines, a convoy on the ring, crews short on the berths. It moves the wages, closes "
                 "jobs and changes the board for a few turns. The turn's screen shows what is on here; look "
                 "and the needle office at Beta tell what is on at the other docks."],
                [""],
                ["Six skills (skills/sk): loader, mechanic, gunner, navigator, steward and broker. They rise "
                 "with work and duties, and decide how the way goes. Bold choices teach more and pay more, "
                 "and can hurt: work can put you down, a fight can kill. Wounds heal with time, faster with rest "
                 "(end/e)."],
                [""],
                ["Look around the docks (look/lk) for people and things, think (th) for your notes, and follow "
                 "the story (log/l, journal/j). Plot points move it: earn them by working, sailing and going "
                 "places. Each shift, voyage or rest is a turn; the game saves itself after every one."]]
        print(self.create_box(rows, 'round'))
        ask("Press Enter to continue...")


# The game's other modules, imported last so that the modules can refer to each other.
from .story import story_data  # noqa: E402
from .terminal import box_inner_width, plain_terminal, short_logo  # noqa: E402
from .commands import COMMODITIES, GLOBAL_COMMANDS, commodity_from  # noqa: E402
from .encounters import odds_word  # noqa: E402
from .person import LOCKER_UNITS, SKILL_WORDS, SKILLS, WOUNDS_DOWN, skill_word  # noqa: E402
from .terminal import ask  # noqa: E402
