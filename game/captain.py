"""The captain's record: what a captain carries between the parts of the trilogy, checked and
cleaned."""
import base64
import hashlib
import json
import os
import time
import zlib
from . import VERSION

# =============================================================================
# The captain's record: a small file (or a line of text) that carries a captain
# from one part of the Cargo trilogy into another.
# =============================================================================

CAPTAIN_FORMAT = 1
CAPTAIN_CODE_PREFIX = "CARGO:"

# The words the story's conditions are written in (see story/cargo1.story.json)
STORY_PLACE_TYPES = ["Planet", "AsteroidBase", "DeepSpaceOutpost", "ResearchColony"]
STORY_BUILDINGS = ["stockmarket", "Neuroengineering Guild", "Agrobot Assembly Line", "mining_platform"]
STORY_VICTORY_TYPES = ["total", "pirate", "militia", "raider", "machine", "rogue_captain", "uprising"]
CAPTAIN_GAMES = ("cargo1", "cargo2", "cargo3")


def _captain_check(record):
    body = {k: v for k, v in record.items() if k != "check"}
    blob = json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]


def _clean_text(value, limit=40):
    text = _ANSI_RE.sub("", str(value))
    text = "".join(ch for ch in text if ch.isprintable())
    return text[:limit]


def _clean_number(value, low=0, high=10 ** 12):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value:
        return low
    return max(low, min(high, int(value)))


def clean_captain(record):
    """Check a captain record from outside and return a tidy copy.

    The record may come from another game, another machine or a text message,
    so nothing in it is trusted: unknown keys are dropped, texts are shortened,
    numbers are clamped.  Raises SaveError when it is not a captain record.
    """
    if not isinstance(record, dict) or record.get("format") != "cargo-captain":
        raise SaveError("this is not a captain record")
    if _clean_number(record.get("version"), 0, 10 ** 6) > CAPTAIN_FORMAT:
        raise SaveError("this captain record was made by a newer game")
    if record.get("check") != _captain_check(record):
        raise SaveError("the captain record is damaged (checksum does not match)")
    origin = record.get("origin") if isinstance(record.get("origin"), dict) else {}
    game = _clean_text(origin.get("game"), 12)
    if game not in CAPTAIN_GAMES:
        raise SaveError("the captain record comes from an unknown game")
    career = record.get("career") if isinstance(record.get("career"), dict) else {}
    story = record.get("story") if isinstance(record.get("story"), dict) else {}
    ship = record.get("ship") if isinstance(record.get("ship"), dict) else {}
    hold = record.get("hold") if isinstance(record.get("hold"), dict) else {}
    log = record.get("log") if isinstance(record.get("log"), list) else []
    standing = record.get("standing") if isinstance(record.get("standing"), dict) else {}

    def texts(values, limit=24, most=40):
        if not isinstance(values, (list, tuple)):
            return []
        return [_clean_text(v, limit) for v in list(values)[:most]]

    clean = {
        "format": "cargo-captain",
        "version": CAPTAIN_FORMAT,
        "id": _clean_text(record.get("id"), 16),
        "name": _clean_text(record.get("name"), 40) or "Captain",
        "origin": {"game": game, "version": _clean_text(origin.get("version"), 16)},
        "rank": _clean_text(record.get("rank"), 24),
        "career": {key: _clean_number(career.get(key)) for key in
                   ("turns", "money", "trades", "victories", "passengers", "reputation",
                    "locations", "research_points")},
        "research": texts(record.get("research")),
        "ship": {key: _clean_number(ship.get(key), 0, 10 ** 6) for key in ("attack", "defense", "speed")},
        "story": {
            "chapter": _clean_text(story.get("chapter"), 24),
            "completed": texts(story.get("completed")),
            "ending": _clean_text(story.get("ending"), 24),
            "flags": texts(story.get("flags"), limit=32, most=160),
            "plot_points": _clean_number(story.get("plot_points"), 0, 10 ** 6),
        },
        "hold": {_clean_text(k, 24): _clean_number(v, 0, 999) for k, v in list(hold.items())[:40]},
        # Cargo 2 adds these; a record from Cargo 1 has none, and Cargo 1 drops them on reading
        "achievements": texts(record.get("achievements"), limit=32, most=60),
        "standing": {key: _clean_number(standing.get(key, 0), -100, 100) if isinstance(standing.get(key, 0), (int, float))
                     and not isinstance(standing.get(key), bool) else 0 for key in ("hansa", "mandate", "concord")},
        "log": [{"game": _clean_text(e.get("game"), 12), "event": _clean_text(e.get("event"), 24),
                 "turn": _clean_number(e.get("turn"), 0, 10 ** 9), "at": _clean_text(e.get("at"), 24)}
                for e in log[-20:] if isinstance(e, dict)],
    }
    clean["check"] = _captain_check(clean)
    return clean


