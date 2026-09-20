import json
import os

import boto3
from botocore.exceptions import ClientError

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
STORIES_FILE = os.path.join(DATA_DIR, "stories.json")
AUDIO_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend", "app", "audio")

def _esc(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_ssml(story):
    headline = _esc(story.get("headline", "").strip())
    facts = [_esc(f.strip()) for f in story.get("agreed_facts", [])
             if isinstance(f, str) and f.strip()]
    inner = headline + '<break time="700ms"/>' + '<break time="400ms"/>'.join(facts)
    return '<speak><prosody rate="92%">' + inner + '</prosody></speak>'


def synthesise(polly, ssml, story_id, out_path):
    """Try Kajal (neural), fall back to Aditi (standard). Returns voice used."""
    for voice, engine in [("Kajal", "neural"), ("Aditi", "standard")]:
        try:
            resp = polly.synthesize_speech(
                Text=ssml,
                TextType="ssml",
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
            text = build_ssml(story)
            print(f"  {story_id}  {len(text):>5} chars  skipped")
            continue

        text = build_ssml(story)
        voice = synthesise(polly, text, story_id, out_path)
        if first_voice is None:
            first_voice = voice
            if voice != "Kajal":
                print(f"  Note: Kajal unavailable in this region — using {voice}")
        print(f"  {story_id}  {len(text):>5} chars  saved  [{voice}]")


if __name__ == "__main__":
    main()
