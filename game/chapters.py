"""Chapters, milestones and endings: the main story's frame and the StoryManager that runs it."""
import random

class MilestoneRequirements:
    """Enhanced requirements checking for story milestones"""

    @staticmethod
    def check_requirements(requirements, game):
        """Check if all requirements are met"""
        for req_type, req_value in requirements.items():
            if not MilestoneRequirements._check_single_requirement(req_type, req_value, game):
                return False
        return True

    @staticmethod
    def _check_single_requirement(req_type, req_value, game):
        """Check a single requirement (main-story thresholds as they stand on this voyage)"""
        if hasattr(game, "voyage_factor"):
            req_value = voyage_value(req_type, req_value, game.voyage_factor())
        # Basic requirements
        if req_type == "plot_points":
            return game.story_manager.plot_points >= req_value
        elif req_type == "money":
            return game.person.money >= req_value
        elif req_type == "research_points":
            return game.person.research_points >= req_value
        # what only a ship has: not met without one
        elif game.ship is None and req_type in ("combat_victories", "combat_rating", "trade_profit",
                                                "trade_specific", "passenger_reputation"):
            return False

        # Combat requirements
        elif req_type == "combat_victories":
            if isinstance(req_value, dict):
                # Check specific enemy types
                for enemy_type, amount in req_value.items():
                    if game.ship.combat_victories.get(enemy_type, 0) < amount:
                        return False
                return True
            else:
                # Check total victories
                return game.ship.combat_victories['total'] >= req_value
        elif req_type == "combat_rating":
            return (game.ship.attack + game.ship.defense + game.ship.speed) >= req_value

        # Trade requirements
        elif req_type == "trades_completed":
            return game.trades_completed >= req_value
        elif req_type == "trade_profit":
            return sum(game.ship.trade_profits.values()) >= req_value
        elif req_type == "trade_specific":
            # Check specific commodity trading requirements
            commodity, amount = req_value
            return game.ship.trade_profits.get(commodity, 0) >= amount

        # Passenger requirements
        elif req_type == "passengers_transported":
            return game.reputation_manager.total_passengers >= req_value
        elif req_type == "passenger_reputation":
            return game.ship.passenger_reputation >= req_value
        elif req_type == "passenger_class":
            # Check specific passenger class requirements
            class_type, amount = req_value
            return game.reputation_manager.class_transports.get(class_type, 0) >= amount

        # Location requirements
        elif req_type == "locations_discovered":
            if isinstance(req_value, dict):
                # Check specific location types
                for loc_type, amount in req_value.items():
                    if game.count_discovered(loc_type) < amount:
                        return False
                return True
            else:
                # Check total discoveries
                return len(game.discovered_locations) >= req_value
        elif req_type == "buildings_built":
            if isinstance(req_value, dict):
                # Check specific building types
                for building_type, amount in req_value.items():
                    total_built = sum(1 for loc in game.locations
                                    for building in loc.buildings
                                    if building == building_type)
                    if total_built < amount:
                        return False
                return True
            else:
                # Check total buildings
                return sum(len(loc.buildings) for loc in game.locations) >= req_value

        # Mining requirements
        elif req_type == "mining_platforms":
            if isinstance(req_value, dict):
                # Check specific resource types
                for resource_type, amount in req_value.items():
                    total_platforms = sum(1 for loc in game.locations
                                        for platform in loc.mining_platforms
                                        if platform['type'] == resource_type)
                    if total_platforms < amount:
                        return False
                return True
            else:
                # Check total platforms
                return sum(len(loc.mining_platforms) for loc in game.locations) >= req_value

        # Quest requirements
        elif req_type == "quests_completed":
            if isinstance(req_value, dict):
                # Check specific quest types
                for quest_type, amount in req_value.items():
                    completed = len([q for q in game.quest_system.completed_quests
                                   if q.quest_type == quest_type])
                    if completed < amount:
                        return False
                return True
            else:
                # Check total completed quests
                return len(game.quest_system.completed_quests) >= req_value

        # Research requirements
        elif req_type == "research_unlocked":
            return all(tech in game.research.unlocked_options for tech in req_value)

        # Faction requirements
        elif req_type == "faction_reputation":
            faction, rep_level = req_value
            return game.faction_system.get_reputation(faction) >= rep_level

        # Item requirements
        elif req_type == "items":
            return all(item in game.person.items for item in req_value)

        # Story progression requirements
        elif req_type == "chapters_completed":
            return all(chapter in game.story_manager.completed_chapters for chapter in req_value)
        elif req_type == "chapters_completed_any":
            return any(chapter in game.story_manager.completed_chapters for chapter in req_value)
        elif req_type == "milestones_completed":
            return all(milestone in game.story_manager.completed_story_beats for milestone in req_value)
        elif req_type == "story_states":
            return all(game.story_manager.story_states.get(state, False) for state in req_value)

        # Captains who crossed over from another part of the trilogy:
        # {"game": "cargo2"}, optionally with "ending" and/or "flag"
        elif req_type == "visiting_captain":
            return game.has_visiting_captain(req_value.get("game"), req_value.get("ending"),
                                             req_value.get("flag"))

        # Custom requirements
        elif req_type == "custom_condition":
            return req_value(game)  # Call custom function with game instance

        # Unknown requirement type
        else:
            print(f"Warning: Unknown requirement type {req_type}")
            return False

