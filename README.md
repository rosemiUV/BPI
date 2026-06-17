# YouTube Plenary Search Engine MVP

This repository contains an MVP to process YouTube links from government plenary sessions, transcribe the audio, identify speakers, and provide semantic search over the generated content.

## 4-Block Pipeline

1. **Block A — Extraction / ASR**
   - Download audio from YouTube.
   - Transcribe with timestamps using `faster-whisper`.
2. **Block B — Diarization**
   - Assign speaker labels over time segments with `pyannote.audio`.
3. **Block C — RAG Search Engine**
   - Chunk text, store embeddings in ChromaDB, and retrieve relevant context.
4. **Block D — Streamlit UI**
   - Process videos and run semantic search from a simple web interface.

## Project Structure

- `requirements.txt`
- `src/transcriber.py` (Block A)
- `src/diarizer.py` (Block B)
- `src/search_engine.py` (Block C)
- `src/app.py` (Block D)

## Setup Instructions

1. Clone the repository.
2. Create and activate a virtual environment.
   - Linux/macOS:
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```powershell
     python -m venv .venv
     .venv\Scripts\Activate.ps1
     ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. (Optional) Create a `.env` file for provider/model tokens.
5. Run the Streamlit app:
   ```bash
   streamlit run src/app.py
   ```

## MVP Notes

- Heavy ML integrations are scaffolded with safe fallbacks so the project can run out of the box.
- Replace mock/fallback logic with production model setup when moving beyond MVP stage.