def captain_to_code(record):
    """The record as one line of text that can be copied anywhere."""
    blob = json.dumps(record, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return CAPTAIN_CODE_PREFIX + base64.urlsafe_b64encode(zlib.compress(blob, 9)).decode("ascii").rstrip("=")


def captain_from_code(text):
    text = "".join(str(text).split())
    if text.upper().startswith(CAPTAIN_CODE_PREFIX):
        text = text[len(CAPTAIN_CODE_PREFIX):]
    try:
        raw = base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))
        blob = zlib.decompressobj().decompress(raw, 200000)      # a record is tiny; refuse bombs
        record = json.loads(blob.decode("utf-8"))
    except Exception:
        raise SaveError("that is not a captain code (or part of it is missing)")
    return clean_captain(record)


def read_captain_file(path):
    try:
        if os.path.getsize(path) > 200000:
            raise SaveError("that file is too large to be a captain record")
        with open(path, encoding="utf-8") as handle:
            record = json.load(handle)
    except OSError:
        raise SaveError("the captain file could not be opened")
    except (ValueError, RecursionError):
        raise SaveError("the captain file is damaged")
    return clean_captain(record)


def list_captain_files():
    """Captain records in the shared folder: [(path, record)], newest first."""
    found = []
    try:
        names = sorted(os.listdir(captain_folder()))
    except OSError:
        return found
    for name in names:
        if not name.endswith(".captain"):
            continue
        path = os.path.join(captain_folder(), name)
        try:
            found.append((os.path.getmtime(path), path, read_captain_file(path)))
        except (SaveError, OSError):
            continue
    found.sort(key=lambda item: item[0], reverse=True)
    return [(path, record) for _, path, record in found]


