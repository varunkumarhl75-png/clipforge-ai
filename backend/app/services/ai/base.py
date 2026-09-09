from abc import ABC, abstractmethod
from dataclasses import dataclass


class AIProviderError(RuntimeError):
    """An expected, user-safe provider failure."""


class ImageGenerationUnavailable(AIProviderError):
    """The configured provider cannot return image bytes."""


@dataclass(frozen=True)
class GeneratedImage:
    data: bytes
    media_type: str


class AIProvider(ABC):
    name = "unknown"

    @abstractmethod
    def generate_text(self, prompt: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def generate_image(self, prompt: str) -> GeneratedImage:
        raise NotImplementedError