from typing import Dict, Optional, List, TYPE_CHECKING
if TYPE_CHECKING:
    from .player import Player


#serves as a container for team data, allows for ease of access and manipulation for use in integration with ui
class Team:
    def __init__(self, name):
        self.name = name
        self.logo_path = None
        self.players: List["Player"] = []
        self.total_entries = 0
        self.total_win_entries = 0
        self.total_bside_entries = 0
        self.total_rside_entries = 0
        self.total_bside_win_entries = 0
        self.total_rside_win_entries = 0
        
        self.first_bloods = 0
        self.total_kills = 0
        self.total_deaths = 0
        self.total_assists = 0

        self.champion_stats: Dict[str, TeamChampionPerformance] = {}
    #maybe add something similar to add_champion_performance here?
    #dont know the nature of which @property updates
    
    @property
    def team_kda_ratio(self) -> float:
        return (self.total_kills + self.total_assists) / max(1,self.total_deaths)
    
    @property
    def total_blueside_games(self) -> int:
        return(self.total_bside_entries/5)
    
    @property
    def total_redside_games(self) -> int:
        return(self.total_rside_entries/5)
    
    @property
    def redside_winrate(self) -> float:
        return(self.total_rside_win_entries/self.total_rside_entries)*100
    
    @property
    def blueside_winrate(self) -> float:
        return(self.total_bside_win_entries/self.total_bside_entries)*100
    
    @property
    def total_games(self) -> int:
        return int(self.total_entries/5)
    
    @property
    def total_wins(self) -> int:
        return int(self.total_win_entries/5)
        
    def add_player(self, player):
        self.players.append(player)

    def to_dict(self): #dictionary converter for the data
        return {
            'name': self.name,
            'logo_path': self.logo_path,
            'players': [player.to_dict() for player in self.players],
            'total_games': self.total_games,
            'total_wins': self.total_wins,
            'total_kills': self.total_kills,
            'total_deaths': self.total_deaths,
            'total_assists': self.total_assists,
            'champion_stats': {k: v.to_dict() for k, v in self.champion_stats.items()},
        }
    #add champion performance given team 
    def add_champion_performance(
        self,
        champion_name: str,
        games: int,
        wins: int,
        kills: int = 0,
        deaths: int = 0,
        assists: int = 0,
        creepscore: int = 0,
    ) -> None:
        
        if champion_name not in self.champion_stats:
            self.champion_stats[champion_name] = TeamChampionPerformance(champion_name)

        perf = self.champion_stats[champion_name]
        perf.games += int(games)
        perf.wins += int(wins)
        perf.kills += int(kills)
        perf.deaths += int(deaths)
        perf.assists += int(assists)
        perf.creepscore += int(creepscore)

    #rebuild team stats from players on team
    def recompute_from_players(self) -> None:
        self.champion_stats.clear()

        for p in self.players:
            # p.champs_played: dict[str, ChampionPerformance]
            for champ_name, pperf in p.champs_played.items():
                self.add_champion_performance(
                    champion_name=champ_name,
                    games=pperf.games,
                    wins=pperf.wins,
                    kills=pperf.kills,
                    deaths=pperf.deaths,
                    assists=pperf.assists,
                    creepscore=pperf.creepscore,
                )
    
    def get_team_winrate_on_champion(self, champion_name: str) -> float:
        perf = self.champion_stats.get(champion_name)
        return perf.winrate if perf else 0.0

    def get_team_games_on_champion(self, champion_name: str) -> int:
        perf = self.champion_stats.get(champion_name)
        return perf.games if perf else 0

    def get_team_kda_on_champion(self, champion_name: str) -> float:
        perf = self.champion_stats.get(champion_name)
        return perf.kda_ratio if perf else 0.0

    def get_top_champions(
        self,
        limit: int = 5,
        min_games: int = 1,
        sort_by: str = "games",  # 'games' | 'winrate' | 'kda'
        descending: bool = True,
    ) -> List[tuple]:
        rows = []
        for cname, perf in self.champion_stats.items():
            if perf.games >= max(0, min_games):
                rows.append((cname, perf.games, perf.winrate, perf.kda_ratio))

        key_fn = {
            "games": lambda r: r[1],
            "winrate": lambda r: r[2],
            "kda": lambda r: float("inf") if r[3] == float("inf") else r[3],
        }.get(sort_by, lambda r: r[1])

        rows.sort(key=key_fn, reverse=descending)
        return rows[:limit]

# Aggregated performance for a team on a specific champion
class TeamChampionPerformance:
    def __init__(self, champion_name: str):
        self.champion_name: str = champion_name
        self.games: int = 0
        self.wins: int = 0
        self.kills: int = 0
        self.deaths: int = 0
        self.assists: int = 0
        self.creepscore: int = 0

    @property
    def winrate(self) -> float:
        if self.games == 0:
            return 0.0
        return (self.wins / self.games) * 100.0

    @property
    def kda_ratio(self) -> float:
        # team-level KDA on this champ across all occurrences
        if self.deaths == 0:
            # Avoid division by zero; treat as kills+assists (infinite practical KDA)
            return float('inf') if (self.kills + self.assists) > 0 else 0.0
        return (self.kills + self.assists) / self.deaths

    @property
    def avg_cs(self) -> float:
        if self.games == 0:
            return 0.0
        return self.creepscore / self.games

    def to_dict(self) -> dict:
        return {
            "champion_name": self.champion_name,
            "games": self.games,
            "wins": self.wins,
            "winrate": self.winrate,
            "kills": self.kills,
            "deaths": self.deaths,
            "assists": self.assists,
            "kda_ratio": self.kda_ratio,
            "avg_cs": self.avg_cs
        }

