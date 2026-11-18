"""The Hauler Hansa in 2460: the needle office's fares, the bonds that lower them, the terminal."""


class HansaMixin:
    """The Game's dealings with the Hansa. Game inherits it (game/world.py)."""
    # The Hansa runs the needles between the stars (game/needles.py) and sells a place in them
    # per jump; the fares grow as the routes get busier. Hansa bonds lower them, 12% each.

    def dues(self):
        """What a middle place in the next needle costs now (Cargo 1's dues, by another name)."""
        return self.needle_fare("middle")

    def bond_price(self):
        return int(4000 * 1.15 ** getattr(self, "hansa_bonds", 0))

    def buy_bonds(self, count=1, announce=True):
        bought = 0
        for _ in range(count):
            price = self.bond_price()
            if self.ship.money < price:
                break
            self.ship.money -= price
            self.hansa_bonds = getattr(self, "hansa_bonds", 0) + 1
            self.bonds_paid = getattr(self, "bonds_paid", 0) + price
            bought += 1
        if announce and bought:
            self.display_simple_message("Bought %d Hansa bond%s. You hold %d; fares are %d%% lower." % (
                bought, "" if bought == 1 else "s", self.hansa_bonds, round(100 * (1 - 0.88 ** self.hansa_bonds))))
        return bought

    def sell_bonds(self):
        """Cash the bonds in at what they cost (the Hansa buys back at face value)."""
        held = getattr(self, "hansa_bonds", 0)
        value = getattr(self, "bonds_paid", 0)
        self.hansa_bonds, self.bonds_paid = 0, 0
        self.ship.money += value
        return held, value

    def handle_hansa(self):
        """The Hansa terminal: fares, bonds, standing, the price board, what is owed."""
        while True:
            bonds = getattr(self, "hansa_bonds", 0)
            rows = [["Hansa terminal - " + self.current_location.name], [""]]
            for text in (
                    "The Hansa runs the needles between the stars. A place in the next one costs %s at the front, "
                    "%s in the middle, %s in the tail; fares go up as the routes get busier." % (
                        self.format_money(self.needle_fare("front")), self.format_money(self.needle_fare("middle")),
                        self.format_money(self.needle_fare("tail"))),
                    "Your standing with the Hansa: %+d. Bonds held: %d (fares %d%% lower). The next bond costs %s "
                    "and takes another 12%% off." % (self.standing_of("hansa"), bonds, round(100 * (1 - 0.88 ** bonds)),
                                                     self.format_money(self.bond_price())),
                    ("On account with the needle office: %s." % self.format_money(self.dues_arrears))
                    if getattr(self, "dues_arrears", 0) else "You owe the needle office nothing."):
                rows.extend([line] for line in self.word_wrap(text))
                rows.append([""])
            rows.extend([["bond/b: buy a bond"], ["prices/p: the needle office's price board"],
                         ["pay/pd: pay what you owe now"]])
            print(self.create_box(rows, 'double'))
            action = self.validate_input("Hansa - choose (Enter to leave): ", ['bond', 'b', 'prices', 'p', 'pay', 'pd'])
            if action is None:
                return
            if action in ('bond', 'b'):
                if not self.buy_bonds(1):
                    self.display_simple_message("Not enough money for a bond (%s)." % self.format_money(self.bond_price()))
            elif action in ('prices', 'p'):
                self.show_forecast("The needle office's price board")
            elif action in ('pay', 'pd'):
                owed = getattr(self, "dues_arrears", 0)
                paid = min(owed, int(self.ship.money))
                self.ship.money -= paid
                self.dues_arrears = owed - paid
                self.display_simple_message("Paid %s. Still owed: %s." % (
                    self.format_money(paid), self.format_money(self.dues_arrears)))
