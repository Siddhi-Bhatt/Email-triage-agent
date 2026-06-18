import logging
from groq import Groq
from app.config import get_settings

logger = logging.getLogger("email_ai_service")

class LLMServiceError(Exception):
    pass


def call_llm(system_prompt: str, user_prompt: str, max_tokens: int = 1024) -> str:
    settings = get_settings()

    try:
        client = Groq(api_key=settings.groq_api_key)

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.7,
        )

        result = response.choices[0].message.content

        if not result:
            raise LLMServiceError("Empty response from Groq")

        return result.strip()

    except Exception as exc:
        logger.error("Groq error: %s", exc)
        raise LLMServiceError(f"Groq API error: {str(exc)}") from exc