class StoryMilestone:
    def __init__(self, milestone_id, title, description, requirements, rewards=None, unlocks=None):
        self.id = milestone_id
        self.title = title
        self.description = description
        self.requirements = requirements
        self.rewards = rewards or {}
        self.unlocks = unlocks or []  # List of unlock dictionaries
        self.completed = False
        self.completion_turn = None

    def check_completion(self, game):
        """Check if milestone requirements are met: the story file's, when it states them."""
        if self.completed:
            return True
        story = getattr(game, "story", None)
        chapter = getattr(self, "chapter_id", None)
        repaired = story.condition_for("%s.%s" % (chapter, self.id)) if story is not None and chapter else None
        if repaired is not None:
            return story.check(voyage_condition(repaired, game.voyage_factor()), story.snapshot())
        return MilestoneRequirements.check_requirements(self.requirements, game)

    def complete(self, game):
        """Complete milestone and handle unlocks"""
        if not self.completed:
            self.completed = True
            self.completion_turn = game.turn
            node = story_data()["nodes"].get("%s.%s" % (getattr(self, "chapter_id", ""), self.id)) or {}
            if node.get("effects") and getattr(game, "story", None) is not None:
                game.story.apply(node["effects"])

            # Handle rewards
            if self.rewards:
                if "money" in self.rewards:
                    game.person.money += self.rewards["money"]
                if "research_points" in self.rewards:
                    game.person.research_points += self.rewards["research_points"]
                if "plot_points" in self.rewards:
                    game.story_manager.plot_points += self.rewards["plot_points"]
                if "items" in self.rewards:
                    for item in self.rewards["items"]:
                        game.person.acquire_item(item)

            # Handle unlocks
            unlock_messages = []
            for unlock in self.unlocks:
                unlock_type = unlock.get("type")
                unlock_id = unlock.get("id")

                if unlock_type == "item":
                    game.person.acquire_item(unlock_id)
                    unlock_messages.append(f"Unlocked item: {unlock_id}")

                elif unlock_type == "location_type":
                    game.unlocked_location_types.add(unlock_id)
                    # Add hidden locations of this type to available locations
                    if unlock_id in game.hidden_locations:
                        game.locations.extend(game.hidden_locations[unlock_id])
                        unlock_messages.append(f"Unlocked new location type: {unlock_id}")

                elif unlock_type == "specific_location":
                    # Search in hidden_locations
                    for loc_type, locations in game.hidden_locations.items():
                        for location in locations:
                            if location.name == unlock_id:
                                game.locations.append(location)
                                game.known_locations.append(location.name)
                                unlock_messages.append(f"Discovered location: {location.name}")
                                break

                    # Search in chapter_locations
                    for chapter_num, chapter_locs in game.chapter_locations.items():
                        for loc_type, locations in chapter_locs.items():
                            for location in locations:
                                if location.name == unlock_id:
                                    game.locations.append(location)
                                    game.known_locations.append(location.name)
                                    unlock_messages.append(f"Discovered location: {location.name}")
                                    break

                elif unlock_type == "chapter_locations":
                    chapter_num = unlock.get("chapter")
                    if chapter_num in game.chapter_locations:
                        for loc_type, locations in game.chapter_locations[chapter_num].items():
                            game.locations.extend(locations)
                            for loc in locations:
                                game.known_locations.append(loc.name)
                        unlock_messages.append(f"Unlocked Chapter {chapter_num} locations!")

            # Display completion message with unlocks
            completion_message = [
                f"Milestone Completed: {self.title}!",
                self.description,
                "",
                "Rewards:"
            ]

            # Add rewards to message
            for reward_type, value in self.rewards.items():
                if reward_type == "money":
                    completion_message.append(f"• {game.format_money(value)} credits")
                elif reward_type == "plot_points":
                    completion_message.append(f"• {value} plot points")
                elif reward_type == "research_points":
                    completion_message.append(f"• {value} research points")
                elif reward_type == "items":
                    completion_message.append(f"• Items: {', '.join(value)}")

            # Add unlock messages
            if unlock_messages:
                completion_message.append("")
                completion_message.append("Unlocked:")
                for msg in unlock_messages:
                    completion_message.append(f"• {msg}")

            game.display_story_message(completion_message)

