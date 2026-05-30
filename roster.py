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
            PositionPlayer("Francisco Lindor", 12, "SS", 84, 88),
            PositionPlayer("Juan Soto", 22, "RF", 97, 76),
            PositionPlayer("Bo Bichette", 19, "3B", 84, 70),
            PositionPlayer("Jorge Polanco", 11, "1B", 80, 76),
            PositionPlayer("Marcus Semien", 2, "2B", 84, 82),
            PositionPlayer("Brett Baty", 10, "DH", 76, 72),
            PositionPlayer("Francisco Alvarez", 4, "C", 82, 84),
            PositionPlayer("Luis Robert Jr.", 88, "CF", 82, 88),
            PositionPlayer("Carson Benge", 34, "LF", 73, 78),
            PositionPlayer("Mark Vientos", 27, "INF", 82, 72),
            PositionPlayer("Jeff McNeil", 1, "2B", 79, 82),
            PositionPlayer("Luis Torrens", 13, "C", 68, 74),
            PositionPlayer("DJ Stewart", 29, "OF", 70, 72),
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
                Pitcher("Devin Williams", 38, "CP", 84, 78),
                Pitcher("Edwin Diaz", 39, "RP", 90, 74),
                Pitcher("Adam Ottavino", 0, "RP", 79, 73),
                Pitcher("Phil Maton", 32, "RP", 76, 75),
                Pitcher("Drew Smith", 40, "RP", 78, 76),
                Pitcher("Jake Diekman", 35, "RP", 74, 71),
                Pitcher("Reed Garrett", 75, "RP", 74, 72),
                Pitcher("Sean Reid-Foley", 64, "RP", 73, 70),
            ]
        }
    },
    "away_team": {
        "position_players": [
           PositionPlayer("Aaron Judge", 99, "RF", 98, 92),
           PositionPlayer("Cody Bellinger", 35, "CF", 88, 88),
           PositionPlayer("Giancarlo Stanton", 27, "DH", 81, 60),
           # TODO(human): Add hit_rating and field_rating for each of these Yankees starters + bench
           PositionPlayer("Jazz Chisholm Jr.", 13, "3B", 0, 0),
           PositionPlayer("Anthony Volpe", 11, "SS", 0, 0),
           PositionPlayer("Austin Wells", 28, "C", 0, 0),
           PositionPlayer("Paul Goldschmidt", 46, "1B", 0, 0),
           PositionPlayer("Oswaldo Cabrera", 95, "2B", 0, 0),
           PositionPlayer("Trent Grisham", 12, "LF", 0, 0),
           PositionPlayer("Jose Trevino", 39, "C", 0, 0),
           PositionPlayer("DJ LeMahieu", 26, "INF", 0, 0),
           PositionPlayer("Oswaldo Peraza", 91, "INF", 0, 0),
           PositionPlayer("Ben Rice", 93, "1B", 0, 0),
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