"""Starting: continue a save, or begin a new game, as a new captain or one from the records
folder."""

def choose_saved_game(saves, game=None):
    """Show the saved games and return the chosen one loaded, or None."""
    def tell(message):
        print(render_box([[message]], 'round'))

    rows = [["Saved games"]]
    for number, entry in enumerate(saves[:9], 1):
        rows.append([f"{number}. {describe_save(entry)}"])
    print(render_box(rows, 'single'))
    tell("Type a number to load it, or press Enter to go back:")
    answer = input(">>> ").strip()
    if not (answer.isdigit() and 1 <= int(answer) <= len(saves[:9])):
        return None
    try:
        loaded = load_game(saves[int(answer) - 1]["path"])
    except SaveError as error:
        tell(f"Could not load: {error}")
        return None
    tell(f"Welcome back, {loaded.player_name}. Turn {loaded.turn}.")
    return loaded


def start_game():
    """New game, or continue a saved one when there are any."""
    saves = list_saves()
    if saves:
        display_logo(logo_data, centered=False)
        print(render_box([["Saved games found."],
                          [f"Latest: {describe_save(saves[0])}"],
                          ["c - continue the latest"],
                          ["l - choose a save"],
                          ["n - new game"]], 'round'))
        answer = input(">>> ").strip().lower()
        try:
            if answer in ("c", "continue", ""):
                return load_game(saves[0]["path"])
            if answer in ("l", "load"):
                loaded = choose_saved_game(saves)
                if loaded:
                    return loaded
        except SaveError as error:
            print(render_box([[f"Could not load: {error}"], ["Starting a new game instead."]], 'round'))
    return new_game()


def choose_captain():
    """A new game: a new captain, or one whose record waits in the shared folder.

    A captain carried in from a finished game - this one or another part of the
    saga - starts again here, and the story says why.  Returns the record or None.
    """
    found = list_captain_files()[:8]
    if not found:
        return None
    rows = [["Captains in your records folder"], [""]]
    for number, (_, record) in enumerate(found, 1):
        story = record.get("story", {})
        rows.append(["%d. %s, %s (%s%s)" % (
            number, record["name"], record["rank"] or "no rank", GAME_TITLES.get(record["origin"]["game"], "?"),
            ", " + ending_title(record) if story.get("ending") else "")])
    rows.extend([[""], ["Type a number to play as that captain, or press Enter for a new one."]])
    print(render_box(rows, 'round'))
    answer = input(">>> ").strip()
    if answer.isdigit() and 1 <= int(answer) <= len(found):
        return found[int(answer) - 1][1]
    return None


def new_game():
    from .world import Game         # world.py imports this module: Game is fetched when needed
    record = choose_captain()
    if record is None:
        return Game()
    return Game(player_name=record["name"], origin=record)


def main():
    safe_output()
    game = start_game()
    while game is not None:
        try:
            game.play()
            game = None
        except SwitchGame as switch:
            game = switch.game
        except (EOFError, KeyboardInterrupt):
            # the terminal went away (or Ctrl-C at a plain prompt): keep the progress
            game.autosave()
            print()
            game = None


# The game's other modules, imported last so that the modules can refer to each other.
from .terminal import display_logo, logo_data, render_box, safe_output  # noqa: E402
from .saves import SaveError, SwitchGame, describe_save, list_saves, load_game  # noqa: E402
from .captain import list_captain_files  # noqa: E402
from .story import GAME_TITLES, ending_title  # noqa: E402
