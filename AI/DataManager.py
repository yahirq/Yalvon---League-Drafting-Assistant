# Python
from typing import Iterable, Optional, List
import pandas as pd

class DataManager:
    def __init__(self, csv_path: str = ""):
        try:
            print("[AI DataManager] Loading historical data from CSV...")

            meta_cols = ['Date', 'Teams', 'Opponent', 'Side', 'Won']
            ban_cols = [f'Ban{i}' for i in range(1, 10)]
            pick_cols = [f'Pick{i}' for i in range(1, 10)]

            # All relevant columns for the model
            all_target_cols = meta_cols + ban_cols + pick_cols

            # Read only relevant columns
            self.df = pd.read_csv(csv_path, usecols=lambda x: x in all_target_cols)

            # Clean NA rows
            self.df = self.df.dropna(subset=all_target_cols)

            # Sort by Date (newest first)
            if 'Date' in self.df.columns:
                self.df['Date'] = pd.to_datetime(self.df['Date'], format="ISO8601")
                self.df = self.df.sort_values(by='Date', ascending=False)

            # Drop the date column since we don't need it
            self.df.drop(columns=['Date'], inplace=True)

            # Save a copy of the full dataframe if a subset is needed
            self.df_limited = self.df

            print(f"[AI DataManager] CSV Success! Rows: {len(self.df)} | String Length: {len(self.df_limited.to_csv(index=False))}")

        except Exception as e:
            print(f"Error loading data: {e}")
            self.df = None

    def limit_games(self, max_games: int = 1500):
        if self.df is not None:
            self.df_limited = self.df.head(max_games)

    # Return a model-friendly text representation of the dataframe.
    def get_context(self) -> str:
        # Convert to CSV (it's kind of misleading but it's just a string basically)
        # Also to_csv saves on tokens compared to to_string
        return self.df_limited.to_csv(index=False)

        
