"""Saves: the whole world as one JSON file in the trilogy's shared folder, and the Game's save and
load commands."""
import json
import os
import re
import shutil
import sys
import time
from . import VERSION

# =============================================================================
# Save games: the whole world as one JSON file.
# Saves and captain records live in a folder shared by the Cargo trilogy:
# ~/.cargo-saga (or wherever CARGO_SAGA_HOME points).
# =============================================================================

GAME_ID = "cargo3"
SAVE_FORMAT = 1
AUTOSAVE_SLOT = "autosave"


class SaveError(Exception):
    """A save or captain file could not be written or understood."""


class SwitchGame(Exception):
    """Raised inside a running game to continue with another one (after a load)."""

    def __init__(self, game):
        Exception.__init__(self, "switch game")
        self.game = game


_ADOPTED = []


def cargo_home():
    """The folder the trilogy shares: ~/.cargo-saga, or wherever CARGO_SAGA_HOME points.
    Up to 1.2.0 it was ~/.cargo (or CARGO_HOME), which Rust's package manager also uses;
    the first time the new default folder is used, Cargo's own files there are copied over."""
    chosen = os.environ.get("CARGO_SAGA_HOME")
    if chosen:
        return chosen
    home = os.path.join(os.path.expanduser("~"), ".cargo-saga")
    if not _ADOPTED:
        _ADOPTED.append(True)
        adopt_old_files(home)
    return home


def adopt_old_files(home):
    """Copy this game's saves and the captain records from the folder 1.2.0 used, once.
    Only Cargo's own subfolders are touched; the old ones stay where they were."""
    old = os.environ.get("CARGO_HOME") or os.path.join(os.path.expanduser("~"), ".cargo")
    for part in (GAME_ID, "captains"):
        source, target = os.path.join(old, part), os.path.join(home, part)
        if os.path.isdir(source) and not os.path.exists(target):
            try:
                shutil.copytree(source, target)
            except (OSError, shutil.Error):
                pass


def save_folder():
    return os.path.join(cargo_home(), GAME_ID, "saves")


def captain_folder():
    return os.path.join(cargo_home(), "captains")


def safe_name(text, fallback="captain"):
    """A file name made of letters, digits, '-' and '_' only."""
    name = re.sub(r"[^A-Za-z0-9_-]+", "_", str(text)).strip("_")[:32]
    return name or fallback


def write_json(path, data):
    """Write a JSON file so that a crash never leaves half a file behind."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = "%s.%d.tmp" % (path, os.getpid())
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    with open(tmp, "w", encoding="utf-8") as handle:
        handle.write(text)
    os.replace(tmp, path)


def game_classes():
    """The classes a save file may contain: the ones defined in the game's own modules."""
    package = __name__.rpartition(".")[0]
    found = {}
    for name, module in list(sys.modules.items()):
        if module is not None and name.startswith(package + "."):
            for key, obj in vars(module).items():
                if isinstance(obj, type) and obj.__module__ == name:
                    found[key] = obj
    return found


def _is_code(value):
    return callable(value) and not isinstance(value, type)


def encode_world(root):
    """Turn the object graph under `root` into JSON-friendly data.

    Objects of the game's own classes are written once and referred to by number
    afterwards, so shared objects stay shared and loops are fine.  Functions are
    not saved; loading takes them from a freshly built game (see decode_world).
    """
    classes = set(game_classes().values())
    counts = {}          # id -> times seen, for containers that are shared
    stack, seen_objects = [root], set()
    while stack:
        value = stack.pop()
        if isinstance(value, (str, int, float, bool, type(None))) or _is_code(value) or isinstance(value, type):
            continue
        key = id(value)
        if isinstance(value, (list, dict, set, frozenset, tuple)):
            counts[key] = counts.get(key, 0) + 1
            if counts[key] > 1:
                continue
            if isinstance(value, dict):
                stack.extend(value.keys())
                stack.extend(value.values())
            else:
                stack.extend(value)
        elif type(value) in classes:
            if key in seen_objects:
                continue
            seen_objects.add(key)
            stack.extend(vars(value).values())
        else:
            raise SaveError("cannot save a value of type %s" % type(value).__name__)

    numbers = {}

    def number(value):
        numbers[id(value)] = len(numbers) + 1
        return numbers[id(value)]

    def enc(value):
        if isinstance(value, (str, int, float, bool, type(None))):
            return value
        if isinstance(value, type):
            return {"~": "c", "c": value.__name__}
        if _is_code(value):
            return {"~": "f"}
        key = id(value)
        if key in numbers:
            return {"~": "r", "i": numbers[key]}
        shared = counts.get(key, 0) > 1
        if isinstance(value, list):
            if not shared:
                return [enc(v) for v in value]
            return {"~": "l", "i": number(value), "v": [enc(v) for v in value]}
        if isinstance(value, tuple):
            return {"~": "t", "v": [enc(v) for v in value]}
        if isinstance(value, (set, frozenset)):
            out = {"~": "s", "v": None}
            if shared:
                out["i"] = number(value)
            items = [enc(v) for v in value]
            try:
                items.sort(key=lambda v: json.dumps(v, sort_keys=True))
            except TypeError:
                pass
            out["v"] = items
            return out
        if isinstance(value, dict):
            simple = all(isinstance(k, str) for k in value) and "~" not in value
            if simple and not shared:
                return {k: enc(v) for k, v in value.items()}
            out = {"~": "d"}
            if shared:
                out["i"] = number(value)
            out["v"] = [[enc(k), enc(v)] for k, v in value.items()]
            return out
        out = {"~": "o", "c": type(value).__name__, "i": number(value)}
        out["s"] = {k: enc(v) for k, v in vars(value).items()}
        return out

    limit = sys.getrecursionlimit()
    sys.setrecursionlimit(max(limit, 20000))
    try:
        return enc(root)
    finally:
        sys.setrecursionlimit(limit)


