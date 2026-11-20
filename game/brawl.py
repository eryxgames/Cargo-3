"""Fights on foot: a hand without a ship fights with what they carry and what they can do.

A fight is a few rounds. Each round the captain gives an order, at odds given in words:
- strike: hand to hand (gunner; a knife or a cutting torch helps);
- shoot: with something that shoots (gunner; a stunner, a rivet gun or a slug pistol);
- grapple: get hold of them (loader; exoskeleton knees help); if it works they cannot hit back;
- guard: cover up; they hit less often this round, and your next blow is likelier;
- talk them down (steward or broker, whichever is better; easier as they get hurt), if they talk;
- run (navigator; harder from people who shoot, and when hurt);
- pay what they want, when what they want is money.
They hit back each round unless something stops them; armour takes some of it. A hit is wounds
(game/person.py). At WOUNDS_DOWN the captain is down: robbed, carried off or saved. Only people
who mean to kill (`lethal`) can make it worse, and only some of the time.

Fights come from the docks (trouble: more often at rough docks, for a hand with a fat purse,
and with some of the events on, game/labour.py), from what the hand does (crossing a picket
line) and from the story (`brawl <foe>`, game/story.py). Gear is bought at the outfitter (`gear`).
tools/brawl.py checks the odds, every ending, the gear, saves and the screens; the bot measures
how often a hand fights and how often one falls.
"""
import random

