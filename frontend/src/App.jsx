import { useState, useEffect } from "react";

const API_BASE = "http://localhost:5000/api";

function App() {
  const [rosters, setRosters] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE}/rosters`)
      .then((res) => res.json())
      .then(setRosters)
      .catch((err) => setError(err.message));
  }, []);

  return (
    <div style={{ padding: "2rem", fontFamily: "sans-serif" }}>
      <h1>⚾ Baseball Simulation</h1>

      {error && <p style={{ color: "red" }}>Error: {error}</p>}

      {rosters ? (
        <div>
          {Object.entries(rosters).map(([teamKey, team]) => (
            <div key={teamKey} style={{ marginBottom: "2rem" }}>
              <h2>{teamKey.replace("_", " ").toUpperCase()}</h2>

              <h3>Position Players</h3>
              <ul>
                {team.position_players.map((p, i) => (
                  <li key={i}>
                    #{p.number} {p.name} — {p.position}
                  </li>
                ))}
              </ul>

              <h3>Starting Pitchers</h3>
              <ul>
                {team.pitchers.starters.map((p, i) => (
                  <li key={i}>
                    #{p.number} {p.name} — {p.position}
                  </li>
                ))}
              </ul>

              <h3>Relievers</h3>
              <ul>
                {team.pitchers.relievers.map((p, i) => (
                  <li key={i}>
                    #{p.number} {p.name} — {p.position}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      ) : (
        <p>Loading rosters...</p>
      )}
    </div>
  );
}

export default App;
