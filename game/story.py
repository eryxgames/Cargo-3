"""The story as data: storykit nodes read from story/, played by StoryRuntime; story hooks, sound
cues, voyage length."""
import json
import os
import random
import re

# =============================================================================
# The story, as data.  The scenes, characters and places live in the storykit
# files under story/ and are written into this file by tools/build_story.py,
# between the two marker lines below.  Edit the story files, not the block.
# CARGO_STORY=path/to/built.json plays a story file instead (for writers).
# =============================================================================

# --- story data ---
# Cargo 3 reads its story from story/cargo3.game.json next to the game (built from
# story/cargo3.story.json and the storykit files in story/cargo3/). CARGO_STORY=path plays another file.
STORY_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "story", "cargo3.game.json")
with open(STORY_FILE, encoding="utf-8") as _story_file:
    STORY_JSON = _story_file.read()
# --- end of story data ---

_STORY = None
_STORY_ITEMS = None
_STORY_LINKS = None
STORY_MOMENTS = {}      # id(game) -> (snapshot, verdicts) of the runtime's last look; not saved


def story_data():
    """The built story: nodes, characters, flags, places (loaded once)."""
    global _STORY
    if _STORY is None:
        data = None
        path = os.environ.get("CARGO_STORY")
        if path:
            try:
                with open(path, encoding="utf-8") as handle:
                    data = json.load(handle)
            except (OSError, ValueError):
                data = None
        if not isinstance(data, dict) or "nodes" not in data:
            data = json.loads(STORY_JSON)
        for key in ("nodes", "characters", "flags", "places", "repaired", "order", "errands", "aliases", "features"):
            data.setdefault(key, [] if key in ("repaired", "order") else {})
        if not data["order"]:
            data["order"] = list(data["nodes"])
        _STORY = data
    return _STORY


def story_items():
    """Items the story gives (a pass, a reader, a loader's hand): keepsakes and keys, not
    equipment, so nothing breaks them or takes them except the story itself."""
    global _STORY_ITEMS
    if _STORY_ITEMS is None:
        found = set()
        for node in story_data()["nodes"].values():
            for effects in [node.get("effects") or {}] + [c.get("effects") or {} for c in node.get("choices") or []]:
                found.update(_as_list(((effects or {}).get("give") or {}).get("items")))
        _STORY_ITEMS = found
    return _STORY_ITEMS


def story_links():
    """(after, chosen): node -> the nodes it leads to through 'next', and the
    nodes reached only through a choice (those wait for that choice)."""
    global _STORY_LINKS
    if _STORY_LINKS is None:
        after, by_choice = {}, set()
        for nid, node in story_data()["nodes"].items():
            for target in _as_list(node.get("next")):
                after.setdefault(target, set()).add(nid)
            for choice in node.get("choices") or []:
                by_choice.update(_as_list(choice.get("next")))
        _STORY_LINKS = (after, by_choice - set(after))
    return _STORY_LINKS


def _as_list(value):
    if value is None:
        return []
    return list(value) if isinstance(value, (list, tuple, set)) else [value]


def record_matches(record, want, player=None):
    """Does a captain record match {"game", "ending", "flag", "same_name"}?"""
    if not isinstance(record, dict) or not isinstance(want, dict):
        return False
    if want.get("game") and record.get("origin", {}).get("game") != want["game"]:
        return False
    if "same_name" in want:
        same = player is not None and str(record.get("name", "")).strip().lower() == str(player).strip().lower()
        if same != bool(want["same_name"]):
            return False
    story = record.get("story", {})
    if want.get("ending") and story.get("ending") != want["ending"]:
        return False
    if want.get("flag") and want["flag"] not in story.get("flags", []):
        return False
    return True


GAME_TITLES = {"cargo1": "Cargo", "cargo2": "Cargo 2", "cargo3": "Cargo 3"}
ENDING_TITLES = {"trade": "the Hauler Hansa", "combat": "the First Legion", "discovery": "the Heading",
                 "tycoon": "Galactic Tycoon", "": "no ending yet"}
GAME_ENDING_TITLES = {"cargo2": {"trade": "the Open Road", "combat": "the Lighthouse", "discovery": "the Door",
                                 "dawn": "the Quiet Node"}}


