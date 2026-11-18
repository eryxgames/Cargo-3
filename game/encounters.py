"""Between docks: who stops a ship (ENEMIES), what the captain can do about it, and the situations
(SITUATIONS)."""
import random

# --- encounters: who stops a ship between docks, and what the captain can do about it ---
# power: how hard they hit and how hard they are to beat (1-7); speed: how hard they are
# to outrun; kind: what a victory counts as; deal: "pay" (they take money to leave),
# "talk" (reputation can talk them down), "toll" (customs: pay a fee or show a clean scan).
# tricks: equipment and crew that work especially well against them.
ENEMIES = {
    "skiff": {"name": "Scrap skiff", "kind": "pirate", "power": 1, "speed": 2, "deal": "pay",
              "text": "A scavenger skiff with a harpoon gun and big ideas. Its pilot is about fifteen."},
    "raider": {"name": "Pirate raider", "kind": "pirate", "power": 2, "speed": 3, "deal": "pay",
               "text": "A cut-down hauler with guns welded where the cargo doors used to be."},
    "drones": {"name": "Feral mining drones", "kind": "machine", "power": 2, "speed": 4, "deal": None,
               "tricks": ["turrets", "mining_laser"],
               "text": "A swarm of cutting drones that lost their mine and kept the habit. Your hull looks like ore to them."},
    "corsair": {"name": "Corsair wing", "kind": "pirate", "power": 3, "speed": 5, "deal": "pay",
                "tricks": ["advanced_radar"],
                "text": "Three light fighters in a tight wedge. Too fast to outrun, too proud to miss."},
    "harvester": {"name": "Runaway harvester", "kind": "machine", "power": 3, "speed": 1, "deal": None,
                  "tricks": ["mining_laser", "quantum_scanner"],
                  "text": "A forty-metre agrobot harvester, off its leash and sure that your hold is a field."},
    "customs": {"name": "Customs cutter", "kind": "militia", "power": 3, "speed": 4, "deal": "toll",
                "text": "A customs cutter flashes its lights: stop for inspection. Inspection has a fee."},
    "cultists": {"name": "Cult boarding party", "kind": "raider", "power": 3, "speed": 2, "deal": "talk",
                 "text": "The Cult of the Broken Machine wants to inspect your ship for holiness. They brought cutting torches."},
    "militia": {"name": "Toll militia", "kind": "militia", "power": 4, "speed": 4, "deal": "pay",
                "text": "A local militia has declared this lane a toll road. The toll is whatever they think you carry."},
    "deserters": {"name": "Legion deserters", "kind": "raider", "power": 4, "speed": 3, "deal": "talk",
                  "tricks": ["advanced_radar"],
                  "text": "A legion gunboat with the corporate logo burned off. The crew left the legion; the training stayed."},
    "mothership": {"name": "Pirate mothership", "kind": "pirate", "power": 5, "speed": 2, "deal": "pay",
                   "tricks": ["quantum_scanner", "combat_drone"],
                   "text": "A converted ore carrier with a pirate flotilla in its belly. It is in no hurry. Neither are you, now."},
    "warship": {"name": "Rogue warship", "kind": "raider", "power": 6, "speed": 3, "deal": "talk",
                "tricks": ["quantum_scanner", "advanced_radar"],
                "text": "A frigate nobody admits to having lost. Its captain sends a polite request to surrender."},
    "cargolytes": {"name": "Cargolyte stevedores", "kind": "raider", "power": 4, "speed": 3, "deal": "tithe",
                   "after": "met_cargolytes",
                   "text": "A Cargolyte boarding party, singing, with cutting torches and a copy of your manifest they should not have. 'In apparent good order and condition,' says the one in front. They have come to receive the Sender's cargo. Yours."},
    "rootstock": {"name": "Rootstock enforcers", "kind": "smuggler", "power": 4, "speed": 5, "deal": "pay",
                  "after": "met_rootstock",
                  "text": "A fast cutter with no transponder and very good paint comes alongside. The androids aboard wear good suits and no expressions. One of them speaks, quietly: the family would like a word, and a share."},
    "dreadnought": {"name": "Pirate dreadnought", "kind": "pirate", "power": 7, "speed": 2, "deal": "pay",
                    "tricks": ["quantum_scanner", "combat_drone"],
                    "text": "Three motherships welded together and called a fleet. Every pirate on the frontier pays it a share."},
}

# Gear and crew that change a fight: a line for the menu, and what it does
FIGHT_TRICKS = {
    "advanced_radar": ("Radar: jam their targeting", {"edge": 2}),
    "combat_drone": ("Drone: send it in first", {"edge": 2, "shield": 0.5}),
    "mining_laser": ("Mining laser: cut them up", {"edge": 3}),
    "quantum_scanner": ("Quantum scanner: find the weak spot", {"edge": 2}),
    "turrets": ("Turrets: fire first", {"edge": 2}),
}


def odds_word(chance):
    return ("long odds" if chance < 0.35 else "even odds" if chance < 0.6
            else "good odds" if chance < 0.85 else "easy")


