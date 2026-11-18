"""Research: what can be researched, and the Game's research, analysis and experiment screens."""
import random
import time

# The second tier (Cargo 2): branches that grow from the first six. Each pair excludes the other:
# researching one closes its twin for good. "story" names a scene that must have happened first.
BRANCHES = {
    "bulk_logistics": {"name": "Bulk logistics", "cost": 300, "requires": ["xenoeconomy"], "excludes": "fast_turnaround",
                       "about": "every container module holds 150 units, not 100"},
    "fast_turnaround": {"name": "Fast turnaround", "cost": 300, "requires": ["xenoeconomy"], "excludes": "bulk_logistics",
                        "about": "needle fares are 10% lower: you are always first at the buoy"},
    "fire_control": {"name": "Fire control", "cost": 350, "requires": ["telemetry"], "excludes": "countermeasure_suite",
                     "about": "better odds every round of a convoy fight"},
    "countermeasure_suite": {"name": "Countermeasure suite", "cost": 350, "requires": ["telemetry"],
                             "excludes": "fire_control", "about": "a shield module's countermeasures work twice a fight"},
    "drone_autonomy": {"name": "Drone autonomy", "cost": 400, "requires": ["telemetry", "geophysics"],
                       "excludes": "repair_swarm", "about": "a drone hangar is worth two points of attack, not one"},
    "repair_swarm": {"name": "Repair swarm", "cost": 400, "requires": ["telemetry", "geophysics"],
                     "excludes": "drone_autonomy", "about": "a repair bay mends twice as fast"},
    "segment_acoustics": {"name": "Segment acoustics", "cost": 450, "requires": ["chronopolitics"], "story": "ring.expedition",
                          "excludes": "throw_dynamics", "about": "hear a segment turn from a system away, as the machines do "
                                                                "(the Binary Dawn notices)"},
    "throw_dynamics": {"name": "Throw dynamics", "cost": 450, "requires": ["chronopolitics"], "story": "ring.expedition",
                       "excludes": "segment_acoustics", "about": "the mathematics of a segment's throw (House Rostrom "
                                                                 "wants it)"},
}


class Research:
    def __init__(self):
        self.unlocked_options = set()
        self.research_costs = {
            'xenoeconomy': 100,
            'telemetry': 150,
            'geophysics': 200,
            'chronopolitics': 250,
            'exogeology': 300,  # New research option
            'psychodynamics': 350  # New research option
        }
        self.research_benefits = {
            'xenoeconomy': {'tax_reduction': 0.02},
            'telemetry': {'scout_success': 0.2},
            'geophysics': {'exogeology': 0.15},
            'chronopolitics': {'revolution_success': 0.2},
            'exogeology': {'output_bonus': 0.25},
            'psychodynamics': {'price_control': 0.1}
        }


    def unlock(self, option):
        self.unlocked_options.add(option)

    def cost_of(self, option):
        return BRANCHES[option]["cost"] if option in BRANCHES else self.research_costs[option]

    def closed(self, option):
        """A branch whose twin was researched."""
        twin = BRANCHES.get(option, {}).get("excludes")
        return bool(twin and twin in self.unlocked_options)

    def open_options(self, done=()):
        """What can be researched now: the first six, then branches whose roots are researched,
        whose story has happened and whose twin has not been chosen."""
        options = [opt for opt in self.research_costs if opt not in self.unlocked_options]
        for opt, branch in BRANCHES.items():
            if opt in self.unlocked_options or self.closed(opt):
                continue
            if all(r in self.unlocked_options for r in branch["requires"]) and \
                    (not branch.get("story") or branch["story"] in done):
                options.append(opt)
        return options


