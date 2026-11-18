"""Convoy fights: a fight with a group, round by round, where the needle's wake does not protect.

A small enemy (threat 1 or 2) is still settled in one roll, as in Cargo 1. A bigger one is a
race: both sides have two marks, and each round one side takes a mark off the other. The
captain gives an order every round:
- focus fire: the round's odds are set so that a fight of focused fire is won as often as a
  one-roll fight with the same ship and enemy;
- screen the convoy: in a needle the haulers in the file behind you are in the line of fire.
  Screening costs you some odds, and the file is safe. Otherwise a round they win also costs
  the file a container, and the Hansa hears about it;
- countermeasures (a working shield module, once a fight): if they win the round, they miss;
- drones in first (a working drone hangar, once a fight): better odds for a round;
- board them (pirates, raiders and smugglers down to their last mark): worse odds, a prize;
- break off: the odds of a run, a little better after you have hurt them.
Every round costs the hull a little glancing fire; a lost mark costs more, and losing the last
one more again. Winning and losing pay out as a one-roll fight does (Game.fight_result), and
tools/fights.py checks the odds and the damage stay close to a one-roll fight's.
"""
import random

MARKS = 2               # each side's marks: lose both and the fight is lost
TACTICAL_FROM = 3       # threat at which a fight becomes a convoy fight

YOU_SCORE = ["A clean hit: one of them drops out of the formation, venting.",
             "Hole in one. Their lead ship spins away with its lights out.",
             "Your fire walks across their hull, and one of them breaks off."]
THEY_SCORE = ["They rake your hull.", "Steel rain: their volley lands.", "Contact, close in: they hit you hard."]


def round_chance(fight_chance):
    """The odds of one round that make a race to two marks as likely to be won as a one-roll
    fight with these odds (so focusing fire every round is the fight Cargo 1 had)."""
    low, high = 0.0, 1.0
    for _ in range(30):
        q = (low + high) / 2
        if q * q * (3 - 2 * q) < fight_chance:
            low = q
        else:
            high = q
    return (low + high) / 2


class TacticsMixin:
    """The Game's convoy fights. Game inherits it (game/world.py)."""

    def convoy_fight(self, enemy_id, bounty, lines, edge=0, shield=1.0):
        enemy = ENEMIES[enemy_id]
        ship = self.ship
        power = enemy["power"]
        convoy = bool(getattr(self, "in_needle", False))
        self.in_fight = True
        self.play_music()
        try:
            return self._rounds(enemy_id, bounty, lines, edge, shield, enemy, ship, power, convoy)
        finally:
            self.in_fight = False
            self.play_music()

    def _rounds(self, enemy_id, bounty, lines, edge, shield, enemy, ship, power, convoy):
        theirs, yours = MARKS, MARKS
        used, counters = set(), 0
        convoy_hits, screened_rounds = 0, 0
        hit_total = 0.0
        hurt = False
        round_no = 0
        story = list(lines)
        while theirs > 0 and yours > 0:
            round_no += 1
            base = round_chance(self.fight_chance(power, edge)) + (0.05 if ship.researched("fire_control") else 0)
            options = [("focus", "Focus fire (%s)" % odds_word(base))]
            if convoy:
                options.append(("screen", "Screen the convoy (%s)" % odds_word(max(0.05, base - 0.1))))
            if ship.working("shield") and counters < (2 if ship.researched("countermeasure_suite") else 1):
                options.append(("counter", "Countermeasures: chaff and flares"))
            if ship.working("hangar") and "drones" not in used:
                options.append(("drones", "Drones in first (%s)" % odds_word(min(0.95, base + 0.2))))
            if theirs == 1 and enemy["kind"] in ("pirate", "raider", "smuggler"):
                options.append(("board", "Board them (%s)" % odds_word(max(0.05, base - 0.15))))
            escape = min(0.95, self.escape_chance(enemy) + (0.1 if hurt else 0))
            options.append(("break", "Break off (%s)" % odds_word(escape)))
            title = "%s, round %d" % (enemy["name"], round_no)
            state = ["Them: %d of %d marks. You: %d of %d." % (theirs, MARKS, yours, MARKS)]
            if convoy:
                state.append("The haulers of your needle are in the file behind you.")
            move = self.ask_move(title, story + state, options, 1)      # what just happened, then where it stands
            story = []
            if move == "break":
                if random.random() < escape:
                    return self.convoy_end(enemy_id, "escaped", convoy, convoy_hits, screened_rounds, round_no,
                                           ["You break off and burn for the far side of the file. They let you go."])
                move = "focus"                 # they catch you: a round fought on their terms
                base -= 0.15
                story.append("They cut you off.")
            chance = base
            if move == "screen":
                chance, screened_rounds = base - 0.1, screened_rounds + 1
            elif move == "drones":
                chance = base + 0.2
                used.add("drones")
            elif move == "board":
                chance = base - 0.15
            elif move == "counter":
                counters += 1
            chance = max(0.05, min(0.95, chance))
            unit = power / ship.fight_defense() * (1 + self.difficulty) * shield
            hit_total += random.randint(1, 2) * unit           # the round's glancing fire, whoever wins it
            if random.random() < chance:
                theirs -= 1
                hurt = True
                sfx("round_won")
                story.append(random.choice(YOU_SCORE))
                if move == "board" and theirs == 0:
                    return self.convoy_end(enemy_id, "boarded", convoy, convoy_hits, screened_rounds, round_no,
                                           ["Your crew goes across with cutters and comes back with their hold."],
                                           bounty, hit_total)
            elif move == "counter":
                sfx("miss")
                story.append("Chaff and flares: their volley goes wide.")
            else:
                sfx("round_lost")
                yours -= 1
                hit_total += random.randint(3, 6) * unit
                if yours == 0:
                    hit_total += random.randint(3, 5) * unit   # and they close in at the end
                story.append(random.choice(THEY_SCORE))
                if convoy and move != "screen":
                    convoy_hits += 1
                    story.append("A shot goes past you into the file: a hauler behind you loses a container.")
        outcome = "won" if theirs == 0 else "lost"
        return self.convoy_end(enemy_id, outcome, convoy, convoy_hits, screened_rounds, round_no, story,
                               bounty, hit_total)

    def convoy_end(self, enemy_id, outcome, convoy, convoy_hits, screened, rounds, lines, bounty=0, hit=0.0):
        """How a convoy fight ends: the file's opinion, then the usual reckoning."""
        lines = list(lines)
        if convoy and outcome != "escaped":
            if convoy_hits == 0 and screened:
                self.change_standing("hansa", 3)
                lines.append("The file saw you screen them. The Hansa hears about it.")
            elif convoy_hits:
                self.change_standing("hansa", -2 * convoy_hits)
                lines.append("The file lost %d container%s. The Hansa hears about that too." % (
                    convoy_hits, "" if convoy_hits == 1 else "s"))
        if outcome == "escaped":
            return self.after_fight("escaped", lines, '33')
        if outcome == "lost":
            hit = max(hit, 1.0)
        return self.fight_result(enemy_id, bounty, lines, outcome in ("won", "boarded"), hit,
                                 prize=1.5 if outcome == "boarded" else 1.0)


# The game's other modules, imported last so that the modules can refer to each other.
from .encounters import ENEMIES, odds_word  # noqa: E402
from .sound import sfx  # noqa: E402
