from typing import Optional, Dict, Any, Type, List
from google import genai
from google.genai import types
from dotenv import load_dotenv
import os

from pydantic import BaseModel

load_dotenv()

class GeminiError(Exception):
    pass

class GeminiManager:
    def __init__(
            self, 
            api_key: Optional[str] = None, 
            default_model: str = "gemini-3-flash-preview",
            #default_model: str = "gemini-2.0-flash",
            default_config: Optional[Dict[str, Any]] = None):

        self.api_key = api_key or os.getenv("GOOGLE_API")
        if not self.api_key:
            raise ValueError("No API Key provided. Set GOOGLE_API or pass it to __init__.")
        
        try:
            self.client = genai.Client(api_key=self.api_key)
        except Exception as e:
            raise GeminiError(f"Error initializing Gemini client: {e} ") from e
        
        self.model_name = default_model
        self.default_config = default_config or {
            "temperature": 0.4,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
        }

    # Updates the config with the provided config or just returns the config
    def update_config(self, override_config: Optional[Dict[str, Any]] = None):
        config = self.default_config.copy()
        if override_config:
            config.update(override_config)
        return config

    # Generates a one time response from Gemini in plaintext
    def generate_text(
            self,
            prompt: str,
            system_instruction: Optional[str] = None, # Behavioral rules 
            generation_config: Optional[Dict[str, Any]] = None, # Parameters for the model
        ) -> str:

        final_conf_dict = self.update_config(generation_config)

        gen_config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            **final_conf_dict
        )

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=gen_config
            )
            if hasattr(response, "text") and response.text:
                return response.text
            raise GeminiError("Empty response from Gemini.")
        except Exception as e:
            raise GeminiError(f"Error generating text: {e}") from e


    def generate_structured(
            self,
            prompt: str,
            response_schema: Type[BaseModel], # Specific response schema
            system_instruction: Optional[str] = None, # Behavioral rules 
            generation_config: Optional[Dict[str, Any]] = None, # Parameters for the model
        ):

        final_conf_dict = self.update_config(generation_config)

        gen_config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=response_schema,
            **final_conf_dict
        )

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=gen_config
            )
            
            if hasattr(response, "parsed") and response.parsed is not None:
                return response.parsed
            
            # Fallback manual parsing
            if hasattr(response, "text") and response.text:
                return response_schema.model_validate_json(response.text)
            
            raise GeminiError("Gemini returned an empty response (no text, no parsed data).")

        except Exception as e:
            raise GeminiError(f"Error generating structured data: {e}") from e
      
    def start_chat_session(self, system_instruction: Optional[str] = None):

        final_conf_dict = self.update_config()

        gen_config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            **final_conf_dict
        )

        return self.client.chats.create(
            model=self.model_name,
            config=gen_config
        )
