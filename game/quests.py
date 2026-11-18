"""Quests: what the captain is asked to do, and the system that offers, tracks and pays them."""
import random

def run_quest_callback(game, callback):
    """What happens when a quest completes.  Kept as data so quests can be saved."""
    if callable(callback):
        callback()
    elif isinstance(callback, (list, tuple)) and len(callback) == 2 and callback[0] == "unlock_location":
        game.location_manager.complete_location_unlock(callback[1])

class Quest:
    def __init__(self, name, description, reward_money, reward_rp, quest_type="generic",
                 requirements=None, on_complete=None, milestone=None, destination=None, rewards=None):
        self.name = name
        self.description = description
        self.destination = destination
        self.reward_money = reward_money
        self.reward_rp = reward_rp  # Research Points reward
        self.quest_type = quest_type
        self.requirements = requirements or {}
        self.on_complete = on_complete
        self.milestone = milestone
        self.progress = 0
        self.completed = False
        self.target_progress = self.requirements.get('target_progress', 1)
        self.location_requirement = self.requirements.get('location_type', None)
        # Add additional rewards handling
        self.rewards = rewards or {}  # Store extra rewards like items

    def __eq__(self, other):
        """Define equality to help prevent duplicates"""
        if not isinstance(other, Quest):
            return False
        return (self.name == other.name and
                self.quest_type == other.quest_type)

    # Cantina quests from listen to gossip, added to Quest class
    def update_cantina_progress(self, event_data):
        """Update cantina quests based on trade actions"""
        if self.quest_type == "cantina":
            action = event_data.get("action", "")

            if action in ["buy", "sell"]:
                commodity = event_data.get("commodity")
                amount = event_data.get("amount", 0)

                if "Deliver" in self.name and commodity:
                    target_commodity = self.name.split()[2].lower()
                    if commodity == target_commodity:
                        self.progress += amount
                        return self.progress >= self.requirements.get("amount", 0)

            elif action == "passenger_delivered":
                self.progress += 1
                return self.progress >= self.requirements.get("count", 0)

        return False


    # What each kind of quest counts, and which requirement holds the target.
    # Quests count from the moment they were taken, never from the start of the game.
    COUNTED = {
        "combat": ("victories.{enemy_type}", ("amount", "victories"), 1, "victories"),
        "patrol": ("turn", ("turns", "patrol_turns"), 3, "turns on duty"),
        "research": ("research_gained", ("target_points",), 30, "research points gained"),
        "mining": ("acquired.{resource_type}", ("amount",), 50, "units"),
        "exploration": ("discovered.{location_type}", ("amount", "discoveries"), 1, "discoveries"),
        "rescue": ("events.disaster", ("rescues",), 1, "ships helped"),
        "trade": ("trades", ("trades",), 1, "trades"),
    }
    # Quests finished by arriving somewhere with something: (what, requirement key, amount key)
    DELIVERED = {
        "delivery": ("cargo", "commodity", "amount"),
        "mining_contract": ("cargo", "resource", "amount"),
        "item_delivery": ("item", "item", None),
        "character_delivery": ("passenger", "character", None),
        "story": ("visit", None, None),
    }

    def begin(self, game):
        """Remember where the counters stood when the quest was taken."""
        if not isinstance(getattr(self, "start", None), dict):
            self.start = game.quest_system.counters()

    def counted(self, game):
        """(done, target, unit) for a counted quest, or None."""
        spec = self.COUNTED.get(self.quest_type)
        if spec is None:
            return None
        key, target_keys, default, unit = spec
        fields = dict(self.requirements)
        fields.setdefault("enemy_type", "total")
        fields.setdefault("location_type", "any")
        fields.setdefault("resource_type", "salt")
        key = key.format(**fields)
        target = next((self.requirements[k] for k in target_keys if k in self.requirements), default)
        self.begin(game)
        now = game.quest_system.counters()
        done = now.get(key, 0) - self.start.get(key, 0)
        if self.quest_type == "mining":
            unit = self.requirements.get("resource_type", "salt")
        return max(0, int(done)), int(target), unit

    def holding(self, game):
        """For a delivery: does the ship carry what is to be delivered?"""
        what, key, amount_key = self.DELIVERED[self.quest_type]
        ship = game.ship
        if what == "cargo":
            return ship.cargo.get(self.requirements.get(key), 0) >= self.requirements.get(amount_key, 0)
        if what == "item":
            return ship.items.get(self.requirements.get(key), 0) > 0
        if what == "passenger":
            return self.quest_passenger(game) is not None
        return True

    def quest_passenger(self, game):
        for module in getattr(game.ship, "passenger_modules", []):
            for passenger in module.passengers:
                if passenger.name == self.requirements.get("character"):
                    return passenger
        return None

    def progress_text(self, game):
        counted = self.counted(game)
        if counted:
            done, target, unit = counted
            text = "%d/%d %s" % (min(done, target), target, unit)
            if self.quest_type == "trade" and self.requirements.get("min_profit"):
                profit = game.quest_system.counters()["profit"] - self.start.get("profit", 0)
                text += ", %s/%s profit" % (game.format_money(max(0, profit)),
                                            game.format_money(self.requirements["min_profit"]))
            return text
        if self.quest_type in self.DELIVERED:
            where = self.destination or "?"
            if self.quest_type == "story":
                return "go to %s" % where
            return "%s, then go to %s" % ("ready" if self.holding(game) else "not aboard yet", where)
        if self.quest_type.startswith("unlock_"):
            return "follow the lead: your next journey"
        return ""

    def check_completion(self, game):
        """Check if quest requirements are met"""
        if self.completed:
            return False
        counted = self.counted(game)
        if counted:
            done, target, _ = counted
            if self.quest_type == "trade" and self.requirements.get("min_profit"):
                profit = game.quest_system.counters()["profit"] - self.start.get("profit", 0)
                if profit < self.requirements["min_profit"]:
                    return False
            return done >= target
        if self.quest_type in self.DELIVERED:
            return game.current_location.name == self.destination and self.holding(game)
        # Generic quest completion check (location unlocks: a journey)
        return self.progress >= self.target_progress

    def hand_over(self, game):
        """A finished delivery leaves the ship: cargo, item or passenger."""
        what, key, amount_key = self.DELIVERED.get(self.quest_type, (None, None, None))
        ship = game.ship
        if what == "cargo":
            item = self.requirements.get(key)
            ship.cargo[item] = max(0, ship.cargo.get(item, 0) - self.requirements.get(amount_key, 0))
        elif what == "item":
            item = self.requirements.get(key)
            ship.items[item] = ship.items.get(item, 0) - 1
            if ship.items[item] <= 0:
                del ship.items[item]
        elif what == "passenger":
            passenger = self.quest_passenger(game)
            for module in getattr(ship, "passenger_modules", []):
                if passenger in module.passengers:
                    module.passengers.remove(passenger)

    def update_progress(self, event_data):
        """Update quest progress based on game events"""
        if self.completed:
            return False

        progress_made = False

        # Update based on event type
        if event_data.get("type") == "combat" and self.quest_type == "combat":
            if event_data.get("outcome") == "victory":
                self.progress += 1
                progress_made = True

        elif event_data.get("action") in ["buy", "sell"] and self.quest_type == "trade":
            commodity = event_data.get("commodity")
            if commodity == self.requirements.get("commodity"):
                self.progress += event_data.get("amount", 0)
                progress_made = True

        return progress_made

    def complete(self, game):
        """Complete the quest (the quest system pays the rewards)."""
        game.quest_system.complete_quest(self)


