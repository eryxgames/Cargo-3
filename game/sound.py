"""Sound: CLIo's synthesizer (kit/audio) playing Cargo 3's music and effects.

Music is composed by the synth from a mood and a seed, so there are no audio files: a song per
kind of place, one for convoy fights and one for each act of the story (music/cargo3.music.json).
Effects are CLIo's, named by what happens: a trade, a fight's rounds, a module fitted, an
achievement, the story's cues.

Everything is optional and fails silently: with no audio player on the machine, with
CARGO_SOUND=0, or after `sound off`, nothing plays. The setting is kept with the style in the
trilogy's settings file.
"""
import json
import os

MUSIC_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "music", "cargo3.music.json")
# The story's cue names (story/cargo3/*.json "sound") and the game's moments, as CLIo effects
CUES = {"intro": "quest", "displaced": "teleport", "ending": "win", "chapter": "quest_done",
        "trade": "coin", "fit": "craft", "achievement": "levelup", "needle": "airlock",
        "round_won": "hit", "round_lost": "hurt", "miss": "miss", "fight_won": "enemy_down",
        "fight_lost": "lose", "broken": "error"}
_AUDIO = []


def music_table():
    try:
        with open(MUSIC_FILE, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return {"songs": {}, "places": {}, "acts": {}}


def audio():
    """The one Audio object (CLIo's), made on first use; a silent one when sound is off."""
    if not _AUDIO:
        table = music_table()
        try:
            from kit.audio import Audio, Silent
            if os.environ.get("CARGO_SOUND", "1") == "0" or not read_settings().get("sound", True):
                player = Silent()
            else:
                player = Audio(songs=table.get("songs"))
        except Exception:                      # no kit, or no way to play: silence
            player = None
        _AUDIO.append(player)
    return _AUDIO[0]


def sfx(moment):
    player = audio()
    if player is not None:
        try:
            player.sfx(CUES.get(moment, moment))
        except Exception:
            pass


class SoundMixin:
    """The Game's music and effects. Game inherits it (game/world.py)."""

    def music_for_now(self):
        """The song for this moment: a fight's, else the act's in act 3, else the place's."""
        table = music_table()
        if getattr(self, "in_fight", False):
            return "battle"
        act = self.story_manager.get_chapter_number() if hasattr(self, "story_manager") else 1
        if act >= 3 and str(act) in table.get("acts", {}):
            return table["acts"][str(act)]
        kind = type(self.current_location).__name__ if getattr(self, "current_location", None) else "Planet"
        return table.get("places", {}).get(kind) or table.get("places", {}).get("default", "calm")

    def play_music(self):
        player = audio()
        if player is not None:
            try:
                player.music(self.music_for_now())
            except Exception:
                pass

    def handle_sound(self):
        """The `sound` command: music and effects on or off (kept for later games)."""
        player = audio()
        on = read_settings().get("sound", True)
        rows = [["Sound"], [""], ["Music and effects are %s." % ("on" if on else "off")]]
        if player is not None and on:
            status = getattr(player, "note", "") or ""
            if status:
                rows.append(["Player: %s." % status])
        rows.append(["Music is composed as you play; no files are needed."])
        print(self.create_box(rows, 'round'))
        answer = self.validate_input("Sound on or off (on/off, Enter to leave): ", ["on", "off"])
        if answer is None:
            return
        write_settings({"sound": answer == "on"})
        _AUDIO.clear()
        if answer == "off" and player is not None:
            try:
                player.shutdown()
            except Exception:
                pass
        else:
            self.play_music()
        self.display_simple_message("Sound is %s." % answer, 1)


# The game's other modules, imported last so that the modules can refer to each other.
from .look import read_settings, write_settings  # noqa: E402
