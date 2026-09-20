import json
import os

import boto3
from botocore.exceptions import ClientError

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
STORIES_FILE = os.path.join(DATA_DIR, "stories.json")
AUDIO_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend", "app", "audio")

PAUSE = "  "  # two spaces — natural inter-sentence pause for TTS


def build_text(story):
    parts = [story.get("headline", "").strip()]
    for fact in story.get("agreed_facts", []):
        if isinstance(fact, str) and fact.strip():
            parts.append(fact.strip())
    return PAUSE.join(parts)


def synthesise(polly, text, story_id, out_path):
    """Try Kajal (neural), fall back to Aditi (standard). Returns voice used."""
    for voice, engine in [("Kajal", "neural"), ("Aditi", "standard")]:
        try:
            resp = polly.synthesize_speech(
                Text=text,
                Engine=engine,
                VoiceId=voice,
                OutputFormat="mp3",
            )
            audio = resp["AudioStream"].read()
            with open(out_path, "wb") as f:
                f.write(audio)
            return voice
        except ClientError as e:
            code = e.response["Error"]["Code"]
            if code in ("InvalidSsmlException", "ValidationException",
                        "UnsupportedPlsAlphabet", "InvalidParameterValue") or \
               "not available" in str(e).lower() or \
               "not supported" in str(e).lower():
                continue
            raise
    raise RuntimeError(f"No available voice for story {story_id}")


def main():
    os.makedirs(AUDIO_DIR, exist_ok=True)

    with open(STORIES_FILE) as f:
        data = json.load(f)
    stories = data.get("stories", [])

    polly = boto3.client("polly")
    first_voice = None

    for story in stories:
        story_id = story.get("id", "")
        if not story_id:
            print(f"  SKIP  (no id)")
            continue

        out_path = os.path.join(AUDIO_DIR, f"{story_id}.mp3")
        if os.path.exists(out_path):
            text = build_text(story)
            print(f"  {story_id}  {len(text):>5} chars  skipped")
            continue

        text = build_text(story)
        voice = synthesise(polly, text, story_id, out_path)
        if first_voice is None:
            first_voice = voice
            if voice != "Kajal":
                print(f"  Note: Kajal unavailable in this region — using {voice}")
        print(f"  {story_id}  {len(text):>5} chars  saved  [{voice}]")


if __name__ == "__main__":
    main()
