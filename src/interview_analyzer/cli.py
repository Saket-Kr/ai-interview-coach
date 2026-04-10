"""CLI entry point for interview-analyzer."""

import logging
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.logging import RichHandler

from interview_analyzer.analyzer import analyze
from interview_analyzer.config import Config
from interview_analyzer.report import write_report

app = typer.Typer(
    name="interview-analyzer",
    help="Analyze technical interview recordings and generate feedback reports.",
    no_args_is_help=True,
)
console = Console()

SUPPORTED_AUDIO_FORMATS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".webm"}


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )


@app.command()
def run(
    audio: Path = typer.Option(
        ..., "--audio", "-a", help="Path to interview audio recording",
    ),
    role: str = typer.Option(
        ..., "--role", "-r", help='Target role (e.g., "Senior Backend Engineer")',
    ),
    jd: Optional[Path] = typer.Option(
        None, "--jd", help="Path to job description text file",
    ),
    resume: Optional[Path] = typer.Option(
        None, "--resume", help="Path to candidate resume (PDF)",
    ),
    output: Path = typer.Option(
        Path("report.md"), "--output", "-o", help="Output path for the markdown report",
    ),
    llm_url: Optional[str] = typer.Option(
        None, "--llm-url", help="LLM API base URL (overrides default/env)",
    ),
    llm_model: Optional[str] = typer.Option(
        None, "--llm-model", help="LLM model name (overrides default/env)",
    ),
    hf_token: Optional[str] = typer.Option(
        None, "--hf-token", help="HuggingFace token for speaker diarization (pyannote)",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging"),
) -> None:
    """Analyze a technical interview recording and generate a feedback report."""
    _setup_logging(verbose)

    # Validate inputs
    if not audio.exists():
        console.print(f"[red]Error:[/red] Audio file not found: {audio}")
        raise typer.Exit(1)
    if audio.suffix.lower() not in SUPPORTED_AUDIO_FORMATS:
        console.print(
            f"[red]Error:[/red] Unsupported audio format '{audio.suffix}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_AUDIO_FORMATS))}"
        )
        raise typer.Exit(1)
    if jd and not jd.exists():
        console.print(f"[red]Error:[/red] Job description file not found: {jd}")
        raise typer.Exit(1)
    if resume and not resume.exists():
        console.print(f"[red]Error:[/red] Resume file not found: {resume}")
        raise typer.Exit(1)

    # Build config with overrides
    config = Config()
    if llm_url:
        config.llm_base_url = llm_url
    if llm_model:
        config.llm_model = llm_model
    if hf_token:
        config.hf_token = hf_token

    console.print(f"\n[bold]Interview Analyzer[/bold]")
    console.print(f"  Audio:  {audio}")
    console.print(f"  Role:   {role}")
    console.print(f"  Model:  {config.llm_model}")
    if jd:
        console.print(f"  JD:     {jd}")
    if resume:
        console.print(f"  Resume: {resume}")
    console.print(f"  Output: {output}\n")

    try:
        result = analyze(
            audio_path=audio,
            role=role,
            config=config,
            jd_path=jd,
            resume_path=resume,
        )
        write_report(result, role, output)
        console.print(f"\n[green]Done![/green] Report written to [bold]{output}[/bold]")
        console.print(
            f"Overall score: [bold]{result.overall.overall_score:.1f}/10[/bold]"
        )
    except Exception as e:
        console.print(f"\n[red]Analysis failed:[/red] {e}")
        logging.debug("Full traceback:", exc_info=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