def chapter_requirements_met(chapter, game):
    """A chapter's own requirements; the story file's when it repairs them."""
    story = getattr(game, "story", None)
    repaired = story.condition_for(chapter.id) if story is not None else None
    if repaired is not None:
        return story.check(voyage_condition(repaired, game.voyage_factor()), story.snapshot())
    return all(MilestoneRequirements._check_single_requirement(req_type, req_value, game)
               for req_type, req_value in chapter.requirements.items())


class StoryChapter:
    def __init__(self, chapter_id, title, description, requirements, milestones, next_chapters=None):
        self.id = chapter_id
        self.title = title
        self.description = description
        self.requirements = requirements
        self.milestones = {}  # Dictionary of milestone_id: StoryMilestone
        self.next_chapters = next_chapters or []  # List of possible next chapter IDs
        self.unlocks = []  # Unlock dictionaries applied when the chapter completes
        self.completed = False
        self.completion_turn = None

        # Initialize milestones
        for milestone_data in milestones:
            milestone = StoryMilestone(**milestone_data)
            milestone.chapter_id = chapter_id
            self.milestones[milestone.id] = milestone

    def check_completion(self, game):
        """Check if chapter can be completed"""
        if self.completed:
            return True

        # First check chapter requirements
        if not chapter_requirements_met(self, game):
            return False

        # Then check if all required milestones are completed
        return all(milestone.completed for milestone in self.milestones.values())

    def get_available_milestones(self, game):
        """Get list of currently available milestones"""
        return [m for m in self.milestones.values()
                if not m.completed and m.check_completion(game)]

    def get_next_chapters(self, game):
        """Get list of possible next chapters based on current game state"""
        available_chapters = []
        for chapter_id in self.next_chapters:
            chapter = game.story_manager.chapters[chapter_id]
            if chapter_requirements_met(chapter, game):
                available_chapters.append(chapter)
        return available_chapters

    def handle_chapter_unlocks(self, game):
        """Handle any unlocks when chapter completes"""
        if hasattr(self, 'unlocks') and self.unlocks:
            for unlock in self.unlocks:
                unlock_type = unlock.get("type")
                unlock_id = unlock.get("id")

                if unlock_type == "location_type":
                    game.unlock_location_type(unlock_id)
                elif unlock_type == "chapter_locations":
                    chapter_num = unlock.get("chapter")
                    if chapter_num in game.chapter_locations:
                        for locations in game.chapter_locations[chapter_num].values():
                            game.locations.extend(locations)

