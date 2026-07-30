"""
LLM Factory — swap between XAI, OpenAI, Anthropic via LangChain.
"""
from typing import Optional
from langchain_openai import ChatOpenAI
from utils.config import config


_PROVIDERS = {
    "xai": {
        "base_url": "https://api.x.ai/v1",
        "default_model": "grok-4-1-fast-reasoning",
    },
    "openai": {
        "base_url": None,
        "default_model": "gpt-4o-mini",
    },
}


def create_llm(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
) -> ChatOpenAI:
    provider = provider or config.default_provider
    if provider not in _PROVIDERS:
        raise ValueError(f"Unsupported MODEL_PROVIDER: {provider}")
    spec = _PROVIDERS[provider]

    api_key = {
        "xai": config.xai_api_key,
        "openai": config.openai_api_key,
    }.get(provider, config.xai_api_key)

    kwargs = dict(
        model=model or config.default_model or spec["default_model"],
        temperature=config.default_temperature if temperature is None else temperature,
        api_key=api_key,
    )
    if spec["base_url"]:
        kwargs["base_url"] = spec["base_url"]

    return ChatOpenAI(**kwargs)
