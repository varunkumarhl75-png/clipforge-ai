import json
from typing import Any
from urllib.request import Request, urlopen

from app.core import settings


class ContentProviderError(RuntimeError):
    pass


class ContentProvider:
    name = 'none'

    def generate(self, transcript: str) -> dict[str, Any]:
        raise NotImplementedError


class OpenAIProvider(ContentProvider):
    name = 'openai'

    def generate(self, transcript: str) -> dict[str, Any]:
        if not settings.OPENAI_API_KEY:
            raise ContentProviderError('LLM is not configured. Set OPENAI_API_KEY to generate a content package.')
        prompt = ('Return only valid JSON with keys title_suggestions, description, hashtags, tags, hooks, '
                  'thumbnail_text_suggestions. Create a concise YouTube package from this transcript:\n\n' + transcript[:12000])
        payload = json.dumps({'model': settings.OPENAI_MODEL, 'messages': [{'role': 'user', 'content': prompt}], 'temperature': 0.4}).encode()
        request = Request('https://api.openai.com/v1/chat/completions', data=payload, headers={'Authorization': f'Bearer {settings.OPENAI_API_KEY}', 'Content-Type': 'application/json'})
        try:
            with urlopen(request, timeout=60) as response:
                content = json.loads(response.read().decode())['choices'][0]['message']['content']
            result = json.loads(content)
        except Exception as exc:
            raise ContentProviderError(f'LLM request failed: {exc}') from exc
        required = ('title_suggestions', 'description', 'hashtags', 'tags', 'hooks', 'thumbnail_text_suggestions')
        if any(key not in result for key in required) or not all(isinstance(result[key], (list, str)) for key in required):
            raise ContentProviderError('LLM returned an invalid content package')
        return result


def get_content_provider() -> ContentProvider:
    return OpenAIProvider()
