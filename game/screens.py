"""The Game's screens: status, location, help, messages and input checks."""
from math import floor
import os
import random
import shutil
import time
from . import look

class ScreensMixin:
    """The Game's screens and input checks. Game inherits it (game/world.py)."""
    def get_terminal_width(self):
        return terminal_columns()

    def get_terminal_height(self):
        try:
            return shutil.get_terminal_size((80, 24)).lines
        except (OSError, ValueError):
            return 24

    def format_money(self, amount):
        if amount >= 1_000_000_000:
            return f"{amount/1_000_000_000:.1f}B"
        elif amount >= 1_000_000:
            return f"{amount/1_000_000:.1f}M"
        elif amount >= 1_000:
            return f"{amount/1_000:.1f}K"
        return str(floor(amount))

    def create_box(self, content, style='single', narrow='auto'):
        """A full-width box around rows of cells (see render_box)."""
        return render_box(content, style, narrow=narrow)

    def create_character_box(self, character_content, style='round'):
        """A character card: title, a rule, then the text sections."""
        rows = []
        if character_content.get('title'):
            rows.append([character_content['title']])
            rows.append(RULE)
        for section in ['introduction', 'description', 'demands', 'options']:
            text = str(character_content.get(section) or '')
            if text.strip():
                rows.append([text])
        return render_box(rows, style, inner=box_inner_width(cap=80))

    def display_simple_message(self, message, pause=1, style='round', color=None):
        if isinstance(message, list):
            box_content = message
        else:
            box_content = [message]

        print(self.create_simple_box(box_content, style, color=color))
        if pause > 0:
            time.sleep(pause)


    def create_simple_box(self, content, style='single', color=None):
        """A full-width box around lines of text, each word-wrapped; `color` a raw colour code."""
        return render_box([[str(row)] for row in content], style, color=color)


    def validate_input(self, default_prompt, valid_options, prompt=None):
            """
            Validate user input against a list of valid options
            default_prompt: Default prompt text
            valid_options: List of valid input options
            prompt: Optional custom prompt to override default
            """
            while True:
                self.display_simple_message(prompt or default_prompt, 0)

                try:
                    user_input = input(">>> ").strip().lower()
                    if not user_input:
                        if "Enter" not in (prompt or default_prompt):
                            self.display_simple_message("Command cancelled.")
                        return None
                    if user_input in valid_options:
                        return user_input
                    self.display_simple_message(f"Invalid input, try: {', '.join(valid_options)}", 1)
                except KeyboardInterrupt:
                    print("Do you want to exit? (yes/no):")
                    confirm = input(">>> ").strip().lower()
                    if confirm == 'yes':
                        self.display_simple_message("Goodbye!", 1)
                        exit()

    def validate_quantity_input(self, prompt):
        while True:
            self.display_simple_message(prompt, 0)
            try:
                user_input = input(">>> ").strip().lower()
                if not user_input:
                    self.display_simple_message("Command cancelled.")
                    return None
                if user_input in ['max', 'm']:
                    return 'max'
                if user_input in ['half', 'h']:
                    return 'half'
                quantity = int(user_input)
                if quantity > 0:
                    return quantity
                self.display_simple_message("Please enter a positive number, 'max/m', or 'half/h'", 1)
            except ValueError:
                self.display_simple_message("Invalid input. Please enter a number, 'max/m', or 'half/h'", 1)


    # Update Game class methods
    def display_turn_info(self):
        self.clear_screen()

        # Calculate passenger stats
        total_passengers = 0
        total_capacity = 0
        if hasattr(self.ship, 'passenger_modules'):
            for module in self.ship.passenger_modules:
                total_passengers += len(module.passengers)
                total_capacity += module.capacity

        status_content = [
            [short_logo(), "Ship", f"{self.current_location.location_type}"],
            [f"Turn: {self.turn}", f"ATK: {self.ship.attack}", f"Name: {self.current_location.name}"],
            [f"¤: {self.format_money(self.ship.money)}", f"DEF: {self.ship.defense}", f"Tech LVL: {self.current_location.tech_level}"],
            [f"Tech: {self.format_money(self.ship.cargo['tech'])}", f"SPD: {self.ship.speed}", f"Agri LVL: {self.current_location.agri_level}"],
            [f"Agri: {self.format_money(self.ship.cargo['agri'])}", f"DMG: {self.ship.damage}%", f"ECO: {self.current_location.economy}"],
            [f"Salt: {self.format_money(self.ship.cargo['salt'])}", f"RP: {self.ship.research_points}", f"EFF: {self.current_location.exogeology}%"],
            [f"Fuel: {self.format_money(self.ship.cargo['fuel'])}", f"★ {self.rank}", f"NET: {len(self.current_location.buildings)}"],
            [f"PAX: {total_passengers}/{total_capacity}", f"REP: {self.ship.passenger_reputation}", f"Hold: {self.ship.hold_text()}"]
        ]

        # Add story progress if available
        if hasattr(self, 'story_manager'):
            current_chapter = self.story_manager.chapters[self.story_manager.current_chapter]
            target = self.story_manager.plot_target()
            points = self.story_manager.plot_points
            status_content.append([
                f"Chapter {self.story_manager.get_chapter_number_roman()}",
                f"Plot Points: {points}/{target}" if target and points < target else f"Plot Points: {points}",
                current_chapter.title
            ])

        status_box = self.create_box(status_content, 'double', narrow='flow')
        print(status_box)

        # Market prices with banned commodities indicator
        tech_status = "BANNED" if 'tech' in self.current_location.banned_commodities else str(self.format_money(self.current_location.market['tech']))
        agri_status = "BANNED" if 'agri' in self.current_location.banned_commodities else str(self.format_money(self.current_location.market['agri']))
        salt_status = "BANNED" if 'salt' in self.current_location.banned_commodities else str(self.format_money(self.current_location.market['salt']))
        fuel_status = "BANNED" if 'fuel' in self.current_location.banned_commodities else str(self.format_money(self.current_location.market['fuel']))

        # Market content with two columns
        market_content = [
            [f"Tech: {tech_status}", f"Salt: {salt_status if self.current_location.trades_bulk('salt') else '——'}"],
            [f"Agri: {agri_status}", f"Fuel: {fuel_status if self.current_location.trades_bulk('fuel') else '——'}"]
        ]

        # Add ban duration if any commodities are banned
        if self.current_location.banned_commodities:
            market_content.append(["", ""])  # Empty line for spacing
            market_content.append(["Trade Bans:", "Duration:"])
            for commodity in self.current_location.banned_commodities:
                duration = self.current_location.ban_duration.get(commodity, "Permanent")
                market_content.append([f"{commodity.capitalize()}", f"{duration} turns"])
        print(self.create_box(market_content, 'single'))

        # The commands this place offers (help/h explains them)
        self.display_simple_message(self.command_hint(), 1)

        # Display active effects
        if self.research.unlocked_options:
            effects = [["Active Research Effects"]]
            for research in self.research.unlocked_options:
                effects.append([f"- {research.replace('_', ' ').title()}"])
            print(self.create_box(effects, 'round'))

    def display_location_info(self):
        # Ship section
        # Get total locations
        total_locations = len(self.locations) if hasattr(self, 'locations') else 0
        # Add 1 to discovered count for starting location if not already included
        discovered = (len(self.discovered_locations) if hasattr(self, 'discovered_locations') else 0)

        ship_info = [
            ["Ship Information"],
            [f"Stats: {self.ship.attack}|{self.ship.defense}|{self.ship.speed}"],
            [f"Locations Discovered: {discovered + 1}/{total_locations}"],
            [f"Trades Completed: {self.trades_completed}"],
            [f"PAX Delivered: {self.reputation_manager.total_passengers}"],
#            [f"Locations Discovered: {len(self.discovered_locations) if hasattr(self, 'discovered_locations') else 0}"]
#            [f"Hull Damage: {self.ship.damage}%"],
            [f"Money: {self.format_money(self.ship.money)}"],
            [f"Research Points: {self.ship.research_points}"],
    #        ["Cargo:"],
    #        [f"  Tech: {self.format_money(self.ship.cargo['tech'])}"],
    #        [f"  Agri: {self.format_money(self.ship.cargo['agri'])}"],
    #        [f"  Salt: {self.format_money(self.ship.cargo['salt'])}"],
    #        [f"  Fuel: {self.format_money(self.ship.cargo['fuel'])}"],
            ["Items:"]
        ]


        # Add items if any exist
        if self.ship.items:
            for item, count in self.ship.items.items():
                ship_info.append([f"  {item.replace('_', ' ').capitalize()}: {count}"])
        else:
            ship_info.append(["  No items"])

        ship_info.append(["Modules (%d/%d):" % (len(self.ship.modules), self.ship.grips())])
        for module in self.ship.modules:
            ship_info.append(["  %s: %s" % (module_name(module["kind"]), condition_word(module["condition"]))])
        if not self.ship.modules:
            ship_info.append(["  empty grips"])

        # Add combat statistics if they exist
        if hasattr(self.ship, 'combat_victories'):
                    ship_info.append(["Combat Record:"])
                    # Format victories
                    ship_info.extend([
                        [f"Victories/Defeats Summary"],
                        [f"  Pirates: {self.ship.combat_victories.get('pirate', 0)}/{self.ship.combat_defeats.get('pirate', 0)}"],
                        [f"  Raiders: {self.ship.combat_victories.get('raider', 0)}/{self.ship.combat_defeats.get('raider', 0)}"],
                        [f"  Militia: {self.ship.combat_victories.get('militia', 0)}/{self.ship.combat_defeats.get('militia', 0)}"],
                        [f"  Aliens: {self.ship.combat_victories.get('alien', 0)}/{self.ship.combat_defeats.get('alien', 0)}"],
                        [f"  Total: {self.ship.combat_victories.get('total', 0)}/{self.ship.combat_defeats.get('total', 0)}"]
                    ])

        if hasattr(self.ship, 'active_infestations') and self.ship.active_infestations:
            ship_info.append(["Active Infestations:"])
            for name, infestation in self.ship.active_infestations.items():
                ship_info.append([
                    f"{infestation['name']} - Turn {infestation['turns_active']}"
                ])

        # Location section
        location_info = [
            ["Location"],
            [f"Name: {self.current_location.name}"],
            [f"Type: {self.current_location.location_type}"],
            [f"Tech Level: {self.current_location.tech_level}"],
            [f"Agri Level: {self.current_location.agri_level}"],
            [f"Research Points: {self.current_location.research_points}"],
            [f"Economy: {self.current_location.economy}"],
            [f"Mining Efficiency: {self.current_location.exogeology}%"],
            ["Current Market:"],
            [f"  Tech: {self.format_money(self.current_location.market['tech'])}"],
            [f"  Agri: {self.format_money(self.current_location.market['agri'])}"],
            [f"  Salt: {self.format_money(self.current_location.market['salt'])}"],
            [f"  Fuel: {self.format_money(self.current_location.market['fuel'])}"]
        ]

        # Add banned commodities if any
        if self.current_location.banned_commodities:
            location_info.append(["Banned Commodities:"])
            for commodity in self.current_location.banned_commodities:
                duration = self.current_location.ban_duration.get(commodity, "Permanent")
                location_info.append([f"  {commodity.capitalize()}: {duration} turns"])

        # Add buildings
        location_info.append(["Networks (Built):"])
        if self.current_location.buildings:
            building_counts = {}
            for building in self.current_location.buildings:
                building_counts[building] = building_counts.get(building, 0) + 1
            for building, count in building_counts.items():
                location_info.append([f"  {building} x{count}"])
        else:
            location_info.append(["  No buildings"])

        # Add mining information
        location_info.append(["Mining Operations:"])
        if self.current_location.mining_platforms:
            for platform in self.current_location.mining_platforms:
                location_info.append([
                    f"  {platform['type'].capitalize()} Platform",
                    f"  (Efficiency: {platform['efficiency']}%",
                    f"  Capacity: {platform['capacity']})"
                ])
        else:
            location_info.append(["  No mining platforms"])

        # Add mineral deposits if any
        if self.current_location.mineral_deposits:
            location_info.append(["Mineral Deposits:"])
            for deposit_type, amount in self.current_location.mineral_deposits.items():
                location_info.append([f"  {deposit_type.capitalize()}: {amount} units"])

        # Create content by combining ship and location info
        content = []
        max_length = max(len(ship_info), len(location_info))

        for i in range(max_length):
            ship_line = ship_info[i][0] if i < len(ship_info) else ""
            location_line = ""
            if i < len(location_info):
                cells = location_info[i]
                location_line = " ".join([str(cells[0])] + [str(c).strip() for c in cells[1:]])
            content.append([ship_line, location_line])

        print(self.create_box(content, 'double', narrow='stack'))
        input("Press Enter to continue...")

    COMMAND_HELP = {
        'buy': "buy goods: then tech/t, agri/a, salt/s, fuel/f and an amount, max/m or half/h",
        'sell': "sell goods, same answers as buy",
        'travel': "fly to a known location (one turn; the trip may bring events)",
        'port': "passengers, cabins, contracts",
        'cantina': "maps, gossip, quests, contracts, and whoever is in the bar",
        'shop': "equipment for the ship",
        'upgrade': "attack, defense or speed (each costs more); hull: a heavier hull; modules: the yard",
        'repair': "repair the hull",
        'research': "spend research points (research colonies)",
        'action': "scan, research and other actions",
        'mine': "mining platforms and deposits",
        'build': "buildings: stock market, farms, guilds, refineries",
        'info': "this location in detail",
        'hunt': "the bounty board: pick a wanted ship and go after it (takes the turn)",
        'end': "end the turn and wait here",
        'hansa': "Hansa terminal: needle fares, bonds that lower them, the price board, what you owe",
        'log': "story progress: what the next chapter needs",
        'journal': "people met, choices remembered, places",
        'save': "save the game (it also saves itself every turn)",
        'load': "load a saved game",
        'captain': "your captain's record: carry it to another part of the saga",
        'style': "the look: colours and frames (themes from CLIo and from Cargo 2 0.1.0-a)",
        'sound': "music and effects on or off (composed as you play; silent without a player)",
        'look': "look around the dock: people here, things to examine, what is going on",
        'think': "your captain's notes: leads, where people travel, what the story still needs",
        'help': "this screen",
        'version': "the game's version",
        'resign': "end this game and see the score",
        'quit': "leave (the autosave keeps your progress)",
    }

    def choose_style(self):
        """The `style` command: pick a theme; it is kept in the settings for every later game."""
        state = look.current()
        choices = look.styles()
        rows = [["Styles"], RULE]
        for number, (name, about) in enumerate(choices, 1):
            mark = "  (in use)" if name == state["style"] else ""
            rows.append(["%d. %s%s: %s" % (number, name, mark, about)])
        print(self.create_box(rows, 'double'))
        answer = self.validate_input("Type a number, or press Enter to keep this one.",
                                     [str(n) for n in range(1, len(choices) + 1)])
        if answer is None:
            return
        name = choices[int(answer) - 1][0]
        look.setup(style=name)
        kept = look.write_settings({"style": name})
        self.display_simple_message(["Style: %s." % name,
                                     "Kept for later games." if kept else "For this game only: the settings could "
                                     "not be written."], 1)

    def here_commands(self):
        """(long, short) for every command accepted at this location, its own first."""
        own = [pair for pair in self.current_location.commands["available"]]
        return own + [pair for pair in GLOBAL_COMMANDS if pair not in own]

    def command_hint(self):
        own = self.current_location.commands["available"]
        return "Commands: " + ", ".join("%s/%s" % pair for pair in own) + " - help/h for more"

    def show_help(self):
        """A short guide: what the game is about, and every command with its shortcut."""
        rows = [["How to play"], [""],
                ["You run a cargo hauler. Buy goods where they are cheap, sell where they are dear "
                 "(your hold takes %d units; the shop sells more room), carry passengers, take contracts "
                 "and quests from the cantina, and follow the story (log/l) to one of three endings: "
                 "trade, combat or discovery." % sum(self.ship.hold_sizes())],
                [""],
                ["Between docks you meet pirates, customs, drones and odd moments: pick how to handle each. "
                 "A small ship is settled in one roll; a bigger one is a convoy fight, round by round: focus "
                 "fire, screen the haulers of your needle, use your modules, board them or break off. "
                 "Gear and crew open better options (a mining laser cuts drones, a scanner spots bait). "
                 "The bounty board (hunt/hu) pays for wanted ships. Cantinas have rumours, people, and "
                 "crew for hire (four bunks). Plot points move the story: earn them by doing things."],
                [""],
                ["Between the stars you ride the Hansa's needles: book a place in the file when you travel. "
                 "The front is safe and dear, the tail cheap and cold, and the Cargolytes work the tail. Fares "
                 "grow as the routes get busier; Hansa bonds and the Hansa's good opinion lower them (hansa/ha). "
                 "Needles leave planets every turn, other docks every third turn. "
                 "Inside a star system you fly free, on your own fuel. Big loads move prices and markets take a "
                 "while to recover: the Hansa price board and the port's broker robot guess prices elsewhere."],
                [""],
                ["Outposts, ruins and listening posts are rough going for an old hull, and the far edge of the "
                 "system is worse: a planet's shipyard (upgrade/u, hull) rebuilds you as an Ironback or a "
                 "Farstrider, which fight and carry better and cost far more to repair. Rich captains draw "
                 "bigger pirates, who take a bigger share. People you meet come back, and so do your choices."],
                [""],
                ["Behind the command module the hull's spine has grips for modules: three on the old hauler, five "
                 "on an Ironback, seven on a Farstrider. Yards at planets and asteroid bases (upgrade/u, modules) "
                 "fit containers, turrets, shields, scanners, a repair bay and more. Modules wear in fights and on "
                 "rough lanes; a broken one does nothing until it is mended. Research colonies (action/a) research "
                 "in two tiers: each branch of the second closes its twin. The journal (log/l) lists your "
                 "standings and achievements."],
                [""],
                ["Look around a dock (look/lk) for the people there and things to examine; some people travel "
                 "routes of their own. Think (th) to read your captain's notes: leads, where people go, what "
                 "the story still needs. Nothing you find this way is needed for an ending, but some of it helps."],
                [""],
                ["Type a command or its shortcut and press Enter. In any menu, Enter on its own goes back. "
                 "Amounts: a number, max/m or half/h. Each 'end' or journey is one turn; the game saves "
                 "itself after every turn."],
                [""], ["Here at %s:" % self.current_location.name]]
        for cmd, shortcut in self.here_commands():
            rows.append(["%s/%s" % (cmd, shortcut), self.COMMAND_HELP.get(cmd, "")])
        print(self.create_box(rows, 'double'))
        input("Press Enter to continue...")

    def display_starting_info(self):
        """Display initial game information with location context"""
        # Get location info based on current_location
        location_type = "an industrial"
        if self.current_location.agri_level > self.current_location.tech_level:
            location_type = "an agricultural"
        elif self.current_location.research_points > 15:
            location_type = "a research"

        intro_text = f"\n  You arrive on {self.current_location.name}, {location_type} {self.current_location.location_type.lower()}, where your adventure begins."
        special_events = [
            "Revolutions are happening!",
            "Economy boom!",
            "Technological advancements!",
            "Agricultural breakthroughs!",
            "Nothing special happening."
        ]
        special_event = random.choice(special_events)
        special_event_text = f"Special Event: {special_event}"

        self.display_story_message(self.word_wrap(intro_text))
        self.display_story_message(self.word_wrap(special_event_text))
        time.sleep(3)  # Pause to let the player read the information

    def option_lines(self, number, label):
        """'3. A long option' wrapped so its later lines sit under its text, not its number."""
        lead = "%d. " % number
        lines = self.word_wrap(label, box_inner_width() - 2 - len(lead))
        return [lead + lines[0]] + [" " * len(lead) + line for line in lines[1:]]

    def word_wrap(self, text, width=None):
        if width is None:
            width = box_inner_width() - 2
        return wrap_text(text, width)

    def display_story_message(self, message, pause=2, style='round', color=None):
        if isinstance(message, list):
            box_content = message
        else:
            box_content = [message]

        print(self.create_simple_box(box_content, style, color=color))
        if pause > 0:
            time.sleep(pause)

    def display_story_status(self):
        """Display story progress and achievements"""
        story_content = [["Story Progress & Achievements"]]
        story_content.append([""])

        # Current chapter info
        current_chapter_obj = self.story_manager.chapters[self.story_manager.current_chapter]
        story_content.append([f"Current Chapter {self.story_manager.get_chapter_number_roman()} : {current_chapter_obj.title}"])
        story_content.append([f"Plot Points: {self.story_manager.plot_points}"])

        # Completed story beats
        if self.story_manager.completed_story_beats:
            story_content.append([""])
            story_content.append(["Completed Story Elements"])
            for beat in self.story_manager.completed_story_beats:
                story_content.append([f"• {beat.replace('_', ' ').title()}"])

        # Achievements
        if hasattr(self.story_manager, 'unlocked_achievements') and self.story_manager.unlocked_achievements:
            story_content.append([""])
            story_content.append(["Achievements Unlocked"])
            for achievement in self.story_manager.unlocked_achievements:
                story_content.append([f"• {achievement.replace('_', ' ').title()}"])

        # Location discoveries
        if hasattr(self.story_manager, 'discovered_locations_by_type'):
            story_content.append([""])
            story_content.append(["Location Discoveries"])
            for loc_type, count in self.story_manager.discovered_locations_by_type.items():
                story_content.append([f"• {loc_type}: {count} discovered"])

        print(self.create_box(story_content, 'double'))
        input("Press Enter to continue...")


    def clear_screen(self):
        os.system('clear' if os.name == 'posix' else 'cls')


# The game's other modules, imported last so that the modules can refer to each other.
from .terminal import RULE, box_inner_width, render_box, short_logo, terminal_columns, wrap_text  # noqa: E402
from .commands import GLOBAL_COMMANDS  # noqa: E402
from .modules import condition_word, module_name  # noqa: E402