# Who a hand can fight. marks: blows that finish them; skill: how well they fight (0-5);
# harm: wounds a blow of theirs does; armed: they shoot (running is harder); talk: the base
# chance of talking them down (None: they do not talk), talk_skill: the skill that talks to them
# (else steward or broker, the better); robs: the share of the purse they want (paying it ends
# the fight; a downed hand loses it); toll and most: the least and the most they take (a hand's
# savings are not all in one pocket); fine and carry: they arrest a
# downed hand instead; lethal: the chance that a downed hand is killed; loot: what a winner finds;
# plot: plot points for beating them. Where they turn up as trouble: weight (0: only when the
# story or a labour action sends them), places, types, labour (only while that event is on here).
FOES = {
    "dock_tough": {
        "name": "a dock tough", "marks": 2, "skill": 1, "harm": (8, 16), "talk": 0.45, "robs": 0.25, "toll": 40, "most": 300,
        "loot": (20, 60), "weight": 3,
        "start": ["A dock tough steps out between two containers with a length of chain. \"Your purse, or your teeth.\"",
                  "Someone big has been following you since the hiring hall. Now he is in front of you, with a chain."],
        "won": "The tough goes down on the deck plates and stays there.",
        "talked": "You talk about the weather, the shift bosses and his mother. He lets the chain drop.",
    },
    "pickpockets": {
        "name": "two kids with quick hands", "marks": 1, "skill": 0, "harm": (3, 6), "talk": 0.6, "robs": 0.1, "toll": 20, "most": 120,
        "loot": (0, 0), "weight": 2,
        "start": ["A hand goes into your pocket in the crowd at the shift change. There are two of them, and they are fast."],
        "won": "You catch one by the collar. The other one gives back what they took, and they both run.",
        "talked": "You tell them where the real money walks: past the Hansa office at the end of the shift. They grin and go.",
    },
    "cargolyte_stevedores": {
        "name": "three Cargolyte stevedores", "marks": 3, "skill": 2, "harm": (10, 18), "talk": 0.4, "robs": 0.33, "toll": 60, "most": 400,
        "loot": (0, 0), "plot": 1, "weight": 2, "places": ("Beta", "Gamma"), "types": ("AsteroidBase", "DeepSpaceOutpost"),
        "start": ["Three Cargolyte stevedores block the gangway. \"Is your lading clean, brother? The Sender takes a third.\""],
        "won": "The stevedores pick each other up and go, chanting a manifest under their breath.",
        "talked": "You greet them \"in apparent good order and condition\", and they bow and let you pass.",
    },
    "company_guards": {
        "name": "two company guards", "marks": 2, "skill": 2, "harm": (8, 14), "talk": 0.45, "talk_skill": "broker",
        "robs": 0, "fine": 80, "carry": True, "loot": (0, 0), "weight": 1, "places": ("Gamma",),
        "start": ["Two company guards with stun batons stop you at the gallery gate. \"You're not on the roster.\""],
        "won": "The guards back off and call it in. Nobody comes; it is the end of the shift.",
        "talked": "You show them a pay slip and a lot of confidence. They wave you through.",
        "carried": "You wake up in the company's lock-up. They let you out for a fine.",
    },
    "claim_jumpers": {
        "name": "claim jumpers", "marks": 2, "skill": 2, "harm": (12, 20), "armed": True, "talk": 0.35, "robs": 0.2,
        "toll": 80, "most": 500, "loot": (60, 140), "plot": 1, "labour": "mine_seam",
        "start": ["Word of the rich seam has brought claim jumpers with rivet guns. They want the survey you are carrying."],
        "won": "The claim jumpers drop their rivet guns and run for the shaft. One leaves a purse behind.",
        "talked": "You point them at the wrong gallery. They thank you.",
    },
    "feral_loader": {
        "name": "a loader agrobot gone wild", "marks": 3, "skill": 2, "harm": (15, 25), "talk": None, "robs": 0,
        "lethal": 0.15, "loot": (0, 0), "plot": 2, "labour": "ring_agrobots",
        "start": ["One of the trial agrobots has lost its safety governor. It is stacking people now, and it has seen you."],
        "won": "You get to its power coupling, and the agrobot settles on its pads like a sigh.",
        "saved": "The stevedores drag you out from under it and someone finds the power coupling.",
        "kill": "The agrobot stacks you with the rest of the load.",
    },
    "yard_guards": {
        "name": "the yard's night watch", "marks": 2, "skill": 2, "harm": (8, 14), "talk": 0.4, "talk_skill": "broker",
        "robs": 0, "fine": 150, "carry": True, "loot": (0, 0), "plot": 1,
        "start": ["Torches come on along the fence: the impound yard's night watch, two of them, with stun batons."],
        "won": "The night watch sits down in the dust between two hulls and decides it saw nothing.",
        "talked": "You show the night watch a letter on good paper. Neither of them can read it, and both of them nod.",
        "carried": "You wake up in the yard's guardhouse. The Mandate fines trespassers by the hour.",
    },
    "pickets": {
        "name": "the picket line", "marks": 2, "skill": 1, "harm": (6, 12), "talk": 0.5, "robs": 0, "loot": (0, 0),
        "start": ["The pickets close the gate on you, arms linked."],
        "won": "You push through the line. Nobody there will forget your face.",
        "talked": "You talk your way through. They let you in, and they let you know what they think.",
        "saved": "The plant's medic picks you up off the gate and patches you, for free, which is worse.",
    },
    "rootstock_enforcers": {
        "name": "two androids in good suits", "marks": 3, "skill": 3, "harm": (14, 22), "talk": 0.35, "robs": 0.2,
        "toll": 100, "most": 1000, "lethal": 0.25, "loot": (50, 150), "plot": 2,
        "start": ["Two androids in good suits fall into step beside you. \"Meza Voce would like a word. Several, in fact.\""],
        "won": "The androids sit down against a bulkhead, very politely, and stop moving.",
        "talked": "You tell them what Meza Voce would want to hear. They decide that is what she said.",
        "kill": "The androids are very polite about it.",
    },
    "mandate_troopers": {
        "name": "a Mandate fire team", "marks": 4, "skill": 4, "harm": (15, 25), "armed": True, "talk": 0.4,
        "talk_skill": "broker", "robs": 0, "fine": 200, "carry": True, "loot": (0, 0), "plot": 2,
        "start": ["A Mandate fire team in heavy armour comes round the corner, and the corporal looks at you, then at a slate."],
        "won": "The fire team falls back to wait for the heavy infantry. You do not wait with them.",
        "talked": "Your papers are in order, as far as the corporal can read them.",
        "carried": "You wake up in a Mandate holding cell, with a fine to pay and a name on a list.",
    },
    "grey_men": {
        "name": "two men in grey", "marks": 3, "skill": 3, "harm": (15, 25), "armed": True, "talk": 0.25, "robs": 0,
        "lethal": 0.35, "loot": (0, 0), "plot": 3,
        "start": ["Two men in grey are waiting at your bunk. \"Serac sends his regards. He has been patient.\""],
        "won": "The men in grey go back the way they came, slower.",
        "talked": "You tell them a story for Serac. They write it down, and leave you for later.",
        "kill": "Serac's patience has run out.",
    },
}

