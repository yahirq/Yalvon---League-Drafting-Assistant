#create player data model, holds info for champs played (this will contain a champion object)
#acts as data that can be interfaced with, allowing for displaying player information
from typing import Dict, List, Optional, TYPE_CHECKING
from .champion import Champion
if TYPE_CHECKING:
    from .team import Team

class Player:
    def __init__(self, name: str):
        self.name = name
        self.team: Team = None
        self.role = None

        self.champs_played: dict[str, ChampionPerformance] = {}
     
        self.total_games: int = 0
        self.total_wins: int = 0
        self.total_kills: int = 0 
        self.total_deaths: int = 0 
        self.total_assists: int = 0
    
    def add_champion_perfomance(self, champion: Champion, games: int, wins:int, kills:int=0, deaths:int=0, assists:int=0, creepscore:int=0):
        if champion.name in self.champs_played:
            perf = self.champs_played[champion.name]
            perf.games += games
            perf.wins += wins
            perf.kills += kills
            perf.deaths += deaths
            perf.assists += assists
            perf.creepscore += creepscore
        else:
            self.champs_played[champion.name] = ChampionPerformance(
                champion=champion,
                games=games,
                wins=wins,
                kills=kills,
                deaths=deaths,
                assists=assists,
                creepscore=creepscore
            )
        self.total_games += games
        self.total_wins += wins
        self.total_kills += kills
        self.total_deaths += deaths
        self.total_assists += assists
    
    @property
    def individual_overall_winrate(self) -> float:
        if self.total_games == 0:
            return 0.0
        return (self.total_wins / self.total_games) * 100
    
    @property
    def kda_ratio(self) -> float:
        if self.total_games == 0:
            return 0.0
        return (self.total_kills + self.total_assists) / max(1,self.total_deaths)
    
    @property
    def avg_kills(self) -> float:
        if self.total_games == 0:
            return 0.0
        return self.total_kills / self.total_games
    
    @property
    def avg_deaths(self) -> float:
        if self.total_games == 0:
            return 0.0
        return self.total_deaths / self.total_games
    
    @property
    def avg_assists(self) -> float:
        if self.total_games == 0:
            return 0.0
        return self.total_assists / self.total_games
    
    def get_winrate_on_champ(self, champion_name:str) -> float:
        if champion_name in self.champs_played:
            perf = self.champs_played[champion_name]
            if perf.games == 0:
                return 0.0
            return(perf.wins/perf.games)*100
        return 0.0
    
    def get_kda_on_champ(self, champion_name:str) -> float:
        if champion_name in self.champs_played:
            perf = self.champs_played[champion_name]
            if perf.deaths == 0:
                return perf.kills + perf.assists
            return (perf.kills + perf.assists) / perf.deaths
        return 0.0
    
    def get_games_on_champ(self,champion_name:str) -> int:
        if champion_name in self.champs_played:
            perf = self.champs_played[champion_name]
            return perf.games
        return 0
    
    def get_top_champions(self,limit:int = 5) ->List[tuple]:
        champions = []
        for champ_name, perf in self.champs_played.items():
            champions.append((champ_name, perf.games, perf.winrate))
            
        champions.sort(key=lambda x: x[1], reverse=True)
        return champions[:limit]
        
    
    def to_dict(self):
        return {
            'name': self.name,
            'role': self.role,
            'team': self.team.name if self.team else None,
            'total_games': self.total_games,
            'total_wins': self.total_wins,
            'individual_overall_winrate': self.individual_overall_winrate,
            'total_kills': self.total_kills,
            'total_deaths': self.total_deaths,
            'total_assists': self.total_assists,
            'kda_ratio': self.kda_ratio,
            'avg_kills': self.avg_kills,
            'avg_deaths': self.avg_deaths,
            'avg_assists': self.avg_assists,
            'champs_played': {champ_name: perf.to_dict() for champ_name, perf in self.champs_played.items()}
        }
    

#stores data for player performance on specific champions         
class ChampionPerformance:
    def __init__(self, champion: Champion, games: int, wins:int, kills:int=0, deaths:int=0, assists:int=0, creepscore:int=0):
        self.champion: Champion = champion
        self.games: int = games
        self.wins: int = wins
        self.kills: int = kills
        self.deaths: int = deaths
        self.assists: int = assists
        self.creepscore: int = creepscore
    
    @property
    def winrate(self) -> float:
        if self.games == 0:
            return 0.0
        return self.wins / self.games * 100
    
    @property
    def avg_cs(self) -> float:
        return self.creepscore / self.games
    
    @property
    def kda_ratio(self) -> float:
        if self.deaths == 0:
            return float('inf')
        return (self.kills + self.assists) / self.deaths
    
    @property
    def average_kills(self) -> float:
        if self.games == 0:
            return 0.0
        return self.kills / self.games
    
    @property
    def average_deaths(self) -> float:
        if self.games == 0:
            return 0.0
        return self.deaths / self.games
    
    @property
    def average_assists(self) -> float:
        if self.games == 0:
            return 0.0
        return self.assists / self.games
    
    def to_dict(self):
        return {
            'champion': self.champion.to_dict(),
            'games': self.games,
            'wins': self.wins,
            'winrate': self.winrate,
            'kills': self.kills,
            'deaths': self.deaths,
            'assists': self.assists,
            'kda_ratio': self.kda_ratio,
            'average_kills': self.average_kills,
            'average_deaths': self.average_deaths,
            'average_assists': self.average_assists
        }