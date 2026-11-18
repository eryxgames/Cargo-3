"""Score, ranks and their rewards."""

class RanksMixin:
    """The Game's score and ranks. Game inherits it (game/world.py)."""
    # ... The end score ...

    def display_score(self):
        """Display final game score and statistics in a formatted box"""
        # Calculate final statistics (a captain without a ship has no hold)
        cargo = self.ship.cargo if self.ship is not None else {"tech": 0, "agri": 0, "salt": 0, "fuel": 0}
        total_cargo_value = (cargo['tech'] * 10) + (cargo['agri'] * 5) + \
                           (cargo['salt'] * 15) + (cargo['fuel'] * 20)
        final_score = self.person.money + total_cargo_value
        efficiency_score = (final_score / self.turn) if self.turn > 0 else final_score

        # Create score content
        score_content = [
            ["FINAL SCORE REPORT", ""],  # Title row
            ["─" * 18, "─" * 18],  # Separator
            ["Assets", "Value"],
            ["Money", f"{self.format_money(self.person.money)}"],
            ["Tech Cargo", f"{self.format_money(cargo['tech'])} units"],
            ["Agri Cargo", f"{self.format_money(cargo['agri'])} units"],
            ["Salt Cargo", f"{self.format_money(cargo['salt'])} units"],
            ["Fuel Cargo", f"{self.format_money(cargo['fuel'])} units"],
            ["", ""],  # Empty row for spacing
            ["Performance Metrics", ""],
            ["Total Score", f"{self.format_money(final_score)}"],
            ["Efficiency Score", f"{self.format_money(efficiency_score)}/turn"],
            ["Turns Played", str(self.turn)],
            ["Final Rank", self.rank],
        ]
        if self.ship is not None:
            score_content += [
                ["", ""],  # Empty row for spacing
                ["Ship Statistics", ""],
                ["Attack Level", str(self.ship.attack)],
                ["Defense Level", str(self.ship.defense)],
                ["Speed Level", str(self.ship.speed)],
                ["Hull Damage", f"{self.ship.damage}%"]
            ]

        # Add equipment section if player has any
        if self.person.items:
            score_content.extend([
                ["", ""],  # Empty row for spacing
                ["Equipment", "Count"]
            ])
            for item, count in self.person.items.items():
                score_content.append([item.capitalize(), str(count)])

        # Add research section if player has any
        if hasattr(self, 'research') and self.research.unlocked_options:
            score_content.extend([
                ["", ""],  # Empty row for spacing
                ["Completed Research", ""]
            ])
            for research in self.research.unlocked_options:
                score_content.append([research.replace('_', ' ').title(), ""])

        # Create the box with double borders for emphasis
        fancy_box = self.create_box(score_content, 'double')
        print(fancy_box)

        # Display achievement message
        achievement_msg = self.get_achievement_message(final_score)
        self.display_simple_message(achievement_msg, style='round', color='32')  # Green color for achievement

    def get_achievement_message(self, score):
        """Generate an achievement message based on the final score"""
        if score >= 1000000:
            return f"Legendary Achievement! {self.player_name}, you have become a true Galactic Legend!"
        elif score >= 500000:
            return f"Outstanding Success! {self.player_name}, your name will be remembered among the Stellar Heroes!"
        elif score >= 200000:
            return f"Remarkable Victory! {self.player_name}, you have proven yourself as a Space Admiral!"
        elif score >= 100000:
            return f"Impressive Results! {self.player_name}, you have earned the title of Star Commander!"
        elif score >= 50000:
            return f"Well Done! {self.player_name}, you have become a respected Commander!"
        elif score >= 20000:
            return f"Good Job! {self.player_name}, you have proven yourself as a capable Captain!"
        elif score >= 10000:
            return f"Nice Work! {self.player_name}, you have graduated from Pilot to veteran trader!"
        else:
            return f"Game Complete! {self.player_name}, you have completed your journey as an Explorer!"

    def update_rank(self):
        cargo = self.ship.cargo if self.ship is not None else {}
        score = self.person.money + cargo.get('tech', 0) * 10 + cargo.get('agri', 0) * 5
        if score >= 1000000:
            self.rank = "Galactic Legend"
        elif score >= 500000:
            self.rank = "Stellar Hero"
        elif score >= 200000:
            self.rank = "Space Admiral"
        elif score >= 100000:
            self.rank = "Star Commander"
        elif score >= 50000:
            self.rank = "Commander"
        elif score >= 20000:
            self.rank = "Captain"
        elif score >= 10000:
            self.rank = "Pilot"
        else:
            self.rank = "Explorer"

    def rank_multiplier(self):
        if self.rank == "Galactic Legend":
            return 10
        elif self.rank == "Stellar Hero":
            return 8
        elif self.rank == "Space Admiral":
            return 6
        elif self.rank == "Star Commander":
            return 4
        elif self.rank == "Commander":
            return 2
        elif self.rank == "Captain":
            return 1.5
        elif self.rank == "Pilot":
            return 1.2
        else:
            return 1
