"""Contracts offered at ports, and the manager that keeps them."""
import random

class ContractManager:
    def __init__(self, game):
        self.game = game
        self.available_contracts = []
        self.active_contracts = []
        self.completed_contracts = []
        self.max_active_contracts = 3
        self.contract_refresh_turns = 0
        self.special_contracts_unlocked = False


    def handle_contract_menu(self):
        """Handle port menu options"""
        self.game.clear_screen()
        self.game.display_simple_message("Contract Management Terminal", 0)

        while True:
            # Refresh contracts if needed
            self.refresh_available_contracts()

            options = {
                'view': ('v', "View new contracts"),
                'claim': ('c', "Claim completed contract rewards"),
                'status': ('s', "Check detailed contract status"),
                'back': ('', "Return to previous menu")
            }

            # Show menu
            menu_content = [["Contract Dashboard:"]]
            menu_content.append([f""])
            for cmd, (shortcut, desc) in options.items():
                menu_content.append([f"{cmd}/{shortcut if shortcut else ''}: {desc}"])
            print(self.game.create_box(menu_content, 'single'))

            valid_inputs = [cmd for cmd in options.keys()] + [s[0] for s in options.values() if s[0]]
            action = self.game.validate_input("Contracts - choose (Enter to leave): ", valid_inputs)

            if action in ['back', None]:
                break

            elif action in ['view', 'v']:
                self.show_available_contracts()

            elif action in ['claim', 'c']:
                self.claim_completed_contracts()

            elif action in ['status', 's']:
                self.show_detailed_status()

            self.game.clear_screen()

    def show_available_contracts(self):
        """Show available contracts for acceptance"""
        if not self.available_contracts:
            self.game.display_simple_message("No contracts available currently.")
            return

        contract_content = [["Available Contracts"]]
        for i, contract in enumerate(self.available_contracts, 1):
            contract_content.append([""])
            contract_content.append([f"Contract #{i}"])
            for info_line in self.get_contract_display_info(contract):
                contract_content.append([info_line])

        print(self.game.create_box(contract_content, 'double'))

        choice = self.game.validate_input(
            f"Accept contract (1-{len(self.available_contracts)}) or Enter to cancel: ",
            [str(i) for i in range(1, len(self.available_contracts) + 1)] + ['']
        )

        if not choice:  # Empty Enter cancels
            return

        success, message = self.accept_contract(int(choice) - 1)
        self.game.display_simple_message(message)

    def claim_completed_contracts(self):
        """Handle claiming rewards for completed contracts"""
        completed = [c for c in self.active_contracts if c.completed and not c.rewards_claimed]

        if not completed:
            self.game.display_simple_message("No completed contracts to claim!")
            return

        # Show completed contracts
        content = [["Completed Contracts Ready to Claim"]]
        for i, contract in enumerate(completed, 1):
            content.append([
                f"{i}. {contract.description}",
                f"Reward: {self.game.format_money(contract.rewards['money'])}",
                f"Rep: +{contract.rewards['reputation']}"
            ])
        print(self.game.create_box(content, 'double'))

        # Get contract choice
        choice = self.game.validate_input(
            "Enter contract number to claim (or Enter to cancel): ",
            [str(i) for i in range(1, len(completed) + 1)] + ['']
        )

        if not choice:  # Empty Enter cancels
            return

        # Claim rewards
        contract = completed[int(choice) - 1]
        self.handle_contract_completion(contract)


    def show_detailed_status(self):
        """Show detailed status of all active contracts with trade history"""
        if not self.active_contracts:
            self.game.display_simple_message("No active contracts!")
            return

        for contract in self.active_contracts:
            content = [
                [f"Contract: {contract.description}"],
                [""],
                ["Requirements:"]
            ]

            # Add type-specific requirements
            if contract.contract_type == "cargo":
                content.extend([
                    [f"• Cargo: {contract.requirements['cargo_type']}"],
                    [f"• Amount: {contract.requirements['min_amount']} units"],
                    [f"• Source: {contract.requirements['source']}"],
                    [f"• Destination: {contract.requirements['destination']}"],
                    [f"• Time Limit: {contract.duration} turns"]
                ])
            elif contract.contract_type == "passenger":
                content.extend([
                    [f"• Passengers: {contract.requirements.get('count', contract.requirements.get('passenger_count', 0))}"],
                    [f"• Class: {contract.requirements.get('passenger_class', 'Any')}"],
                    [f"• Source: {contract.requirements['source']}"],
                    [f"• Destination: {contract.requirements['destination']}"],
                    [f"• Time Limit: {contract.duration} turns"]
                ])

            content.extend([
                [""],
                ["Current Status:"]
            ])

            # Add status lines
            status = contract.get_status_display()
            for line in status.split('\n'):
                content.append([f"• {line}"])

            # Add trade history
            content.extend([
                [""],
                ["Delivery History:"]
            ])

            history = contract.get_trade_history_display()
            for line in history.split('\n'):
                content.append([f"• {line}"])

            # Add reward info if completed
            if contract.completed and not contract.rewards_claimed:
                content.extend([
                    [""],
                    ["Rewards Available:"],
                    [f"• {self.game.format_money(contract.rewards['money'])} credits"],
                    [f"• {contract.rewards['reputation']} reputation"],
                    [f"• {contract.rewards.get('plot_points', 0)} plot points"]
                ])

            print(self.game.create_box(content, 'double'))
            print()  # Add space between contracts

        input("Press Enter to continue...")

    def refresh_available_contracts(self):
        """Refresh available contracts every 5 turns"""
        if self.game.turn - self.contract_refresh_turns >= 5:
            self.contract_refresh_turns = self.game.turn
            self.available_contracts = []
            # Generate 2-4 new contracts using known locations
            num_contracts = random.randint(2, 4)
            for _ in range(num_contracts):
                # If special contracts are unlocked, 30% chance for special contract
                if self.special_contracts_unlocked and random.random() < 0.3:
                    contract = self.generate_special_contract()
                    if contract:
                        self.available_contracts.append(contract)
                        continue

                # Regular contract generation
                if random.random() < 0.6:  # 60% chance for cargo contract
                    contract = self.generate_cargo_contract()
                else:
                    contract = self.generate_passenger_contract()
                if contract:
                    self.available_contracts.append(contract)

    def generate_cargo_contract(self):
        """Generate a cargo transport contract"""
        if len(self.game.known_locations) < 2:
            return None

        # Get actual Location objects from known locations
        known_locations = [loc for loc in self.game.locations
                        if loc.name in self.game.known_locations]

        if len(known_locations) < 2:
            return None

        source = random.choice(known_locations)
        destinations = [loc for loc in known_locations if loc != source]
        destination = random.choice(destinations)

        contract_types = [
            {
                "desc_template": "Exclusive Trading",
                "requirements": {
                    "cargo_type": (cargo_type := random.choice(["tech", "agri"])),
                    "min_amount": (amount := random.randint(100, 300)),
                    "source": source.name,
                    "destination": destination.name
                },
                "duration": 8,
                "base_reward": 20000,
                "description": f"Transport {amount} units of {cargo_type} from {source.name} to {destination.name}"
            },
            {
                "desc_template": "Resource Distribution",
                "requirements": {
                    "cargo_type": (cargo_type := random.choice(["salt", "fuel"])),
                    "min_amount": (amount := random.randint(50, 150)),
                    "source": source.name,
                    "destination": destination.name
                },
                "duration": 12,
                "base_reward": 30000,
                "description": f"Transport {amount} units of {cargo_type} from {source.name} to {destination.name}"
            }
        ]

        contract_type = random.choice(contract_types)
        return Contract(
            contract_type="cargo",
            duration=contract_type["duration"],
            requirements=contract_type["requirements"],
            rewards={
                "money": contract_type["base_reward"],
                "reputation": 20,
                "plot_points": 3
            },
            description=contract_type["description"]
        )

    def generate_passenger_contract(self):
        """Generate a passenger transport contract"""
        if len(self.game.known_locations) < 2:
            return None

        # Get actual Location objects from known locations
        known_locations = [loc for loc in self.game.locations
                        if loc.name in self.game.known_locations]

        if len(known_locations) < 2:
            return None

        source = random.choice(known_locations)
        destinations = [loc for loc in known_locations if loc != source]
        destination = random.choice(destinations)

        contract_types = [
            {
                "desc_template": "VIP Transport",
                "requirements": {
                    "passenger_class": (passenger_class := random.choice(["S", "M", "E"])),
                    "count": (count := random.randint(3, 8)),
                    "source": source.name,
                    "destination": destination.name,
                    "min_satisfaction": 80
                },
                "duration": 10,
                "base_reward": 25000,
                "description": f"Transport {count} {passenger_class}-class passengers from {source.name} to {destination.name}"
            },
            {
                "desc_template": "Group Transport",
                "requirements": {
                    "passenger_count": (count := random.randint(10, 20)),
                    "source": source.name,
                    "destination": destination.name,
                    "min_satisfaction": 70
                },
                "duration": 15,
                "base_reward": 35000,
                "description": f"Transport {count} passengers from {source.name} to {destination.name}"
            }
        ]

        contract_type = random.choice(contract_types)
        return Contract(
            contract_type="passenger",
            duration=contract_type["duration"],
            requirements=contract_type["requirements"],
            rewards={
                "money": contract_type["base_reward"],
                "reputation": 25,
                "plot_points": 5
            },
            description=contract_type["description"]
        )

    def generate_special_contract(self):
        """Generate a special contract with higher rewards and requirements"""
        if len(self.game.known_locations) < 2:
            return None

        # Get actual Location objects from known locations
        known_locations = [loc for loc in self.game.locations
                        if loc.name in self.game.known_locations]

        if len(known_locations) < 2:
            return None

        source = random.choice(known_locations)
        destinations = [loc for loc in known_locations if loc != source]
        destination = random.choice(destinations)

        contract_types = [
            {
                "desc_template": "High-Value Transport",
                "requirements": {
                    "cargo_type": (cargo_type := random.choice(["tech", "agri"])),
                    "min_amount": (amount := random.randint(400, 600)),
                    "source": source.name,
                    "destination": destination.name,
                    "reputation_required": 40
                },
                "duration": 10,
                "base_reward": 50000,
                "description": f"Transport {amount} units of {cargo_type} from {source.name} to {destination.name}"
            },
            {
                "desc_template": "Diplomatic Mission",
                "requirements": {
                    "passenger_class": "D",
                    "count": (count := random.randint(2, 4)),
                    "source": source.name,
                    "destination": destination.name,
                    "min_satisfaction": 90,
                    "reputation_required": 60
                },
                "duration": 8,
                "base_reward": 60000,
                "description": f"Transport {count} diplomatic passengers from {source.name} to {destination.name}"
            }
        ]

        contract_type = random.choice(contract_types)
        return Contract(
            contract_type=contract_type["desc_template"].lower().replace(" ", "_"),
            duration=contract_type["duration"],
            requirements=contract_type["requirements"],
            rewards={
                "money": contract_type["base_reward"],
                "reputation": 30,
                "plot_points": 8
            },
            description=contract_type["description"]
        )

    def accept_contract(self, contract_index):
        """Accept a contract from available contracts"""
        if contract_index >= len(self.available_contracts):
            return False, "Invalid contract selection."

        if len(self.active_contracts) >= self.max_active_contracts:
            return False, "Maximum number of active contracts reached."

        contract = self.available_contracts.pop(contract_index)
        self.active_contracts.append(contract)
        return True, f"Contract accepted: {contract.description}"

    def handle_contract_completion(self, contract):
        """Handle completed contract and reward claiming"""
        if contract not in self.active_contracts:
            return

        if contract.rewards_claimed:
            return

        # Calculate and award final rewards
        rewards = contract.calculate_final_reward()
        self.game.ship.money += rewards["money"]
        self.game.reputation += rewards["reputation"]
        self.game.story_manager.plot_points += rewards["plot_points"]

        # Mark contract as claimed
        contract.rewards_claimed = True
        self.active_contracts.remove(contract)
        self.completed_contracts.append(contract)

        # Display completion message
        self.game.display_simple_message([
            "Contract Rewards Claimed!",
            f"Earned {self.game.format_money(rewards['money'])} credits",
            f"Reputation +{rewards['reputation']}",
            f"Plot Points +{rewards['plot_points']}"
        ])

    def get_contract_display_info(self, contract):
        """Get formatted display info for a contract"""
        info = []
        info.append(f"Type: {contract.contract_type.title()}")
        info.append(f"Duration: {contract.duration} turns")

        # Requirements
        if contract.contract_type == "passenger":
            if "passenger_class" in contract.requirements:
                class_code = contract.requirements["passenger_class"]
                count = contract.requirements["count"]
                info.append(f"Transport: {count} {class_code}-class passengers")
            if "passenger_count" in contract.requirements:
                info.append(f"Transport: {contract.requirements['passenger_count']} passengers")
            if "min_satisfaction" in contract.requirements:
                info.append(f"Min. Satisfaction: {contract.requirements['min_satisfaction']}%")
        else:  # cargo contract
            if "cargo_type" in contract.requirements:
                info.append(f"Cargo: {contract.requirements['cargo_type']}")
                if "min_amount" in contract.requirements:
                    info.append(f"Amount: {contract.requirements['min_amount']} units")

        # Route information
        source = contract.requirements.get('source', 'Any')
        dest = contract.requirements.get('destination', 'Any')
        info.append(f"Route: {source} → {dest}")

        # Rewards
        info.append(f"Reward: {self.game.format_money(contract.rewards['money'])} credits")
        info.append(f"Reputation: +{contract.rewards['reputation']}")
        if contract.rewards['plot_points'] > 0:
            info.append(f"Plot Points: +{contract.rewards['plot_points']}")

        return info

    def update_contract_progress(self, event_data):
        """Update progress for all active contracts"""
        messages = []
        for contract in self.active_contracts[:]:  # Create copy to allow safe removal
            if contract.completed or contract.failed:
                continue

            result = contract.update_progress(event_data)

            if result["status"] == "completed":
                messages.append(result["message"])
                if contract.contract_type == "cargo":
                    self.game.display_simple_message(
                        f"Contract completed: Delivered {contract.progress['amount']} {contract.requirements['cargo_type']} " +
                        f"from {contract.requirements['source']} to {contract.requirements['destination']}"
                    )
                elif contract.contract_type == "passenger":
                    self.game.display_simple_message(
                        f"Contract completed: Transported {contract.progress['passengers_delivered']} passengers " +
                        f"from {contract.requirements['source']} to {contract.requirements['destination']}"
                    )
            elif result["status"] == "updated" and "message" in result:
                messages.append(result["message"])

        if messages:
            for msg in messages:
                self.game.display_simple_message(msg)


