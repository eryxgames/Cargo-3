"""Travel between places, and the lanes that hurt lighter hulls."""
import random

class TravelMixin:
    """The Game's travel between places. Game inherits it (game/world.py)."""
    def handle_travel(self):
        """Centralized travel handler that can be called from anywhere in the game"""
        if "navcomp" in self.ship.items:
            self.display_simple_message("Choose a location to travel to:")
            # Display known locations with numbers
            for i, location in enumerate(self.known_locations, 1):
                hop = " (this system: a hop on your own fuel)" if self.same_system(self.current_location, location) \
                    and location != self.current_location.name else ""
                print(f"{i}. {location}{hop}")

            self.display_simple_message("Enter the number or name of the location (or 'cancel'): ", 0)
            choice = input(">>> ").strip()

            if not choice or choice.lower() == 'cancel':
                self.display_simple_message("Travel cancelled.")
                return False

            if choice.isdigit():
                index = int(choice) - 1
                if 0 <= index < len(self.known_locations):
                    return self.travel_to_location(self.known_locations[index])
                else:
                    self.display_simple_message("Invalid location number.")
                    return False
            else:
                return self.travel_to_location(choice)
        else:
            self.display_simple_message("Enter location name (or 'cancel'): ", 0)
            location_name = input(">>> ").strip()

            if not location_name or location_name.lower() == 'cancel':
                self.display_simple_message("Travel cancelled.")
                return False

            return self.travel_to_location(location_name)

    def travel_to_location(self, location_name):
        """Handle travel to a new location"""
        # Convert input to lowercase for case-insensitive comparison
        target_name = location_name.lower()

        # Find location by exact name match
        found_location = None
        for location in self.locations:
            if location.name.lower() == target_name:
                found_location = location
                break

        if found_location:
            old_location = self.current_location
            self.in_needle = False
            if self.same_system(old_location, found_location):
                self.fly_in_system(found_location)
            elif self.book_needle(found_location) is None:
                return False                  # stayed: no needle, no turn
            self.current_location = found_location

            # Initialize and update discovered locations
            if not hasattr(self, 'discovered_locations'):
                self.discovered_locations = set([old_location.name])
            first_visit = found_location.name not in self.discovered_locations
            self.discovered_locations.add(found_location.name)

            self.arrive_through_hazard(found_location)
            self.play_music()
            if first_visit:
                self.story_manager.plot_points += 3
                about = (story_data()["places"].get(found_location.name) or {}).get("about")
                self.display_simple_message(f"Traveled to {found_location.name}. First visit: +3 plot points."
                                            + (" " + about if about else ""))
            else:
                self.display_simple_message(f"Traveled to {found_location.name}.")

            # Calculate research exchange based on location differences
            research_difference = found_location.research_points - old_location.research_points

            # Base gain is the location's research points if first visit
            if found_location.name not in self.known_locations:
                base_research = found_location.research_points
                self.known_locations.append(found_location.name)
                # Trigger location discovery event
                if hasattr(self, 'location_manager'):
                    self.location_manager.handle_location_discovery(found_location)
            else:
                # For revisits, only get bonus from research difference if positive
                base_research = max(0, research_difference)

            # Apply bonus based on research difference
            if research_difference > 0:
                research_bonus = int(research_difference * 0.2)  # 20% of the difference
            else:
                research_bonus = int(abs(research_difference) * 0.1)  # 10% of the difference

            # Apply rank multiplier to the bonus
            rank_multiplier = {
                "Explorer": 1.0,
                "Pilot": 1.2,
                "Captain": 1.5,
                "Commander": 1.8,
                "Star Commander": 2.2,
                "Space Admiral": 2.5,
                "Stellar Hero": 3.0,
                "Galactic Legend": 3.5
            }.get(self.rank, 1.0)

            # Calculate final research gain
            total_gain = base_research + max(1, int(research_bonus * rank_multiplier * (1 + self.difficulty)))

            # Add research points to the ship (a research module and an analyzer add a share)
            total_gain = int(total_gain * (1 + self.ship.research_bonus()) * self.concord_research_factor()
                             * (CHARTS_RESEARCH if self.has_equipment("institute_charts") else 1))
            self.ship.research_points += total_gain

            # After successful travel for quest
            self.quest_system.update_from_travel({
                "destination": location_name,
                "turn": self.turn
            })

            # Display informative message about research gain
            if found_location.name not in self.known_locations:
                self.display_simple_message(f"Gained {total_gain} research points from discovering new location!")
            elif research_difference > 0:
                self.display_simple_message(f"Gained {total_gain} research points from clearing orbital junk!")
            else:
                self.display_simple_message(f"Gained {total_gain} research points from salvaged debris!")

            self.turn += 1
            self.shop.reset_turn()
            self.in_needle = getattr(self, "needle_position", None) is not None and not self.same_system(
                old_location, found_location)
            self.random_event()
            self.in_needle = False
            self.after_needle()
            self.needle_risk = 1.0
            self.autosave()
            return True
        else:
            # More informative error message
            if "navcomp" in self.ship.items:
                self.display_simple_message("Location not found. Known locations:")
                for i, loc in enumerate(self.known_locations, 1):
                    print(f"{i}. {loc}")
            else:
                self.display_simple_message(f"Location '{location_name}' not found or not yet discovered.")
            return False

    # Lanes that wear a hull: (hull class that rides them out, damage range otherwise)
    ROUGH_PLACES = ("DeepSpaceOutpost", "Ancient Ruins", "Alien Signal Research Outpost")
    DEEP_PLACES = ("Stator Field Megastructure", "Builder Site", "Zeta", "Eta", "Theta", "Omega-1", "DSO-Delta")

    def lane_hazard(self, loc):
        """How hard the way to `loc` is on a hull: 0 easy, 1 rough, 2 deep."""
        if loc.name in self.DEEP_PLACES:
            return 2
        if loc.location_type in self.ROUGH_PLACES:
            return 1
        return 0

    def arrive_through_hazard(self, loc):
        """A hull too light for the lane takes a beating on the way."""
        need = self.lane_hazard(loc)
        hull = self.ship.hull
        if need <= hull:
            return
        low, high = (10, 20) if need == 1 else ((20, 35) if hull == 1 else (30, 45))
        hit = random.randint(low, high)
        shielded = self.ship.working("rad")
        if shielded:
            hit //= 2
        self.ship.damage = min(99, self.ship.damage + hit)
        lines = ["The way to %s is %s, and the %s was not built for it: hull damage +%d%%%s." % (
            loc.name, "rough" if need == 1 else "deep and empty", self.ship.hull_info()["name"].lower(), hit,
            " (the radiation shielding took half)" if shielded else "")]
        if not shielded:
            self.wear_modules(hit, "the lane")
        if random.random() < 0.3:
            goods = [g for g in ('tech', 'agri', 'salt', 'fuel') if self.ship.cargo[g] > 0]
            if goods:
                good = random.choice(goods)
                lost = max(1, self.ship.cargo[good] // 10)
                self.ship.cargo[good] -= lost
                lines.append("A hold seal gives: %d %s lost." % (lost, good))
        lines.append("An %s hull (planet shipyards, upgrade/u, hull) would ride it out." % (
            "Ironback or Farstrider" if need == 1 else "Farstrider"))
        self.display_simple_message([line for text in lines for line in self.word_wrap(text)], 3, color='31')


# The game's other modules, imported last so that the modules can refer to each other.
from .story import story_data  # noqa: E402
from .looking import CHARTS_RESEARCH  # noqa: E402