class CaptainMixin:
    """The Game's captain's record: export, import, visitors. Game inherits it (game/world.py)."""
    # ------------------------------------------------------------------
    # The captain's record
    # ------------------------------------------------------------------
    def captain_record(self, event="export"):
        """This captain as a record the other Cargo games can read."""
        story = self.story_manager
        entry = {"game": GAME_ID, "event": event, "turn": self.turn,
                 "at": time.strftime("%Y-%m-%d")}
        record = {
            "format": "cargo-captain",
            "version": CAPTAIN_FORMAT,
            "id": self.captain_id,
            "name": self.player_name,
            "origin": {"game": GAME_ID, "version": VERSION},
            "rank": self.rank,
            "career": {
                "turns": self.turn,
                "money": int(self.ship.money),
                "trades": self.trades_completed,
                "victories": self.ship.combat_victories.get("total", 0),
                "passengers": self.reputation_manager.total_passengers,
                "reputation": self.ship.passenger_reputation,
                "locations": len(self.known_locations),
                "research_points": self.ship.research_points,
            },
            "research": sorted(self.research.unlocked_options),
            "ship": {"attack": self.ship.attack, "defense": self.ship.defense, "speed": self.ship.speed},
            "story": {
                "chapter": story.current_chapter or "",
                "completed": sorted(story.completed_chapters),
                "ending": self.ending_reached or "",
                "flags": self.record_flags(),
                "plot_points": story.plot_points,
            },
            "hold": {str(item): int(count) for item, count in self.ship.items.items()
                     if isinstance(count, int) and count > 0},
            "achievements": sorted(getattr(self, "achievements", {})),
            "standing": {faction: self.standing_of(faction) for faction in ("hansa", "mandate", "concord")},
            "log": list(self.captain_log) + [entry],
        }
        record["check"] = _captain_check(record)
        return clean_captain(record)

    def record_flags(self):
        """The flags a record carries: those later parts read first, then the rest."""
        on = {flag for flag, value in self.story_manager.story_states.items() if value}
        carried = {flag for flag, info in story_data()["flags"].items() if info.get("carries_to")}
        return sorted(on & carried) + sorted(on - carried)

    def close_record(self, ending):
        """The story is told: remember how it ended and let the record travel on."""
        self.ending_reached = ending
        path, code = self.export_captain("ending")
        lines = ["Your captain's record has been closed for this timeline."]
        if path:
            lines.append(f"It waits in {path}")
        lines.append("Use 'captain' to carry it into another part of the saga.")
        self.display_story_message(lines)

    def export_captain(self, event="export"):
        """Write the captain's record to the shared folder; returns (path, code)."""
        record = self.captain_record(event)
        path = os.path.join(captain_folder(), "%s-%s.captain" % (safe_name(self.player_name), GAME_ID))
        try:
            write_json(path, record)
        except OSError:
            path = None
        self.captain_log = record["log"]
        return path, captain_to_code(record)

    def receive_captain(self, record):
        """Take in a captain from another timeline.  Returns a message."""
        if record["id"] == self.captain_id:
            return "That is your own record. The Loop does not let a captain meet themselves here."
        self.visiting_captains = [c for c in self.visiting_captains if c["id"] != record["id"]]
        self.visiting_captains.append(record)
        self.captain_log.append({"game": record["origin"]["game"], "event": "crossing",
                                 "turn": self.turn, "at": time.strftime("%Y-%m-%d")})
        self.captain_log = self.captain_log[-20:]
        return "Captain %s (%s, from %s) has crossed into this timeline." % (
            record["name"], record["rank"] or "no rank", record["origin"]["game"])

    def has_visiting_captain(self, game=None, ending=None, flag=None):
        """True when a captain with the given origin / ending / story flag has crossed over."""
        for captain in self.visiting_captains:
            if game and captain["origin"]["game"] != game:
                continue
            if ending and captain["story"]["ending"] != ending:
                continue
            if flag and flag not in captain["story"]["flags"]:
                continue
            return True
        return False

    def handle_captain_menu(self):
        """The captain's record: look at it, send it out, take one in."""
        content = [
            [f"Captain {self.player_name}", f"{self.rank}"],
            [f"Record {self.captain_id}", f"Turn {self.turn}"],
            [f"Crossings logged: {len(self.captain_log)}", f"Visitors: {len(self.visiting_captains)}"],
        ]
        for captain in self.visiting_captains:
            content.append([f"  {captain['name']}", f"from {captain['origin']['game']}"])
        print(self.create_box(content, 'double'))
        action = self.validate_input(
            "Captain's record: export, import, back",
            ['export', 'e', 'import', 'i', 'back', 'b'])
        if action in ('export', 'e'):
            path, code = self.export_captain()
            lines = ["Your record is ready to travel."]
            if path:
                lines.append(f"File: {path}")
            lines.append("Or carry this code (copy all of it):")
            self.display_simple_message(lines, 0)
            print(code)                 # unboxed and unwrapped, so it copies cleanly
            input("Press Enter to continue...")
        elif action in ('import', 'i'):
            self.handle_captain_import()

    def handle_captain_import(self):
        files = [(path, record) for path, record in list_captain_files()
                 if record["id"] != self.captain_id]
        if files:
            content = [["Records in the shared folder:"]]
            for number, (path, record) in enumerate(files[:9], 1):
                content.append([f"{number}. {record['name']} - {record['origin']['game']}, "
                                f"{record['rank'] or 'no rank'}"])
            print(self.create_box(content, 'single'))
        self.display_simple_message(
            "Type a number from the list, paste a captain code, or press Enter to cancel:", 0)
        answer = input(">>> ").strip()
        if not answer:
            self.display_simple_message("Nobody crossed over.")
            return
        try:
            if answer.isdigit() and 1 <= int(answer) <= len(files[:9]):
                record = files[int(answer) - 1][1]
            else:
                record = captain_from_code(answer)
            self.display_simple_message(self.receive_captain(record))
        except SaveError as error:
            self.display_simple_message(f"The record was refused: {error}")


# The game's other modules, imported last so that the modules can refer to each other.
from .terminal import _ANSI_RE  # noqa: E402
from .saves import GAME_ID, SaveError, captain_folder, safe_name, write_json  # noqa: E402
from .story import story_data  # noqa: E402
