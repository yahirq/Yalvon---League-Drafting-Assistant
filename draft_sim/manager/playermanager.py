import csv
import json
from typing import Dict,List,Optional,Set
from ..datamodel.player import Player, ChampionPerformance
from ..datamodel.champion import Champion
from ..datamodel.team import Team

#handles initialization and management of player data
#loads from csv files

#need to implement haroon's requirements for his scouting report, update values that need to be parsed and add them to either the player, team or champion data models


class PlayerManager:
    def __init__(self):
        self.players: Dict[str, Player] = {}
        self.players_by_team: Dict[str, List[Player]] = {}
        self.team_recent_rosters: Dict[str, List[str]] = {}
    
    def load_from_csv(self,csv_path: str, champion_registry: Dict[str, Champion], team_registry: Dict[str, Team] = None):
        
        with open(csv_path, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            player_team_map = {}
            latest_match_date = {}
            match_counter = 0
            
            for row in reader:
                try:
                    player_name = row['Player'].strip()
                    champion_played = row['Champ'].strip()
                    team_name = row['Teams'].strip()
                    current_date = row['Date'].strip()
                    
                    won = row["Won"].strip()
                    
                    def safe_int(val, default=0):
                        try:
                            return int(float(val)) if val else default
                        except:
                            return default
                    
                    def safe_float(val, default=0.0):
                        try:
                            return float(val) if val else default
                        except:
                            return default
                        

                    creepscore = safe_int(row.get("CreepScore"))
                    kills = safe_int(row.get("Kills"))
                    deaths = safe_int(row.get("Deaths"))
                    assists = safe_int(row.get("Assists"))

                    if team_name:
                        player_team_map[player_name] = team_name
                    
                    if player_name not in self.players:
                        player = Player(player_name)
                        self.players[player_name] = player
                        
                    player = self.players[player_name]
                    
                    champion = None
                    if champion_played in champion_registry:
                        champion = champion_registry[champion_played]
                    else:
                        print(f"Champion not found: {champion_played} in registry")
                        continue
                    
                    #add the data to the champion performance record of the player
                    #more stats can be added if required, parse and then update accordingly here
                    if champion_played not in player.champs_played:
                        player.champs_played[champion_played] = ChampionPerformance(
                            champion=champion,
                            games=0,
                            wins=0,
                            kills=0,
                            deaths=0,
                            assists=0,
                            creepscore=0
                        )
                       
                    player.add_champion_perfomance(
                        champion=champion,
                        games=1,
                        wins=1 if won.lower() == 'true' else 0,
                        kills=kills,
                        deaths=deaths,
                        assists=assists,
                        creepscore=creepscore
                    )

                    match_counter += 1
                    
                    
                except KeyError as e:
                    print(f"Error: missing column - {e}")
                except ValueError as e:
                    print(f"Error: invalid data - {e}")
                except Exception as e:
                    print(f"Error processing row - {e}")
                    import traceback
                    traceback.print_exc()

            print("Attempted assignment of players to teams")
            self._assign_players_to_teams(player_team_map, team_registry)

            self._build_indexes()
            
            print(f"Processed {match_counter} matches")

    def _assign_players_to_teams(self, player_team_map: Dict[str, str], team_registry: Optional[Dict[str, Team]]):
        if not team_registry:
            print("Failed to assign players to team, ensure team registry is valid")
            return
        
        for player_name, team_name in player_team_map.items():
            if player_name in self.players and team_name in team_registry:
                player = self.players[player_name]
                team = team_registry[team_name]
                
                player.team = team
                
                team.add_player(self.players[player_name])
            for team in team_registry.values():
                team.recompute_from_players()
                
    def _build_indexes(self):
        self.players_by_team.clear()
        
        for player in self.players.values():
            if player.team and player.team.name:
                team_name = player.team.name
                if team_name not in self.players_by_team:
                    self.players_by_team[team_name] = []
                self.players_by_team[team_name].append(player)
    
    def get_player(self, name: str) -> Optional[Player]:
        return self.players.get(name)
    
    def get_players_by_team(self, team_name: str) -> List[Player]:
        return self.players_by_team.get(team_name, [])
    
    def get_top_players_by_stat(self, stat: str, limit: int = 10) -> List[tuple]:
        players_with_stats = []
        
        for player in self.players.values():
            if stat == 'total_games':
                value = player.total_games
            elif stat == 'total_wins':
                value = player.total_wins
            elif stat == 'total_kills':
                value = player.total_kills
            elif stat == 'total_deaths':
                value = player.total_deaths
            elif stat == 'total_assists':
                value = player.total_assists
            else:
                continue
            
            if player.total_games >= 5:  # Minimum games threshold
                players_with_stats.append((player, value))
        
        # Sort by stat value (descending)
        players_with_stats.sort(key=lambda x: x[1], reverse=True)
        return [(player, value) for player, value in players_with_stats[:limit]]
    
    def get_players_who_play_champion(self, champion_name: str, min_games: int = 3) -> List[tuple]:
        results = []
        
        for player in self.players.values():
            if champion_name in player.champs_played:
                perf = player.champs_played[champion_name]
                if perf.games >= min_games:
                    results.append((
                        player.name,
                        perf.winrate,
                        perf.games,
                        perf.kda_ratio
                    ))
        
        # Sort by winrate (descending)
        results.sort(key=lambda x: x[1], reverse=True)
        return results
