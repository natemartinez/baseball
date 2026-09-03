

class StrikeZone():
    def __init__(self):
        self.grid = {
            "INNER": {
                (0,0): "Top-Left", (0,1): "Top-Middle", (0,2): "Top-Right",
                (1,0): "Middle-Left", (1,1): "Middle", (1,2): "Middle-Right",
                (2,0): "Bottom-Left", (2,1): "Bottom-Middle", (2,2): "Bottom-Right"
            },
            "OUTER": {
                (0,0): "Top-Left", (0,1): "Top-Middle", (0,2): "Top-Right",
                (1,0): "Middle-Left", (1,1): "Middle", (1,2): "Middle-Right",
                (2,0): "Bottom-Left", (2,1): "Bottom-Middle", (2,2): "Bottom-Right"
            }
        }

# establish batter's hot/cold zones
# establish pitcher's hot/cold zones - coloring is opposite to a batter ( the lower, the better)