def ending_title(record):
    """How a captain record's ending is called, in the part it comes from."""
    ending = (record or {}).get("story", {}).get("ending", "")
    game = (record or {}).get("origin", {}).get("game")
    return GAME_ENDING_TITLES.get(game, {}).get(ending) or ENDING_TITLES.get(ending, ending)
_PLACEHOLDER = re.compile(r"\{([a-z_][a-z0-9_]*)(?:\.([a-z_]+))?\}")


class StoryRuntime:
    """Plays the story's scenes: checks conditions, shows text, offers choices,
    applies effects.  Chapters and endings are still run by the StoryManager;
    this plays everything else and supplies the text for both."""

    PLAYS = ("event", "encounter", "quest", "beat", "stage")
    MOST_PER_MOMENT = 2

    def __init__(self, game):
        self.game = game
        self.done = {}          # node id -> turn it happened
        self.due = {}           # node id -> earliest turn (it follows a node shown earlier)
        self.shown = {}         # repeating node id -> last turn shown
        self.met = []           # characters met, in order
        self.moment = None      # (turn, place) last looked at
        self.origin = None      # the captain record the player is playing as, if any
        self.venue = None

    # -- state -----------------------------------------------------------------
    def snapshot(self):
        snap = self.game.story_snapshot()
        snap["venue"] = self.venue
        snap["origin"] = self.origin
        snap["past"] = self.game.captain_start["ledger"]           # what the captain left in other parts
        snap["errands"] = history.errand_states(self.game.errands)
        return snap

    def mark(self, nid):
        """The game tells the story that something it runs has happened."""
        if nid not in self.done:
            self.done[nid] = self.game.turn
            self._queue_followers(nid)

    def _queue_followers(self, nid):
        node = story_data()["nodes"].get(nid) or {}
        for target in _as_list(node.get("next")):
            if not node.get("choose"):
                self.due.setdefault(target, self.game.turn + 1)

    # -- conditions --------------------------------------------------------------
    def where_is(self, who, turn=None):
        """Where a character's route has them on a turn (this one by default); None without a route."""
        route = (story_data()["characters"].get(who) or {}).get("route")
        return route_place(route, self.game.turn if turn is None else turn)

    def check(self, cond, snap, found=None):
        if not cond:
            return True
        if isinstance(cond, list):
            return all(self.check(c, snap, found) for c in cond)
        for key, want in cond.items():
            if not self._holds(key, want, snap, found):
                return False
        return True

    def _holds(self, key, want, snap, found):
        if key.startswith("_"):
            return True
        if key == "all":
            return all(self.check(c, snap, found) for c in want)
        if key == "any":
            return any(self.check(c, snap, found) for c in want)
        if key == "not":
            return not self.check(want, snap)
        if key == "flag":
            return all(f in snap["flags"] for f in _as_list(want))
        if key == "not_flag":
            return not any(f in snap["flags"] for f in _as_list(want))
        if key == "done":
            return all(n in snap["done"] for n in _as_list(want))
        if key == "done_any":
            return any(n in snap["done"] for n in _as_list(want))
        if key == "not_done":
            return not any(n in snap["done"] for n in _as_list(want))
        if key == "since":
            at = snap.get("done_at", {})
            return all(n in snap["done"] and snap["turn"] - at.get(n, -10 ** 9) >= turns for n, turns in want.items())
        if key in ("act_min", "act_max", "turn_min", "turn_max"):
            value = snap["act"] if key.startswith("act") else snap["turn"]
            return value >= want if key.endswith("min") else value <= want
        if key == "at":
            return snap["place"] in _as_list(want)
        if key == "at_type":
            return snap["place_type"] in _as_list(want)
        if key == "venue":
            return snap.get("venue") in _as_list(want)
        if key == "here":
            return any(self.where_is(who, snap["turn"]) == snap["place"] for who in _as_list(want))
        if key == "chapter":
            return snap.get("chapter") in _as_list(want)
        if key == "has":
            return all(set(_as_list(items)) <= set(snap["sets"].get(name, [])) for name, items in want.items())
        if key == "visiting_captain":
            for record in snap["visitors"]:
                if record_matches(record, want, snap["player"]):
                    if found is not None:
                        found.setdefault("visitor", record)
                    return True
            return False
        if key == "player_origin":
            return snap.get("origin") is not None and record_matches(snap["origin"], want)
        if key == "past":
            return history.past_holds(snap.get("past"), want)
        if key == "errand":
            return history.errands_hold(snap.get("errands"), want)
        if key == "code":
            return False            # the story should not lean on code the game cannot read
        value = snap["stats"].get(key, 0)
        if isinstance(want, dict):
            return want.get("min", value) <= value <= want.get("max", value)
        return value >= want

    def requires_of(self, node):
        """A node's condition; the main story's (chapters, milestones, endings, the drama arc)
        scaled to the voyage."""
        cond = node.get("requires")
        if node.get("kind") in ("chapter", "milestone", "ending") or node.get("arc") == "drama":
            return voyage_condition(cond, self.game.voyage_factor())
        return cond

    def condition_for(self, nid):
        """A repaired condition the game should use instead of its own, or None."""
        data = story_data()
        if nid in data["repaired"]:
            return data["nodes"][nid].get("requires") or {}
        return None

    # -- text ---------------------------------------------------------------------
    def fill(self, text, found=None):
        game = self.game
        chars = story_data()["characters"]
        visitor = (found or {}).get("visitor") or {}
        origin = self.origin or {}
        values = {
            "player_name": game.player_name, "rank": game.rank,
            "money": game.format_money(game.person.money),
            "trades_completed": game.trades_completed,
            "combat_victories": game.ship.combat_victories.get("total", 0) if game.ship is not None else 0,
            "research_points": game.person.research_points,
            "discoveries": len(game.discovered_locations),
            "place": game.current_location.name, "turn": game.turn,
            "ship_name": getattr(game.ship, "name", None) or "your ship",
            "labour_news": game.labour_news_line(),
        }
        records = {"visitor": visitor, "origin": origin}

        def swap(match):
            head, field = match.group(1), match.group(2)
            if head in records:
                record = records[head] or {}
                info = {"name": record.get("name", ""), "rank": record.get("rank", "") or "captain",
                        "game": GAME_TITLES.get(record.get("origin", {}).get("game"), "another part"),
                        "ending": ending_title(record),
                        "turns": record.get("career", {}).get("turns", 0)}
                return str(info.get(field or "name", match.group(0)))
            if head in chars and (field is None or field in chars[head]):
                return str(chars[head].get(field or "name", ""))
            if field is None and head in values:
                return str(values[head])
            return match.group(0)

        return _PLACEHOLDER.sub(swap, str(text))

    def text_of(self, nid, snap=None, fallback=None, found=None):
        """The lines of a node, its first matching variant first; placeholders filled."""
        node = story_data()["nodes"].get(nid)
        if not node:
            return list(_as_list(fallback))
        text = node.get("text")
        if node.get("variants"):
            snap = snap or self.snapshot()
            for variant in node["variants"]:
                trial = {}
                if variant.get("requires") and self.check(variant["requires"], snap, trial):
                    text = variant.get("text")
                    found = dict(found or {}, **trial)
                    break
        lines = _as_list(text) or _as_list(fallback)
        return [self.fill(line, found) for line in lines if line]

    def title_of(self, nid, fallback=""):
        node = story_data()["nodes"].get(nid) or {}
        return self.fill(node.get("title") or fallback)

    # -- playing ----------------------------------------------------------------
    def playable(self, nid, node):
        if node.get("kind") not in self.PLAYS or node.get("handled_by") or node.get("status") == "unused":
            return False
        if nid in self.done:
            repeat = node.get("repeat")
            if not repeat:
                return False
            cooldown = repeat.get("cooldown", 1) if isinstance(repeat, dict) else 1
            if self.game.turn - self.shown.get(nid, -10 ** 6) < cooldown:
                return False
        after, by_choice = story_links()
        if nid in by_choice and nid not in self.due:
            return False                    # waits for the choice that leads here
        before = after.get(nid)
        if before and nid not in self.due and not any(b in self.done for b in before):
            return False
        if self.due.get(nid, 0) > self.game.turn:
            return False
        return True

    def tick(self):
        """Once per turn and place: play the scenes whose time has come."""
        moment = (self.game.turn, self.game.current_location.name)
        if moment == self.moment:
            return
        self.moment = moment
        self.play_ready()

    def play_ready(self, limit=None):
        data = story_data()
        snap = self.snapshot()
        ready = []
        verdicts = {}
        STORY_MOMENTS[id(self.game)] = (snap, verdicts)     # for tools: what was judged, on what
        for nid in data["order"]:
            node = data["nodes"][nid]
            if not self.playable(nid, node):
                continue
            ok = self.check(self.requires_of(node), snap)
            verdicts[nid] = ok
            if not ok:
                continue
            chance = node.get("chance")
            if chance and nid not in self.due and random.random() >= chance:
                continue
            ready.append(nid)
        ready.sort(key=lambda n: (n not in self.due, bool(data["nodes"][n].get("chance"))))
        for nid in ready[:limit or self.MOST_PER_MOMENT]:
            self.play(nid)

    def play(self, nid, snap=None):
        data = story_data()
        node = data["nodes"][nid]
        snap = snap or self.snapshot()
        found = {}
        self.check(self.requires_of(node), snap, found)
        lines = self.text_of(nid, snap, found=found)
        title = self.title_of(nid)
        for who in _as_list(node.get("who")):
            if who not in self.met:
                self.met.append(who)
        self.cue(node.get("sound"))
        box = [title] if title else []
        for line in lines:
            box.extend([""] + self.game.word_wrap(line))
        choices = [c for c in node.get("choices") or [] if self.check(c.get("requires"), snap)]
        self.done[nid] = self.game.turn
        self.shown[nid] = self.game.turn
        self.due.pop(nid, None)
        self.apply(node.get("effects"))
        if not choices:
            if box:
                self.game.display_story_message(box, pause=1)
            self._queue_followers(nid)
            return None
        for number, choice in enumerate(choices, 1):
            box.extend([""] if number == 1 else [])
            box.extend(self.game.option_lines(number, self.fill(choice.get("say", choice.get("id", "")))))
        self.game.display_story_message(box, pause=0)
        self.offered = choices              # what a reader of the screen sees (tools/bot.py)
        self.offered_at = nid
        picked = self.ask(len(choices))
        self.offered = self.offered_at = None
        choice = choices[picked]
        self.done["%s:%s" % (nid, choice.get("id", picked))] = self.game.turn
        self.apply(choice.get("effects"))
        for target in _as_list(choice.get("next")):
            self.due[target] = self.game.turn
            target_node = data["nodes"].get(target)
            if target_node and self.check(target_node.get("requires"), self.snapshot()):
                self.play(target)
        self._queue_followers(nid)
        return choice.get("id")

    def ask(self, count):
        options = [str(i) for i in range(1, count + 1)]
        answer = self.game.validate_input("Your choice (1-%d, Enter = %d): " % (count, count), options)
        return int(answer) - 1 if answer else count - 1     # Enter: the last option, usually "leave it"

    # -- effects -----------------------------------------------------------------
    def apply(self, effects):
        """Do what a story node does. Money, items and research are the captain's; what only a
        ship can take (crew, cargo, passenger reputation, guns) waits for nobody when there is
        no ship: it is noted in `shipless` for the checks, and nothing happens."""
        game = self.game
        person = game.person
        for key, value in (effects or {}).items():
            ship = game.ship                # a 'ship' code earlier in these effects gives one
            if ship is None and (key in SHIP_EFFECTS or key.startswith("cargo.") or (
                    key == "give" and isinstance(value, dict) and "crew" in value)):
                self.note_shipless(key)
                if key != "give":
                    continue
                value = {k: v for k, v in value.items() if k != "crew"}
            if key == "errand":           # an errand for another part of the saga
                for eid in _as_list(value):
                    history.open_errand(game.errands, eid, story_data()["errands"], GAME_ID, game.captain_start["line"])
            elif key == "errand_done":
                for eid in _as_list(value):
                    history.finish_errand(game.errands, eid, story_data()["errands"], GAME_ID,
                                          game.captain_start["line"])
            elif key == "set":
                for flag in _as_list(value):
                    game.story_manager.story_states[flag] = True
            elif key == "clear":
                for flag in _as_list(value):
                    game.story_manager.story_states[flag] = False
            elif key == "give":
                for name, members in value.items():
                    for member in _as_list(members):
                        if name == "items":
                            held = person.items.get(member, 0)
                            person.items[member] = (held if isinstance(held, int) else 0) + 1
                        elif name == "researched":
                            game.research.unlocked_options.add(member)
                        elif name == "unlocked_types":
                            game.unlock_location_type(member)
                        elif name == "crew":
                            if member not in ship.crew:
                                ship.crew.append(member)
            elif key == "start":
                for target in _as_list(value):
                    self.due[target] = game.turn
            elif key == "reveal":
                for name in _as_list(value):
                    game.reveal_place(name)
            elif key == "code":
                story_hook(game, value)
            elif key == "money":
                person.money += value
            elif key == "plot_points":
                game.story_manager.plot_points += value
            elif key == "research_points":
                person.research_points += value
            elif key == "passenger_reputation":
                ship.passenger_reputation += value
            elif key == "passengers_transported":
                game.reputation_manager.total_passengers += value
            elif key == "combat_rating":
                ship.attack = max(1, ship.attack + value)
            elif key.startswith("skill.") and key[6:] in person.skills:
                person.skills[key[6:]] = max(0, min(SKILL_TOP, person.skills[key[6:]] + value))
                person.__dict__.setdefault("next_at", {}).pop(key[6:], None)   # a new level, a new draw
            elif key.startswith("labour.") and key[7:] in LABOUR_EVENTS:
                # something starts at this dock (game/labour.py), for so many turns
                if game.current_location is not None:
                    game.start_labour(key[7:], game.current_location.name, max(1, int(value)))
            elif key.startswith("practice.") and key[9:] in person.skills:
                # practice toward the next level, on the same curve as work (person.train)
                risen = person.train(key[9:], max(0, int(value)))
                if risen:
                    game.display_story_message(["%s: now %s." % (key[9:].capitalize(), skill_word(risen))], pause=0)
            elif key == "wounds":
                person.wounds = max(0, min(WOUNDS_DEAD, person.wounds + value))
            elif key.startswith("standing.") or key == "dawn_trust":
                game.change_standing("dawn" if key == "dawn_trust" else key[9:], value)
            elif key.startswith("cargo.") and key[6:] in ship.cargo:
                good = key[6:]
                ship.cargo[good] = max(0, ship.cargo[good] + (min(value, ship.hold_room(good)) if value > 0 else value))

    def note_shipless(self, what):
        """A story effect that needs a ship came while the captain has none (for the checks)."""
        noted = self.__dict__.setdefault("shipless", [])
        if what not in noted:
            noted.append(what)

    def cue(self, name):
        if name:
            play_cue(name)

    # -- moments the game calls in -------------------------------------------------
    def visit_venue(self, venue):
        """The captain walks into a port or a cantina."""
        self.venue = venue
        try:
            data = story_data()
            snap = self.snapshot()
            for nid in data["order"]:
                node = data["nodes"][nid]
                if "venue" not in json.dumps(node.get("requires") or {}):
                    continue
                if self.playable(nid, node) and self.check(self.requires_of(node), snap):
                    if not node.get("chance") or random.random() < node["chance"]:
                        self.play(nid)
                        break
            if venue == "cantina":
                self.tell_rumour(snap)
        finally:
            self.venue = None

    def tell_rumour(self, snap):
        data = story_data()
        fresh, heard = [], []
        for nid in data["order"]:
            node = data["nodes"][nid]
            if node.get("kind") == "rumour" and self.check(node.get("requires"), snap):
                (heard if nid in self.done else fresh).append(nid)
        story = [n for n in fresh if data["nodes"][n].get("arc") != "gossip"]
        pool = [n for n in story if data["nodes"][n].get("requires")] or \
            ([n for n in fresh if n not in story] if random.random() < 0.6 else story) or fresh or heard
        if pool:
            nid = random.choice(pool)
            self.done[nid] = self.game.turn
            self.game.display_story_message(["Overheard in the cantina", ""] + sum(
                (self.game.word_wrap(line) for line in self.text_of(nid, snap)), []), pause=1)

    def introduce(self):
        """The first scene of a new game: who this captain is and why they start here."""
        data = story_data()
        snap = self.snapshot()
        for nid in data["order"]:
            node = data["nodes"][nid]
            if node.get("kind") == "intro" and self.check(node.get("requires"), snap):
                self.play_as(nid, snap)
                return nid
        return None

    def play_as(self, nid, snap):
        node = story_data()["nodes"][nid]
        lines = self.text_of(nid, snap)
        box = [self.title_of(nid)] if node.get("title") else []
        for line in lines:
            box.extend([""] + self.game.word_wrap(line))
        self.cue(node.get("sound"))
        self.game.display_story_message(box, pause=2)
        self.done[nid] = self.game.turn
        self.apply(node.get("effects"))

    def epilogue(self):
        """After an ending: what became of the people the captain met."""
        data = story_data()
        snap = self.snapshot()
        lines = []
        for nid in data["order"]:
            node = data["nodes"][nid]
            if node.get("kind") == "epilogue" and self.check(node.get("requires"), snap):
                for line in self.text_of(nid, snap):
                    lines.extend([""] + self.game.word_wrap(line))
        if lines:
            self.game.display_story_message(["What became of them"] + lines[:60], pause=2)

    def journal(self):
        """The captain's log: people met, choices that will be remembered, places."""
        data = story_data()
        game = self.game
        chars = data["characters"]
        rows = [["Captain's log"], [""]]
        aboard = getattr(game.ship, "special_cargo", {}) if game.ship is not None else {}
        if aboard:
            labels = getattr(game.ship, "special_labels", {})
            rows.append(["Aboard"])
            rows.extend([["- %s (%d units of hold)" % (labels.get(name, name), units)] for name, units in aboard.items()])
            rows.append([""])
        rows.append(["Standing"])
        rows.extend(game.standing_rows())
        earned = game.achievement_rows()
        if earned:
            rows.extend([[""], ["Achievements"]] + earned)
        equipment = game.equipment_rows()
        if equipment:
            rows.extend([[""], ["Special equipment"]] + equipment)
        rows.extend([[""], ["People"]])
        people = [c for c in self.met if c in chars and not chars[c].get("generated")]
        for cid in people or []:
            info = chars[cid]
            rows.append(["- %s" % info.get("name", cid)])
        if not people:
            rows.append(["Nobody worth writing down yet."])
        rows.extend([[""], ["Remembered"]])
        states = game.story_manager.story_states
        notes = [info.get("about") for flag, info in data["flags"].items()
                 if states.get(flag) and info.get("carries_to") and info.get("about")]
        notes = [self.fill(note) for note in notes]
        rows.extend([["- " + note[0].upper() + note[1:]] for note in notes] or [["Nothing the future will ask about."]])
        rows.extend([[""], ["Places"]])
        for name in game.known_locations:
            place = data["places"].get(name, {})
            system = place.get("system")
            rows.append(["- %s%s" % (name, " (%s%s)" % (system, ", %s ly" % place["ly"] if place.get("ly") else "") if system else "")])
        print(game.create_box(rows, 'double', narrow='flow'))
        ask("Press Enter to continue...")


