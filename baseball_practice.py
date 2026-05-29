'''
Practice of baseball back-end logic game
  - CURRENT TRAJECTORY - Strictly text-based
  - FUTURE TRAJECTORY - SQLite & Flask server included 
    (database <--> backend <--> frontend)

'''


'''
# Pseudocode

- MAIN GOAL: build simulation that returns a successful simulation of a proper
nine-inning game (3 outs, 9 innings, final score, substitutions, box score, hit/walk/out)

- SUB GOALS:

  1. define main() function that handles all results from other functions
  2. pitch -> hit/foul/miss/called strike/ball -> result -> pitch 
    (user-controlled, timeouts() between events)
'''

'''
FUNCTIONS NEEDED
def init_roster() -- Call once, Roster initializes random players and stays the same until simulation starts over
                    Use dict to create players

def setup_field()
'''


from operator import truediv
from roster import PositionPlayer, rosters

def adjust_lineup_order(lineup, pos1, pos2):
    '''
    Params (Inputs)
      - lineup: list of PositionPlayer objects
      - pos1, pos2: 1-indexed batting order positions to swap
    Modifies lineup in-place.
    '''

    index1 = pos1 - 1
    index2 = pos2 - 1

    lineup[index1], lineup[index2] = lineup[index2], lineup[index1]

    return lineup


def display_lineups(lineup):
    '''
    Params (Input) - Batter Lineup (one team, list of PositionPlayer)
    Output - Prints numbered batting order to console

    Constraints:
    - No negatives
    - Only 1-9
    - No repeat inputs

    Helper Function - adjust_lineup_order()
    '''
    for order, player in enumerate(lineup, start=1):
        print(f"{order}. {player.name} - {player.position}")


def display_rotations(rotation):
    for order, player in enumerate(rotation, start=1):
        print(f"{order}. {player.name} - {player.position}")

def in_play():
    '''
     Function for when the ball is in play (bat makes contact with ball, not fouled)
    '''

    return

def pitch():
    '''
     params:
      - pitchRating(stuff, movement, control)
      - pitchTypes
      - pitchersStyle
     
      - hitRating(contact, hot/cold zones)


      IDEAS:
      - would like to build a function to take field dimensions into account
    '''

    return

def at_bat():
    '''
      - Function loop for a single at-bat

      -params
        - pitcher
        - hitter

      - functions
        - calc_outcome() - For the specific pitch

    '''

    return

def init_game():
    return print("Play Ball!")


def print_option(option):
    '''
    Docstring for printOption
    - Will call the specific function based on option
    - DIFFERENT OPTIONS:
      1. Play Ball!
      2. Check Lineups ->
      3. Adjust defensive positioning -> setup_field()
      4. Settings
      5. Quit

    :param option: Input of what was chosen from main()
    '''        
    team_rosters = [rosters['away_team'], rosters['home_team']] # List of two dictionaries
    team_names = ["New York Yankees", "New York Mets"]


    if option == 1:
        init_game()
    elif option == 2:
        [team['position_players'] for team in team_rosters]
        for i, team in enumerate(batters):
            print(f"\n--- {team_names[i]} Lineup ---")
            display_lineups(team)

            while True:
                try:
                    raw1 = input("Choose 1st player to switch or type 'done': ")
                    if raw1.lower() == 'done':
                        break
                    raw2 = input("Choose 2nd player to switch with or type 'done': ")
                    if raw2.lower() == 'done':
                        break

                    first_player = int(raw1)
                    second_player = int(raw2)


                    if 1 <= first_player <= len(team) and 1 <= second_player <= len(team) and first_player != second_player:
                        adjust_lineup_order(team, first_player, second_player)
                        print(f"\n--- {team_names[i]} Updated Lineup ---")
                        display_lineups(team)
                    else:
                        print(f"Enter two different numbers between 1 and {len(team)}")
                except ValueError:
                    print(f"Enter two different numbers between 1 and {len(team)}")

    elif option == 3:
        starting_pitchers = [team['pitchers']['starters'] for team in team_rosters]
        for i, team in enumerate(starting_pitchers):  
            print(f"\n--- {team_names[i]} Rotation ---")
            display_rotations(team)

            while True:
                try:
                    raw1 = input("Choose 1st player to switch or type 'done': ")
                    if raw1.lower() == 'done':
                        break
                    raw2 = input("Choose 2nd player to switch with or type 'done': ")
                    if raw2.lower() == 'done':
                        break

                    first_player = int(raw1)
                    second_player = int(raw2)

                    if 1 <= first_player <= len(team) and 1 <= second_player <= len(team) and first_player != second_player:
                        adjust_lineup_order(team, first_player, second_player)
                        print(f"\n--- {team_names[i]} Updated Lineup ---")
                        display_rotations(team)
                    else:
                        print(f"Enter two different numbers between 1 and {len(team)}")
                except ValueError:
                    print(f"Enter two different numbers between 1 and {len(team)}")

    elif option == 5:
        quit()
        
    # return/cleanup after intended function


def main():
    """Main loop - Pitching, Hitting, Results"""
    print("WELCOME TO MY BASEBALL SIMULATION")
    print("1. Play Ball!")
    print("2. Adjust Lineups") # Lineups / Positioning -> Line 123
    print("3. Adjust Rotation")
    print("4. Settings")
    print("5. Quit")


    while True:
        try:
            option=int(input("Choose an option (1-5): ")) # waits for string input -> converts into integer
            if 1 <= option <= 5: # boundary conditions: 1 & 5
                print_option(option)
        except ValueError:
            print("Enter a number")


if __name__ == '__main__':
    '''
      This block makes sure that the main() function only runs when this
      file is ran directly, not when imported
    '''
    main()