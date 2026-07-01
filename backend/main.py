import os
import re
import json
from urllib.request import urlopen, Request
from urllib.parse import quote

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

from services.llm import generate_song_analysis

load_dotenv()


app = FastAPI(title="SongCraft API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

YOUTUBE_URL_PATTERN = re.compile(
    r"^(https?://)?(www\.|m\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)[\w\-]+"
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


def extract_metadata(youtube_url: str) -> dict:
    """Extract title and artist from YouTube using the oEmbed API."""
    youtube_url = re.split(r"[&?]list=", youtube_url)[0]

    oembed_url = f"https://www.youtube.com/oembed?url={quote(youtube_url, safe='')}&format=json"
    req = Request(oembed_url, headers={"User-Agent": "Mozilla/5.0"})
    resp = urlopen(req, timeout=10)
    data = json.loads(resp.read().decode())

    full_title = data.get("title", "Unknown Title")
    author = data.get("author_name", "Unknown Artist")

    if " - " in full_title:
        artist, title = full_title.split(" - ", 1)
    else:
        title = full_title
        artist = author

    if artist.endswith(" - Topic"):
        artist = artist[: -len(" - Topic")]

    return {"title": title.strip(), "artist": artist.strip()}


@app.post("/api/analyze", response_model=AnalysisResponse)
def analyze_song(request: AnalyzeRequest):
    url = request.youtube_url.strip()
    print(f"[ANALYZE] Received request for: {url}")

    if not YOUTUBE_URL_PATTERN.match(url):
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")

    # Step 1: Extract metadata from YouTube
    print("[ANALYZE] Step 1: Extracting metadata...")
    try:
        metadata = extract_metadata(url)
    except Exception as e:
        print(f"[ANALYZE] Step 1 FAILED: {e}")
        raise HTTPException(status_code=422, detail=f"YouTube extraction failed: {str(e)}")
    print(f"[ANALYZE] Step 1 done: {metadata['title']} by {metadata['artist']}")

    # Step 2: Generate full analysis and tips via LLM
    print("[ANALYZE] Step 2: Generating analysis...")
    try:
        result = generate_song_analysis(
            title=metadata["title"],
            artist=metadata["artist"],
        )
    except Exception as e:
        print(f"[ANALYZE] Step 2 FAILED: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis generation failed: {str(e)}")
    print("[ANALYZE] Step 2 done")

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


# Serve the frontend from the parent directory
frontend_path = os.path.join(os.path.dirname(__file__), "..")
app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