# Classes older saves may contain that this version replaced (their content now
# comes from the story data): loading drops them instead of refusing the save.
RETIRED_CLASSES = {"DynamicCharacterSystem", "EventChain", "CharacterManager", "CharacterTemplate"}

# Places that were renamed: old saves are brought up to date when loaded.
RENAMED_PLACES = {"Alien Outpost X": "Alien Signal Research Outpost X",
                  "Alien Outpost Y": "Alien Signal Research Outpost Y"}
RENAMED_TYPES = {"Alien Outpost": "Alien Signal Research Outpost"}


def decode_world(data, fresh):
    """Rebuild a saved world on top of `fresh`, a newly constructed game.

    Only classes from this file are ever instantiated, and never through their
    constructors, so loading a save cannot run code of its own.  The fresh game
    supplies what a save does not carry: functions, and attributes added in a
    later version.
    """
    classes = game_classes()
    by_number = {}
    claimed = set()

    def hashable(value):
        try:
            hash(value)
            return True
        except TypeError:
            return False

    def dec(node, old):
        if isinstance(node, list):
            base = old if isinstance(old, list) else []
            return [dec(v, base[i] if i < len(base) else None) for i, v in enumerate(node)]
        if not isinstance(node, dict):
            return node
        kind = node.get("~")
        if kind is None:
            base = old if isinstance(old, dict) else {}
            return {k: dec(v, base.get(k)) for k, v in node.items()}
        if kind == "r":
            if node.get("i") not in by_number:
                raise SaveError("save file refers to something it does not contain")
            return by_number[node["i"]]
        if kind == "f":
            return old if _is_code(old) else None
        if kind == "c":
            if node.get("c") not in classes:
                raise SaveError("unknown class in save file")
            return classes[node["c"]]
        if kind == "t":
            return tuple(dec(v, None) for v in node.get("v", []))
        if kind == "l":
            out = []
            if "i" in node:
                by_number[node["i"]] = out
            base = old if isinstance(old, list) else []
            out.extend(dec(v, base[i] if i < len(base) else None) for i, v in enumerate(node.get("v", [])))
            return out
        if kind == "s":
            out = set()
            if "i" in node:
                by_number[node["i"]] = out
            for v in node.get("v", []):
                item = dec(v, None)
                if hashable(item):
                    out.add(item)
            return out
        if kind == "d":
            out = {}
            if "i" in node:
                by_number[node["i"]] = out
            base = old if isinstance(old, dict) else {}
            for pair in node.get("v", []):
                key = dec(pair[0], None)
                if hashable(key):
                    out[key] = dec(pair[1], base.get(key))
            return out
        if kind == "o":
            cls = classes.get(node.get("c"))
            if cls is None and node.get("c") in RETIRED_CLASSES:
                by_number[node.get("i")] = None          # a system this version no longer has
                return None
            if cls is None:
                raise SaveError("unknown class in save file: %s" % str(node.get("c"))[:40])
            if type(old) is cls and id(old) not in claimed:
                obj = old
            else:
                obj = cls.__new__(cls)
            claimed.add(id(obj))
            by_number[node.get("i")] = obj
            before = dict(vars(obj))
            for key, value in node.get("s", {}).items():
                if isinstance(value, dict) and value.get("~") == "f" and not _is_code(before.get(key)):
                    continue        # a function set on this object when it was saved: keep the class's own
                obj.__dict__[str(key)] = dec(value, before.get(key))
            return obj
        raise SaveError("save file contains something unknown")

    limit = sys.getrecursionlimit()
    sys.setrecursionlimit(max(limit, 20000))
    try:
        result = dec(data, fresh)
    finally:
        sys.setrecursionlimit(limit)
    if result is not fresh:
        raise SaveError("save file does not hold a game")
    return result


