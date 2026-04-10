"""Render the analysis result into a markdown report."""

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from interview_analyzer.models import AnalysisResult

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"


def render_report(result: AnalysisResult, role: str) -> str:
    """Render the analysis result into a markdown string."""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("report.md.j2")
    return template.render(result=result, role=role)


def write_report(result: AnalysisResult, role: str, output_path: Path) -> None:
    """Render and write the report to a file."""
    markdown = render_report(result, role)
    output_path.write_text(markdown)
    logger.info("Report written to %s", output_path)
