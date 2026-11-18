"""The commands a captain can type, and the names of the goods."""

class LocationCommands:
    """Define available commands per location type"""
    COMMANDS = {
        "Planet": {
            "base_commands": [
                ('buy', 'b'), ('sell', 's'), ('upgrade', 'u'),
                ('travel', 't'), ('repair', 'r'), ('info', 'i'),
                ('build', 'bl'), ('cantina', 'c'), ('shop', 'sh'),
                ('action', 'a'), ('mine', 'm'), ('port', 'p'), ('hunt', 'hu'), ('end', 'e')
            ],
            "description": "Standard planetary commerce hub"
        },
        "AsteroidBase": {
            "base_commands": [
                ('buy', 'b'), ('sell', 's'), ('upgrade', 'u'),
                ('travel', 't'), ('repair', 'r'), ('info', 'i'),
                ('build', 'bl'), ('cantina', 'c'), ('shop', 'sh'),
                ('action', 'a'), ('mine', 'm'), ('port', 'p'), ('hunt', 'hu'), ('end', 'e')
            ],
            "description": "Mining and resource extraction facility"
        },
        "DeepSpaceOutpost": {
            "base_commands": [
                ('buy', 'b'), ('sell', 's'), ('upgrade', 'u'),
                ('travel', 't'), ('repair', 'r'), ('info', 'i'),
                ('build', 'bl'), ('cantina', 'c'), ('shop', 'sh'),
                ('action', 'a'), ('port', 'p'), ('hunt', 'hu'), ('end', 'e')
            ],
            "description": "Strategic trading outpost"
        },
        "ResearchColony": {
            "base_commands": [
                ('buy', 'b'), ('sell', 's'), ('upgrade', 'u'),
                ('travel', 't'), ('research', 'r'), ('info', 'i'),
                ('build', 'bl'), ('cantina', 'c'), ('shop', 'sh'), ('action', 'a'),
                ('port', 'p'), ('end', 'e')
            ],
            "special_commands": {
                "research": {
                    "options": ["analyze", "experiment", "fundamental"],
                    "description": "Conduct research activities"
                }
            },
            "description": "Advanced scientific research facility. No repair facilities available."
        }
    }

    @staticmethod
    def get_available_commands(location_type):
        """Get available commands for location type"""
        commands = LocationCommands.COMMANDS.get(location_type,
                                               LocationCommands.COMMANDS["Planet"])
        return commands["base_commands"]

    @staticmethod
    def get_special_commands(location_type):
        """Get special commands if any"""
        location_data = LocationCommands.COMMANDS.get(location_type, {})
        return location_data.get("special_commands", {})

    @staticmethod
    def get_commands_for_location(location):
        """Helper method to get all commands for a location instance"""
        return {
            "available": LocationCommands.get_available_commands(location.location_type),
            "special": LocationCommands.get_special_commands(location.location_type)
        }

# The goods in a hold, with the shortcut each answers to in buy and sell
COMMODITIES = {"tech": ("t",), "agri": ("a", "agro"), "salt": ("s",), "fuel": ("f",)}

# Commands every location accepts besides its own (long form, shortcut)
GLOBAL_COMMANDS = [('hansa', 'ha'), ('log', 'l'), ('journal', 'j'), ('save', 'sv'), ('load', 'ld'),
                   ('look', 'lk'), ('think', 'th'), ('captain', 'cap'), ('style', 'st'), ('sound', 'so'), ('help', 'h'), ('version', 'v'), ('resign', 'rs'), ('quit', 'q')]


def commodity_from(answer):
    """'t', 'tech', 'agro', 'a' ... -> the commodity's name, or None."""
    answer = (answer or "").strip().lower()
    for name, shortcuts in COMMODITIES.items():
        if answer == name or answer in shortcuts:
            return name
    return None
