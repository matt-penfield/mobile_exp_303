import os
import re
import json
import tempfile

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp
from groq import Groq


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

YOUTUBE_URL_PATTERN = re.compile(
    r"^(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)[\w\-]+"
)


class AnalyzeRequest(BaseModel):
    youtube_url: str


class AnalysisResponse(BaseModel):
    title: str
    artist: str
    key: str
    key_detail: str
    tempo: str
    tempo_detail: str
    arrangement: str
    instruments: list[str]
    mood_text: str
    moods: list[dict]
    tips: list[dict]


def _get_groq_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not configured")
    return Groq(api_key=api_key)


def extract_metadata(youtube_url: str) -> dict:
    """Extract title and artist from YouTube without downloading audio."""
    # Strip playlist parameters
    youtube_url = re.split(r"[&?]list=", youtube_url)[0]

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "skip_download": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_url, download=False)

    title = info.get("title", "Unknown Title")
    artist = info.get("artist") or info.get("uploader") or "Unknown Artist"

    # Clean up " - Topic" suffix from auto-generated channels
    if artist.endswith(" - Topic"):
        artist = artist[: -len(" - Topic")]

    return {"title": title, "artist": artist}


SYSTEM_PROMPT = """You are a professional music analyst and songwriting coach. Given a song's title and artist, provide a detailed musical analysis including key, tempo, arrangement, instrumentation, mood, and actionable songwriting tips.

You must respond with valid JSON matching this exact structure:
{
  "key": "The key as a string, e.g. 'F Major' or 'C# Minor'",
  "key_detail": "1-2 sentences about the key choice, any modal characteristics, or key changes",
  "tempo": "BPM as a string with unit, e.g. '120 BPM'",
  "tempo_detail": "1-2 sentences about the feel, groove, whether it's straight or swing, energy level",
  "arrangement": "Song structure described as sections with arrows, e.g. 'Intro → Verse 1 → Chorus → ...'",
  "instruments": ["Array of instruments with emoji prefix. Use ONLY these emoji mappings: 🎸 for guitar (acoustic or electric), 🥁 for drums/percussion, 🎹 for piano/keyboards/synth, 🎤 for vocals, 🎵 for bass, 🎶 for backing vocals/harmonies, 🎻 for strings/violin/cello, 🎷 for saxophone/brass/woodwinds, 🎺 for trumpet/horn"],
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
- Keep all text concise and scannable
- For key and tempo, use your musical knowledge of the song to provide accurate values"""


def generate_analysis(title: str, artist: str) -> dict:
    """Generate full song analysis using Groq LLM."""
    user_prompt = f"""Analyze this song and generate songwriting tips:

Title: {title}
Artist: {artist}

Provide a complete analysis covering key, tempo, arrangement, instrumentation, mood, and 4 actionable songwriting tips."""

    client = _get_groq_client()
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

    required_fields = ["key", "key_detail", "tempo", "tempo_detail", "arrangement", "instruments", "mood_text", "moods", "tips"]
    for field in required_fields:
        if field not in result:
            raise ValueError(f"LLM response missing required field: {field}")

    return result


@app.post("/api/analyze")
def analyze_song(request: AnalyzeRequest):
    url = request.youtube_url.strip()

    if not YOUTUBE_URL_PATTERN.match(url):
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")

    # Step 1: Extract metadata from YouTube (no download needed)
    try:
        metadata = extract_metadata(url)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to extract metadata: {str(e)}")

    # Step 2: Generate full analysis via LLM
    try:
        result = generate_analysis(
            title=metadata["title"],
            artist=metadata["artist"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis generation failed: {str(e)}")

    return AnalysisResponse(
        title=f"{metadata['title']} — {metadata['artist']}",
        artist=metadata["artist"],
        key=result["key"],
        key_detail=result["key_detail"],
        tempo=result["tempo"],
        tempo_detail=result["tempo_detail"],
        arrangement=result["arrangement"],
        instruments=result["instruments"],
        mood_text=result["mood_text"],
        moods=result["moods"],
        tips=result["tips"],
    )
