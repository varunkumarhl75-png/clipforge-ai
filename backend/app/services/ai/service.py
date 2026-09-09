from app.core import settings
from app.services.ai.base import AIProviderError
from app.services.ai.providers import GeminiProvider, OpenAIProvider


def get_ai_provider() -> GeminiProvider | OpenAIProvider:
    providers = {"gemini": GeminiProvider, "openai": OpenAIProvider}
    provider_class = providers.get(settings.AI_PROVIDER.lower())
    if provider_class is None:
        raise AIProviderError("The configured AI provider is not supported.")
    return provider_class()