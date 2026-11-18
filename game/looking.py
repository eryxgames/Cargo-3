"""Look and think: a light adventure layer over the docks.

`look` shows what is at the dock now: the place, what is going on (the next needle, people due),
the people whose routes have them here (story characters with a "route"), and the sights of the
place (story nodes of kind "sight"). Picking one plays it as a scene; sights can be looked at
again. Some sights have choices that need an item, a flag or a person met elsewhere: that is how
the side quests work (a pass for a locker, a reader for a console, a loader's hand, a recorded
trace, a sold archive). None of it is on the way to an ending.

`think` shows the captain's own notes: thoughts (story nodes of kind "thought") whose conditions
hold, where the people the captain has met travel, the special equipment aboard, and what the
next step of the story still needs, in the captain's words.
"""

# Special equipment found through sights: a story flag each, read by the game where it matters
EQUIPMENT = {
    "founders_transponder": ("Founders' transponder", "needle fares 15% lower: the offices wave a founder's code through"),
    "decoy_code": ("Decoy code", "Mandate patrols wave you through half the time"),
    "loader_patch": ("Adit's patch routine", "modules wear half as fast"),
    "needle_talk": ("Needle-talk", "fewer fights on needles: the file closes up when you call trouble"),
    "institute_charts": ("The Institute's survey charts", "research from every voyage goes 15% further"),
}
EQUIPMENT_FARE = 0.85
DECOY_WAVE = 0.5
LOADER_WEAR = 0.5           # modules wear this much with Adit's patch routine
NEEDLE_TALK_RISK = 0.7      # trouble on a needle with needle-talk
CHARTS_RESEARCH = 1.15      # research on the way with the Institute's charts


class LookMixin:
    """The Game's look and think commands. Game inherits it (game/world.py)."""

    def has_equipment(self, flag):
        return bool(self.story_manager.story_states.get(flag))

    def people_here(self):
        place = self.current_location.name
        return [cid for cid, info in story_data()["characters"].items()
                if info.get("route") and self.story.where_is(cid) == place]

    def sights_here(self):
        """Sight nodes the captain can look at here now: people first, then things."""
        data = story_data()
        snap = self.story.snapshot()
        place = self.current_location.name
        people, things = [], []
        for nid in data.get("order", list(data["nodes"])):
            node = data["nodes"].get(nid) or {}
            if node.get("kind") != "sight":
                continue
            if node.get("where") and node["where"] != place:
                continue
            if not self.story.check(self.story.requires_of(node), snap):
                continue
            (people if "here" in str(node.get("requires", "")) else things).append(nid)
        return people + things

    def met(self, cid):
        """Whether the captain has talked to this character at a dock."""
        data = story_data()
        return any(nid in self.story.done for nid, node in data["nodes"].items()
                   if node.get("kind") == "sight" and cid in (node.get("who") or []))

    def happenings(self):
        lines = []
        wait = self.needle_wait()
        lines.append("A needle forms at the buoy this turn." if not wait else
                     "The next needle forms in %d turn%s." % (wait, "" if wait == 1 else "s"))
        place = self.current_location.name
        for cid, info in story_data()["characters"].items():
            if info.get("route") and self.met(cid) and self.story.where_is(cid) != place \
                    and self.story.where_is(cid, self.turn + 1) == place:
                lines.append("%s is due here next turn." % self.story.fill("{%s}" % cid))
        return lines

    def handle_look(self):
        place = self.current_location
        about = (story_data()["places"].get(place.name) or {}).get("about")
        sights = self.sights_here()
        rows = [["Look around: %s" % place.name], [""]]
        if about:
            rows.extend([line] for line in self.word_wrap(about))
            rows.append([""])
        rows.extend([line] for line in self.happenings())
        if sights:
            rows.append([""])
            for number, nid in enumerate(sights, 1):
                rows.extend([line] for line in self.option_lines(number, self.sight_label(nid)))
        else:
            rows.extend([[""], ["Nothing else here catches your eye."]])
        print(self.create_box(rows, 'double'))
        if not sights:
            return
        answer = self.validate_input("Look at (1-%d, Enter to leave): " % len(sights),
                                     [str(i) for i in range(1, len(sights) + 1)])
        if answer is None:
            return
        self.story.play(sights[int(answer) - 1])

    def sight_label(self, nid):
        node = story_data()["nodes"][nid]
        title = self.story.fill(node.get("title") or nid)
        return ("Talk to " + title) if node.get("who") and "here" in str(node.get("requires", "")) else title

    def handle_think(self):
        data = story_data()
        snap = self.story.snapshot()
        rows = [["What you think"], [""]]
        thoughts = [self.story.fill(node.get("text") if isinstance(node.get("text"), str) else " ".join(node.get("text", [])))
                    for nid, node in data["nodes"].items()
                    if node.get("kind") == "thought" and self.story.check(self.story.requires_of(node), snap)]
        for line in thoughts:
            rows.extend([w] for w in self.word_wrap(line))
            rows.append([""])
        for cid, info in data["characters"].items():
            route = info.get("route")
            if route and self.met(cid):
                stay = route.get("stay", 1)
                places = route["places"]
                where = self.story.where_is(cid)
                if len(places) == 1:
                    line = "%s is always at %s." % (self.story.fill("{%s}" % cid), places[0])
                else:
                    line = "%s flies %s, %s at each; now at %s." % (
                        self.story.fill("{%s}" % cid), ", ".join(places), "a turn" if stay == 1 else "%d turns" % stay, where)
                rows.extend([w] for w in self.word_wrap(line))
        owned = [EQUIPMENT[f] for f in EQUIPMENT if self.has_equipment(f)]
        if owned:
            rows.extend([[""], ["Special equipment aboard:"]])
            for name, what in owned:
                rows.extend([w] for w in self.word_wrap("%s: %s." % (name, what)))
        sm = self.story_manager
        chapter = sm.chapters.get(sm.current_chapter)
        if chapter is not None:
            target = chapter
            if chapter.completed:
                target = next((sm.chapters[c] for c in chapter.next_chapters if c in sm.chapters
                               and not (story_data()["nodes"].get(c) or {}).get("secret")), chapter)
            needs = [words for _, words in sm.chapter_needs(target)]
            needs += ["%s (%s)" % (m.title, m.description) for m in target.milestones.values()
                      if target is chapter and not m.completed]
            if needs:
                rows.extend([[""], ["To go on (%s), I still need:" % target.title]])
                for need in needs[:6]:
                    rows.extend([w] for w in self.word_wrap("- " + need))
        if len(rows) == 2:
            rows.append(["Nothing in particular. Fly, trade, look around."])
        print(self.create_box(rows, 'round'))
        input("Press Enter to continue...")

    def equipment_rows(self):
        return [["  %s: %s" % EQUIPMENT[f]] for f in EQUIPMENT if self.has_equipment(f)]


# The game's other modules, imported last so that the modules can refer to each other.
from .story import story_data  # noqa: E402
