# RE:LIFE

RE:LIFE is a mobile-first sustainability web app built as a hackathon submission for the Tuwaiq Academy Cloud Computing Program, delivered in collaboration with Google.

The idea is simple: take a photo of an everyday object before throwing it away. RE:LIFE uses Google Gemini to understand the object, suggest four practical reuse ideas, and generate a visual preview showing what those ideas could look like. The experience is designed to make reuse feel approachable, useful, and worth sharing.

## What we built

| Area | What it does |
|---|---|
| Smart analysis | Identifies the photographed object, material, category, and appropriate handling method. |
| Four reuse ideas | Gemini proposes four realistic ideas based on the actual object instead of a fixed list. |
| Visual concept | Generates one four-panel image that presents all suggested outcomes while keeping image-generation costs controlled. |
| Guided execution | Each idea includes materials, clear steps, difficulty, and estimated time. |
| Community | Users can publish their reuse results, upload photos, share posts, and toggle likes. |
| Personal impact | Tracks analyzed items, generated ideas, eco points, community activity, and unlocked achievements. |
| Mobile web app | Includes camera capture, gallery upload, a fixed bottom navigation bar, responsive layouts, and PWA support. |

## How it works

```text
Capture or upload an object
            ↓
Normalize and validate the image
            ↓
Check the local analysis cache
            ↓
Analyze the object with Gemini
            ↓
Create four practical reuse ideas
            ↓
Generate one four-panel concept image
            ↓
Explore the steps or share the result
```

Repeated uploads of the same image reuse the stored analysis, reducing unnecessary API calls and keeping the prototype cost-aware.

## Technology

| Layer | Technology |
|---|---|
| Backend | Python, Flask |
| AI | Google Gemini API, Google Gen AI SDK |
| Data | SQLite |
| Frontend | HTML, CSS, vanilla JavaScript |
| Image processing | Pillow |
| Web app support | Web App Manifest, Service Worker |

## Project structure

```text
.
├── app.py                  # Flask routes, database, AI workflow, and image handling
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
├── templates/              # Arabic RTL application pages
│   ├── index.html          # Onboarding and home camera experience
│   ├── result.html         # Analysis and four generated ideas
│   ├── idea.html           # Materials and implementation steps
│   ├── community.html      # Community feed and publishing
│   └── impact.html         # Personal impact and achievements
└── static/
    ├── app.js              # Camera, uploads, navigation, likes, and UI behavior
    ├── style.css           # Responsive design system
    ├── manifest.json       # PWA metadata
    ├── sw.js               # Application shell cache
    ├── assets/             # Brand and interface artwork
    ├── images/             # Curated community demo images
    └── uploads/            # Runtime user and Gemini-generated images
```

The architecture intentionally remains compact. This is a hackathon MVP, so the backend stays in one Flask file and the frontend uses framework-free HTML, CSS, and JavaScript.

## Run locally

1. Create and activate a virtual environment.

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install the dependencies.

   ```bash
   pip install -r requirements.txt
   ```

3. Create the local environment file.

   ```bash
   cp .env.example .env
   ```

4. Add your Gemini API key to `.env`, then start the app.

   ```bash
   python app.py
   ```

5. Open [http://127.0.0.1:5000](http://127.0.0.1:5000).

Camera access requires `localhost` or HTTPS. If camera permission is unavailable, the gallery upload remains available as a fallback.

## Environment variables

| Variable | Required | Purpose |
|---|---:|---|
| `GEMINI_API_KEY` | Yes | Enables live object analysis and concept-image generation. |
| `SECRET_KEY` | Recommended | Protects Flask session signing outside local development. |
| `GEMINI_TEXT_MODEL` | No | Overrides the default cost-efficient text model. |
| `GEMINI_IMAGE_MODEL` | No | Overrides the default image model. |

## Current scope

RE:LIFE is a functional MVP rather than a production identity platform. Community likes are associated with a stable browser identifier, and personal impact is derived from the local SQLite database. A production release would add authenticated accounts, cloud object storage, managed databases, moderation, observability, and deployment-specific security controls.

## Why this project matters

Many reusable objects are discarded because people cannot quickly imagine a practical second use. RE:LIFE turns that moment into a small creative decision: one photo becomes four realistic possibilities, clear instructions, and a result that can inspire someone else.

