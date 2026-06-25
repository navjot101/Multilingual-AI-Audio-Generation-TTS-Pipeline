import os
import logging
from openai import OpenAI

log = logging.getLogger(__name__)


def generate_story(script: str, genre: str, language: str, context_chunks: list[str]) -> str:
    provider = os.getenv("LLM_PROVIDER", "groq")
    log.info("Using LLM provider: %s", provider)

    if provider == "deepseek":
        return _generate_deepseek(script, genre, language, context_chunks)
    elif provider == "groq":
        return _generate_groq(script, genre, language, context_chunks)
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {provider}")


def _build_system_prompt(context_chunks: list[str]) -> str:
    context_text = "\n\n".join(context_chunks)
    return (
        f"You are a professional audio story writer. Use the following context "
        f"to inform your story:\n\n{context_text}\n\n"
        "Write a short dramatic script (2-4 paragraphs) with speaker and emotion tags.\n"
        "Format:\n"
        "[SPEAKER:NARRATOR][EMOTION:NEUTRAL] text here.\n"
        "[SPEAKER:CHARACTER][EMOTION:HAPPY] dialogue here.\n\n"
        "Available speakers: NARRATOR, CHARACTER_1, CHARACTER_2 (create names "
        "fitting the genre).\n"
        "Available emotions: NEUTRAL, HAPPY, SAD, ANGRY, FEARFUL, TENSE, EXCITED, "
        "CALM, MYSTERIOUS"
    )


def _generate_deepseek(script: str, genre: str, language: str, context_chunks: list[str]) -> str:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY environment variable not set")

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": _build_system_prompt(context_chunks)},
            {
                "role": "user",
                "content": (
                    f"Genre: {genre}\n"
                    f"Language: {language}\n"
                    f"Script premise: {script}"
                ),
            },
        ],
        temperature=0.7,
        max_tokens=1024,
    )
    return response.choices[0].message.content


def _generate_groq(script: str, genre: str, language: str, context_chunks: list[str]) -> str:
    from groq import Groq

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable not set")

    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[
            {"role": "system", "content": _build_system_prompt(context_chunks)},
            {
                "role": "user",
                "content": (
                    f"Genre: {genre}\n"
                    f"Language: {language}\n"
                    f"Script premise: {script}"
                ),
            },
        ],
        temperature=0.7,
        max_tokens=1024,
    )
    return response.choices[0].message.content
