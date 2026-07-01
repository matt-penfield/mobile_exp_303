import os
import tempfile
import re
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

from services.youtube import extract_audio_and_metadata
from services.audio_analysis import analyze_audio
from services.llm import generate_song_analysis

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure temp directory exists
    os.makedirs(tempfile.gettempdir(), exist_ok=True)
    yield


app = FastAPI(title="SongCraft API", lifespan=lifespan)

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


@app.post("/analyze", response_model=AnalysisResponse)
def analyze_song(request: AnalyzeRequest):
    url = request.youtube_url.strip()
    print(f"[ANALYZE] Received request for: {url}")

    if not YOUTUBE_URL_PATTERN.match(url):
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")

    # Step 1: Extract audio and metadata from YouTube
    print("[ANALYZE] Step 1: Extracting audio...")
    try:
        audio_path, metadata = extract_audio_and_metadata(url)
    except Exception as e:
        print(f"[ANALYZE] Step 1 FAILED: {e}")
        raise HTTPException(status_code=422, detail=f"Failed to extract audio: {str(e)}")
    print(f"[ANALYZE] Step 1 done: {metadata['title']} by {metadata['artist']}")

    # Step 2: Analyze key and tempo with librosa
    print("[ANALYZE] Step 2: Analyzing audio...")
    try:
        audio_features = analyze_audio(audio_path)
    except Exception as e:
        print(f"[ANALYZE] Step 2 FAILED: {e}")
        raise HTTPException(status_code=500, detail=f"Audio analysis failed: {str(e)}")
    finally:
        # Clean up temp audio file
        if os.path.exists(audio_path):
            os.remove(audio_path)
    print(f"[ANALYZE] Step 2 done: {audio_features}")

    # Step 3: Generate full analysis and tips via LLM
    try:
        result = generate_song_analysis(
            title=metadata["title"],
            artist=metadata["artist"],
            key=audio_features["key"],
            mode=audio_features["mode"],
            bpm=audio_features["bpm"],
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


# Serve the frontend from the parent directory
frontend_path = os.path.join(os.path.dirname(__file__), "..")
app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
