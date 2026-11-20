"""What a hand's money buys: implants at the clinic, and lessons with a master at each dock.

A hand on foot earns more than a hand needs (about 13,000 credits by turn 120, with nothing
dear to buy). These turn money into skill, on curves that rise with the level, so the first
steps are cheap and the last are dear, and the best deals are spread across the docks:

- **Implants** (the cybersurgeon at Epsilon): a level now. The price grows with the square of
  the level fitted (500 for green, 2,000 for able, 4,500 for handy, 8,000 for skilled), and
  each implant already fitted makes the next dearer by three tenths. Surgery hurts (10 wounds
  and 5 more for each level), and the surgeon will not cut a hand hurt worse than 50. Nothing is
  fitted above skilled: a master's level is earned.
- **Lessons** (a master of one skill at each dock): practice toward the next level, a turn
  each, at a price that grows with the level (40, 160, 360, 640, 1,000) and teaches more as it
  rises (1, 3, 5, 7, 9). Cheaper than implants, slower, and only where that master works.

Measured with the bot (tools/bot.py, which uses both when it has money to spare): see
tools/training.py for the numbers this is checked against.
"""
from .person import SKILL_TOP, SKILLS, skill_word

IMPLANT_BASE = 500          # the price of an implant to green; the curve is BASE x level^2
IMPLANT_LOAD = 0.3          # each implant already fitted makes the next dearer by this share
IMPLANT_TOP = 4             # implants go up to skilled; a master's level is earned
IMPLANT_WOUNDS = (10, 5)    # surgery: 10 wounds, and 5 more for each level of the new skill
IMPLANT_MAX_WOUNDS = 50     # the surgeon will not cut a hand hurt worse than this
LESSON_BASE = 40            # a lesson at level 0; the curve is BASE x (level + 1)^2
# The masters: where each skill is taught, and by whom (roles, named by what they do)
MASTERS = {
    "Alpha": [("broker", "an exchange clerk of the Hansa")],
    "Beta": [("steward", "the farm drums' canteen boss")],
    "Gamma": [("loader", "the crane master on the ring")],
    "Delta": [("mechanic", "the plant's line chief"), ("gunner", "the range master")],
    "Epsilon": [("navigator", "a navigation tutor on the research ring")],
}


def round_to(value, step=50):
    return int(step * round(float(value) / step))


def implant_price(level_to, fitted):
    """An implant that brings a skill to this level, when so many are fitted already."""
    return round_to(IMPLANT_BASE * level_to ** 2 * (1 + IMPLANT_LOAD * fitted))


def lesson_price(level):
    return int(LESSON_BASE * (level + 1) ** 2)


def lesson_practice(level):
    return 1 + 2 * level


class TrainingMixin:
    """The Game's clinic and lessons. Game inherits it (game/world.py)."""

    # -- implants ---------------------------------------------------------------------------------
    def implants_fitted(self):
        fitted = getattr(self.person, "implants", None)
        if not isinstance(fitted, dict):
            fitted = self.person.implants = {}
        return sum(n for n in fitted.values() if isinstance(n, int) and not isinstance(n, bool))

    def implant_offer(self, skill):
        """(price, the level it brings, why not) for one skill: why not is '' when it can be fitted."""
        level = self.person.skill(skill)
        if level >= IMPLANT_TOP:
            return None, level, ("a master's level is earned, not fitted" if level < SKILL_TOP else "as good as it gets")
        price = implant_price(level + 1, self.implants_fitted())
        if self.person.wounds > IMPLANT_MAX_WOUNDS:
            return price, level + 1, "too hurt for surgery"
        if self.person.money < price:
            return price, level + 1, "you cannot pay it"
        return price, level + 1, ""

    def implant_clinic(self, pick=None, sure=None):
        """The cybersurgeon's catalogue: an implant for any skill, a level each. `pick` and `sure`
        answer the prompts in a test. Returns the skill fitted, or None."""
        rows = [["The implant catalogue"], [""]]
        for number, skill in enumerate(SKILLS, 1):
            price, to, why = self.implant_offer(skill)
            level = skill_word(self.person.skill(skill))
            if price is None:
                label = "%s: %s (%s)" % (skill.capitalize(), level, why)
            else:
                label = "%s: %s to %s, %s%s" % (skill.capitalize(), level, skill_word(to), self.format_money(price),
                                                " (%s)" % why if why else "")
            rows.extend([line] for line in self.option_lines(number, label))
        rows.extend([[""]] + [[line] for line in self.word_wrap(
            "Each implant fitted makes the next dearer. Surgery hurts. Nothing is fitted above skilled.")])
        print(self.create_box(rows, 'round'))
        answer = pick if pick is not None else self.validate_input(
            "Fit which (1-%d, Enter to leave): " % len(SKILLS), [str(i) for i in range(1, len(SKILLS) + 1)])
        if not answer:
            return None
        skill = SKILLS[int(answer) - 1]
        price, to, why = self.implant_offer(skill)
        if price is None or why:
            self.display_simple_message("The cybersurgeon shakes her head: %s." % why, 1)
            return None
        if sure is None:
            sure = self.validate_input("Fit a %s implant for %s? (yes/no): " % (skill, self.format_money(price)),
                                       ['yes', 'no', 'y', 'n']) in ('yes', 'y')
        if not sure:
            return None
        person = self.person
        person.money -= price
        person.skills[skill] = to
        person.__dict__.setdefault("next_at", {}).pop(skill, None)     # a new level, a new draw
        person.practice[skill] = 0
        person.implants[skill] = person.implants.get(skill, 0) + 1
        hurt = IMPLANT_WOUNDS[0] + IMPLANT_WOUNDS[1] * to
        person.wounds += hurt
        self.display_story_message([
            "It takes an hour and a local anaesthetic that runs out halfway. Afterwards your hands "
            "know the work a little before you do.", "",
            "Paid %s. %s: now %s. Wounds +%d%%." % (self.format_money(price), skill.capitalize(), skill_word(to), hurt)],
            pause=1)
        self.autosave()
        return skill

    # -- lessons ----------------------------------------------------------------------------------------
    def lessons_here(self):
        """[(skill, master, price, practice)] taught at this dock, below the top level."""
        offers = []
        for skill, master in MASTERS.get(self.current_location.name, []):
            level = self.person.skill(skill)
            if level < SKILL_TOP:
                offers.append((skill, master, lesson_price(level), lesson_practice(level)))
        return offers

    def take_lesson(self, skill, master, price, practice):
        """A lesson: paid, practised, a turn. Returns the new level if it rose."""
        person = self.person
        if person.money < price:
            self.display_simple_message("A lesson with %s costs %s; you have %s." % (
                master, self.format_money(price), self.format_money(int(person.money))))
            return None
        person.money -= price
        risen = person.train(skill, practice)
        lessons = self.__dict__.setdefault("lessons", {})
        lessons[skill] = lessons.get(skill, 0) + 1
        lines = ["A turn with %s: %s practice." % (master, skill), "", "Paid %s." % self.format_money(price)]
        if risen:
            lines.append("%s: now %s." % (skill.capitalize(), skill_word(risen)))
        self.display_story_message(lines, pause=1)
        self.pass_turns(1)
        self.autosave()
        return risen
