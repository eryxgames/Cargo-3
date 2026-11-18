"""How the game looks: CLIo's terminal detection and themes (kit/), applied to Cargo's boxes.

The terminal is asked once what it can show (colour depth, Unicode); the chosen theme gives
each kind of box its frame and colours. A theme is picked with the `style` command and kept
in the settings file in the trilogy's shared folder; CARGO_STYLE overrides it for one run.
Themes come from CLIo (kit/style/configs) and from Cargo 2's own folder (themes/), which
holds the palettes of Cargo 2 0.1.0-a. With no colour (a pipe, a file, NO_COLOR) the boxes
are drawn exactly as before, only their frames follow the theme.
"""
import json
import os
import sys

from kit.term import Term
from kit.theme import available_themes, load_theme
from kit.ui import UI

GAME_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # themes/ lives here
DEFAULT_STYLE = "cargo"

# Cargo's three kinds of box, and the CLIo role whose frame each takes
BOX_ROLES = {"single": "description", "double": "story", "round": "dialogue"}
# the border colour of each kind of box, when the theme sets no frame colour of its own
BORDER_ROLES = {"single": "system", "double": "list_title", "round": "ambient"}

# CLIo's frames, with the pieces render_box also needs (tees, column separator, inner rule)
FRAME_PARTS = {
    "SINGLE": dict(tl="┌", tr="┐", bl="└", br="┘", h="─", v="│", sep="│", l="├", r="┤"),
    "DOUBLE": dict(tl="╔", tr="╗", bl="╚", br="╝", h="═", v="║", sep="║", l="╟", r="╢", rule="─"),
    "ROUNDED": dict(tl="╭", tr="╮", bl="╰", br="╯", h="─", v="│", sep="│", l="├", r="┤"),
    "HEAVY": dict(tl="┏", tr="┓", bl="┗", br="┛", h="━", v="┃", sep="┃", l="┠", r="┨", rule="─"),
    "DOTS": dict(tl="·", tr="·", bl="·", br="·", h="·", v=":", sep=":", l=":", r=":"),
    "BLOCK": dict(tl="▛", tr="▜", bl="▙", br="▟", h="▀", v="█", sep="▐", l="█", r="█", rule="▀"),
    "ASCII": dict(tl="+", tr="+", bl="+", br="+", h="-", v="|", sep="|", l="+", r="+"),
}
# what each box falls back to when a theme draws that role with no frame at all
PLAIN_FRAMES = {"single": "SINGLE", "double": "DOUBLE", "round": "ROUNDED"}

_STATE = {}


def settings_path():
    from .saves import GAME_ID, cargo_home      # saves imports the screens; fetch it when needed
    return os.path.join(cargo_home(), GAME_ID, "settings.json")


def read_settings():
    try:
        with open(settings_path(), encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def write_settings(changes):
    from .saves import write_json
    data = read_settings()
    data.update(changes)
    try:
        write_json(settings_path(), data)
        return True
    except OSError:
        return False


def styles():
    """[(name, description)] of every theme there is: Cargo 2's own first, then CLIo's."""
    found = []
    for name in available_themes(GAME_DIR):
        theme = load_theme(name, GAME_DIR)
        found.append((name, theme.description))
    return sorted(found, key=lambda pair: (pair[0] != DEFAULT_STYLE, pair[0]))


def setup(style=None, out=None, **term_options):
    """Ask the terminal what it can show and load a theme. Tests pass `out` and options."""
    if out is None:
        out = sys.__stdout__ or sys.stdout       # the real terminal, even while output is captured
    if os.environ.get("CARGO_ASCII"):
        term_options.setdefault("unicode", False)
    term = Term(out=out, **term_options)
    name = style or os.environ.get("CARGO_STYLE") or read_settings().get("style") or DEFAULT_STYLE
    if name not in [n for n, _ in styles()]:
        name = DEFAULT_STYLE
    theme = load_theme(name, GAME_DIR)
    term.set_roles(theme.roles())
    _STATE.clear()
    _STATE.update(term=term, theme=theme, ui=UI(term, theme), style=name)
    return _STATE


def current():
    """The terminal, theme and CLIo UI in use (set up on first use)."""
    if not _STATE:
        setup()
    return _STATE


def unicode():
    return current()["term"].unicode


def box_chars(kind):
    """The frame pieces for one of Cargo's boxes ('single', 'double', 'round')."""
    state = current()
    if not state["term"].unicode:
        return FRAME_PARTS["ASCII"]
    frame = state["theme"].style(BOX_ROLES.get(kind, "description"))["frame"]
    if frame not in FRAME_PARTS:
        frame = PLAIN_FRAMES.get(kind, "SINGLE")
    if frame == "BLOCK" and state["term"].limited_glyphs:
        frame = "HEAVY"
    return FRAME_PARTS[frame]


def border_spec(kind):
    """Colour spec for the border of a box ('' with no colour)."""
    state = current()
    if state["term"].color_depth <= 0:
        return ""
    own = state["theme"].ui.get("frame_color") or ""
    return own or BORDER_ROLES.get(kind, "system")


def text_spec(color=None):
    """Colour spec for the text in a box: a raw SGR code the game asks for ('31'), or the theme's."""
    if current()["term"].color_depth <= 0:
        return ""
    return "sgr:" + color if color else "default"


def paint(text, spec):
    return current()["term"].paint(text, spec) if spec else text


def gradient(lines):
    """Lines in the theme's title gradient (the logo); unchanged with little or no colour."""
    return current()["ui"].gradient(lines)
