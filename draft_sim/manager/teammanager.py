import csv
import json
from typing import Dict,List,Optional,Set
from ..datamodel.player import Player, ChampionPerformance
from ..datamodel.champion import Champion
from ..datamodel.team import Team

class TeamManager:
    def __init__(self):
        self.teams: Dict[str, Team] = {}

    def load_from_csv(self, csv_path: str):
        with open(csv_path, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                team_name = row['Teams']
                side = row['Side']
                player_death = row['Deaths']
                player_kills = row["Kills"]
                player_assists = row["Assists"]
                win = 1 if row['Won'].strip().lower() == 'true' else 0
                
                if team_name not in self.teams:
                    self.teams[team_name] = Team(name=team_name)
                
                if team_name in self.teams:
                    team = self.teams[team_name]
                    team.total_entries += 1
                    team.total_kills += int(player_kills)
                    team.total_deaths += int(player_death)
                    team.total_assists += int(player_assists)
                    team.total_win_entries += win
                    if side == "red":
                        team.total_rside_entries += 1
                        team.total_rside_win_entries += win
                    else:
                        team.total_bside_entries += 1
                        team.total_bside_win_entries += win

    def dump_team_info(self) -> None:
        for team in self.teams.values():
            print(f"Team: {team.name}, Total Games: {team.total_games}, Total Wins: {team.total_wins}, Total Kills: {team.total_kills}, Total Deaths: {team.total_deaths}, Total Assists: {team.total_assists}")
    
    def get_players_on_team(self, team_name: str) -> List[Player]:
        if team_name in self.teams:
            return self.teams[team_name].players
        return []
    
    def get_team(self, team_name: str) -> Optional[Team]:
        return self.teams.get(team_name)
    
    def get_registry(self) -> Optional[Team]:
        return self.teams
