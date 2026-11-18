#!/usr/bin/env python3
"""Cargo 3's sound, played into CLIo's recording backend (nothing reaches a speaker): the songs
compose and render, each kind of place gets its song, a convoy fight switches to the battle song
and back, act 3 has its own, the moments play their effects, `sound off` is kept, and with no
player at all nothing breaks.
Usage: python3 tools/sound.py"""
import os, random, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ["CARGO_SAGA_HOME"] = tempfile.mkdtemp(prefix="cargo3-sound-")
import headless  # noqa: E402

cargo = headless.load(os.path.join(os.path.dirname(HERE), "game", "world.py"))
from game import sound, tactics  # noqa: E402
from kit.audio import Audio, Silent  # noqa: E402
from kit.audio.backends import NullBackend  # noqa: E402

problems = []


def expect(ok, what):
    if not ok:
        problems.append(what)


table = sound.music_table()
backend = NullBackend(record=True)
player = Audio(songs=table["songs"], backend=backend, cache_dir=tempfile.mkdtemp(prefix="cargo3-audio-"))
sound._AUDIO[:] = [player]

game, io = headless.new_game(cargo, afloat=True)
for kind, song in table["places"].items():
    if kind == "default":
        continue
    expect(song in table["songs"], "the song for %s is in the table" % kind)
game.current_location = next(loc for loc in game.locations if type(loc).__name__ == "Planet")
game.play_music()
expect(player.playing == player.resolve_track("calm")[0], "a planet plays the calm song: %s" % player.playing)
rendered = [path for kind, path in backend.log if kind == "loop"]
expect(rendered and os.path.getsize(rendered[-1]) > 10000, "the song is composed and rendered to a sound file")
game.current_location = cargo.DeepSpaceOutpost("DSO-Test", 7, 3, 20, "Stable")
game.play_music()
expect(player.playing == player.resolve_track("mystery")[0], "an outpost plays the mystery song")

# a convoy fight: the battle song, effects for the rounds, then back to the place's song
game.ship.attack, game.ship.defense = 6, 4
io.queue.clear(); io.feed(["1", "1", "1"] + [""] * 6)
before = len(backend.log)
random.seed(4)
playing = []
real = game.play_music


def spy():
    real()
    playing.append(player.playing)


game.play_music = spy
with headless.quiet():
    game.fight("corsair", 0, [])
game.play_music = real
expect(player.resolve_track("battle")[0] in playing, "a convoy fight plays the battle song")
expect(player.playing == player.resolve_track("mystery")[0], "after the fight the place's song comes back")
effects = [path for kind, path in backend.log[before:] if kind == "play"]
expect(len(effects) >= 2, "the rounds of a fight play effects: %d" % len(effects))

# act 3 has its own song
game.story_manager.current_chapter = "ch3a"
game.play_music()
expect(player.playing == player.resolve_track("tense")[0], "act 3 plays the tense song")

# the moments and the story's cues all name effects CLIo has
from kit.audio.sfx import SFX  # noqa: E402
missing = [cue for cue, effect in sound.CUES.items() if effect not in SFX]
expect(not missing, "every cue names one of CLIo's effects: %s" % missing)
cues = {n.get("sound") for n in cargo.story_data()["nodes"].values() if n.get("sound")}
expect(cues <= set(sound.CUES), "every story cue has an effect: %s" % sorted(cues - set(sound.CUES)))

# `sound off` is kept, and the next game is silent
io.queue.clear(); io.feed(["off"])
with headless.quiet():
    game.handle_sound()
from game import look  # noqa: E402
expect(look.read_settings().get("sound") is False, "sound off is kept in the settings")
os.environ["CARGO_SOUND"] = "1"
expect(isinstance(sound.audio(), Silent), "with sound off the game makes a silent player")
os.environ["CARGO_SOUND"] = "0"

# with nothing to play on, nothing breaks
sound._AUDIO[:] = [Audio(songs=table["songs"], backend=NullBackend(), cache_dir=tempfile.mkdtemp())]
with headless.quiet():
    game.play_music()
    sound.sfx("trade")
    game.fight("corsair", 0, [])
sound._AUDIO[:] = [None]
with headless.quiet():
    game.play_music()
    sound.sfx("trade")

for problem in problems:
    print("FAIL", problem)
print("sound: %s" % ("ok" if not problems else "%d problems" % len(problems)))
sys.exit(1 if problems else 0)