class Contract:
    def __init__(self, contract_type, duration, requirements, rewards, description):
        self.contract_type = contract_type
        self.duration = duration
        self.requirements = requirements
        self.rewards = rewards
        self.description = description
        self.progress = {
            'amount': 0,
            'destinations_visited': set(),
            'passengers_delivered': 0,
            'source_visited': False,
            'turns_remaining': duration
        }
        self.completed = False
        self.rewards_claimed = False
        self.failed = False
        self.last_update_turn = None
        self.trade_history = []

    def update_progress(self, event_data):
        """Enhanced progress update with trade history tracking"""
        current_location = event_data.get("location")
        action = event_data.get("action", "")
        commodity = event_data.get("commodity")
        current_turn = event_data.get("turn", 0)

        # Update turns only when it's a new turn
        if self.last_update_turn != current_turn:
            self.progress['turns_remaining'] -= 1
            self.last_update_turn = current_turn

        if self.progress['turns_remaining'] <= 0:
            self.failed = True
            return {"status": "failed", "reason": "time_expired"}

        # Record location visit
        if current_location:
            self.progress['destinations_visited'].add(current_location)

        if self.contract_type == "cargo":
            # Track source visit through buy action
            if action == "buy" and current_location == self.requirements.get("source"):
                self.progress["source_visited"] = True

            elif action == "sell" and commodity == self.requirements.get("cargo_type"):
                amount = event_data.get("amount", 0)

                if (current_location == self.requirements.get("destination") and
                    self.progress["source_visited"]):

                    # Record trade in history
                    self.trade_history.append({
                        'turn': current_turn,
                        'amount': amount,
                        'location': current_location
                    })

                    self.progress['amount'] += amount

                    if self.progress['amount'] >= self.requirements.get('min_amount', 0):
                        self.completed = True
                        return {
                            "status": "completed",
                            "message": f"Contract completed! Visit Contract Management to claim rewards."
                        }

                    return {
                        "status": "updated",
                        "trade_recorded": True,
                        "new_amount": self.progress['amount'],
                        "message": f"Delivered: {self.progress['amount']}/{self.requirements.get('min_amount')} {commodity}"
                    }

        elif self.contract_type == "passenger":
            # Handle passenger delivery
            if current_location == self.requirements.get("destination"):
                passenger_data = event_data.get("passenger_data")
                if passenger_data:
                    count = 1
                    if "passenger_class" in self.requirements:
                        if passenger_data["class"] == self.requirements["passenger_class"]:
                            self.progress['passengers_delivered'] += count
                            # Record delivery in history
                            self.trade_history.append({
                                'turn': current_turn,
                                'count': count,
                                'location': current_location
                            })
                    else:
                        self.progress['passengers_delivered'] += count
                        # Record delivery in history
                        self.trade_history.append({
                            'turn': current_turn,
                            'count': count,
                            'location': current_location
                        })

                    # Check completion
                    if (self.progress['passengers_delivered'] >= self.requirements.get('count',
                        self.requirements.get('passenger_count', 0))):
                        self.completed = True
                        return {
                            "status": "completed",
                            "message": f"Contract completed! Visit Contract Management to claim rewards."
                        }

        return {"status": "in_progress"}

    def get_status_display(self):
        """Get formatted status display"""
        if self.completed:
            return "✓ COMPLETED - Ready to claim"
        elif self.failed:
            return "✗ FAILED - Time expired"

        status_lines = [
            f"Time remaining: {self.progress['turns_remaining']} turns"
        ]

        if self.contract_type == "cargo":
            cargo_type = self.requirements.get('cargo_type')
            status_lines.extend([
                f"Source ({self.requirements['source']}): {'✓ Visited' if self.progress['source_visited'] else '□ Not visited'}",
                f"Destination ({self.requirements['destination']}): {'✓ Visited' if self.requirements['destination'] in self.progress['destinations_visited'] else '□ Not visited'}",
                f"Delivered: {self.progress['amount']}/{self.requirements.get('min_amount')} {cargo_type}"
            ])
        elif self.contract_type == "passenger":
            status_lines.extend([
                f"Passengers: {self.progress['passengers_delivered']}/{self.requirements.get('count', self.requirements.get('passenger_count', 0))}",
                f"Class: {self.requirements.get('passenger_class', 'Any')}"
            ])

        return "\n".join(status_lines)

    def get_trade_history_display(self):
        """Get formatted trade history"""
        if not hasattr(self, 'trade_history') or not self.trade_history:
            return "No trade history recorded"

        history_lines = []
        if self.contract_type == "cargo":
            for trade in self.trade_history:
                history_lines.append(
                    f"Turn {trade.get('turn', '?')}: Delivered {trade.get('amount', 0)} units of {self.requirements.get('cargo_type', 'cargo')} at {trade.get('location', 'Unknown')}"
                )
        elif self.contract_type == "passenger":
            for trade in self.trade_history:
                history_lines.append(
                    f"Turn {trade.get('turn', '?')}: Delivered {trade.get('count', 1)} passengers at {trade.get('location', 'Unknown')}"
                )

        return "\n".join(history_lines) if history_lines else "No trade history recorded"

    def calculate_final_reward(self):
        """Calculate final reward with bonuses"""
        if not self.completed:
            return None

        total_reward = dict(self.rewards)

        # Early completion bonus
        if self.progress['turns_remaining'] > self.duration / 2:
            total_reward["money"] = int(total_reward["money"] * 1.5)
            total_reward["reputation"] = int(total_reward["reputation"] * 1.2)

        # Overdelivery bonus for cargo contracts
        if self.contract_type == "cargo":
            required_amount = self.requirements.get('min_amount', 0)
            if self.progress['amount'] > required_amount * 1.5:  # 50% more than required
                total_reward["money"] = int(total_reward["money"] * 1.2)

        # High satisfaction bonus for passenger contracts
        if self.contract_type == "passenger":
            if "min_satisfaction" in self.requirements:
                avg_satisfaction = sum(p.get("satisfaction", 0) for p in self.trade_history) / len(self.trade_history) if self.trade_history else 0
                if avg_satisfaction > self.requirements["min_satisfaction"] * 1.2:  # 20% above minimum
                    total_reward["reputation"] = int(total_reward["reputation"] * 1.3)

        return total_reward

    def check_requirements(self):
        """Check if all requirements are met"""
        if self.contract_type == "cargo":
            return (
                self.progress["source_visited"] and
                self.requirements["destination"] in self.progress["destinations_visited"] and
                self.progress["amount"] >= self.requirements.get("min_amount", 0)
            )
        elif self.contract_type == "passenger":
            return (
                self.progress["passengers_delivered"] >= self.requirements.get("count",
                    self.requirements.get("passenger_count", 0))
            )
        return False