# --- situations: moments between docks where the right gear, crew or nerve pays off ---
# Each option: say (the menu line), needs (items / crew / cargo the option requires;
# "any" means one of them), and an outcome: a dict of effects with a line of text, or
# {"chance": p, "win": {...}, "lose": {...}}.  Effects: money, damage, rp (research),
# pp (plot points), rep (passenger reputation), cargo (good: amount, or "any": amount),
# fight (an enemy id), tier (scale money by the danger level).  "{x}" names crew.
SITUATIONS = {
    "distress": {
        "title": "Distress beacon",
        "text": "A distress beacon, two light-minutes off your course. A life pod or bait: the signal looks the same.",
        "options": [
            {"say": "Scan it before you go in", "needs": {"any": ["advanced_radar", "scanner", "cargo_scanner"]},
             "do": {"chance": 0.6, "win": {"say": "Real survivors: four miners in a pod built for two. The shipping line pays a finder's fee.",
                                           "money": 600, "tier": True, "rep": 4, "pp": 4},
                    "lose": {"say": "The scan shows weapons warm behind the beacon. You log it for the militia and fly on.",
                             "rp": 10, "pp": 1}}},
            {"say": "Answer the call",
             "do": {"chance": 0.6, "win": {"say": "Real survivors: four miners in a pod built for two. The shipping line pays a finder's fee.",
                                           "money": 600, "tier": True, "rep": 4, "pp": 4},
                    "lose": {"say": "It was bait.", "fight": "raider"}}},
            {"say": "Fly on", "do": {"say": "The beacon fades behind you. Somebody else's problem, or somebody else's trap."}},
        ]},
    "derelict": {
        "title": "Derelict hauler",
        "text": "A hauler drifts with its lights off and its bay doors welded shut. No answer on any channel.",
        "options": [
            {"say": "Cut the bay open with the mining laser", "needs": {"items": ["mining_laser"]},
             "do": {"say": "The doors fall away in one piece. Most of the cargo is still there.",
                    "cargo": {"any": 60}, "rp": 5, "pp": 2}},
            {"say": "Read its log (quantum scanner)", "needs": {"items": ["quantum_scanner"]},
             "do": {"say": "The log covers forty years of routes, including three nobody uses now. The research colonies will want this.",
                    "rp": 35, "pp": 3}},
            {"say": "Board it",
             "do": {"chance": 0.55, "win": {"say": "You squeeze through a maintenance hatch and pass crates out by hand.",
                                            "cargo": {"any": 25}, "pp": 1},
                    "lose": {"say": "The airlock was rigged. Whoever welded those doors meant it.", "damage": 10}}},
            {"say": "Report it to the registry", "do": {"say": "The registry thanks you and pays a small salvage notice fee.",
                                                         "money": 200, "rep": 2}},
        ]},
    "ion_storm": {
        "title": "Ion storm",
        "text": "An ion storm sits across the lane like a bad mood. The navigation computer suggests prayer.",
        "options": [
            {"say": "Raise shields and ride it out", "needs": {"any": ["shield", "shield_booster"]},
             "do": {"say": "The shields glow and complain, and hold.", "damage": 3, "rp": 8}},
            {"say": "Let {navigator.short} find a gap", "needs": {"crew": ["navigator"]},
             "do": {"say": "{navigator.short} reads the storm like weather on a farm drum and finds a lane through it.", "rp": 12, "pp": 1}},
            {"say": "Emergency jump clear", "needs": {"items": ["emergency_warp"]},
             "do": {"say": "One lurch, one headache, and the storm is behind you.", "damage": 2}},
            {"say": "Ride it out", "do": {"say": "Every panel on the bridge lights up at once.", "damage": 18, "rp": 8}},
            {"say": "Go around (extra fuel)", "do": {"say": "The long way round costs fuel and a day.", "money": -150, "tier": True}},
        ]},
    "debris": {
        "title": "Debris field",
        "text": "Debris from an old collision, spread thin and moving fast. Some of it is worth money. The navigation computer works out the odds of getting through and decides not to share them.",
        "options": [
            {"say": "Shoot a path with the turrets", "needs": {"items": ["turrets"]},
             "do": {"say": "The turrets turn the worst of it to gravel. You scoop the rest.", "cargo": {"salt": 30}, "pp": 1}},
            {"say": "Cut and scoop with the mining laser", "needs": {"items": ["mining_laser"]},
             "do": {"say": "You cut the big pieces down and scoop the ore.", "cargo": {"salt": 40, "fuel": 15}, "pp": 1}},
            {"say": "Send the probe ahead", "needs": {"items": ["probe"]},
             "do": {"say": "The probe maps a clear line through. It also maps where the debris came from.", "rp": 15}},
            {"say": "Thread it slowly",
             "do": {"chance": 0.5, "win": {"say": "Slow and careful works. Only paint lost.", "damage": 2},
                    "lose": {"say": "Something the size of a fridge finds you.", "damage": 12}}},
        ]},
    "cargo_pod": {
        "title": "Loose cargo pod",
        "text": "A cargo pod tumbles past, beacon dead, owner unknown. Salvage law says finders keepers, mostly.",
        "options": [
            {"say": "Let {loader} grab it", "needs": {"crew": ["loader"]},
             "do": {"say": "{loader} catches the pod one-handed and stacks it before you finish the sentence.",
                    "cargo": {"any": 50}, "pp": 1}},
            {"say": "Grab it", "do": {"say": "It takes an hour and a lot of swearing to get it in the hold.", "cargo": {"any": 25}}},
            {"say": "Log it and leave it", "do": {"say": "You log the pod for its owner. Someone, somewhere, owes you a drink.", "rep": 1}},
        ]},
    "fluencer": {
        "title": "Yacht alongside",
        "text": "A yacht wrapped in screens pulls alongside. Somebody's heir, or somebody saying so, wants to stream your ship for her followers.",
        "options": [
            {"say": "Let {steward} handle her", "needs": {"crew": ["steward"]},
             "do": {"say": "{steward} serves tea on camera and corrects her grammar. The stream loves him. So do the sponsors.",
                    "money": 800, "rep": 5, "pp": 2}},
            {"say": "Pose for the stream",
             "do": {"chance": 0.65, "win": {"say": "Nine minutes of your best side. A paint company sends a sponsorship.",
                                            "money": 500, "rep": 3, "pp": 1},
                    "lose": {"say": "She also streams your cargo manifest. Three pirates subscribe.", "rep": -2}}},
            {"say": "Close the shutters", "do": {"say": "The yacht films your shutters for a while and leaves."}},
        ]},
    "stowaway": {
        "title": "Stowaway",
        "text": "Your hold has one more person in it than the manifest. She says she is a welder. She is holding a welder.",
        "options": [
            {"say": "{steward} finds her a bunk", "needs": {"crew": ["steward"]},
             "do": {"say": "{steward} finds her a bunk and a job list. She fixes three things before the next dock.",
                    "damage": -8, "rep": 2, "pp": 2}},
            {"say": "Let her work her fare",
             "do": {"say": "She welds what needs welding and leaves at the next dock with a reference.", "damage": -5, "rep": 1}},
            {"say": "Hand her to customs", "do": {"say": "Customs pays a small fee. The dock talks about it for a week.",
                                                 "money": 300, "rep": -3}},
        ]},
    "comet": {
        "title": "Comet tail",
        "text": "A comet's tail crosses the lane: ice, dust and free volatiles for anyone with the gear.",
        "options": [
            {"say": "Skim it with the compressor", "needs": {"items": ["mining_compressor"]},
             "do": {"say": "The compressor drinks the tail. The fuel tanks fill without a single invoice.", "cargo": {"fuel": 60}, "pp": 1}},
            {"say": "Skim it anyway",
             "do": {"chance": 0.6, "win": {"say": "A good haul of ice, and only a few new dents.", "cargo": {"fuel": 20}, "damage": 3},
                    "lose": {"say": "A rock hidden in the ice hits the scoop.", "cargo": {"fuel": 8}, "damage": 10}}},
            {"say": "Keep clear", "do": {"say": "You watch it go. It is very pretty, and very free."}},
        ]},
    "buoy": {
        "title": "Old buoy",
        "text": "An old navigation buoy keeps broadcasting a route that closed forty years ago, in a voice from a dead shipping line.",
        "options": [
            {"say": "Decode its archive", "needs": {"any": ["quantum_scanner", "data_analyzer", "research_module"]},
             "do": {"say": "The archive holds survey data nobody bothered to copy. The colonies will pay in attention.",
                    "rp": 30, "pp": 3}},
            {"say": "Note the coordinates", "do": {"say": "You note them down. One day they may mean something.", "rp": 6}},
        ]},
    "flare": {
        "title": "Flare warning",
        "text": "Your star tracker warns of a flare in nine minutes.",
        "options": [
            {"say": "Raise shields", "needs": {"any": ["shield", "shield_booster"]},
             "do": {"say": "The shields take the flare. The instruments take notes.", "rp": 8}},
            {"say": "Shelter behind a moon", "do": {"say": "You lose half a day behind a moon, and gain a nice view.", "money": -100, "tier": True}},
            {"say": "Push on", "do": {"chance": 0.5, "win": {"say": "The flare misses. Mostly.", "damage": 3},
                                      "lose": {"say": "The flare does not miss.", "damage": 15}}},
        ]},
    "tow": {
        "title": "Barge in trouble",
        "text": "A broken-down ore barge asks for a tow to the nearest dock. Its crew offers money and soup.",
        "options": [
            {"say": "Let {loader} rig the tow", "needs": {"crew": ["loader"]},
             "do": {"say": "{loader} rigs the tow in ten minutes. The barge crew asks if it is for sale. It is not.",
                    "money": 700, "tier": True, "rep": 3, "pp": 2}},
            {"say": "Tow it", "do": {"say": "A slow trip, good soup, and a fair fee at the dock.", "money": 400, "tier": True, "rep": 2, "pp": 1}},
            {"say": "Pass by", "do": {"say": "The barge crew says nothing on the channel, which says plenty."}},
        ]},
    "breakdown": {
        "title": "Reactor hiccup",
        "text": "The reactor coughs, the lights dim, and something in the engine room makes a noise you have not heard before.",
        "options": [
            {"say": "Follow the ship's bugrat to the leak", "needs": {"flags": ["ship_bugrat"]},
             "do": {"say": "The bugrat sits on the cracked coupling and looks at you until you fix it.", "damage": -8, "pp": 1}},
            {"say": "Let {mechanic.short} have a look", "needs": {"crew": ["mechanic"]},
             "do": {"say": "{mechanic.short} finds a cracked coupling, swears at it, and fixes two other things while she is there.",
                    "damage": -10, "pp": 1}},
            {"say": "Run the repair bot", "needs": {"items": ["repair_bot"]},
             "do": {"say": "The repair bot crawls into the engine and comes out pleased with itself.", "damage": -5}},
            {"say": "Hit it until it stops", "do": {"chance": 0.5, "win": {"say": "It stops. You decide not to ask why."},
                                                    "lose": {"say": "It stops, and so does the port thruster.", "damage": 8}}},
        ]},
}


