"""
Configuration management for LiquidRound system.
"""
import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv


class Config:
    """Configuration manager for LiquidRound."""

    def __init__(self):
        load_dotenv()

        # API Keys
        self.xai_api_key = os.getenv("XAI_API_KEY") or os.getenv("XAI_API")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.exa_api_key = os.getenv("EXA_API_KEY")
        self.tavily_api_key = os.getenv("TAVILY_API_KEY")

        # LLM settings
        self.default_provider = os.getenv("DEFAULT_PROVIDER", "xai")
        self.default_model = os.getenv("DEFAULT_MODEL", "grok-3-mini-fast")
        self.default_temperature = float(os.getenv("DEFAULT_TEMPERATURE", "0.7"))

        # Environment
        self.environment = os.getenv("ENVIRONMENT", "development")

        self._validate_config()

    def _validate_config(self):
        if not self.xai_api_key and not self.openai_api_key:
            raise ValueError("At least one of XAI_API_KEY or OPENAI_API_KEY must be set")

    def get_model_config(self, model: Optional[str] = None, temperature: Optional[float] = None) -> Dict[str, Any]:
        return {
            "model": model or self.default_model,
            "temperature": temperature or self.default_temperature,
        }

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


config = Config()
