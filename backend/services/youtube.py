import os
import tempfile
import yt_dlp


def extract_audio_and_metadata(youtube_url: str) -> tuple[str, dict]:
    """
    Downloads audio from a YouTube URL and extracts metadata.
    Returns (path_to_wav_file, metadata_dict).
    """
    temp_dir = tempfile.mkdtemp()
    output_path = os.path.join(temp_dir, "audio.wav")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(temp_dir, "audio.%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "192",
            }
        ],
        "quiet": True,
        "no_warnings": True,
        # Limit download to 10 minutes max to avoid huge files
        "match_filter": yt_dlp.utils.match_filter_func("duration < 600"),
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_url, download=True)

    # Parse metadata
    title = info.get("title", "Unknown Title")
    artist = info.get("artist") or info.get("uploader") or "Unknown Artist"

    # Clean up artist name — remove " - Topic" suffix from YouTube auto-generated channels
    if artist.endswith(" - Topic"):
        artist = artist[: -len(" - Topic")]

    metadata = {
        "title": title,
        "artist": artist,
        "duration": info.get("duration", 0),
    }

    # yt-dlp may name the file slightly differently
    if not os.path.exists(output_path):
        # Find the wav file in temp_dir
        for f in os.listdir(temp_dir):
            if f.endswith(".wav"):
                output_path = os.path.join(temp_dir, f)
                break
        else:
            raise RuntimeError("Audio extraction failed — no WAV file produced")

    return output_path, metadata
