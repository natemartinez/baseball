class Player:
    def __init__(self, name, number, field_rating):
        self.name = name
        self.number = number
        self.field_rating = field_rating
      

class Pitcher(Player): 
    def __init__(self, name, number, position, pitch_rating, field_rating):
        super().__init__(name, number, field_rating)
        self.position = position
        self.pitch_rating = pitch_rating

    def __str__(self):
        return f"#{self.number} {self.name} - {self.position} / Pitcher Ratings: Pitch: {self.pitch_rating} Fielding: {self.field_rating}"   
    
class PositionPlayer(Player): 
    def __init__(self, name, number, position, hit_rating, field_rating):
        super().__init__(name, number, field_rating) # super() passes into the parent class(inheritance) so need to have 
        self.position = position                     # same parameters as the parent class besides 'self'
        self.hit_rating = hit_rating

    def __str__(self):
        return f"#{self.number} {self.name} Pos: {self.position} / Ratings: Hitting: {self.hit_rating} Fielding: {self.field_rating}"   
    

# 
rosters = {
    "home_team" : {
        "position_players": [
            PositionPlayer("Juan Soto", 22, "RF", 97, 76),
            PositionPlayer("Francisco Lindor", 12, "SS", 84, 88),
            PositionPlayer("Bo Bichette", 19, "3B", 84, 70),
        ],
        "pitchers": {
            "starters": [
                Pitcher("Freddy Peralta", 51, "SP", 87, 78),
                Pitcher("Nolan Mclean", 26, "SP", 87, 84),
                Pitcher("David Peterson", 23, "SP", 78, 75),
                Pitcher("Christian Scott", 45, "SP", 76, 63),
                Pitcher("Jonah Tong", 21, "SP", 78, 61),
            ],
            "relievers": [
                Pitcher("Devin Williams", 38, "CP", 84, 78)
            ]
        }
    },
    "away_team": {
        "position_players": [
           PositionPlayer("Aaron Judge", 99, "RF", 98, 92),
           PositionPlayer("Cody Bellinger", 35, "RF", 98, 92),
           PositionPlayer("Giancarlo Stanton", 35, "LF", 81, 60),
        ],
        "pitchers": {
            "starters": [
                Pitcher("Max Fried", 54, "SP", 87, 78),
                Pitcher("Cam Schlittler", 31, "SP", 87, 84),
                Pitcher("Will Warren", 29, "SP", 82, 75),
                Pitcher("Carlos Rodon", 55, "SP", 83, 63),
                Pitcher("Ryan Weathers", 40, "SP", 76, 61),
            ],
            "relievers": [
                Pitcher("David Bednar", 53, "CP", 84, 78)
            ]
        }        
    }
}