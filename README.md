# AI Interview Coach

An AI-powered technical interview coach that helps you prepare for and improve at technical interviews. Practice with a live AI interviewer, or upload a recorded interview for detailed analysis.

## What it does

**Mock Interview Simulator** — A web-based mock interview where an AI interviewer asks you real technical questions, listens to your spoken answers, follows up based on what you say, and manages time like a real interview. When the session ends, you get a detailed analysis report.

**Recording Analyzer** — Upload an audio recording of a real interview you've already had. The tool transcribes it, identifies questions and answers, and generates a brutally honest feedback report with scores, gaps, and a prioritized improvement plan.

### Analysis covers

- **Content** — Technical accuracy, depth, specificity, completeness, trade-off awareness
- **Communication** — Structure, conciseness, clarity, filler words, recovery under pressure
- **Interaction** — Clarifying questions, listening, adaptability
- **Overall** — Role fit assessment, technical depth map, improvement plan with severity levels, tailored practice questions

### Domains supported

System Design, Agentic AI, RAG & Information Retrieval, LLM Engineering, Data Structures & Algorithms, Backend Engineering

### Configurable

- **Role level** — Junior, Mid, Senior, Staff/Principal
- **Difficulty** — Easy, Medium, Hard
- **Duration** — 30, 45, 60, or 90 minutes

---

## Setup

**Requirements:** Python 3.11+, ffmpeg

```bash
git clone https://github.com/Saket-Kr/ai-interview-coach.git
cd ai-interview-coach

python -m venv .venv
source .venv/bin/activate

pip install -e .
```

**Configure your LLM endpoint:**

```bash
cp .env.example .env
# Edit .env with your LLM endpoint details
```

The tool works with any OpenAI-compatible API (vLLM, Ollama, LiteLLM, etc.).

**Install ffmpeg** (required for audio processing):

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html and add to PATH
```

### Voice model (WhisperX)

WhisperX handles speech-to-text. Models are downloaded automatically on first run.

| Model | Size | Speed (CPU) | Accuracy | Best for |
|---|---|---|---|---|
| `base` (default) | ~150 MB | Fast (~2 min for 30 min audio) | Good | Mock interviews, quick analysis |
| `medium` | ~1.5 GB | Moderate (~8 min for 30 min audio) | Better | Recorded interview analysis |
| `large-v3` | ~3 GB | Slow (~20 min for 30 min audio) | Best | Final reports where accuracy matters |

To change the model, set the env var before running:

```bash
# In your .env or shell
export WHISPER_MODEL=medium
```

Or pass it in code — the default is `base` in `config.py`.

**GPU acceleration:** If you have a CUDA-compatible GPU, WhisperX will use it automatically and transcription will be 10-20x faster. No config change needed.

**Speaker diarization (optional):** To identify who said what in recorded interviews, you need a HuggingFace token:

1. Create a token at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
2. Accept the terms for [pyannote/speaker-diarization](https://huggingface.co/pyannote/speaker-diarization-3.1)
3. Set `HF_TOKEN` in your `.env` or pass `--hf-token` to the CLI

Without it, the tool still works — the LLM infers speakers from context. Diarization just makes it more accurate.

---

## Usage

### Mock Interview (Web UI)

```bash
interview-simulator
```

Open [http://localhost:8000](http://localhost:8000) — select your domain, role, difficulty, and duration. Click start, speak into your mic, and the AI interviewer handles the rest.

### Analyze a Recorded Interview (CLI)

```bash
interview-analyzer \
  --audio recording.mp3 \
  --role "Senior Backend Engineer" \
  --resume resume.pdf \
  --output report.md
```

**Options:**

| Flag | Required | Description |
|---|---|---|
| `--audio, -a` | Yes | Path to interview audio (mp3, wav, m4a, flac, ogg, webm) |
| `--role, -r` | Yes | Target role (e.g., "Senior AI Engineer") |
| `--resume` | No | Candidate resume PDF — enables resume-aware evaluation |
| `--jd` | No | Job description text file |
| `--output, -o` | No | Output path (default: `report.md`) |
| `--hf-token` | No | HuggingFace token for speaker diarization |
| `--verbose, -v` | No | Debug logging |

---

## Tech Stack

- **Transcription** — WhisperX (local, free)
- **LLM** — Any OpenAI-compatible endpoint
- **Web** — FastAPI + vanilla JS
- **Audio capture** — Browser MediaRecorder API
- **Analysis** — Parallel LLM evaluation across content, communication, and interaction dimensions

---

## License

MIT
