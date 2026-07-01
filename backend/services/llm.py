import json
import os
from groq import Groq


def _get_client():
    return Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """You are a professional music analyst and songwriting coach. Given a song's title, artist, detected musical key, and tempo (BPM), provide a detailed analysis and actionable songwriting tips.

You must respond with valid JSON matching this exact structure:
{
  "key": "The key as a string, e.g. 'F Major' or 'C# Minor'",
  "key_detail": "1-2 sentences about the key choice, any modal characteristics, or key changes",
  "tempo": "BPM as a string with unit, e.g. '120 BPM'",
  "tempo_detail": "1-2 sentences about the feel, groove, whether it's straight or swing, energy level",
  "arrangement": "Song structure described as sections with arrows, e.g. 'Intro → Verse 1 → Chorus → ...'",
  "instruments": ["Array of instruments with emoji prefix, e.g. '🎸 Electric Guitar', '🥁 Drums'"],
  "mood_text": "2-3 sentences describing the overall emotional character and energy",
  "moods": [
    {"text": "Mood tag word", "class": "one of: warm, teal, gold, purple"}
  ],
  "tips": [
    {
      "label": "Tip category (e.g. 'Try This', 'Arrangement Tip', 'Instrumentation Tip', 'Mood Tip')",
      "class": "CSS class: '' for primary, 'warm' for arrangement, 'teal' for instrumentation, 'gold' for mood",
      "text": "2-3 sentences of specific, actionable songwriting advice based on this song's characteristics"
    }
  ]
}

Guidelines:
- Provide exactly 4 mood tags
- Provide exactly 4 tips (one general "Try This", one arrangement, one instrumentation, one mood)
- Tips must be SPECIFIC to this song — reference the actual key, tempo, and known characteristics
- Instruments should reflect what's actually in the song (typically 5-7 instruments/layers)
- Be musically accurate — if the song is well-known, use your knowledge of it
- Keep all text concise and scannable"""


def generate_song_analysis(title: str, artist: str, key: str, mode: str, bpm: int) -> dict:
    """
    Generate full song analysis and songwriting tips using OpenAI.
    """
    user_prompt = f"""Analyze this song and generate songwriting tips:

Title: {title}
Artist: {artist}
Detected Key: {key} {mode}
Detected Tempo: {bpm} BPM

Provide a complete analysis covering arrangement, instrumentation, mood, and 4 actionable songwriting tips."""

    client = _get_client()
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.7,
        max_tokens=1500,
    )

    result = json.loads(response.choices[0].message.content)

    # Validate required fields exist
    required_fields = ["key", "key_detail", "tempo", "tempo_detail", "arrangement", "instruments", "mood_text", "moods", "tips"]
    for field in required_fields:
        if field not in result:
            raise ValueError(f"LLM response missing required field: {field}")

    return result
