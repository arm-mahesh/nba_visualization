import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QComboBox, QLineEdit,
    QPushButton, QHBoxLayout, QCompleter, QTabWidget, QListWidget, QFormLayout
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
        self.setGeometry(100, 100, 1200, 800)

        self.current_player_1 = None
        self.current_player_2 = None
        self.data_1 = None
        self.data_2 = None

        self.fantasy_settings = {
            'PTS': 1,
            'REB': 1.2,
            'AST': 1.5,
            'STL': 3,
            'BLK': 3,
            'TO': -1
        }

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
        self.create_settings_tab()

    def create_settings_tab(self):
        """Create the Settings tab."""
        settings_widget = QWidget()
        layout = QVBoxLayout(settings_widget)

        # Form layout for fantasy point settings
        form_layout = QFormLayout()

        self.pts_input = QLineEdit(str(self.fantasy_settings['PTS']))
        form_layout.addRow("Fantasy Points for PTS:", self.pts_input)

        self.reb_input = QLineEdit(str(self.fantasy_settings['REB']))
        form_layout.addRow("Fantasy Points for REB:", self.reb_input)

        self.ast_input = QLineEdit(str(self.fantasy_settings['AST']))
        form_layout.addRow("Fantasy Points for AST:", self.ast_input)

        self.stl_input = QLineEdit(str(self.fantasy_settings['STL']))
        form_layout.addRow("Fantasy Points for STL:", self.stl_input)

        self.blk_input = QLineEdit(str(self.fantasy_settings['BLK']))
        form_layout.addRow("Fantasy Points for BLK:", self.blk_input)

        self.to_input = QLineEdit(str(self.fantasy_settings['TO']))
        form_layout.addRow("Fantasy Points for TO:", self.to_input)

        layout.addLayout(form_layout)

        # Save Button
        save_button = QPushButton("Save Settings")
        save_button.clicked.connect(self.save_settings)
        layout.addWidget(save_button)

        self.tabs.addTab(settings_widget, "Settings")

    def save_settings(self):
        """Save the custom fantasy points settings."""
        try:
            self.fantasy_settings['PTS'] = float(self.pts_input.text())
            self.fantasy_settings['REB'] = float(self.reb_input.text())
            self.fantasy_settings['AST'] = float(self.ast_input.text())
            self.fantasy_settings['STL'] = float(self.stl_input.text())
            self.fantasy_settings['BLK'] = float(self.blk_input.text())
            self.fantasy_settings['TO'] = float(self.to_input.text())

            print("Settings saved successfully.")
        except ValueError:
            print("Invalid input. Please enter numeric values.")

    def create_player_stats_tab(self):
        """Create the Player Stats tab."""
        player_stats_widget = QWidget()
        layout = QVBoxLayout(player_stats_widget)
        self.all_players = players.get_active_players()

        # Player Stats Tab
        self.player_stats_tab = QWidget()
        self.setup_player_stats_tab()
        self.tabs.addTab(self.player_stats_tab, "Compare Players")

        # Projections Tab
        self.projections_tab = QWidget()
        self.setup_projections_tab()
        self.tabs.addTab(self.projections_tab, "Per-Game Projections")

    def setup_player_stats_tab(self):
        layout = QVBoxLayout(self.player_stats_tab)

        # Search Bars for Player 1 and Player 2
        search_layout_1 = QHBoxLayout()
        self.search_bar_1 = QLineEdit()
        self.search_bar_1.setPlaceholderText("Search Player 1...")
        self.search_completer_1 = QCompleter(self.player_names)
        self.search_completer_1.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.search_bar_1.setCompleter(self.search_completer_1)
        search_button_1 = QPushButton("Search Player 1")
        search_button_1.clicked.connect(lambda: self.search_player(1))
        search_layout_1.addWidget(self.search_bar_1)
        search_layout_1.addWidget(search_button_1)
        layout.addLayout(search_layout_1)

        search_layout_2 = QHBoxLayout()
        self.search_bar_2 = QLineEdit()
        self.search_bar_2.setPlaceholderText("Search Player 2...")
        self.search_completer_2 = QCompleter(self.player_names)
        self.search_completer_2.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.search_bar_2.setCompleter(self.search_completer_2)
        search_button_2 = QPushButton("Search Player 2")
        search_button_2.clicked.connect(lambda: self.search_player(2))
        search_layout_2.addWidget(self.search_bar_2)
        search_layout_2.addWidget(search_button_2)
        layout.addLayout(search_layout_2)

        # Dropdown for metric selection
        self.metric_label = QLabel("Select Metric:")
        layout.addWidget(self.metric_label)

        self.metric_dropdown = QComboBox()
        self.metric_dropdown.addItems(["Fantasy Score", "Points Per Game", "Assists", "Rebounds", "Efficiency"])
        self.metric_dropdown.currentIndexChanged.connect(self.update_plot)
        layout.addWidget(self.metric_dropdown)

        # Matplotlib figure for comparison
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

    def setup_projections_tab(self):
        layout = QVBoxLayout(self.projections_tab)

        # Player Search
        search_layout = QHBoxLayout()
        self.projection_search_bar = QLineEdit()
        self.projection_search_bar.setPlaceholderText("Search Player for Projections...")
        self.projection_completer = QCompleter(self.player_names)
        self.projection_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.projection_search_bar.setCompleter(self.projection_completer)
        search_button = QPushButton("Search")
        search_button.clicked.connect(self.generate_projections)
        search_layout.addWidget(self.projection_search_bar)
        search_layout.addWidget(search_button)
        layout.addLayout(search_layout)

        # Label for displaying projections
        self.projection_label = QLabel("Projection Details will appear here.")
        layout.addWidget(self.projection_label)

        # Matplotlib figure for projections
        self.projection_figure = Figure()
        self.projection_canvas = FigureCanvas(self.projection_figure)
        layout.addWidget(self.projection_canvas)

    def search_player(self, player_num):
        """Search for the player and load their stats."""
        player_name = self.search_bar_1.text() if player_num == 1 else self.search_bar_2.text()
        matched_player = next((p for p in self.all_players if p['full_name'].lower() == player_name.lower()), None)

        if matched_player:
            if player_num == 1:
                self.current_player_1 = matched_player
                self.data_1 = self.load_player_data(matched_player)
            else:
                self.current_player_2 = matched_player
                self.data_2 = self.load_player_data(matched_player)
            self.update_plot()
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

    def load_player_data(self, player):
        """Load stats for the selected player."""
        player_id = player['id']
        career_stats = playercareerstats.PlayerCareerStats(player_id=player_id)
        df = career_stats.get_data_frames()[0]

        # Ensure TO column exists
        if 'TO' not in df.columns:
            df['TO'] = 0

        # Add fantasy score using user-defined settings
        df['Fantasy Score'] = (
            df['PTS'] * self.fantasy_settings['PTS'] +
            df['REB'] * self.fantasy_settings['REB'] +
            df['AST'] * self.fantasy_settings['AST'] +
            df['STL'] * self.fantasy_settings['STL'] +
            df['BLK'] * self.fantasy_settings['BLK'] -
            df['TO'] * self.fantasy_settings['TO']
        )
        df['Points Per Game'] = df['PTS'] / df['GP']
        df['Rebounds'] = df['REB'] / df['GP']
        df['Assists'] = df['AST'] / df['GP']
        df['Efficiency'] = (df['PTS'] + df['REB'] + df['AST']) / df['GP']

        return df[['SEASON_ID', 'Fantasy Score', 'Points Per Game', 'Assists', 'Rebounds', 'Efficiency']]

    def update_plot(self):
        """Update the plot based on selected metric."""
        if self.data_1 is None and self.data_2 is None:
            return

        # Clear the current figure
        self.figure.clear()

        # Get selected metric
        metric = self.metric_dropdown.currentText()

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

        self.canvas.draw()

    def generate_projections(self):
        """Generate per-game projections for the selected player."""
        player_name = self.projection_search_bar.text()
        matched_player = next((p for p in self.all_players if p['full_name'].lower() == player_name.lower()), None)

        if not matched_player:
            self.projection_label.setText("Player not found! Try again.")
            return

        player_id = matched_player['id']
        career_stats = playercareerstats.PlayerCareerStats(player_id=player_id)
        df = career_stats.get_data_frames()[0]

        # Ensure the TO column exists
        if 'TO' not in df.columns:
            df['TO'] = 0  # Assign 0 turnovers if the column is missing

        # Calculate per-game stats
        df['Points Per Game'] = df['PTS'] / df['GP']
        df['Rebounds Per Game'] = df['REB'] / df['GP']
        df['Assists Per Game'] = df['AST'] / df['GP']
        df['Fantasy Score Per Game'] = (
            df['Points Per Game'] * self.fantasy_settings['PTS'] +
            df['Rebounds Per Game'] * self.fantasy_settings['REB'] +
            df['Assists Per Game'] * self.fantasy_settings['AST'] +
            df['STL'] / df['GP'] * self.fantasy_settings['STL'] +
            df['BLK'] / df['GP'] * self.fantasy_settings['BLK'] -
            df['TO'] / df['GP'] * self.fantasy_settings['TO']
        )

        # Take projections as the most recent season's per-game stats
        latest_season = df.iloc[-1]
        projections = {
            "Points": latest_season['Points Per Game'],
            "Rebounds": latest_season['Rebounds Per Game'],
            "Assists": latest_season['Assists Per Game'],
            "Fantasy Score": latest_season['Fantasy Score Per Game']
        }

        # Update label and plot
        self.projection_label.setText(f"Projected Stats for Next Game:\n"
                                      f"Points: {projections['Points']:.1f}, "
                                      f"Rebounds: {projections['Rebounds']:.1f}, "
                                      f"Assists: {projections['Assists']:.1f}, "
                                      f"Fantasy Score: {projections['Fantasy Score']:.1f}")

        # Plot projections
        self.projection_figure.clear()
        ax = self.projection_figure.add_subplot(111)
        categories = list(projections.keys())
        values = list(projections.values())
        ax.bar(categories, values, color='skyblue')
        ax.set_title(f"Projections for {matched_player['full_name']}")
        self.projection_canvas.draw()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FantasyDashboard()
    window.show()
    sys.exit(app.exec())
