# August 2026 Dev Log - Main Gameplay Loop, Integration of Database

## My Thought Process

I decided to my all my attention to fully manually working out the logic of the core loop of any Baseball game - **"The At-Bat"**
The battle between Pitcher & Catcher vs. Batter is a battle with preparation, strategy, and many different factors to determine a specific result.

When considering the logic for the at-bat loop, I wanted to try to emulate the real-world process of a pitcher knowing:
- What pitch to throw
- What batter expects to be thrown
- How pitcher executes the pitch
- How Batter reacts to the pitch - (Does batter swing or not?)
- If Batter swings, did they make contact? 
- If bat makes contact with ball -> How is result determined? -> What's the end result?

In its current state as a "prototype" baseball simulation, each step is randomized using probablity weights (from Statcast) to protect from repeated 
outliers.

## Database Integration
Once the basic at-bat logic was working with test numbers, the next step was figuring out how to actually store and pull real player data.

At first, I was considering just looking through all the players in the database and filtering them to their proper teams whenever a specific team got queried. But searching through every single player every time would take way too long. I also thought about doing the opposite—having a database of teams and keeping the players inside them—but that gets messy fast when players change teams, get traded, or when tracking different seasons.

## Decision
Instead, I landed on a setup that gives me the best of both worlds:

- **Junction Table for Teams & Rosters**: I set up separate tables for teams and players, and connected them using a rosters table with indexes. That way, grabbing a team's active roster doesn't scan the whole database; it just instantly grabs the players linked to that team for that season.

- **JSON for Deep Player Data**: For things like pitch zones, attribute ratings, seasonal stats, and traits, I kept them as JSON inside the player row. It keeps things flexible so I don't have to build ten separate tables just to store a player's hitting zones or badges.

- **Connecting Database to Simulation**: I didn't want the game engine itself to be touching raw SQL or parsing JSON strings in the middle of a pitch. The idea is to have a clean pipeline where the database pulls the raw data, turns it into clean Player objects with the right stats and traits, feeds those objects into the simulation engine to run the at-bat, and then sends the result over to the frontend.

## Flow Graph

[ SQLite (players.db) ]
        │  1. SELECT row & json.loads()
        ▼
[ Data Access Layer (db.py) ]
        │  2. Raw Python dict
        ▼
[ Domain Models (player.py) ]  ──►  [ Simulation Engine (game_engine.py) ]
        │                                  │
        │                                  ▼
[ API / Transport (main.py) ]  ◄──  Simulation Event Log (JSON)
        │
        ▼  3. HTTP / WebSocket
[ Client (static/templates or SPA) ]

### Explanations of components (for the Flow Graph)
- SQLite (players.db): Stores persistent player tables and serialized JSON attributes (zones, ratings, traits).

- Data Access Layer (db.py): Handles raw SQL queries and converts stored JSON strings into standard Python dictionaries.

- Domain Models (player.py): Turns raw dictionaries into typed Player objects with helper methods (get_rating(), has_trait()) so the engine never deals with raw dictionary keys.

- Simulation Engine (game_engine.py): Takes the hydrated Player objects, evaluates the pitch/swing probabilities, and generates a chronological event log of the outcome.

- API / Transport (main.py): Coordinates the flow—receives user requests, pulls player IDs, runs the engine, and formats the event log as JSON.

- Client (Frontend UI): Consumes the JSON event log over HTTP or WebSockets to render animations, strike zone graphics, and the box score.



*Written on September 2nd*