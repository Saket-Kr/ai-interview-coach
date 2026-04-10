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
