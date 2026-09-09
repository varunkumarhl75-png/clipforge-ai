from app.services.ai.base import AIProvider, AIProviderError, GeneratedImage, ImageGenerationUnavailable
from app.services.content_service import ContentProviderError, OpenAIProvider as ContentOpenAIProvider


class OpenAIProvider(AIProvider):
    name = "openai"

    def generate_text(self, prompt: str) -> str:
        try:
            return ContentOpenAIProvider().generate(prompt)["description"]
        except ContentProviderError as exc:
            raise AIProviderError(str(exc)) from exc

    def generate_image(self, prompt: str) -> GeneratedImage:
        raise ImageGenerationUnavailable(
            "Image generation is not available with the configured provider/model."
        )