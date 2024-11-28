import json
import time
from nba_api.stats.static import players
from nba_api.stats.endpoints import commonplayerinfo

def fetch_all_player_positions():
    all_players = players.get_active_players()
    player_data = []

    for player in all_players:
        player_id = player['id']
        try:
            info = commonplayerinfo.CommonPlayerInfo(player_id=player_id)
            position = info.get_normalized_dict()['CommonPlayerInfo'][0]['POSITION']
            player_data.append({
                'id': player_id,
                'name': player['full_name'],
                'position': position
            })
            print(player_data)
        except Exception as e:
            print(f"Error fetching data for {player['full_name']}: {e}")
        time.sleep(0.6)  # Avoid hitting rate limits

    # Save to JSON or CSV
    with open('player_positions.json', 'w') as f:
        json.dump(player_data, f)

if __name__ == "__main__":
    fetch_all_player_positions()
