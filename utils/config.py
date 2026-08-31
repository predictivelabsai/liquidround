"""
Configuration management for LiquidRound system.
"""
VERSION = "0.8.1"

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
        self.default_provider = os.getenv("MODEL_PROVIDER") or os.getenv("DEFAULT_PROVIDER") or "xai"
        self.default_model = os.getenv("DEFAULT_MODEL", "grok-4-1-fast-reasoning")
        self.default_temperature = float(os.getenv("DEFAULT_TEMPERATURE", "0.7"))

        # Environment
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.public_base_url = os.getenv("PUBLIC_BASE_URL", "http://localhost:5007").rstrip("/")
        self.agent_timeout_seconds = max(
            5, min(int(os.getenv("AGENT_TIMEOUT_SECONDS", "120")), 300)
        )
        self.agent_recursion_limit = max(
            4, min(int(os.getenv("AGENT_RECURSION_LIMIT", "24")), 100)
        )
        self.agent_max_tool_calls = max(
            1, min(int(os.getenv("AGENT_MAX_TOOL_CALLS", "12")), 50)
        )

        # Optional Hermes delegation. Disabled unless explicitly enabled.
        self.hermes_enabled = os.getenv("HERMES_ENABLED", "false").lower() in {"1", "true", "yes"}
        self.hermes_command = os.getenv("HERMES_COMMAND", "hermes")
        self.hermes_model = os.getenv("HERMES_MODEL", "")
        self.hermes_provider = os.getenv("HERMES_PROVIDER", "")
        self.hermes_toolsets = os.getenv("HERMES_TOOLSETS", "")
        self.hermes_timeout_seconds = max(5, min(int(os.getenv("HERMES_TIMEOUT_SECONDS", "90")), 300))
        self.hermes_safe_mode = os.getenv("HERMES_SAFE_MODE", "true").lower() not in {"0", "false", "no"}

        self._validate_config()

    def _validate_config(self):
        if not self.xai_api_key and not self.openai_api_key:
            raise ValueError("At least one of XAI_API_KEY or OPENAI_API_KEY must be set")

    def get_model_config(self, model: Optional[str] = None, temperature: Optional[float] = None) -> Dict[str, Any]:
        return {
            "model": model or self.default_model,
            "temperature": self.default_temperature if temperature is None else temperature,
        }

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


config = Config()
