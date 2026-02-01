import csv
import json
from typing import Dict,List,Optional,Set
from ..datamodel.player import Player, ChampionPerformance
from ..datamodel.champion import Champion
from ..datamodel.team import Team
from .playermanager import PlayerManager
from .teammanager import TeamManager
from .championmanager import ChampionManager

class MainManager:
    def __init__(self):
        self.player_manager = PlayerManager()
        self.team_manager = TeamManager()
        self.champion_manager = ChampionManager()

    def load_data(self, player_csv: str, team_csv: str, champion_csv: str):
        self.team_manager.load_from_csv(team_csv)
        self.champion_manager.load_from_csv(champion_csv)
        self.player_manager.load_from_csv(player_csv, self.champion_manager.get_registry(),self.team_manager.get_registry())

    def get_player_data(self, player_name: str) -> Optional[Player]:
        return self.player_manager.get_player(player_name)

    def get_team_data(self, team_name: str) -> Optional[Team]:
        return self.team_manager.get_team(team_name)

    def get_champion_data(self, champion_name: str) -> Optional[Champion]:
        return self.champion_manager.dump_specific_champ_info(champion_name)



