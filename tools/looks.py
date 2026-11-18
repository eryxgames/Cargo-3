#!/usr/bin/env python3
"""Every style, at every width, with and without colour and Unicode: each kind of box the game
draws fits the screen exactly, an ASCII terminal gets only ASCII, no colour means no escape
codes, and the `style` command picks a style and keeps it.

    python3 tools/looks.py
"""
import io, os, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ["CARGO_SAGA_HOME"] = tempfile.mkdtemp(prefix="cargo-looks-")
import headless  # noqa: E402

cargo = headless.load(os.path.join(os.path.dirname(HERE), "game", "world.py"))
from game import look, terminal  # noqa: E402

SAMPLES = [   # (rows, kind, narrow): the shapes the game's screens use
    ([["A message that is long enough to wrap on a phone screen, and then some more."]], "round", "auto"),
    ([["Status"], terminal.RULE, ["Money: 1,000", "Hold: 0/400", "Turn 1"]], "double", "flow"),
    ([["Tech", "120", "130"], ["Agri", "40", "35"], ["Salt", "90", "88"], ["Fuel", "60", "61"]], "single", "auto"),
    ([["Commands here"], ["buy (b)", "sell (s)", "travel (t)", "port (p)"]], "double", "stack"),
    ([["Red text, as the game asks for warnings."]], "round", "auto"),
]
problems = []
names = [name for name, _ in look.styles()]
for name in names:
    for color in (0, 2, 3):
        for uni in (True, False):
            look.setup(style=name, out=io.StringIO(), color=color, unicode=uni)
            for columns in (100, 80, 60, 44, 40, 36):
                os.environ["COLUMNS"] = str(columns)
                terminal.terminal_columns = (lambda c: (lambda: c))(columns)
                for rows, kind, narrow in SAMPLES:
                    box = terminal.render_box(rows, kind, narrow=narrow, color="31" if "Red" in str(rows) else None)
                    where = "%s colour %d %s %d cols %s" % (name, color, "unicode" if uni else "ascii", columns, kind)
                    widths = {terminal.visible_len(line) for line in box.split("\n")}
                    if len(widths) != 1 or max(widths) > columns:
                        problems.append("%s: line widths %s" % (where, sorted(widths)))
                    if not color and "\x1b" in box:
                        problems.append("%s: escape codes with no colour" % where)
                    if color and "\x1b" not in box:
                        problems.append("%s: no colour at colour depth %d" % (where, color))
                    if not uni and not terminal._ANSI_RE.sub("", box).isascii():
                        problems.append("%s: not ASCII" % where)
terminal.terminal_columns = lambda: 80

# the command, through the real prompts: pick the third style, it is kept for later games
game, io_ = headless.new_game(cargo)
look.setup(out=io.StringIO(), color=0)
io_.feed(["3"])
with headless.quiet():
    game.choose_style()
third = names[2]
if look.current()["style"] != third or look.read_settings().get("style") != third:
    problems.append("style command: chose %s, in use %s, kept %s" % (third, look.current()["style"],
                                                                      look.read_settings().get("style")))
look.setup(out=io.StringIO(), color=0)
if look.current()["style"] != third:
    problems.append("the kept style is not used next time")
os.environ["CARGO_STYLE"] = names[0]
look.setup(out=io.StringIO(), color=0)
if look.current()["style"] != names[0]:
    problems.append("CARGO_STYLE does not override the kept style")
os.environ["CARGO_STYLE"] = "no-such-style"
look.setup(out=io.StringIO(), color=0)
if look.current()["style"] != look.DEFAULT_STYLE:
    problems.append("an unknown style does not fall back to %s" % look.DEFAULT_STYLE)

for problem in problems[:20]:
    print("FAIL", problem)
print("looks: %d styles at 6 widths, colour and not, Unicode and not: %s"
      % (len(names), "ok" if not problems else "%d problems" % len(problems)))
sys.exit(1 if problems else 0)
