"""Markdown builder — converts a Paper object to a Markdown document."""

from __future__ import annotations

from pathlib import Path

from academic_paper_api.models import Figure, Paper


def paper_to_markdown(paper: Paper) -> str:
    """Convert a Paper dataclass to a Markdown string.

    Produces a document with:
    - Title as h1
    - Authors as a byline
    - DOI and publisher metadata
    - Abstract in a blockquote
    - Keywords (if any)
    - Sections with proper heading levels
    - Figures placed inline with ![caption](path)
    """
    lines: list[str] = []

    # Title
    lines.append(f"# {paper.title}")
    lines.append("")

    # Authors
    if paper.authors:
        lines.append(f"**Authors:** {', '.join(paper.authors)}")
        lines.append("")

    # Metadata
    lines.append(f"**DOI:** [{paper.doi}](https://doi.org/{paper.doi})")
    if paper.publisher:
        lines.append(f"**Publisher:** {paper.publisher.upper()}")
    if paper.url:
        lines.append(f"**URL:** [{paper.url}]({paper.url})")
    lines.append("")

    # Keywords
    if paper.keywords:
        lines.append(f"**Keywords:** {', '.join(paper.keywords)}")
        lines.append("")

    # Abstract
    if paper.abstract:
        lines.append("## Abstract")
        lines.append("")
        lines.append(f"> {paper.abstract}")
        lines.append("")

    # Sections
    for section in paper.sections:
        heading_prefix = "#" * min(section.level + 1, 6)  # offset by 1 since title is h1
        lines.append(f"{heading_prefix} {section.heading}")
        lines.append("")

        for block in section.content:
            if isinstance(block, Figure):
                _render_figure(lines, block)
            elif isinstance(block, str):
                lines.append(block)
                lines.append("")

    return "\n".join(lines)


def _render_figure(lines: list[str], fig: Figure) -> None:
    """Render a figure as markdown image with caption."""
    if not fig.local_path and not fig.url:
        return

    path = fig.local_path or fig.url
    caption = fig.caption or fig.figure_id or "Figure"

    lines.append(f"![{caption}]({path})")
    if fig.caption:
        lines.append(f"*{fig.caption}*")
    lines.append("")


def save_paper(paper: Paper, output_dir: Path) -> Path:
    """Save a Paper as Markdown to the output directory.

    Args:
        paper: The Paper to save.
        output_dir: Target directory.

    Returns:
        Path to the saved Markdown file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    md_content = paper_to_markdown(paper)

    # Sanitize title for filename
    safe_title = "".join(
        c if c.isalnum() or c in " -_" else "_" for c in paper.title
    )[:80].strip()
    filename = f"{safe_title}.md" if safe_title else "paper.md"

    out_path = output_dir / filename
    out_path.write_text(md_content, encoding="utf-8")
    return out_path
