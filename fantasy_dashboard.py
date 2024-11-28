import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QComboBox, QLineEdit, QPushButton, QHBoxLayout, QCompleter
)
from PyQt6.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import pandas as pd
from nba_api.stats.static import players
from nba_api.stats.endpoints import playercareerstats


class FantasyDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Fantasy Basketball Dashboard")
        self.setGeometry(100, 100, 1000, 700)

        # Main container widget
        self.container = QWidget(self)
        self.setCentralWidget(self.container)
        self.layout = QVBoxLayout(self.container)

        # Load player list for autocomplete
        self.all_players = players.get_players()
        self.player_names = [player['full_name'] for player in self.all_players]

        # Search Bar with Autocomplete
        search_layout = QHBoxLayout()
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search Player...")
        self.search_completer = QCompleter(self.player_names)
        self.search_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.search_bar.setCompleter(self.search_completer)
        search_button = QPushButton("Search")
        search_button.clicked.connect(self.search_player)
        search_layout.addWidget(self.search_bar)
        search_layout.addWidget(search_button)
        self.layout.addLayout(search_layout)

        # Dropdown for metric selection
        self.metric_label = QLabel("Select Metric:")
        self.layout.addWidget(self.metric_label)

        self.metric_dropdown = QComboBox()
        self.metric_dropdown.addItems(["Points Per Game", "Assists", "Rebounds", "Efficiency"])
        self.metric_dropdown.currentIndexChanged.connect(self.update_plot)
        self.layout.addWidget(self.metric_dropdown)

        # Matplotlib figure
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.layout.addWidget(self.canvas)

        # Placeholder for game insights
        self.insight_label = QLabel("Future Game Insights Coming Soon...")
        self.layout.addWidget(self.insight_label)

        # Initialize data and current player
        self.data = None
        self.current_player = None

    def search_player(self):
        """Search for a player and load their stats."""
        player_name = self.search_bar.text()
        matched_player = next((p for p in self.all_players if p['full_name'].lower() == player_name.lower()), None)

        if matched_player:
            self.current_player = matched_player
            self.load_player_data()
        else:
            self.metric_label.setText("Player not found! Try again.")

    def load_player_data(self):
        """Load stats for the currently selected player."""
        player_id = self.current_player['id']
        career_stats = playercareerstats.PlayerCareerStats(player_id=player_id)
        df = career_stats.get_data_frames()[0]

        # Preprocess player stats
        df['Points Per Game'] = df['PTS'] / df['GP']
        df['Assists'] = df['AST'] / df['GP']
        df['Rebounds'] = df['REB'] / df['GP']
        df['Efficiency'] = (df['PTS'] + df['REB'] + df['AST']) / df['GP']
        self.data = df[['SEASON_ID', 'Points Per Game', 'Assists', 'Rebounds', 'Efficiency']]

        self.metric_label.setText(f"Stats for {self.current_player['full_name']}")
        self.update_plot()

    def update_plot(self):
        """Update the plot based on selected metric."""
        if self.data is None:
            self.metric_label.setText("Search for a player first!")
            return

        # Clear the current figure
        self.figure.clear()

        # Get selected metric
        metric = self.metric_dropdown.currentText()

        # Plot the selected metric
        ax = self.figure.add_subplot(111)
        ax.plot(self.data['SEASON_ID'], self.data[metric], marker='o')
        ax.set_title(f"{metric} Over Seasons for {self.current_player['full_name']}")
        ax.set_xlabel("Season")
        ax.set_ylabel(metric)
        ax.grid(True)

        # Redraw the canvas
        self.canvas.draw()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FantasyDashboard()
    window.show()
    sys.exit(app.exec())
