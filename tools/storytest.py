"""Helpers for the story tests (tools/openings.py, tools/acts.py): a game started as any kind of
captain, scenes played one at a time with scripted answers, and the screen text checked."""
import os, random, re, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["CARGO_SAGA_HOME"] = tempfile.mkdtemp(prefix="cargo3-story-tests-")     # saves stay out of ~
from headless import IO, load, patch, quiet  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cargo = load(os.path.join(ROOT, "game", "world.py"))
from game import captain as captains  # noqa: E402  (loaded with the package above)

problems = [0]


def expect(ok, what):
    if not ok:
        problems[0] += 1
        print("FAIL", what)


def record(game_id=None, ending="", flags=(), name="Ada Quill", rank="Hauler"):
    """A captain record as another part would write it."""
    if game_id is None:
        return None
    rec = {"format": "cargo-captain", "version": 1, "id": "T-1", "name": name, "rank": rank,
           "origin": {"game": game_id, "version": "test"},
           "career": {"turns": 140, "money": 900000, "trades": 80},
           "story": {"chapter": "ch3", "completed": [], "ending": ending, "flags": list(flags), "plot_points": 40},
           "ship": {"attack": 5, "defense": 5, "speed": 5}, "hold": {}, "log": []}
    rec["check"] = captains._captain_check(rec)
    return captains.clean_captain(rec)


def start(rec, seed=1):
    """A new game as this captain (or a fresh one): the opening plays; returns game, io, screen text."""
    random.seed(seed)
    io = IO()
    patch(cargo, io)
    with quiet() as buf:
        if rec is None:
            io.feed(["1", "2", "Tester"])
            game = cargo.Game()
        else:
            io.feed(["1", "2"])
            game = cargo.Game(player_name=rec["name"], origin=rec)
    io.queue.clear()
    return game, io, buf.getvalue()


def flat(text):
    """Screen text as one line: box borders out, wrapped lines joined."""
    return " ".join(re.sub(r"[\u2500-\u259f|]", " ", text).split())


def options(text):
    """How many numbered choices the last box on the screen offers."""
    return len(set(re.findall(r"(?:^|[\u2502|]) (\d+)\. ", text, flags=re.M)))


def unfilled(text):
    return re.findall(r"\{[a-z_]+(?:\.[a-z]+)?\}", text)


def play(game, io, nid, answer="1", where=None):
    """Play one scene with one answer, at a planet or at the named place; returns the screen text."""
    if where:
        game.current_location = next(loc for loc in game.locations if loc.name == where)
    else:
        game.current_location = next(loc for loc in game.locations if type(loc).__name__ == "Planet")
    io.queue.clear()
    io.feed([answer] + [""] * 10)
    snap = game.story.snapshot()
    node = cargo.story_data()["nodes"][nid]
    expect(game.story.check(game.story.requires_of(node), snap), "%s can play here (%s)" % (nid, game.player_name))
    with quiet() as buf:
        game.story.play(nid)
    text = buf.getvalue()
    expect(not unfilled(text), "%s leaves %s unfilled" % (nid, unfilled(text)))
    return text
