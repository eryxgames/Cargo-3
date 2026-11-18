"""The market: prices, forecasts, trade and trade events."""
import random
import zlib

class MarketMixin:
    """The Game's market: forecasts and trade. Game inherits it (game/world.py)."""
    # --- markets that remember, and the Hansa ---------------------------------------
    def affordable(self, item, tax_rate, room):
        """The largest load of `item` the money covers here, price movement and tax included."""
        loc = self.current_location
        low, high = 0, room
        while low < high:
            mid = (low + high + 1) // 2
            if mid * loc.trade_price(item, mid, selling=False) * (1 + tax_rate) <= self.ship.money:
                low = mid
            else:
                high = mid - 1
        return low

    def note_prices(self, loc=None):
        loc = loc or self.current_location
        self.__dict__.setdefault("prices_seen", {})[loc.name] = (self.turn, dict(loc.market))

    def forecast(self, loc):
        """What a broker would guess {good: (price, spread)} for a place: close for a dock
        seen this turn, looser the older the news, a rough guess for a dock never seen."""
        seen = getattr(self, "prices_seen", {}).get(loc.name)
        if seen and seen[0] == self.turn:
            return {good: (price, 0.0) for good, price in loc.market.items()}, 0
        age = self.turn - seen[0] if seen else None
        spread = 0.45 if age is None else min(0.35, 0.04 + 0.03 * age)
        if "broker" in self.ship.crew:
            spread /= 2
        if self.story_flag("harp_relay"):        # the quantum harp carries prices between the stars
            spread /= 2
        rng = random.Random(zlib.crc32(("%s/%d/%s" % (loc.name, self.turn, self.player_name)).encode()))
        guess = {}
        for good, price in loc.market.items():
            if price <= 0:
                guess[good] = (0, 0.0)
                continue
            truth = price if seen else loc.equilibrium().get(good, price)
            error = max(-spread, min(spread, rng.gauss(0, spread / 2)))
            guess[good] = (max(1, truth * (1 + error)), spread)
        return guess, age

    def show_forecast(self, who):
        """Price guesses for the other docks the captain knows of."""
        rows = [[who], [""]]
        for loc in self.locations:
            if loc.name not in self.known_locations or loc is self.current_location:
                continue
            guess, age = self.forecast(loc)
            note = "never visited: a guess" if age is None else "seen %d turn%s ago" % (age, "" if age == 1 else "s")
            rows.append(["%s (%s)" % (loc.name, note)])
            parts = []
            for good in ('tech', 'agri', 'salt', 'fuel'):
                price, spread = guess.get(good, (0, 0))
                if price > 0:
                    word = "~" if spread < 0.15 else "about " if spread < 0.3 else "maybe "
                    parts.append("%s %s%s" % (good, word, self.format_money(price)))
            rows.append(["  " + (", ".join(parts) or "no market")])
        rows.append([""])
        rows.extend([line] for line in self.word_wrap(
            "Fresh news is close; old news drifts; places you never saw are guesses. Big loads move prices, "
            "and prices take a few weeks to recover."))
        print(self.create_box(rows, 'double'))
        input("Press Enter to continue...")

    # Add trade tracking to buy/sell methods
    def handle_trade(self, action_type, commodity=None, quantity=None, price=None):
        """Handle trade completion and contract/quest updates"""
        self.trades_completed += 1

        # Build complete trade event data
        trade_data = {
            "action": action_type,
            "location": self.current_location.name,
            "turn": self.turn,
            "trade_completed": True,
        }

        # Add commodity-specific data for sell actions
        if action_type == 'sell' and commodity and quantity:
            trade_data.update({
                "commodity": commodity,
                "amount": quantity,
                "price": price
            })

            # Update contracts with complete trade data
            if hasattr(self, 'contract_manager'):
                self.contract_manager.update_contract_progress(trade_data)

        # Update quests
        if hasattr(self, 'quest_system'):
            self.quest_system.update_from_trade(trade_data)


    def handle_trade_event(self, event):
        """Handle trade disruption events with full market impact"""
        event_types = {
            "Market crash!": {
                "price_impact": (-0.5, -0.3),  # 30-50% price reduction
                "duration": (2, 4),  # 2-4 turns
                "severity": "major"
            },
            "Trade embargo!": {
                "price_impact": (0.3, 0.5),  # 30-50% price increase
                "duration": (3, 5),
                "severity": "major"
            },
            "Resource shortage!": {
                "price_impact": (0.2, 0.4),
                "duration": (2, 3),
                "severity": "minor"
            },
            "Price manipulation!": {
                "price_impact": (-0.3, 0.3),  # Can go either way
                "duration": (1, 3),
                "severity": "minor"
            },
            "Trade route disruption!": {
                "price_impact": (0.1, 0.3),
                "duration": (2, 4),
                "severity": "moderate"
            },
            "Black market emergence!": {
                "price_impact": (-0.4, -0.2),
                "duration": (3, 5),
                "severity": "moderate"
            }
        }

        event_data = event_types.get(event, event_types["Market crash!"])

        # Select affected commodities
        commodities = ["tech", "agri", "salt", "fuel"]
        num_affected = random.randint(1, len(commodities))
        affected_commodities = random.sample(commodities, num_affected)

        # Apply market effects
        for commodity in affected_commodities:
            impact = random.uniform(*event_data["price_impact"])
            current_price = self.current_location.market[commodity]

            # Calculate new price
            new_price = current_price * (1 + impact)

            # Apply commodity-specific limits
            if commodity == "salt":
                new_price = max(60, min(150, new_price))
            elif commodity == "fuel":
                new_price = max(120, min(250, new_price))
            else:
                new_price = max(1, min(200, new_price))

            self.current_location.market[commodity] = new_price

            # Add temporary trade ban if price would be too low
            if new_price < 10:
                duration = random.randint(*event_data["duration"])
                self.current_location.add_temporary_ban(commodity, duration)

        # Generate message based on severity
        messages = {
            "major": f"Major market disruption! {event}",
            "moderate": f"Market instability detected. {event}",
            "minor": f"Minor market fluctuation. {event}"
        }

        self.display_simple_message([
            messages[event_data["severity"]],
            f"Affected commodities: {', '.join(affected_commodities)}",
            "Check market prices for details."
        ])

        # Possible quest generation
        if event_data["severity"] == "major" and random.random() < 0.3:
            self.quest_system.generate_quest("trade", 1.5)
