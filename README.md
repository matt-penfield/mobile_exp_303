# SongCraft

A mobile-first web app that analyzes songs from YouTube links and generates actionable songwriting tips. Paste a link, get a structured breakdown of key, tempo, arrangement, instrumentation, and mood — plus four tailored tips to apply those techniques to your own writing.

**Live:** Deployed on Vercel

---

## Project Structure

```
├── index.html              # Frontend (single-file SPA)
├── api/
│   └── analyze.py          # Vercel serverless function (Python)
├── backend/
│   ├── main.py             # Local dev server (FastAPI + uvicorn)
│   ├── .env                # Local env vars (git-ignored)
│   ├── .env.example        # Template for required env vars
│   ├── requirements.txt    # Local dev dependencies
│   └── services/
│       └── llm.py          # Groq LLM integration
├── requirements.txt        # Vercel serverless dependencies
├── vercel.json             # Vercel deployment config
├── BRIEF.md                # Product brief
└── .gitignore
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Single `index.html` — vanilla HTML/CSS/JS, no build step |
| Local Dev Server | FastAPI + uvicorn (port 8000), serves frontend + API |
| Vercel Function | Python serverless function (`BaseHTTPRequestHandler`) |
| Metadata | YouTube oEmbed API (public, no auth required) |
| Song Analysis | Groq API — Llama 3.3 70B Versatile, JSON mode |
| Storage | Browser localStorage |

### Dependencies

- **Groq SDK** — LLM API client
- **FastAPI + uvicorn** — Local development server
- **python-dotenv** — Local env var loading

---

## Setup

### Prerequisites

- Python 3.12+
- A [Groq API key](https://console.groq.com/keys)

### Local Development

```bash
# Clone the repo
git clone https://github.com/matt-penfield/mobile_exp_303.git
cd mobile_exp_303

# Install backend dependencies
cd backend
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your GROQ_API_KEY

# Start the server
python -m uvicorn main:app --reload --port 8000
```

Open `http://localhost:8000` in your browser.

### Vercel Deployment

1. Import the GitHub repo into [Vercel](https://vercel.com)
2. Vercel auto-detects the config from `vercel.json`
3. Add the environment variable in **Settings → Environment Variables**:
   - `GROQ_API_KEY` = your Groq API key
   - Ensure it's enabled for **Production** (not just Preview)
4. Deploy (or redeploy if you added the env var after the first deploy)

**Important:** Env var changes require a redeploy to take effect. Go to Deployments → latest → ⋮ → Redeploy.

The `vercel.json` config:
- Sets `"framework": null` to prevent FastAPI auto-detection
- Gives the serverless function a 30-second max duration
- Adds CORS headers for the API route

---

## Architecture Notes

### How It Works

1. User submits a YouTube URL
2. The backend extracts the song title and artist via YouTube's oEmbed API (no download, no auth needed)
3. Title and artist are sent to Groq's Llama 3.3 70B model, which returns a structured JSON analysis covering key, tempo, arrangement, instrumentation, mood, and songwriting tips
4. Results are displayed as cards and saved to browser localStorage

Both the local dev server (`backend/main.py`) and the Vercel serverless function (`api/analyze.py`) use the same approach. The local server uses FastAPI; the Vercel function uses a plain `BaseHTTPRequestHandler` to avoid framework auto-detection conflicts.

### Frontend

- Single `index.html` — all CSS inline, vanilla JS, no build step
- Screens: Home (URL input + recent list), Loading (animated steps), Results (5 analysis cards + tips), Library
- Analyses persisted to `localStorage` under key `songcraft_analyses`
- API endpoint: `POST /api/analyze` with body `{ "youtube_url": "..." }`

### Design System

- Light minimal theme — white surface, `#F6F6F6` cards, no borders
- Merriweather 900 (serif, black weight) for the logo
- Helvetica for body text
- Accent colors: dark red `#C62828`, teal `#00796B`, gold `#8D6200`
- WCAG AA compliant contrast ratios

---

## API Reference

### `POST /api/analyze`

**Request:**
```json
{
  "youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID"
}
```

**Response:**
```json
{
  "title": "Song Title — Artist",
  "artist": "Artist",
  "key": "F Major",
  "key_detail": "Description of key characteristics...",
  "tempo": "96 BPM",
  "tempo_detail": "Description of feel and groove...",
  "arrangement": "Intro → Verse 1 → Chorus → ...",
  "instruments": ["🎸 Acoustic Guitar", "🥁 Drums", "🎤 Vocals"],
  "mood_text": "Description of emotional character...",
  "moods": [{"text": "Melancholic", "class": "warm"}],
  "tips": [{"label": "Try This", "class": "", "text": "Specific advice..."}]
}
```

**Error Response:**
```json
{
  "detail": "Error description with type and message"
}
```