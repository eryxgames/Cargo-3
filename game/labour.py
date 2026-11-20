"""The labour market: what moves a hand's wages and the berths board, as the trade events move
the prices of goods.

Every turn something may start at one of the docks (LABOUR_START): a strike or a rush order at
the hovertank plant, gas or a rich seam in the deep levels, a harvest or a blight in the farm
drums, a convoy unloading on the cargo ring, a Hansa audit, crews short or hands cheap on the
berths, a customs crackdown, a Cargolyte pilgrimage. Each runs a few turns at its dock and moves
one site's shifts (wage, closed jobs, risk) or the berths board (wages, how many ships, which
kinds stay away), or both. At most one event a site, and one for the berths, at a dock.

The hand sees what is on at this dock in the turn's market box, on the work and berths screens,
on arrival and in `look`; what is on elsewhere comes as word on the ring (news), so a hand can
go where the work is. The story reads it as stats (`labour.<id>`: turns left here, 0 if not on)
and can start one here (effect `labour.<id>`: for so many turns); `{labour_news}` fills in the
news. Events are kept in the save (`Game.labour`).
"""
import random

LABOUR_START = 0.45         # a turn's chance that something starts at one of the docks
NEWS_MOST = 2               # word on the ring: how many events elsewhere a screen names

# Each event: a short name (for the box), what it does in words, the message when it starts
# here, the news line for elsewhere, where (a work site's id, or "berths", or both), and what it
# moves: wage (a factor), closed (skills whose jobs stop, or "all"), risk (added to a bad shift's
# chance, or to the trouble a ship finds), ships (more or fewer come-and-go ships on the board),
# kinds (ship kinds weighted on the board; 0 keeps a kind away, the story's captains too), legs
# (turns added to every voyage from here), turns (how long), weight (how often).
LABOUR_EVENTS = {
    "ring_convoy": {
        "name": "Ring: a convoy unloading", "site": "ring", "wage": 1.4, "turns": (1, 2), "weight": 1.2,
        "start": "A convoy is unloading on the cargo ring: every crane is working and the ring pays four tenths more a shift.",
        "news": "a convoy unloading on %s's ring"},
    "ring_quiet": {
        "name": "Ring: quiet", "site": "ring", "wage": 0.7, "turns": (2, 3), "weight": 1.0,
        "start": "The ring is quiet: half the berths are empty and the crane bosses pay what they like.",
        "news": "the ring at %s is quiet"},
    "ring_agrobots": {
        "name": "Ring: agrobot trial", "site": "ring", "closed": ("loader",), "turns": (2, 4), "weight": 0.6,
        "start": "The ring is trying out a crew of loader agrobots. The stevedores sit it out on the bollards and watch.",
        "news": "an agrobot trial on %s's ring"},
    "ring_audit": {
        "name": "Ring: Hansa audit", "site": "ring", "berths": True, "wage": 1.0, "job_wage": {"broker": 1.6},
        "kinds": {"smuggler": 0}, "turns": (2, 3), "weight": 0.8,
        "start": "A Hansa auditor is counting the ring's manifests: tally clerks are paid six tenths more, and the smugglers have found somewhere else to be.",
        "news": "a Hansa audit at %s"},
    "plant_rush": {
        "name": "Plant: a rush order", "site": "hovertank", "wage": 1.4, "turns": (2, 4), "weight": 1.0,
        "start": "A rush order lands at the hovertank plant: double shifts, and four tenths more a shift.",
        "news": "a rush order at %s's hovertank plant"},
    "plant_strike": {
        "name": "Plant: on strike", "site": "hovertank", "closed": "all", "turns": (2, 3), "weight": 0.7,
        "start": "The hovertank plant is on strike. The pickets at the gate let nobody in, and remember faces.",
        "news": "a strike at %s's hovertank plant"},
    "mine_gas": {
        "name": "Mine: gas, shafts shut", "site": "mine", "closed": "all", "turns": (1, 3), "weight": 0.8,
        "start": "Firedamp on the deep levels: the fire boss has shut the shafts until the air clears.",
        "news": "gas in %s's deep levels"},
    "mine_seam": {
        "name": "Mine: a rich seam", "site": "mine", "wage": 1.5, "risk": 0.05, "turns": (2, 4), "weight": 0.8,
        "start": "A surveyor has found a rich seam on the deep levels: half again a shift, and nobody asks how tired you are.",
        "news": "a rich seam in %s's deep levels"},
    "drums_harvest": {
        "name": "Drums: harvest", "site": "biomass", "wage": 1.3, "turns": (2, 3), "weight": 1.0,
        "start": "Harvest in the farm drums: every tender and steward wanted, three tenths more a shift.",
        "news": "harvest in the farm drums at %s"},
    "drums_blight": {
        "name": "Drums: blight", "site": "biomass", "wage": 0.6, "risk": 0.05, "turns": (2, 4), "weight": 0.6,
        "start": "Blight in the farm drums: the crops are being burnt, and the shifts pay what burning pays.",
        "news": "blight in the farm drums at %s"},
    "berths_short": {
        "name": "Berths: crews short", "berths": True, "wage": 1.4, "ships": 1, "turns": (2, 4), "weight": 1.0,
        "start": "Crews are short on the berths: a needle shed three of them last week, and every ship is paying four tenths more for a hand.",
        "news": "crews short at %s"},
    "berths_glut": {
        "name": "Berths: hands cheap", "berths": True, "wage": 0.7, "turns": (2, 3), "weight": 0.8,
        "start": "A liner paid off its whole crew here: hands are cheap on the berths this week.",
        "news": "hands cheap at %s"},
    "berths_convoy": {
        "name": "Berths: a convoy forming", "berths": True, "ships": 2, "kinds": {"hauler": 8}, "turns": (1, 2),
        "weight": 1.0,
        "start": "A Hansa convoy is forming at the buoy: more haulers on the board than the board has room for.",
        "news": "a convoy forming at %s"},
    "berths_crackdown": {
        "name": "Berths: customs crackdown", "berths": True, "ships": -1, "kinds": {"smuggler": 0, "courier": 2},
        "risk": -0.05, "turns": (2, 4), "weight": 0.7,
        "start": "Customs is cracking down: every manifest read twice, and the smugglers keep their ships dark.",
        "news": "a customs crackdown at %s"},
    "berths_pilgrimage": {
        "name": "Berths: a pilgrimage", "berths": True, "kinds": {"tail": 6}, "turns": (2, 3), "weight": 0.5,
        "start": "A Cargolyte pilgrimage passes through: tail ships on every berth, and brothers asking who will sign the lading.",
        "news": "a Cargolyte pilgrimage at %s"},
    "berths_delay": {
        "name": "Berths: needle delayed", "berths": True, "legs": 1, "wage": 1.2, "turns": (1, 3), "weight": 0.6,
        "start": "The needle office has pushed the next needle back a turn: every voyage from here takes a turn longer, and pays for it.",
        "news": "the needle delayed at %s"},
}

