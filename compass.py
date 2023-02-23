# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
class Compass:
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    """
    Modification of portolan
    https://pypi.python.org/pypi/portolan
    """

    def __init__(self):
        # self.setup()
        self.ABBRS = {
            "nne": {
                "trad": "Greco-Tramontana",
                "point": "north-northeast",
                "mid": 22.5,
                "abbr": "NNE",
            },
            "swbw": {
                "trad": "Quarto di Libeccio verso Ponente",
                "point": "southwest by west",
                "mid": 236.25,
                "abbr": "SWbW",
            },
            "nwbw": {
                "trad": "Quarto di Maestro verso Ponente",
                "point": "northwest by west",
                "mid": 303.75,
                "abbr": "NWbW",
            },
            "swbs": {
                "trad": "Quarto di Libeccio verso Ostro",
                "point": "southwest by south",
                "mid": 213.75,
                "abbr": "SWbS",
            },
            "nwbn": {
                "trad": "Quarto di Maestro verso Tramontana",
                "point": "northwest by north",
                "mid": 326.25,
                "abbr": "NWbN",
            },
            "ebs": {
                "trad": "Quarto di Levante verso Scirocco",
                "point": "east by south",
                "mid": 101.25,
                "abbr": "EbS",
            },
            "nnw": {
                "trad": "Maestro-Tramontana",
                "point": "north-northwest",
                "mid": 337.5,
                "abbr": "NNW",
            },
            "nbe": {
                "trad": "Quarto di Tramontana verso Greco",
                "point": "north by east",
                "mid": 11.25,
                "abbr": "NbE",
            },
            "sebe": {
                "trad": "Quarto di Scirocco verso Levante",
                "point": "southeast by east",
                "mid": 123.75,
                "abbr": "SEbE",
            },
            "ene": {
                "trad": "Greco-Levante",
                "point": "east-northeast",
                "mid": 67.5,
                "abbr": "ENE",
            },
            "nebn": {
                "trad": "Quarto di Greco verso Tramontana",
                "point": "northeast by north",
                "mid": 33.75,
                "abbr": "NEbN",
            },
            "nebe": {
                "trad": "Quarto di Greco verso Levante",
                "point": "northeast by east",
                "mid": 56.25,
                "abbr": "NEbE",
            },
            "ne": {"trad": "Greco", "point": "northeast", "mid": 45.0, "abbr": "NE"},
            "ese": {
                "trad": "Levante-Scirocco",
                "point": "east-southeast",
                "mid": 112.5,
                "abbr": "ESE",
            },
            "sebs": {
                "trad": "Quarto di Scirocco verso Ostro",
                "point": "southeast by south",
                "mid": 146.25,
                "abbr": "SEbS",
            },
            "ebn": {
                "trad": "Quarto di Levante verso Greco",
                "point": "east by north",
                "mid": 78.75,
                "abbr": "EbN",
            },
            "nw": {"trad": "Maestro", "point": "northwest", "mid": 315.0, "abbr": "NW"},
            "sbw": {
                "trad": "Quarto di Ostro verso Libeccio",
                "point": "south by west",
                "mid": 191.25,
                "abbr": "SbW",
            },
            "nbw": {
                "trad": "Quarto di Tramontana verso Maestro",
                "point": "north by west",
                "mid": 348.75,
                "abbr": "NbW",
            },
            "ssw": {
                "trad": "Ostro-Libeccio",
                "point": "south-southwest",
                "mid": 202.5,
                "abbr": "SSW",
            },
            "wnw": {
                "trad": "Maestro-Ponente",
                "point": "west-northwest",
                "mid": 292.5,
                "abbr": "WNW",
            },
            "sbe": {
                "trad": "Quarto di Ostro verso Scirocco",
                "point": "south by east",
                "mid": 168.75,
                "abbr": "SbE",
            },
            "sse": {
                "trad": "Ostro-Scirocco",
                "point": "south-southeast",
                "mid": 157.5,
                "abbr": "SSE",
            },
            "e": {"trad": "Levante", "point": "east", "mid": 90.0, "abbr": "E"},
            "wbs": {
                "trad": "Quarto di Ponente verso Libeccio",
                "point": "west by south",
                "mid": 258.75,
                "abbr": "WbS",
            },
            "sw": {
                "trad": "Libeccio",
                "point": "southwest",
                "mid": 225.0,
                "abbr": "SW",
            },
            "n": {"trad": "Tramontana", "point": "north", "mid": 0.0, "abbr": "N"},
            "w": {"trad": "Ponente", "point": "west", "mid": 270.0, "abbr": "W"},
            "s": {"trad": "Ostro", "point": "south", "mid": 180.0, "abbr": "S"},
            "wsw": {
                "trad": "Ponente-Libeccio",
                "point": "west-southwest",
                "mid": 247.5,
                "abbr": "WSW",
            },
            "wbn": {
                "trad": "Quarto di Ponente verso Maestro",
                "point": "west by north",
                "mid": 281.25,
                "abbr": "WbN",
            },
            "se": {
                "trad": "Scirocco",
                "point": "southeast",
                "mid": 135.0,
                "abbr": "SE",
            },
        }

        self.SEGMENTS = {
            0: self.ABBRS["n"],
            1: self.ABBRS["nbe"],
            2: self.ABBRS["nne"],
            3: self.ABBRS["nebn"],
            4: self.ABBRS["ne"],
            5: self.ABBRS["nebe"],
            6: self.ABBRS["ene"],
            7: self.ABBRS["ebn"],
            8: self.ABBRS["e"],
            9: self.ABBRS["ebs"],
            10: self.ABBRS["ese"],
            11: self.ABBRS["sebe"],
            12: self.ABBRS["se"],
            13: self.ABBRS["sebs"],
            14: self.ABBRS["sse"],
            15: self.ABBRS["sbe"],
            16: self.ABBRS["s"],
            17: self.ABBRS["sbw"],
            18: self.ABBRS["ssw"],
            19: self.ABBRS["swbs"],
            20: self.ABBRS["sw"],
            21: self.ABBRS["swbw"],
            22: self.ABBRS["wsw"],
            23: self.ABBRS["wbs"],
            24: self.ABBRS["w"],
            25: self.ABBRS["wbn"],
            26: self.ABBRS["wnw"],
            27: self.ABBRS["nwbw"],
            28: self.ABBRS["nw"],
            29: self.ABBRS["nwbn"],
            30: self.ABBRS["nnw"],
            31: self.ABBRS["nbw"],
        }

        self.ABBRS16 = {
            "e": {"trad": "Levante", "point": "east", "mid": 90.0, "abbr": "E"},
            "ene": {
                "trad": "Greco-Levante",
                "point": "east-northeast",
                "mid": 67.5,
                "abbr": "ENE",
            },
            "ese": {
                "trad": "Levante-Scirocco",
                "point": "east-southeast",
                "mid": 112.5,
                "abbr": "ESE",
            },
            "n": {"trad": "Tramontana", "point": "north", "mid": 0.0, "abbr": "N"},
            "ne": {"trad": "Greco", "point": "northeast", "mid": 45.0, "abbr": "NE"},
            "nne": {
                "trad": "Greco-Tramontana",
                "point": "north-northeast",
                "mid": 22.5,
                "abbr": "NNE",
            },
            "nnw": {
                "trad": "Maestro-Tramontana",
                "point": "north-northwest",
                "mid": 337.5,
                "abbr": "NNW",
            },
            "nw": {"trad": "Maestro", "point": "northwest", "mid": 315.0, "abbr": "NW"},
            "s": {"trad": "Ostro", "point": "south", "mid": 180.0, "abbr": "S"},
            "se": {
                "trad": "Scirocco",
                "point": "southeast",
                "mid": 135.0,
                "abbr": "SE",
            },
            "sse": {
                "trad": "Ostro-Scirocco",
                "point": "south-southeast",
                "mid": 157.5,
                "abbr": "SSE",
            },
            "ssw": {
                "trad": "Ostro-Libeccio",
                "point": "south-southwest",
                "mid": 202.5,
                "abbr": "SSW",
            },
            "sw": {
                "trad": "Libeccio",
                "point": "southwest",
                "mid": 225.0,
                "abbr": "SW",
            },
            "w": {"trad": "Ponente", "point": "west", "mid": 270.0, "abbr": "W"},
            "wnw": {
                "trad": "Maestro-Ponente",
                "point": "west-northwest",
                "mid": 292.5,
                "abbr": "WNW",
            },
            "wsw": {
                "trad": "Ponente-Libeccio",
                "point": "west-southwest",
                "mid": 247.5,
                "abbr": "WSW",
            },
        }

        self.SEGMENTS16 = {
            0: self.ABBRS16["n"],
            1: self.ABBRS16["nne"],
            2: self.ABBRS16["ne"],
            3: self.ABBRS16["ene"],
            4: self.ABBRS16["e"],
            5: self.ABBRS16["ese"],
            6: self.ABBRS16["se"],
            7: self.ABBRS16["sse"],
            8: self.ABBRS16["s"],
            9: self.ABBRS16["ssw"],
            10: self.ABBRS16["sw"],
            11: self.ABBRS16["wsw"],
            12: self.ABBRS16["w"],
            13: self.ABBRS16["wnw"],
            14: self.ABBRS16["nw"],
            15: self.ABBRS16["nnw"],
        }

        self.ABBRS08 = {
            "e": {"trad": "Levante", "point": "east", "mid": 90.0, "abbr": "E"},
            "n": {"trad": "Tramontana", "point": "north", "mid": 0.0, "abbr": "N"},
            "ne": {"trad": "Greco", "point": "northeast", "mid": 45.0, "abbr": "NE"},
            "nw": {"trad": "Maestro", "point": "northwest", "mid": 315.0, "abbr": "NW"},
            "s": {"trad": "Ostro", "point": "south", "mid": 180.0, "abbr": "S"},
            "se": {
                "trad": "Scirocco",
                "point": "southeast",
                "mid": 135.0,
                "abbr": "SE",
            },
            "sw": {
                "trad": "Libeccio",
                "point": "southwest",
                "mid": 225.0,
                "abbr": "SW",
            },
            "w": {"trad": "Ponente", "point": "west", "mid": 270.0, "abbr": "W"},
        }

        self.SEGMENTS08 = {
            0: self.ABBRS08["n"],
            1: self.ABBRS08["ne"],
            2: self.ABBRS08["e"],
            3: self.ABBRS08["se"],
            4: self.ABBRS08["s"],
            5: self.ABBRS08["sw"],
            6: self.ABBRS08["w"],
            7: self.ABBRS08["nw"],
        }

        self.ABBRS04 = {
            "e": {"trad": "Levante", "point": "east", "mid": 90.0, "abbr": "E"},
            "n": {"trad": "Tramontana", "point": "north", "mid": 0.0, "abbr": "N"},
            "s": {"trad": "Ostro", "point": "south", "mid": 180.0, "abbr": "S"},
            "w": {"trad": "Ponente", "point": "west", "mid": 270.0, "abbr": "W"},
        }

        self.SEGMENTS04 = {
            0: self.ABBRS04["n"],
            1: self.ABBRS04["e"],
            2: self.ABBRS04["s"],
            3: self.ABBRS04["w"],
        }

    def _by_(self, key, degree=None, abbr=None):
        if None not in (degree, abbr):
            raise ValueError("Requires an argument")

        if degree is not None:
            return self._by_degree(key, degree)

        if abbr:
            return self._by_abbr(key, abbr)

    def _by_abbr(self, key, abbr):
        return self.ABBRS[abbr.lower()][key]

    def _by_degree(self, key, degree):
        # 11.25 is 1/32 of a circle.
        # rotate by half that (5.625) because the 0th segment straddles the origin
        x = int(((degree + 5.625) % 360) / 11.25)
        return self.SEGMENTS[x][key]

    def point(self, degree=None, abbr=None):
        return self._by_("point", degree=degree, abbr=abbr)

    def traditional(self, degree=None, abbr=None):
        return self._by_("trad", degree=degree, abbr=abbr)

    def abbr(self, degree):
        return self._by_degree("abbr", degree)

    def degrees(self, abbr):
        mid = self.middle(abbr)
        return (mid - 5.625) % 360, mid, mid + 5.625

    def middle(self, abbr):
        return self._by_abbr("mid", abbr)

    def range(self, abbr):
        a, _, b = self.degrees(abbr)
        return (a, b)

    def _by_16(self, key, degree=None, abbr=None):
        if None not in (degree, abbr):
            raise ValueError("Requires an argument")
        if degree is not None:
            return self._by_degree16(key, degree)
        if abbr:
            return self._by_abbr16(key, abbr)

    def _by_abbr16(self, key, abbr):
        return self.ABBRS16[abbr.lower()][key]

    def _by_degree16(self, key, degree):
        x = int(((degree + 11.25) % 360) / 22.5)
        return self.SEGMENTS16[x][key]

    def point16(self, degree=None, abbr=None):
        return self._by_16("point", degree=degree, abbr=abbr)

    def traditional16(self, degree=None, abbr=None):
        return self._by_16("trad", degree=degree, abbr=abbr)

    def abbr16(self, degree):
        return self._by_degree16("abbr", degree)

    def degrees16(self, abbr):
        mid = self.middle16(abbr)
        return (mid - 11.25) % 360, mid, mid + 11.25

    def middle16(self, abbr):
        return self._by_abbr16("mid", abbr)

    def range16(self, abbr):
        a, _, b = self.degrees16(abbr)
        return (a, b)

    def _by_08(self, key, degree=None, abbr=None):
        if None not in (degree, abbr):
            raise ValueError("Requires an argument")
        if degree is not None:
            return self._by_degree08(key, degree)
        if abbr:
            return self._by_abbr08(key, abbr)

    def _by_abbr08(self, key, abbr):
        return self.ABBRS08[abbr.lower()][key]

    def _by_degree08(self, key, degree):
        x = int(((degree + 22.5) % 360) / 45.0)
        return self.SEGMENTS08[x][key]

    def point08(self, degree=None, abbr=None):
        return self._by_08("point", degree=degree, abbr=abbr)

    def traditional08(self, degree=None, abbr=None):
        return self._by_08("trad", degree=degree, abbr=abbr)

    def abbr08(self, degree):
        return self._by_degree08("abbr", degree)

    def degrees08(self, abbr):
        mid = self.middle08(abbr)
        return (mid - 22.5) % 360, mid, mid + 22.5

    def middle08(self, abbr):
        return self._by_abbr08("mid", abbr)

    def range08(self, abbr):
        a, _, b = self.degrees08(abbr)
        return (a, b)

    def _by_04(self, key, degree=None, abbr=None):
        if None not in (degree, abbr):
            raise ValueError("Requires an argument")
        if degree is not None:
            return self._by_degree04(key, degree)
        if abbr:
            return self._by_abbr04(key, abbr)

    def _by_abbr04(self, key, abbr):
        return self.ABBRS04[abbr.lower()][key]

    def _by_degree04(self, key, degree):
        x = int(((degree + 45.0) % 360) / 90.0)
        return self.SEGMENTS04[x][key]

    def point04(self, degree=None, abbr=None):
        return self._by_04("point", degree=degree, abbr=abbr)

    def traditional04(self, degree=None, abbr=None):
        return self._by_04("trad", degree=degree, abbr=abbr)

    def abbr04(self, degree):
        return self._by_degree04("abbr", degree)

    def degrees04(self, abbr):
        mid = self.middle04(abbr)
        return (mid - 44.5) % 360, mid, mid + 45.0

    def middle04(self, abbr):
        return self._by_abbr04("mid", abbr)

    def range04(self, abbr):
        a, _, b = self.degrees04(abbr)
        return (a, b)