def play_cue(name):
    """A story sound: CLIo's synthesizer through game/sound.py (silent when it cannot play)."""
    sfx(name)


def _repair_at_cost(game):
    if game.ship is None:
        game.story.note_shipless("hull repaired at cost")
        return
    cost = int(game.ship.damage * game.ship.repair_rate() * 2)
    if game.ship.damage and game.person.money >= cost:
        game.person.money -= cost
        game.ship.damage = 0
        game.display_simple_message("Hull repaired for %s credits." % game.format_money(cost))


def _open_portal(game):
    game.open_portal()


# what only a ship can take: story effects, and the first word of story hooks ('crew joins' and
# 'crew leaves' too). Without a ship they do nothing (StoryRuntime.note_shipless).
SHIP_EFFECTS = ("passenger_reputation", "combat_rating")
SHIP_HOOKS = ("fight", "stow", "unstow", "damage", "repair")

STORY_HOOKS = {
    "hull repaired at cost": _repair_at_cost,
    "portal": _open_portal,
    "implants": lambda game: game.implant_clinic(),     # the cybersurgeon's catalogue (game/training.py)
}


def story_hook(game, value):
    """Game code a story effect names: a hook above, or one of these phrases:
    'fight <enemy>' (no paying or talking your way out), 'fight <enemy> edge <n>' (with allies),
    'brawl <foe>' and 'brawl <foe> edge <n>' (a fight on foot, game/brawl.py), 'ship <hull>' (the
    captain has a ship again, named Nameless), 'rename <words>' (the ship's name; {ship_name}),
    'crew joins <role>', 'repair <points>', 'damage <points>', 'lose money <share> min <amount>',
    'stow <units> <name> as <words>' (special cargo takes hold room until 'unstow <name>'; the
    words name it on screen and in the journal), 'profit <credits>' (paid, and counted as trade profit),
    'lose research <share>', 'buy bonds <n>', 'give bonds <n>' (free), 'sell bonds', 'crew leaves <role>',
    'dues hike <factor>' (for thirty turns), 'squeeze <good> <factor>' (prices of a good fall at
    every known dock, then recover like any market), 'front berths <n>' (the next n places at the
    front of a needle cost the middle's fare), 'take <item>' (an item the story gave leaves the ship)."""
    if isinstance(value, list):
        for one in value:
            story_hook(game, one)
        return None
    hook = STORY_HOOKS.get(value)
    if hook:
        return hook(game)
    words = str(value).split()
    ship = game.ship
    person = game.person
    if ship is None and words and (words[0] in SHIP_HOOKS or words[:2] in (["crew", "joins"], ["crew", "leaves"])):
        game.story.note_shipless(" ".join(words[:2]))
        return None
    if len(words) == 2 and words[0] == "ship" and words[1].isdigit():
        # a ship again (chapter III, story/cargo3/ship.json): from the next turn the turn is a captain's
        if ship is None:
            game.give_ship(hull=int(words[1]), name="Nameless")
        return None
    if len(words) >= 2 and words[0] == "rename":
        if ship is not None:
            ship.name = " ".join(words[1:])
        return None
    if len(words) in (2, 4) and words[0] == "brawl" and words[1] in FOES:
        # a fight on foot (game/brawl.py); it sets fight_<outcome>_<foe> for the story
        game.brawl(words[1], edge=int(words[3]) if len(words) == 4 and words[2] == "edge" else 0)
        return None
    if len(words) in (2, 4) and words[0] == "fight" and words[1] in ENEMIES:
        help_ = int(words[3]) if len(words) == 4 and words[2] == "edge" else 0
        outcome = game.encounter(words[1], hunted=True, edge=help_)
        # the story remembers how a fight it started went: fight_won_<enemy> / fight_lost_<enemy>
        won = outcome == "victory"
        game.story_manager.story_states["fight_%s_%s" % ("won" if won else "lost", words[1])] = True
    elif words[:2] == ["lose", "money"]:
        share = float(words[2])
        floor_ = int(words[4]) if len(words) > 4 and words[3] == "min" else 0
        loss = min(int(person.money), max(floor_, int(person.money * share)))
        person.money -= loss
        game.display_simple_message("It costs you %s." % game.format_money(loss), 2, color='31')
    elif words[:2] == ["lose", "research"]:
        loss = int(person.research_points * float(words[2]))
        person.research_points -= loss
        game.display_simple_message("%d research points are gone with the logs." % loss, 2, color='31')
    elif words[:2] == ["buy", "bonds"]:
        game.buy_bonds(int(words[2]))
    elif words[:2] == ["give", "bonds"] and len(words) == 3:
        game.hansa_bonds = getattr(game, "hansa_bonds", 0) + int(words[2])
        game.display_simple_message("The Hansa gives you %s bond%s: needle fares are %d%% lower." % (
            words[2], "" if words[2] == "1" else "s", round(100 * (1 - 0.88 ** game.hansa_bonds))), 2, color='32')
    elif words[:2] == ["sell", "bonds"]:
        held, value_ = game.sell_bonds()
        game.display_simple_message("The Hansa buys back %d bond%s for %s. Your dues go back up." % (
            held, "" if held == 1 else "s", game.format_money(value_)), 2)
    elif words[:2] == ["crew", "joins"]:
        if words[2] not in ship.crew:
            ship.crew.append(words[2])
            game.display_simple_message("%s is back aboard." % game.crew_name(words[2]), 2, color='32')
    elif words[0] == "stow" and len(words) >= 3:
        if not hasattr(ship, "special_cargo"):
            ship.special_cargo, ship.special_labels = {}, {}
        labels = ship.__dict__.setdefault("special_labels", {})
        ship.special_cargo[words[2]] = int(words[1])
        if len(words) > 4 and words[3] == "as":
            labels[words[2]] = " ".join(words[4:])
        game.display_simple_message("Loaded: %s (%s units of hold)."
                                    % (labels.get(words[2], words[2]), words[1]), 2)
    elif words[0] == "unstow" and len(words) == 2:
        units = getattr(ship, "special_cargo", {}).pop(words[1], None)
        if units is not None:
            label = getattr(ship, "special_labels", {}).pop(words[1], words[1])
            game.display_simple_message("Unloaded: %s (%d units of hold free again)." % (label, units), 2)
    elif words[0] == "take" and len(words) == 2:
        if isinstance(person.items.get(words[1]), int) and person.items[words[1]] > 1:
            person.items[words[1]] -= 1
        else:
            person.items.pop(words[1], None)
    elif words[:2] == ["front", "berths"] and len(words) == 3:
        game.front_berths = getattr(game, "front_berths", 0) + int(words[2])
        game.display_simple_message("The needle office owes you %d berth%s at the front, at the middle's fare."
                                    % (game.front_berths, "" if game.front_berths == 1 else "s"), 2, color='32')
    elif words[0] == "profit" and len(words) == 2 and ship is None:   # pay, with no ship to count it
        person.money += int(words[1])
        game.display_simple_message("Paid: %s credits." % format(int(words[1]), ","), 2)
    elif words[0] == "profit" and len(words) == 2:      # contract pay that counts as trade profit
        person.money += int(words[1])
        ship.trade_profits["contracts"] = ship.trade_profits.get("contracts", 0) + int(words[1])
        game.display_simple_message("Contract paid: %s credits (counts as trade profit)." % format(int(words[1]), ","), 2)
    elif words[0] == "damage" and len(words) == 2:
        ship.damage = min(99, ship.damage + int(words[1]))
        game.display_simple_message("Hull damage +%s%%." % words[1], 2, color='31')
    elif words[0] == "repair" and len(words) == 2:
        fixed = min(ship.damage, int(words[1]))
        ship.damage -= fixed
        if fixed:
            game.display_simple_message("Hull repaired by %d%%, free of charge." % fixed, 2, color='32')
    elif words[:2] == ["crew", "leaves"] and words[2] in ship.crew:
        ship.crew.remove(words[2])
        game.display_simple_message("%s packs a bag and leaves the ship." % game.crew_name(words[2]), 2, color='31')
    elif words[:2] == ["dues", "hike"]:          # for the next thirty turns
        game.dues_hike = float(words[2])
        game.dues_hike_until = game.turn + 30
    elif words[0] == "squeeze" and len(words) == 3:
        for loc in game.locations:
            if loc.name in game.known_locations and loc.market.get(words[1], 0) > 0:
                loc.market[words[1]] = round(loc.market[words[1]] * float(words[2]), 1)