# The board's usual mix of come-and-go ships (game/hand.py picks from it)
BOARD_KINDS = {"hauler": 3, "smuggler": 1, "courier": 1, "tail": 1}


def percent(factor):
    """A wage factor as words for the box: 'pay +40%', 'pay -30%'."""
    change = int(round((factor - 1) * 100))
    return "pay %+d%%" % change if change else ""


class LabourMixin:
    """The Game's labour market. Game inherits it (game/world.py)."""

    # -- where things can happen ---------------------------------------------------------------
    def labour_scopes(self, event):
        """What an event occupies at a dock: its site's id, 'berths', or both."""
        scopes = []
        if event.get("site"):
            scopes.append(event["site"])
        if event.get("berths"):
            scopes.append("berths")
        return scopes

    def labour_can_happen(self, eid, place):
        event = LABOUR_EVENTS[eid]
        if event.get("site") and not any(site["id"] == event["site"] for site in self.sites_at(place)):
            return False
        return place.location_type in ("Planet", "AsteroidBase", "DeepSpaceOutpost", "ResearchColony")

    # -- the turn ------------------------------------------------------------------------------
    def labour_tick(self, rng=random):
        """Once a turn (new_turn): what ended ends, and something may start at one of the docks."""
        self.labour = [e for e in self.labour_list() if e["until"] >= self.turn]
        if rng.random() >= LABOUR_START:
            return None
        busy = {(e["place"], scope) for e in self.labour for scope in self.labour_scopes(LABOUR_EVENTS[e["id"]])}
        where = {}                  # each event, and the docks where it could start now
        for eid, event in LABOUR_EVENTS.items():
            places = [loc.name for loc in self.locations if self.labour_can_happen(eid, loc)
                      and not any((loc.name, s) in busy for s in self.labour_scopes(event))]
            if places:
                where[eid] = places
        if not where:
            return None
        # the event first, by its weight, then the dock: a plant's strike is as likely as a quiet ring
        eid = rng.choices(list(where), weights=[LABOUR_EVENTS[e]["weight"] for e in where])[0]
        place = rng.choice(where[eid])
        return self.start_labour(eid, place, rng.randint(*LABOUR_EVENTS[eid]["turns"]))

    def start_labour(self, eid, place, turns):
        """Start (or lengthen) an event at a dock for so many turns, from this one. Anything it
        would collide with there (the same site, the berths) ends. Returns the event."""
        event = LABOUR_EVENTS[eid]
        scopes = set(self.labour_scopes(event))
        kept, found = [], None
        for item in self.labour_list():
            if item["place"] == place and item["id"] == eid:
                found = item
                kept.append(item)
            elif item["place"] == place and scopes & set(self.labour_scopes(LABOUR_EVENTS[item["id"]])):
                continue
            else:
                kept.append(item)
        until = self.turn + max(1, int(turns)) - 1
        if found:
            found["until"] = max(found["until"], until)
        else:
            found = {"id": eid, "place": place, "start": self.turn, "until": until}
            kept.append(found)
            if self.current_location is not None and place == self.current_location.name:
                self.__dict__.setdefault("labour_fresh", []).append(eid)
        self.labour = kept
        return found

    def labour_list(self):
        """The events kept in the game, mended if a save had them damaged."""
        items = getattr(self, "labour", None)
        if not isinstance(items, list):
            items = []
        good = []
        for item in items:
            if (isinstance(item, dict) and item.get("id") in LABOUR_EVENTS and isinstance(item.get("place"), str)
                    and isinstance(item.get("until"), int) and not isinstance(item.get("until"), bool)):
                good.append({"id": item["id"], "place": item["place"], "start": item.get("start", self.turn)
                             if isinstance(item.get("start"), int) else self.turn, "until": item["until"]})
        self.labour = good
        return good

    # -- what is on ------------------------------------------------------------------------------
    def labour_at(self, place=None):
        """[(id, event, turns left)] on at a dock (here by default)."""
        name = place if isinstance(place, str) else (place or self.current_location).name
        return [(e["id"], LABOUR_EVENTS[e["id"]], e["until"] - self.turn + 1)
                for e in self.labour_list() if e["place"] == name and e["until"] >= self.turn]

    def labour_left(self, eid, place=None):
        return max([left for i, _, left in self.labour_at(place) if i == eid] or [0])

    def site_terms(self, site_id, skill, place=None):
        """A job's terms at a dock: (wage factor, added risk, the event that closed it or None)."""
        factor, risk, closed = 1.0, 0.0, None
        for eid, event, _ in self.labour_at(place):
            if event.get("site") != site_id:
                continue
            shut = event.get("closed")
            if shut == "all" or (shut and skill in shut):
                closed = eid
            factor *= event.get("job_wage", {}).get(skill, event.get("wage", 1.0))
            risk += event.get("risk", 0.0)
        return factor, risk, closed

    def berth_terms(self, place=None):
        """The berths board's terms at a dock: wage factor, ships added, kinds, legs, risk."""
        terms = {"wage": 1.0, "ships": 0, "kinds": dict(BOARD_KINDS), "legs": 0, "risk": 0.0, "events": []}
        for eid, event, _ in self.labour_at(place):
            if not event.get("berths"):
                continue
            terms["events"].append(eid)
            terms["wage"] *= event.get("wage", 1.0)
            terms["ships"] += event.get("ships", 0)
            terms["legs"] += event.get("legs", 0)
            terms["risk"] += event.get("risk", 0.0)
            terms["kinds"].update(event.get("kinds", {}))
        return terms

    # -- in words ----------------------------------------------------------------------------------
    def labour_effect_words(self, event):
        bits = []
        if event.get("closed") == "all":
            bits.append("closed")
        elif event.get("closed"):
            bits.append("no %s shifts" % "/".join(event["closed"]))
        wage = percent(event.get("wage", 1.0))
        if wage:
            bits.append(wage)
        for skill, factor in event.get("job_wage", {}).items():
            bits.append("%s %s" % (skill, percent(factor)))
        if event.get("ships", 0) > 0:
            bits.append("+%d ship%s" % (event["ships"], "" if event["ships"] == 1 else "s"))
        if event.get("legs"):
            bits.append("+%d turn a voyage" % event["legs"])
        if event.get("kinds", {}).get("smuggler") == 0:
            bits.append("no smugglers")
        return ", ".join(bits)

    def labour_line(self, event, left):
        """'Plant: on strike (closed, 3 turns)'."""
        effect = self.labour_effect_words(event)
        return "%s (%s%s%d turn%s)" % (event["name"], effect, ", " if effect else "", left, "" if left == 1 else "s")

    def labour_rows(self, place=None):
        """Rows for the turn's box: what is on at a dock, a line each, wrapped to the screen."""
        rows = []
        for _, event, left in self.labour_at(place):
            rows.extend([part] for part in self.word_wrap(self.labour_line(event, left)))
        return rows

    def labour_news(self, limit=NEWS_MOST):
        """Word on the ring: what is on at other docks the captain knows of, newest first."""
        here = self.current_location.name if self.current_location is not None else ""
        known = set(self.known_locations) | set(self.discovered_locations)
        items = [e for e in self.labour_list() if e["place"] != here and e["place"] in known and e["until"] >= self.turn]
        items.sort(key=lambda e: -e["start"])
        return [LABOUR_EVENTS[e["id"]]["news"] % e["place"] for e in items[:limit]]

    def labour_news_line(self):
        news = self.labour_news()
        if not news:
            return "nothing much on at the other docks."
        line = "; ".join(news)
        return line[0].upper() + line[1:] + "."

    def labour_screen_lines(self, scope=None):
        """Lines for the foot of a screen: what is on here (for 'work', the sites' events that
        do not close anything, which the work screen names itself; for 'berths', the board's),
        then word from the other docks."""
        lines = []
        for _, event, left in self.labour_at():
            if scope == "work" and (not event.get("site") or event.get("closed")):
                continue
            if scope == "berths" and not event.get("berths"):
                continue
            lines.append(self.labour_line(event, left) + ".")
        news = self.labour_news()
        if news:
            lines.append("Word on the ring: %s." % "; ".join(news))
        return lines

    def labour_fresh_lines(self):
        """What started here since the hand last looked: its message, once."""
        fresh = self.__dict__.pop("labour_fresh", None) or []
        here = {i for i, _, _ in self.labour_at()}
        return [LABOUR_EVENTS[eid]["start"] for eid in dict.fromkeys(fresh) if eid in here]

    def labour_arrival_lines(self, place):
        return [LABOUR_EVENTS[eid]["start"] for eid, _, _ in self.labour_at(place)]
