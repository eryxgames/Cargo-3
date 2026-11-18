"""Load cargo.py as a module and build a Game without a terminal.

    from headless import load, new_game
    cargo = load("/path/to/cargo.py")
    game, io = new_game(cargo)          # io.feed([...]) queues answers for input()
"""
import builtins, importlib.util, io as _io, os, sys, time, contextlib

os.environ.setdefault("CARGO_SOUND", "0")      # tests never start an audio player


class IO:
    def __init__(self):
        self.queue = []
        self.default = ""
        self.asked = []
        self.strict = False

    def feed(self, items):
        self.queue.extend(items)

    def input(self, prompt=""):
        self.asked.append(prompt)
        if self.queue:
            return self.queue.pop(0)
        if self.strict:
            raise EOFError("input exhausted at prompt %r" % prompt)
        return self.default


def load(path, name="cargo"):
    """The game as a module. A file inside a package (game/world.py) is imported as
    part of its package, which also loads every module of the game; a single file (Cargo 1's
    cargo.py) is loaded on its own under `name`."""
    folder = os.path.dirname(os.path.abspath(path))
    if os.path.exists(os.path.join(folder, "__init__.py")):
        sys.path.insert(0, os.path.dirname(folder))
        module = os.path.basename(folder) + "." + os.path.splitext(os.path.basename(path))[0]
        return importlib.import_module(module)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def is_game_object(value, game_module):
    """True for an object of one of the game's own classes (in any of its modules)."""
    package = game_module.__name__.rpartition(".")[0] or game_module.__name__
    module = type(value).__module__
    return module == package or module.startswith(package + ".") or module == game_module.__name__


def patch(cargo, io):
    builtins.input = io.input
    time.sleep = lambda *a, **k: None
    os.system = lambda *a, **k: 0
    if hasattr(cargo, "time"):
        cargo.time.sleep = lambda *a, **k: None


@contextlib.contextmanager
def quiet():
    buf = _io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        yield buf
    finally:
        sys.stdout = old


def new_game(cargo, difficulty="1", name="Tester", silent=True, voyage="2", afloat=False):
    """A new game, answered through its first prompts. Cargo 3 begins without a ship; `afloat`
    gives the captain one at once, for the checks of the ship's own systems."""
    io = IO()
    patch(cargo, io)
    io.feed([difficulty, voyage, name])
    if silent:
        with quiet():
            game = cargo.Game()
    else:
        game = cargo.Game()
    if afloat and getattr(game, "ship", None) is None and hasattr(game, "give_ship"):
        game.give_ship()
    return game, io
