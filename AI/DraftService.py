from typing import List, Optional, Tuple
from pydantic import BaseModel, ValidationError

from AI.GeminiManager import GeminiManager

# Individual champion recommendations
class DraftPick(BaseModel):
    champion_name: str
    reasoning: str
    confidence_score: float
    possible_synergies: List[str]
    possible_counters: List[str]

class DraftPredict(BaseModel):
    predicted_next_champ: str
    reasoning: str
    confidence_score: float

# A list of champion recommendations
class RecommendationResponse(BaseModel):
    recommendations: List[DraftPick]
    predictions: List[DraftPredict]
    strategic_summary: str # A summary of why these N picks were chosen

# Stateless draft helper that builds up a prompt and sends updates. There is NO chat/session. Every call must include the context.
class DraftService:
    def __init__(self, manager: GeminiManager):
        self.gm = manager
        self.prompt = ""

        # Context fields
        self.blue_team = ""
        self.red_team = ""
        self.home_side = "unset" # Either "blue" or "red" or "unset"
        self.current_turn = ""
        self.turn_counter = 0
        self.blue_bans: List[str] = []
        self.red_bans: List[str] = []
        self.blue_picks: List[str] = []
        self.red_picks: List[str] = []

        # Current draft state
        self.context: List[str] = []
        # loldatafull.csv context
        self.data_context: str = ""

    # Updates the prompt
    def update_prompt(self, prompt: str):
        print("[AI DraftService] Updated prompt.")
        self.prompt = prompt

    # Updates the data context (data from a CSV file)
    def set_data_context(self, data_text: str):
        print("[AI DraftService] Replaced data context.")
        self.data_context = (data_text or "").strip()

    # Return (suggest_side, predict_side, friendly_team, opponent_team) based on home_side.
    def sides(self) -> Tuple[str, str, str, str]:

        hs = str(self.home_side).strip().lower()

        if hs == "blue":
            return "blue", "red", self.blue_team, self.red_team
        if hs == "red":
            return "red", "blue", self.red_team, self.blue_team

        # Fallback: if unset, follow current_turn when suggesting
        ct = str(self.current_turn).strip().lower()
        if ct == "blue":
            return "blue", "red", self.blue_team, self.red_team
        if ct == "red":
            return "red", "blue", self.red_team, self.blue_team
        
        # Final fallback
        return "blue", "red", self.blue_team, self.red_team

    # Takes current draft state and updates the context fields
    def update_context(
            self,
            blue_team: str,
            red_team: str,
            home_side: Optional[str],
            current_turn: str,
            turn_counter: int,
            next_turn: str,
            blue_bans: List[str],
            red_bans: List[str],
            blue_picks: List[str],
            red_picks: List[str],
        ) -> str:

        print("[AI DataService] Updated context.")

        self.blue_team = blue_team
        self.red_team = red_team
        self.home_side = str(home_side).strip().lower()
        self.current_turn = current_turn
        self.turn_counter = turn_counter
        self.next_turn = next_turn
        self.blue_bans = blue_bans
        self.red_bans = red_bans
        self.blue_picks = blue_picks
        self.red_picks = red_picks

        self.context = [
            "You are a pro League of Legends draft analyst hired by an eSports organization to give draft advice.",
            "You will be given a CSV containing historical match/pick data.",
            "You will provide suggestions and predictions taking into account draft state, team composition and the historical data.",
            "Context: Champion Draft Assistant.",
            f"Blue Team: {self.blue_team}",
            f"Red Team: {self.red_team}",
            f"Home side: {self.home_side or 'unset'}", 
            f"Turn: {self.current_turn}", # blue_pick, red_pick, blue_ban, red_ban
            f"Next turn: {self.next_turn}",
            f"Blue bans: {', '.join(self.blue_bans) if self.blue_bans else 'none'}",
            f"Red bans: {', '.join(self.red_bans) if self.red_bans else 'none'}",
            f"Blue picks: {', '.join(self.blue_picks) if self.blue_picks else 'none'}",
            f"Red picks: {', '.join(self.red_picks) if self.red_picks else 'none'}",

            "Be concise and helpful.",
            "If asked for suggestions or predictions, provide 5 champions with brief reasons.",
        ]

    # Sends a one-off message that includes the current context.
    def send_status_update(
            self,
            update_text: str,
            system_instruction: Optional[str] = None,
        ) -> str:

        print("[AI DataService] Sent status update to Gemini.")

        prompt = f"{self.context}\n\nUser request:\n{update_text}".strip()
        return self.gm.generate_text(
            prompt=prompt,
            system_instruction=system_instruction,
        )
    
    # Returns a RecommendationResponse
    def get_recommendations(
            self,
            n: int = 3,
            system_instruction: Optional[str] = None,
        ) -> RecommendationResponse:

        print("[AI DataService] Sending recommendations request to Gemini.")

        suggest_side, predict_side, friendly_team, opponent_team = self.sides()

        # Phase 1 Bans (Turns 0-5)
        if self.turn_counter < 6:
            task = (
                f"Ban Phase 1: Provide exactly 5 champion recommendations for {friendly_team} ({suggest_side}) to ban. "
                f"Then, predict exactly 5 champions that {opponent_team} ({predict_side}) will likely ban in this phase."
            )

        # Blue 1 pick (Turn 6)
        elif self.turn_counter < 7:
            if suggest_side == "blue":
                task = f"B1 Pick: Suggest 5 high-priority power picks for {friendly_team} to lock in first, and predict 5 responses {opponent_team} might pick in the next turn."
            else:
                task = f"B1 Prediction: Predict 5 champions {opponent_team} (Blue) will pick first. Include probabilities for each. Suggest 5 responses {friendly_team} should pick in the next turn."

        # Red Pick 1 & 2 (Turn 7 & 8)
        elif self.turn_counter < 9:
            if suggest_side == "red":
                task = f"R1/R2 Picks: Suggest 5 champion pairs or individual picks for {friendly_team} to secure in the R1/R2 slots, and predict 5 responses {opponent_team} might pick in the next turn."
            else:
                task = f"R1/R2 Prediction: Predict 5 champions {opponent_team} will pick in these slots. Include probabilities. Suggest 5 responses {friendly_team} should pick in the next turn."

        # Blue Pick 2 & 3 (Turn 9 & 10)
        elif self.turn_counter < 11:
            if suggest_side == "blue":
                task = f"B2/B3 Picks: Suggest 5 champions for {friendly_team} to round out the Phase 1 core (B2, B3), and predict 5 responses {opponent_team} might pick in the next turn."
            else:
                task = f"B2/B3 Prediction: Predict 5 champions {opponent_team} will pick here. Include probabilities. Suggest 5 responses {friendly_team} should pick in the next turn."

        # Red Pick 3 (Turn 11)
        elif self.turn_counter < 12:
            if suggest_side == "red":
                task = f"R3 Pick: Suggest 5 champions for {friendly_team} to finalize Phase 1 (R3)."
            else:
                task = f"R3 Prediction: Predict 5 champions {opponent_team} (Red) will pick for R3. Include probabilities."

        # Ban Phase 2 (Turns 12-15)
        elif self.turn_counter < 16:
            task = (
                f"Ban Phase 2: Suggest 5 target bans for {friendly_team} based on remaining roles. "
                f"Predict 5 bans that {opponent_team} will target against us."
            )

        # Red Pick 4 (Turn 16)
        elif self.turn_counter < 17:
            if suggest_side == "red":
                task = f"R4 Pick: Suggest 5 champions for {friendly_team} (R4) to bridge into the final comp, and predict 5 responses {opponent_team} might pick in the next turn."
            else:
                task = f"R4 Prediction: Predict 5 champions {opponent_team} will pick for R4. Include probabilities. Suggest 5 responses {friendly_team} should pick in the next turn."

        # Blue Pick 4 & 5 (Turns 17-18)
        elif self.turn_counter < 19:
            if suggest_side == "blue":
                task = f"B4/B5 Picks: Suggest 5 champions or champion pairs for {friendly_team} to finalize the draft (B4, B5), and predict 5 responses {opponent_team} might pick in the next turn."
            else:
                task = f"B4/B5 Prediction: Predict 5 champions {opponent_team} will pick for B4/B5. Include probabilities. Suggest 5 responses {friendly_team} should pick in the next turn."

        # Red Pick 5 (Turn 19)
        elif self.turn_counter < 20:
            if suggest_side == "red":
                task = f"R5 (Counter-Pick): Suggest 5 ultimate counter-picks for {friendly_team} for the R5 slot."
            else:
                task = f"R5 Prediction: Predict 5 champions {opponent_team} (Red) will use for their final counter-pick."
        
        if self.turn_counter < 20:
            task += (
                "Return them in the JSON schema under 'recommendations' suggestions go in 'DraftModel' with champion_name, reasoning, confidence_score possible_synergies, possible_counters."
                "Predictions go in 'DraftPrediction' with predicted_next_champ, confidence_score, and reasoning. When asked to predict, do not provide suggestions and rely heavily on historical data."
                "Keep the 'strategic_summary' concise and reference historical statistics and data from the provided csv, with emphasis on recent data.\n\n"
            )
        else:
            task = (
                "Return a predicted winrate for both teams given the current state of the draft and an analysis of key factors/champions, and put it in the 'strategic_summary'."
                "Predictions on the winrate should be based on csv data provided, reference it and provide any additional information that is relevant."
            )

        print("[AI DataService] Adding data context to prompt...")

        prompt = f"{self.context}\n\nData Context: {self.data_context}\n\nTask:\n{task}".strip()

        result = self.gm.generate_structured(
            prompt=prompt,
            response_schema=RecommendationResponse,
            system_instruction=system_instruction,
        )

        print("[AI DataService] Got response from Gemini:", result)
        print("[AI DataService] This was the prompt given:",prompt)
        # If response is in correct format then return it
        if isinstance(result, RecommendationResponse):
            return result

        if result is None:
             raise ValueError("GeminiManager returned None for structured generation.")

        # Otherwise, validate into RecommendationResponse
        try:
            return RecommendationResponse.model_validate(result)
        except ValidationError as ve:
            # If that doesn't work then just ask for plain text
            text = self.gm.generate_text(
                prompt=prompt,
                system_instruction=system_instruction,
            )
            raise ValueError(f"Failed to parse RecommendationResponse: {ve}\nModel said:\n{text}") from ve