import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QComboBox, QLineEdit,
    QPushButton, QHBoxLayout, QCompleter, QTabWidget, QListWidget, QFormLayout, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QColor, QPalette
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import time
import json
import pandas as pd
from requests.exceptions import ReadTimeout
from nba_api.stats.static import players
from nba_api.stats.endpoints import playercareerstats, commonplayerinfo

class StyledQLabel(QLabel):
    """Custom label with improved styling"""
    def __init__(self, text, font_size=12, bold=False, color='#333'):
        super().__init__(text)
        font = QFont('Arial', font_size)
        if bold:
            font.setBold(True)
        self.setFont(font)
        self.setStyleSheet(f"color: {color};")

class StyledQPushButton(QPushButton):
    """Custom button with modern styling"""
    def __init__(self, text):
        super().__init__(text)
        self.setStyleSheet("""
            QPushButton {
                background-color: #2C3E50;
                color: white;
                border-radius: 5px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #34495E;
            }
            QPushButton:pressed {
                background-color: #2980B9;
            }
        """)
        # Add subtle shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor("#888888"))
        shadow.setOffset(3, 3)
        self.setGraphicsEffect(shadow)


class FantasyDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        # Set up modern color palette
        self.setStyleSheet("""
            QMainWindow {
                background-color: #ECF0F1;
            }
            QTabWidget::pane {
                background-color: white;
                border-radius: 10px;
            }
            QTabBar::tab {
                background-color: #3498DB;
                color: white;
                padding: 10px;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
            QTabBar::tab:selected {
                background-color: #2980B9;
            }
            QLineEdit, QComboBox {
                padding: 6px;
                border: 1px solid #BDC3C7;
                border-radius: 5px;
            }
        """)

        # Rest of the initialization remains the same as in the original code
        self.setWindowTitle("Fantasy Basketball Dashboard")
        self.setGeometry(100, 100, 1400, 900)

        # Matplotlib style
        plt.style.use('bmh')
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
        self.all_players = players.get_active_players()
        # Tab widget for switching pages
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Create tabs
        self.create_player_stats_tab()
        self.create_position_filter_tab()
        self.create_settings_tab()

    def create_settings_tab(self):
        """Create the Settings tab with improved styling"""
        settings_widget = QWidget()
        layout = QVBoxLayout(settings_widget)
        layout.setSpacing(15)

        # Title for settings
        title = StyledQLabel("Fantasy Points Settings", font_size=16, bold=True, color='#2C3E50')
        layout.addWidget(title)

        # Form layout for fantasy point settings
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form_layout.setFormAlignment(Qt.AlignmentFlag.AlignCenter)
        form_layout.setSpacing(10)

        stats = [
            ('PTS', "Points"),
            ('REB', "Rebounds"),
            ('AST', "Assists"),
            ('STL', "Steals"),
            ('BLK', "Blocks"),
            ('TO', "Turnovers")
        ]

        self.stat_inputs = {}
        for stat_key, stat_name in stats:
            label = StyledQLabel(f"{stat_name} Fantasy Points:", font_size=12, color='#2C3E50')
            input_field = QLineEdit(str(self.fantasy_settings[stat_key]))
            input_field.setStyleSheet("width: 100px;")
            form_layout.addRow(label, input_field)
            self.stat_inputs[stat_key] = input_field

        layout.addLayout(form_layout)

        # Save Button with improved styling
        save_button = StyledQPushButton("Save Settings")
        save_button.clicked.connect(self.save_settings)
        layout.addWidget(save_button)

        self.tabs.addTab(settings_widget, "Settings")

    def save_settings(self):
        """Save the custom fantasy points settings."""
        try:
            for stat_key in self.fantasy_settings.keys():
                self.fantasy_settings[stat_key] = float(self.stat_inputs[stat_key].text())
            print("Settings saved successfully.")
        except ValueError:
            print("Invalid input. Please enter numeric values.")

    def create_player_stats_tab(self):
        """Create the Player Stats tab."""
        player_stats_widget = QWidget()
        layout = QVBoxLayout(player_stats_widget)

        # Player Stats Tab
        self.player_stats_tab = QWidget()
        self.setup_player_stats_tab()
        self.tabs.addTab(self.player_stats_tab, "Compare Players")

        # Projections Tab
        self.projections_tab = QWidget()
        self.setup_projections_tab()
        self.tabs.addTab(self.projections_tab, "Per-Game Projections")

    def setup_player_stats_tab(self):
        """Enhanced player stats tab with better layout, styling, and autocomplete"""
        layout = QVBoxLayout(self.player_stats_tab)
        layout.setSpacing(15)

        # Title for the comparison section
        title = StyledQLabel("Player Comparison", font_size=16, bold=True, color='#2C3E50')
        layout.addWidget(title)

        # Search section with improved layout
        search_container = QWidget()
        search_layout = QHBoxLayout(search_container)
        
        # Player 1 search with autocomplete
        player1_section = QVBoxLayout()
        player1_section.addWidget(StyledQLabel("Player 1", bold=True))
        self.search_bar_1 = QLineEdit()
        self.search_bar_1.setPlaceholderText("Search Player 1...")
        
        # Add autocomplete for player 1
        player1_completer = QCompleter(self.player_names)
        player1_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.search_bar_1.setCompleter(player1_completer)
        
        player1_section.addWidget(self.search_bar_1)
        search_layout.addLayout(player1_section)

        # Player 2 search with autocomplete
        player2_section = QVBoxLayout()
        player2_section.addWidget(StyledQLabel("Player 2", bold=True))
        self.search_bar_2 = QLineEdit()
        self.search_bar_2.setPlaceholderText("Search Player 2...")
        
        # Add autocomplete for player 2
        player2_completer = QCompleter(self.player_names)
        player2_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.search_bar_2.setCompleter(player2_completer)
        
        player2_section.addWidget(self.search_bar_2)
        search_layout.addLayout(player2_section)

        layout.addWidget(search_container)

        # Dropdowns section
        dropdown_container = QHBoxLayout()
        
        metric_section = QVBoxLayout()
        metric_section.addWidget(StyledQLabel("Select Metric", bold=True))
        self.metric_dropdown = QComboBox()
        self.metric_dropdown.addItems(["Fantasy Score", "Points Per Game", "Assists", "Rebounds", "Efficiency", "Steals", "Blocks"])
        metric_section.addWidget(self.metric_dropdown)
        dropdown_container.addLayout(metric_section)

        normalization_section = QVBoxLayout()
        normalization_section.addWidget(StyledQLabel("Normalize Data By", bold=True))
        self.normalization_dropdown = QComboBox()
        self.normalization_dropdown.addItems(["Season Year", "Career Year"])
        normalization_section.addWidget(self.normalization_dropdown)
        dropdown_container.addLayout(normalization_section)

        layout.addLayout(dropdown_container)

        # Matplotlib figure for comparison with better styling
        plt.style.use('seaborn-v0_8-whitegrid')
        self.figure = Figure(figsize=(10, 6), dpi=100, facecolor='#ECF0F1')
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        # Connect dropdowns to update function
        self.metric_dropdown.currentIndexChanged.connect(self.update_plot)
        self.normalization_dropdown.currentIndexChanged.connect(self.update_plot)

        # Search buttons
        search_buttons_layout = QHBoxLayout()
        search_button_1 = StyledQPushButton("Search Player 1")
        search_button_1.clicked.connect(lambda: self.search_player(1))
        search_buttons_layout.addWidget(search_button_1)

        search_button_2 = StyledQPushButton("Search Player 2")
        search_button_2.clicked.connect(lambda: self.search_player(2))
        search_buttons_layout.addWidget(search_button_2)

        layout.addLayout(search_buttons_layout)

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
        """Create the Position Filtering tab with player navigation."""
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
        self.player_list_widget.itemDoubleClicked.connect(self.navigate_to_player_stats)
        layout.addWidget(self.player_list_widget)

        # Load all players initially
        self.load_all_players()

        # Add this tab to the main widget
        self.tabs.addTab(position_filter_widget, "Position Filter")

    def navigate_to_player_stats(self, item):
        """Navigate to the Compare Players tab and search for the selected player."""
        # Switch to the Compare Players tab (index 1 in the current setup)
        self.tabs.setCurrentIndex(0)
        
        # Fill the first search bar with the selected player's name
        self.search_bar_1.setText(item.text())
        
        # Trigger the search for the player
        self.search_player(1)


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
        df['Steals'] = df['STL'] / df['GP']
        df['Blocks'] = df['BLK'] / df['GP']


        return df[['SEASON_ID', 'Fantasy Score', 'Points Per Game', 'Assists', 'Rebounds', 'Efficiency', 'Steals', 'Blocks']]

    def update_plot(self):
        """Update the plot based on selected metric."""
        if self.data_1 is None and self.data_2 is None:
            return

        # Clear the current figure
        self.figure.clear()

        # Get selected metric
        metric = self.metric_dropdown.currentText()
        
        # Get normalization choice
        normalize_by = self.normalization_dropdown.currentText()

        # Create a combined dataframe with both players' data
        combined_df = pd.DataFrame()

        # Normalize player data based on the selected normalization choice
        if normalize_by == "Career Year":
            def normalize_by_career_year(df):
                df['Career Year'] = df['SEASON_ID'].index + 1
                return df

            if self.data_1 is not None:
                self.data_1 = normalize_by_career_year(self.data_1)
                self.data_1['Player'] = self.current_player_1['full_name']
                combined_df = pd.concat([combined_df, self.data_1[['Career Year', metric, 'Player']]])

            if self.data_2 is not None:
                self.data_2 = normalize_by_career_year(self.data_2)
                self.data_2['Player'] = self.current_player_2['full_name']
                combined_df = pd.concat([combined_df, self.data_2[['Career Year', metric, 'Player']]])

            x_axis_label = "Career Year"
        else:
            if self.data_1 is not None:
                self.data_1['Player'] = self.current_player_1['full_name']
                combined_df = pd.concat([combined_df, self.data_1[['SEASON_ID', metric, 'Player']]])

            if self.data_2 is not None:
                self.data_2['Player'] = self.current_player_2['full_name']
                combined_df = pd.concat([combined_df, self.data_2[['SEASON_ID', metric, 'Player']]])

            x_axis_label = "Season"

        # Sort the dataframe by SEASON_ID or Career Year to align the seasons properly
        combined_df = combined_df.sort_values(by='SEASON_ID' if normalize_by == "Season Year" else 'Career Year')

        # Plot the data
        ax = self.figure.add_subplot(111)
        for player_name in combined_df['Player'].unique():
            player_data = combined_df[combined_df['Player'] == player_name]
            ax.plot(
                player_data['SEASON_ID' if normalize_by == "Season Year" else 'Career Year'],
                player_data[metric],
                marker='o' if player_name == self.current_player_1['full_name'] else 'x',
                label=player_name
            )

        # Update plot aesthetics
        ax.set_title(f"{metric} Over {x_axis_label}")
        ax.set_xlabel(x_axis_label)
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
