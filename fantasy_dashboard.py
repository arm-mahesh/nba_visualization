import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QComboBox, QLineEdit,
    QPushButton, QHBoxLayout, QCompleter, QTabWidget, QListWidget
)
from PyQt6.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import time
import json
import pandas as pd
from requests.exceptions import ReadTimeout
from nba_api.stats.static import players
from nba_api.stats.endpoints import playercareerstats, commonplayerinfo


class FantasyDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Fantasy Basketball Dashboard")
        self.setGeometry(100, 100, 1000, 700)

        # Create tabs and add them to the tab widget
        with open('player_positions.json', 'r') as f:
            self.player_positions = json.load(f)

        # Extract player names and initialize UI
        self.player_names = [player['name'] for player in self.player_positions]
        # Tab widget for switching pages
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Create tabs
        self.create_player_stats_tab()
        self.create_position_filter_tab()

    def create_player_stats_tab(self):
        """Create the Player Stats tab."""
        player_stats_widget = QWidget()
        layout = QVBoxLayout(player_stats_widget)

        # Load player list for autocomplete
        self.all_players = players.get_active_players()
        self.player_names = [player['full_name'] for player in self.all_players]

        # Search Bar for Player 1
        search_layout_1 = QHBoxLayout()
        self.search_bar_1 = QLineEdit()
        self.search_bar_1.setPlaceholderText("Search Player 1...")
        self.search_completer_1 = QCompleter(self.player_names)
        self.search_completer_1.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.search_bar_1.setCompleter(self.search_completer_1)
        search_button_1 = QPushButton("Search Player 1")
        search_button_1.clicked.connect(self.search_player_1)
        search_layout_1.addWidget(self.search_bar_1)
        search_layout_1.addWidget(search_button_1)
        layout.addLayout(search_layout_1)

        # Search Bar for Player 2
        search_layout_2 = QHBoxLayout()
        self.search_bar_2 = QLineEdit()
        self.search_bar_2.setPlaceholderText("Search Player 2...")
        self.search_completer_2 = QCompleter(self.player_names)
        self.search_completer_2.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.search_bar_2.setCompleter(self.search_completer_2)
        search_button_2 = QPushButton("Search Player 2")
        search_button_2.clicked.connect(self.search_player_2)
        search_layout_2.addWidget(self.search_bar_2)
        search_layout_2.addWidget(search_button_2)
        layout.addLayout(search_layout_2)

        # Dropdown for metric selection
        self.metric_label = QLabel("Select Metric:")
        layout.addWidget(self.metric_label)

        self.metric_dropdown = QComboBox()
        self.metric_dropdown.addItems(["Points Per Game", "Assists", "Rebounds", "Efficiency"])
        self.metric_dropdown.currentIndexChanged.connect(self.update_plot)
        layout.addWidget(self.metric_dropdown)

        # Matplotlib figure
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        # Placeholder for game insights
        self.insight_label = QLabel("Future Game Insights Coming Soon...")
        layout.addWidget(self.insight_label)

        # Initialize data and current players
        self.data_1 = None
        self.data_2 = None
        self.current_player_1 = None
        self.current_player_2 = None

        # Add this tab to the main widget
        self.tabs.addTab(player_stats_widget, "Player Stats")

    def create_position_filter_tab(self):
        """Create the Position Filtering tab."""
        position_filter_widget = QWidget()
        layout = QVBoxLayout(position_filter_widget)

        # Dropdown for position selection
        self.position_label = QLabel("Select Position:")
        layout.addWidget(self.position_label)

        self.position_dropdown = QComboBox()
        self.position_dropdown.addItems(["All", "Guard", "Forward", "Center"])
        self.position_dropdown.currentIndexChanged.connect(self.filter_players_by_position)
        layout.addWidget(self.position_dropdown)

        # Player list display
        self.player_list_widget = QListWidget()
        layout.addWidget(self.player_list_widget)

        # Load all players initially
        self.load_all_players()

        # Add this tab to the main widget
        self.tabs.addTab(position_filter_widget, "Position Filter")

    def load_all_players(self):
        """Load all players into the player list widget."""
        self.player_list_widget.clear()
        for player in self.all_players:
            self.player_list_widget.addItem(player['full_name'])

    def filter_players_by_position(self):
        """Filter players based on the selected position."""
        position = self.position_dropdown.currentText()

        if position == "All":
            filtered_players = self.player_positions
        else:
            filtered_players = [
                player for player in self.player_positions if position in player['position']
            ]

        # Update the player list widget
        self.player_list_widget.clear()
        for player in filtered_players:
            self.player_list_widget.addItem(player['name'])

    def search_player_1(self):
        """Search for the first player and load their stats."""
        player_name = self.search_bar_1.text()
        matched_player = next((p for p in self.all_players if p['full_name'].lower() == player_name.lower()), None)

        if matched_player:
            self.current_player_1 = matched_player
            self.load_player_data(1)
        else:
            self.metric_label.setText("Player 1 not found! Try again.")

    def search_player_2(self):
        """Search for the second player and load their stats."""
        player_name = self.search_bar_2.text()
        matched_player = next((p for p in self.all_players if p['full_name'].lower() == player_name.lower()), None)

        if matched_player:
            self.current_player_2 = matched_player
            self.load_player_data(2)
        else:
            self.metric_label.setText("Player 2 not found! Try again.")

    def load_player_data(self, player_num):
        """Load stats for the selected player."""
        if player_num == 1:
            player = self.current_player_1
        else:
            player = self.current_player_2

        player_id = player['id']
        career_stats = playercareerstats.PlayerCareerStats(player_id=player_id)
        df = career_stats.get_data_frames()[0]

        # Preprocess player stats
        df['Points Per Game'] = df['PTS'] / df['GP']
        df['Assists'] = df['AST'] / df['GP']
        df['Rebounds'] = df['REB'] / df['GP']
        df['Efficiency'] = (df['PTS'] + df['REB'] + df['AST']) / df['GP']
        filtered_data = df[['SEASON_ID', 'Points Per Game', 'Assists', 'Rebounds', 'Efficiency']]

        if player_num == 1:
            self.data_1 = filtered_data
        else:
            self.data_2 = filtered_data

        self.metric_label.setText(f"Stats updated for {player['full_name']}")
        self.update_plot()

    def update_plot(self):
        """Update the plot based on selected metric."""
        if self.data_1 is None and self.data_2 is None:
            self.metric_label.setText("Search for players first!")
            return

        # Clear the current figure
        self.figure.clear()

        # Get selected metric
        metric = self.metric_dropdown.currentText()

        # Align the seasons for both players
        if self.data_1 is not None and self.data_2 is not None:
            all_seasons = sorted(set(self.data_1['SEASON_ID']).union(set(self.data_2['SEASON_ID'])))
            self.data_1 = self.data_1.set_index('SEASON_ID').reindex(all_seasons).reset_index()
            self.data_2 = self.data_2.set_index('SEASON_ID').reindex(all_seasons).reset_index()

        ax = self.figure.add_subplot(111)

        # Plot Player 1's data
        if self.data_1 is not None:
            ax.plot(
                self.data_1['SEASON_ID'],
                self.data_1[metric],
                marker='o',
                label=self.current_player_1['full_name']
            )

        # Plot Player 2's data
        if self.data_2 is not None:
            ax.plot(
                self.data_2['SEASON_ID'],
                self.data_2[metric],
                marker='x',
                label=self.current_player_2['full_name']
            )

        # Update plot aesthetics
        ax.set_title(f"{metric} Over Seasons")
        ax.set_xlabel("Season")
        ax.set_ylabel(metric)
        ax.legend()
        ax.grid(True)

        # Redraw the canvas
        self.canvas.draw()

    def fetch_player_info(player_id, retries=3):
        for attempt in range(retries):
            try:
                return commonplayerinfo.CommonPlayerInfo(player_id=player_id)
            except ReadTimeout:
                if attempt < retries - 1:
                    time.sleep(2)  # Wait before retrying
                    continue
                else:
                    raise



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FantasyDashboard()
    window.show()
    sys.exit(app.exec())
