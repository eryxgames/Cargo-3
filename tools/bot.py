"""Playthrough bot: plays cargo.py through its real commands until an ending.

It reads the game's state to decide (like a player reading the screen) but acts
only by answering the game's own prompts, so every step is something a player
can type.

usage: bot.py cargo.py <path: trade|combat|discovery> <seed> [max_turns] [--verbose]

Without a ship (Cargo 3's first chapters) it plays an able hand: it signs on where the pay and
its skill are best, works a shift when no berth suits, rests when hurt, and keeps a locker of
private trade. With money to spare it buys skill: an implant at the clinic at Epsilon when it
has two and a half times the price, a lesson with a master now and then when it has ten times
the lesson's (--no-spending turns that off, to measure the hand's earnings alone).
"""
import sys, os, io, re, json, random, shutil, traceback, tempfile, builtins, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import headless

path, goal, seed = sys.argv[1], sys.argv[2], int(sys.argv[3])
# --voyage=short|standard|long (default standard)
VOYAGE = {"short": "1", "standard": "2", "long": "3"}.get(
    next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--voyage=")), "standard"), "2")
max_turns = int(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4].isdigit() else 3000
verbose = "--verbose" in sys.argv
# --captain=trade|combat|discovery|tycoon: play as a captain from Cargo 1 with that ending (and a
# handful of the flags the act-1 scenes read) instead of a fresh one
CAPTAIN = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--captain=")), None)
# --difficulty=1|2|3 (default 2)
DIFFICULTY = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--difficulty=")), "2")
# --afloat: the captain has a ship from the start (Cargo 3 begins on foot), to play a captain's
# turns until the story gives a ship
AFLOAT = "--afloat" in sys.argv
NO_SPENDING = "--no-spending" in sys.argv
ASHORE = "--ashore" in sys.argv         # Cargo 3: never get the ship out of the yard (to measure a hand's life)
# --curious: look around at every dock and follow what turns up (people, sights, side quests);
# without it the bot never looks, and the result still says whom it shared a dock with
CURIOUS = "--curious" in sys.argv or "--leads" in sys.argv
# --leads: curious, and every other voyage goes where one of the captain's thoughts points
LEADS = "--leads" in sys.argv
save_every = 0
trace_path = None
for a in sys.argv:
    if a.startswith("--save-every="):
        save_every = int(a.split("=")[1])
    if a.startswith("--trace="):
        trace_path = a.split("=", 1)[1]
trace_file = open(trace_path, "w", encoding="utf-8") if trace_path else None
ledger_on = "--ledger" in sys.argv
LEDGER = collections.defaultdict(lambda: collections.defaultdict(float))


def install_ledger(cargo):
    """Record every change to money, plot points and research points, by the
    function that made it (for tools/economy.py)."""
    def tracked(cls, attr, book):
        store = "_ledger_" + attr

        def get(self):
            return self.__dict__.get(store, 0)

        def put(self, value):
            old = self.__dict__.get(store)
            self.__dict__[store] = value
            if old is None or not isinstance(value, (int, float)):
                return
            delta = value - old
            if delta:
                frame = sys._getframe(1)
                while frame and frame.f_code.co_name in ("put", "<lambda>"):
                    frame = frame.f_back
                who = getattr(frame.f_code, "co_qualname", frame.f_code.co_name) if frame else "?"
                LEDGER[book + ("+" if delta > 0 else "-")][who] += delta
        setattr(cls, attr, property(get, put))
    tracked(cargo.Person, "money", "money")
    tracked(cargo.Person, "research_points", "rp")
    tracked(cargo.StoryManager, "plot_points", "plot_points")
traced_turn = [-1]


def write_trace(g, final=False):
    """One line per turn: the story kit's view of the game, and the game's own verdicts."""
    if not trace_file or g is None or (g.turn == traced_turn[0] and not final):
        return
    import cargo_story
    traced_turn[0] = g.turn
    snap = cargo_story.snapshot(g)
    snap["verdicts"] = cargo_story.game_verdicts(g)
    moment = cargo_story.story_moment(g)
    if moment:
        snap["moment"] = moment
    snap["style"] = goal
    snap["seed"] = seed
    if final:
        snap["final"] = True
        snap["ending"] = getattr(g, "ending_reached", None)
    trace_file.write(json.dumps(snap, ensure_ascii=False, separators=(",", ":")) + "\n")

home = tempfile.mkdtemp(prefix="cargo-bot-")
os.environ["CARGO_SAGA_HOME"] = home
size = os.terminal_size((int(next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--cols=")), 80)), 40))
shutil.get_terminal_size = lambda fallback=(80, 24): size
cargo = headless.load(path)
try:                                    # Cargo 3: upgrades on the price curve (game/prices.py)
    from game.prices import upgrade_price
except ImportError:
    upgrade_price = None
# the flags of the docks' side quests (Cargo 2.1), to see when each moves
_people = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(path))), "story", "cargo3", "people.json")
DOCK_FLAGS = list(json.load(open(_people, encoding="utf-8"))["flags"]) if os.path.exists(_people) else []
if ledger_on:
    install_ledger(cargo)
headless.patch(cargo, headless.IO())
random.seed(seed)
rng = random.Random(seed * 7 + 1)

PATH_CHOICE = {   # which follow-up chapter to pick, by goal
    "trade": ["ch2a", "ch3a", "ending_trade"],
    "combat": ["ch2b", "ch3b", "ending_combat"],
    "discovery": ["ch2a", "ch3c", "ending_discovery"],
    "discovery2": ["ch2b", "ch3c", "ending_discovery"],
    "dawn": ["ch2a", "ch3d", "ending_dawn"],          # Cargo 2's hidden road
}[goal]
# whose good opinion a road needs, so story choices can lean that way (Cargo 2)
ROAD_STAT = {"trade": "standing.hansa", "combat": "standing.mandate", "discovery": "standing.concord",
             "discovery2": "standing.concord", "dawn": "dawn_trust"}[goal]


class Done(Exception):
    pass


class Bot:
    def __init__(self):
        self.game = None
        self.ctx = None            # (prompt, options) while validate_input is asking
        self.story_choices = 0     # choices made in story scenes
        self.qty = False
        self.turn_seen = -1
        self.flags = set()
        self.item = None
        self.upgrade = None
        self.building = None
        self.research = None
        self.dest = None
        self.cost = collections.defaultdict(float)   # average price paid per item
        self.sell_at = {}
        self.unknown = collections.Counter()
        self.inputs = 0
        self.stall = 0
        self.last_progress = (0, None)
        self.log = []
        self.pax_dest = None
        self.port_step = None
        self.loads = 0
        self.reload_step = None
        self.reload_turn = -1
        self.sight = None
        self.hand = {}             # the able hand's pending answers: {prompt word: answer}
        self.hand_log = collections.Counter()
        self.first_ship = None
        self.docks = {"places": collections.Counter(), "together": collections.Counter(), "first": {}, "flags": {},
                      "leads": collections.Counter(), "lead_first": {},
                      "unlocked": {}, "chapters": {}, "lead_from": collections.Counter()}

    # ---- helpers -----------------------------------------------------
    def note_docks(self, g):
        """Where the captain is this turn, who shares the dock, and when the side quests move."""
        if not hasattr(g, "people_here"):
            return
        d = self.docks
        d["places"][g.current_location.name] += 1
        for cid in g.people_here():
            d["together"][cid] += 1
            d["first"].setdefault(cid, g.turn)
        for kind in g.unlocked_location_types:
            d["unlocked"].setdefault(kind, g.turn)
        d["chapters"].update({c: g.turn for c in g.story_manager.completed_chapters if c not in d["chapters"]})
        states = g.story_manager.story_states
        for flag in DOCK_FLAGS:
            if states.get(flag) and flag not in d["flags"]:
                d["flags"][flag] = g.turn

    def advances(self, g, choice):
        """A choice that sets a flag not yet set or gives an item not yet held. A careful captain
        does not count a fight with people who mean to kill, or the restart from the wrong end while
        it can still be started from home (Cargo 3)."""
        effects = choice.get("effects") or {}
        code = effects.get("code") or ""
        code = " ".join(code) if isinstance(code, list) else code
        if code.startswith("brawl ") and getattr(cargo, "FOES", {}).get(code.split()[1], {}).get("lethal"):
            return False
        if "chose_loop" in (effects.get("set") or ()) and g.story_manager.current_chapter == "ch6" \
                and g.turn - self.docks["chapters"].get("ch5", g.turn) < 120:
            return False
        states = g.story_manager.story_states
        if any(not states.get(f) for f in ([effects["set"]] if isinstance(effects.get("set"), str) else effects.get("set", []))):
            return True
        items = (effects.get("give") or {}).get("items", [])
        return any(not g.person.items.get(i) for i in ([items] if isinstance(items, str) else items))

    def lead_place(self, g):
        """A place one of the captain's thoughts names (not this one), read off the think screen."""
        import game.story as gs
        snap = g.story.snapshot()
        names = sorted((l.name for l in g.locations), key=len, reverse=True)
        for nid, node in gs.story_data()["nodes"].items():
            if node.get("kind") != "thought" or not g.story.check(g.story.requires_of(node), snap):
                continue
            text = g.story.fill(node["text"] if isinstance(node["text"], str) else " ".join(node["text"]))
            for name in names:
                short = " ".join(name.split()[:2]) if len(name.split()) > 2 else name
                if name != g.current_location.name and re.search(r"(?<![\w-])%s(?![\w-])" % re.escape(short), text):
                    self.docks["lead_from"][nid] += 1
                    return name
        return None

    def pick_sight(self, g):
        """The sight a curious captain looks at: one with a step forward, else one not seen yet."""
        import game.story as gs
        nodes = gs.story_data()["nodes"]
        sights = [n if not (ASHORE and n == "ship.yard") else None for n in g.sights_here()]
        snap = g.story.snapshot()
        for i, nid in enumerate(sights):
            if nid and any(self.advances(g, c) and g.story.check(c.get("requires"), snap)
                           for c in nodes[nid].get("choices") or []):
                return str(i + 1)
        for i, nid in enumerate(sights):
            if nid and nid not in g.story.done:
                return str(i + 1)
        return None

    def need(self):
        """Open requirement keys of the current chapter and of the wanted next chapter."""
        g = self.game
        sm = g.story_manager
        ch = sm.chapters[sm.current_chapter]
        reqs = []
        for m in ch.milestones.values():
            if not m.completed:
                reqs.append(m.requirements)
        reqs.append(ch.requirements)
        for nid in ch.next_chapters:
            if nid in PATH_CHOICE:
                reqs.append(sm.chapters[nid].requirements)
        out = {}
        for r in reqs:
            for k, v in r.items():
                if not cargo.MilestoneRequirements._check_single_requirement(k, v, g):
                    out.setdefault(k, v)
        return out

    def prices(self, loc, item):
        if not loc.can_trade(item):
            return None
        if item in ("salt", "fuel") and not loc.trades_bulk(item):
            return None
        p = loc.market.get(item, 0)
        return p if p and p > 0 else None

    def best_trade(self):
        g = self.game
        here = g.current_location
        best = None
        for item in ("tech", "agri", "salt", "fuel"):
            buy = self.prices(here, item)
            if not buy:
                continue
            if g.ship.hold_room(item) <= 0:
                continue
            for loc in g.locations:
                if loc is here or loc.name not in g.known_locations:
                    continue
                sell = self.prices(loc, item)
                if not sell:
                    continue
                load = min(g.ship.hold_room(item), 400)       # a full load moves both prices
                margin = loc.trade_price(item, load, True) * 0.92 - here.trade_price(item, load, False) * 1.08
                if margin > 0 and (best is None or margin / buy > best[0]):
                    best = (margin / buy, item, loc.name)
        return best

    def best_sale_elsewhere(self, item):
        g = self.game
        best = None
        for loc in g.locations:
            if loc is g.current_location:
                continue
            p = self.prices(loc, item)
            if p and (best is None or p > best[0]):
                best = (p, loc.name)
        return best

    # ---- main menu ---------------------------------------------------
    def main_action(self, options):
        g = self.game
        ship = g.ship
        here = g.current_location
        if g.turn != self.turn_seen:
            self.turn_seen = g.turn
            self.flags = set()
            self.note_docks(g)
        need = self.need()

        # every so often: save under a name, then load that save and play on from it
        if self.reload_step == "load" and "load" in options:
            self.reload_step = None
            return "load"
        if save_every and g.turn and g.turn % save_every == 0 and g.turn != self.reload_turn and "save" in options:
            self.reload_turn = g.turn
            self.reload_step = "load"
            return "save"

        # a curious captain looks around first (Cargo 2.1)
        if CURIOUS and "look" in options and "look" not in self.flags and hasattr(g, "sights_here"):
            self.flags.add("look")
            self.sight = self.pick_sight(g)
            if self.sight:
                return "look"

        if "repair" in options and ship.damage >= 20 and "repair" not in self.flags:
            self.flags.add("repair")
            if ship.money >= ship.damage * 10:
                return "r"

        # sell what we carry when this is the planned market or a profitable one
        for item in ("tech", "agri", "salt", "fuel"):
            if ship.cargo[item] > 0 and ("sell", item) not in self.flags:
                price = self.prices(here, item)
                if price is None:
                    continue
                planned = self.sell_at.get(item) == here.name
                better = self.best_sale_elsewhere(item)
                # what the goods really cost (load size and tax included), and what selling them
                # all here would really bring, since a big load moves the price
                held = ship.cargo[item]
                cost = ship.__dict__.get("cost_basis", {}).get(item, 0) / held if held else 0
                tax = ship.trade_tax(here.calculate_tax_rate(g.rank, price))
                price = here.trade_price(item, held, selling=True) * (1 - tax)
                bought_here = self.__dict__.setdefault("bought_at", {}).get(item) == here.name
                stale = better is None or g.turn - self.__dict__.setdefault("bought_turn", {}).get(item, g.turn) > 12
                held_for = g.turn - self.__dict__.setdefault("bought_turn", {}).get(item, g.turn)
                if (price >= cost * 1.05 and not bought_here) or (planned and price >= cost) \
                        or (stale and price >= cost * 0.8) or held_for > 25:      # cut the loss
                    self.flags.add(("sell", item))
                    self.item = item
                    return "s"

        # passengers
        if "port" in options and "port" not in self.flags and goal in ("trade", "discovery", "dawn") and \
                ("passengers_transported" in need or "passenger_reputation" in need or
                 any(m.passengers for m in getattr(ship, "passenger_modules", []))):
            self.flags.add("port")
            self.port_step = "start"
            return "p"

        # stock markets
        want_sm = need.get("buildings_built", {}).get("stockmarket") if isinstance(need.get("buildings_built"), dict) else None
        if want_sm and "build" in options and "build" not in self.flags and "stockmarket" not in here.buildings:
            cost = 5000 * (here.buildings.count("stockmarket") + 1)
            if ship.money >= cost * 2:
                self.flags.add("build")
                self.building = "stockmarket"
                return "bl"
        want_ng = need.get("buildings_built", {}).get("Neuroengineering Guild") if isinstance(need.get("buildings_built"), dict) else None
        if want_ng and "build" in options and "build" not in self.flags:
            if ship.money >= 7000 * (here.buildings.count("Neuroengineering Guild") + 1) * 2:
                self.flags.add("build")
                self.building = "neuroengineering"
                return "bl"

        # a mine, when the story needs Asteroid Bases and they are not open yet
        wanted_locs = need.get("locations_discovered")
        if isinstance(wanted_locs, dict) and "AsteroidBase" in wanted_locs and \
                "AsteroidBase" not in g.unlocked_location_types and \
                not any(l.mining_platforms for l in g.locations):
            if here.mineral_deposits:
                if "mine" in options and "mine" not in self.flags and ship.money >= 10000:
                    self.flags.add("mine")
                    return "m"
            elif "action" in options and "geoscan" not in self.flags and ship.research_points >= 75:
                self.flags.add("geoscan")
                self.research = "geoscan"
                return "a"

        # research
        want_res = [r for r in need.get("research_unlocked", []) if r not in g.research.unlocked_options]
        if goal.startswith("discovery") or want_res:
            todo = want_res or [r for r in g.research.research_costs if r not in g.research.unlocked_options]
            todo = [r for r in todo if ship.research_points >= g.research.research_costs.get(r, 10 ** 9)]
            if todo and "action" in options and "research" not in self.flags:
                self.flags.add("research")
                self.research = todo[0]
                return "a"

        # a heavier hull at a planet shipyard, once the money is there (fighters and explorers first)
        if "upgrade" in options and "upgrade" not in self.flags and isinstance(here, cargo.Planet) \
                and ship.hull + 1 < len(ship.HULLS):
            price = ship.HULLS[ship.hull + 1]["price"]
            if ship.money > price * (2 if goal in ("combat", "discovery", "discovery2") else 4):
                self.flags.add("upgrade")
                self.upgrade = "hull"
                return "u"

        # modules at a yard (Cargo 2): a trader wants hold and a lower tax, a fighter guns and
        # shields; a broken module is mended; one visit to the yard a turn
        if "upgrade" in options and "upgrade" not in self.flags and hasattr(ship, "grips") and g.has_yard():
            wants = (["turret", "shield", "hangar", "repair", "turret", "shield", "salvage"]
                     if goal == "combat" or "combat_victories" in need
                     else ["container", "offloader", "container", "repair", "scanner", "container", "container"])
            fitted = [m["kind"] for m in ship.modules]
            todo = [k for k in wants if fitted.count(k) < wants.count(k)]
            broken = any(m["condition"] < 40 for m in ship.modules)
            self.yard = None
            if broken and ship.money > 3 * sum(cargo.mend_cost(m) for m in ship.modules) + 20000:
                self.yard = ["m"]
            elif todo and len(fitted) < ship.grips() and ship.money > 4 * cargo.MODULES[todo[0]][1] + 20000:
                self.yard = ["f", str(list(cargo.MODULES).index(todo[0]) + 1)]
            if self.yard:
                self.flags.add("upgrade")
                self.upgrade = "modules"
                return "u"

        # ship upgrades: attack decides every fight (attack must exceed the enemy's defence,
        # which goes up to 6), defence only reduces damage
        if "upgrade" in options and "upgrade" not in self.flags:
            cap = 12 if (goal == "combat" or "combat_rating" in need) else 7
            order = []
            if ship.attack < 3:
                order = [("attack", 1.15)]
            elif ship.defense < 3:
                order = [("defense", 1.5)]
            elif ship.attack < 7:
                order = [("attack", 1.6), ("defense", 4)]
            else:
                order = [("defense", 3), ("speed", 4), ("attack", 4)]
            for prop, reserve in order:
                stat = getattr(ship, prop)
                price = upgrade_price(ship, prop) if upgrade_price else ship.upgrade_costs[prop]
                if stat < cap and ship.money >= price * reserve:
                    self.flags.add("upgrade")
                    self.upgrade = prop
                    return "u"

        # a fighter takes bounties two days in three (a hunt uses the turn)
        fighter = goal == "combat" or "combat_victories" in need
        if fighter and "hunt" in options and "hunt" not in self.flags and ship.damage < 40 and g.turn % 3:
            self.flags.add("hunt")
            return "hu"

        # every fifth turn a look in the shop for gear that suits the captain's road
        if "shop" in options and "shop" not in self.flags and g.turn % 5 == 0 and ship.money > 20000:
            self.flags.add("shop")
            return "sh"

        # idle money buys Hansa bonds, which lower the convoy dues
        if "hansa" in options and "hansa" not in self.flags and ship.money > 15 * g.bond_price() \
                and getattr(g, "hansa_bonds", 0) < 8:
            self.flags.add("hansa")
            return "ha"

        # now and then a drink in the cantina: people, rumours, crew for hire
        if "cantina" in options and "cantina" not in self.flags and g.turn % 4 == 0:
            self.flags.add("cantina")
            return "c"

        # buy for the best route and go
        if "buy" not in self.flags:
            self.flags.add("buy")
            trade = self.best_trade()
            if trade and ship.money >= 50:
                _, item, dest = trade
                self.item = item
                self.dest = dest
                self.sell_at[item] = dest
                self.buy_price = self.prices(here, item)
                held = ship.cargo[item]
                self.__dict__.setdefault("bought_turn", {})[item] = g.turn
                self.__dict__.setdefault("bought_at", {})[item] = here.name
                self.cost[item] = self.buy_price if not held else (self.cost[item] or self.buy_price)
                return "b"

        if "travel" not in self.flags:
            self.flags.add("travel")
            dest = None
            # places the story asks us to find come first
            wanted = need.get("locations_discovered")
            if isinstance(wanted, dict):
                for loc in g.locations:
                    if loc.location_type in wanted and loc.name not in g.discovered_locations and loc is not here \
                            and g.count_discovered(loc.location_type) < wanted[loc.location_type]:
                        dest = loc.name
                        break
            # a captain who follows leads goes where a thought points, every other voyage
            if dest is None and LEADS and g.turn % 2 == 0 and hasattr(g, "sights_here"):
                dest = self.lead_place(g)
                if dest:
                    self.docks["leads"][dest] += 1
                    self.docks["lead_first"].setdefault(dest, g.turn)
            # then a passenger destination, then unexplored places, then the trade plan
            if dest is None and self.pax_dest and self.pax_dest != here.name:
                dest = self.pax_dest
            # a trader who only shuttles between two docks never sees the rest of the map
            unseen = [l.name for l in g.locations if l.name not in g.known_locations]
            if dest is None and unseen and (len(g.known_locations) < 5 or g.turn % 6 == 0):
                dest = rng.choice(unseen)
            if dest is None:
                carried = [i for i in ship.cargo if ship.cargo[i] > 0 and self.sell_at.get(i) and self.sell_at[i] != here.name]
                if carried:
                    dest = self.sell_at[carried[0]]
            if dest is None:
                unknown = [l.name for l in g.locations if l.name not in g.known_locations]
                if unknown:
                    dest = rng.choice(unknown)
            if dest is None and self.dest and self.dest != here.name:
                dest = self.dest
            if dest is None:
                others = [l.name for l in g.locations if l is not here]
                dest = rng.choice(others) if others else None
            if dest:
                self.travel_to = dest
                return "t"
        return "e"

    # ---- answering prompts ---------------------------------------------
    def answer(self, tail):
        g = self.game
        self.inputs += 1
        if self.ctx is not None:
            prompt, options = self.ctx
            self.ctx = None
            options = list(options)
            p = prompt.lower()
            if "end" in options and "work" in options:
                return self.hand_action(options)
            if "end" in options and "buy" in options:
                if self.first_ship is None:
                    self.first_ship = g.turn
                return self.main_action(options)
            hand = self.hand_answer(p, options)
            if hand is not None:
                return hand
            if p.startswith(("buy which", "sell which")):
                return self.item
            if "your place in the needle" in p:      # the needle office (Cargo 2)
                fare = g.needle_fare("middle")
                if g.ship.money > 60 * fare:
                    return "1"
                return "2" if g.ship.money > 2 * fare else "3"
            if "property to upgrade" in p:
                return self.upgrade
            if p.startswith("yard:") or p.startswith("fit which"):      # the yard (Cargo 2)
                return (getattr(self, "yard", None) or [""]).pop(0) if getattr(self, "yard", None) else ""
            if "overhaul the hull" in p:
                return "yes"
            if "building type" in p:
                return self.building
            if "choose your path" in p:
                sm = g.story_manager
                ch = sm.chapters[sm.current_chapter]
                avail = ch.get_next_chapters(g)
                for i, c in enumerate(avail, 1):
                    if c.id in PATH_CHOICE:
                        return str(i)
                return ""          # wait for the wanted path to open
            if "do you want to resign" in p or "are you sure" in p or "play again" in p:
                return "no"
            if "choose action type" in p:           # research/actions menu
                if self.research == "geoscan":
                    self.research = None
                    return "geoscan"
                if self.research:
                    return "research"
                return "back"
            if "mining options" in p:
                return "build"
            if "choose deposit type" in p:
                return options[0]
            if "choose research option" in p:
                r, self.research = self.research, None
                return r if r in options else ""
            if "modules" in options and "board" in options:      # port menu
                return self.port_action()
            if "module number to buy" in p:
                if self.port_step == "buy_module":
                    self.port_step = "bought"
                    ids = [o for o in options if o != "back"]
                    mods = g.port_system.available_modules
                    afford = [i for i in ids if mods[i]["cost"] <= g.ship.money * 0.5]
                    if afford:
                        return min(afford, key=lambda i: mods[i]["cost"])
                return "back"
            if p.startswith("hansa - choose"):        # the Hansa terminal: a bond when money is idle
                if g.ship.money > 15 * g.bond_price() and getattr(g, "hansa_bonds", 0) < 8:
                    return "b"
                return ""
            if p.startswith("your move"):             # a fight, a situation or the bounty board
                return self.move(options)
            if p.startswith("look at"):               # the look list (Cargo 2.1)
                pick, self.sight = self.sight, None
                return pick or ""
            if p.startswith("your choice"):           # a story scene's choice
                self.story_choices += 1
                offered = getattr(getattr(g, "story", None), "offered", None) or []
                at = getattr(g.story, "offered_at", None) or ""
                if CURIOUS and offered and at:              # any scene: a step forward first
                    forward = [i for i, c in enumerate(offered) if self.advances(g, c)]
                    if forward:
                        return str(forward[0] + 1)
                if offered and options:
                    gain = [(c.get("effects") or {}).get(ROAD_STAT, 0) for c in offered]
                    if max(gain) > 0:
                        return str(gain.index(max(gain)) + 1)
                    safe = [i for i, c in enumerate(offered) if (c.get("effects") or {}).get(ROAD_STAT, 0) >= 0]
                    return str(random.choice(safe or list(range(len(offered)))) + 1)
                return random.choice(options) if options else ""
            if "choose action (1/2/3)" in p or "choose action" in p or "your response" in p:
                self.unknown[("choice", tuple(options)[:6])] += 1
                return options[0] if options else ""
            if "0 to leave" in p:
                return "0"
            if "choose item to buy" in p:
                wanted = {"trade": ["quantum_compressor", "cargo_extender", "containment_field", "stasis_vault",
                                    "auto_loader", "cargo_scanner", "shield", "patcher"],
                          "combat": ["combat_drone", "turrets", "shield", "shield_booster", "mining_laser",
                                     "advanced_radar", "patcher", "neutron_shield", "warp_core", "emergency_warp"]}.get(
                    goal, ["research_module", "data_analyzer", "quantum_scanner", "probe", "scanner", "shield",
                           "cargo_extender", "patcher"])
                prices = dict((name, data["price"]) for name, data in g.shop.current_turn_items)
                for name in wanted:
                    if name in options and not g.ship.items.get(name) and prices.get(name, 10 ** 9) * 4 < g.ship.money:
                        return name
                return "none"
            if "none" in options:
                return "none"
            if "back" in options:
                return "back"
            self.unknown[("prompt", prompt[:50])] += 1
            return ""
        if self.qty:
            asked, self.qty = str(self.qty).lower(), False
            if "research points to buy" in asked:      # a researcher selling research for credits
                if goal.startswith("discovery") and g.ship.money > 50000 and "research_points" in self.need():
                    return "half"
                return ""
            return "max"
        # a phrase may be wrapped across the lines of a narrow box: match it with the frames
        # taken out and the lines joined
        t = " ".join(re.sub("[\u2500-\u259f|]", " ", tail).split()).lower()
        if "save as" in t:
            return "botsave"
        if "type a number to load it" in t:
            return "1"
        if "choose a location to travel to" in t or "enter location name" in t or "enter the number or name" in t:
            return self.travel_to
        if "select passengers" in t:
            if self.port_step == "board":
                self.port_step = "boarding"
                return "a"
            return ""
        if "choose destination number" in t:
            loc = g.current_location.name
            waiting = g.port_system.waiting_passengers.get(loc, [])
            dests = sorted(set(p.destination for p in waiting))
            if not dests:
                return "0"
            counts = [sum(1 for p in waiting if p.destination == d) for d in dests]
            i = max(range(len(dests)), key=lambda k: counts[k])
            self.pax_dest = dests[i]
            return str(i + 1)
        if "choose module number" in t:
            return "a"
        if "press enter" in t:
            return ""
        self.unknown[("raw", t.strip().splitlines()[-1][:50] if t.strip() else "")] += 1
        return ""

    # ---- the able hand (Cargo 3, without a ship) ------------------------------------------
    def hand_action(self, options):
        g = self.game
        person = g.person
        if g.turn != self.turn_seen:
            self.turn_seen = g.turn
            self.flags = set()
            self.note_docks(g)
        if self.reload_step == "load" and "load" in options:
            self.reload_step = None
            return "load"
        if save_every and g.turn and g.turn % save_every == 0 and g.turn != self.reload_turn and "save" in options:
            self.reload_turn = g.turn
            self.reload_step = "load"
            return "save"
        if CURIOUS and "look" not in self.flags and hasattr(g, "sights_here"):
            self.flags.add("look")
            self.sight = self.pick_sight(g)
            if self.sight:
                return "look"
        if person.wounds >= 45:
            self.hand_log["rest"] += 1
            return "end"
        spend = None if NO_SPENDING else self.plan_spending(g)
        if spend:
            return spend
        # the locker: sell what is dearer here than it cost, buy what is cheap here
        goods = g.locker_goods_here()
        for good, units in list(person.locker.items()):
            paid = person.locker_cost.get(good, 0) / max(1, units)
            if good in goods and g.current_location.market[good] > paid * 1.15 and ("sold", good) not in self.flags:
                self.flags.add(("sold", good))
                self.hand.update({"buy or sell": "s", "which": good, "how many": str(units)})
                self.hand_log["locker sale"] += 1
                return "locker"
        if not person.locker and goods and person.money > 250 and "bought" not in self.flags:
            seen = getattr(g, "prices_seen", {})
            best = None
            for good in goods:
                here = g.current_location.market[good]
                dear = max([m.get(good, 0) for _, m in seen.values()] or [0])
                if dear > here * 1.3 and (best is None or dear / here > best[0]):
                    best = (dear / here, good, here)
            if best:
                units = min(cargo.LOCKER_UNITS, int((person.money - 150) // (best[2] * 1.1)))
                if units > 0:
                    self.flags.add("bought")
                    self.hand.update({"buy or sell": "b", "which": best[1], "how many": str(units)})
                    self.hand_log["locker buy"] += 1
                    return "locker"
        # a berth: the best pay for a duty the hand can do, somewhere new now and then
        offers = g.berths()
        if offers and "berth" not in self.flags:
            lead = self.lead_place(g) if LEADS else None

            def worth(o):
                skill = person.skill(o["duty"])
                new = 1.3 if o["to"] not in g.known_locations else 1.0
                named = 1.15 if o["who"] else 1.0
                follow = 2.0 if lead and o["to"] == lead else 1.0
                return o["wage"] / o["legs"] * (1 + 0.25 * skill) * new * named * follow
            pick = max(range(len(offers)), key=lambda i: worth(offers[i]))
            if rng.random() < 0.75:
                self.flags.add("berth")
                self.hand.update({"sign on (": str(pick + 1), "sign on?": "yes"})
                self.hand_log["voyage"] += 1
                self.hand_log["with " + (offers[pick]["who"] or offers[pick]["kind"])] += 1
                return "berths"
        shown, _ = g.work_options()
        jobs = [i for i, (kind, _, _) in enumerate(shown) if kind == "job"]
        if jobs:
            def wage(i):
                site, job = shown[i][1]
                return g.shift_wage(job[2], job[0], site["id"])
            pick = max(jobs, key=wage)
            self.hand.update({"work which": str(pick + 1)})
            self.hand_log["shift " + shown[pick][1][0]["id"]] += 1
            return "work"
        return "end"

    def plan_spending(self, g):
        """Money to spare buys skill: an implant at the clinic at Epsilon for the best skill whose
        implant costs no more than two fifths of the purse; else, now and then, a lesson with the
        master here when the purse holds ten times the lesson's price."""
        person = g.person
        ranked = sorted(cargo.SKILLS, key=lambda s: (-person.skill(s), cargo.SKILLS.index(s)))
        if g.current_location.name == "Epsilon" and "implant" not in self.flags and person.wounds <= 30:
            self.flags.add("implant")
            for skill in ranked:
                price, _, why = g.implant_offer(skill)
                if price is None:
                    continue
                if not why and person.money >= 2.5 * price:
                    import game.story as gs
                    sights = g.sights_here()
                    if "sight.epsilon.clinic" not in sights:
                        break
                    node = gs.story_data()["nodes"]["sight.epsilon.clinic"]
                    snap = g.story.snapshot()
                    offered = [c for c in node.get("choices") or [] if g.story.check(c.get("requires"), snap)]
                    pick = next(i for i, c in enumerate(offered) if c["id"] == "implants")
                    self.hand.update({"look at": str(sights.index("sight.epsilon.clinic") + 1),
                                      "your choice": str(pick + 1), "fit which": str(cargo.SKILLS.index(skill) + 1),
                                      "fit a": "yes"})
                    self.hand_log["implant " + skill] += 1
                    return "look"
        if "gear" not in self.flags:
            self.flags.add("gear")
            sold = list(g.outfitter_here())
            want = None
            for name, kind, purse in (("work suit", "armour", 400), ("knife", "melee", 300), ("rivet gun", "ranged", 1500),
                                      ("stunner", "ranged", 2000), ("vacuum suit", "armour", 4000),
                                      ("exoskeleton knees", "knees", 5000)):
                have = g.gear_best(kind)
                better = have is None or (kind == "armour" and cargo.GEAR[name]["soak"] > cargo.GEAR[have]["soak"])
                if name in sold and name not in person.gear and better and person.money >= purse:
                    want = name
                    break
            if want:
                self.hand.update({"buy which": str(sold.index(want) + 1)})
                self.hand_log["gear " + want] += 1
                return "gear"
        if "lesson" not in self.flags:
            self.flags.add("lesson")
            shown, _ = g.work_options()
            lessons = [(i, d) for i, (kind, d, _) in enumerate(shown) if kind == "lesson"]
            lessons.sort(key=lambda item: ranked.index(item[1][0]))
            for i, (skill, master, price, practice) in lessons:
                if person.money >= max(1500, 10 * price) and rng.random() < 0.5:
                    self.hand.update({"work which": str(i + 1)})
                    self.hand_log["lesson " + skill] += 1
                    return "work"
        return None

    def hand_answer(self, p, options):
        """Answers to the hand's own prompts, as hand_action planned them; None if not one."""
        g = self.game
        if g is None or g.ship is not None:
            return None
        if p.startswith("your call"):
            person = g.person
            bold = person.wounds < 30 and rng.random() < 0.35 + 0.1 * max(person.skills.values())
            return "1" if bold else "2"
        for key in list(self.hand):
            if p.startswith(key):
                answer = self.hand.pop(key)
                return answer if answer in options or not options else (options[0] if options else "")
        if p.startswith(("work which", "sign on", "book (", "buy or sell", "which?", "how many")):
            return ""
        return None

    ODDS = (("easy", 0.9), ("good odds", 0.7), ("even odds", 0.47), ("long odds", 0.25))

    def brawl_move(self, g, shown):
        """A round of a fight on foot: talk when it is likely, pay when hurt, run from killers
        when hurt, else the best blow."""
        odds = {}
        for key, label in shown:
            odds[key] = next((v for word, v in self.ODDS if "(" + word + ")" in label), None)
        person = g.person
        foe = cargo.FOES.get(getattr(g, "brawl_foe", None) or "", {})
        blows = [k for k in ("strike", "shoot", "grapple") if odds.get(k) is not None]
        best = max(blows, key=lambda k: (odds[k], k == "shoot"))
        self.hand_log["fight round"] += 1
        if "pay" in odds and person.wounds >= 50:
            return "pay"
        if odds.get("talk") and odds["talk"] >= 0.6:
            return "talk"
        if foe.get("lethal") and person.wounds >= 40 and (odds.get("run") or 0) >= 0.45:
            return "run"
        if odds[best] >= 0.45:
            return best
        if odds.get("talk") and odds["talk"] >= odds[best]:
            return "talk"
        if "pay" in odds:
            return "pay"
        if (odds.get("run") or 0) > odds[best]:
            return "run"
        return best

    def move(self, numbers):
        """Read the options on screen (game.move_options) and pick one like a sensible captain."""
        g = self.game
        shown = list(getattr(g, "move_options", None) or [])
        if not shown:
            return numbers[0] if numbers else ""
        keys = [k for k, _ in shown]
        if "strike" in keys:                                 # a fight on foot (Cargo 3)
            return str(keys.index(self.brawl_move(g, shown)) + 1)
        fighter = goal == "combat" or "combat_victories" in self.need()
        if "leave" in keys:                                  # the bounty board
            best = None
            for i, key in enumerate(keys):
                if key == "leave":
                    continue
                label = shown[i][1]
                if "easy" in label or "good odds" in label:
                    best = i                                 # the hardest target with good odds
            return str((best if best is not None and fighter else keys.index("leave")) + 1)
        if "focus" in keys:                                  # a round of a convoy fight (Cargo 2)
            ship = g.ship
            for key in ("drones", "board"):
                if key in keys:
                    return str(keys.index(key) + 1)
            if "counter" in keys and ship.damage > 30:
                return str(keys.index("counter") + 1)
            if ship.damage > 75 and not fighter:
                return str(keys.index("break") + 1)
            if "screen" in keys and any(w in shown[keys.index("screen")][1] for w in ("good odds", "easy")):
                return str(keys.index("screen") + 1)
            return str(keys.index("focus") + 1)
        if "fight" in keys:                                  # a fight
            found = re.search(r"threat (\d)", getattr(g, "move_title", "") or "")
            power = int(found.group(1)) if found else 3
            best_key, best_chance = "fight", g.fight_chance(power)
            for key in keys:
                if key.startswith("trick:"):
                    chance = g.fight_chance(power, cargo.FIGHT_TRICKS[key[6:]][1]["edge"])
                    if chance > best_chance:
                        best_key, best_chance = key, chance
                if key.startswith("ally:"):
                    chance = g.fight_chance(power, g.ALLIES[key[5:]][2])
                    if chance > best_chance:
                        best_key, best_chance = key, chance
            for key in ("mraz", "pilgrims", "lauritz"):          # an old favour ends it peacefully
                if key in keys and not fighter:
                    return str(keys.index(key) + 1)
            if best_chance >= (0.4 if fighter else 0.6):
                return str(keys.index(best_key) + 1)
            for key in ("slip", "warp", "scan", "holy", "feed", "tithe", "talk", "pay", "run"):
                if key in keys and not (key == "pay" and g.ship.money < 5000):
                    return str(keys.index(key) + 1)
            return str(keys.index(best_key) + 1)
        return random.choice(numbers) if numbers else ""      # a situation: whatever looks interesting

    def port_action(self):
        g = self.game
        ship = g.ship
        mods = getattr(ship, "passenger_modules", [])
        here = g.current_location.name
        if self.port_step == "start":
            if any(p.destination == here for m in mods for p in m.passengers):
                self.port_step = "unloaded"
                if self.pax_dest == here:
                    self.pax_dest = None
                return "u"
            self.port_step = "unloaded"
        if self.port_step == "unloaded":
            if sum(m.capacity for m in mods) < 6 and ship.money > 4000:
                self.port_step = "buy_module"
                return "m"
            self.port_step = "bought"
        if self.port_step == "bought":
            free = sum(m.capacity - len(m.passengers) for m in mods)
            aboard = sum(len(m.passengers) for m in mods)
            if free > 0 and aboard == 0 and g.port_system.waiting_passengers.get(here):
                self.port_step = "board"
                return "b"
            self.port_step = "done"
        return "back"


bot = Bot()
out = io.StringIO()
real = sys.stdout
sys.stdout = out


def fake_input(prompt=""):
    text = out.getvalue()
    tail = text[-600:]
    if len(text) > 200000:
        out.seek(0)
        out.truncate(0)
    g = bot.game
    write_trace(g)
    if g is not None:
        if g.turn >= max_turns:
            raise Done("max turns")
        if getattr(g, "ending_reached", None):
            raise Done("ending")
        if ledger_on:
            marks = bot.__dict__.setdefault("chapters_at", {})
            for chapter in g.story_manager.completed_chapters:
                if chapter not in marks:
                    marks[chapter] = {"turn": g.turn, "plot_points": g.story_manager.plot_points,
                                      "money": int(g.person.money)}
        prog = (g.turn, g.story_manager.current_chapter)
        if prog == bot.last_progress:
            bot.stall += 1
            if bot.stall > 400:
                raise Done("stalled: no turn passes (last prompt tail: %r)" % tail[-160:])
        else:
            bot.stall = 0
            bot.last_progress = prog
    a = bot.answer(tail)
    if verbose:
        real.write("turn %s ch %s $%s -> %r\n" % (g.turn if g else "-", g.story_manager.current_chapter if g else "-",
                                                 int(g.person.money) if g else "-", a))
    return a if a is not None else ""


builtins.input = fake_input
orig_vi = cargo.Game.validate_input
orig_vq = cargo.Game.validate_quantity_input


def vi(self, default_prompt, valid_options, prompt=None):
    bot.game = self
    bot.ctx = (prompt or default_prompt, valid_options)
    return orig_vi(self, default_prompt, valid_options, prompt)


def vq(self, prompt):
    bot.qty = prompt or True
    return orig_vq(self, prompt)


cargo.Game.validate_input = vi
cargo.Game.validate_quantity_input = vq

result = {"goal": goal, "seed": seed}
history = []
try:
    bot.ctx = None
    if CAPTAIN:
        from game import captain as captains
        record = {"format": "cargo-captain", "version": 1, "id": "BOT", "name": "Bot %s %d" % (goal, seed),
                  "rank": "Veteran", "origin": {"game": "cargo1", "version": "bot"},
                  "career": {"turns": 150}, "ship": {}, "hold": {}, "log": [],
                  "story": {"ending": CAPTAIN, "flags": ["hansa_founder", "convoy_friend", "pell_lent",
                                                          "lauritz_bribed", "took_the_commission"]}}
        record["check"] = captains._captain_check(record)
        record = captains.clean_captain(record)
        answers = iter([DIFFICULTY, VOYAGE])
        builtins.input = lambda prompt="": next(answers)
        game = cargo.Game(player_name=record["name"], origin=record)
        result["captain"] = CAPTAIN
    else:
        answers = iter([DIFFICULTY, VOYAGE, "Bot %s %d" % (goal, seed)])
        builtins.input = lambda prompt="": next(answers)
        game = cargo.Game()
    if AFLOAT and getattr(game, "ship", None) is None:
        game.give_ship()
        result["afloat"] = True
    builtins.input = fake_input
    bot.game = game
    while True:
        try:
            game.play()
            result["end"] = "game over (play returned)"
            break
        except cargo.SwitchGame as sw:
            game = sw.game
            bot.game = game
            bot.loads += 1
        except Done as d:
            result["end"] = str(d)
            # after a save, reload it and continue (exercises save/load mid-game)
            break
        except SystemExit:
            result["end"] = "exit"
            break
except Exception:
    result["traceback"] = traceback.format_exc()[-1800:]
finally:
    sys.stdout = real
    shutil.rmtree(home, ignore_errors=True)

g = bot.game
write_trace(g, final=True)
if trace_file:
    trace_file.close()
if g is not None and g.ship is None:          # still on foot (Cargo 3)
    sm = g.story_manager
    result.update({
        "turn": g.turn, "chapter": sm.current_chapter, "completed": sorted(sm.completed_chapters),
        "ending": getattr(g, "ending_reached", None), "money": int(g.person.money), "afloat": False,
        "plot_points": sm.plot_points, "wounds": g.person.wounds, "skills": dict(g.person.skills),
        "implants": dict(getattr(g.person, "implants", {})), "lessons": dict(getattr(g, "lessons", {})),
        "brawls": dict(getattr(g, "brawls", {}) or {}), "gear": list(g.person.gear),
        "ship_needs": [f for f in cargo.SHIP_NEEDS if sm.story_states.get(f)],
        "closing": [f for f in ("serac_offer", "serac_refused", "envoy_heard", "broker_card") if sm.story_states.get(f)],
        "voyages": getattr(g, "voyages", 0), "shifts": dict(getattr(g, "shifts", {})),
        "locker_profit": getattr(g, "locker_profit", 0), "regard": dict(getattr(g, "hand_regard", {})),
        "hand": dict(bot.hand_log), "known": len(g.known_locations), "here": g.current_location.name,
        "inputs": bot.inputs, "loads": bot.loads, "standing": dict(getattr(g, "standing", {}) or {}),
        "docks": {"places": dict(bot.docks["places"].most_common()), "together": dict(bot.docks["together"]),
                  "first": bot.docks["first"], "chapters": bot.docks["chapters"]},
        "unknown_prompts": [[list(map(str, k)), n] for k, n in bot.unknown.most_common(8)],
    })
elif g is not None:
    sm = g.story_manager
    result.update({
        "first_ship": bot.first_ship,
        "way": [f[4:] for f in ("way_serac", "way_envoy", "way_broker", "way_court", "way_night", "way_auction")
                if sm.story_states.get(f)],
        "chapters_at": bot.docks["chapters"],
        "turn": g.turn, "chapter": sm.current_chapter, "completed": sorted(sm.completed_chapters),
        "ending": getattr(g, "ending_reached", None), "money": int(g.person.money),
        "modules": ["%s %d" % (m["kind"], m["condition"]) for m in getattr(g.ship, "modules", [])],
        "difficulty": getattr(g, "difficulty", None), "wins": g.ship.combat_victories.get("total", 0),
        "losses": g.ship.combat_defeats.get("total", 0),
        "plot_points": sm.plot_points, "trades": g.trades_completed,
        "victories": g.ship.combat_victories.get("total"), "defeats": g.ship.combat_defeats.get("total"),
        "rating": g.ship.attack + g.ship.defense + g.ship.speed, "damage": g.ship.damage,
        "rp": g.person.research_points, "research": sorted(g.research.unlocked_options),
        "pax": g.reputation_manager.total_passengers, "pax_rep": g.ship.passenger_reputation,
        "trade_profit": int(sum(g.ship.trade_profits.values())),
        "stockmarkets": sum(1 for l in g.locations for b in l.buildings if b == "stockmarket"),
        "locations": len(g.locations), "known": len(g.known_locations),
        "open_requirements": {k: (v if not callable(v) else "fn") for k, v in bot.need().items()} if not result.get("traceback") else None,
        "inputs": bot.inputs, "loads": bot.loads,
        "standing": dict(getattr(g, "standing", {}) or {}),
        "story_needs": {c: [w for _, w in sm.chapter_needs(sm.chapters[c])] for c in PATH_CHOICE
                        if c in sm.chapters and c not in sm.completed_chapters} if hasattr(sm, "chapter_needs") else None,
        "docks": {"places": dict(bot.docks["places"].most_common()), "together": dict(bot.docks["together"]),
                  "first": bot.docks["first"], "flags": bot.docks["flags"],
                  "leads": dict(bot.docks["leads"]), "lead_first": bot.docks["lead_first"],
                  "unlocked": bot.docks["unlocked"], "chapters": bot.docks["chapters"],
                  "lead_from": dict(bot.docks["lead_from"])},
        "discovered": sorted(g.discovered_locations), "all_locations": [(l.name, l.location_type) for l in g.locations],
        "here": g.current_location.name, "travel_to": getattr(bot, "travel_to", None),
        "active_quests": [q.name for q in g.quest_system.active_quests][:8],
        "unknown_prompts": [[list(map(str, k)), n] for k, n in bot.unknown.most_common(8)],
    })
    if ledger_on:
        result["ledger"] = {book: {k: round(v) for k, v in sorted(entries.items(), key=lambda kv: -abs(kv[1]))}
                            for book, entries in LEDGER.items()}
        result["chapters_at"] = getattr(bot, "chapters_at", {})
print(json.dumps(result, ensure_ascii=False, default=str))