class StoryManager:
    def __init__(self, game):
        self.game = game
        self.current_chapter = None
        self.completed_chapters = set()
        self.completed_story_beats = set()
        self.plot_points = 0
        self.story_states = {
            "pirate_threat": False,
            "alien_discovery": False,
            "trade_empire": False,
            "resource_empire": False,
            "ancient_mystery": False,
            "galactic_crisis": False
        }
        self.chapters = self.initialize_chapters()
        self.event_cooldowns = {}
        self.enabled_events = set()

    def get_chapter_number(self, chapter_string=None):
        """
        Extract numeric chapter number from chapter string.
        If no chapter string provided, uses current chapter.
        Returns: int chapter number
        """
        if chapter_string is None:
            chapter_string = self.current_chapter
        if chapter_string and str(chapter_string).startswith("ending"):
            return 4  # every ending is the fourth act
        try:
            return int(''.join(filter(str.isdigit, chapter_string)))
        except (ValueError, TypeError):
            return 1  # Default to chapter 1 if conversion fails

    def number_to_roman(self, num):
        """Convert integer to Roman numeral with dot"""
        roman_map = {
            1: 'I.', 2: 'II.', 3: 'III.', 4: 'IV.', 5: 'V.',
            6: 'VI.', 7: 'VII.', 8: 'VIII.', 9: 'IX.', 10: 'X.',
            11: 'XI.', 12: 'XII.', 13: 'XIII.', 14: 'XIV.', 15: 'XV.',
            16: 'XVI.', 17: 'XVII.', 18: 'XVIII.', 19: 'XIX.', 20: 'XX.',
            21: 'XXI.', 22: 'XXII.', 23: 'XXIII.', 24: 'XXIV.', 25: 'XXV.',
            26: 'XXVI.', 27: 'XXVII.', 28: 'XXVIII.', 29: 'XXIX.', 30: 'XXX.'
        }

        return roman_map.get(num, str(num))

    def get_chapter_number_roman(self, chapter_string=None):
        """Get chapter number as Roman numeral"""
        number = self.get_chapter_number(chapter_string)
        return self.number_to_roman(number)

    def initialize_chapters(self):
        """The chapters, their milestones and the endings, from the story's frame
        (story/cargo3/main.json): a chapter or ending node gives the title, the text, the
        conditions ("requires", checked by the story runtime) and the chapters that follow
        ("next"); its milestones are the milestone nodes that name it ("in"), with their own
        conditions and effects. Cargo 1 and 2 wrote these in code; Cargo 3 writes them as story."""
        nodes = story_data()["nodes"]

        def text(node):
            body = node.get("text") or ""
            return " ".join(body) if isinstance(body, list) else body

        chapters = {}
        for nid, node in nodes.items():
            if node.get("kind") not in ("chapter", "ending"):
                continue
            milestones = [{"milestone_id": mid.split(".", 1)[1], "title": m.get("title", mid),
                           "description": text(m), "requirements": {}}
                          for mid, m in nodes.items()
                          if m.get("kind") == "milestone" and m.get("in") == nid and "." in mid]
            chapters[nid] = StoryChapter(chapter_id=nid, title=node.get("title", nid), description=text(node),
                                         requirements={}, milestones=milestones,
                                         next_chapters=list(node.get("next") or []))
        return chapters

    def apply_story_text(self):
        """Titles and texts of chapters and milestones come from the story data."""
        story = self.game.story
        for cid, chapter in self.chapters.items():
            chapter.title = story.title_of(cid, chapter.title)
            if not cid.startswith("ending_"):
                chapter.description = " ".join(story.text_of(cid, fallback=chapter.description))
            for mid, milestone in chapter.milestones.items():
                nid = "%s.%s" % (cid, mid)
                milestone.title = story.title_of(nid, milestone.title)
                milestone.description = " ".join(story.text_of(nid, fallback=milestone.description))

    def start_game(self):
        """Initialize story at game start"""
        self.apply_story_text()
        self.current_chapter = "ch1"  # Store the ID string instead of the chapter object
        first_chapter = self.chapters["ch1"]

        self.game.display_story_message([
            f"Chapter I.: {first_chapter.title}",
            first_chapter.description,
            "",
            "Your journey begins..."
        ])

    def is_story_completed(self):
        """Check if the story has reached an ending"""
        if not self.current_chapter:
            return False
        current_chapter_obj = self.chapters[self.current_chapter]
        return (not current_chapter_obj.next_chapters and
                current_chapter_obj.completed)

    def check_milestone_progress(self):
        """Check for milestone completions in current chapter"""
        if self.current_chapter:
            current_chapter_obj = self.chapters[self.current_chapter]
            available_milestones = current_chapter_obj.get_available_milestones(self.game)
            for milestone in available_milestones:
                if milestone.check_completion(self.game):
                    milestone.complete(self.game)
                    self.completed_story_beats.add(milestone.id)

    def check_chapter_progress(self):
        """Complete the current chapter when it is done, then move on.

        A finished chapter waits here until one of its follow-up chapters
        opens; an ending chapter shows its ending once.
        """
        if not self.current_chapter:
            return

        chapter = self.chapters[self.current_chapter]
        if not chapter.completed:
            if not chapter.check_completion(self.game):
                return
            self.complete_current_chapter()
            if not chapter.next_chapters and self.current_chapter.startswith("ending"):
                self.handle_game_ending()
                return

        if not chapter.next_chapters:
            return
        options = chapter.get_next_chapters(self.game)
        if not options:
            return
        if len(chapter.next_chapters) == 1:
            self.start_chapter(options[0].id)
            return
        # Several ways on: ask, but only when the open ways have changed since
        # the last time the captain decided to wait
        open_now = sorted(option.id for option in options)
        if open_now != getattr(self, 'offered_paths', None):
            self.offered_paths = open_now
            self.present_chapter_choice(options)

    def handle_game_ending(self):
        """Handle reaching a game ending: its text, the score, what became of
        everyone, and the captain's record closed for this timeline."""
        story = self.game.story
        story.mark(self.current_chapter)
        story.cue("ending")
        self.game.display_story_message(story.text_of(
            self.current_chapter, fallback="Congratulations! You've completed your journey!"))
        self.game.display_score()
        story.epilogue()
        self.game.close_record(self.current_chapter.replace("ending_", ""))

    def complete_current_chapter(self):
        """Mark the current chapter complete and announce it"""
        current_chapter_obj = self.chapters[self.current_chapter]
        if not current_chapter_obj.completed:
            current_chapter_obj.completed = True
            current_chapter_obj.completion_turn = self.game.turn
            self.completed_chapters.add(self.current_chapter)

            # Handle any chapter unlocks
            current_chapter_obj.handle_chapter_unlocks(self.game)

            self.game.display_story_message([
                f"Chapter Complete: {current_chapter_obj.title}",
                "Your journey continues to evolve..."
            ])

    def present_chapter_choice(self, available_chapters):
        """Let the player pick the next chapter among the ones that are open.

        Ways that are not open yet are listed too, so the captain can decide
        to wait for them (Enter) instead of taking the first open door.
        """
        current = self.chapters[self.current_chapter]
        open_ids = [chapter.id for chapter in available_chapters]
        content = [["Choose Your Path"]]
        for i, chapter in enumerate(available_chapters, 1):
            content.extend([
                [""],
                [f"{i}. {chapter.title}"],
                [chapter.description]
            ])
        nodes = story_data()["nodes"]
        waiting = [self.chapters[cid] for cid in current.next_chapters
                   if cid not in open_ids and not (nodes.get(cid) or {}).get("secret")]
        for chapter in waiting:
            content.extend([
                [""],
                [f"-  {chapter.title} (not open yet)"],
                [chapter.description]
            ])
        print(self.game.create_box(content, 'double'))

        prompt = f"Choose your path (1-{len(available_chapters)})"
        if waiting:
            prompt += ", or press Enter to wait for the other"
        choice = self.game.validate_input(
            prompt + ": ",
            [str(i) for i in range(1, len(available_chapters) + 1)]
        )

        if choice:
            self.offered_paths = None
            chosen_chapter = available_chapters[int(choice) - 1]
            self.start_chapter(chosen_chapter.id)  # Use the ID

    def start_chapter(self, chapter):
        """Start a new chapter"""
        if isinstance(chapter, str):
            self.current_chapter = chapter
            chapter_obj = self.chapters[chapter]
        else:
            self.current_chapter = chapter.id
            chapter_obj = chapter

        self.chapter_started = self.game.turn
        self.game.display_story_message([
            f"{self.get_chapter_label()}: {chapter_obj.title}",
            chapter_obj.description,
            "",
            "New milestones await..."
        ])

    def plot_target(self):
        """The plot points the next chapter asks for, or None when no chapter waits on them."""
        chapter = self.chapters.get(self.current_chapter)
        nodes = story_data()["nodes"]
        wanted = [voyage_condition((nodes.get(c) or {}).get("requires", {}), self.game.voyage_factor()).get("plot_points")
                  for c in (chapter.next_chapters if chapter else [])]
        wanted = [w for w in wanted if isinstance(w, int)]
        return min(wanted) if wanted else None

    READABLE = {"plot_points": "plot points", "trades_completed": "trades", "trade_profit": "trade profit",
                "combat_victories": "fights won", "research_points": "research points",
                "passengers_transported": "passengers delivered", "passenger_reputation": "passenger reputation",
                "combat_rating": "attack + defense + speed", "discovered": "places visited", "money": "credits"}

    def chapter_needs(self, chapter):
        """What still stands between the captain and a chapter: [(key, words)].
        The story file's condition when it repairs the chapter's, else the code's."""
        game = self.game
        story = game.story
        cond = voyage_condition(story.condition_for(chapter.id), game.voyage_factor())
        if cond is None:
            return [(k, "%s: %s" % (k, v)) for k, v in chapter.requirements.items()
                    if not k.startswith("chapters_completed")
                    and not MilestoneRequirements._check_single_requirement(k, v, game)]
        snap = story.snapshot()
        out = []
        for key, want in cond.items():
            if story.check({key: want}, snap):
                continue
            if key in ("done", "done_any"):
                scenes = [n for n in _as_list(want) if n not in snap["done"] and n not in self.chapters]
                if scenes:
                    out.append((key, "a turning point: " + " or ".join(story.title_of(n) or n for n in scenes)))
                continue
            label = self.READABLE.get(key) or key.replace("buildings.", "buildings: ").replace(
                "combat_victories.", "victories over ").replace("discovered.", "places visited: ")
            value = game.format_money(want) if isinstance(want, int) and want >= 10000 else want
            out.append((key, "%s: %s" % (label, value)))
        return out

    # What a dock master says to a captain who has been stuck in one chapter a while,
    # by the first thing the way on still needs
    NUDGES = [
        ("done", "Some doors only open after the right meeting. Keep calling at cantinas and ports; "
                 "the people who matter are looking for you too."),
        ("plot", "Nobody sings about a captain who only waits. Take the jobs people offer in cantinas and ports, "
                 "trade well, look at new places: that is how a story gets told."),
        ("trade_profit", "Profit is what is left after the goods are paid for. Find a lane with a wide margin and work it."),
        ("trades", "The dock masters count every trade. Buy, sell, and do it often."),
        ("combat_victories", "The bounty board pays for ships the legions want gone. Hunt (hu) when your guns are ready."),
        ("combat_rating", "Your ship is too soft for the work you want. Upgrade it: attack, defense, speed."),
        ("research", "The research colonies pay attention to research points: travel, discoveries and old buoys all earn them."),
        ("passenger", "Passengers pay and talk. A better cabin helps; so does a steward who knows which fork is which."),
        ("building", "Build something: a stock market, a guild. People notice a captain who puts money into a dock."),
        ("locations", "There are places you have not seen yet. The cantina sells maps; the bar sells rumours."),
    ]

    def nudge(self):
        """After twenty turns in one chapter, the cantina offers a hint about what is missing."""
        game = self.game
        started = getattr(self, "chapter_started", 0)
        if game.turn - started < 20 or game.turn - getattr(self, "nudged_turn", -100) < 10:
            return
        chapter = self.chapters.get(self.current_chapter)
        if not chapter:
            return
        missing = []
        for milestone in chapter.milestones.values():
            if not milestone.completed:
                missing += [k for k, v in milestone.requirements.items()
                            if not MilestoneRequirements._check_single_requirement(k, v, game)]
        for cid in chapter.next_chapters:
            missing += [k for k, _ in self.chapter_needs(self.chapters[cid])]
        for key, text in self.NUDGES:
            if any(key in m for m in missing):
                self.nudged_turn = game.turn
                game.display_story_message(["A word at the bar", ""] + game.word_wrap(
                    "An old dock master who has seen a hundred captains come and go leans over: '" + text + "'"), pause=1)
                return

    def get_chapter_label(self, chapter_string=None):
        """'Chapter II.' for a numbered chapter, 'Finale' for an ending"""
        if chapter_string is None:
            chapter_string = self.current_chapter
        if chapter_string and chapter_string.startswith("ending"):
            return "Finale"
        return f"Chapter {self.get_chapter_number_roman(chapter_string)}"


    def complete_milestone(self, milestone_id):
        """Complete a specific milestone in the current chapter"""
        if self.current_chapter:
            current_chapter_obj = self.chapters[self.current_chapter]

            # Check if milestone exists in current chapter
            if milestone_id in current_chapter_obj.milestones:
                milestone = current_chapter_obj.milestones[milestone_id]

                # Complete the milestone if not already completed
                if not milestone.completed:
                    milestone.complete(self.game)
                    self.completed_story_beats.add(milestone_id)
                    return True

        return False