class QuestSystem:
    def __init__(self, game):
        self.game = game
        self.active_quests = []  # For Quest objects
        self.available_quests = []  # For tuple-based quests (legacy support)
        self.completed_quests = []
        self.story_progress = 0
        self.quest_ids = set()  # Track unique quest IDs
        self.quest_message_shown = set()  # Track shown quest messages
        self.research_gained = 0     # research points earned (spending does not undo it)
        self.acquired = {}           # units of each commodity that came aboard
        self.events_seen = {}        # random events by type
        self._last_seen = None

        # Quest line progression tracking

    MOST_ACTIVE = 6

    def watch(self):
        """Count what came in since the last look: research points, cargo."""
        ship = self.game.ship
        now = {"rp": ship.research_points, **{"cargo." + k: v for k, v in ship.cargo.items()}}
        last = getattr(self, "_last_seen", None) or now
        if now["rp"] > last.get("rp", now["rp"]):
            self.research_gained = getattr(self, "research_gained", 0) + now["rp"] - last["rp"]
        acquired = getattr(self, "acquired", None)
        if acquired is None:
            acquired = self.acquired = {}
        for key, value in now.items():
            if key.startswith("cargo.") and value > last.get(key, value):
                acquired[key[6:]] = acquired.get(key[6:], 0) + value - last[key]
        self._last_seen = now

    def counters(self):
        """Everything a quest can count, as it stands now."""
        self.watch()
        game = self.game
        ship = game.ship
        out = {"turn": game.turn, "trades": game.trades_completed,
               "profit": int(sum(ship.trade_profits.values())),
               "passengers": game.reputation_manager.total_passengers,
               "research_gained": getattr(self, "research_gained", 0),
               "discovered.any": game.count_discovered()}
        for kind, count in ship.combat_victories.items():
            out["victories." + kind] = count
        for place_type in STORY_PLACE_TYPES:
            out["discovered." + place_type] = game.count_discovered(place_type)
        for item, count in (getattr(self, "acquired", None) or {}).items():
            out["acquired." + item] = count
        for kind, count in (getattr(self, "events_seen", None) or {}).items():
            out["events." + kind] = count
        return out

    def check_active_quests(self):
        for quest in list(self.active_quests):
            if quest.check_completion(self.game):
                self.complete_quest(quest)

    def display_quests(self):
        """Display all active quests"""
        active_quests = [q for q in self.active_quests if isinstance(q, Quest)]
        if active_quests:
            quest_content = [["Active Quests"]]
            quest_content.append([""])
            for quest in active_quests:
                quest_content.append([quest.name])
                quest_content.append([f"└─ {quest.description}"])
                quest_content.append([f"└─ Rewards: {self.game.format_money(quest.reward_money)} credits, {quest.reward_rp} RP"])
                progress = quest.progress_text(self.game)
                if progress:
                    quest_content.append([f"└─ Progress: {progress}"])
                quest_content.append([""])

            print(self.game.create_box(quest_content, 'double'))
        else:
            self.game.display_simple_message("No active quests.")

        input("Press Enter to continue...")

    def update_from_trade(self, trade_data):
        """Update quests based on trade actions"""
        for quest in self.active_quests:
            if quest.quest_type == "trade":
                # Check if trade matches quest requirements
                if trade_data.get('action') == 'buy' or trade_data.get('action') == 'sell':
                    commodity = trade_data.get('commodity')
                    amount = trade_data.get('amount', 0)

                    # Update trade-specific quests
                    if 'commodity' in quest.requirements:
                        if commodity == quest.requirements['commodity']:
                            quest.progress += amount

                            # Display quest progress
                            self.display_quest_progress(quest)

                            # Check if quest is completed
                            if quest.check_completion(self.game):
                                self.complete_quest(quest)

        # Update cantina-type quests if they exist
        for quest in self.active_quests:
            if hasattr(quest, 'update_cantina_progress'):
                quest.update_cantina_progress(trade_data)


    def update_discovery_quests(self, location):
        """Update quests that involve location discovery"""
        for quest in self.active_quests:
            if quest.quest_type == "exploration":
                if "location_type" in quest.requirements:
                    if location.location_type == quest.requirements["location_type"]:
                        quest.progress += 1
                        self.display_quest_progress(quest)

                        if quest.check_completion(self.game):
                            self.complete_quest(quest)

                elif "specific_location" in quest.requirements:
                    if location.name == quest.requirements["specific_location"]:
                        quest.progress += 1
                        self.display_quest_progress(quest)

                        if quest.check_completion(self.game):
                            self.complete_quest(quest)

            elif quest.quest_type == "location_unlock":
                if "location_type" in quest.requirements:
                    if location.location_type == quest.requirements["location_type"]:
                        quest.progress += 1
                        self.display_quest_progress(quest)

                        if quest.check_completion(self.game):
                            self.complete_quest(quest)

    # Add these methods to the QuestSystem class

    def update_cargo_quests(self, cargo_lost):
        """Update quests that involve cargo requirements"""
        for quest in self.active_quests:
            if quest.quest_type == "cargo" or quest.quest_type == "trade":
                # Check if quest requires specific cargo type that was lost
                if "cargo_type" in quest.requirements:
                    cargo_type = quest.requirements["cargo_type"]
                    if cargo_type in cargo_lost:
                        # Update progress based on remaining cargo
                        remaining_cargo = self.game.ship.cargo[cargo_type]
                        if "target_amount" in quest.requirements:
                            quest.progress = remaining_cargo / quest.requirements["target_amount"]
                        self.display_quest_progress(quest)

    def update_money_quests(self, money_lost):
        """Update quests that involve money requirements"""
        if money_lost > 0:  # Only process if money was actually lost
            for quest in self.active_quests:
                # Check trade profit quests
                if quest.quest_type == "profit" or quest.quest_type == "trade":
                    if "target_money" in quest.requirements:
                        current_money = self.game.ship.money
                        target_money = quest.requirements["target_money"]
                        quest.progress = max(0, min(1.0, current_money / target_money))
                        self.display_quest_progress(quest)

                # Check money protection quests
                if quest.quest_type == "protect" and "max_money_loss" in quest.requirements:
                    if money_lost > quest.requirements["max_money_loss"]:
                        quest.failed = True
                        self.game.display_simple_message(f"Quest failed: Lost too much money!")
                        self.active_quests.remove(quest)

                # Update trade margin quests
                if quest.quest_type == "margin" and "min_balance" in quest.requirements:
                    if self.game.ship.money < quest.requirements["min_balance"]:
                        quest.progress = max(0.0, quest.progress - 0.2)  # Lose 20% progress
                        self.display_quest_progress(quest)

    def update_combat_quests(self, damage_taken):
        """Update quests that involve combat requirements"""
        for quest in self.active_quests:
            if quest.quest_type == "combat":
                # Update survival quests
                if "max_damage" in quest.requirements:
                    if damage_taken > quest.requirements["max_damage"]:
                        quest.failed = True
                        self.display_quest_progress(quest)

                # Update combat victory quests that require minimal damage
                if "damage_threshold" in quest.requirements:
                    if damage_taken <= quest.requirements["damage_threshold"]:
                        quest.progress += 1
                        self.display_quest_progress(quest)


    def check_event_requirements(self, event_result):
        """Count the event, then see whether it finished a quest."""
        event_type = event_result.get("type", "")
        seen = getattr(self, "events_seen", None)
        if seen is None:
            seen = self.events_seen = {}
        seen[event_type] = seen.get(event_type, 0) + 1
        self.check_active_quests()

    def generate_quest(self, quest_type, difficulty):
        """Generate a quest based on type and difficulty"""
        base_reward = 1000 * (difficulty + 1)
        research_reward = 50 * (difficulty + 1)

        quest_templates = {
            "mining": [
                {
                    "name": f"Mine {50 * (difficulty + 1)} units of salt",
                    "description": "Extract valuable minerals from the asteroid field",
                    "type": "mining",
                    "requirements": {
                        "resource_type": "salt",
                        "amount": 50 * (difficulty + 1)
                    },
                    "reward_money": base_reward,
                    "reward_rp": research_reward
                },
                {
                    "name": f"Extract {40 * (difficulty + 1)} units of fuel",
                    "description": "Extract fuel from deep space deposits",
                    "type": "mining",
                    "requirements": {
                        "resource_type": "fuel",
                        "amount": 40 * (difficulty + 1)
                    },
                    "reward_money": int(base_reward * 1.2),
                    "reward_rp": int(research_reward * 1.2)
                }
            ],
            "combat": [
                {
                    "name": f"Eliminate {2 * (difficulty + 1)} pirate ships",
                    "description": "Clear the sector of pirate activity",
                    "type": "combat",
                    "requirements": {
                        "enemy_type": "pirate",
                        "amount": 2 * (difficulty + 1)
                    },
                    "reward_money": int(base_reward * 1.5),
                    "reward_rp": int(research_reward * 1.5)
                },
                {
                    "name": f"Defend trade route for {3 * (difficulty + 1)} turns",
                    "description": "Maintain security in a trade route",
                    "type": "patrol",
                    "requirements": {
                        "turns": 3 * (difficulty + 1)
                    },
                    "reward_money": int(base_reward * 1.3),
                    "reward_rp": int(research_reward * 1.3)
                }
            ],
            "research": [
                {
                    "name": f"Collect {30 * (difficulty + 1)} research data",
                    "description": "Gather scientific data from space phenomena",
                    "type": "research",
                    "requirements": {
                        "research_type": "data",
                        "target_points": 30 * (difficulty + 1)
                    },
                    "reward_money": int(base_reward * 1.2),
                    "reward_rp": int(research_reward * 2)
                }
            ],
            "story": [
                {
                    "name": "Investigate mysterious signals",
                    "description": "Track down the source of unusual transmissions",
                    "type": "story",
                    "requirements": {
                        "story_progression": 1
                    },
                    "reward_money": int(base_reward * 2),
                    "reward_rp": int(research_reward * 3)
                }
            ]
        }

        # Select a random quest template
        if quest_type in quest_templates:
            template = random.choice(quest_templates[quest_type])
            destination = None
            description = template["description"]
            if template["type"] == "story":
                places = [name for name in self.game.known_locations
                          if name != self.game.current_location.name]
                if not places:
                    return None
                destination = random.choice(places)
                description += " (the trail leads to %s)" % destination
            quest = Quest(
                name=template["name"],
                description=description,
                reward_money=template["reward_money"],
                reward_rp=template["reward_rp"],
                quest_type=template["type"],
                requirements=template["requirements"],
                destination=destination
            )
            return quest
        return None


    def generate_cantina_quest(self):
        """Generate quests based on player's progress and reputation"""
        current_location = self.game.current_location.name
        quest_types = {
            "delivery": {
                "name": "Urgent Delivery",
                "description": lambda details: f"Deliver {details['amount']} {details['commodity']} to {details['destination']}",
                "requirements": {
                    "amount": (50, 150),
                    "commodity": ["tech", "agri"],
                    "time_limit": 5,
                    "min_plot_points": 10,
                    "min_reputation": 0
                },
                "rewards": {
                    "money": (5000, 10000),
                    "research_points": (50, 100),
                    "reputation": 2,
                    "items": ["scanner", "probe"]  # Possible bonus items
                }
            },
            "item_delivery": {
                "name": "Special Item Contract",
                "description": lambda details: f"Deliver {details['item']} to {details['destination']}",
                "requirements": {
                    "item": ["scanner", "shield", "probe", "turrets"],
                    "min_plot_points": 20,
                    "min_reputation": 20
                },
                "rewards": {
                    "money": (8000, 15000),
                    "research_points": (80, 150),
                    "reputation": 3,
                    "items": ["quantum_core", "neural_hack"]  # High-tier rewards
                }
            },
            "character_delivery": {
                "name": "VIP Transport",
                "description": lambda details: f"Transport {details['character']} to {details['destination']}",
                "requirements": {
                    "character": ["Research Director", "Trade Minister", "Military Commander"],
                    "min_reputation": 50,
                    "min_plot_points": 40
                },
                "rewards": {
                    "money": (12000, 20000),
                    "research_points": (100, 200),
                    "reputation": 5,
                    "plot_points": 2,
                    "items": ["neural_boost", "quantum_shield"]
                }
            },
            "mining_contract": {
                "name": "Resource Contract",
                "description": lambda details: f"Mine and deliver {details['amount']} {details['resource']} to {details['destination']}",
                "requirements": {
                    "amount": (100, 200),
                    "resource": ["salt", "fuel"],
                    "min_plot_points": 15,
                    "min_reputation": 10
                },
                "rewards": {
                    "money": (6000, 12000),
                    "research_points": (60, 120),
                    "reputation": 2,
                    "items": ["mining_laser", "cargo_scanner"]
                }
            }
        }

        # Filter quests based on player's progress
        available_quests = []
        for quest_type, template in quest_types.items():
            reqs = template["requirements"]
            if (self.game.story_manager.plot_points >= reqs.get("min_plot_points", 0) and
                self.game.ship.passenger_reputation >= reqs.get("min_reputation", 0)):
                available_quests.append((quest_type, template))

        if not available_quests:
            return None

        quest_type, template = random.choice(available_quests)

        # Generate quest details
        details = {}
        for key, value in template["requirements"].items():
            if isinstance(value, list):
                details[key] = random.choice(value)
            elif isinstance(value, tuple) and len(value) == 2:
                details[key] = random.randint(*value)
            elif key not in ["min_plot_points", "min_reputation"]:
                details[key] = value

        # Choose destination from known locations excluding current location
        possible_destinations = [loc for loc in self.game.known_locations
                            if loc != current_location]
        if not possible_destinations:
            return None

        details['destination'] = random.choice(possible_destinations)

        # Generate rewards
        base_rewards = template["rewards"]
        rewards = {
            "money": random.randint(*base_rewards["money"]),
            "research_points": random.randint(*base_rewards["research_points"]),
            "reputation": base_rewards.get("reputation", 0),
            "plot_points": base_rewards.get("plot_points", 0)
        }

        # Chance for bonus item
        if random.random() < 0.3 and "items" in base_rewards:  # 30% chance
            rewards["bonus_item"] = random.choice(base_rewards["items"])

        # Scale rewards based on chapter and difficulty
        chapter_multiplier = 1 + (self.game.story_manager.get_chapter_number() * 0.2)
        rep_multiplier = 1 + (template["requirements"].get("min_reputation", 0) / 100)

        for key in ["money", "research_points"]:
            rewards[key] = int(rewards[key] * chapter_multiplier * rep_multiplier)

        return Quest(
            name=template["name"],
            description=template["description"](details),
            reward_money=rewards["money"],
            reward_rp=rewards["research_points"],
            quest_type=quest_type,
            requirements=details,
            rewards=rewards,
            destination=details['destination']  # Add destination
        )

    def update_from_travel(self, travel_data):
        """Update quests based on travel actions"""
        for quest in list(self.active_quests):
            # A quest that opens a new kind of location is a lead to follow:
            # the next journey after it appears completes it.
            if quest.quest_type.startswith("unlock_"):
                quest.progress += 1
                if quest.check_completion(self.game):
                    self.complete_quest(quest)
                continue
            if quest.quest_type == "exploration" or quest.quest_type == "location_unlock":
                # Check location discovery requirements
                if "destination" in travel_data:
                    if quest.requirements.get('specific_location') == travel_data['destination']:
                        quest.progress += 1

                        # Display quest progress
                        self.display_quest_progress(quest)

                        # Check if quest is completed
                        if quest.check_completion(self.game):
                            self.complete_quest(quest)

    def complete_quest(self, quest):
        """Handle quest completion and cleanup with full quest lifecycle"""
        quest_id = f"{quest.name}_{quest.quest_type}"

        if quest in self.active_quests:
            # Remove from active quests and add to completed
            self.active_quests.remove(quest)
            self.completed_quests.append(quest)

            # Award rewards (and hand over what was delivered)
            quest.hand_over(self.game)
            self.game.ship.money += quest.reward_money
            self.game.ship.research_points += quest.reward_rp
            extras = getattr(quest, "rewards", None) or {}
            if extras.get("reputation"):
                self.game.ship.passenger_reputation += extras["reputation"]
            if extras.get("plot_points"):
                self.game.story_manager.plot_points += extras["plot_points"]
            if extras.get("bonus_item"):
                self.game.ship.acquire_item(extras["bonus_item"])

            # Apply any special effects based on quest type
            if quest.quest_type == 'mining':
                self.game.current_location.exogeology = min(100,
                    self.game.current_location.exogeology + 5)  # Small mining efficiency boost
            elif quest.quest_type == 'research':
                boost = int(quest.reward_rp * 0.1)  # 10% bonus research points
                self.game.ship.research_points += boost

            # Execute completion callback if exists
            if quest.on_complete:
                run_quest_callback(self.game, quest.on_complete)

            # Mark quest as completed
            quest.completed = True

            # Clean up message tracking
            if quest_id in self.quest_message_shown:
                self.quest_message_shown.remove(quest_id)

            # Display completion message
            lines = [f"Quest Completed: {quest.name}", "Rewards:",
                     f"• {self.game.format_money(quest.reward_money)} credits",
                     f"• {quest.reward_rp} research points"]
            if extras.get("reputation"):
                lines.append(f"• +{extras['reputation']} reputation")
            if extras.get("plot_points"):
                lines.append(f"• +{extras['plot_points']} plot points")
            if extras.get("bonus_item"):
                lines.append(f"• Bonus item: {extras['bonus_item']}")
            self.game.display_story_message(lines)

            # Update story progression if applicable
            if hasattr(self.game, 'story_manager'):
                self.game.story_manager.handle_quest_completion(quest)

            # Check for milestone completion
            if hasattr(self.game, 'check_milestone_triggers'):
                self.game.check_milestone_triggers()

            return True

        return False


    def display_quest_progress(self, quest):
        """Display quest progress update"""
        if isinstance(quest, Quest):
            progress_text = f"Quest Progress: {quest.name}"
            if quest.target_progress > 1:
                progress_text += f" ({quest.progress}/{quest.target_progress})"
            self.game.display_simple_message(progress_text)


    def add_quest(self, quest):
        """Add a new quest with duplication check"""
        if quest is None:
            return False
        # Create unique identifier for the quest
        quest_id = f"{quest.name}_{quest.quest_type}"

        # Check if quest is already active
        existing_quest = any(q.name == quest.name and q.quest_type == quest.quest_type
                           for q in self.active_quests)
        if existing_quest:
            return False  # Don't add duplicate quest
        if len(self.active_quests) >= self.MOST_ACTIVE and not quest.quest_type.startswith("unlock_"):
            return False  # enough on the board already
        quest.begin(self.game)
        if quest.quest_type == "character_delivery":
            # the passenger waits at this port for the captain to board them
            port = self.game.port_system
            passenger = Passenger(quest.requirements["character"], quest.destination, wealth_level=5)
            passenger.is_quest_passenger = True
            port.waiting_passengers.setdefault(self.game.current_location.name, []).append(passenger)

        # Check if we've already shown this quest message
        if quest_id not in self.quest_message_shown:
            self.game.display_story_message([
                "New Quest Available!",
                quest.name,
                quest.description,
                f"Rewards: {self.game.format_money(quest.reward_money)} credits, {quest.reward_rp} RP"
            ])
            self.quest_message_shown.add(quest_id)

        # Add quest to active quests
        self.active_quests.append(quest)
        return True


class ResourceTransportQuest:
    def __init__(self, game):
        self.game = game
        self.active_missions = []


# The game's other modules, imported last so that the modules can refer to each other.
from .captain import STORY_PLACE_TYPES  # noqa: E402
from .passengers import Passenger  # noqa: E402