class EncountersMixin:
    """The Game's fights, bounties and situations. Game inherits it (game/world.py)."""
    # --- encounters: fights, bounties and situations between docks ------------------
    WANTED_NAMES = ["Lucky Nine", "Widow's Tax", "Second Opinion", "Unpaid Invoice", "Small Print",
                    "Overdraft", "Bad Penny", "Quiet Word", "Last Orders", "Due Diligence", "Rust Never",
                    "Grandmother's Revenge", "Fine Print", "Late Fee", "No Refunds", "Sunday Best"]

    def wealth_tier(self):
        """0-3: how much the lanes have heard this captain is worth."""
        money = self.ship.money
        return 3 if money >= 2000000 else 2 if money >= 500000 else 1 if money >= 100000 else 0

    def danger_tier(self):
        """How dangerous the lanes are for this captain (1-7): it grows with time, guns and
        money (pirates read bank gossip too), and with the difficulty."""
        tier = 1 + self.turn // 50 + self.ship.fight_attack() // 3 + self.wealth_tier() + (self.difficulty - 1)
        return max(1, min(7, tier))

    def fight_chance(self, power, edge=0):
        chance = 0.55 + 0.12 * (self.ship.fight_attack() + edge - power)
        if self.ship.items.get("turrets"):
            chance += 0.08
        return max(0.08, min(0.95, chance))

    def escape_chance(self, enemy):
        chance = 0.4 + 0.1 * (self.ship.speed + (2 if self.ship.items.get("quantum_drive") else 0) - enemy["speed"])
        if "navigator" in self.ship.crew:
            chance += 0.15
        return max(0.05, min(0.95, chance))

    def pick_enemy(self, power=None):
        """An enemy for this place and moment: near the danger tier, or of the given power."""
        if power is None:
            tier = self.danger_tier()
            pool = [e for e, d in ENEMIES.items() if tier - 2 <= d["power"] <= tier]
        else:
            pool = [e for e, d in ENEMIES.items() if d["power"] == power and d["deal"] != "toll"]
        pool = [e for e in pool if not ENEMIES[e].get("after") or self.story_flag(ENEMIES[e]["after"])]
        return random.choice(pool or ["skiff"])

    def crew_name(self, role):
        person = story_data()["characters"].get(role) or {}
        return person.get("short") or person.get("name") or role

    def ask_move(self, title, lines, options, default):
        """Show a moment and its options; return the key of the option taken."""
        box = [title, ""]
        for line in lines:
            box.extend(self.word_wrap(line))
        box.append("")
        for number, (_key, label) in enumerate(options, 1):
            box.extend(self.option_lines(number, label))
        self.display_story_message(box, pause=0)
        self.move_options, self.move_title = options, title   # what a reader of the screen sees (tools/bot.py)
        answer = self.validate_input("Your move (1-%d, Enter = %d): " % (len(options), default),
                                     [str(i) for i in range(1, len(options) + 1)])
        self.move_options = None
        return options[int(answer or default) - 1][0]

    # Friends who come when called: (story flag, character, edge in the fight, turns between calls)
    ALLIES = {"convoy": ("convoy_friend", "convoy_captain", 3, 15), "pell": ("pell_friend", "young_hauler", 1, 8)}

    def encounter(self, enemy_id, bounty=0, hunted=False, edge=0):
        """A fight, or the threat of one. The captain picks how to meet it. `edge` is help the
        story brings (allies at a climax). Returns 'victory', 'defeat', 'escaped', 'paid' or 'talked'."""
        enemy = ENEMIES[enemy_id]
        ship = self.ship
        power = enemy["power"]
        if not hunted and not edge and self.waved_through(enemy["kind"]):
            self.display_simple_message("A %s hails you, reads your transponder, and waves you on: the Mandate "
                                        "knows your name." % enemy["name"].lower(), 2)
            return "talked"
        options = [("fight", "Fight (%s)" % odds_word(self.fight_chance(power, edge)))]
        used = self.__dict__.setdefault("allies_called", {})
        for ally, (flag, who, help_, every) in self.ALLIES.items():
            if self.story_flag(flag) and self.turn - used.get(ally, -10 ** 6) >= every:
                options.append(("ally:" + ally, "Call %s (%s)" % (
                    self.crew_name(who) + ("'s convoy" if ally == "convoy" else "'s skiff"),
                    odds_word(self.fight_chance(power, edge + help_)))))
        if not hunted and enemy["kind"] == "pirate" and power <= 5 and self.story_flag("mraz_spared", "mraz_protection"):
            options.append(("mraz", "Drop %s's name" % self.crew_name("pirate_captain")))
        if enemy_id == "cultists" and self.story_flag("carried_the_pilgrims"):
            options.append(("pilgrims", "The pilgrims you carried vouch for you"))
        if enemy_id == "customs" and self.story_flag("lauritz_trust", "lauritz_courier"):
            options.append(("lauritz", "%s vouches for you on the channel" % self.crew_name("inspector")))
        tricks = [t for t in FIGHT_TRICKS
                  if ship.items.get(t) and (t in enemy.get("tricks", []) or t in ("advanced_radar", "combat_drone"))]
        tricks.sort(key=lambda t: -FIGHT_TRICKS[t][1]["edge"])
        for trick in tricks[:2]:
            label, effect = FIGHT_TRICKS[trick]
            options.append(("trick:" + trick, "%s (%s)" % (label, odds_word(self.fight_chance(power, edge + effect["edge"])))))
        if enemy_id == "harvester" and ship.cargo["agri"] >= 10:
            options.append(("feed", "Throw it a crate of agri"))
        if enemy_id == "cultists" and ship.damage >= 25:
            options.append(("holy", "Show them your battered hull"))
        if not hunted:
            if enemy["deal"] in ("pay", "toll"):
                price = self.toll_for(enemy)
                options.append(("pay", "%s (%s)" % ("Pay the fee" if enemy["deal"] == "toll" else "Pay them off",
                                                    self.format_money(price))))
            if enemy["deal"] == "toll" and ship.items.get("cargo_scanner"):
                options.append(("scan", "Hand over a clean cargo scan"))
            if enemy["deal"] == "talk":
                options.append(("talk", "Talk them down (%s)" % odds_word(self.talk_chance())))
            if enemy["deal"] == "tithe" and any(ship.cargo.values()):
                options.append(("tithe", "Give them a container: a third of your fullest hold"))
            if ship.items.get("advanced_radar"):
                options.append(("slip", "Radar: slip away before they lock on"))
        if ship.items.get("emergency_warp"):
            options.append(("warp", "Emergency jump"))
        options.append(("run", "%s (%s)" % ("Break off" if hunted else "Run for it",
                                            odds_word(self.escape_chance(enemy)))))

        title = "%s (threat %d)" % (enemy["name"], power)
        if hunted:
            title = "Bounty: " + title
        lines = [enemy["text"]]
        if not hunted and self.wealth_tier() and enemy["deal"] in ("pay", "talk"):
            lines.append(random.choice(["They have heard what you are worth.",
                                        "Somebody sold them your bank balance. It was not cheap.",
                                        "Rich captains get the better class of pirate."]))
        move = self.ask_move(title, lines, options, 1)

        if move == "tithe":
            good = max(('tech', 'agri', 'salt', 'fuel'), key=lambda g: ship.cargo[g])
            taken = max(1, ship.cargo[good] // 3)
            ship.cargo[good] -= taken
            return self.after_fight("paid", ["Sister Tare weighs %d %s, subtracts the container, and gives you a receipt: "
                                             "'clean lading'. They go, singing." % (taken, good)], '33')
        if move == "mraz":
            return self.after_fight("talked", ["You mention %s. The channel goes quiet, then a voice says "
                                               "'Sorry, captain. Didn't see the name.' They leave." %
                                               self.crew_name("pirate_captain")], '32')
        if move == "pilgrims":
            return self.after_fight("talked", ["The cultists recognise the ship that carried their pilgrims. "
                                               "They bless your airlock and go."], '32')
        if move == "lauritz":
            return self.after_fight("talked", ["%s comes on the channel, reads out your inspection record, "
                                               "and the cutter waves you through." % self.crew_name("inspector")], '32')
        if move.startswith("ally:"):
            ally = move[5:]
            flag, who, help_, every = self.ALLIES[ally]
            used[ally] = self.turn
            text = ("Forty haulers come up the lane in close order, %s's tug at the front." if ally == "convoy"
                    else "%s's skiff cuts across their bow, guns hot.") % self.crew_name(who)
            return self.fight(enemy_id, bounty, [text], edge + help_)
        if move == "pay":
            price = self.toll_for(enemy)
            ship.money -= price
            return self.after_fight("paid", ["You pay %s. They take it and go." % self.format_money(price)], '33')
        if move == "scan":
            self.ship.passenger_reputation += 1
            return self.after_fight("talked", ["The cutter reads your scan, finds nothing to fine, and waves you on."], '32')
        if move == "talk":
            if random.random() < self.talk_chance():
                return self.after_fight("talked", ["Your reputation arrives before you do. They let you pass."], '32')
            return self.fight(enemy_id, bounty, ["They are not in a talking mood."], edge)
        if move == "feed":
            ship.cargo["agri"] -= 10
            return self.after_fight("talked", ["The harvester eats the crate, crate and all, and wanders off content."], '32')
        if move == "holy":
            ship.research_points += 10
            return self.after_fight("talked", ["The cultists see your hull and fall silent. They bless it, weld a "
                                               "tin medal to the airlock and leave. +10 RP"], '32')
        if move in ("slip", "warp"):
            if move == "warp":
                ship.damage = min(99, ship.damage + 3)
            text = "The radar saw them first: you are gone before they lock on." if move == "slip" \
                else "One lurch, one headache, and they are a long way behind you."
            return self.after_fight("escaped", [text], '32')
        if move == "run":
            if random.random() < self.escape_chance(enemy):
                return self.after_fight("escaped", ["You open the throttle and leave them behind."], '33')
            return self.fight(enemy_id, bounty, ["They catch you."], edge - 1)
        shield = 1.0
        if move.startswith("trick:"):
            effect = FIGHT_TRICKS[move[6:]][1]
            edge, shield = edge + effect["edge"], effect.get("shield", 1.0)
        return self.fight(enemy_id, bounty, [], edge, shield)

    def toll_for(self, enemy):
        """What they want to go away: a share of the money aboard, a bigger share from the rich."""
        share = (0.03 if enemy["deal"] == "toll" else 0.06) + 0.015 * self.wealth_tier()
        cap = 1500 * enemy["power"] * (1 + 2 * self.wealth_tier())
        return int(max(150 * enemy["power"], min(self.ship.money * share, cap)))

    def talk_chance(self):
        return max(0.1, min(0.9, 0.15 + self.ship.passenger_reputation / 120))

    def fight(self, enemy_id, bounty, lines, edge=0, shield=1.0):
        """Settle a fight: one roll against a small enemy, a convoy fight (game/tactics.py) against
        a bigger one."""
        enemy = ENEMIES[enemy_id]
        power = enemy["power"]
        if power >= TACTICAL_FROM:
            return self.convoy_fight(enemy_id, bounty, lines, edge, shield)
        won = random.random() < self.fight_chance(power, edge)
        hit = random.randint(4, 9) * power / self.ship.fight_defense() * (1 + self.difficulty) * shield
        if not won:
            hit *= 2.2
        return self.fight_result(enemy_id, bounty, lines, won, hit)

    def fight_result(self, enemy_id, bounty, lines, won, hit, prize=1.0):
        """What a fight leaves: damage (less with armour and a crew that patches), wear on the
        modules, and the winnings or the losses."""
        enemy = ENEMIES[enemy_id]
        ship = self.ship
        power = enemy["power"]
        if ship.items.get("shield"):
            hit *= 0.7
        if ship.items.get("armor"):
            hit *= 0.8
        before = ship.damage
        ship.damage = min(99, int(ship.damage + hit))
        if ship.items.get("patcher"):
            ship.damage = max(0, ship.damage - 10)
        if "mechanic" in ship.crew:
            ship.damage = max(0, ship.damage - 5)
        if ship.damage > before:
            lines.append("Hull damage +%d%%." % (ship.damage - before))
            worn = self.wear_modules(min(40, 2 * (ship.damage - before)))
            if worn and worn["condition"] > 0:
                lines.append("The %s took some of it (%s)." % (module_name(worn["kind"]).lower(),
                                                                condition_word(worn["condition"])))

        if won:
            ship.record_combat_victory(enemy["kind"])
            money = int(random.randint(150, 350) * power * prize) + bounty
            if ship.working("salvage"):
                salvage = int(random.randint(100, 300) * power)
                money += salvage
                lines.append("Debris retrieval brings in %s of salvage." % self.format_money(salvage))
            research = int(random.randint(4, 10) * power * (1 + ship.research_bonus()))
            plot = 1 + power // 3
            ship.money += money
            ship.research_points += research
            self.story_manager.plot_points += plot
            lines.append("Victory! +%s credits%s, +%d RP, +%d plot points." % (
                self.format_money(money), " (bounty included)" if bounty else "", research, plot))
            if enemy["kind"] == "machine":
                parts = min(ship.hold_room("tech"), random.randint(5, 12) * power)
                if parts > 0:
                    ship.cargo["tech"] += parts
                    lines.append("You salvage %d tech from the wreckage." % parts)
            if enemy["kind"] == "pirate":
                rep = random.randint(2, 4)
                self.reputation += rep
                ship.passenger_reputation += rep
                lines.append("Reputation +%d for clearing the lane." % rep)
            elif enemy_id == "customs":
                ship.passenger_reputation -= 3
                lines.append("You shot at customs. Reputation -3.")
            return self.after_fight("victory", lines, '32')

        ship.record_combat_defeat(enemy["kind"])
        # they take a tenth to a quarter, and four per cent more for each step of wealth
        share = random.uniform(0.10, 0.25) + 0.04 * self.wealth_tier()
        stolen = int(ship.money * share) if ship.money > 10 else 0
        stolen = min(stolen, 3000 * power * (1 + 3 * self.wealth_tier()))
        losses = []
        if stolen > 0:
            ship.money -= stolen
            losses.append("%s credits" % self.format_money(stolen))
        for good in ('tech', 'agri', 'salt', 'fuel'):
            if ship.cargo[good] > 0:
                taken = random.randint(1, max(1, ship.cargo[good] // 3))
                ship.cargo[good] -= taken
                losses.append("%d %s" % (taken, good))
        lines.append("Defeat." + (" They take " + ", ".join(losses) + "." if losses else ""))
        if enemy["kind"] == "pirate":
            rep = random.randint(1, 3)
            self.reputation = max(0, self.reputation - rep)
            ship.passenger_reputation -= rep
            lines.append("Reputation -%d." % rep)
        return self.after_fight("defeat", lines, '31')

    def after_fight(self, outcome, lines, color):
        self.last_fight = outcome
        self.display_simple_message([line for text in lines for line in self.word_wrap(text)], 3, color=color)
        return outcome

    def handle_combat_event(self, event=None):
        """Someone stops the ship between docks."""
        return self.encounter(event if event in ENEMIES else self.pick_enemy())

    def handle_hunt(self):
        """The bounty board: the legions and the docks pay for ships they want gone.
        Taking a bounty uses the turn. Returns True when a hunt was flown."""
        if getattr(self, "hunted_turn", None) == self.turn:
            self.display_simple_message("The board has nothing new until tomorrow.")
            return False
        tier = self.danger_tier()
        act = self.story_manager.get_chapter_number()
        targets = []
        for power in (tier - 1, tier, tier + 1):
            power = max(1, min(7, power))
            enemy_id = self.pick_enemy(power)
            bounty = int(power * 700 * (1 + 0.25 * act))
            targets.append((enemy_id, bounty, random.choice(self.WANTED_NAMES)))
        options = [("%d" % i, "%s '%s' - threat %d, bounty %s (%s)" % (
            ENEMIES[e]["name"], name, ENEMIES[e]["power"], self.format_money(b),
            odds_word(self.fight_chance(ENEMIES[e]["power"]))))
            for i, (e, b, name) in enumerate(targets)]
        options.append(("leave", "Not today"))
        pick = self.ask_move("Bounty board - " + self.current_location.name,
                             ["Wanted by the legions and the dock masters. Hunting one takes the day."],
                             options, len(options))
        if pick == "leave":
            return False
        enemy_id, bounty, _name = targets[int(pick)]
        self.hunted_turn = self.turn
        self.last_fight = None
        outcome = self.encounter(enemy_id, bounty=bounty, hunted=True)
        self.quest_system.check_event_requirements({"type": "combat", "name": ENEMIES[enemy_id]["name"],
                                                    "location": self.current_location.name, "turn": self.turn,
                                                    "outcome": outcome})
        return True

    def situation(self, sid=None):
        """A moment between docks where gear, crew or nerve pays off."""
        sid = sid or random.choice(sorted(SITUATIONS))
        moment = SITUATIONS[sid]
        offered = [opt for opt in moment["options"] if self.can_take(opt.get("needs"))]
        options = [(str(i), self.story.fill(opt["say"])) for i, opt in enumerate(offered)]
        pick = self.ask_move(moment["title"], [self.story.fill(moment["text"])], options, len(options))
        self.apply_outcome(offered[int(pick)]["do"])
        return sid

    def can_take(self, needs):
        if not needs:
            return True
        items = self.ship.items
        if any(not items.get(i) for i in needs.get("items", [])):
            return False
        if "any" in needs and not any(items.get(i) for i in needs["any"]):
            return False
        if any(role not in self.ship.crew for role in needs.get("crew", [])):
            return False
        if any(not self.story_flag(flag) for flag in needs.get("flags", [])):
            return False
        return True

    def apply_outcome(self, out):
        """Effects of a situation's choice: money, damage, research, plot points,
        reputation, cargo, or a fight."""
        if "chance" in out:
            out = out["win"] if random.random() < out["chance"] else out["lose"]
        ship = self.ship
        lines = [self.story.fill(out["say"])] if out.get("say") else []
        scale = self.danger_tier() if out.get("tier") else 1
        money = int(out.get("money", 0) * scale)
        if money:
            ship.money = max(0, ship.money + money)
            lines.append("%s%s credits" % ("+" if money > 0 else "-", self.format_money(abs(money))))
        if out.get("damage"):
            ship.damage = max(0, min(99, ship.damage + out["damage"]))
            lines.append("Hull %s %d%%" % ("damage +" if out["damage"] > 0 else "repaired", abs(out["damage"])))
        if out.get("rp"):
            rp = int(out["rp"] * (1 + ship.research_bonus()))
            ship.research_points += rp
            lines.append("+%d RP" % rp)
        if out.get("pp"):
            self.story_manager.plot_points += out["pp"]
            lines.append("+%d plot points" % out["pp"])
        if out.get("rep"):
            ship.passenger_reputation += out["rep"]
            lines.append("Reputation %+d" % out["rep"])
        for good, amount in (out.get("cargo") or {}).items():
            if good == "any":
                good = random.choice(['tech', 'agri', 'salt', 'fuel'])
            amount = min(int(amount * random.uniform(0.6, 1.2)), ship.hold_room(good))
            if amount > 0:
                ship.cargo[good] += amount
                lines.append("+%d %s in the hold" % (amount, good))
            else:
                lines.append("No room in the hold for the %s." % good)
        if lines:
            self.display_simple_message([line for text in lines for line in self.word_wrap(text)], 3)
        if out.get("fight"):
            self.encounter(out["fight"])


    def battle_event(self, enemy_attack, enemy_defense, enemy_speed):
        say(f"An enemy is attacking! Enemy stats: ATK {enemy_attack}, DEF {enemy_defense}, SPD {enemy_speed}")

        player_damage = max(0, enemy_attack - self.ship.defense)
        enemy_damage = max(0, self.ship.attack - enemy_defense)

        if self.ship.speed > enemy_speed:
            say("You have the speed advantage!")
            enemy_damage += 5
        elif self.ship.speed < enemy_speed:
            say("Enemy has the speed advantage!")
            player_damage += 5

        # Introduce randomness based on stats
        if random.random() < 0.5:
            player_damage = max(0, player_damage - random.randint(0, self.ship.defense))
        if random.random() < 0.5:
            enemy_damage = max(0, enemy_damage - random.randint(0, enemy_defense))

        say(f"You deal {enemy_damage} damage to the enemy.")
        say(f"The enemy deals {player_damage} damage to you.")

        if enemy_damage > player_damage:
            say("You won the battle!")
            reward = random.choice([
                ("money", random.randint(100, 500)),
                ("tech", random.randint(5, 15)),
                ("agri", random.randint(5, 15)),
                ("item", random.choice(["navcomp", "shield", "turrets", "scanner"]))
            ])
            if reward[0] == "money":
                self.ship.money += reward[1]
                self.display_simple_message(f"Reward: {self.format_money(reward[1])} money", 3, color='32')
            elif reward[0] == "tech":
                self.ship.cargo['tech'] += reward[1]
                self.display_simple_message(f"Reward: {self.format_money(reward[1])} tech goods", 3, color='32')
            elif reward[0] == "agri":
                self.ship.cargo['agri'] += reward[1]
                self.display_simple_message(f"Reward: {self.format_money(reward[1])} agri goods", 3, color='32')
            elif reward[0] == "item":
                self.ship.acquire_item(reward[1])
                self.display_simple_message(f"Reward: {reward[1]} item", 3, color='32')
        else:
            say("You lost the battle!")
            penalty = random.choice([
                ("money", random.randint(50, 200)),
                ("tech", random.randint(2, 10)),
                ("agri", random.randint(2, 10)),
                ("damage", random.randint(10, 30))
            ])
            if penalty[0] == "money":
                self.ship.money = max(0, self.ship.money - penalty[1])
                self.display_simple_message(f"Penalty: Lost {self.format_money(penalty[1])} money", 3, color='31')
            elif penalty[0] == "tech":
                self.ship.cargo['tech'] = max(0, self.ship.cargo['tech'] - penalty[1])
                self.display_simple_message(f"Penalty: Lost {self.format_money(penalty[1])} tech goods", 3, color='31')
            elif penalty[0] == "agri":
                self.ship.cargo['agri'] = max(0, self.ship.cargo['agri'] - penalty[1])
                self.display_simple_message(f"Penalty: Lost {self.format_money(penalty[1])} agri goods", 3, color='31')
            elif penalty[0] == "damage":
                self.ship.damage += penalty[1]
                self.display_simple_message(f"Penalty: {penalty[1]}% additional damage", 3, color='31')

    def handle_combat(self, enemy_stats):
        """Handle combat with enemy ships"""
        enemy_attack = enemy_stats.get("attack", 2)
        enemy_defense = enemy_stats.get("defense", 1)
        enemy_type = enemy_stats.get("type", "pirate")

        self.battle_event(enemy_attack, enemy_defense, self.ship.speed)
        if enemy_type == "rogue_captain":
            # Add special rewards for defeating rogue captain
            if enemy_attack < self.ship.attack:
                self.ship.money += random.randint(2000, 5000)
                special_items = ["quantum_core", "advanced_shield", "neural_hack"]
                self.ship.acquire_item(random.choice(special_items))


# The game's other modules, imported last so that the modules can refer to each other.
from .terminal import say  # noqa: E402
from .story import story_data  # noqa: E402
from .modules import condition_word, module_name  # noqa: E402
from .tactics import TACTICAL_FROM  # noqa: E402