# Add these methods from old system:
    def process_event(self, event_type, details):
        """Process events and award plot points"""
        if self.check_cooldown(event_type):
            return

        points = self.calculate_points(event_type, details)

        # Extract numeric part of chapter string and use that for multiplier
        chapter_num = self.get_chapter_number()
        points *= (1 + chapter_num * 0.2)

        self.plot_points += int(points)

        self.update_story_states(event_type, details)
        self.check_chapter_progress()

    def enable_story_event(self, event_id):
        """Enable a story event for potential triggering"""
        self.enabled_events.add(event_id)

    def trigger_story_event(self, event_id, details=None):
        """Legacy support for story events"""
        if event_id in self.enabled_events:
            self.process_event("story", {
                "event_id": event_id,
                "details": details
            })
            return True
        return False

    def check_event_trigger(self, event, game):
        """Story switches that random events flip (no plot points: an event that only
        happened to the ship is not progress; what the captain does about it is)"""
        if isinstance(event, str):
            if "pirate" in event.lower():
                self.update_story_states("combat", {"enemy_type": "pirate"})
            elif "artifact" in event.lower():
                self.update_story_states("exploration", {"discovery_type": "artifact"})

    def handle_quest_completion(self, quest):
        """Update story progress when quests complete"""
        plot_points = {
            "story": 10,
            "combat": 5,
            "trade": 5,
            "exploration": 8,
            "research": 8
        }.get(quest.quest_type, 3)

        self.plot_points += plot_points

        # Handle milestone completion if this was a story quest
        if quest.milestone and self.current_chapter:
            chapter_obj = self.chapters[self.current_chapter]
            if quest.milestone in chapter_obj.milestones:
                milestone = chapter_obj.milestones[quest.milestone]
                milestone.complete(self.game)

        # Update story states based on quest completion
        if quest.quest_type == "trade" and self.game.trades_completed >= 50:
            self.story_states["trade_empire"] = True
        elif quest.quest_type == "combat" and self.game.ship.combat_victories['total'] >= 25:
            self.story_states["pirate_threat"] = True
        elif quest.quest_type == "research" and len(self.game.research.unlocked_options) >= 3:
            self.story_states["tech_breakthrough"] = True
        elif quest.quest_type == "exploration" and len(self.game.discovered_locations) >= 5:
            self.story_states["ancient_mystery"] = True

        # Check for chapter progression
        self.check_chapter_progress()

        # Generate new quests if appropriate
        if random.random() < 0.3:  # 30% chance for follow-up quest
            self.game.quest_system.add_quest(self.game.quest_system.generate_quest(quest.quest_type, 1.5))


    def check_cooldown(self, event_type):
        """Check event cooldown to prevent spam"""
        current_turn = self.game.turn
        if event_type in self.event_cooldowns:
            if current_turn - self.event_cooldowns[event_type] < 5:
                return True
        self.event_cooldowns[event_type] = current_turn
        return False

    def check_discovery_milestone(self, location):
        """
        Check if a discovered location triggers any story milestones

        Args:
            location: The location object that was discovered
        """
        if not self.current_chapter:
            return False

        current_chapter_obj = self.chapters[self.current_chapter]

        # Check each milestone in the current chapter
        for milestone_id, milestone in current_chapter_obj.milestones.items():
            if not milestone.completed and 'locations_discovered' in milestone.requirements:
                required_locations = milestone.requirements['locations_discovered']

                # Check if specific location type requirements are met
                if isinstance(required_locations, dict):
                    for loc_type, count in required_locations.items():
                        if self.game.count_discovered(loc_type) < count:
                            return False

                # Check total location type discovery
                elif isinstance(required_locations, int):
                    if len(self.game.discovered_locations) < required_locations:
                        return False

        return True

    def calculate_points(self, event_type, details):
        """Calculate points based on event type and details"""
        base_points = {
            "combat": 5,
            "trade": 3,
            "exploration": 8,
            "research": 6,
            "story": 10
        }.get(event_type, 2)

        if details.get("enemy_type") == "pirate":
            base_points *= 1.5
        elif details.get("discovery_type") == "artifact":
            base_points *= 2

        return base_points

    def update_story_states(self, event_type, details):
        """Update story state flags based on events"""
        if event_type == "combat" and details.get("enemy_type") == "pirate":
            self.story_states["pirate_threat"] = True
        elif event_type == "exploration" and details.get("discovery_type") == "artifact":
            self.story_states["alien_discovery"] = True

    def display_story_progress(self):
        current_chapter_obj = self.chapters[self.current_chapter] if self.current_chapter else None

        content = [
            ["Captain's Log: Story Progress"],
            [""],
            [f"Current Chapter: {current_chapter_obj.title if current_chapter_obj else 'None'}"],
        ]

        # Find next possible chapters and their plot point requirements
        if current_chapter_obj and current_chapter_obj.next_chapters:
            target = self.plot_target()     # the story's thresholds, which replace the code's
            plot_points_needed = target - self.plot_points if target else float('inf')

            if plot_points_needed != float('inf'):
                content.append([f"Plot Points: {self.plot_points} ({max(0, plot_points_needed)} to Next)"])
            else:
                content.append([f"Plot Points: {self.plot_points}"])
            content.extend([line] for line in self.game.word_wrap(
                "Plot points come from story scenes, quests, passengers, good deals, research, "
                "first visits, fights won and moments handled well."))
        else:
            content.append([f"Plot Points: {self.plot_points}"])

        content.extend([
            [""],
            ["Active Milestones:"]
        ])
        # Show current chapter's milestones with status
        if current_chapter_obj:
            for milestone in current_chapter_obj.milestones.values():
                status = "✓" if milestone.completed else "□"
                content.append([f"{status} {milestone.title}"])
                if not milestone.completed:
                    # Show requirements still needed
                    for req_type, req_value in milestone.requirements.items():
                        content.append([f"  └─ Needs: {req_type}: {req_value}"])

            # What opens the way on from here
            if current_chapter_obj.next_chapters:
                content.extend([[""], ["Ways on:"]])
                for chapter_id in current_chapter_obj.next_chapters:
                    chapter = self.chapters[chapter_id]
                    missing = [words for _, words in self.chapter_needs(chapter)]
                    content.append([f"→ {chapter.title}" + ("" if missing else " (open)")])
                    for line in missing:
                        content.append([f"  └─ Needs: {line}"])

        content.extend([
            [""],
            ["Completed Chapters:"]
        ])

        # Show completed chapters and their significant milestones
        for chapter_id in self.completed_chapters:
            chapter = self.chapters[chapter_id]
            content.append([f"• {chapter.title}"])
            for milestone in chapter.milestones.values():
                if milestone.completed:
                    completion_turn = getattr(milestone, 'completion_turn', '?')
                    content.append([f"  └─ {milestone.title} (Turn {completion_turn})"])

        print(self.game.create_box(content, 'double'))
        ask("Press Enter to continue...")

        # A captain who chose to wait can take an open path from the log
        if current_chapter_obj and current_chapter_obj.completed and len(current_chapter_obj.next_chapters) > 1:
            options = current_chapter_obj.get_next_chapters(self.game)
            if options:
                self.offered_paths = sorted(option.id for option in options)
                self.present_chapter_choice(options)


# The game's other modules, imported last so that the modules can refer to each other.
from .story import _as_list, story_data, voyage_condition, voyage_value  # noqa: E402
from .terminal import ask  # noqa: E402
