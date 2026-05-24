class Player:
    def __init__(self, name, number, field_rating):
        self.name = name
        self.number = number
        self.field_rating = field_rating
      

class StartingPitcher(Player): 
    def __init__(self, name, number, pitch_rating, field_rating):
        super().__init__(name, number, "SP", field_rating)
        self.pitch_rating = pitch_rating

    def __str__(self):
        return f"#{self.number} {self.name} - Starting Pitcher / Pitcher Ratings: Pitch: {self.pitch_rating} Fielding: {self.field_rating}"   
    
class PositionPlayer(Player): 
    def __init__(self, name, number, position, hit_rating, field_rating):
        super().__init__(name, number, field_rating) #super() passes into the parent class(inheritance) so need to have 
        self.position = position                     # same parameters as the parent class besides 'self'
        self.hit_rating = hit_rating

    def __str__(self):
        return f"#{self.number} {self.name} Pos: {self.position} / Ratings: Hitting: {self.hit_rating} Fielding: {self.field_rating}"   
    

# 
rosters = {
    "home_team" : {
        "position_players": [
            PositionPlayer("Juan Soto", 22, "RF", 97, 73),
            PositionPlayer("Francisco Lindor", 12, "SS", 84, 81),
            PositionPlayer("Bo Bichette", 19, "3B", 84, 70),
        ],
    },
    "away_team": {
        "position_players": [
           PositionPlayer("Aaron Judge", 99, "RF", 98, 92),
           PositionPlayer("Cody Bellinger", 35, "RF", 98, 92),
           PositionPlayer("Giancarlo Stanton", 35, "LF", 81, 60),
        ]
    }
}