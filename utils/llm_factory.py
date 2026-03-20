"""
LLM Factory — swap between XAI, OpenAI, Anthropic via LangChain.
"""
from typing import Optional
from langchain_openai import ChatOpenAI
from utils.config import config


_PROVIDERS = {
    "xai": {
        "base_url": "https://api.x.ai/v1",
        "default_model": "grok-3-mini-fast",
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
    spec = _PROVIDERS.get(provider, _PROVIDERS["xai"])

    api_key = {
        "xai": config.xai_api_key,
        "openai": config.openai_api_key,
    }.get(provider, config.xai_api_key)

    kwargs = dict(
        model=model or spec["default_model"],
        temperature=temperature or config.default_temperature,
        api_key=api_key,
    )
    if spec["base_url"]:
        kwargs["base_url"] = spec["base_url"]

    return ChatOpenAI(**kwargs)
