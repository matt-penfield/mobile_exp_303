import os
import re
import json
from http.server import BaseHTTPRequestHandler
from urllib.request import urlopen, Request
from urllib.parse import quote
from groq import Groq


YOUTUBE_URL_PATTERN = re.compile(
    r"^(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)[\w\-]+"
)


def _get_groq_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not configured")
    return Groq(api_key=api_key)


def extract_metadata(youtube_url: str) -> dict:
    """Extract title and artist from YouTube using the oEmbed API."""
    youtube_url = re.split(r"[&?]list=", youtube_url)[0]

    oembed_url = f"https://www.youtube.com/oembed?url={quote(youtube_url, safe='')}&format=json"
    req = Request(oembed_url, headers={"User-Agent": "Mozilla/5.0"})
    resp = urlopen(req, timeout=10)
    data = json.loads(resp.read().decode())

    full_title = data.get("title", "Unknown Title")
    author = data.get("author_name", "Unknown Artist")

    # Many music videos use "Artist - Song" format in the title
    # Try to split; if not, use the channel name as artist
    if " - " in full_title:
        artist, title = full_title.split(" - ", 1)
    else:
        title = full_title
        artist = author

    # Clean up " - Topic" suffix
    if artist.endswith(" - Topic"):
        artist = artist[: -len(" - Topic")]

    return {"title": title.strip(), "artist": artist.strip()}


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


class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)

            url = data.get("youtube_url", "").strip()

            if not YOUTUBE_URL_PATTERN.match(url):
                self._send_error(400, "Invalid YouTube URL")
                return

            # Step 1: Extract metadata
            try:
                metadata = extract_metadata(url)
            except Exception as e:
                self._send_error(422, f"YouTube extraction failed: {type(e).__name__}: {str(e)}")
                return

            # Step 2: Generate analysis via LLM
            try:
                result = generate_analysis(metadata["title"], metadata["artist"])
            except Exception as e:
                self._send_error(500, f"LLM analysis failed: {type(e).__name__}: {str(e)}")
                return

            # Build response
            response = {
                "title": f"{metadata['title']} — {metadata['artist']}",
                "artist": metadata["artist"],
                "key": result["key"],
                "key_detail": result["key_detail"],
                "tempo": result["tempo"],
                "tempo_detail": result["tempo_detail"],
                "arrangement": result["arrangement"],
                "instruments": result["instruments"],
                "mood_text": result["mood_text"],
                "moods": result["moods"],
                "tips": result["tips"],
            }

            self._send_json(200, response)

        except Exception as e:
            self._send_error(500, f"Unexpected error: {type(e).__name__}: {str(e)}")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _send_json(self, status, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, status, message):
        self._send_json(status, {"detail": message})