def list_saves():
    """Saved games, newest first: [{'slot', 'path', 'summary', 'saved_at'}]."""
    saves = []
    try:
        names = os.listdir(save_folder())
    except OSError:
        return saves
    for name in names:
        if not name.endswith(".json"):
            continue
        path = os.path.join(save_folder(), name)
        try:
            with open(path, encoding="utf-8") as handle:
                head = json.load(handle)
            if head.get("format") != "cargo-save" or head.get("game") != GAME_ID:
                continue
            saves.append({"slot": name[:-5], "path": path, "summary": head.get("summary", {}),
                          "saved_at": head.get("saved_at", ""), "mtime": os.path.getmtime(path)})
        except (OSError, ValueError, AttributeError, RecursionError):
            continue
    saves.sort(key=lambda entry: entry["mtime"], reverse=True)
    return saves


def describe_save(entry):
    summary = entry.get("summary") or {}
    return "%s - %s, turn %s, %s" % (
        entry["slot"], str(summary.get("player", "?"))[:20], summary.get("turn", "?"),
        str(summary.get("location", "?"))[:20])


def load_game(slot_or_path):
    """Read a save file and return the game it holds."""
    path = slot_or_path
    if not os.path.isfile(path):
        path = os.path.join(save_folder(), safe_name(slot_or_path, AUTOSAVE_SLOT) + ".json")
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except OSError:
        raise SaveError("no such saved game")
    except (ValueError, RecursionError):
        raise SaveError("the save file is damaged")
    if not isinstance(data, dict) or data.get("format") != "cargo-save" or data.get("game") != GAME_ID:
        raise SaveError("this is not a Cargo save file")
    if data.get("version", 0) > SAVE_FORMAT:
        raise SaveError("this save was made by a newer version of the game")
    summary = data.get("summary") or {}
    difficulty = summary.get("difficulty")
    from .world import Game         # world.py imports this module: Game is fetched when needed
    fresh = Game(difficulty=difficulty if difficulty in (0, 1, 2) else 1,
                 player_name=str(summary.get("player", "Captain"))[:40], intro=False)
    try:
        game = decode_world(data.get("state"), fresh)
    except SaveError:
        raise
    except Exception as error:      # a save from elsewhere must never crash the game
        raise SaveError("the save file could not be read (%s)" % type(error).__name__)
    game.term_width = game.get_terminal_width()
    game.term_height = game.get_terminal_height()
    game.bring_up_to_date()
    return game


class SavingMixin:
    """The Game's save and load commands. Game inherits it (game/world.py)."""
    # ------------------------------------------------------------------
    # Saving and loading
    # ------------------------------------------------------------------
    def save_summary(self):
        return {
            "player": self.player_name,
            "difficulty": self.difficulty,
            "turn": self.turn,
            "money": int(self.person.money),
            "location": self.current_location.name,
            "chapter": self.story_manager.current_chapter,
        }

    def save_game(self, slot=None):
        """Write the whole game to a slot; returns the file path."""
        slot = safe_name(slot or self.player_name, AUTOSAVE_SLOT)
        path = os.path.join(save_folder(), slot + ".json")
        data = {
            "format": "cargo-save",
            "version": SAVE_FORMAT,
            "game": GAME_ID,
            "game_version": VERSION,
            "saved_at": time.strftime("%Y-%m-%d %H:%M"),
            "summary": self.save_summary(),
            "state": encode_world(self),
        }
        try:
            write_json(path, data)
        except OSError as error:
            raise SaveError("could not write the save file (%s)" % (error.strerror or "error"))
        return path

    def autosave(self):
        """Quietly keep the latest turn; a failed autosave never stops the game."""
        try:
            self.save_game(AUTOSAVE_SLOT)
        except Exception:
            pass

    def handle_save(self):
        self.display_simple_message(
            f"Save as (Enter for '{safe_name(self.player_name)}', or type a name):", 0)
        slot = ask(">>> ").strip()
        if slot.lower() in ("cancel", "back", "none"):
            self.display_simple_message("Not saved.")
            return
        try:
            self.save_game(slot or self.player_name)
            self.display_simple_message(
                f"Game saved as '{safe_name(slot or self.player_name)}' (turn {self.turn}).")
        except SaveError as error:
            self.display_simple_message(f"Not saved: {error}")

    def handle_load(self):
        saves = list_saves()
        if not saves:
            self.display_simple_message("There are no saved games yet.")
            return
        game = choose_saved_game(saves, self)
        if game:
            raise SwitchGame(game)


# The game's other modules, imported last so that the modules can refer to each other.
from .start import choose_saved_game  # noqa: E402
from .terminal import ask  # noqa: E402
