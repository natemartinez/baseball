import tkinter as tk
from tkinter import messagebox, Listbox, MULTIPLE, Button, Label, Frame
from roster import PositionPlayer, rosters
from backend.game_engine import GameEngine
import random

# ------------------- YOUR EXISTING BACKEND (unchanged) -------------------
def adjust_lineup_order(lineup, pos1, pos2):
    index1 = pos1 - 1
    index2 = pos2 - 1
    lineup[index1], lineup[index2] = lineup[index2], lineup[index1]
    return lineup

def display_lineups(lineup):
    lines = []
    for order, player in enumerate(lineup, start=1):
        lines.append(f"{order}. {player.name} - {player.position}")
    return lines

def display_rotations(rotation):
    lines = []
    for order, player in enumerate(rotation, start=1):
        lines.append(f"{order}. {player.name} - {player.position}")
    return lines
# -------------------------------------------------------------------------


# ------------------------- MAIN UI (SINGLE WINDOW) -------------------------
class BaseballApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Baseball Simulation")
        self.root.geometry("700x600")

        # Load team data
        self.team_rosters = [rosters['away_team'], rosters['home_team']]
        self.team_names = ["New York Yankees", "New York Mets"]

        # Current state
        self.current_team_index = 0
        self.current_mode = None
        self.game_engine = None

        # Toolbar
        toolbar = Frame(root)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        Button(toolbar, text="Play Ball!", command=self.show_game).pack(side=tk.LEFT, padx=5, pady=5)
        Button(toolbar, text="Adjust Lineups", command=self.show_lineups).pack(side=tk.LEFT, padx=5, pady=5)
        Button(toolbar, text="Adjust Rotation", command=self.show_rotation).pack(side=tk.LEFT, padx=5, pady=5)
        Button(toolbar, text="Settings", command=self.show_settings).pack(side=tk.LEFT, padx=5, pady=5)
        Button(toolbar, text="Quit", command=root.quit).pack(side=tk.LEFT, padx=5, pady=5)

        # Main content area
        self.content_frame = Frame(root)
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.show_welcome()

    def clear_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def show_welcome(self):
        self.clear_content()
        Label(self.content_frame, text="Welcome to Baseball Simulation\nSelect an option from the toolbar.").pack(expand=True)

    # ------------------------- GAME VIEW (with simulation) -------------------------
    def show_game(self):
        self.current_mode = 'game'
        self.clear_content()

        # Initialize a fresh game engine using current rosters (which may have been edited)
        away_team = self.team_rosters[0]  # away = Yankees index 0? check order: rosters['away_team'] first
        home_team = self.team_rosters[1]
        self.game_engine = GameEngine(home_team, away_team, self.team_names[1], self.team_names[0])

        # UI elements
        self.game_info_label = Label(self.content_frame, text="", font=("Courier", 12), justify=tk.LEFT)
        self.game_info_label.pack(pady=10)

        self.pitch_button = Button(self.content_frame, text="Throw Pitch", command=self.throw_pitch)
        self.pitch_button.pack(pady=5)

        self.reset_button = Button(self.content_frame, text="Reset Game", command=self.reset_game)
        self.reset_button.pack(pady=5)

        self.update_game_display()

    def throw_pitch(self):
        if self.game_engine.game_over:
            messagebox.showinfo("Game Over", "The game is over. Press Reset Game to play again.")
            return
        result, (outs, balls, strikes) = self.game_engine.pitch()
        # Show result in a temporary status bar or messagebox? Use a label.
        if not hasattr(self, 'result_label'):
            self.result_label = Label(self.content_frame, text="", fg="blue")
            self.result_label.pack(pady=5)
        self.result_label.config(text=f"Last pitch: {result}")
        self.update_game_display()

    def reset_game(self):
        # Re-initialize game engine with same rosters
        away_team = self.team_rosters[0]
        home_team = self.team_rosters[1]
        self.game_engine = GameEngine(home_team, away_team, self.team_names[1], self.team_names[0])
        self.update_game_display()
        if hasattr(self, 'result_label'):
            self.result_label.config(text="Game reset.")

    def update_game_display(self):
        state_text = self.game_engine.get_game_state_text()
        self.game_info_label.config(text=state_text)
        if self.game_engine.game_over:
            self.pitch_button.config(state=tk.DISABLED)
        else:
            self.pitch_button.config(state=tk.NORMAL)

    # ---------- LINEUP UI (same as before) ----------
    def show_lineups(self):
        self.current_mode = 'lineup'
        self.current_team_index = 0
        self._refresh_lineup_view()

    def _refresh_lineup_view(self):
        self.clear_content()
        header_frame = Frame(self.content_frame)
        header_frame.pack(fill=tk.X, pady=5)
        Label(header_frame, text=f"Batting Order - {self.team_names[self.current_team_index]}", font=("Arial", 14)).pack(side=tk.LEFT)
        def next_team():
            self.current_team_index = (self.current_team_index + 1) % 2
            self._refresh_lineup_view()
        Button(header_frame, text="Next Team", command=next_team).pack(side=tk.RIGHT)

        self.lineup_listbox = Listbox(self.content_frame, width=50, height=15, selectmode=MULTIPLE)
        self.lineup_listbox.pack(pady=10)

        batters = self.team_rosters[self.current_team_index]['position_players']
        lines = display_lineups(batters)
        for line in lines:
            self.lineup_listbox.insert(tk.END, line)

        def swap_selected():
            selected = self.lineup_listbox.curselection()
            if len(selected) != 2:
                messagebox.showwarning("Selection", "Please select exactly two players to swap.")
                return
            pos1 = selected[0] + 1
            pos2 = selected[1] + 1
            adjust_lineup_order(batters, pos1, pos2)
            self.lineup_listbox.delete(0, tk.END)
            new_lines = display_lineups(batters)
            for line in new_lines:
                self.lineup_listbox.insert(tk.END, line)
        Button(self.content_frame, text="Swap Selected Players", command=swap_selected).pack(pady=5)

    # ---------- ROTATION UI ----------
    def show_rotation(self):
        self.current_mode = 'rotation'
        self.current_team_index = 0
        self._refresh_rotation_view()

    def _refresh_rotation_view(self):
        self.clear_content()
        header_frame = Frame(self.content_frame)
        header_frame.pack(fill=tk.X, pady=5)
        Label(header_frame, text=f"Starting Rotation - {self.team_names[self.current_team_index]}", font=("Arial", 14)).pack(side=tk.LEFT)
        def next_team():
            self.current_team_index = (self.current_team_index + 1) % 2
            self._refresh_rotation_view()
        Button(header_frame, text="Next Team", command=next_team).pack(side=tk.RIGHT)

        self.rotation_listbox = Listbox(self.content_frame, width=50, height=15, selectmode=MULTIPLE)
        self.rotation_listbox.pack(pady=10)

        pitchers = self.team_rosters[self.current_team_index]['pitchers']['starters']
        lines = display_rotations(pitchers)
        for line in lines:
            self.rotation_listbox.insert(tk.END, line)

        def swap_selected():
            selected = self.rotation_listbox.curselection()
            if len(selected) != 2:
                messagebox.showwarning("Selection", "Select exactly two pitchers to swap.")
                return
            pos1 = selected[0] + 1
            pos2 = selected[1] + 1
            adjust_lineup_order(pitchers, pos1, pos2)
            self.rotation_listbox.delete(0, tk.END)
            new_lines = display_rotations(pitchers)
            for line in new_lines:
                self.rotation_listbox.insert(tk.END, line)
        Button(self.content_frame, text="Swap Selected Pitchers", command=swap_selected).pack(pady=5)

    def show_settings(self):
        self.current_mode = 'settings'
        self.clear_content()
        Label(self.content_frame, text="SETTINGS (not implemented yet)").pack(pady=10)

# ------------------------- MAIN ENTRY POINT -------------------------
if __name__ == '__main__':
    root = tk.Tk()
    app = BaseballApp(root)
    root.mainloop()