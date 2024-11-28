import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QComboBox
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import pandas as pd
from nba_api.stats.static import players
from nba_api.stats.endpoints import playercareerstats

class FantasyDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Fantasy Basketball Dashboard")
        self.setGeometry(100, 100, 800, 600)

        # Main container widget
        self.container = QWidget(self)
        self.setCentralWidget(self.container)
        self.layout = QVBoxLayout(self.container)

        # Dropdown to filter by metric
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

        # Load and preprocess data
        self.data = self.load_data()
        self.update_plot()

    def load_data(self):
        # Example: Fetch data using nba_api and preprocess
        all_players = players.get_players()
        example_player = next(player for player in all_players if player['full_name'] == "LeBron James")
        career = playercareerstats.PlayerCareerStats(player_id=example_player['id'])
        df = career.get_data_frames()[0]

        # Example preprocessing: Create a subset with key metrics
        df['Points Per Game'] = df['PTS'] / df['GP']
        df['Assists'] = df['AST'] / df['GP']
        df['Rebounds'] = df['REB'] / df['GP']
        df['Efficiency'] = (df['PTS'] + df['REB'] + df['AST']) / df['GP']

        return df[['SEASON_ID', 'Points Per Game', 'Assists', 'Rebounds', 'Efficiency']]

    def update_plot(self):
        # Clear the current figure
        self.figure.clear()

        # Get selected metric
        metric = self.metric_dropdown.currentText()

        # Plot the selected metric
        ax = self.figure.add_subplot(111)
        ax.plot(self.data['SEASON_ID'], self.data[metric], marker='o')
        ax.set_title(f"{metric} Over Seasons")
        ax.set_xlabel("Season")
        ax.set_ylabel(metric)

        # Redraw the canvas
        self.canvas.draw()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FantasyDashboard()
    window.show()
    sys.exit(app.exec())
