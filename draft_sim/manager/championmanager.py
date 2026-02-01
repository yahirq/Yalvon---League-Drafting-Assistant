import csv
import json
from typing import Dict,List,Optional,Set
from ..datamodel.player import Player, ChampionPerformance
from ..datamodel.champion import Champion
from ..datamodel.team import Team

#create the registry
class ChampionManager:
    def __init__(self):
        self.champions: Dict[str, Champion] = {}

    def load_from_csv(self, csv_path: str):
        with open(csv_path, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                try:
                    champion_name = row['Champ'].strip()
                    if champion_name not in self.champions:
                        self.champions[champion_name] = Champion(name=champion_name)
                        print(f"Loaded new champion: {champion_name}")
                        
                    if champion_name in self.champions:
                        champion = self.champions[champion_name]
                        champion.total_games += 1
                        champion.total_wins += 1 if row['Won'].strip().lower() == 'true' else 0
                        

                except KeyError as e:
                    print(f"Error: missing column - {e}")
                except ValueError as e:
                    print(f"Error: invalid data - {e}")
                except Exception as e:
                    print(f"Error processing row - {e}")

    def get_registry(self) -> Dict[str, Champion]:
        return self.champions

    def dump_champ_info(self) -> None:
        for champion in self.champions.values():
            print(f"Champion: {champion.name}, Total Games: {champion.total_games}, Total Wins: {champion.total_wins}")

    def dump_specific_champ_info(self, champion_name: str) -> None:
        champion = self.get_champion(champion_name)
        if champion:
            print(f"Champion: {champion.name}, Total Games: {champion.total_games}, Total Wins: {champion.total_wins}")
        else:
            print(f"Champion '{champion_name}' not found.")

    #return the top most picked champions, default to 1
    def get_most_picked_champ(self, limit: int = 1) -> List[tuple]:
        champions = []
        for champ in self.champions.values():
            champions.append((champ.name, champ.total_games))
        
        champions.sort(key=lambda x: x[1], reverse=True)
        return champions[:limit]
    
    def get_highest_winrate_champ(self, limit: int = 1) -> List[tuple]:
        champions = []
        for champ in self.champions.values():
            champions.append((champ.name, champ.overall_winrate))
        
        champions.sort(key=lambda x: x[1], reverse=True)
        return champions[:limit]
    
    
    def get_champion(self, champion_name: str) -> Optional[Champion]:
        return self.champions.get(champion_name)