# What a hand can carry. melee and ranged weapons (bonus to the odds; heavy: a blow that lands
# counts twice; stun: a hit stops their next blow), armour (soak: wounds taken off each of their
# blows; dodge: on their odds), knees (grapple and run bonuses).
GEAR = {
    "knife": {"kind": "melee", "bonus": 0.10, "price": 60, "words": "strikes land more often"},
    "cutting torch": {"kind": "melee", "bonus": 0.15, "heavy": True, "price": 450, "words": "a strike that lands counts twice"},
    "stunner": {"kind": "ranged", "bonus": 0.10, "stun": True, "price": 300, "words": "a hit stops their next blow"},
    "rivet gun": {"kind": "ranged", "bonus": 0.10, "price": 220, "words": "something to shoot with"},
    "slug pistol": {"kind": "ranged", "bonus": 0.20, "heavy": True, "price": 1200,
                    "words": "a hit counts twice; the Mandate does not like it"},
    "work suit": {"kind": "armour", "soak": 3, "price": 120, "words": "takes a little off every blow"},
    "vacuum suit": {"kind": "armour", "soak": 6, "dodge": -0.03, "price": 600, "words": "takes more off, and slows you"},
    "exoskeleton knees": {"kind": "knees", "grapple": 0.15, "run": 0.10, "price": 800,
                          "words": "from Scholz's Star's old stock: grapple and run better"},
}
# Who sells what (an outfitter at every dock; places first, then kinds of place)
OUTFITTERS = {
    "Alpha": ("knife", "stunner", "work suit"),
    "Beta": ("knife", "work suit", "vacuum suit"),
    "Gamma": ("rivet gun", "cutting torch", "work suit", "vacuum suit"),
    "Delta": ("cutting torch", "exoskeleton knees", "rivet gun"),
    "Epsilon": ("stunner", "vacuum suit", "slug pistol"),
    "AsteroidBase": ("knife", "rivet gun", "vacuum suit"),
    "DeepSpaceOutpost": ("knife", "rivet gun"),
}
ORDERS = ("strike", "shoot", "grapple", "guard", "talk", "run", "pay")
ORDER_SKILL = {"strike": "gunner", "shoot": "gunner", "grapple": "loader", "run": "navigator"}
TROUBLE_BASE = 0.04         # the chance a turn that trouble finds a hand at an ordinary dock
TROUBLE_FROM = 6            # never before this turn
TROUBLE_GAP = 4             # turns between two fights the docks start
TROUBLE_TOP = 0.3
ROUGH = {"Gamma": 1.5, "Alpha": 0.5, "AsteroidBase": 1.5, "DeepSpaceOutpost": 1.5}
RICH = 3000                 # each this much in the purse makes trouble likelier (up to three times)
DOWN_TURNS = 2              # turns a downed hand loses, resting

HIT_LINES = ["Your blow lands.", "You catch them square.", "That one hurt them."]
MISS_LINES = ["You miss.", "They see it coming.", "Your blow goes wide."]
THEIR_HIT = ["They hit you.", "A blow you never saw.", "They land one on you."]
THEIR_MISS = ["Their blow goes past your ear.", "They miss.", "You take it on the arm, and it holds."]


def marks_word(left, total):
    if left >= total:
        return "fresh"
    if left <= 0:
        return "beaten"
    return "hurt" if left > total / 2.0 else "staggering"


