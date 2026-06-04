# YouTube Autonomous Content Engine (YACE)

YACE (YouTube Autonomous Content Engine) is a fully automated YouTube content production platform. The engine manages the entire lifecycle of content creation, including topic discovery, script writing, voiceover generation, video rendering, thumbnail creation, publication scheduling, and performance monitoring.

---

## Technology Stack

- **Language:** Python 3.12+
- **Backend Framework:** FastAPI, Uvicorn
- **ORM & Database Tooling:** SQLAlchemy 2.0, Alembic
- **Database:** PostgreSQL
- **AI Synthesis (Ollama & Piper TTS):** Qwen3 LLM (Topic/Script), Piper (WAV narration)
- **Media Engine:** FFmpeg (Video rendering, caption burn-in)

---

## Folder Structure

```text
youtube-agent/
├── agents/             # Modular AI agents (Research, Script, Voice, etc.)
├── assets/             # Raw assets for media rendering
│   ├── fonts/          # Custom subtitle fonts
│   ├── music/          # Background music tracks
│   └── templates/      # Thumbnail templates
├── config/             # Configuration layer and env loaders
│   └── settings.py     # Pydantic Settings implementation
├── database/           # Database foundation, models, and session management
│   ├── models.py       # Core SQLAlchemy ORM models
│   └── postgres.py     # Engine initialization and get_db dependency
├── generated/          # Rendered artifacts (gitignored)
│   ├── scripts/        # Saved JSON/text script scripts
│   ├── audio/          # Rendered voice narration wav/mp3 files
│   ├── videos/         # Final rendered MP4 videos
│   ├── thumbnails/     # PNG thumbnails
│   └── assets/         # Intermediate image sequences/assets
├── logs/               # Application log files
├── migrations/         # Alembic database migrations
├── tests/              # Automated unit and integration tests
├── workflows/          # Orchestrators and pipeline managers
├── .env.example        # Reference environment configuration file
├── .gitignore          # Git exclusion settings
├── alembic.ini         # Alembic migration configuration
├── main.py             # Application bootstrap validator
├── requirements.txt    # Python package dependencies
└── README.md           # Project documentation
```

---

## Local Setup Instructions

### 1. Prerequisites
- Python 3.12 or 3.13 installed.
- PowerShell or command shell terminal access.

### 2. Environment Setup
Clone or navigate to the repository folder, and set up a virtual environment:
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Install package dependencies
pip install -r requirements.txt
```

### 3. Database Setup (Local-First Portable DB)
A PostgreSQL database is required. If you do not have PostgreSQL installed globally, you can initialize a local portable instance inside the project folder:
```bash
# Run setup script to download, extract, and start local PostgreSQL
python scripts/setup_postgres.py
```
This script downloads EDB's official portable binaries, initializes the data directory inside `.postgres/data`, creates the `yace` database, and starts the server on port `5432` with no password credentials required for localhost development.

To control the database manually in the future, use the generated helper scripts:
```powershell
# Start local PostgreSQL
.\start_postgres.ps1

# Stop local PostgreSQL
.\stop_postgres.ps1
```

### 4. Environment Variables Configuration
Configure your `.env` file in the root folder based on `.env.example`:
```env
APP_NAME=YACE
APP_ENV=development
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/yace
OLLAMA_URL=http://localhost:11434
LOG_LEVEL=INFO
```

---

## Database Migrations

This project uses Alembic to manage schemas. Generate and apply your schemas using the following commands:

```bash
# Generate the initial migration revision
alembic revision --autogenerate -m "initial schema"

# Apply migrations to database
alembic upgrade head
```

---

## Running the Application

To bootstrap and verify the application foundation (verifying settings loading, directory paths, and PostgreSQL database connection):

```bash
python main.py
```

Expected output upon successful execution:
```text
----------------------------------------
YACE started successfully
Environment: development
Database: Connected
----------------------------------------
```

---

## Production Hardening (Phase 4.9)

Phase 4.9 introduces environment configuration hardening, database isolation, AI model interaction auditing, and automated verification pipelines.

### Environment Setup

Create a `.env` file in the root directory based on the provided `.env.example` file. All environment variables have safe, localized defaults:

* `DATABASE_URL`: Connection string for production database sessions.
* `TEST_DATABASE_URL`: Connection string dedicated strictly to testing (must not equal `DATABASE_URL` for safety).
* `OLLAMA_MODEL`: Target local model name (e.g. `llama3.2:latest`).
* `PIPER_MODEL` & `PIPER_EXECUTABLE`: Paths to voice models and synthesizer binary.
* `FFMPEG_PATH` & `FFPROBE_PATH`: Paths to local media rendering tools.

### Test Database Setup

Before running tests, create a dedicated test database to isolate tests from production data:

1. Create a `yace_test` database:
   ```bash
   .postgres/bin/createdb.exe -h localhost -p 5432 -U postgres yace_test
   ```
2. Apply the Alembic migrations to your test database:
   ```bash
   $env:APP_ENV="test"; venv/Scripts/alembic.exe upgrade head
   ```

### Running Demo Pipeline

You can run the end-to-end automated demo pipeline to generate topics, script, SEO metadata, voice narration, scene structures, and the final video using:

```bash
python scripts/demo_run.py "AI Automation"
```

The pipeline will:
1. Generate topics and select the highest-scoring candidate.
2. Produce a full narration script.
3. Formulate optimized SEO title, tags, and description metadata.
4. Clean and synthesize speech to a WAV narration track.
5. Breakdown the script into scene layouts with fallback search keywords.
6. Build video visual assets and stitch them into a slideshow synced to narration.
7. Burn styled SRT subtitles directly into the video stream.
8. Output execution results to `generated/reports/demo_report.json` and logs to `logs/demo_run.log`.

### AI Audit Logs

All Ollama LLM requests (including prompts, responses, agent types, models, durations, and success status) are logged in the `ai_generations` database table. You can query them using standard SQL:

```sql
SELECT agent_name, model, success, duration_ms FROM ai_generations;
```

This supports traceability, prompt optimization, and debugging.

### Troubleshooting

* **Pydantic ValidationError on startup**: Ensure you do not leave environment variables empty in `.env`. If a setting (such as `PIPER_SPEAKER_ID`) is not used, comment it out (`# PIPER_SPEAKER_ID=`) rather than assigning it an empty string.
* **OperationalError on database yace_test**: Ensure you have created the `yace_test` database and run alembic migrations on it.
* **404 Not Found from Ollama**: Ensure the target model specified in `OLLAMA_MODEL` is pulled and running locally. Run `ollama list` to inspect installed models.
* **Duration Consistency Mismatch**: If narration validation fails because scene plans are not aligned with audio duration, check that `SPEECH_WORDS_PER_SECOND` in your `.env` matches the narration speed of your active voice model.