# How long a voyage is: what the main story's chapters, milestones and climaxes ask for
# (plot points, trade profit, trades, victories, research, passengers), times this
VOYAGES = {"short": 0.6, "standard": 1.0, "long": 1.5}
VOYAGE_STATS = ("plot_points", "trade_profit", "trades_completed", "combat_victories", "research_points",
                "passengers_transported")


def voyage_value(key, value, factor):
    """A requirement as it stands on this voyage."""
    if factor == 1.0 or not (key in VOYAGE_STATS or key.startswith("combat_victories.")):
        return value
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return int(round(value * factor))
    if isinstance(value, dict):
        return {k: voyage_value(key, v, factor) if k in ("min", "max") or key == "combat_victories" else v
                for k, v in value.items()}
    return value


def voyage_condition(cond, factor):
    """A story condition with its main-story thresholds scaled to the voyage."""
    if factor == 1.0 or not cond:
        return cond
    if isinstance(cond, list):
        return [voyage_condition(c, factor) for c in cond]
    out = {}
    for key, want in cond.items():
        if key in ("all", "any"):
            out[key] = [voyage_condition(c, factor) for c in want]
        elif key == "not":
            out[key] = voyage_condition(want, factor)
        else:
            out[key] = voyage_value(key, want, factor)
    return out


# The game's other modules, imported last so that the modules can refer to each other.
from .encounters import ENEMIES  # noqa: E402
from . import record as history  # noqa: E402
from .saves import GAME_ID  # noqa: E402
from .sound import sfx  # noqa: E402


def route_place(route, turn):
    """Where a route puts a character on a turn: places[((turn + start) // stay) % len(places)]
    (as storykit/story.py computes it)."""
    places = (route or {}).get("places") or []
    if not places:
        return None
    stay = max(1, int(route.get("stay", 1)))
    return places[((turn + int(route.get("start", 0))) // stay) % len(places)]
from .person import SKILL_TOP, WOUNDS_DEAD, skill_word  # noqa: E402
from .brawl import FOES  # noqa: E402
from .labour import LABOUR_EVENTS  # noqa: E402
from .terminal import ask  # noqa: E402
