import hashlib
from typing import TypeVar

from openai import APIConnectionError, APIStatusError, OpenAI, RateLimitError
from pydantic import BaseModel, ValidationError

from ..config import GROQ_MODEL, require_groq_key
from ..config import AI_CACHE_TTL
from ..db import cache_get, cache_set
T = TypeVar("T", bound=BaseModel)


def _key(version: str, payload: str) -> str:
    return hashlib.sha256(f"{version}:{payload}".encode()).hexdigest()


def ask_json(system: str, user: str, version: str, schema: type[T]) -> T:
    cache_key = _key(f"{version}:{GROQ_MODEL}:{system}", user)
    cached = cache_get(f"groq:{cache_key}")
    if cached:
        return schema.model_validate_json(cached)

    client = OpenAI(api_key=require_groq_key(), base_url="https://api.groq.com/openai/v1")
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                temperature=0,
                reasoning_effort="low",
                response_format={"type": "json_object"},
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            )
            value = schema.model_validate_json(response.choices[0].message.content or "{}")
            cache_set(f"groq:{cache_key}", value.model_dump_json(), AI_CACHE_TTL)
            return value
        except (ValidationError, ValueError, APIConnectionError, APIStatusError, RateLimitError) as exc:
            last_error = exc
            if "429" not in str(exc) and attempt == 2:
                break
            time.sleep(2**attempt)
    raise RuntimeError(f"AI request failed after retries: {last_error}") from last_error
