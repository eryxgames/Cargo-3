"""Standing with the powers of 2460: the Hauler Hansa, the Terran Mandate and the Stellar Concord.

Each standing runs from -100 to 100 and starts at 0 (an opening can move it). The story reads
it as `standing.hansa` and so on and changes it with effects of the same name. What it does now:
the Hansa's needle fares follow it; Mandate cutters and militia wave a trusted captain through;
the Concord's houses share more of what they know (research from travel). The Binary Dawn's
trust is kept too, as `dawn_trust`, and shown nowhere until the Dawn speaks to the captain.
"""

FACTIONS = {   # id: (name in text, what it is in 2460)
    "hansa": ("the Hansa", "the Hauler Hansa: the needles between the stars, the Mark, the dues"),
    "mandate": ("the Mandate", "the Terran Mandate: the legions merged, the observatories that see every jump"),
    "concord": ("the Concord", "the Stellar Concord: the research houses, the drive licences, the underwriters"),
}
LOW, HIGH = -100, 100
WORDS = ((60, "one of their own"), (20, "trusted"), (-19, "known"), (-59, "distrusted"), (LOW, "hunted"))


def standing_word(value):
    for floor, word in WORDS:
        if value >= floor:
            return word
    return WORDS[-1][1]


class FactionsMixin:
    """The Game's standing with the factions. Game inherits it (game/world.py)."""

    def standing_of(self, faction):
        return getattr(self, "standing", {}).get(faction, 0)

    def change_standing(self, faction, amount):
        """Move a standing (clamped to -100..100); the dawn's trust is 'dawn'."""
        if not hasattr(self, "standing"):
            self.standing = {name: 0 for name in FACTIONS}
        if faction == "dawn":
            self.dawn_trust = max(LOW, min(HIGH, getattr(self, "dawn_trust", 0) + int(amount)))
            return self.dawn_trust
        if faction not in FACTIONS:
            return 0
        self.standing[faction] = max(LOW, min(HIGH, self.standing.get(faction, 0) + int(amount)))
        return self.standing[faction]

    def standing_rows(self):
        """One row per faction, for the journal: name, number, a word."""
        return [["- %s: %+d, %s" % (FACTIONS[f][0][0].upper() + FACTIONS[f][0][1:], self.standing_of(f),
                                     standing_word(self.standing_of(f)))] for f in FACTIONS]

    def hansa_fare_factor(self):
        """The Hansa charges a captain it trusts less, and one it distrusts more (0.6 to 1.4)."""
        return 1.0 - self.standing_of("hansa") / 250.0

    def waved_through(self, enemy_kind):
        """A Mandate cutter or militia lets a captain it trusts pass without a stop."""
        import random
        if enemy_kind != "militia":           # customs cutters and toll militia
            return False
        trust = self.standing_of("mandate")
        if self.has_equipment("decoy_code") and random.random() < DECOY_WAVE:
            return True                         # the Mandate's own decoy code, found at Gamma
        return trust >= 20 and random.random() < trust / 100.0

    def concord_research_factor(self):
        """The Concord's houses share more with a captain they trust (0.5 to 1.5)."""
        return 1.0 + self.standing_of("concord") / 200.0


from .looking import DECOY_WAVE  # noqa: E402