class BrawlMixin:
    """The Game's fights on foot and the outfitter. Game inherits it (game/world.py)."""

    # -- gear ------------------------------------------------------------------------------------
    def gear_best(self, kind):
        """The best piece of this kind the captain carries, or None."""
        owned = [g for g in self.person.gear if g in GEAR and GEAR[g]["kind"] == kind]
        if not owned:
            return None
        key = (lambda g: GEAR[g].get("soak", 0)) if kind == "armour" else (lambda g: (GEAR[g].get("bonus", 0), GEAR[g]["price"]))
        return max(owned, key=key)

    def outfitter_here(self):
        here = self.current_location
        if here is None:
            return ()
        return OUTFITTERS.get(here.name) or OUTFITTERS.get(here.location_type, ())

    def gear_price(self, name):
        """The outfitter's price: dearer for every piece the hand carries already (game/prices.py)."""
        return curve(GEAR[name]["price"], 1, len([g for g in self.person.gear if g in GEAR]))

    def buy_gear(self, name):
        person = self.person
        item = GEAR[name]
        price = self.gear_price(name)
        if name in person.gear:
            self.display_simple_message("You already have %s." % self.gear_name(name), 1)
            return False
        if person.money < price:
            self.display_simple_message("%s costs %s; you have %s." % (
                self.gear_name(name, True), self.format_money(price), self.format_money(int(person.money))), 1)
            return False
        if person.gear:
            paid_dearer(self, "gear")
        person.money -= price
        person.gear.append(name)
        self.display_simple_message("You buy %s: %s." % (self.gear_name(name), item["words"]), 1, color='32')
        return True

    def gear_name(self, name, capital=False):
        word = ("an " if name[0] in "aeiou" else "a ") + name if not name.endswith(("knees",)) else name
        return word[0].upper() + word[1:] if capital else word

    def handle_gear(self):
        person = self.person
        sold = self.outfitter_here()
        rows = [["The outfitter"], [""]]
        for line in self.word_wrap("What a hand fights with on foot. You carry the best of each kind into a fight."):
            rows.append([line])
        rows.append([""])
        for number, name in enumerate(sold, 1):
            item = GEAR[name]
            mark = " (yours)" if name in person.gear else ""
            for line in self.option_lines(number, "%s, %s%s: %s" % (
                    name.capitalize(), self.format_money(self.gear_price(name)), mark, item["words"])):
                rows.append([line])
        if not sold:
            rows.append(["Nobody here sells gear."])
        rows.append([""])
        rows.extend([line] for line in self.word_wrap("Yours: %s." % (", ".join(person.gear) if person.gear else "nothing")))
        if person.gear and sold:
            rows.extend([[""]] + [[line] for line in self.word_wrap(price_note("gear"))])
        print(self.create_box(rows, 'round'))
        if not sold:
            return
        answer = self.validate_input("Buy which (1-%d, Enter to leave): " % len(sold),
                                     [str(i) for i in range(1, len(sold) + 1)])
        if answer is None:
            return
        if self.buy_gear(sold[int(answer) - 1]):
            self.autosave()

    # -- the odds --------------------------------------------------------------------------------
    def talk_skill(self, foe):
        person = self.person
        if foe.get("talk_skill"):
            return foe["talk_skill"]
        return "steward" if person.skill("steward") >= person.skill("broker") else "broker"

    def brawl_odds(self, order, foe_id, state):
        """The chance an order works this round (pay always does)."""
        foe = FOES[foe_id]
        person = self.person
        hurt = person.wounds / 250.0
        edge = 0.05 * state.get("edge", 0)
        read = 0.15 if state.get("read") else 0.0
        if order == "pay":
            return 1.0
        if order == "guard":
            return 1.0
        if order == "strike":
            weapon = self.gear_best("melee")
            chance = 0.45 + 0.07 * person.skill("gunner") + (GEAR[weapon]["bonus"] if weapon else 0) + read
        elif order == "shoot":
            weapon = self.gear_best("ranged")
            chance = 0.40 + 0.09 * person.skill("gunner") + (GEAR[weapon]["bonus"] if weapon else 0) + read
        elif order == "grapple":
            knees = self.gear_best("knees")
            chance = 0.40 + 0.09 * person.skill("loader") + (GEAR[knees]["grapple"] if knees else 0) + read
        elif order == "talk":
            if foe.get("talk") is None:
                return 0.0
            hurt_them = foe["marks"] - state.get("marks", foe["marks"])
            chance = foe["talk"] + 0.07 * person.skill(self.talk_skill(foe)) + 0.08 * hurt_them
            if foe_id == "mandate_troopers" and "slug pistol" in person.gear:
                chance -= 0.15
            return max(0.05, min(0.95, chance - hurt))
        elif order == "run":
            knees = self.gear_best("knees")
            chance = (0.40 + 0.08 * person.skill("navigator") + (GEAR[knees]["run"] if knees else 0)
                      - (0.15 if foe.get("armed") else 0) - person.wounds / 200.0)
            return max(0.05, min(0.95, chance + edge))
        else:
            return 0.0
        return max(0.05, min(0.95, chance - 0.08 * foe["skill"] - hurt + edge))

    def foe_hit_chance(self, foe_id, state, order, free=False):
        """The chance their blow lands this round."""
        foe = FOES[foe_id]
        armour = self.gear_best("armour")
        chance = 0.30 + 0.07 * foe["skill"] - (GEAR[armour].get("dodge", 0) if armour else 0)
        if order == "guard":
            chance -= 0.2
        if order == "shoot" and not foe.get("armed"):
            chance -= 0.1                   # you keep your distance
        if free:
            chance += 0.15                  # a failed talk or run: they get a free one
        chance -= 0.03 * state.get("edge", 0)
        return max(0.05, min(0.9, chance))

    def brawl_toll(self, foe):
        """What they take: their share of the purse, at least their toll, at most their most."""
        want = max(foe.get("toll", 0), int(self.person.money * foe.get("robs", 0)))
        return max(0, min(int(self.person.money), want, foe.get("most", want)))

    def brawl_options(self, foe_id, state):
        foe = FOES[foe_id]
        person = self.person
        options = []
        melee = self.gear_best("melee")
        options.append(("strike", "Strike%s (%s)" % (" with your " + melee if melee else "",
                                                   self.odds_word(self.brawl_odds("strike", foe_id, state)))))
        ranged = self.gear_best("ranged")
        if ranged:
            options.append(("shoot", "Shoot with your %s (%s)" % (ranged, self.odds_word(self.brawl_odds("shoot", foe_id, state)))))
        options.append(("grapple", "Grapple and hold (%s)" % self.odds_word(
            self.brawl_odds("grapple", foe_id, state))))
        options.append(("guard", "Guard: your next blow is likelier"))
        if foe.get("talk") is not None:
            options.append(("talk", "Talk them down, as a %s (%s)" % (self.talk_skill(foe), self.odds_word(
                self.brawl_odds("talk", foe_id, state)))))
        options.append(("run", "Run (%s)" % self.odds_word(self.brawl_odds("run", foe_id, state))))
        if foe.get("robs") and person.money > 0:
            options.append(("pay", "Pay them %s" % self.format_money(self.brawl_toll(foe))))
        return options

    def odds_word(self, chance):
        return odds_word(chance)

    # -- the fight -------------------------------------------------------------------------------
    def brawl(self, foe_id, edge=0, lines=None, rolls=None):
        """A fight on foot. Returns 'won', 'talked', 'ran', 'paid', 'robbed', 'carried', 'saved'
        or 'dead'. `rolls` (tests) are used in turn for every chance before random ones."""
        foe = FOES[foe_id]
        person = self.person
        rolls = list(rolls or [])

        def roll():
            return rolls.pop(0) if rolls else random.random()

        state = {"marks": foe["marks"], "read": False, "edge": edge, "round": 0}
        practised = set()
        story = list(lines) if lines else [random.choice(foe["start"])]
        if foe.get("lethal"):
            story.append("They mean to kill.")
        outcome = None
        while outcome is None:
            state["round"] += 1
            options = self.brawl_options(foe_id, state)
            title = "%s, round %d" % (foe["name"][0].upper() + foe["name"][1:], state["round"])
            status = "Them: %s. You: %s (wounds %d%%)." % (marks_word(state["marks"], foe["marks"]),
                                                           _hand.wound_word(person.wounds), person.wounds)
            self.brawl_foe = foe_id         # for a reader of the screen (tools/bot.py)
            move = self.ask_move(title, story + ([""] if story else []) + [status], options, 1)
            story = []
            chance = self.brawl_odds(move, foe_id, state)
            free, blocked = False, False
            if move == "pay":
                toll = self.brawl_toll(foe)
                person.money -= toll
                story.append("You pay %s. They count it twice and go." % self.format_money(toll))
                outcome = "paid"
                break
            if move in ("talk", "run"):
                if roll() < chance:
                    skill = self.talk_skill(foe) if move == "talk" else "navigator"
                    practised.add(skill)
                    story.append(foe.get("talked", "They let you go.") if move == "talk"
                                 else "You run, and they do not follow far.")
                    outcome = "talked" if move == "talk" else "ran"
                    break
                story.append("They are not listening." if move == "talk" else "They cut you off.")
                free = True
            elif move == "guard":
                state["read"] = True
                story.append("You cover up and watch how they move.")
            else:
                state["read"] = False
                if roll() < chance:
                    weapon = self.gear_best("melee" if move == "strike" else "ranged") if move != "grapple" else None
                    take = 2 if weapon and GEAR[weapon].get("heavy") else 1
                    state["marks"] -= take
                    practised.add(ORDER_SKILL[move])
                    if move == "grapple":
                        story.append("You get them in a hold and put them down on the deck.")
                        blocked = True
                    else:
                        story.append(random.choice(HIT_LINES))
                    if weapon and GEAR[weapon].get("stun"):
                        story.append("The stunner locks them up for a moment.")
                        blocked = True
                    sfx("round_won")
                else:
                    story.append(random.choice(MISS_LINES))
                    sfx("miss")
            if state["marks"] <= 0:
                outcome = "won"
                break
            if blocked:
                continue
            if roll() < self.foe_hit_chance(foe_id, state, move, free):
                armour = self.gear_best("armour")
                harm = max(2, random.randint(*foe["harm"]) - (GEAR[armour]["soak"] if armour else 0))
                harm = min(harm, WOUNDS_DOWN - person.wounds)
                person.wounds += harm
                story.append("%s Wounds +%d%%." % (random.choice(THEIR_HIT), harm))
                sfx("round_lost")
                if person.wounds >= WOUNDS_DOWN:
                    outcome, more = self.brawl_down(foe_id, roll)
                    story.extend(more)
                    break
            else:
                story.append(random.choice(THEIR_MISS))
        self.brawl_foe = None
        return self.brawl_end(foe_id, outcome, story, practised)

    def brawl_down(self, foe_id, roll):
        """The captain is down: what they do with you. Returns (outcome, lines)."""
        foe = FOES[foe_id]
        person = self.person
        lines = ["You go down."]
        if foe.get("lethal") and roll() < foe["lethal"]:
            person.wounds = WOUNDS_DEAD
            return "dead", lines + [foe.get("kill", "They make sure of it.")]
        if foe.get("carry"):
            fine = min(int(person.money), foe.get("fine", 0))
            person.money -= fine
            lines.append(foe.get("carried", "They carry you off."))
            if fine:
                lines.append("Fined %s." % self.format_money(fine))
            if foe_id == "mandate_troopers" and "slug pistol" in person.gear:
                person.gear.remove("slug pistol")
                lines.append("They keep your slug pistol.")
            return "carried", lines
        if foe.get("robs"):
            take = self.brawl_toll(foe)
            person.money -= take
            lines.append("You wake up in a gangway with your pockets inside out%s." % (
                ": %s gone" % self.format_money(take) if take else ""))
            weapons = [g for g in person.gear if GEAR.get(g, {}).get("kind") in ("melee", "ranged")]
            if weapons and roll() < 0.3:
                lost = max(weapons, key=lambda g: GEAR[g]["price"])
                person.gear.remove(lost)
                lines.append("They took your %s too." % lost)
            return "robbed", lines
        lines.append(foe.get("saved", "Someone drags you clear."))
        return "saved", lines

    def brawl_end(self, foe_id, outcome, story, practised):
        foe = FOES[foe_id]
        person = self.person
        counts = self.brawl_counts()
        counts[outcome] = counts.get(outcome, 0) + 1
        states = self.story_manager.story_states
        states["fight_%s_%s" % ("lost" if outcome in ("robbed", "carried", "saved", "dead") else outcome, foe_id)] = True
        lines = list(story)
        if outcome == "won":
            sfx("fight_won")
            lines.append(foe.get("won", "They are beaten."))
            loot = random.randint(*foe["loot"]) if foe.get("loot", (0, 0))[1] else 0
            if loot:
                person.money += loot
                lines.append("You find %s on them." % self.format_money(loot))
            points = 1 + foe.get("plot", 0)
            self.story_manager.plot_points += points
            lines.append("Plot points +%d." % points)
        if outcome != "dead":
            for skill in sorted(practised):
                risen = person.train(skill, 1)
                if risen:
                    lines.append("%s: now %s." % (skill.capitalize(), skill_word(risen)))
        self.display_story_message(self.fight_box(foe, lines), pause=1)
        self.last_brawl = self.turn
        if outcome in ("robbed", "carried", "saved"):
            self.pass_turns(DOWN_TURNS, resting=True)
        return outcome

    def fight_box(self, foe, lines):
        box = [foe["name"][0].upper() + foe["name"][1:], ""]
        for line in lines:
            box.extend(self.word_wrap(line))
        return box

    def brawl_counts(self):
        counts = self.__dict__.setdefault("brawls", {})
        if not isinstance(counts, dict):
            counts = self.brawls = {}
        return counts

    # -- trouble at the docks ----------------------------------------------------------------------
    def trouble_foes(self):
        """Who could come for a hand at this dock now: [(foe, weight)]."""
        here = self.current_location
        pool = []
        for fid, foe in FOES.items():
            if foe.get("labour"):
                if self.labour_left(foe["labour"]) > 0:
                    pool.append((fid, 4))
                continue
            if not foe.get("weight"):
                continue
            if foe.get("places") or foe.get("types"):
                if here.name not in foe.get("places", ()) and here.location_type not in foe.get("types", ()):
                    continue
            pool.append((fid, foe["weight"]))
        return pool

    def trouble_chance(self):
        here = self.current_location
        if here is None or self.turn < TROUBLE_FROM:
            return 0.0
        last = getattr(self, "last_brawl", None)
        if isinstance(last, int) and self.turn - last < TROUBLE_GAP:
            return 0.0
        chance = TROUBLE_BASE * ROUGH.get(here.name, ROUGH.get(here.location_type, 1.0))
        chance *= 1 + min(2.0, max(0, self.person.money) / float(RICH))
        if any(FOES[fid].get("labour") for fid, _ in self.trouble_foes()):
            chance += 0.06
        return min(TROUBLE_TOP, chance)

    def dock_trouble(self, roll=None):
        """Maybe trouble finds the hand here this turn. Returns the fight's outcome, or None."""
        roll = random.random() if roll is None else roll
        if roll >= self.trouble_chance():
            return None
        pool = self.trouble_foes()
        if not pool:
            return None
        total = sum(w for _, w in pool)
        pick = random.random() * total
        for fid, weight in pool:
            pick -= weight
            if pick < 0:
                break
        outcome = self.brawl(fid)
        self.autosave()
        return outcome


# The game's other modules, imported last so that the modules can refer to each other.
from .encounters import odds_word  # noqa: E402
from . import hand as _hand  # noqa: E402  (the hand may be importing this module)
from .person import WOUNDS_DEAD, WOUNDS_DOWN, skill_word  # noqa: E402
from .sound import sfx  # noqa: E402
from .prices import curve, paid_dearer, price_note  # noqa: E402
