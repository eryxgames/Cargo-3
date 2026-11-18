"""Passengers, cabins and the captain's reputation with travellers."""
import random

class PassengerModule:
    def __init__(self, name, capacity, comfort_level, cost):
        self.name = name
        self.capacity = capacity  # How many passengers it can hold
        self.comfort_level = comfort_level  # 1-5, affects passenger satisfaction and payment
        self.cost = cost
        self.passengers = []

class Passenger:
    def __init__(self, name, destination, wealth_level):
        self.name = name
        self.destination = destination
        self.wealth_level = wealth_level  # 1-5
        self.satisfaction = 100
        self.turns_waiting = 0
        # Add passenger classification
        self.classification = self.generate_classification()

    def generate_classification(self):
        classifications = [
            ("S", "Scientist", "science"),
            ("M", "Military", "military"),
            ("E", "Engineer", "engineering"),
            ("T", "Trader", "trade"),
            ("D", "Diplomat", "diplomacy"),
            ("R", "Researcher", "research")
        ]
        class_code, class_name, class_type = random.choice(classifications)
        return {
            "code": class_code,
            "name": class_name,
            "type": class_type
        }

class PassengerReputationManager:
    """Manages passenger reputation effects and related story/character events"""
    def __init__(self, game):
        self.game = game
        self.reputation_thresholds = {
            20: "Reliable Transport",
            40: "Luxury Provider",
            60: "Elite Service",
            80: "Legendary Captain",
            100: "Stellar Legend"
        }
        self.vip_characters = {
            "Ambassador": {
                "rep_required": 30,
                "plot_points": 3,
                "rewards": {"money": 15000, "reputation": 10}
            },
            "Corporate Executive": {
                "rep_required": 50,
                "plot_points": 5,
                "rewards": {"money": 25000, "reputation": 15}
            },
            "Research Director": {
                "rep_required": 70,
                "plot_points": 8,
                "rewards": {"money": 40000, "reputation": 20}
            }
        }
        self.last_vip_spawn = 0
        self.spawned_characters = set()
                # Add total_passengers tracking
        self.total_passengers = 0

    def update_reputation(self, satisfaction, passenger=None):
        """Update passenger reputation based on satisfaction"""
        base_change = (satisfaction - 75) / 25  # -1 to +1 base change

        # Apply modifiers based on passenger class
        class_multipliers = {
            "S": 1.5,  # Scientists
            "M": 1.3,  # Military
            "E": 1.4   # Engineers
        }

        # Get passenger's class if available
        if passenger and hasattr(passenger, 'classification'):
            passenger_class = passenger.classification.get('code', '')
            multiplier = class_multipliers.get(passenger_class, 1.0)
        else:
            multiplier = 1.0

        reputation_change = base_change * multiplier

        # Apply final change and round to one decimal
        old_rep = self.game.ship.passenger_reputation
        self.game.ship.passenger_reputation = round(max(-100, min(100,
            self.game.ship.passenger_reputation + reputation_change)), 1)

        # Check for threshold crossings
        self.check_reputation_thresholds(old_rep, self.game.ship.passenger_reputation)

        return round(reputation_change, 1)  # Also round the return value

    def check_reputation_thresholds(self, old_rep, new_rep):
        """Check if any reputation thresholds were crossed"""
        for threshold, title in self.reputation_thresholds.items():
            if old_rep < threshold <= new_rep:
                self.game.display_story_message([
                    f"Reputation Milestone Achieved: {title}!",
                    "Your excellent service is becoming legendary.",
                    f"Passenger Reputation: {int(new_rep)}"
                ])
                # Trigger appropriate events
                self.check_character_spawns()

    def check_character_spawns(self):
        """Check if it's time to spawn a VIP character"""
        current_turn = self.game.turn
        reputation = self.game.ship.passenger_reputation

        # Only spawn every 5 turns minimum
        if current_turn - self.last_vip_spawn < 5:
            return

        # Check VIP characters
        for char_type, data in self.vip_characters.items():
            if (reputation >= data["rep_required"] and
                char_type not in self.spawned_characters and
                random.random() < 0.3):  # 30% chance if all conditions met

                # Generate VIP character
                character = self.game.character_generators["human"].generate_character(
                    title=char_type,
                    specialization="VIP"
                )

                # Add to waiting passengers
                if self.game.current_location.name in self.game.port_system.waiting_passengers:
                    passenger = Passenger(
                        character.name,
                        random.choice(list(self.game.known_locations)),
                        wealth_level=5
                    )
                    passenger.is_vip = True
                    passenger.rewards = data["rewards"]
                    passenger.plot_points = data["plot_points"]

                    self.game.port_system.waiting_passengers[
                        self.game.current_location.name].append(passenger)

                    self.game.display_story_message([
                        f"VIP Passenger Available: {char_type} {character.name}",
                        "Your reputation has attracted important attention!",
                        f"Rewards: {self.game.format_money(data['rewards']['money'])} credits",
                        f"Plot Points: {data['plot_points']}"
                    ])

                    self.spawned_characters.add(char_type)
                    self.last_vip_spawn = current_turn

    # Update to use enhanced systems of special passengers
    def spawn_special_passenger(self):
        """A VIP asks to board when the captain's reputation has earned one.
        (Story passengers - envoys, rebels, scholars - come from the story now.)"""
        if (self.game.ship.passenger_reputation >= 40 and
                self.game.turn - self.last_vip_spawn >= 5):
            vip_character = self.game.character_generators["human"].generate_vip_passenger()
            return bool(self.add_special_passenger_to_port(vip_character))
        return False

    def add_special_passenger_to_port(self, character):
        """Add a special character as a passenger to the current port with full attributes

        Args:
            character: The special character to add
        """
        if self.game.current_location.name in self.game.port_system.waiting_passengers:
            # Create base passenger with known destination
            available_destinations = [loc for loc in self.game.known_locations
                                    if loc != self.game.current_location.name]
            if not available_destinations:
                return False  # Can't add passenger with no valid destinations

            passenger = Passenger(
                name=character.name,
                destination=random.choice(available_destinations),
                wealth_level=5  # Special characters are always high wealth
            )

            # Add base character attributes
            passenger.character = character
            passenger.is_special = True
            passenger.full_name = character.full_name
            passenger.title = character.title
            passenger.satisfaction = 100  # Start at max satisfaction

            # Handle different character types
            message = [f"Special Passenger Available: {character.title} {character.name}"]
            if hasattr(character, 'rewards'):
                # VIP character attributes
                passenger.is_vip = True
                passenger.rewards = character.rewards
                passenger.special_abilities = getattr(character, 'special_abilities', [])
                passenger.reputation_bonus = 15
                passenger.classification = {
                    "code": "V",
                    "name": "VIP",
                    "type": character.specialization
                }
                message = [
                    f"VIP Passenger Available: {character.title} {character.name}",
                    f"Potential Reward: {self.game.format_money(character.rewards['base_money'])} credits",
                    f"Reputation Bonus: +{passenger.reputation_bonus}",
                    "Find them waiting at the port"
                ]
                if passenger.special_abilities:
                    message.append(f"Special Ability: {passenger.special_abilities[0]}")

            elif character.title.startswith(("Neurodroid", "Agrobot")):
                # Synthetic character attributes
                passenger.is_synthetic = True
                passenger.uprising_chance = getattr(character, 'uprising_chance', 0.2)
                passenger.demands = getattr(character, 'demands', None)
                passenger.reputation_bonus = 25
                passenger.plot_points = 15
                message = [
                    f"Synthetic Entity Requesting Transport: {character.title}",
                    "This passenger represents significant risk and reward...",
                    f"Reputation Bonus: +{passenger.reputation_bonus}",
                    "Exercise caution in your decision"
                ]

            else:
                # Alien or other special character attributes
                passenger.is_alien = True
                passenger.culture = getattr(character, 'culture', 'Unknown')
                passenger.tech_bonus = getattr(character, 'tech_bonus', 0)
                passenger.trade_multiplier = getattr(character, 'trade_multiplier', 1.0)
                passenger.reputation_bonus = 18
                message = [
                    f"Alien Dignitary Available: {character.title} {character.name}",
                    f"Culture: {passenger.culture}",
                    f"Reputation Bonus: +{passenger.reputation_bonus}",
                    "This passenger may offer unique opportunities"
                ]

            # Add requirements for luxury accomodation
            passenger.minimum_comfort_level = 4  # Require high comfort level
            passenger.bonus_threshold = 90  # High satisfaction threshold for bonuses

            # Add to waiting passengers
            self.game.port_system.waiting_passengers[
                self.game.current_location.name].append(passenger)

            # Display announcement
            self.game.display_story_message(message)

            # Mark character as spawned
            self.spawned_characters.add(character.title)
            self.last_vip_spawn = self.game.turn

            return True

        return False

    def handle_vip_delivery(self, passenger):
        """Handle delivery of VIP passenger"""
        if hasattr(passenger, 'is_vip') and passenger.is_vip:
            # Award rewards (VIP templates call their fee "base_money")
            rewards = getattr(passenger, 'rewards', None) or {}
            money = rewards.get("money", rewards.get("base_money", 0))
            reputation = rewards.get("reputation", 0)
            plot_points = getattr(passenger, 'plot_points', 0)
            self.game.ship.money += money
            self.game.ship.passenger_reputation += reputation
            self.game.story_manager.plot_points += plot_points

            self.game.display_story_message([
                "VIP Passenger Successfully Delivered!",
                f"Earned {self.game.format_money(money)} credits",
                f"Reputation +{reputation}",
                f"Plot Points +{plot_points}"
            ])

    def get_fare_multiplier(self):
        """Get fare multiplier based on reputation"""
        reputation = self.game.ship.passenger_reputation
        if reputation >= 80:
            return 2.0
        elif reputation >= 60:
            return 1.5
        elif reputation >= 40:
            return 1.3
        elif reputation >= 20:
            return 1.1
        return 1.0
