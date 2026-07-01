# Song Writing Assistant

## Overview

A responsive mobile app (not a native app) that helps aspiring songwriters learn from their favorite music. Users paste YouTube links of songs they love, and the app analyzes each track to generate tailored songwriting tips — breaking down what makes the song work musically and how to apply those techniques to their own writing.  Mobile is key here, because musicians are often working with instruments that make it inconvenient to use desktop applications.

**Target User:** Beginner-to-intermediate songwriters who learn by studying songs they admire.

**Core Value Prop:** Turn passive listening into active learning — go from "I love this song" to "here's how to write something like it."

---

## Core Feature: Song Analysis via YouTube Link

The user pastes a YouTube URL into the app. The app extracts the audio, runs it through musical analysis, and returns a structured breakdown covering five dimensions:

### Analysis Output

| Dimension | What's Returned |
|-----------|----------------|
| **Key** | Detected musical key (e.g., C major, F♯ minor) and any key changes |
| **Tempo** | BPM, tempo variations, and feel (straight vs. swing) |
| **Arrangement** | Song structure map — intro, verse, pre-chorus, chorus, bridge, outro with approximate timestamps and section lengths |
| **Instrumentation** | Detected instruments/layers per section (e.g., "verse: acoustic guitar + vocals; chorus: adds drums, bass, synth pad") |
| **Mood** | Emotional tone (melancholic, uplifting, aggressive, dreamy), energy level (low/mid/high), and how mood shifts across sections |

---

## Songwriting Tips Generation

Analysis feeds into an LLM-powered tips engine that produces actionable, personalized writing advice. Tips are presented as structured cards:

**Example output for a song in D minor at 92 BPM:**

> **Try this:** Write in D minor at ~90 BPM. Start your verse sparse — just one instrument and vocals — then layer in drums and bass at the chorus to create contrast.

> **Arrangement tip:** This song uses a short 4-bar pre-chorus to build tension before the drop. Try adding a 2–4 bar transitional section between your verse and chorus.

> **Mood tip:** The melancholic tone comes from minor key + slow tempo + reverb-heavy vocals. To capture a similar vibe, keep your vocal production wet and your chord voicings open.


---

## User Flow

1. **Input** — User taps "Analyze a Song" and pastes a YouTube link
2. **Processing** — App extracts audio and runs analysis (loading state with progress)
3. **Results** — Structured breakdown appears as a scrollable card layout (key, tempo, arrangement, instrumentation, mood)
4. **Tips** — Below the analysis, actionable songwriting tips are generated and displayed as cards
5. **Save & Collect** — User can save the analysis to their library and build a multi-song style profile over time

---

## Technical Considerations

| Concern | Possible Approach |
|---------|-------------------|
| YouTube audio extraction | Server-side extraction via audio stream API |
| Musical analysis (key, tempo, structure) | Audio ML models (pitch detection, beat tracking, segmentation) |
| Instrumentation detection | Source separation + classification models |
| Mood analysis | Combination of audio features (valence, energy) + lyric sentiment |
| Tips generation | LLM with structured analysis as context, prompt-engineered for actionable songwriting advice |

---

## Scope & Constraints

### v1 (MVP)
- Single song analysis from YouTube link
- All five analysis dimensions returned
- Songwriting tips generated per song
- Save analyses to a personal library
- Mobile-first (iOS + Android)

### Future Roadmap
- Multi-song style profiles
- Side-by-side song comparison
- Export tips as a "writing brief" (PDF/share)
- Integration with DAWs or notation apps
- Support for Spotify/Apple Music/SoundCloud links
- Collaborative features (share analyses with bandmates)