class ResearchMixin:
    """The Game's research screens. Game inherits it (game/world.py)."""
    def display_research_status(self):
        """Display current research status and benefits"""
        status_content = [["Research Status", "Benefit"]]

        # Add unlocked research
        if self.research.unlocked_options:
            for research in self.research.unlocked_options:
                benefit = self.get_research_benefit_description(research)
                status_content.append([research, benefit])
        else:
            status_content.append(["No research completed", ""])

        print(self.create_box(status_content, 'double'))
        time.sleep(3)

    def get_research_benefit_description(self, research):
        """Get description of research benefit"""
        if research in BRANCHES:
            return BRANCHES[research]["about"]
        benefits = {
            'xenoeconomy': "Trading tax reduced by 2%",
            'telemetry': "Scout success +20%",
            'geophysics': "Mining efficiency +15%",
            'chronopolitics': "Revolution success +20%",
            'exogeology': "Mining output +25%",
            'psychodynamics': "Price control ±10%"
        }
        return benefits.get(research, "Unknown benefit")


    def handle_research_options(self):
        """Enhanced research options system"""
        if not isinstance(self.current_location, ResearchColony):
            self.display_simple_message("Research options only available at Research Colonies!")
            return

        # Show current research points and colony specialization
        specialization = getattr(self.current_location, 'research_specialization',
                            random.choice(['quantum', 'xenology', 'engineering', 'temporal']))
        self.current_location.research_specialization = specialization

        research_content = [
            ["Research Laboratory Options"],
            [f"Available Research Points: {self.ship.research_points}"],
            [f"Colony Specialization: {specialization.title()}"],
            [""],
            ["1. Analyze (20 RP) - Safe, steady progress"],
            ["2. Experiment (40 RP) - Risky, higher rewards"],
            ["3. Breakthrough (100 RP) - Major discovery attempt"],
            ["4. Collaborate (30 RP) - Work with colony scientists"]
        ]
        print(self.create_box(research_content, 'double'))

        choice = self.validate_input(
            "Choose research action (1-4, or 'back'): ",
            ['1', '2', '3', '4', 'back']
        )

        if choice == 'back':
            return

        if choice == '1':
            self.conduct_analysis(specialization)
        elif choice == '2':
            self.conduct_experiment(specialization)
        elif choice == '3':
            self.attempt_breakthrough(specialization)
        elif choice == '4':
            self.collaborate_research(specialization)

    def conduct_analysis(self, specialization):
        """Safe research analysis with guaranteed small rewards and chance for items"""
        cost = 20
        if self.ship.research_points < cost:
            self.display_simple_message(f"Not enough research points! Need: {cost}")
            return

        self.ship.research_points -= cost

        # Base rewards
        tech_bonus = random.randint(5, 15)
        money_bonus = random.randint(500, 1500)

        # Specialization bonuses
        if specialization == 'quantum':
            tech_bonus *= 1.5
        elif specialization == 'engineering':
            money_bonus *= 1.5

        # Chance for bonus item or ship stat
        if random.random() < 0.2:  # 20% chance for bonus
            bonus_type = random.choice(['item', 'stat'])
            if bonus_type == 'item':
                research_items = {
                    'quantum': ['quantum_analyzer', 'entanglement_core', 'quantum_shield'],
                    'xenology': ['xeno_scanner', 'translation_matrix', 'alien_artifact'],
                    'engineering': ['efficiency_module', 'repair_nanites', 'power_core'],
                    'temporal': ['time_dilator', 'causality_shield', 'temporal_lens']
                }
                item = random.choice(research_items[specialization])
                self.ship.acquire_item(item)
                self.display_simple_message(f"Bonus research item acquired: {item}!")
            else:
                stat = random.choice(['attack', 'defense', 'speed'])
                bonus = 1
                if stat == 'attack':
                    self.ship.attack += bonus
                elif stat == 'defense':
                    self.ship.defense += bonus
                else:
                    self.ship.speed += bonus
                self.display_simple_message(f"Ship {stat} improved by {bonus}!")

        # Generate research findings
        findings = {
            'quantum': [
                "Quantum field fluctuations mapped",
                "Superposition states stabilized",
                "Entanglement patterns documented",
                "Wave function variations recorded"
            ],
            'xenology': [
                "Alien artifact patterns analyzed",
                "Bio-signatures catalogued",
                "Cultural markers identified",
                "Xenotechnology principles documented"
            ],
            'engineering': [
                "Efficiency algorithms optimized",
                "Material stress patterns mapped",
                "Power distribution improved",
                "Systems integration enhanced"
            ],
            'temporal': [
                "Temporal anomalies measured",
                "Causality patterns documented",
                "Time dilation effects mapped",
                "Chronological variations recorded"
            ]
        }

        result = random.choice(findings[specialization])

        self.ship.money += money_bonus
        self.ship.research_points += tech_bonus

        self.display_simple_message([
            f"Analysis Complete: {result}",
            f"Gained {tech_bonus} research points",
            f"Earned {self.format_money(money_bonus)} credits"
        ])

    def conduct_experiment(self, specialization):
        """Risky research with variable outcomes and enhanced rewards"""
        cost = 40
        if self.ship.research_points < cost:
            self.display_simple_message(f"Not enough research points! Need: {cost}")
            return

        self.ship.research_points -= cost

        # Success chance based on specialization
        base_chance = 0.7
        if specialization == 'engineering':
            base_chance += 0.1

        if random.random() < base_chance:
            # Successful experiment
            reward_mult = random.uniform(1.5, 3.0)
            tech_bonus = int(cost * reward_mult)
            money_bonus = int(1000 * reward_mult)

            # Enhanced rewards
            if random.random() < 0.4:  # 40% chance for significant bonus
                advanced_items = {
                    'quantum': {
                        'items': ['quantum_core_v2', 'phase_shifter', 'quantum_capacitor'],
                        'stat_bonus': {'attack': 2, 'defense': 1, 'speed': 2}
                    },
                    'xenology': {
                        'items': ['alien_reactor', 'xeno_shield', 'biotech_enhancer'],
                        'stat_bonus': {'attack': 1, 'defense': 2, 'speed': 1}
                    },
                    'engineering': {
                        'items': ['fusion_drive', 'nanotech_armor', 'power_amplifier'],
                        'stat_bonus': {'attack': 2, 'defense': 2, 'speed': 1}
                    },
                    'temporal': {
                        'items': ['time_dilation_core', 'temporal_shield', 'causality_engine'],
                        'stat_bonus': {'attack': 1, 'defense': 1, 'speed': 3}
                    }
                }

                # Either get an advanced item or stat bonus
                if random.random() < 0.5:
                    item = random.choice(advanced_items[specialization]['items'])
                    self.ship.acquire_item(item)
                    self.display_simple_message(f"Advanced research item acquired: {item}!")
                else:
                    stat_bonuses = advanced_items[specialization]['stat_bonus']
                    for stat, bonus in stat_bonuses.items():
                        if random.random() < 0.5:  # 50% chance for each stat
                            if stat == 'attack':
                                self.ship.attack += bonus
                            elif stat == 'defense':
                                self.ship.defense += bonus
                            else:
                                self.ship.speed += bonus
                            self.display_simple_message(f"Ship {stat} improved by {bonus}!")

            # Special bonuses based on specialization
            special_outcomes = {
                'quantum': ["Quantum Computing Breakthrough",
                        lambda: setattr(self.ship, 'quantum_bonus', True)],
                'xenology': ["Alien Technology Integration",
                            lambda: setattr(self.ship, 'alien_tech', True)],
                'engineering': ["Advanced Engineering Insights",
                            lambda: setattr(self.ship, 'engineering_bonus', True)],
                'temporal': ["Temporal Mechanics Discovery",
                            lambda: setattr(self.ship, 'temporal_bonus', True)]
            }

            outcome, effect = special_outcomes[specialization]
            effect()  # Apply the special effect

            self.display_simple_message([
                f"Experiment Success: {outcome}!",
                f"Gained {tech_bonus} research points",
                f"Earned {self.format_money(money_bonus)} credits",
                "Special ability unlocked!"
            ])

            self.ship.money += money_bonus
            self.ship.research_points += tech_bonus

        else:
            # Failed experiment
            damage = random.randint(5, 15)
            self.ship.damage = min(99, self.ship.damage + damage)
            lost_points = random.randint(5, 15)
            self.ship.research_points = max(0, self.ship.research_points - lost_points)

            self.display_simple_message([
                "Experiment Failed!",
                f"Ship took {damage}% damage",
                f"Lost {lost_points} research points"
            ])

    def attempt_breakthrough(self, specialization):
        """Attempt a major research breakthrough"""
        cost = 100
        if self.ship.research_points < cost:
            self.display_simple_message(f"Not enough research points! Need: {cost}")
            return

        self.ship.research_points -= cost

        # Breakthrough chance increases with more research points spent
        breakthrough_chance = min(0.8, 0.3 + (self.ship.research_points / 1000))

        if random.random() < breakthrough_chance:
            # Major breakthrough
            breakthrough_rewards = {
                'quantum': {
                    'name': "Quantum Tunneling Drive",
                    'effect': lambda: setattr(self.ship, 'speed', self.ship.speed + 2),
                    'bonus_rp': 300,
                    'bonus_money': 50000
                },
                'xenology': {
                    'name': "Xenomorph Shield Matrix",
                    'effect': lambda: setattr(self.ship, 'defense', self.ship.defense + 2),
                    'bonus_rp': 250,
                    'bonus_money': 40000
                },
                'engineering': {
                    'name': "Nano-fabrication System",
                    'effect': lambda: setattr(self.ship, 'engineering_level',
                                            getattr(self.ship, 'engineering_level', 0) + 1),
                    'bonus_rp': 200,
                    'bonus_money': 60000
                },
                'temporal': {
                    'name': "Temporal Compression Field",
                    'effect': lambda: setattr(self.ship, 'temporal_compression', True),
                    'bonus_rp': 400,
                    'bonus_money': 45000
                }
            }

            reward = breakthrough_rewards[specialization]
            reward['effect']()  # Apply the special effect

            self.ship.research_points += reward['bonus_rp']
            self.ship.money += reward['bonus_money']

            self.display_simple_message([
                f"Major Breakthrough: {reward['name']}!",
                f"Gained {reward['bonus_rp']} research points",
                f"Earned {self.format_money(reward['bonus_money'])} credits",
                "Revolutionary technology acquired!"
            ])

        else:
            # Minor breakthrough
            bonus_rp = random.randint(50, 150)
            bonus_money = random.randint(5000, 15000)

            self.ship.research_points += bonus_rp
            self.ship.money += bonus_money

            self.display_simple_message([
                "Minor Breakthrough Achieved",
                f"Gained {bonus_rp} research points",
                f"Earned {self.format_money(bonus_money)} credits"
            ])

    def collaborate_research(self, specialization):
        """Collaborate with colony scientists"""
        cost = 30
        if self.ship.research_points < cost:
            self.display_simple_message(f"Not enough research points! Need: {cost}")
            return

        self.ship.research_points -= cost

        # Collaboration projects
        projects = {
            'quantum': [
                ("Quantum Encryption", 1.2),
                ("Entanglement Network", 1.3),
                ("Quantum Computing", 1.4)
            ],
            'xenology': [
                ("Alien Languages", 1.2),
                ("Xenobiology", 1.3),
                ("First Contact Protocols", 1.4)
            ],
            'engineering': [
                ("Power Systems", 1.2),
                ("Shield Technology", 1.3),
                ("Propulsion Theory", 1.4)
            ],
            'temporal': [
                ("Time Dilation", 1.2),
                ("Causality Mechanics", 1.3),
                ("Temporal Physics", 1.4)
            ]
        }

        project, multiplier = random.choice(projects[specialization])

        # Calculate rewards
        research_gain = int(cost * multiplier)
        money_gain = int(2000 * multiplier)

        # Colony gains permanent bonus to future research
        colony_bonus = random.uniform(0.05, 0.15)  # 5-15% bonus
        current_multiplier = getattr(self.current_location, 'research_multiplier', 1.0)
        self.current_location.research_multiplier = current_multiplier + colony_bonus

        self.ship.research_points += research_gain
        self.ship.money += money_gain

        self.display_simple_message([
            f"Collaboration Project: {project}",
            f"Gained {research_gain} research points",
            f"Earned {self.format_money(money_gain)} credits",
            f"Colony research efficiency increased by {int(colony_bonus * 100)}%"
        ])


# The game's other modules, imported last so that the modules can refer to each other.
from .places import ResearchColony  # noqa: E402
