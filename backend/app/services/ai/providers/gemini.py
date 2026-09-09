from app.core import settings
from app.services.ai.base import AIProvider, AIProviderError, GeneratedImage, ImageGenerationUnavailable


class GeminiProvider(AIProvider):
    name = "gemini"

    def _client(self):
        if not settings.GEMINI_API_KEY:
            raise AIProviderError("Gemini AI is not configured.")
        try:
            from google import genai
            return genai.Client(api_key=settings.GEMINI_API_KEY)
        except Exception as exc:
            raise AIProviderError("Gemini AI request failed.") from exc

    def generate_text(self, prompt: str) -> str:
        try:
            interaction = self._client().interactions.create(
                model=settings.GEMINI_MODEL,
                input=prompt,
                store=False,
            )
            return (getattr(interaction, "output_text", "") or "").strip()
        except AIProviderError:
            raise
        except Exception as exc:
            raise AIProviderError("Gemini AI returned an invalid response.") from exc

    def generate_image(self, prompt: str) -> GeneratedImage:
        if not settings.GEMINI_API_KEY:
            raise AIProviderError("Gemini AI is not configured.")
        if not settings.GEMINI_IMAGE_MODEL:
            raise ImageGenerationUnavailable(
                "No Gemini image-generation model is configured. Configure GEMINI_IMAGE_MODEL first."
            )
        image_models = {
            "gemini-2.5-flash-image",
            "gemini-3.1-flash-image",
            "gemini-3.1-flash-lite-image",
            "gemini-3-pro-image",
        }
        if settings.GEMINI_IMAGE_MODEL not in image_models:
            raise ImageGenerationUnavailable(
                "The configured Gemini image model does not support image generation. Configure a supported image model."
            )
        try:
            interaction = self._client().interactions.create(
                model=settings.GEMINI_IMAGE_MODEL,
                input=prompt,
                response_format={"type": "image", "aspect_ratio": "16:9", "image_size": "1K"},
                store=False,
            )
            output_image = getattr(interaction, "output_image", None)
            data = getattr(output_image, "data", None)
            if not data:
                raise AIProviderError("Gemini AI returned no image data.")
            import base64
            return GeneratedImage(data=base64.b64decode(data), media_type=getattr(output_image, "mime_type", "image/png"))
        except AIProviderError:
            raise
        except Exception as exc:
            raise AIProviderError("Thumbnail generation failed. Please try again.") from exc